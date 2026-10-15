
"""
EnejiStats stats-tracker routes.

This module is limited to the APIs used by the supplied stats-tracker.html:

    GET  /api/dco/assignments
    GET  /api/dco/metrics
    GET  /api/dco/submissions
    POST /api/dco/accept-assignment
    POST /api/dco/decline-assignment
    POST /api/dco/{id}/widget/submit
    POST /api/dco/{id}/widget/save-draft
    POST /api/dco/{id}/liveness/heartbeat
    DELETE /api/dco/{id}/liveness/heartbeat

``GET /api/dco/user-info`` is intentionally owned by
``dco_dashboard_routes.py`` because it is a shared identity endpoint called
by both pages.  Register both routers from main.py; that avoids duplicate
FastAPI route registrations.
"""

# Integration contract: this router owns the Stats Tracker endpoints only.
# Register exactly once alongside dco_dashboard_routes_aligned.router.
# The shared GET /api/dco/user-info endpoint is owned by the dashboard router;
# do not duplicate it here. Keep /api/dco/submissions distinct from the
# dashboard's /api/dco/{id}/submissions legacy player-stat-record endpoint.


from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError


router = APIRouter(tags=["Stats tracker"])

_READY = False
_database = None
_submission_index_lock = asyncio.Lock()
_submission_indexes_ready = False
dco_collection = None
dco_tokens_collection = None
activity_history_collection = None
dco_assignments_collection = None
liveness_sessions_collection = None
stats_requests_collection = None
players_collection = None
clubs_collection = None
stat_submissions_collection = None
stat_submission_players_collection = None
stat_events_collection = None
stat_drafts_collection = None
stat_draft_players_collection = None
stat_draft_events_collection = None

get_current_user = None
get_dco_user = None
MongoSerializer = None
logger = None
calculate_performance_score = None


def _setup_dependencies(main_globals: dict) -> None:
    """Inject only the collections/helpers required by the stats tracker."""
    global _READY, _database, dco_collection, dco_tokens_collection
    global activity_history_collection, dco_assignments_collection
    global liveness_sessions_collection
    global stats_requests_collection, players_collection, clubs_collection
    global stat_submissions_collection, stat_submission_players_collection
    global stat_events_collection, stat_drafts_collection
    global stat_draft_players_collection, stat_draft_events_collection
    global get_current_user, get_dco_user, MongoSerializer, logger
    global calculate_performance_score
    if _READY:
        return

    _database = main_globals["database"]

    def collection(name: str, global_name: str) -> Any:
        value = main_globals.get(global_name)
        return value if value is not None else _database[name]

    dco_collection = collection("dco", "dco_collection")
    dco_tokens_collection = collection("dco_tokens", "dco_tokens_collection")
    activity_history_collection = collection("activity_history", "activity_history_collection")
    dco_assignments_collection = collection("dco_assignments", "dco_assignments_collection")
    liveness_sessions_collection = collection("liveness_sessions", "liveness_sessions_collection")
    stats_requests_collection = collection("stats_requests", "stats_requests_collection")
    players_collection = collection("players", "players_collection")
    clubs_collection = collection("clubs", "clubs_collection")
    stat_submissions_collection = collection("stat_submissions", "stat_submissions_collection")
    stat_submission_players_collection = collection(
        "stat_submission_players", "stat_submission_players_collection"
    )
    stat_events_collection = collection("stat_events", "stat_events_collection")
    stat_drafts_collection = collection("stat_drafts", "stat_drafts_collection")
    stat_draft_players_collection = collection(
        "stat_draft_players", "stat_draft_players_collection"
    )
    stat_draft_events_collection = collection(
        "stat_draft_events", "stat_draft_events_collection"
    )

    get_current_user = main_globals["get_current_user"]
    get_dco_user = main_globals.get("get_dco_user", get_current_user)
    MongoSerializer = main_globals.get("MongoSerializer")
    logger = main_globals.get("logger")
    calculate_performance_score = main_globals.get("calculate_performance_score", lambda *_: 0)
    _READY = True


def _now() -> Any:
    if MongoSerializer is not None and hasattr(MongoSerializer, "now_utc"):
        return MongoSerializer.now_utc()
    return MongoSerializer.now_utc()


def _serialize(value: Any) -> Any:
    return MongoSerializer.serialize_value(value)


def _dco_id(document: dict) -> str:
    return str(
        document.get("dco_id")
        or document.get("dcoId")
        or document.get("data_scout_id")
        or document.get("dataScoutId")
        or document.get("user_id")
        or document.get("uid")
        or document.get("id")
        or document.get("_id")
        or ""
    )


async def _token_balance(identifier: str) -> int:
    """Return the DCO token balance using the same wallet keys as the dashboard routes."""
    wallet = await dco_tokens_collection.find_one(
        {"$or": [{"dco_id": identifier}, {"user_id": identifier}]}
    )
    return int((wallet or {}).get("balance", 0))


def _authorize(current_user: dict, identifier: str) -> None:
    if str(current_user.get("role") or "").lower() in {"admin", "supervisor"}:
        return
    owner_ids = {
        str(current_user.get("dco_id") or ""),
        str(current_user.get("data_scout_id") or ""),
        str(current_user.get("user_id") or ""),
        str(current_user.get("_id") or ""),
    }
    if str(identifier) not in owner_ids:
        raise HTTPException(status_code=403, detail="Access denied")


def _assignment_filter(value: Any) -> Dict[str, Any]:
    text = str(value or "")
    return {"_id": ObjectId(text)} if ObjectId.is_valid(text) else {"assignment_id": value}


def _number(value: Any, field: str, allow_float: bool = False) -> int | float:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        if allow_float:
            parsed = float(value)
        else:
            numeric = float(value)
            if not numeric.is_integer():
                raise ValueError(f"{field} must be an integer")
            parsed = int(numeric)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(float(parsed)) or parsed < 0:
        raise ValueError(f"{field} must be finite and non-negative")
    return parsed


_METRIC_REGISTRY = {
    "outfield": (
        "goals", "assists", "shots", "passes", "dribbles", "carries", "crosses",
        "tackles", "duels", "fouls_won", "fouls_committed", "interceptions",
        "recoveries", "clearances", "blocks", "defensive_errors", "cards",
        "offsides", "substitution", "key_passes", "big_chances", "pressure_actions",
        "possession_losses", "progressive_passes", "progressive_carries",
        "final_third_entries", "penalty_area_entries",
    ),
    "goalkeeper": (
        "saves", "shots_faced", "punches", "claims", "goals_conceded",
        "distribution", "passes", "dribbles", "carries", "tackles", "duels",
        "fouls_won", "fouls_committed", "interceptions", "recoveries", "clearances",
        "blocks", "defensive_errors", "cards", "offsides", "substitution",
        "key_passes", "big_chances", "pressure_actions", "possession_losses",
        "progressive_passes", "progressive_carries", "final_third_entries",
        "penalty_area_entries",
    ),
}
_OUTFIELD_METRIC_KEYS = _METRIC_REGISTRY["outfield"]
_GOALKEEPER_METRIC_KEYS = _METRIC_REGISTRY["goalkeeper"]
_POSITION_STAT_FIELDS = {
    "outfield": (
        "goals",
        "shot_goals",
        "header_goals",
        "penalty_goals",
        "assists",
        "shots_on_target",
        "shots_off_target",
        "successful_short_passes",
        "unsuccessful_short_passes",
        "successful_long_passes",
        "unsuccessful_long_passes",
        "successful_dribbles",
        "unsuccessful_dribbles",
        "successful_crosses",
        "unsuccessful_crosses",
        "tackles_won",
        "tackles_lost",
        "aerial_duels_won",
        "aerial_duels_lost",
        "interceptions",
        "clearances",
        "dispossessed",
        "yellow_cards",
        "red_cards",
        "fouls_given",
        "fouls_won",
        "offsides",
        "shots",
        "shots_blocked",
        "free_kick_goals",
        "chances_created",
        "passes_attempted",
        "passes_completed",
        "through_balls",
        "switches",
        "final_third_passes",
        "penalty_area_passes",
        "progressive_passes",
        "progressive_dribbles",
        "duels_won",
        "duels_lost",
        "shots_on_target_faced",
        "penalty_goals_conceded",
        "key_passes",
        "carries",
        "fouls_committed",
        "cards",
        "substitution",
        "big_chances",
        "pressure_actions",
        "possession_losses",
        "advanced_progressive_passes",
        "advanced_progressive_carries",
        "advanced_final_third",
        "advanced_penalty_area",
    ),
    "goalkeeper": (
        "saves",
        "goals_conceded",
        "penalty_saves",
        "clean_sheets",
        "successful_distributions",
        "unsuccessful_distributions",
        "punches",
        "successful_short_passes",
        "unsuccessful_short_passes",
        "successful_long_passes",
        "unsuccessful_long_passes",
        "interceptions",
        "clearances",
        "aerial_duels_won",
        "aerial_duels_lost",
        "tackles_won",
        "tackles_lost",
        "fouls_won",
        "dispossessed",
        "yellow_cards",
        "red_cards",
        "fouls_given",
        "offsides",
    "key_passes",
    "carries",
    "progressive_passes",
    "progressive_carries",
    "final_third_entries",
    "penalty_area_entries",
    "blocks",
    "recoveries",
    "defensive_errors",
    "pressure_actions",
    "shots_faced",
    "claims",
        "shots",
        "shots_blocked",
        "free_kick_goals",
        "chances_created",
        "passes_attempted",
        "passes_completed",
        "through_balls",
        "switches",
        "final_third_passes",
        "penalty_area_passes",
        "progressive_dribbles",
        "duels_won",
        "duels_lost",
        "shots_on_target_faced",
        "penalty_goals_conceded",
        "fouls_committed",
        "cards",
        "substitution",
        "big_chances",
        "possession_losses",
    ),
}
_PAIR_ALIASES = {
    "shots": ("shots_on_target", "shots_off_target"),
    "passes": ("successful_short_passes", "unsuccessful_short_passes"),
    "dribbles": ("successful_dribbles", "unsuccessful_dribbles"),
    "crosses": ("successful_crosses", "unsuccessful_crosses"),
    "duels": ("aerial_duels_won", "aerial_duels_lost"),
    "tackles": ("tackles_won", "tackles_lost"),
    "distribution": ("successful_distributions", "unsuccessful_distributions"),
}
_SINGLE_ALIASES = {
    "assists": ("assists",),
    "cards": ("cards",),
    "fouls_won": ("fouls_won", "foulsWon"),
    "dispossessed": ("dispossessed",),
    "interceptions": ("interceptions",),
    "clearances": ("clearances",),
    "saves": ("saves",),
    "goals_conceded": ("goals_conceded", "goalsConceded"),
    "penalty_saves": ("penalty_saves", "penaltySaves"),
    "clean_sheets": ("clean_sheets", "cleanSheets"),
    "punches": ("punches",),
    "yellow_cards": ("yellow_cards", "yellowCards"),
    "red_cards": ("red_cards", "redCards"),
    "fouls_given": ("fouls_given", "fouls"),
    "offsides": ("offsides",),
}

_EVENT_TYPE_TO_METRIC = {
    "goal": "goals",
    "assist": "assists",
    "shot": "shots",
    "pass": "passes",
    "dribble": "dribbles",
    "cross": "crosses",
    "foul_won": "fouls_won",
    "foul_committed": "fouls_committed",
    "dispossessed": "dispossessed",
    "duel": "duels",
    "tackle": "tackles",
    "interception": "interceptions",
    "clearance": "clearances",
    "recovery": "recoveries",
    "block": "blocks",
    "defensive_error": "defensive_errors",
    "save": "saves",
    "goal_conceded": "goals_conceded",
    "punch": "punches",
    "distribution": "distribution",
    "card": "cards",
    "offside": "offsides",
    "substitution": "substitution",
    "key_pass": "key_passes",
    "carry": "carries",
    "progressive_pass": "progressive_passes",
    "progressive_carry": "progressive_carries",
    "final_third_entry": "final_third_entries",
    "penalty_area_entry": "penalty_area_entries",
    "pressure_action": "pressure_actions",
    "big_chance": "big_chances",
    "possession_loss": "possession_losses",
    "shot_faced": "shots_faced",
    "claim": "claims",
}

# Accept payloads produced by both the current mounted-player widget and
# earlier tracker builds.  These are metric-name aliases, not extra
# capabilities; they are canonicalized before position validation.
_METRIC_ALIASES = {
    "goals": "goals",
    "assists": "assists",
    "shots": "shots",
    "passes": "passes",
    "dribbles": "dribbles",
    "carries": "carries",
    "crosses": "crosses",
    "tackles": "tackles",
    "duels": "duels",
    "fouls_won": "fouls_won",
    "fouls_committed": "fouls_committed",
    "interceptions": "interceptions",
    "recoveries": "recoveries",
    "clearances": "clearances",
    "blocks": "blocks",
    "defensive_errors": "defensive_errors",
    "cards": "cards",
    "offsides": "offsides",
    "substitution": "substitution",
    "key_passes": "key_passes",
    "big_chances": "big_chances",
    "pressure_actions": "pressure_actions",
    "possession_losses": "possession_losses",
    "progressive_passes": "progressive_passes",
    "progressive_carries": "progressive_carries",
    "final_third_entries": "final_third_entries",
    "penalty_area_entries": "penalty_area_entries",
    "saves": "saves",
    "shots_faced": "shots_faced",
    "punches": "punches",
    "claims": "claims",
    "goals_conceded": "goals_conceded",
    "distribution": "distribution",
    "longpass": "passes",
    "long_pass": "passes",
    "foulsWon": "fouls_won",
    "foulsCommitted": "fouls_committed",
    "keyPasses": "key_passes",
    "defensiveErrors": "defensive_errors",
    "pressureActions": "pressure_actions",
    "bigChances": "big_chances",
    "possessionLosses": "possession_losses",
    "progressivePasses": "progressive_passes",
    "progressiveCarries": "progressive_carries",
    "finalThirdEntries": "final_third_entries",
    "penaltyAreaEntries": "penalty_area_entries",
    "goalsConceded": "goals_conceded",
    "shotsFaced": "shots_faced",
    "substitutions": "substitution",
    "shot_faced": "shots_faced",
    "penaltySaves": "penalty_saves",
    "cleanSheets": "clean_sheets",
    "yellowCards": "cards",
    "redCards": "cards",
    "fouls": "fouls_committed",
}


def _read_stat(stats: dict, keys: tuple[str, ...], nested: str = "success") -> int:
    for key in keys:
        if key not in stats:
            continue
        value = stats[key]
        if isinstance(value, dict):
            value = value.get(nested, value.get("success", 0))
        return int(_number(value, key))
    return 0


def _is_goalkeeper_position(position: Any) -> bool:
    normalized = str(position or "").strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    return (
        normalized in {"gk", "g", "goalkeeper", "goal keeper", "goalie"}
        or "keeper" in normalized
        or "goalie" in normalized
    )


def _position_metric_keys(position: str) -> tuple[str, ...]:
    return _GOALKEEPER_METRIC_KEYS if _is_goalkeeper_position(position) else _OUTFIELD_METRIC_KEYS


def _position_stat_fields(position: str) -> tuple[str, ...]:
    return _POSITION_STAT_FIELDS["goalkeeper" if _is_goalkeeper_position(position) else "outfield"]


def _normalise_stats(raw_stats: dict, position: str) -> Dict[str, int]:
    """Convert the widget's exact nested/canonical stats into exact persisted keys."""
    is_goalkeeper = _is_goalkeeper_position(position)
    canonical: Dict[str, int] = {field: 0 for field in _position_stat_fields(position)}

    goals = raw_stats.get("goals", 0)
    shot_goals = raw_stats.get("shot_goals", raw_stats.get("shotGoals", None))
    header_goals = raw_stats.get("header_goals", raw_stats.get("headerGoals", None))
    penalty_goals = raw_stats.get("penalty_goals", raw_stats.get("penaltyGoals", None))
    if isinstance(goals, dict):
        goal_values = {
            "shot": _number(goals.get("shot", goals.get("shots", 0)), "stats.goals.shot"),
            "header": _number(goals.get("header", 0), "stats.goals.header"),
            "penalty": _number(goals.get("penalty", 0), "stats.goals.penalty"),
        }
        if not is_goalkeeper:
            canonical["shot_goals"] = int(goal_values["shot"])
            canonical["header_goals"] = int(goal_values["header"])
            canonical["penalty_goals"] = int(goal_values["penalty"])
            canonical["goals"] = sum(int(value) for value in goal_values.values())
    elif not is_goalkeeper:
        # The frontend sends `goals` as the aggregate and the three breakdowns.
        # A legacy scalar is treated as a shot goal so it is never lost.
        canonical["goals"] = int(_number(goals, "stats.goals"))

    if not is_goalkeeper:
        if shot_goals is not None or header_goals is not None or penalty_goals is not None:
            breakdown = {
                "shot_goals": int(_number(shot_goals or 0, "stats.shot_goals")),
                "header_goals": int(_number(header_goals or 0, "stats.header_goals")),
                "penalty_goals": int(_number(penalty_goals or 0, "stats.penalty_goals")),
            }
            aggregate = int(_number(goals, "stats.goals")) if not isinstance(goals, dict) else sum(breakdown.values())
            if aggregate != sum(breakdown.values()):
                raise ValueError("stats.goals must equal shot_goals + header_goals + penalty_goals")
            canonical.update(breakdown)
            canonical["goals"] = aggregate

    for widget_key, (success, failure) in _PAIR_ALIASES.items():
        if widget_key not in _position_metric_keys(position):
            continue
        canonical[success] = _read_stat(raw_stats, (success, widget_key), "success")
        canonical[failure] = _read_stat(raw_stats, (failure, widget_key), "fail")

    for field, aliases in _SINGLE_ALIASES.items():
        widget_key = {
            "fouls_won": "fouls_won",
            "goals_conceded": "goals_conceded",
            "penalty_saves": "penalty_saves",
            "clean_sheets": "clean_sheets",
        }.get(field, field)
        if widget_key not in _position_metric_keys(position):
            continue
        canonical[field] = _read_stat(raw_stats, aliases)

    # Cards are one widget capability, but the tracker may also send explicit
    # yellow/red breakdowns.  Preserve those breakdowns without copying their
    # values into the aggregate `cards` field.
    for field, aliases in {
        "yellow_cards": ("yellow_cards", "yellowCards"),
        "red_cards": ("red_cards", "redCards"),
    }.items():
        if any(alias in raw_stats for alias in aliases):
            canonical[field] = _read_stat(raw_stats, aliases)

    # Preserve the mounted-player tracker metrics that are not part of the
    # older short-form alias tables.  This also makes legacy submissions that
    # contain stats but no event array fully lossless.
    extra_fields = {
        "key_passes": "key_passes",
        "keyPasses": "key_passes",
        "fouls_committed": "fouls_committed",
        "foulsCommitted": "fouls_committed",
        "cards": "cards",
        "substitution": "substitution",
        "substitutions": "substitution",
        "bigChances": "big_chances",
        "big_chances": "big_chances",
        "pressureActions": "pressure_actions",
        "pressure_actions": "pressure_actions",
        "possessionLosses": "possession_losses",
        "possession_losses": "possession_losses",
        "advancedProgressivePasses": "advanced_progressive_passes",
        "advancedProgressiveCarries": "advanced_progressive_carries",
        "advancedFinalThird": "advanced_final_third",
        "advancedPenaltyArea": "advanced_penalty_area",
        "progressive_passes": "progressive_passes",
        "progressivePasses": "progressive_passes",
        "progressive_carries": "progressive_carries",
        "progressiveCarries": "progressive_carries",
        "final_third_entries": "final_third_entries",
        "finalThirdEntries": "final_third_entries",
        "penalty_area_entries": "penalty_area_entries",
        "penaltyAreaEntries": "penalty_area_entries",
        "defensive_errors": "defensive_errors",
        "defensiveErrors": "defensive_errors",
        "shots_faced": "shots_faced",
        "shotsFaced": "shots_faced",
        "claims": "claims",
    }
    for widget_key, field in extra_fields.items():
        canonical_widget_key = _METRIC_ALIASES.get(widget_key, widget_key)
        if canonical_widget_key in _position_metric_keys(position) and field in canonical:
            canonical[field] = _read_stat(raw_stats, (widget_key, field))

    # The frontend's canonical transform includes these goalkeeping fields and
    # never sends goal metrics for a goalkeeper.
    return canonical


def _provided_stat_fields(raw_stats: dict, position: str) -> set[str]:
    """Return only fields represented by the frontend's outgoing stats object."""
    provided: set[str] = set()
    if "goals" in raw_stats:
        provided.add("goals")
    for field, aliases in {
        "shot_goals": ("shot_goals", "shotGoals"),
        "header_goals": ("header_goals", "headerGoals"),
        "penalty_goals": ("penalty_goals", "penaltyGoals"),
    }.items():
        if any(alias in raw_stats for alias in aliases):
            provided.add(field)
    for widget_key, (success, failure) in _PAIR_ALIASES.items():
        if widget_key not in _position_metric_keys(position):
            continue
        if any(key in raw_stats for key in (success, failure, widget_key)):
            provided.update((success, failure))
    for field, aliases in _SINGLE_ALIASES.items():
        widget_key = {
            "fouls_won": "fouls_won",
            "goals_conceded": "goals_conceded",
            "penalty_saves": "penalty_saves",
            "clean_sheets": "clean_sheets",
        }.get(field, field)
        if widget_key in _position_metric_keys(position) and any(key in raw_stats for key in aliases):
            provided.add(field)
    return provided


def _stats_from_events(events: List[Dict[str, Any]], position: str) -> Dict[str, int]:
    """Derive the exact persisted stats shape from the widget's canonical events."""
    # Derive from the complete registry.  This keeps counters intact when a
    # player is position-switched after recording an event and prevents a
    # valid metric from disappearing merely because the final position differs
    # from the position at the time of the tap.
    derived = {
        field: 0
        for field in dict.fromkeys(
            (*_POSITION_STAT_FIELDS["outfield"], *_POSITION_STAT_FIELDS["goalkeeper"])
        )
    }
    pair_fields = {
        "shots": ("shots_on_target", "shots_off_target"),
        "passes": ("successful_short_passes", "unsuccessful_short_passes"),
        "dribbles": ("successful_dribbles", "unsuccessful_dribbles"),
        "crosses": ("successful_crosses", "unsuccessful_crosses"),
        "duels": ("aerial_duels_won", "aerial_duels_lost"),
        "tackles": ("tackles_won", "tackles_lost"),
        "distribution": ("successful_distributions", "unsuccessful_distributions"),
    }
    single_fields = {
        "assists": "assists",
        "fouls_won": "fouls_won",
        "dispossessed": "dispossessed",
        "interceptions": "interceptions",
        "clearances": "clearances",
        "saves": "saves",
        "goals_conceded": "goals_conceded",
        "punches": "punches",
        "cards": "cards",
        "fouls_committed": "fouls_committed",
        "offsides": "offsides",
    }
    for event in events:
        metric = event["metric"]
        contributions = event.get("derived_contributions", {})
        if not isinstance(contributions, dict):
            contributions = {}
        if metric == "goals":
            field = {
                "shot": "shot_goals",
                "header": "header_goals",
                "penalty": "penalty_goals",
            }.get(event.get("value_type", event.get("valueType", "open_play")), "shot_goals")
            if field not in contributions:
                derived[field] += 1
            derived["goals"] += 1
        elif metric in pair_fields:
            pair = pair_fields[metric]
            value_type = str(event.get("value_type") or event.get("sub_key") or "").lower()
            if metric == "passes" and (
                value_type in {"long", "pass_long"}
                or value_type.endswith("_long")
            ):
                pair = ("successful_long_passes", "unsuccessful_long_passes")
            field = pair[event["outcome"] == "failure"]
            if field not in contributions:
                derived[field] += 1
        elif metric in single_fields:
            field = single_fields[metric]
            if field not in contributions:
                derived[field] += 1
        elif metric in derived:
            # The mounted-player widget has several metric-specific subtype
            # buttons (for example short_success and short_fail).  Events are
            # the source of truth; retain a safe aggregate for score/report
            # calculations without dropping the subtype from the event row.
            if metric not in contributions:
                derived[metric] += 1
        else:
            field = {
                "key_passes": "key_passes",
                "fouls_committed": "fouls_committed",
                "big_chances": "big_chances",
                "pressure_actions": "pressure_actions",
                "possession_losses": "possession_losses",
                "progressive_passes": "progressive_passes",
                "progressive_carries": "progressive_carries",
                "final_third_entries": "final_third_entries",
                "penalty_area_entries": "penalty_area_entries",
                "defensive_errors": "defensive_errors",
                "shots_faced": "shots_faced",
                "claims": "claims",
                "cards": "cards",
                "substitution": "substitution",
                "recoveries": "recoveries",
                "blocks": "blocks",
            }.get(metric)
            if field in derived:
                derived[field] += 1
        # The widget records derived counters (for example shots on target,
        # chances created, and penalty goals) on the event so the server can
        # reproduce the exact review totals without storing a second copy of
        # the same metric beside the canonical event stream.
        for field, value in contributions.items():
            if field not in derived:
                continue
            try:
                derived[field] += int(_number(value, f"event.derived_contributions.{field}"))
            except (TypeError, ValueError):
                raise ValueError(
                    f"event.derived_contributions.{field} must be a non-negative integer"
                )
    return derived


_HEATMAP_METRICS = {
    "outfield": {
        "goals",
        "assists",
        "shots",
        "passes",
        "longpass",
        "dribbles",
        "crosses",
        "duels",
        "tackles",
        "interceptions",
        "clearances",
    },
    "goalkeeper": {
        "saves",
        "distribution",
        "passes",
        "longpass",
        "clearances",
        "interceptions",
        "duels",
        "tackles",
    },
}


def _normalise_events(raw_events: Any, position: str) -> List[Dict[str, Any]]:
    """Validate and persist the widget's single-source-of-truth event stream."""
    if raw_events is None:
        return []
    if not isinstance(raw_events, list):
        raise ValueError("player.events must be an array")

    # A player can be moved between positions while a match is being tracked.
    # Validate against the complete tracker registry, not only the player's
    # current position, so changing position never turns valid events into a
    # 422 submission failure.
    allowed = set(_OUTFIELD_METRIC_KEYS) | set(_GOALKEEPER_METRIC_KEYS)
    normalised: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_client_event_ids: set[str] = set()
    for index, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, dict):
            raise ValueError(f"events[{index}] must be an object")
        event_id = str(
            raw_event.get("eventId")
            or raw_event.get("event_id")
            or raw_event.get("id")
            or ""
        ).strip()
        if not event_id:
            raise ValueError(f"events[{index}].eventId is required")
        client_event_id = str(
            raw_event.get("clientEventId")
            or raw_event.get("client_event_id")
            or event_id
        ).strip()
        if event_id in seen_ids:
            raise ValueError(f"events[{index}].eventId is duplicated within the player")
        if client_event_id in seen_client_event_ids:
            raise ValueError(f"events[{index}].clientEventId is duplicated within the player")
        seen_ids.add(event_id)
        seen_client_event_ids.add(client_event_id)

        metric = str(
            raw_event.get("metric")
            or raw_event.get("metricKey")
            or raw_event.get("metric_key")
            or _EVENT_TYPE_TO_METRIC.get(
                str(raw_event.get("type") or "").strip().lower()
            )
            or ""
        ).strip()
        metric = _METRIC_ALIASES.get(
            metric,
            _METRIC_ALIASES.get(metric.casefold(), metric),
        )
        if metric not in allowed:
            raise ValueError(f"events[{index}].metric is not available for position {position}")
        value_type = str(
            raw_event.get("valueType")
            or raw_event.get("value_type")
            or raw_event.get("subKey")
            or raw_event.get("sub_key")
            or ""
        ).strip().lower()
        raw_outcome = str(
            raw_event.get("outcome")
            or raw_event.get("result")
            or ""
        ).strip().lower()
        outcome = raw_outcome
        is_failure = (
            outcome in {
                "fail",
                "failure",
                "unsuccessful",
                "lost",
                "miss",
                "off_target",
                "blocked",
                "woodwork",
                "foul",
            }
            or re.search(r"(^|_)(fail|failure|unsuccessful|lost|miss)$", value_type) is not None
        ) or value_type in {
            "fail",
            "failure",
            "unsuccessful",
            "lost",
            "miss",
            "off_target",
            "blocked",
            "woodwork",
            "foul",
        }
        outcome = "failure" if is_failure and metric != "goals" else "success"
        if metric == "goals":
            value_type = (
                value_type
                if value_type in {
                    "open_play",
                    "set_piece",
                    "shot",
                    "header",
                    "penalty",
                    "free_kick",
                }
                else "open_play"
            )
        else:
            # Preserve the metric subtype.  Only the normalized outcome is
            # collapsed; replacing `short_success`, `line_break`, etc. with
            # success/fail loses information needed for round-trip retrieval.
            value_type = value_type or ("fail" if outcome == "failure" else "success")
            if value_type in {"failure", "unsuccessful", "lost", "miss"}:
                value_type = "fail"

        raw_location = raw_event.get("location")
        if not isinstance(raw_location, dict):
            raw_location = {"x": raw_event.get("x"), "y": raw_event.get("y")}
        x = raw_location.get("x")
        y = raw_location.get("y")
        if x is not None or y is not None:
            if x is None or y is None:
                raise ValueError(f"events[{index}].location requires both x and y")
            try:
                x = float(_number(x, f"events[{index}].x", True))
                y = float(_number(y, f"events[{index}].y", True))
            except (TypeError, ValueError) as exc:
                raise ValueError(str(exc)) from exc
            if not 0 <= x <= 1 or not 0 <= y <= 1:
                raise ValueError(f"events[{index}] coordinates must be between 0 and 1")
        else:
            x = y = None

        multiplier = float(_number(raw_event.get("multiplier", 1), f"events[{index}].multiplier", True))
        metadata = raw_event.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"events[{index}].metadata must be an object")
        raw_clock = raw_event.get("clock")
        if not isinstance(raw_clock, dict):
            raw_clock = {
                "period": raw_event.get("period", raw_event.get("half", 1)),
                "elapsedSeconds": raw_event.get("elapsedSeconds", 0),
            }
        period = int(raw_clock.get("period", raw_clock.get("half", 1)) or 1)
        elapsed_seconds = int(
            raw_clock.get("elapsedSeconds", raw_clock.get("elapsed", 0)) or 0
        )
        if period not in (1, 2) or elapsed_seconds < 0:
            raise ValueError(f"events[{index}].clock is invalid")

        event = {
            "event_id": event_id,
            "event_type": str(
                raw_event.get("type")
                or raw_event.get("eventType")
                or raw_event.get("event_type")
                or metric
            ).strip(),
            "metric": metric,
            "outcome": outcome,
            "outcome_detail": raw_outcome or None,
            "value_type": value_type,
            "sub_key": str(
                raw_event.get("subKey")
                or raw_event.get("sub_key")
                or value_type
                or ""
            ).strip() or None,
            "client_event_id": str(
                client_event_id
            ).strip(),
            "player_id": str(
                raw_event.get("playerId")
                or raw_event.get("player_id")
                or ""
            ).strip() or None,
            "match_id": str(
                raw_event.get("matchId")
                or raw_event.get("match_id")
                or ""
            ).strip() or None,
            "position": str(raw_event.get("position") or "").strip() or None,
            "period": period,
            "elapsed_seconds": elapsed_seconds,
            "multiplier": multiplier or 1,
            "recorded_at": (
                raw_event.get("recordedAt")
                or raw_event.get("recorded_at")
                or raw_event.get("timestamp")
            ),
            "heatmap_required": bool(
                raw_event.get("heatmapRequired", raw_event.get("heatmap_required", False))
            ),
            "heatmap_recorded": bool(
                raw_event.get("heatmapRecorded", raw_event.get("heatmap_recorded", False))
            ),
        }
        attributes = raw_event.get("attributes", {})
        if not isinstance(attributes, dict):
            raise ValueError(f"events[{index}].attributes must be an object")
        event["attributes"] = dict(attributes)
        for key, output_key in (
            ("relatedEventId", "related_event_id"),
            ("related_event_id", "related_event_id"),
            ("derivedFlags", "derived_flags"),
            ("derived_flags", "derived_flags"),
            ("derivedContributions", "derived_contributions"),
            ("derived_contributions", "derived_contributions"),
        ):
            value = raw_event.get(key)
            if value is not None:
                if not isinstance(value, dict):
                    raise ValueError(f"events[{index}].{key} must be an object")
                event[output_key] = dict(value)
        event["status"] = str(raw_event.get("status") or "accepted").strip() or "accepted"
        if x is not None and y is not None:
            event["location"] = {"x": x, "y": y}
        if metadata:
            event["metadata"] = dict(metadata)
        normalised.append(event)
    return normalised


def _normalise_player(raw: Any, player_order: int) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Return a compact player row and its atomic events.

    The submitted player object is never persisted as-is.  Display aliases,
    derived counters, and heatmap projections are intentionally excluded.
    """
    if not isinstance(raw, dict):
        raise ValueError("Each players entry must be an object")

    position = str(raw.get("position") or raw.get("player_position") or "").strip()
    if not position:
        raise ValueError("player.position is required")

    raw_stats = raw.get("stats") or {}
    if not isinstance(raw_stats, dict):
        raise ValueError("player.stats must be an object")

    events = _normalise_events(raw.get("events", []), position)
    event_stats = _stats_from_events(events, position)
    # Events are the authoritative source for the mounted widget.  Older
    # clients also sent a derived ``stats`` object, and it can legitimately
    # be one click behind React state when the user submits immediately after
    # tapping a metric.  Rejecting the whole submission for that transient
    # mismatch was the source of otherwise valid 422 responses.  Rebuild the
    # counters from the normalized events whenever events are present.
    calculation_stats = event_stats if events else (
        _normalise_stats(raw_stats, position) if raw_stats else event_stats
    )

    requires_heatmap = bool(
        raw.get("heatmap", {}).get("required")
        if isinstance(raw.get("heatmap"), dict)
        else raw.get("requiresHeatmap", raw.get("requires_heatmap", False))
    )
    missing_heatmap = [
        event["metric"]
        for event in events
        if event.get("heatmap_required")
        and "location" not in event
    ]
    if requires_heatmap and missing_heatmap:
        raise ValueError(
            "Required heatmap location is missing for: "
            + ", ".join(sorted(set(missing_heatmap)))
        )

    player_id = str(
        raw.get("playerId")
        or raw.get("player_id")
        or raw.get("sourceId")
        or f"slot-{player_order + 1}"
    ).strip()
    jersey_raw = str(raw.get("jerseyNumber") or raw.get("jersey_number") or "").strip()
    jersey_number = int(jersey_raw) if jersey_raw.isdigit() else None
    status = str(
        raw.get("status")
        or ("substituted" if raw.get("subStatus") == "subbed_out" else raw.get("subStatus"))
        or "starting"
    )
    minutes_raw = raw.get(
        "minutesPlayed",
        raw.get("minutes_played", raw.get("minutes")),
    )
    try:
        minutes_played = (
            int(_number(minutes_raw, "player.minutes_played"))
            if minutes_raw not in (None, "")
            else 0
        )
    except (TypeError, ValueError):
        minutes_played = 0
    team_id = raw.get("teamId") or raw.get("team_id")
    team_side = str(
        raw.get("teamSide")
        or raw.get("team_side")
        or raw.get("side")
        or raw.get("matchSide")
        or raw.get("match_side")
        or raw.get("team")
        or ""
    ).strip().lower() or None
    if team_side not in {"home", "away"}:
        team_side = None
    team_name = (
        raw.get("teamName")
        or raw.get("team_name")
        or raw.get("clubName")
        or raw.get("club_name")
        or raw.get("club")
    )
    home_team = raw.get("homeTeam") or raw.get("home_team") or raw.get("homeClub") or raw.get("home_club")
    away_team = raw.get("awayTeam") or raw.get("away_team") or raw.get("awayClub") or raw.get("away_club")
    player_category = (
        raw.get("playerCategory")
        or raw.get("player_category")
        or raw.get("playerLevel")
        or raw.get("player_level")
        or raw.get("category")
        or raw.get("level")
        or None
    )
    assignment_id = str(
        raw.get("assignmentId") or raw.get("assignment_id") or ""
    ).strip() or None
    profile = {
        "player_id": player_id,
        "assignment_id": assignment_id,
        "player_name": str(raw.get("name") or raw.get("playerName") or "").strip(),
        "team_id": team_id,
        "team_side": team_side,
        "team_name": team_name,
        "home_team": home_team,
        "away_team": away_team,
        "position": position,
        "main_position": str(
            raw.get("mainPosition")
            or raw.get("main_position")
            or position
        ).strip(),
        "position_changed": bool(raw.get("positionChanged", raw.get("position_changed", False))),
        "position_options": list(
            raw.get("positionOptions") or raw.get("position_options") or [position]
        ),
        "club": raw.get("club") or raw.get("teamName") or raw.get("team_name"),
        "player_category": player_category,
        "player_level": player_category,
        "jersey_number": jersey_number,
        "status": status,
        "attacking_direction": str(
            raw.get("attackingDirection")
            or raw.get("attacking_direction")
            or "left-to-right"
        ),
        "heatmap_required": requires_heatmap,
        "player_order": player_order,
    }
    # Every atomic action is explicitly linked to its persisted player and
    # position. This prevents an otherwise valid event from becoming orphaned
    # when the client omitted a redundant event-level playerId.
    for event in events:
        event["player_id"] = event.get("player_id") or player_id
        event["assignment_id"] = event.get("assignment_id") or assignment_id
        event["position"] = event.get("position") or position
        if team_id is not None:
            event["team_id"] = team_id
        if team_side:
            event["team_side"] = team_side
        if team_name not in (None, ""):
            event["team_name"] = team_name

    if minutes_raw not in (None, ""):
        profile["minutes_played"] = minutes_played

    participation = raw.get(
        "participationSecondsByPeriod",
        raw.get("participation_seconds_by_period"),
    )
    if participation is not None:
        if not isinstance(participation, list) or len(participation) != 2:
            raise ValueError(
                "player.participationSecondsByPeriod must contain two periods"
            )
        profile["participation_seconds_by_period"] = [
            int(
                _number(
                    value,
                    f"player.participationSecondsByPeriod[{period}]",
                )
            )
            for period, value in enumerate(participation)
        ]
        profile.pop("minutes_played", None)

    try:
        score = float(calculate_performance_score(calculation_stats, position) or 0)
        profile["performance_score"] = score if math.isfinite(score) else 0.0
    except Exception:
        profile["performance_score"] = 0.0

    return profile, events


def _event_identity(raw_event: Any) -> tuple[str, str]:
    if not isinstance(raw_event, dict):
        return "", ""
    event_id = str(
        raw_event.get("eventId")
        or raw_event.get("event_id")
        or raw_event.get("id")
        or raw_event.get("clientEventId")
        or raw_event.get("client_event_id")
        or ""
    ).strip()
    client_event_id = str(
        raw_event.get("clientEventId")
        or raw_event.get("client_event_id")
        or event_id
    ).strip()
    return event_id, client_event_id


def _player_identity(raw_player: Any) -> str:
    if not isinstance(raw_player, dict):
        return ""
    return str(
        raw_player.get("playerId")
        or raw_player.get("player_id")
        or raw_player.get("sourceId")
        or raw_player.get("source_id")
        or ""
    ).strip()


def _merge_widget_actions(raw_players: Any, raw_actions: Any) -> List[Dict[str, Any]]:
    """Build one player/event source of truth from current and legacy payloads.

    Current clients send events under players[].events. Older/aligned clients may
    also send a top-level actions[] journal. The two representations are merged
    by stable event identity and never persisted twice.
    """
    players = [dict(player) for player in raw_players if isinstance(player, dict)]
    actions = raw_actions if isinstance(raw_actions, list) else []
    if not actions:
        return players

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        player_key = _player_identity(action)
        assignment_key = str(
            action.get("assignmentId") or action.get("assignment_id") or ""
        ).strip()
        if player_key:
            buckets.setdefault(f"player:{player_key}", []).append(action)
        if assignment_key:
            buckets.setdefault(f"assignment:{assignment_key}", []).append(action)

    for player in players:
        player_key = _player_identity(player)
        assignment_key = str(
            player.get("assignmentId") or player.get("assignment_id") or ""
        ).strip()
        existing = list(player.get("events") or []) if isinstance(player.get("events"), list) else []
        merged = list(existing)
        seen_event_ids: set[str] = set()
        seen_client_event_ids: set[str] = set()
        for event in existing:
            event_id, client_event_id = _event_identity(event)
            if event_id:
                seen_event_ids.add(event_id)
            if client_event_id:
                seen_client_event_ids.add(client_event_id)

        candidates = []
        if player_key:
            candidates.extend(buckets.get(f"player:{player_key}", []))
        if assignment_key:
            candidates.extend(buckets.get(f"assignment:{assignment_key}", []))
        for action in candidates:
            event_id, client_event_id = _event_identity(action)
            if (
                (event_id and event_id in seen_event_ids)
                or (client_event_id and client_event_id in seen_client_event_ids)
            ):
                continue
            merged.append(dict(action))
            if event_id:
                seen_event_ids.add(event_id)
            if client_event_id:
                seen_client_event_ids.add(client_event_id)
        player["events"] = merged
    return players


def _normalise_widget_players(
    raw_players: Any,
    raw_actions: Any = None,
    max_players: int = 3,
) -> List[tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """Normalize every player once for both draft and final submission paths."""
    if not isinstance(raw_players, list):
        raise ValueError(f"players must contain between 1 and {max_players} players")
    players = _merge_widget_actions(raw_players, raw_actions)
    if not players or len(players) > max_players:
        raise ValueError(f"players must contain between 1 and {max_players} players")

    seen_player_ids: set[str] = set()
    seen_event_ids: set[str] = set()
    seen_client_event_ids: set[str] = set()
    normalized: List[tuple[Dict[str, Any], List[Dict[str, Any]]]] = []

    for order, player in enumerate(players):
        player_id = _player_identity(player)
        if player_id:
            if player_id in seen_player_ids:
                raise ValueError(f"players[{order}].playerId is duplicated")
            seen_player_ids.add(player_id)

        profile, events = _normalise_player(player, order)
        for event_index, event in enumerate(events):
            event_id, client_event_id = _event_identity(event)
            if event_id and event_id in seen_event_ids:
                raise ValueError(f"players[{order}].events[{event_index}].eventId is duplicated")
            if client_event_id and client_event_id in seen_client_event_ids:
                raise ValueError(
                    f"players[{order}].events[{event_index}].clientEventId is duplicated"
                )
            if event_id:
                seen_event_ids.add(event_id)
            if client_event_id:
                seen_client_event_ids.add(client_event_id)

        # Category and level are separate only when they are genuinely different.
        def first_player_value(*keys: str) -> str:
            for key in keys:
                value = player.get(key)
                if value not in (None, ""):
                    text = str(value).strip()
                    if text:
                        return text
            return ""

        category_aliases = {
            "pro": "professional",
            "professional": "professional",
            "professionals": "professional",
            "semi pro": "semi-professional",
            "semi-pro": "semi-professional",
            "semi professional": "semi-professional",
            "semi-professional": "semi-professional",
            "academy": "academy",
            "academies": "academy",
            "youth": "academy",
            "university": "university",
            "universities": "university",
            "varsity": "university",
            "other": "others",
            "others": "others",
        }
        category = first_player_value(
            "playerCategory", "player_category", "category", "matchCategory", "match_category"
        )
        category_key = " ".join(category.lower().replace("_", " ").replace("-", " ").split())
        category = category_aliases.get(category_key, category) if category else ""
        level = first_player_value("playerLevel", "player_level", "level")
        if category and level and category.casefold() != level.casefold():
            profile["player_category"] = category
            profile["player_level"] = level
        elif category or level:
            profile["player_level"] = category or level
            profile.pop("player_category", None)
        else:
            profile.pop("player_category", None)
            profile.pop("player_level", None)

        # Events are the canonical representation. Only a legacy stats-only
        # player receives the compact stats object; never store both copies.
        raw_stats = player.get("stats")
        if not events and isinstance(raw_stats, dict) and raw_stats:
            canonical_stats = _normalise_stats(raw_stats, profile["position"])
            if any(value for value in canonical_stats.values()):
                profile["stats"] = canonical_stats
        else:
            profile.pop("stats", None)

        participation = player.get(
            "participationSecondsByPeriod",
            player.get("participation_seconds_by_period"),
        )
        if participation is not None:
            if not isinstance(participation, list) or len(participation) != 2:
                raise ValueError("player.participationSecondsByPeriod must contain two periods")
            participation_seconds = [
                int(_number(value, f"player[{order}].participationSecondsByPeriod[{period}]") )
                for period, value in enumerate(participation)
            ]
            if any(participation_seconds):
                profile["participation_seconds_by_period"] = participation_seconds
            profile.pop("minutes_played", None)

        normalized.append((profile, events))
    return normalized


def _normalise_club_tracking(
    raw_tracking: Any,
    assignment_id: str = "",
    match_id: str = "",
) -> Optional[Dict[str, Any]]:
    """Validate and canonicalize the club widget's event snapshot."""
    if raw_tracking is None:
        return None
    if not isinstance(raw_tracking, dict):
        raise ValueError("clubTracking must be an object")

    raw_events = raw_tracking.get("events", [])
    if not isinstance(raw_events, list):
        raise ValueError("clubTracking.events must be a list")
    if len(raw_events) > 10000:
        raise ValueError("clubTracking.events cannot exceed 10000 events")

    normalized_events: List[Dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    seen_client_event_ids: set[str] = set()
    for index, raw_event in enumerate(raw_events):
        field = f"clubTracking.events[{index}]"
        if not isinstance(raw_event, dict):
            raise ValueError(f"{field} must be an object")

        team = str(
            raw_event.get("team")
            or raw_event.get("clubTeam")
            or raw_event.get("club_team")
            or raw_event.get("teamSide")
            or raw_event.get("team_side")
            or ""
        ).strip().lower()
        if team not in {"home", "away"}:
            raise ValueError(f"{field}.team must be 'home' or 'away'")

        metric_key = str(
            raw_event.get("key")
            or raw_event.get("metricKey")
            or raw_event.get("metric_key")
            or raw_event.get("metric")
            or ""
        ).strip()
        if not metric_key or len(metric_key) > 100:
            raise ValueError(f"{field}.key must contain 1 to 100 characters")

        event_id = str(
            raw_event.get("eventId")
            or raw_event.get("event_id")
            or raw_event.get("id")
            or raw_event.get("clientEventId")
            or raw_event.get("client_event_id")
            or f"club-event-{index + 1}"
        ).strip()
        client_event_id = str(
            raw_event.get("clientEventId")
            or raw_event.get("client_event_id")
            or event_id
        ).strip()
        if event_id in seen_event_ids:
            raise ValueError(f"{field}.eventId is duplicated")
        if client_event_id in seen_client_event_ids:
            raise ValueError(f"{field}.clientEventId is duplicated")
        seen_event_ids.add(event_id)
        seen_client_event_ids.add(client_event_id)

        period_value = raw_event.get("period", raw_event.get("half", 1))
        period = int(_number(period_value, f"{field}.period"))
        if period not in {1, 2}:
            raise ValueError(f"{field}.period must be 1 or 2")
        period_seconds = int(
            _number(
                raw_event.get(
                    "periodSeconds",
                    raw_event.get("period_seconds", raw_event.get("elapsed_seconds", 0)),
                ),
                f"{field}.periodSeconds",
            )
        )
        match_seconds = int(
            _number(
                raw_event.get(
                    "absoluteMatchTime",
                    raw_event.get(
                        "absolute_match_time",
                        raw_event.get(
                            "matchTime",
                            raw_event.get(
                                "match_time",
                                period_seconds + (45 * 60 if period == 2 else 0),
                            ),
                        ),
                    ),
                ),
                f"{field}.matchTime",
            )
        )

        event = dict(raw_event)
        event.update(
            {
                "event_id": event_id,
                "client_event_id": client_event_id,
                "entity_type": "club",
                "team": team,
                "club_team": team,
                "team_name": (
                    raw_event.get("teamName")
                    or raw_event.get("team_name")
                    or raw_event.get("clubName")
                    or raw_event.get("club_name")
                    or ""
                ),
                "metric_key": metric_key,
                "metric_label": (
                    raw_event.get("metricLabel")
                    or raw_event.get("metric_label")
                    or metric_key.replace("_", " ").title()
                ),
                "outcome": raw_event.get("outcome"),
                "outcome_label": (
                    raw_event.get("outcomeLabel")
                    or raw_event.get("outcome_label")
                    or ""
                ),
                "type": raw_event.get("type"),
                "type_label": raw_event.get("typeLabel") or raw_event.get("type_label") or "",
                "recorded_at": (
                    raw_event.get("recordedAt")
                    or raw_event.get("recorded_at")
                    or raw_event.get("timestamp")
                ),
                "period": period,
                "half": period,
                "period_seconds": period_seconds,
                "elapsed_seconds": period_seconds,
                "match_time": match_seconds,
                "absolute_match_time": match_seconds,
                "assignment_id": str(
                    raw_event.get("assignmentId")
                    or raw_event.get("assignment_id")
                    or assignment_id
                    or ""
                ).strip()
                or None,
                "match_id": str(
                    raw_event.get("matchId")
                    or raw_event.get("match_id")
                    or match_id
                    or ""
                ).strip()
                or None,
            }
        )
        normalized_events.append(event)

    normalized = dict(raw_tracking)
    normalized["events"] = normalized_events
    for key in ("stats", "derived", "redo", "possession"):
        value = normalized.get(key)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"clubTracking.{key} must be an object")
    return normalized


def _club_event_documents(
    parent_field: str,
    parent_id: Any,
    club_tracking: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Create event rows compatible with the existing normalized event collections."""
    if not club_tracking:
        return []
    documents = []
    for order, event in enumerate(club_tracking.get("events", [])):
        row = dict(event)
        row.update(
            {
                "_id": ObjectId(),
                parent_field: parent_id,
                "event_order": order,
                "entity_type": "club",
                "event_type": "club_tracker",
                "team": event["team"],
                "club_team": event["team"],
                "metric": event["metric_key"],
                "metric_key": event["metric_key"],
                "elapsed_seconds": event["period_seconds"],
                "match_time": event["absolute_match_time"],
            }
        )
        documents.append(row)
    return documents


def _normalise_widget_match(payload: BaseModel) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Canonicalize the match once for both draft and final submission."""
    match = _normalise_match(payload) or {}
    raw_match = _payload_value(payload, "match", "matchData", default={})
    if not isinstance(raw_match, dict):
        raw_match = {}
    raw_match_details = raw_match.get("details") if isinstance(raw_match.get("details"), dict) else {}

    def is_missing(value: Any) -> bool:
        return value is None or value == "" or (
            isinstance(value, str)
            and value.strip().lower() in {"-", "—", "null", "undefined", "none", "n/a"}
        )

    def first(*keys: str) -> Any:
        for source in (match, raw_match, raw_match_details):
            for key in keys:
                value = source.get(key)
                if not is_missing(value):
                    return value
        for key in keys:
            value = _payload_value(payload, key, default=None)
            if not is_missing(value):
                return value
        return None

    for canonical, aliases in {
        "home_team_name": ("home_team_name", "homeTeamName", "home_team", "homeTeam", "home_club_name", "homeClubName", "home_club", "homeClub"),
        "away_team_name": ("away_team_name", "awayTeamName", "away_team", "awayTeam", "away_club_name", "awayClubName", "away_club", "awayClub"),
    }.items():
        value = first(*aliases)
        if isinstance(value, dict):
            value = value.get("name") or value.get("team_name") or value.get("club_name")
        if value not in (None, ""):
            match[canonical] = str(value).strip()

    score = first("score")
    home_score = first("home_score", "homeScore", "home_goals", "homeGoals")
    away_score = first("away_score", "awayScore", "away_goals", "awayGoals")
    if isinstance(score, dict):
        if home_score in (None, ""):
            home_score = score.get("home", score.get("home_score"))
        if away_score in (None, ""):
            away_score = score.get("away", score.get("away_score"))
    if home_score not in (None, ""):
        match["home_score"] = home_score
    if away_score not in (None, ""):
        match["away_score"] = away_score

    venue = first("venue", "stadium", "venue_name", "venueName", "stadium_name", "stadiumName")
    if venue not in (None, ""):
        match["venue"] = venue
        if isinstance(venue, dict):
            venue_name = venue.get("name") or venue.get("venue_name") or venue.get("stadium")
            if venue_name not in (None, ""):
                match["venue_name"] = venue_name
        else:
            match["venue_name"] = str(venue).strip()

    for canonical, aliases in {
        "venue_address": ("venue_address", "venueAddress", "stadium_address", "stadiumAddress", "address"),
        "venue_lga": ("venue_lga", "venueLGA", "lga", "local_government_area"),
        "venue_city": ("venue_city", "venueCity", "city"),
        "venue_state": ("venue_state", "venueState", "state"),
        "venue_country": ("venue_country", "venueCountry", "country"),
        "match_date": ("match_date", "matchDate", "date"),
        "match_time": ("match_time", "matchTime", "time"),
        "competition": ("competition", "competition_name", "competitionName", "match_type", "matchType"),
        "result": ("result", "match_result", "matchResult"),
    }.items():
        value = first(*aliases)
        if value not in (None, ""):
            match[canonical] = value

    match_category = first("match_category", "matchCategory", "category")
    player_level = first("player_level", "playerLevel", "level")
    if match_category not in (None, ""):
        match["match_category"] = match_category
    if player_level not in (None, "") and (
        match_category in (None, "")
        or str(player_level).strip().casefold() != str(match_category).strip().casefold()
    ):
        match["player_level"] = player_level

    match = _canonicalise_match_document(match)
    geo = {
        key: value
        for key, value in {
            "status": _payload_value(payload, "geoStatus", "geo_status", default=None),
            "latitude": _payload_value(payload, "geoLat", "geo_lat", default=None),
            "longitude": _payload_value(payload, "geoLon", "geo_lon", default=None),
        }.items()
        if value not in (None, "")
    }
    return match, geo


class AssignmentDecision(BaseModel):
    assignment_id: Optional[str] = None
    assignmentId: Optional[str] = None
    stats_request_id: Optional[str] = None
    statsRequestId: Optional[str] = None
    request_id: Optional[str] = None
    requestId: Optional[str] = None
    reason: Optional[str] = None

    class Config:
        extra = "allow"

    def identifier(self) -> str:
        return (
            self.assignment_id
            or self.assignmentId
            or self.stats_request_id
            or self.statsRequestId
            or self.request_id
            or self.requestId
            or ""
        )


class DraftRequest(BaseModel):
    schemaVersion: Optional[int] = None
    mode: Optional[str] = None
    dcoId: Optional[str] = None
    assignmentId: Optional[str] = None
    supervisorId: Optional[str] = None
    matchId: Optional[str] = None
    match: Optional[Dict[str, Any]] = None
    assignment_id: Optional[str] = None
    match_id: Optional[str] = None
    player_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    players: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    assignmentIds: Optional[List[str]] = None
    clubTracking: Optional[Dict[str, Any]] = None
    club_tracking: Optional[Dict[str, Any]] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None
    homeTeamId: Optional[str] = None
    awayTeamId: Optional[str] = None
    scoreA: Optional[int] = None
    scoreB: Optional[int] = None
    timerSeconds: Optional[int] = None
    half: Optional[Any] = None

    class Config:
        extra = "allow"


class WidgetSubmitRequest(BaseModel):
    schemaVersion: Optional[int] = None
    mode: Optional[str] = None
    dcoId: Optional[str] = None
    assignmentId: Optional[str] = None
    assignmentIds: Optional[List[str]] = None
    clubTracking: Optional[Dict[str, Any]] = None
    club_tracking: Optional[Dict[str, Any]] = None
    supervisorId: Optional[str] = None
    match: Optional[Dict[str, Any]] = None
    assignment_id: Optional[str] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None
    scoreA: Optional[int] = None
    scoreB: Optional[int] = None
    half: Optional[Any] = None
    timerSeconds: Optional[int] = None
    matchTime: Optional[str] = None
    players: Optional[List[Dict[str, Any]]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    homeTeamId: Optional[str] = None
    awayTeamId: Optional[str] = None
    geoStatus: Optional[str] = None
    geoLat: Optional[float] = None
    geoLon: Optional[float] = None
    isResubmit: bool = False
    tracking_type: Optional[str] = None
    submission_trigger: Optional[str] = None
    reason: Optional[str] = None
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    heatmap_data: Optional[Any] = None
    geo_status: Optional[str] = None

    class Config:
        extra = "allow"


async def _ensure_submission_index() -> None:
    """Create the normalized write-path indexes once per process."""
    global _submission_indexes_ready
    if _submission_indexes_ready:
        return
    async with _submission_index_lock:
        if _submission_indexes_ready:
            return
        try:
            await stat_submissions_collection.create_index(
                [("submission_key", 1)],
                unique=True,
                name="uniq_stat_submissions_submission_key",
            )
            await stat_submissions_collection.create_index(
                [("dco_id", 1), ("submitted_at", -1)],
                name="idx_stat_submissions_dco_submitted",
            )
            await stat_submission_players_collection.create_index(
                [("submission_id", 1), ("player_order", 1)],
                unique=True,
                name="uniq_stat_submission_players_order",
            )
            await stat_submission_players_collection.create_index(
                [("submission_id", 1), ("player_id", 1)],
                unique=True,
                name="uniq_stat_submission_players_player",
            )
            await stat_events_collection.create_index(
                [("submission_id", 1), ("event_id", 1)],
                unique=True,
                name="uniq_stat_events_submission_event",
            )
            await stat_events_collection.create_index(
                [("submission_id", 1), ("client_event_id", 1)],
                unique=True,
                name="uniq_stat_events_submission_client_event",
            )
            await stat_events_collection.create_index(
                [("submission_player_id", 1), ("period", 1), ("elapsed_seconds", 1)],
                name="idx_stat_events_player_clock",
            )
            await stat_drafts_collection.create_index(
                [("dco_id", 1), ("assignment_id", 1), ("match_id", 1)],
                unique=True,
                name="uniq_stat_drafts_owner_match",
            )
            await stat_draft_players_collection.create_index(
                [("draft_id", 1), ("player_order", 1)],
                unique=True,
                name="uniq_stat_draft_players_order",
            )
            await stat_draft_players_collection.create_index(
                [("draft_id", 1), ("player_id", 1)],
                unique=True,
                name="uniq_stat_draft_players_player",
            )
            await stat_draft_events_collection.create_index(
                [("draft_id", 1), ("event_id", 1)],
                unique=True,
                name="uniq_stat_draft_events_event",
            )
            await stat_draft_events_collection.create_index(
                [("draft_id", 1), ("client_event_id", 1)],
                unique=True,
                name="uniq_stat_draft_events_client_event",
            )
        except Exception as exc:
            if logger is not None and hasattr(logger, "warning"):
                logger.warning("Could not create normalized stats indexes: %s", exc)
        _submission_indexes_ready = True


def _payload_value(payload: BaseModel, *names: str, default: Any = None) -> Any:
    data = payload.dict(exclude_none=True) if hasattr(payload, "dict") else payload.model_dump(exclude_none=True)
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return default


def _normalise_match(payload: BaseModel) -> Dict[str, Any]:
    raw_match = _payload_value(
        payload,
        "match",
        "matchData",
        default={},
    )
    match = raw_match if isinstance(raw_match, dict) else {}
    details = match.get("details") if isinstance(match.get("details"), dict) else {}
    teams = match.get("teams") if isinstance(match.get("teams"), dict) else {}
    score = match.get("score") if isinstance(match.get("score"), dict) else {}
    clock = match.get("clock") if isinstance(match.get("clock"), dict) else {}
    detail_teams = details.get("teams") if isinstance(details.get("teams"), dict) else {}
    detail_score = details.get("score") if isinstance(details.get("score"), dict) else {}
    detail_clock = details.get("clock") if isinstance(details.get("clock"), dict) else {}

    def pick(*keys: str, default: Any = None) -> Any:
        value = _payload_value(payload, *keys, default=None)
        if value not in (None, ""):
            return value
        for key in keys:
            value = match.get(key)
            if value not in (None, ""):
                return value
        for key in keys:
            value = details.get(key)
            if value not in (None, ""):
                return value
        return default

    raw_venue = (
        match.get("venue")
        if isinstance(match.get("venue"), dict)
        else details.get("venue")
        if isinstance(details.get("venue"), dict)
        else {}
    )
    venue_name = (
        match.get("venue_name")
        or match.get("venueName")
        or match.get("stadium")
        or raw_venue.get("name")
        or raw_venue.get("stadium")
        or pick("venue", "venue_name", "venueName", "stadium", "stadiumName")
    )
    venue_address = (
        match.get("venue_address")
        or match.get("venueAddress")
        or match.get("stadium_address")
        or raw_venue.get("address")
        or raw_venue.get("street")
        or pick("venue_address", "venueAddress", "stadium_address")
    )
    venue_city = (
        match.get("venue_city")
        or match.get("venueCity")
        or match.get("city")
        or raw_venue.get("city")
        or pick("venue_city", "venueCity", "city")
    )
    venue_lga = (
        match.get("venue_lga")
        or match.get("venueLGA")
        or match.get("lga")
        or match.get("local_government_area")
        or raw_venue.get("lga")
        or raw_venue.get("local_government_area")
        or pick("venue_lga", "venueLGA", "lga", "local_government_area")
    )
    venue_province = (
        match.get("venue_province")
        or match.get("venueProvince")
        or match.get("province")
        or raw_venue.get("province")
        or pick("venue_province", "venueProvince", "province")
    )
    venue_county = (
        match.get("venue_county")
        or match.get("venueCounty")
        or match.get("county")
        or raw_venue.get("county")
        or pick("venue_county", "venueCounty", "county")
    )
    venue_state = (
        match.get("venue_state")
        or match.get("venueState")
        or match.get("state")
        or raw_venue.get("state")
        or pick("venue_state", "venueState", "state")
    )
    venue_country = (
        match.get("venue_country")
        or match.get("venueCountry")
        or match.get("country")
        or raw_venue.get("country")
        or pick("venue_country", "venueCountry", "country")
    )

    result = {
        "match_id": str(
            match.get("id")
            or _payload_value(payload, "matchId", "match_id", "assignmentId", "assignment_id", default="")
        ),
        "match_date": pick("match_date", "matchDate", "date"),
        "match_time": pick("match_time", "matchTime", "time"),
        "competition": pick("competition", "league"),
        "match_type": pick("match_type", "matchType", "competition_type"),
        "home_team_name": match.get("homeTeam")
        or match.get("home_team")
        or details.get("homeTeam")
        or details.get("home_team")
        or match.get("homeClub")
        or match.get("home_club")
        or _payload_value(payload, "homeTeam", "home_team", default=None),
        "away_team_name": match.get("awayTeam")
        or match.get("away_team")
        or details.get("awayTeam")
        or details.get("away_team")
        or match.get("awayClub")
        or match.get("away_club")
        or _payload_value(payload, "awayTeam", "away_team", default=None),
        "home_team_id": (
            teams.get("homeId")
            or teams.get("home_id")
            or detail_teams.get("homeId")
            or detail_teams.get("home_id")
            or match.get("homeTeamId")
            or match.get("home_team_id")
        ),
        "away_team_id": (
            teams.get("awayId")
            or teams.get("away_id")
            or detail_teams.get("awayId")
            or detail_teams.get("away_id")
            or match.get("awayTeamId")
            or match.get("away_team_id")
        ),
        "home_score": int(
            score.get(
                "home",
                detail_score.get(
                    "home",
                    match.get(
                        "homeScore",
                        match.get("home_score", _payload_value(payload, "scoreA", default=0)),
                    ),
                ),
            )
            or 0
        ),
        "away_score": int(
            score.get(
                "away",
                detail_score.get(
                    "away",
                    match.get(
                        "awayScore",
                        match.get("away_score", _payload_value(payload, "scoreB", default=0)),
                    ),
                ),
            )
            or 0
        ),
        "period": 2 if int(
            clock.get(
                "period",
                detail_clock.get("period", _payload_value(payload, "half", default=1)),
            )
            or 1
        ) == 2 else 1,
        "elapsed_seconds": max(
            0,
            int(
                clock.get(
                    "elapsedSeconds",
                    clock.get(
                        "elapsed",
                        detail_clock.get(
                            "elapsedSeconds",
                            detail_clock.get(
                                "elapsed",
                                _payload_value(payload, "timerSeconds", default=0),
                            ),
                        ),
                    ),
                )
                or 0
            ),
        ),
        "status": str(match.get("status") or "live"),
        "match_category": pick("match_category", "matchCategory", "category"),
        "player_level": pick("player_level", "playerLevel", "level"),
        "result": pick("result", "match_result", "matchResult"),
        "venue_gps_lat": pick("venue_gps_lat", "venueGpsLat", "gps_lat", "gpsLat"),
        "venue_gps_lon": pick("venue_gps_lon", "venueGpsLon", "gps_lon", "gpsLon"),
    }
    venue = {
        "name": venue_name,
        "address": venue_address,
        "lga": venue_lga,
        "city": venue_city,
        "province": venue_province,
        "county": venue_county,
        "state": venue_state,
        "country": venue_country,
    }
    if any(value not in (None, "") for value in venue.values()):
        result["venue"] = {
            key: value
            for key, value in venue.items()
            if value not in (None, "")
        }
        result["venue_name"] = venue_name
        result["venue_address"] = venue_address
        result["venue_lga"] = venue_lga
        result["venue_city"] = venue_city
        result["venue_province"] = venue_province
        result["venue_county"] = venue_county
        result["venue_state"] = venue_state
        result["venue_country"] = venue_country
    return _canonicalise_match_document({
        key: value
        for key, value in result.items()
        if value is not None and value != ""
    })


def _canonicalise_match_document(raw_match: Any) -> Dict[str, Any]:
    """Keep one stored field for each match/detail value.

    The widget has shipped several camelCase, snake_case, nested, and legacy
    match shapes.  Accept all of them at the boundary, but persist one stable
    shape so the same venue, team, score, or schedule value is never written
    twice under different keys.
    """
    source = raw_match if isinstance(raw_match, dict) else {}
    details = source.get("details") if isinstance(source.get("details"), dict) else {}
    nested_teams = source.get("teams") if isinstance(source.get("teams"), dict) else {}
    nested_score = source.get("score") if isinstance(source.get("score"), dict) else {}
    nested_clock = source.get("clock") if isinstance(source.get("clock"), dict) else {}

    def first(*keys: str, default: Any = None) -> Any:
        for container in (source, details):
            for key in keys:
                value = container.get(key)
                if value not in (None, ""):
                    return value
        return default

    canonical: Dict[str, Any] = {}
    scalar_aliases = {
        "match_id": ("match_id", "matchId", "id"),
        "match_date": ("match_date", "matchDate", "date"),
        "match_time": ("match_time", "matchTime", "time"),
        "competition": ("competition", "league", "competition_name", "competitionName"),
        "match_type": ("match_type", "matchType", "competition_type"),
        "home_team_name": ("home_team_name", "homeTeamName", "home_team", "homeTeam", "homeClub"),
        "away_team_name": ("away_team_name", "awayTeamName", "away_team", "awayTeam", "awayClub"),
        "home_team_id": ("home_team_id", "homeTeamId"),
        "away_team_id": ("away_team_id", "awayTeamId"),
        "status": ("status",),
        "match_category": ("match_category", "matchCategory", "category"),
        "player_level": ("player_level", "playerLevel", "level"),
        "result": ("result", "match_result", "matchResult"),
    }
    for canonical_key, aliases in scalar_aliases.items():
        value = first(*aliases)
        if isinstance(value, dict):
            value = value.get("name") or value.get("team_name") or value.get("club_name")
        if value not in (None, ""):
            canonical[canonical_key] = value

    home_score = (
        nested_score.get("home")
        if nested_score.get("home") not in (None, "")
        else first("home_score", "homeScore", "home_goals", "homeGoals")
    )
    away_score = (
        nested_score.get("away")
        if nested_score.get("away") not in (None, "")
        else first("away_score", "awayScore", "away_goals", "awayGoals")
    )
    if home_score not in (None, ""):
        canonical["home_score"] = int(home_score)
    if away_score not in (None, ""):
        canonical["away_score"] = int(away_score)

    period = nested_clock.get("period", nested_clock.get("half", first("period", "half", default=1)))
    elapsed = nested_clock.get(
        "elapsedSeconds",
        nested_clock.get("elapsed", first("elapsed_seconds", "elapsedSeconds", "timerSeconds", default=0)),
    )
    canonical["period"] = 2 if int(period or 1) == 2 else 1
    canonical["elapsed_seconds"] = max(0, int(elapsed or 0))

    venue_source = source.get("venue") if isinstance(source.get("venue"), dict) else {}
    detail_venue = details.get("venue") if isinstance(details.get("venue"), dict) else {}
    venue_containers = (venue_source, detail_venue, source, details)
    venue: Dict[str, Any] = {}
    venue_aliases = {
        "name": ("name", "venue_name", "venueName", "stadium", "stadium_name", "stadiumName"),
        "address": ("address", "venue_address", "venueAddress", "stadium_address", "stadiumAddress"),
        "lga": ("lga", "venue_lga", "venueLGA", "local_government_area"),
        "city": ("city", "venue_city", "venueCity"),
        "province": ("province", "venue_province", "venueProvince"),
        "county": ("county", "venue_county", "venueCounty"),
        "state": ("state", "venue_state", "venueState"),
        "country": ("country", "venue_country", "venueCountry"),
        "gps_lat": ("gps_lat", "gpsLat", "venue_gps_lat", "venueGpsLat", "latitude"),
        "gps_lon": ("gps_lon", "gpsLon", "venue_gps_lon", "venueGpsLon", "longitude"),
    }
    for canonical_key, aliases in venue_aliases.items():
        for container in venue_containers:
            value = next(
                (container[key] for key in aliases if container.get(key) not in (None, "")),
                None,
            )
            if value not in (None, ""):
                venue[canonical_key] = value
                break
    if isinstance(source.get("venue"), str) and "name" not in venue:
        venue["name"] = source["venue"].strip()
    if venue:
        canonical["venue"] = venue

    return canonical


async def _run_atomic(operation):
    """Use a Mongo transaction when the configured client supports sessions."""
    client = getattr(_database, "client", None)
    if client is None or not hasattr(client, "start_session"):
        return await operation(None)
    session = await client.start_session()
    try:
        async with session.start_transaction():
            return await operation(session)
    finally:
        await session.end_session()


def _session_kwargs(session: Any) -> Dict[str, Any]:
    return {"session": session} if session is not None else {}


_FINGERPRINT_ALIASES = {
    "assignmentId": "assignment_id",
    "assignmentIds": "assignment_ids",
    "clubTracking": "club_tracking",
    "supervisorId": "supervisor_id",
    "trackingType": "tracking_type",
    "submissionTrigger": "submission_trigger",
    "isResubmit": "is_resubmit",
    "matchId": "match_id",
    "playerId": "player_id",
    "sourceId": "player_id",
    "source_id": "player_id",
    "clientEventId": "client_event_id",
    "eventId": "event_id",
    "metricKey": "metric",
    "metric_key": "metric",
    "valueType": "value_type",
    "subKey": "sub_key",
    "eventType": "event_type",
    "event_type": "event_type",
    "recordedAt": "recorded_at",
    "heatmapRequired": "heatmap_required",
    "heatmapRecorded": "heatmap_recorded",
    "positionChanged": "position_changed",
    "mainPosition": "main_position",
    "jerseyNumber": "jersey_number",
    "playerCategory": "player_category",
    "playerLevel": "player_level",
    "participationSecondsByPeriod": "participation_seconds_by_period",
    "periodSeconds": "period_seconds",
    "absoluteMatchTime": "absolute_match_time",
    "teamName": "team_name",
    "metricLabel": "metric_label",
    "oppositionTeam": "opposition_team",
    "geoStatus": "geo_status",
    "geoLat": "geo_lat",
    "geoLon": "geo_lon",
}


def _canonicalise_fingerprint_value(value: Any) -> Any:
    """Normalize duplicate client naming conventions before hashing a retry."""
    if isinstance(value, list):
        return [_canonicalise_fingerprint_value(item) for item in value]
    if not isinstance(value, dict):
        return value

    normalized: Dict[str, Any] = {}
    keys = sorted(
        value,
        key=lambda key: (
            0 if key == _FINGERPRINT_ALIASES.get(key, key) else 1,
            str(key),
        ),
    )
    for key in keys:
        canonical_key = _FINGERPRINT_ALIASES.get(key, key)
        if canonical_key in normalized:
            continue
        normalized[canonical_key] = _canonicalise_fingerprint_value(value[key])
    return normalized


def _first_data_value(
    data: Dict[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def _canonical_submission_body(payload: WidgetSubmitRequest) -> Dict[str, Any]:
    data = payload.dict(exclude_none=True) if hasattr(payload, "dict") else payload.model_dump(exclude_none=True)
    raw_players = data.get("players")
    if raw_players is None:
        raw_players = [{
            "player_id": data.get("player_id") or "legacy-player",
            "name": data.get("player_name") or "",
            "position": data.get("position") or "",
            "stats": data.get("stats") or {},
            "events": data.get("events") or [],
        }]
    canonical_players = _canonicalise_fingerprint_value(raw_players)
    unique_players = []
    seen_player_ids: set[str] = set()
    for player in canonical_players:
        if not isinstance(player, dict):
            unique_players.append(player)
            continue
        player_id = str(player.get("player_id") or "").strip()
        if player_id and player_id in seen_player_ids:
            continue
        if player_id:
            seen_player_ids.add(player_id)
        events = player.get("events")
        if isinstance(events, list):
            unique_events = []
            seen_event_ids: set[str] = set()
            seen_client_event_ids: set[str] = set()
            for event in events:
                if not isinstance(event, dict):
                    unique_events.append(event)
                    continue
                event_id = str(event.get("event_id") or "").strip()
                client_event_id = str(
                    event.get("client_event_id") or event_id
                ).strip()
                if (
                    (event_id and event_id in seen_event_ids)
                    or (
                        client_event_id
                        and client_event_id in seen_client_event_ids
                    )
                ):
                    continue
                if event_id:
                    seen_event_ids.add(event_id)
                if client_event_id:
                    seen_client_event_ids.add(client_event_id)
                unique_events.append(event)
            player = dict(player)
            player["events"] = unique_events
        unique_players.append(player)
    return _canonicalise_fingerprint_value({
        "schema_version": _first_data_value(
            data,
            "schemaVersion",
            "schema_version",
        ),
        "mode": data.get("mode"),
        "assignment_id": _first_data_value(
            data,
            "assignmentId",
            "assignment_id",
        ),
        "assignment_ids": list(dict.fromkeys(
            str(value).strip()
            for value in _first_data_value(
                data,
                "assignmentIds",
                "assignment_ids",
                default=[],
            )
            if value not in (None, "")
        )),
        "supervisor_id": _first_data_value(
            data,
            "supervisorId",
            "supervisor_id",
        ),
        "tracking_type": _first_data_value(
            data,
            "tracking_type",
            "trackingType",
            default="full",
        ),
        "submission_trigger": _first_data_value(
            data,
            "submission_trigger",
            "submissionTrigger",
            default="individual",
        ),
        "is_resubmit": _first_data_value(
            data,
            "isResubmit",
            "is_resubmit",
            default=False,
        ),
        "reason": data.get("reason"),
        "match": _canonicalise_match_document(_normalise_match(payload)),
        "players": unique_players,
        "club_tracking": _canonicalise_fingerprint_value(
            _first_data_value(data, "clubTracking", "club_tracking")
        ),
        "geo": {
            "status": _first_data_value(data, "geoStatus", "geo_status"),
            "latitude": _first_data_value(data, "geoLat", "geo_lat"),
            "longitude": _first_data_value(data, "geoLon", "geo_lon"),
        },
    })


def _submission_key(identifier: str, request: Request, payload: WidgetSubmitRequest) -> str:
    header_value = request.headers.get("X-Widget-Submission-Id", "").strip()
    if header_value:
        if len(header_value) > 200:
            raise HTTPException(status_code=400, detail="X-Widget-Submission-Id is too long")
        return f"widget:{identifier}:{header_value}"

    # The supplied HTML sends the header. This deterministic fallback keeps a
    # retried request idempotent even when an older client does not.
    try:
        body = _canonical_submission_body(payload)
    except (TypeError, ValueError, OverflowError):
        body = payload.dict() if hasattr(payload, "dict") else payload.model_dump()
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"widget:{identifier}:body:{digest}"


def _submission_result_response(record: dict, submission_key: str) -> JSONResponse:
    return JSONResponse(
        {
            "success": True,
            "message": record.get("response_message") or (
                "Stats submitted successfully! Awaiting supervisor approval."
                if record.get("supervisor_id")
                else "Stats submitted and published successfully!"
            ),
            "status": record.get("status"),
            "record_id": str(record.get("_id", "")),
            "player_count": int(record.get("player_count") or 0),
            "club_event_count": int(record.get("club_event_count") or 0),
            "performance_score": float(record.get("performance_score") or 0),
            "submission_id": record.get("client_submission_id") or submission_key.rsplit(":", 1)[-1],
            "duplicate": bool(record.get("_idempotent_replay", False)),
        }
    )


async def _current_tracker_user(request: Request) -> dict:
    return await get_dco_user(request)


async def _enriched_assignments(identifier: str) -> List[Dict[str, Any]]:
    rows = await dco_assignments_collection.find(
        {"$or": [{"assigned_dco_id": identifier}, {"assignee_id": identifier}, {"dco_id": identifier}]}
    ).sort("created_at", -1).limit(200).to_list(length=200)
    result: List[Dict[str, Any]] = []
    for assignment in rows:
        item = _serialize(assignment)
        request_id = item.get("stats_request_id") or item.get("request_id") or ""
        request_doc = {}
        if request_id:
            if ObjectId.is_valid(str(request_id)):
                request_doc = await stats_requests_collection.find_one({"_id": ObjectId(str(request_id))}) or {}
            if not request_doc:
                request_doc = await stats_requests_collection.find_one({"request_id": request_id}) or {}
        request_item = _serialize(request_doc)
        player_id = item.get("player_id") or request_item.get("player_id") or ""
        player_doc = {}
        if player_id:
            player_doc = await players_collection.find_one(
                {"$or": [{"player_id": player_id}, {"user_id": player_id}]}
            ) or {}
        player = _serialize(player_doc)

        def pick(*keys: str, default: Any = "") -> Any:
            for source in (request_item, item):
                for key in keys:
                    if source.get(key) not in (None, ""):
                        return source[key]
            return default

        entity_type = str(
            pick("entity_type", "entityType", "requester_type",
                 "request_type", "requestType", default="")
        ).strip().lower()
        if entity_type not in {"club", "player"}:
            entity_type = "player" if player_id else "club"
        club_name = pick("club_name", "club", "team_name", "teamName")
        assignment_id = item.get("assignment_id") or item.get("_id") or ""
        result.append(
            {
                "id": assignment_id,
                "assignmentId": assignment_id,
                "_id": item.get("_id", ""),
                "reference_id": pick("reference_id", "request_id"),
                "playerName": pick("player_name", "playerName") or player.get("full_name") or " ".join(
                    str(player.get(key, "")) for key in ("firstName", "middleName", "lastName")
                ).strip() if entity_type == "player" else "",
                "position": pick("position") or player.get("position") or player.get("preferredPosition", ""),
                "jerseyNumber": pick("jersey_number", "jerseyNumber"),
                "club": club_name or player.get("club", ""),
                "clubName": club_name,
                "clubId": pick("club_id", "clubId"),
                "entityType": entity_type,
                "requestType": entity_type,
                "trackingType": pick("tracking_type", "trackingType", default="no_tracking"),
                "matchCategory": pick("category", "player_level", "match_category", "level"),
                "playerLevel": pick("category", "player_level", "match_category", "level") or player.get("category", ""),
                "matchType": pick("match_type", "matchType", "competition_type"),
                "competition": pick("competition", "league"),
                "matchDate": pick("match_date", "matchDate"),
                "matchTime": pick("match_time", "matchTime"),
                "venue": pick("venue", "stadium", "venue_name", "state"),
                "venueStadium": pick("venue", "stadium", "venue_name"),
                "venueAddress": pick("venue_address", "venueAddress", "stadium_address"),
                "venueLGA": pick("venue_lga", "lga"),
                "venueCountry": pick("venue_country", "country", default="Nigeria"),
                "venueState": pick("venue_state", "state"),
                "homeTeam": pick("home_team", "homeTeam"),
                "awayTeam": pick("away_team", "awayTeam"),
                "homeClub": pick("home_club", "homeClub"),
                "awayClub": pick("away_club", "awayClub"),
                "heatmap": pick("heatmap", default=None),
                "contactPhone": pick("contact_phone", "contactPhone", "phone"),
                "supervisorId": item.get("assigned_supervisor_id", ""),
                "requestedBy": pick("requested_by", "club_id"),
                "submittedAt": pick("submitted_at", "created_at"),
                "assignedDate": item.get("created_at") or item.get("updated_at", ""),
                "notes": item.get("notes", ""),
                "status": item.get("status", "assigned"),
                "stats_request_id": request_id,
                "player_id": player_id,
                "parent_request_id": pick("parent_request_id", "parentRequestId"),
            }
        )
    return result


@router.get("/api/dco/assignments")
async def tracker_assignments(request: Request):
    """
    Return all assignments for the authenticated DCO.

    Data precedence:
    1. Live stats-request data
    2. Assignment snapshot data
    3. Player and club collection data
    """

    current_user = await _current_tracker_user(request)
    identifier = _dco_id(current_user)

    if not identifier:
        return JSONResponse(
            {"assignments": [], "detail": "Authenticated DCO identifier not found"},
            status_code=401,
        )

    def coerce_heatmap(value):
        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        normalized = str(value).strip().lower()

        if normalized in {"true", "1", "yes", "on", "enabled"}:
            return True

        if normalized in {"false", "0", "no", "off", "disabled"}:
            return False

        return None

    def pick(
        live_doc: Dict[str, Any],
        snapshot_doc: Dict[str, Any],
        live_keys,
        snapshot_keys=None,
        default="",
    ):
        """
        Select the first available value from the live document,
        then fall back to the assignment snapshot.
        """

        live_key_list = (
            list(live_keys)
            if isinstance(live_keys, (list, tuple))
            else [live_keys]
        )

        snapshot_key_list = (
            list(snapshot_keys)
            if isinstance(snapshot_keys, (list, tuple))
            else [snapshot_keys or live_key_list[0]]
        )

        for key in live_key_list:
            value = live_doc.get(key)
            if value is not None and value != "":
                return value

        for key in snapshot_key_list:
            value = snapshot_doc.get(key)
            if value is not None and value != "":
                return value

        return default

    owner_filter = {
        "$or": [
            {"assigned_dco_id": identifier},
            {"assignedDcoId": identifier},
            {"assigned_scout_id": identifier},
            {"assignedScoutId": identifier},
            {"assignee_id": identifier},
            {"assigneeId": identifier},
            {"dco_id": identifier},
            {"dcoId": identifier},
            {"data_scout_id": identifier},
            {"dataScoutId": identifier},
        ]
    }

    raw_assignments: List[Dict[str, Any]] = []
    if dco_assignments_collection is not None:
        cursor = (
            dco_assignments_collection.find(owner_filter)
            .sort("created_at", -1)
            .limit(200)
        )
        raw_assignments = await cursor.to_list(length=200)

    # Match Centre may persist the DCO assignment on the stats request
    # without creating a separate dco_assignments record. Include those
    # request documents as virtual assignments for the same DCO dashboard.
    linked_request_ids = {
        str(row.get("stats_request_id") or row.get("request_id") or "").strip()
        for row in raw_assignments
        if row.get("stats_request_id") or row.get("request_id")
    }
    if stats_requests_collection is not None:
        request_cursor = (
            stats_requests_collection.find(owner_filter)
            .sort("created_at", -1)
            .limit(200)
        )
        owned_requests = await request_cursor.to_list(length=200)
        for request_doc in owned_requests:
            request_snapshot = _serialize(request_doc)
            request_id = str(
                request_snapshot.get("request_id")
                or request_snapshot.get("_id")
                or ""
            ).strip()
            if not request_id or request_id in linked_request_ids:
                continue
            linked_request_ids.add(request_id)
            raw_assignments.append(
                {
                    "assignment_id": request_snapshot.get("assignment_id")
                    or request_id,
                    "stats_request_id": request_id,
                    "request_id": request_id,
                    "assigned_dco_id": (
                        request_snapshot.get("assigned_dco_id")
                        or request_snapshot.get("assigned_scout_id")
                        or request_snapshot.get("dco_id")
                        or identifier
                    ),
                    "assigned_supervisor_id": request_snapshot.get(
                        "assigned_supervisor_id"
                    )
                    or request_snapshot.get("supervisor_id")
                    or "",
                    "status": request_snapshot.get("status") or "assigned",
                    "created_at": request_snapshot.get("assigned_at")
                    or request_snapshot.get("created_at")
                    or request_snapshot.get("submitted_at"),
                    "updated_at": request_snapshot.get("updated_at"),
                    "notes": request_snapshot.get("notes")
                    or request_snapshot.get("additional_notes")
                    or "",
                    "_linked_stats_request": request_doc,
                }
            )

    raw_assignments = raw_assignments[:400]

    enriched: List[Dict[str, Any]] = []

    for assignment in raw_assignments:
        assignment_snapshot = _serialize(assignment)

        # Retrieve the latest linked stats request.
        stats_request: Dict[str, Any] | None = assignment.get(
            "_linked_stats_request"
        )
        stats_request_snapshot: Dict[str, Any] = {}

        stats_request_id = (
            assignment_snapshot.get("stats_request_id")
            or assignment_snapshot.get("request_id")
            or ""
        )

        if stats_request:
            stats_request_snapshot = _serialize(stats_request)
        elif stats_request_id:
            if len(str(stats_request_id)) == 24:
                try:
                    from bson import ObjectId

                    stats_request = await stats_requests_collection.find_one(
                        {"_id": ObjectId(str(stats_request_id))}
                    )
                except Exception:
                    stats_request = None

            if not stats_request:
                stats_request = await stats_requests_collection.find_one(
                    {
                        "$or": [
                            {"request_id": stats_request_id},
                            {"_id": stats_request_id},
                        ]
                    }
                )

            if stats_request:
                stats_request_snapshot = _serialize(stats_request)

        # Retrieve the linked player document.
        player_snapshot: Dict[str, Any] = {}

        player_id = (
            assignment_snapshot.get("player_id")
            or assignment_snapshot.get("playerId")
            or stats_request_snapshot.get("player_id")
            or stats_request_snapshot.get("playerId")
            or ""
        )

        if player_id and players_collection is not None:
            try:
                player_doc = await players_collection.find_one(
                    {
                        "$or": [
                            {"player_id": player_id},
                    {"playerId": player_id},
                            {"user_id": player_id},
                        ]
                    }
                )

                if player_doc:
                    player_snapshot = _serialize(player_doc)

            except Exception:
                player_snapshot = {}

        # Resolve the club or venue document.
        club_snapshot: Dict[str, Any] = {}

        club_name = (
            pick(
                stats_request_snapshot,
                assignment_snapshot,
                ["club", "club_name"],
                ["club", "club_name"],
                "",
            )
            or player_snapshot.get("club")
            or ""
        )

        club_name = str(club_name).strip()

        if club_name and clubs_collection is not None:
            try:
                club_pattern = re.escape(club_name)

                club_doc = await clubs_collection.find_one(
                    {
                        "$or": [
                            {
                                "club_name": {
                                    "$regex": f"^{club_pattern}$",
                                    "$options": "i",
                                }
                            },
                            {"club_id": club_name},
                            {"clubId": club_name},
                        ]
                    }
                )

                if club_doc:
                    club_snapshot = _serialize(club_doc)

            except Exception:
                club_snapshot = {}

        assignment_id = (
            assignment_snapshot.get("assignment_id")
            or assignment_snapshot.get("_id")
            or ""
        )

        venue_name = pick(
            stats_request_snapshot,
            assignment_snapshot,
            ["venue", "stadium", "venue_name", "venue_state", "state"],
            ["venue", "stadium", "venue_name", "venue_state", "state"],
            "",
        )

        match_category = pick(
            stats_request_snapshot,
            assignment_snapshot,
            ["category", "player_level", "match_category", "level"],
            ["category", "player_level", "match_category", "level"],
            "",
        )

        raw_heatmap = stats_request_snapshot.get("heatmap")

        if raw_heatmap is None:
            raw_heatmap = assignment_snapshot.get("heatmap")

        heatmap_flag = coerce_heatmap(raw_heatmap)

        player_name = (
            pick(
                stats_request_snapshot,
                assignment_snapshot,
                ["player_name", "playerName"],
                ["player_name", "playerName"],
                "",
            )
            or player_snapshot.get("full_name")
            or " ".join(
                filter(
                    None,
                    [
                        player_snapshot.get("firstName")
                        or player_snapshot.get("first_name")
                        or "",
                        player_snapshot.get("middleName")
                        or player_snapshot.get("middle_name")
                        or "",
                        player_snapshot.get("lastName")
                        or player_snapshot.get("last_name")
                        or "",
                    ],
                )
            ).strip()
        )

        venue_address = (
            club_snapshot.get("address")
            or club_snapshot.get("city")
            or pick(
                stats_request_snapshot,
                assignment_snapshot,
                ["venue_address", "venueAddress", "stadium_address"],
                ["venue_address", "venueAddress", "stadium_address"],
                "",
            )
        )

        request_notes = pick(
            stats_request_snapshot,
            assignment_snapshot,
            ["request_notes", "requestNotes", "notes"],
            default="",
        )
        request_additional_notes = pick(
            stats_request_snapshot,
            assignment_snapshot,
            [
                "request_additional_notes",
                "additional_notes",
                "additionalNotes",
            ],
            default="",
        )
        assignment_notes = (
            assignment_snapshot.get("assignment_notes")
            or assignment_snapshot.get("notes")
            or ""
        )
        note_sections = []
        if request_notes:
            note_sections.append(f"Request: {request_notes}")
        if (
            request_additional_notes
            and request_additional_notes not in {request_notes, assignment_notes}
        ):
            note_sections.append(
                f"Additional request details: {request_additional_notes}"
            )
        if assignment_notes and assignment_notes != request_notes:
            note_sections.append(f"Assignment: {assignment_notes}")
        display_notes = "\n".join(note_sections)
        requested_by_name = (
            stats_request_snapshot.get("requested_by_name")
            or stats_request_snapshot.get("requestedByName")
            or assignment_snapshot.get("requested_by_name")
            or assignment_snapshot.get("requestedByName")
            or ""
        )
        requested_by_id = (
            stats_request_snapshot.get("requested_by")
            or assignment_snapshot.get("requested_by")
            or ""
        )

        raw_entity_type = str(
            pick(
                stats_request_snapshot,
                assignment_snapshot,
                [
                    "entity_type",
                    "entityType",
                    "requester_type",
                    "request_type",
                    "requestType",
                    "tracking_type",
                    "trackingType",
                    "stats_type",
                    "scope",
                ],
                default="",
            )
            or ""
        ).strip().lower()
        if raw_entity_type.startswith("club") or raw_entity_type in {
            "team",
            "club_request",
        }:
            entity_type = "club"
        elif raw_entity_type.startswith("player"):
            entity_type = "player"
        else:
            has_club_identity = bool(
                pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_id", "clubId", "club_name", "clubName", "club"],
                    default="",
                )
            )
            has_player_identity = bool(
                player_id
                or pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["player_name", "playerName"],
                    default="",
                )
            )
            entity_type = (
                "club"
                if has_club_identity and not has_player_identity
                else "player"
            )

        enriched.append(
            {
                # Identity
                "id": assignment_id,
                "assignmentId": assignment_id,
                "assignment_id": assignment_id,
                "_id": assignment_snapshot.get("_id") or "",
                "reference_id": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["reference_id", "request_id"],
                    ["reference_id", "request_id"],
                    "",
                ),

                # Player information
                "playerName": player_name,
                "player_name": player_name,
                "playerId": player_id,
                "position": (
                    pick(
                        stats_request_snapshot,
                        assignment_snapshot,
                        ["position"],
                        ["position"],
                        "",
                    )
                    or player_snapshot.get("position")
                    or player_snapshot.get("preferredPosition")
                    or player_snapshot.get("preferred_position")
                    or ""
                ),
                "jerseyNumber": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["jersey_number", "jerseyNumber"],
                ),
                "club": (
                    pick(
                        stats_request_snapshot,
                        assignment_snapshot,
                        ["club", "club_name"],
                        ["club", "club_name"],
                        "",
                    )
                    or player_snapshot.get("club")
                    or ""
                ),
                "clubName": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_name", "clubName", "club"],
                    default="",
                ),
                "club_name": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_name", "clubName", "club"],
                    default="",
                ),
                "clubId": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_id", "clubId"],
                    default="",
                ),
                "club_id": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_id", "clubId"],
                    default="",
                ),
                "clubRole": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_role", "clubRole"],
                    default="",
                ),
                "club_role": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["club_role", "clubRole"],
                    default="",
                ),
                "jerseyColor": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["jersey_color", "jerseyColor"],
                    default="",
                ),
                "jersey_color": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["jersey_color", "jerseyColor"],
                    default="",
                ),
                "entityType": entity_type,
                "entity_type": entity_type,
                "requestType": entity_type,
                "request_type": entity_type,
                "playerRepresents": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["player_represents", "playerRepresents", "represents"],
                ),

                # Match information
                "matchCategory": match_category,
                "playerLevel": (
                    match_category
                    or player_snapshot.get("category")
                    or player_snapshot.get("player_level")
                    or ""
                ),
                "matchType": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["match_type", "matchType", "competition_type"],
                ),
                "competition": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["competition", "league"],
                ),

                # Scheduling
                "matchDate": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["match_date", "matchDate"],
                ),
                "matchTime": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["match_time", "matchTime"],
                ),

                # Venue
                "venue": club_snapshot.get("stadium") or venue_name,
                "venueStadium": club_snapshot.get("stadium") or venue_name,
                "venueAddress": venue_address,
                "stadiumAddress": venue_address,
                "venueLGA": club_snapshot.get("lga")
                or pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["venue_lga", "lga"],
                ),
                "venueCountry": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["venue_country", "country"],
                    default="Nigeria",
                ),
                "venueState": club_snapshot.get("state")
                or pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["venue_state", "state"],
                ),
                "venueGpsLat": club_snapshot.get("gps_lat")
                or club_snapshot.get("latitude")
                or "",
                "venueGpsLon": club_snapshot.get("gps_lon")
                or club_snapshot.get("longitude")
                or "",

                # Teams
                "homeTeam": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["home_team", "homeTeam"],
                ),
                "awayTeam": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["away_team", "awayTeam"],
                ),
                "homeClub": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["home_club", "homeClub"],
                ),
                "awayClub": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["away_club", "awayClub"],
                ),

                # Heatmap
                # True  = heatmap enabled
                # False = heatmap disabled
                # None  = allow frontend default behavior
                "heatmap": heatmap_flag,

                # Contact and metadata
                "contactPhone": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["contact_phone", "contactPhone", "phone"],
                ),
                "supervisorId": assignment_snapshot.get(
                    "assigned_supervisor_id",
                    "",
                ),
                "requestedBy": pick(
                    {"requested_by_name": requested_by_name},
                    assignment_snapshot,
                    ["requested_by_name"],
                    ["requested_by_name", "requestedByName", "requested_by", "club_id"],
                    requested_by_id,
                ) or requested_by_id,
                "requestedById": requested_by_id,
                "requested_by_name": pick(
                    {"requested_by_name": requested_by_name},
                    assignment_snapshot,
                    ["requested_by_name"],
                    ["requested_by_name", "requestedByName"],
                    "",
                ),
                "submittedAt": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["submitted_at", "created_at"],
                ),
                "assignedDate": (
                    assignment_snapshot.get("created_at")
                    or assignment_snapshot.get("updated_at")
                    or ""
                ),
                "notes": display_notes,
                "requestNotes": request_notes,
                "request_notes": request_notes,
                "requestAdditionalNotes": request_additional_notes,
                "request_additional_notes": request_additional_notes,
                "assignmentNotes": assignment_notes,
                "assignment_notes": assignment_notes,

                # Assignment status
                "status": (
                    assignment_snapshot.get("status")
                    or stats_request_snapshot.get("status")
                    or stats_request_snapshot.get("assignment_status")
                    or stats_request_snapshot.get("acceptance_status")
                    or assignment_snapshot.get("assignment_status")
                    or assignment_snapshot.get("acceptance_status")
                    or "assigned"
                ),

                # Linking fields
                "stats_request_id": stats_request_id,
                "player_id": pick(
                    stats_request_snapshot,
                    assignment_snapshot,
                    ["player_id"],
                    ["player_id"],
                    "",
                ),
                # Preserve request-specific fields so frontend normalization
                # can display all request details, not only this route's
                # flattened aliases.
                "stats_request": stats_request_snapshot,
            }
        )

    return JSONResponse({"assignments": enriched})

@router.get("/api/dco/metrics")
async def dco_metrics(request: Request):
    """
    Combined DCO metrics endpoint.

    Preserves the functionality of the previous /api/dco/metrics
    implementations while exposing one canonical response.

    Response fields:
        assigned_players
        stats_total
        stats_today
        pending_validation
        token_balance
        bio_updates_total
        bio_updates_today
    """

    # ------------------------------------------------------------
    # Authenticate current DCO
    # ------------------------------------------------------------
    user = await get_dco_user(request)
    identifier = _dco_id(user)

    # ------------------------------------------------------------
    # Start of current UTC day
    # ------------------------------------------------------------
    now = MongoSerializer.now_utc()
    day_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    # ------------------------------------------------------------
    # ASSIGNED PLAYERS
    #
    # Supports all legacy assignment ownership fields:
    #   assigned_dco_id
    #   assignee_id
    #   dco_id
    #
    # Only currently active assignments are counted.
    #
    # This deliberately excludes "declined", matching the first
    # implementation while also respecting the active-state logic
    # from the second implementation.
    # ------------------------------------------------------------
    assignment_filter = {
        "$and": [
            {
                "$or": [
                    {"assigned_dco_id": identifier},
                    {"assignee_id": identifier},
                    {"dco_id": identifier},
                ]
            },
            {
                "status": {
                    "$in": [
                        "active",
                        "assigned",
                        "in_progress",
                    ]
                }
            },
            {
                "status": {
                    "$ne": "declined",
                }
            },
        ]
    }

    # ------------------------------------------------------------
    # PLAYER STATS
    # ------------------------------------------------------------
    stats_total_filter = {
        "dco_id": identifier,
    }

    stats_today_filter = {
        "dco_id": identifier,
        "submitted_at": {
            "$gte": day_start,
        },
    }

    # ------------------------------------------------------------
    # PENDING VALIDATION
    #
    # Supports both status conventions used by the existing code:
    #   submitted
    #   pending_validation
    #   pending_approval
    # ------------------------------------------------------------
    pending_filter = {
        "dco_id": identifier,
        "status": {
            "$in": [
                "submitted",
                "pending_validation",
                "pending_approval",
            ]
        },
    }

    # ------------------------------------------------------------
    # BIO / ACTIVITY HISTORY
    # ------------------------------------------------------------
    bio_updates_filter = {
        "actor_id": identifier,
        "type": {
            "$in": [
                "bio_update",
                "bio_updated",
            ]
        },
    }

    bio_updates_today_filter = {
        **bio_updates_filter,
        "created_at": {
            "$gte": day_start,
        },
    }

    # ------------------------------------------------------------
    # Run independent database operations concurrently.
    #
    # This is preferable to awaiting every count one after another.
    # ------------------------------------------------------------
    import asyncio

    (
        assigned_players,
        stats_total,
        stats_today,
        pending_validation,
        bio_updates_total,
        bio_updates_today,
        token_balance,
    ) = await asyncio.gather(
        dco_assignments_collection.count_documents(
            assignment_filter
        ),
        stat_submissions_collection.count_documents(
            stats_total_filter
        ),
        stat_submissions_collection.count_documents(
            stats_today_filter
        ),
        stat_submissions_collection.count_documents(
            pending_filter
        ),
        activity_history_collection.count_documents(
            bio_updates_filter
        ),
        activity_history_collection.count_documents(
            bio_updates_today_filter
        ),
        _token_balance(identifier),
    )

    # ------------------------------------------------------------
    # Combined response
    # ------------------------------------------------------------
    return JSONResponse(
        {
            "assigned_players": int(assigned_players),
            "stats_total": int(stats_total),
            "stats_today": int(stats_today),
            "pending_validation": int(pending_validation),
            "token_balance": token_balance,
            "bio_updates_total": int(bio_updates_total),
            "bio_updates_today": int(bio_updates_today),
        }
    )

@router.get("/api/dco/submissions")
async def tracker_submissions(request: Request):
    identifier = _dco_id(await _current_tracker_user(request))
    rows = await stat_submissions_collection.find(
        {"dco_id": identifier}
    ).sort("submitted_at", -1).limit(200).to_list(length=200)
    return JSONResponse({"submissions": _serialize(rows)})


async def _update_owned_assignment_or_request(
    identifier: str,
    assignment_id: str,
    values: Dict[str, Any],
    session: Any = None,
) -> bool:
    """Update either a materialized assignment or a Match Centre request row."""
    assignment_owner_filter = {
        "$or": [
            {"assigned_dco_id": identifier},
            {"assignedDcoId": identifier},
            {"assigned_scout_id": identifier},
            {"assignedScoutId": identifier},
            {"assignee_id": identifier},
            {"assigneeId": identifier},
            {"dco_id": identifier},
            {"dcoId": identifier},
            {"data_scout_id": identifier},
            {"dataScoutId": identifier},
        ]
    }
    object_id = ObjectId(assignment_id) if ObjectId.is_valid(assignment_id) else None

    if dco_assignments_collection is not None:
        result = await dco_assignments_collection.update_one(
            {
                "$and": [
                    {
                        "$or": [
                            {"assignment_id": assignment_id},
                            {"_id": object_id},
                        ]
                    },
                    assignment_owner_filter,
                ]
            },
            {"$set": values},
            **_session_kwargs(session),
        )
        if result.matched_count:
            return True

    # The Match Centre assign route can store ownership and status directly
    # on stats_requests. Apply the same owner check before allowing a decision.
    if stats_requests_collection is not None:
        request_result = await stats_requests_collection.update_one(
            {
                "$and": [
                    {
                        "$or": [
                            {"request_id": assignment_id},
                            {"assignment_id": assignment_id},
                            {"_id": object_id if object_id is not None else assignment_id},
                        ]
                    },
                    assignment_owner_filter,
                ]
            },
            {"$set": values},
            **_session_kwargs(session),
        )
        return bool(request_result.matched_count)
    return False


@router.post("/api/dco/accept-assignment")
async def accept_assignment(request: Request, payload: AssignmentDecision):
    identifier = _dco_id(await _current_tracker_user(request))
    assignment_id = payload.identifier()
    if not assignment_id:
        raise HTTPException(status_code=400, detail="assignment_id is required")
    updated = await _update_owned_assignment_or_request(
        identifier, assignment_id, {"status": "accepted", "accepted_at": _now()}
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Assignment not found or not yours")
    return JSONResponse({"success": True, "message": "Assignment accepted successfully!"})


@router.post("/api/dco/decline-assignment")
async def decline_assignment(request: Request, payload: AssignmentDecision):
    identifier = _dco_id(await _current_tracker_user(request))
    assignment_id = payload.identifier()
    if not assignment_id:
        raise HTTPException(status_code=400, detail="assignment_id is required")
    updated = await _update_owned_assignment_or_request(
        identifier,
        assignment_id,
        {
            "status": "declined",
            "reason": payload.reason or "",
            "declined_at": _now(),
        },
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Assignment not found or not yours")
    return JSONResponse({"success": True, "message": "Assignment declined successfully!"})


@router.post("/api/dco/{id}/widget/save-draft")
async def save_widget_draft(id: str, request: Request, payload: DraftRequest):
    user = await get_current_user(request)
    _authorize(user, id)
    await _ensure_submission_index()
    now = _now()
    assignment_value = _payload_value(payload, "assignmentId", "assignment_id", default="")
    assignment_id = str(assignment_value or "").strip()
    raw_players = payload.players or []
    raw_club_tracking = _payload_value(
        payload, "clubTracking", "club_tracking", default=None
    )

    if raw_club_tracking is not None:
        normalised_players = []
    else:
        try:
            normalised_players = _normalise_widget_players(
                raw_players,
                _payload_value(payload, "actions", default=[]),
                max_players=3,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    match, geo = _normalise_widget_match(payload)
    match_id = str(match.get("match_id") or assignment_id).strip()
    try:
        club_tracking = _normalise_club_tracking(
            raw_club_tracking, assignment_id=assignment_id, match_id=match_id
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for profile, events in normalised_players:
        profile["assignment_id"] = profile.get("assignment_id") or assignment_id or None
        for event in events:
            event["assignment_id"] = event.get("assignment_id") or profile.get("assignment_id")
            event["match_id"] = event.get("match_id") or match_id or None

    draft_id = ObjectId()
    key = {"dco_id": id, "assignment_id": assignment_id, "match_id": match_id}
    draft = {
        "_id": draft_id,
        "schema_version": 2,
        **key,
        "match": match,
        "entity_type": "club" if club_tracking is not None else "player",
        "tracking_type": "club" if club_tracking is not None else "full",
        "player_count": len(normalised_players),
        "event_count": (
            sum(len(events) for _profile, events in normalised_players)
            + len(club_tracking.get("events", []) if club_tracking else [])
        ),
        "club_event_count": len(club_tracking.get("events", []) if club_tracking else []),
        "club_tracking": club_tracking,
        "assignment_ids": list(dict.fromkeys(
            [str(value).strip() for value in (_payload_value(payload, "assignmentIds", "assignment_ids", default=[]) or [])
             if value is not None and str(value).strip()]
            + ([assignment_id] if assignment_id else [])
        )),
        "updated_at": now,
        "created_at": now,
    }
    if geo:
        draft["geo"] = geo

    async def persist(session):
        opts = _session_kwargs(session)
        existing = await stat_drafts_collection.find_one(key, **opts)
        if existing:
            draft_id_local = existing["_id"]
            draft["created_at"] = existing.get("created_at", now)
            await stat_drafts_collection.update_one(
                {"_id": draft_id_local},
                {"$set": {k: v for k, v in draft.items() if k not in {"_id", "created_at"}}},
                **opts,
            )
        else:
            draft_id_local = draft_id
            await stat_drafts_collection.insert_one(draft, **opts)

        await stat_draft_players_collection.delete_many({"draft_id": draft_id_local}, **opts)
        await stat_draft_events_collection.delete_many({"draft_id": draft_id_local}, **opts)

        player_rows = []
        event_rows = []
        for order, (profile, events) in enumerate(normalised_players):
            profile_id = ObjectId()
            player_rows.append(
                {
                    "_id": profile_id,
                    "draft_id": draft_id_local,
                    **profile,
                }
            )
            event_rows.extend(
                {
                    "_id": ObjectId(),
                    "draft_id": draft_id_local,
                    "draft_player_id": profile_id,
                    "event_order": event_order,
                    **event,
                }
                for event_order, event in enumerate(events)
            )
        event_rows.extend(
            _club_event_documents("draft_id", draft_id_local, club_tracking)
        )
        if player_rows:
            await stat_draft_players_collection.insert_many(player_rows, **opts)
        if event_rows:
            await stat_draft_events_collection.insert_many(event_rows, **opts)
        return draft_id_local

    saved_draft_id = await _run_atomic(persist)
    if liveness_sessions_collection is not None:
        await liveness_sessions_collection.find_one_and_update(
            {"user_id": id},
            {"$set": {"user_id": id, "is_active": True, "updated_at": now}},
            upsert=True,
        )
    doc_id = str(saved_draft_id)
    return JSONResponse({"success": True, "_id": doc_id, "id": doc_id, "message": "Draft saved"})


@router.post("/api/dco/{id}/widget/submit")
async def submit_widget_stats(id: str, request: Request, payload: WidgetSubmitRequest):
    user = await get_current_user(request)
    _authorize(user, id)
    await _ensure_submission_index()
    submission_key = _submission_key(id, request, payload)

    # The unique submission key makes retries safe across multiple workers.
    async with _submission_index_lock:
        existing = await stat_submissions_collection.find_one({"submission_key": submission_key})
        if existing:
            existing["_idempotent_replay"] = True
            return _submission_result_response(existing, submission_key)

        now = _now()
        dco = await dco_collection.find_one(
            {"$or": [{"dco_id": id}, {"data_scout_id": id}, {"user_id": id}]}
        ) or {}
        assignment_value = _payload_value(payload, "assignmentId", "assignment_id", default="")
        assignment_id = str(assignment_value or "").strip()
        assignment_ids = _payload_value(payload, "assignmentIds", "assignment_ids", default=[])
        if not isinstance(assignment_ids, list):
            assignment_ids = []
        assignment_ids = list(dict.fromkeys(
            [
                str(value).strip()
                for value in assignment_ids
                if value is not None and str(value).strip()
                and str(value).strip().lower() not in {"none", "null", "undefined"}
            ]
            + ([assignment_id] if assignment_id else [])
        ))
        supervisor_id = (
            _payload_value(payload, "supervisorId", "supervisor_id", default=None)
            or dco.get("supervisor_id")
            or ""
        )
        status = "pending_approval" if supervisor_id else "approved"
        tracking_type = str(
            _payload_value(payload, "tracking_type", "trackingType", default="")
            or "full"
        ).strip().lower()
        raw_club_tracking = _payload_value(
            payload, "clubTracking", "club_tracking", default=None
        )
        if raw_club_tracking is not None:
            tracking_type = "club"
        elif tracking_type in {"club_tracking", "club-match", "club_match"}:
            tracking_type = "club"
        submission_trigger = str(
            _payload_value(
                payload, "submission_trigger", "submissionTrigger", default="individual"
            )
            or "individual"
        ).strip().lower()
        raw_players = payload.players
        if raw_players is None:
            raw_players = [
                {
                    "playerId": payload.player_id or "legacy-player",
                    "name": payload.player_name or "",
                    "position": payload.position or "",
                    "playerCategory": _payload_value(
                        payload,
                        "playerCategory",
                        "player_category",
                        "category",
                        "matchCategory",
                        "match_category",
                        default=None,
                    ),
                    "playerLevel": _payload_value(
                        payload,
                        "playerLevel",
                        "player_level",
                        "level",
                        default=None,
                    ),
                    "stats": payload.stats or {},
                    "events": _payload_value(payload, "events", default=[]),
                }
            ]

        if tracking_type == "club":
            normalised_players = []
            reason_value = None
        elif tracking_type == "reason":
            reason = str(payload.reason or "").strip()
            if not reason:
                raise HTTPException(status_code=400, detail="reason is required for non-tracking submissions")
            normalised_players = []
            reason_value = reason
        else:
            try:
                normalised_players = _normalise_widget_players(
                    raw_players,
                    _payload_value(payload, "actions", default=[]),
                    max_players=3,
                )
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            reason_value = None

        match, geo = _normalise_widget_match(payload)
        try:
            club_tracking = _normalise_club_tracking(
                raw_club_tracking,
                assignment_id=assignment_id,
                match_id=str(match.get("match_id") or assignment_id).strip(),
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if tracking_type == "club" and (
            not club_tracking or not club_tracking.get("events")
        ):
            raise HTTPException(
                status_code=422,
                detail="Record at least one club match event before submitting",
            )
        for profile, events in normalised_players:
            profile["assignment_id"] = profile.get("assignment_id") or assignment_id or None
            for event in events:
                event["assignment_id"] = event.get("assignment_id") or profile.get("assignment_id")
                event["match_id"] = event.get("match_id") or match.get("match_id") or assignment_id or None
        score_values = [
            float(profile.get("performance_score") or 0)
            for profile, _events in normalised_players
        ]
        match_projection = dict(match or {})
        first_profile = normalised_players[0][0] if normalised_players else {}
        root_id = ObjectId()
        root = {
            "_id": root_id,
            "schema_version": 2,
            "submission_key": submission_key,
            "client_submission_id": request.headers.get("X-Widget-Submission-Id", "").strip() or None,
            "dco_id": id,
            "assignment_id": assignment_id or None,
            "assignment_ids": assignment_ids,
            "supervisor_id": supervisor_id or None,
            "match": match,
            "match_id": match_projection.get("match_id") or match_projection.get("id") or "",
            "home_team": match_projection.get("home_team_name") or match_projection.get("home_team") or "",
            "away_team": match_projection.get("away_team_name") or match_projection.get("away_team") or "",
            "match_date": match_projection.get("match_date") or "",
            "match_time": match_projection.get("match_time") or "",
            "venue": match_projection.get("venue_name") or match_projection.get("venue") or "",
            "venue_address": match_projection.get("venue_address") or "",
            "venue_state": match_projection.get("venue_state") or "",
            "venue_lga": match_projection.get("venue_lga") or "",
            "venue_country": match_projection.get("venue_country") or "",
            "competition": match_projection.get("competition") or "",
            "players": [profile for profile, _events in normalised_players],
            "entity_type": "club" if tracking_type == "club" else "player",
            "club_tracking": club_tracking,
            "club_event_count": len(
                club_tracking.get("events", []) if club_tracking else []
            ),
            "stats": dict(first_profile.get("stats") or {}),
            "player_id": first_profile.get("player_id") or first_profile.get("playerId") or "",
            "player_name": first_profile.get("player_name") or first_profile.get("name") or "",
            "position": first_profile.get("position") or "",
            "player_level": first_profile.get("player_level") or first_profile.get("playerLevel") or first_profile.get("category") or "",
            "club": first_profile.get("club") or first_profile.get("club_name") or "",
            "jersey_number": first_profile.get("jersey_number") or first_profile.get("jerseyNumber") or "",
            "tracking_type": tracking_type,
            "submission_trigger": submission_trigger,
            "is_resubmit": bool(payload.isResubmit),
            "status": status,
            "player_count": len(normalised_players),
            "event_count": (
                sum(len(events) for _profile, events in normalised_players)
                + len(club_tracking.get("events", []) if club_tracking else [])
            ),
            "performance_score": max(score_values, default=0.0),
            "submitted_at": now,
            "created_at": now,
        }
        if reason_value:
            root["reason"] = reason_value
        if geo:
            root["geo"] = geo

        async def persist(session):
            opts = _session_kwargs(session)
            await stat_submissions_collection.insert_one(root, **opts)
            player_rows = []
            event_rows = []
            for profile, events in normalised_players:
                submission_player_id = ObjectId()
                player_rows.append(
                    {
                        "_id": submission_player_id,
                        "submission_id": root_id,
                        **profile,
                    }
                )
                event_rows.extend(
                    {
                        "_id": ObjectId(),
                        "submission_id": root_id,
                        "submission_player_id": submission_player_id,
                        "event_order": event_order,
                        **event,
                    }
                    for event_order, event in enumerate(events)
                )
            if player_rows:
                await stat_submission_players_collection.insert_many(player_rows, **opts)
            if event_rows:
                await stat_events_collection.insert_many(event_rows, **opts)
            club_event_rows = _club_event_documents(
                "submission_id", root_id, club_tracking
            )
            if club_event_rows:
                await stat_events_collection.insert_many(club_event_rows, **opts)

            if tracking_type != "reason":
                if tracking_type == "club":
                    activity_description = (
                        f"Submitted club statistics for "
                        f"{len(club_event_rows)} event(s): "
                        f"{match.get('home_team_name') or 'home'} vs "
                        f"{match.get('away_team_name') or 'away'}"
                    )
                else:
                    activity_description = (
                        f"Submitted stats for {len(player_rows)} player(s): "
                        f"{match.get('home_team_name') or 'home'} vs "
                        f"{match.get('away_team_name') or 'away'}"
                    )
                await activity_history_collection.insert_one(
                    {
                        "actor_id": id,
                        "actor_role": "dco",
                        "assignment_id": assignment_id or None,
                        "submission_id": root_id,
                        "type": "stats_submission",
                        "description": activity_description,
                        "created_at": now,
                    },
                    **opts,
                )
            for completed_assignment_id in assignment_ids:
                await _update_owned_assignment_or_request(
                    id,
                    completed_assignment_id,
                    {
                        "status": "pending_approval" if supervisor_id else "completed",
                        "submitted_at": now,
                        "completed_at": now if not supervisor_id else None,
                        "submission_id": root_id,
                        "updated_at": now,
                    },
                    session=session,
                )
            return root

        try:
            record = await _run_atomic(persist)
        except DuplicateKeyError:
            existing = await stat_submissions_collection.find_one(
                {"submission_key": submission_key}
            )
            if existing:
                existing["_idempotent_replay"] = True
                return _submission_result_response(existing, submission_key)
            raise

        if liveness_sessions_collection is not None:
            await liveness_sessions_collection.update_many(
                {"user_id": id, "is_active": True},
                {"$set": {"is_active": False, "updated_at": now}},
            )
        return _submission_result_response(record, submission_key)





@router.post("/api/dco/{id}/liveness/heartbeat")
async def liveness_heartbeat(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    now = _now()
    await liveness_sessions_collection.find_one_and_update(
        {"user_id": id},
        {"$set": {"user_id": id, "is_active": True, "updated_at": now}},
        upsert=True,
    )
    return JSONResponse({"success": True, "is_active": True, "user_id": id})


@router.delete("/api/dco/{id}/liveness/heartbeat")
async def stop_liveness(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    now = _now()
    await liveness_sessions_collection.update_many(
        {"user_id": id},
        {"$set": {"is_active": False, "updated_at": now}},
    )
    return JSONResponse({"success": True, "is_active": False, "user_id": id})
