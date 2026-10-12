"""
player_dashboard_routes.py
==========================
FastAPI APIRouter module — all API endpoints consumed by player-dashboard.html.

Integration (already stubbed in main.py):
    import player_dashboard_routes as _pdr
    _pdr._setup_dependencies(globals())
    app.include_router(_pdr.router)

Design rules
------------
* Zero imports from main at module-level (circular-import prevention).
* All shared state injected via _setup_dependencies() from main.py globals().
* Router prefix is /api; every route path starts from there.
* Helpers reused from main: get_current_user, verify_password, hash_password,
  MongoSerializer, upload_to_cloudinary, calculate_performance_score,
  aggregate_player_stats, get_token_cost, _make_tx_ref, _make_stats_request_ref.
* No business logic is duplicated from main.py or auth.py.
"""

from __future__ import annotations

import re
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ============================================================
# START: MODULE CONFIGURATION / DEPENDENCY CONTRACT
# ============================================================

database = None

# Primary collections
players_collection            = None
player_stats_collection       = None
stats_requests_collection     = None
stat_submissions_collection   = None
stat_submission_players_collection = None
stat_events_collection        = None
player_tokens_collection      = None
token_transactions_collection = None
notifications_collection      = None
match_fixtures_collection     = None
competitions_collection       = None
agent_contracts_collection    = None
content_manager_contracts_collection = None
stadiums_collection           = None
support_tickets_collection    = None
payment_intents_collection    = None
transactions_collection       = None
clubs_collection              = None
agents_collection             = None
subscriptions_collection      = None

# Canonical auth / identity / permission services
get_current_user = None
get_player_user = None
verify_password = None
hash_password = None
normalize_email = None
normalize_role = None
role_has_permission = None
ROLE_COLLECTION_MAP = None
CANONICAL_ROLES = None
TOKEN_ELIGIBLE_ROLES = None
SUBSCRIPTION_ELIGIBLE_ROLES = None
build_user_access_token = None

# Business-logic helpers
MongoSerializer             = None
logger                      = None
upload_to_cloudinary        = None
send_email                  = None
_make_tx_ref                = None
_make_stats_request_ref     = None
normalize_level             = None
calculate_performance_score = None
aggregate_player_stats      = None
_user_auth_check            = None
_find_user_doc              = None
find_player_by_uid          = None

# Config / pricing
FLUTTERWAVE_PUBLIC_KEY = None
FLUTTERWAVE_SECRET_KEY = None
pricing_service        = None
get_token_cost         = None

_DEPS_READY = False

# ============================================================
# END: MODULE CONFIGURATION / DEPENDENCY CONTRACT

# ============================================================
# START: ROUTER
# ============================================================

router = APIRouter(prefix="/api", tags=["player-dashboard"])

# ============================================================
# END: ROUTER

# ============================================================
# START: CANONICAL DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Populate every module-level placeholder from the main module namespace.
    Called once by main.py immediately after importing this module.
    """
    global _DEPS_READY

    global database
    global players_collection, player_stats_collection, stats_requests_collection
    global stat_submissions_collection, stat_submission_players_collection
    global stat_events_collection
    global player_tokens_collection, token_transactions_collection, notifications_collection
    global match_fixtures_collection, competitions_collection, agent_contracts_collection, content_manager_contracts_collection
    global stadiums_collection, support_tickets_collection
    global payment_intents_collection, transactions_collection, clubs_collection
    global agents_collection, subscriptions_collection

    global get_current_user, get_player_user, verify_password, hash_password
    global normalize_email, normalize_role, role_has_permission
    global ROLE_COLLECTION_MAP, CANONICAL_ROLES
    global TOKEN_ELIGIBLE_ROLES, SUBSCRIPTION_ELIGIBLE_ROLES
    global build_user_access_token

    global MongoSerializer, logger, upload_to_cloudinary, send_email
    global _make_tx_ref, _make_stats_request_ref, normalize_level
    global calculate_performance_score, aggregate_player_stats
    global _user_auth_check, _find_user_doc, find_player_by_uid

    global FLUTTERWAVE_PUBLIC_KEY, FLUTTERWAVE_SECRET_KEY
    global pricing_service, get_token_cost

    if _DEPS_READY:
        return

    g = main_globals

    # ── Database handle ──────────────────────────────────────
    database = g.get("database")
    if database is None:
        raise RuntimeError(
            "Database dependency was not injected into player_dashboard_routes."
        )

    # ── Required collections ─────────────────────────────────
    players_collection = g.get("players_collection")
    player_stats_collection = g.get("player_stats_collection")
    stats_requests_collection = g.get("stats_requests_collection")
    stat_submissions_collection = g.get("stat_submissions_collection")
    if stat_submissions_collection is None:
        stat_submissions_collection = database["stat_submissions"]
    stat_submission_players_collection = g.get("stat_submission_players_collection")
    if stat_submission_players_collection is None:
        stat_submission_players_collection = database["stat_submission_players"]
    stat_events_collection = g.get("stat_events_collection")
    if stat_events_collection is None:
        stat_events_collection = database["stat_events"]
    player_tokens_collection = g.get("player_tokens_collection")
    token_transactions_collection = g.get("token_transactions_collection")
    notifications_collection = g.get("notifications_collection")
    payment_intents_collection = g.get("payment_intents_collection")
    clubs_collection = g.get("clubs_collection")
    agents_collection = g.get("agents_collection")
    subscriptions_collection = g.get("subscriptions_collection")

    # ── Optional collections with safe fallbacks ─────────────
    match_fixtures_collection = g.get("match_fixtures_collection")
    if match_fixtures_collection is None:
        match_fixtures_collection = database["match_fixtures"]

    competitions_collection = g.get("competitions_collection")
    if competitions_collection is None:
        competitions_collection = database["competitions"]

    agent_contracts_collection = g.get("agent_contracts_collection")
    if agent_contracts_collection is None:
        agent_contracts_collection = database["agent_contracts"]

    content_manager_contracts_collection = g.get("content_manager_contracts_collection")
    if content_manager_contracts_collection is None:
        content_manager_contracts_collection = database["content_manager_contracts"]

    stadiums_collection = g.get("stadiums_collection")
    if stadiums_collection is None:
        stadiums_collection = database["stadiums"]

    support_tickets_collection = g.get("support_tickets_collection")
    if support_tickets_collection is None:
        support_tickets_collection = database["support_tickets"]

    transactions_collection = g.get("transactions_collection")
    if transactions_collection is None:
        transactions_collection = database["transactions"]

    # ── Canonical authentication / identity / permissions ────
    get_current_user = g.get("get_current_user")
    get_player_user = g.get("get_player_user")
    verify_password = g.get("verify_password")
    hash_password = g.get("hash_password")
    normalize_email = g.get("normalize_email")
    normalize_role = g.get("normalize_role")
    role_has_permission = g.get("role_has_permission")
    ROLE_COLLECTION_MAP = g.get("ROLE_COLLECTION_MAP")
    CANONICAL_ROLES = g.get("CANONICAL_ROLES")
    TOKEN_ELIGIBLE_ROLES = g.get("TOKEN_ELIGIBLE_ROLES")
    SUBSCRIPTION_ELIGIBLE_ROLES = g.get("SUBSCRIPTION_ELIGIBLE_ROLES")
    build_user_access_token = g.get("build_user_access_token")

    # ── Shared business helpers ──────────────────────────────
    MongoSerializer = g.get("MongoSerializer")
    logger = g.get("logger")
    upload_to_cloudinary = g.get("upload_to_cloudinary")
    send_email = g.get("send_email")

    _make_tx_ref = g.get("_make_tx_ref")
    _make_stats_request_ref = g.get("_make_stats_request_ref")
    normalize_level = g.get("normalize_level")

    calculate_performance_score = g.get("calculate_performance_score")
    aggregate_player_stats = g.get("aggregate_player_stats")

    _user_auth_check = g.get("_user_auth_check")
    _find_user_doc = g.get("_find_user_doc")
    find_player_by_uid = g.get("find_player_by_uid")

    # ── Pricing & payment helpers ────────────────────────────
    FLUTTERWAVE_PUBLIC_KEY = g.get("FLUTTERWAVE_PUBLIC_KEY", "")
    FLUTTERWAVE_SECRET_KEY = g.get("FLUTTERWAVE_SECRET_KEY", "")

    pricing_service = g.get("pricing_service")
    get_token_cost = g.get("get_token_cost")

    required_canonical = {
        "get_current_user": get_current_user,
        "verify_password": verify_password,
        "hash_password": hash_password,
        "MongoSerializer": MongoSerializer,
        "normalize_role": normalize_role,
        "ROLE_COLLECTION_MAP": ROLE_COLLECTION_MAP,
        "CANONICAL_ROLES": CANONICAL_ROLES,
    }
    missing = [name for name, value in required_canonical.items() if value is None]
    if missing:
        raise RuntimeError(
            "Canonical main.py dependencies missing from player_dashboard_routes: "
            + ", ".join(missing)
        )

    _DEPS_READY = True

    if logger is not None:
        logger.debug(
            "[player_dashboard_routes] _setup_dependencies COMPLETE | "
            "players_collection=%s | subscriptions_collection=%s",
            players_collection.name if players_collection is not None else "MISSING",
            subscriptions_collection.name if subscriptions_collection is not None else "MISSING",
        )

# ============================================================
# END: CANONICAL DEPENDENCY INJECTION

# ============================================================
# START: PYDANTIC MODELS
# ============================================================

class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class ContractRespondBody(BaseModel):
    request_id: str
    action: str
    code: Optional[str] = ""


class ContentManagerContractRespondBody(BaseModel):
    contract_id: str
    action: str
    code: Optional[str] = ""


class ContentManagerContractTerminateBody(BaseModel):
    reason: str = ""


class StatsRequestBody(BaseModel):
    match_date: Optional[str] = None
    match_time: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    homeTeam: Optional[str] = None
    awayTeam: Optional[str] = None
    jersey_number: Optional[str] = None
    player_represents: Optional[str] = "home"
    match_type: Optional[str] = None
    heatmap: Optional[bool] = False
    venue_address: Optional[str] = None
    venue_country: Optional[str] = None
    venue_country_code: Optional[str] = None
    venue_state: Optional[str] = None
    venue_lga: Optional[str] = None
    venue_city: Optional[str] = None
    venue_detailed_address: Optional[str] = None
    contact_phone: Optional[str] = None

    class Config:
        extra = "allow"


class CompetitionApplyBody(BaseModel):
    competition_id: Optional[str] = None
    competition_title: Optional[str] = None
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_category: Optional[str] = None
    player_position: Optional[str] = None
    player_club: Optional[str] = None
    applied_at: Optional[str] = None

    class Config:
        extra = "allow"


class TokenTopupBody(BaseModel):
    amount: float
    tokens: int
    description: Optional[str] = ""
    player_id: Optional[str] = None


class TokenVerifyBody(BaseModel):
    transaction_id: Optional[str] = None
    tx_ref: Optional[str] = None


class YouTubeVideoBody(BaseModel):
    url: str
    title: Optional[str] = "YouTube Video"


class PlayerSettingsBody(BaseModel):
    """
    Partial settings update for a player account.
    All fields are optional — only supplied fields are applied.

    Frontend field mapping
    ─────────────────────
    dob_visible           ← Privacy Settings toggle (DOB visibility)
    notif_email_contract  ← "Email notifications for contract requests"
    notif_email_token     ← "Email notifications for token updates"
    notif_inapp_stats     ← "In-app notifications for stats updates"
    """
    dob_visible:           Optional[bool] = None
    profile_visible:       Optional[bool] = None
    contact_visible:       Optional[bool] = None
    # Legacy generic notification flags
    email_notifications:   Optional[bool] = None
    sms_notifications:     Optional[bool] = None
    push_notifications:    Optional[bool] = None
    # Granular notification flags sent by the Settings modal
    notif_email_contract:  Optional[bool] = None
    notif_email_token:     Optional[bool] = None
    notif_inapp_stats:     Optional[bool] = None
    language:              Optional[str]  = None
    timezone:              Optional[str]  = None

    class Config:
        extra = "allow"  # accept any additional boolean/string setting keys


# ============================================================
# END: PYDANTIC MODELS

# ============================================================
# START: MODULE-SPECIFIC HELPERS
# ============================================================

def _pf(uid: str) -> dict:
    """MongoDB filter that matches a player by user_id or player_id."""
    return {"$or": [{"user_id": uid}, {"player_id": uid}]}


async def _resolve_player(uid: str) -> Optional[dict]:
    """Find a player document by uid (user_id, player_id, or ObjectId)."""
    if players_collection is None:    # ← correct None-check
        return None
    doc = await players_collection.find_one(_pf(uid))
    if not doc and len(uid) == 24:
        try:
            doc = await players_collection.find_one({"_id": ObjectId(uid)})
        except Exception:
            pass
    return doc


def _pid(doc: dict) -> str:
    """Return the canonical player_id from a player document."""
    return doc.get("player_id") or doc.get("user_id") or str(doc.get("_id", ""))


def _player_name(doc: dict) -> str:
    full = doc.get("name") or doc.get("full_name") or doc.get("player_name")
    if full:
        return str(full).strip()
    return " ".join(str(v or "").strip() for v in [
        doc.get("first_name") or doc.get("firstName"),
        doc.get("middle_name") or doc.get("middleName"),
        doc.get("last_name") or doc.get("lastName"),
    ] if v).strip() or "Player"


def _normalize_achievement_list(raw: Any) -> list:
    """Return achievements in the card-ready shape used by the dashboard.

    Older DCO updates stored comma-separated values as plain strings, while
    other parts of the application store achievement documents.  Normalizing
    both forms here keeps the public player API stable and prevents the
    frontend from trying to render ``a.title`` on a string.
    """
    if raw is None:
        return []

    if isinstance(raw, dict):
        items = [raw]
    elif isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        items = [part.strip() for part in raw.split(",") if part.strip()]
    else:
        items = [raw]

    normalized = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            title = (
                item.get("title")
                or item.get("name")
                or item.get("achievement")
                or item.get("award")
                or item.get("label")
            )
            description = item.get("description") or item.get("details") or item.get("notes") or ""
            category = item.get("category") or item.get("type") or "Achievement"
            date = item.get("date") or item.get("awarded_on") or item.get("year")
            organizer = item.get("organizer") or item.get("issuer") or item.get("awarded_by")
            icon = item.get("icon") or "fa-trophy"
            result = dict(item)
        else:
            title = str(item).strip()
            description = ""
            category = "Achievement"
            date = None
            organizer = None
            icon = "fa-trophy"
            result = {}

        title = str(title or "").strip()
        if not title:
            continue

        result.update({
            "id": result.get("id") or result.get("_id") or f"achievement-{index}",
            "title": title,
            "description": str(description or "").strip(),
            "category": str(category or "Achievement").strip(),
            "date": date,
            "icon": str(icon or "fa-trophy").strip(),
        })
        if organizer:
            result["organizer"] = str(organizer).strip()
        normalized.append(result)

    return normalized


async def _require_player_auth(request: Request, uid: str) -> dict:
    """
    Resolve the authenticated identity through main.py and enforce ownership.

    Player-dashboard resources are player-scoped. Canonical Admin and
    Supervisor identities retain the module's established privileged read/write
    access; all other identities must match the player's canonical public ID.
    """
    user = await get_current_user(request)
    role = normalize_role(user.get("role", ""))

    if role in {"admin", "supervisor"}:
        return user

    canonical_player_id = str(user.get("player_id") or "")
    canonical_user_id = str(user.get("user_id") or user.get("unique_id") or "")
    requested_id = str(uid or "")

    if requested_id not in {canonical_player_id, canonical_user_id}:
        raise HTTPException(status_code=403, detail="Access denied")

    return user


def _make_ref(prefix: str) -> str:
    """Generate domain references through main.py's canonical helpers."""
    if prefix.startswith("SR"):
        return _make_stats_request_ref()
    if prefix.startswith("TX"):
        return _make_tx_ref()
    raise ValueError(f"Unsupported canonical reference prefix: {prefix}")


def _ser(doc: Optional[dict]) -> Optional[dict]:
    """Serialize through main.py's canonical MongoSerializer."""
    if not doc:
        return None
    return MongoSerializer.serialize_document(doc)


def _ser_list(docs: list) -> list:
    return [_ser(d) for d in docs if d]


def _now() -> datetime:
    """Return main.py's canonical UTC-aware timestamp."""
    return MongoSerializer.now_utc()


def _player_filter_combined(uid: str, pid_val: str) -> dict:
    """Match player by either uid or pid_val across common field names."""
    ids = list({uid, pid_val} - {""})
    clauses = []
    for fid in ids:
        clauses += [{"player_id": fid}, {"unique_id": fid}]
    return {"$or": clauses} if clauses else {"player_id": uid}


_DASHBOARD_OUTFIELD_STAT_FIELDS = (
    "goals",
    "shot_goals",
    "header_goals",
    "penalty_goals",
    "assists",
    "shots",
    "shots_on_target",
    "shots_off_target",
    "shots_blocked",
    "free_kick_goals",
    "penalty_goals_conceded",
    "successful_short_passes",
    "unsuccessful_short_passes",
    "successful_long_passes",
    "unsuccessful_long_passes",
    "passes_attempted",
    "passes_completed",
    "through_balls",
    "switches",
    "final_third_passes",
    "penalty_area_passes",
    "successful_dribbles",
    "unsuccessful_dribbles",
    "progressive_dribbles",
    "successful_crosses",
    "unsuccessful_crosses",
    "tackles_won",
    "tackles_lost",
    "duels_won",
    "duels_lost",
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
    "key_passes",
    "carries",
    "substitution",
    "cards",
    "big_chances_created",
    "big_chances_missed",
    "progressive_passes",
    "progressive_carries",
    "final_third_entries",
    "penalty_area_entries",
    "recoveries",
    "blocks",
    "defensive_errors",
    "pressure_actions",
    "successful_pressure_actions",
    "unsuccessful_pressure_actions",
    "fouls_committed",
    "passes",
    "dribbles",
    "crosses",
    "tackles",
    "duels",
    "big_chances",
    "substitutions",
    "possession_losses",
)

_DASHBOARD_GOALKEEPER_STAT_FIELDS = (
    "saves",
    "goals_conceded",
    "clean_sheets",
    "penalty_saves",
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
    "shots_faced",
    "claims",
    "defensive_errors",
    "recoveries",
    "blocks",
    "key_passes",
    "carries",
    "substitution",
    "cards",
    "progressive_passes",
    "progressive_carries",
    "final_third_entries",
    "penalty_area_entries",
    "pressure_actions",
    "successful_pressure_actions",
    "unsuccessful_pressure_actions",
    "fouls_committed",
    "passes",
    "dribbles",
    "crosses",
    "tackles",
    "duels",
    "big_chances",
    "substitutions",
    "possession_losses",
)

_DASHBOARD_PAIR_EVENT_FIELDS = {
    "shots": ("shots_on_target", "shots_off_target"),
    "passes": ("successful_short_passes", "unsuccessful_short_passes"),
    "longpass": ("successful_long_passes", "unsuccessful_long_passes"),
    "dribbles": ("successful_dribbles", "unsuccessful_dribbles"),
    "crosses": ("successful_crosses", "unsuccessful_crosses"),
    "duels": ("aerial_duels_won", "aerial_duels_lost"),
    "tackles": ("tackles_won", "tackles_lost"),
    "distribution": (
        "successful_distributions",
        "unsuccessful_distributions",
    ),
}

_DASHBOARD_SINGLE_EVENT_FIELDS = {
    "assists": "assists",
    "foulsWon": "fouls_won",
    "dispossessed": "dispossessed",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "saves": "saves",
    "goalsConceded": "goals_conceded",
    "penaltySaves": "penalty_saves",
    "cleanSheets": "clean_sheets",
    "punches": "punches",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "fouls": "fouls_given",
    "offsides": "offsides",
    "substitution": "substitution",
}


def _is_goalkeeper_position(position: Any) -> bool:
    normalized = str(position or "").strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    return (
        normalized in {"gk", "g", "goalkeeper", "goal keeper", "goalie"}
        or "keeper" in normalized
        or "goalie" in normalized
    )


_DASHBOARD_CATEGORY_ALIASES = {
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
_DASHBOARD_CATEGORY_POLICIES = {
    "professional": {"max_subtypes": None, "sections": None},
    "semi-professional": {
        "max_subtypes": None,
        "sections": {"attack", "defence", "discipline", "goalkeeping"},
    },
    "university": {
        "max_subtypes": 3,
        "sections": {"attack", "defence", "discipline", "goalkeeping"},
    },
    "academy": {
        "max_subtypes": 3,
        "sections": {"attack", "defence", "discipline", "goalkeeping"},
    },
    "others": {
        "max_subtypes": 3,
        "sections": {"attack", "defence", "discipline", "goalkeeping"},
    },
}
_DASHBOARD_TRACKER_METRICS_BY_SECTION = {
    "attack": (
        "goals", "shots", "assists", "key_passes", "crosses",
        "passes", "dribbles", "carries", "big_chances",
    ),
    "defence": (
        "tackles", "duels", "recoveries", "interceptions", "clearances",
        "blocks", "fouls_won", "fouls_committed", "defensive_errors",
    ),
    "discipline": ("cards", "offsides", "substitutions"),
    "advanced": ("pressure_actions", "possession_losses"),
    "goalkeeping": ("saves", "shots_faced", "claims", "punches", "distribution"),
}
_DASHBOARD_GOALKEEPER_ONLY_METRICS = {
    "saves", "shots_faced", "claims", "punches", "distribution",
}
_DASHBOARD_GOALKEEPER_AVAILABLE_METRICS = {
    "passes", "dribbles", "duels", "interceptions", "clearances",
    "fouls_won", "fouls_committed",
}


def _dashboard_normalize_category(value: Any) -> str:
    normalized = " ".join(
        str(value or "").strip().lower().replace("_", " ").replace("-", " ").split()
    )
    return _DASHBOARD_CATEGORY_ALIASES.get(normalized, "others")


def _dashboard_category_policy(value: Any) -> dict:
    category = _dashboard_normalize_category(value)
    policy = _DASHBOARD_CATEGORY_POLICIES.get(
        category, _DASHBOARD_CATEGORY_POLICIES["others"]
    )
    return {"category": category, **policy}


def _dashboard_metric_alias(metric: Any) -> str:
    value = str(metric or "").strip()
    return {
        "longpass": "passes",
        "pass": "passes",
        "fouls_won": "fouls_won",
        "foulsWon": "fouls_won",
        "fouls_committed": "fouls_committed",
        "foulsCommitted": "fouls_committed",
        "key_passes": "key_passes",
        "keyPasses": "key_passes",
        "defensive_errors": "defensive_errors",
        "defensiveErrors": "defensive_errors",
        "shots_faced": "shots_faced",
        "shotsFaced": "shots_faced",
        "goals_conceded": "goals_conceded",
        "goalsConceded": "goals_conceded",
        "yellow_cards": "yellow_cards",
        "yellowCards": "yellow_cards",
        "red_cards": "red_cards",
        "redCards": "red_cards",
        "substitution": "substitutions",
        "substitutions": "substitutions",
        "bigChances": "big_chances",
        "big_chances": "big_chances",
        "pressureActions": "pressure_actions",
        "pressure_actions": "pressure_actions",
        "possessionLosses": "possession_losses",
        "possession_losses": "possession_losses",
        "progressivePasses": "progressive_passes",
        "progressiveCarries": "progressive_carries",
    }.get(value, value)


def _dashboard_projection_metric(metric: Any) -> str:
    """Convert tracker metric names to the legacy projection switch names."""
    canonical = _dashboard_metric_alias(metric)
    return {
        "fouls_won": "foulsWon",
        "fouls_committed": "foulsCommitted",
        "key_passes": "keyPasses",
        "defensive_errors": "defensiveErrors",
        "shots_faced": "shotsFaced",
        "goals_conceded": "goalsConceded",
        "yellow_cards": "yellowCards",
        "red_cards": "redCards",
        "substitutions": "substitution",
        "pressure_actions": "pressureActions",
        "possession_losses": "possessionLosses",
        "progressive_passes": "progressivePasses",
        "progressive_carries": "progressiveCarries",
    }.get(canonical, canonical)


def _dashboard_allowed_metric_keys(position: str, category: Any) -> set[str]:
    policy = _dashboard_category_policy(category)
    allowed_sections = policy["sections"]
    is_goalkeeper = _is_goalkeeper_position(position)
    allowed = set()
    for section, metrics in _DASHBOARD_TRACKER_METRICS_BY_SECTION.items():
        if allowed_sections is not None and section not in allowed_sections:
            continue
        for metric in metrics:
            if is_goalkeeper:
                if (
                    metric in _DASHBOARD_GOALKEEPER_ONLY_METRICS
                    or metric in _DASHBOARD_GOALKEEPER_AVAILABLE_METRICS
                ):
                    allowed.add(metric)
            elif metric not in _DASHBOARD_GOALKEEPER_ONLY_METRICS:
                allowed.add(metric)
    return allowed


def _dashboard_metric_value(stats: Dict[str, Any], metric: str) -> int | float:
    source = stats if isinstance(stats, dict) else {}

    def value(*keys: str) -> int | float:
        for key in keys:
            if key in source and source[key] not in (None, ""):
                return _dashboard_numeric(source[key])
        return 0

    def total(*keys: str) -> int | float:
        return sum(value(key) for key in keys)

    return {
        "shots": lambda: value("shots") or total(
            "shots_on_target", "shots_off_target", "shots_blocked"
        ),
        "passes": lambda: value("passes") or value("passes_attempted") or total(
            "successful_short_passes",
            "unsuccessful_short_passes",
            "successful_long_passes",
            "unsuccessful_long_passes",
        ),
        "crosses": lambda: value("crosses") or total(
            "successful_crosses", "unsuccessful_crosses"
        ),
        "dribbles": lambda: value("dribbles") or total(
            "successful_dribbles", "unsuccessful_dribbles"
        ),
        "tackles": lambda: value("tackles") or total("tackles_won", "tackles_lost"),
        "duels": lambda: value("duels") or total(
            "duels_won", "duels_lost", "aerial_duels_won", "aerial_duels_lost"
        ),
        "cards": lambda: value("cards") or total("yellow_cards", "red_cards"),
        "substitutions": lambda: value("substitutions") or value("substitution"),
        "big_chances": lambda: value("big_chances") or total(
            "big_chances_created", "big_chances_missed"
        ),
        "distribution": lambda: value("distribution") or total(
            "successful_distributions", "unsuccessful_distributions"
        ),
        "shots_faced": lambda: value("shots_faced") or total(
            "shots_on_target_faced", "goals_conceded"
        ),
        "possession_losses": lambda: value("possession_losses") or value("dispossessed"),
    }.get(metric, lambda: value(metric))()


def _dashboard_available_metric_keys(
    stats: Dict[str, Any],
    events: List[Dict[str, Any]],
    position: str,
    category: Any,
) -> List[str]:
    allowed = _dashboard_allowed_metric_keys(position, category)
    available = set()
    for event in events or []:
        metric = _dashboard_metric_alias(
            event.get("metric") or event.get("metric_key") or event.get("event_type")
        )
        if metric in allowed:
            available.add(metric)
    for metric in allowed:
        if _dashboard_metric_value(stats, metric) > 0:
            available.add(metric)
    return sorted(available)


def _dashboard_stat_fields(position: str) -> tuple[str, ...]:
    return (
        _DASHBOARD_GOALKEEPER_STAT_FIELDS
        if _is_goalkeeper_position(position)
        else _DASHBOARD_OUTFIELD_STAT_FIELDS
    )


def _stats_from_normalized_events(
    events: List[Dict[str, Any]], position: str
) -> Dict[str, int]:
    """Project tracker event rows into the dashboard's legacy stats shape.

    The stats tracker intentionally stores atomic events as the source of
    truth.  This read-side projection uses the same persisted field names as
    the old player_stats documents, so existing dashboard consumers need no
    response-shape change.
    """
    stats = {field: 0 for field in _dashboard_stat_fields(position)}
    # Keep the projection total even when a malformed or legacy submission
    # contains a role-inappropriate event; the position adapter below will
    # remove fields that are not part of the selected role contract.
    for field in _DASHBOARD_OUTFIELD_STAT_FIELDS + _DASHBOARD_GOALKEEPER_STAT_FIELDS:
        stats.setdefault(field, 0)

    for event in events:
        metric = _dashboard_projection_metric(
            event.get("metric") or event.get("metric_key") or event.get("event_type")
        )
        if metric == "goals":
            value_type = event.get("value_type") or event.get("valueType") or "shot"
            field = {
                "shot": "shot_goals",
                "header": "header_goals",
                "penalty": "penalty_goals",
                "free_kick": "free_kick_goals",
                "open_play": "shot_goals",
                "set_piece": "shot_goals",
            }.get(value_type, "shot_goals")
            stats[field] += 1
            stats["goals"] += 1
            continue

        if metric == "shots":
            value_type = str(
                event.get("value_type") or event.get("sub_key") or ""
            ).lower()
            if "on_target" in value_type or value_type in {"on", "target"}:
                target = "shots_on_target"
            elif "blocked" in value_type:
                target = "shots_blocked"
            else:
                target = "shots_off_target"
            if target in stats:
                stats[target] += 1
            if "shots" in stats:
                stats["shots"] += 1
            continue

        if metric in _DASHBOARD_PAIR_EVENT_FIELDS:
            # The mounted tracker sends subtype-aware values such as
            # short_success and long_fail.  Route those to the same
            # dashboard fields used by the legacy stats contract.
            is_through_ball = False
            if metric == "passes":
                value_type = str(event.get("value_type") or "").lower()
                is_long = "long" in value_type
                is_through_ball = "through_ball" in value_type
                success_field = (
                    "successful_long_passes"
                    if is_long
                    else "successful_short_passes"
                )
                failure_field = (
                    "unsuccessful_long_passes"
                    if is_long
                    else "unsuccessful_short_passes"
                )
            else:
                success_field, failure_field = _DASHBOARD_PAIR_EVENT_FIELDS[metric]
            outcome = str(event.get("outcome") or "success").lower()
            if is_through_ball:
                if "through_balls" in stats:
                    stats["through_balls"] += 1
            else:
                stats[failure_field if outcome == "failure" else success_field] += 1
            if metric == "passes":
                if "passes_attempted" in stats:
                    stats["passes_attempted"] += 1
                if outcome != "failure" and "passes_completed" in stats:
                    stats["passes_completed"] += 1
            continue

        field = _DASHBOARD_SINGLE_EVENT_FIELDS.get(metric)
        if field in stats:
            stats[field] += 1
            continue

        # Extended mounted-player widget metrics.  Atomic event rows retain
        # the original subtype; these aggregates make them available to the
        # existing stats-tab schema and season totals.
        if metric == "cards":
            value_type = str(event.get("value_type") or "").lower()
            target = "red_cards" if "red" in value_type else "yellow_cards"
            if target in stats:
                stats[target] += 1
            if "cards" in stats:
                stats["cards"] += 1
            continue

        if metric == "pressure_actions":
            stats["pressure_actions"] += 1
            outcome = str(event.get("outcome") or "").lower()
            target = (
                "unsuccessful_pressure_actions"
                if outcome in {"failure", "unsuccessful", "fail"}
                else "successful_pressure_actions"
            )
            if target in stats:
                stats[target] += 1
            continue

        extended_fields = {
            "keyPasses": "key_passes",
            "carries": "carries",
            "progressivePasses": "progressive_passes",
            "advancedProgressivePasses": "progressive_passes",
            "progressiveCarries": "progressive_carries",
            "advancedProgressiveCarries": "progressive_carries",
            "finalThirdEntries": "final_third_entries",
            "advancedFinalThird": "final_third_entries",
            "penaltyAreaEntries": "penalty_area_entries",
            "advancedPenaltyArea": "penalty_area_entries",
            "recoveries": "recoveries",
            "blocks": "blocks",
            "defensiveErrors": "defensive_errors",
            "pressureActions": "pressure_actions",
            "foulsCommitted": "fouls_committed",
            "possessionLosses": "dispossessed",
            "shotsFaced": "shots_faced",
            "claims": "claims",
            "substitution": "substitution",
            "substitutions": "substitution",
            "shots": "shots",
            "shotsBlocked": "shots_blocked",
            "shots_blocked": "shots_blocked",
            "freeKickGoals": "free_kick_goals",
            "free_kick_goals": "free_kick_goals",
            "penaltyGoalsConceded": "penalty_goals_conceded",
            "penalty_goals_conceded": "penalty_goals_conceded",
            "passesAttempted": "passes_attempted",
            "passes_attempted": "passes_attempted",
            "passesCompleted": "passes_completed",
            "passes_completed": "passes_completed",
            "throughBalls": "through_balls",
            "through_balls": "through_balls",
            "switches": "switches",
            "finalThirdPasses": "final_third_passes",
            "final_third_passes": "final_third_passes",
            "penaltyAreaPasses": "penalty_area_passes",
            "penalty_area_passes": "penalty_area_passes",
            "progressiveDribbles": "progressive_dribbles",
            "progressive_dribbles": "progressive_dribbles",
            "duelsWon": "duels_won",
            "duels_won": "duels_won",
            "duelsLost": "duels_lost",
            "duels_lost": "duels_lost",
        }
        target = extended_fields.get(metric)
        if target in stats:
            stats[target] += 1
            continue

        if metric in {"bigChances", "big_chances"}:
            value_type = str(event.get("value_type") or "").lower()
            target = "big_chances_missed" if "miss" in value_type else "big_chances_created"
            if target in stats:
                stats[target] += 1
            continue

        if metric == "foulsCommitted" and "fouls_given" in stats:
            stats["fouls_given"] += 1

    contribution_aliases = {
        "advanced_progressive_passes": "progressive_passes",
        "advanced_progressive_carries": "progressive_carries",
        "advanced_final_third": "final_third_entries",
        "advanced_penalty_area": "penalty_area_entries",
    }
    for event in events:
        contributions = event.get("derived_contributions")
        if not isinstance(contributions, dict):
            continue
        for contribution, amount in contributions.items():
            target = contribution_aliases.get(contribution, contribution)
            if target in stats:
                stats[target] += _dashboard_numeric(amount)

    return stats


def _dashboard_normalize_outcome(outcome: Any) -> str:
    """Normalize tracker outcomes without discarding the original detail."""
    value = str(outcome or "").strip().lower()
    if value in {"success", "successful", "won", "saved", "completed", "complete"}:
        return "success"
    if value in {"failure", "fail", "unsuccessful", "lost", "foul", "off_target", "blocked", "woodwork", "goal"}:
        return "failure"
    return value


def _dashboard_display_key(value: Any) -> str:
    """Turn a persisted metric/sub-key token into a stable human label."""
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("_", " ").replace("-", " ")).strip().title()


def _dashboard_metric_breakdown(events: List[Dict[str, Any]], position: str = "", category: Any = "") -> Dict[str, Dict[str, Any]]:
    """Preserve the complete tracker button -> outcome -> subbutton hierarchy."""
    allowed = _dashboard_allowed_metric_keys(position, category)
    result: Dict[str, Dict[str, Any]] = {}
    for event in events or []:
        if not isinstance(event, dict):
            continue
        metric = _dashboard_metric_alias(event.get("metric") or event.get("metric_key") or event.get("event_type"))
        if not metric or (allowed and metric not in allowed):
            continue
        row = result.setdefault(metric, {"metric": metric, "label": _dashboard_display_key(metric), "total": 0, "success": 0, "failure": 0, "outcomes": {}, "value_types": {}, "sub_keys": {}, "events": []})
        row["total"] += 1
        outcome_raw = event.get("outcome")
        outcome = _dashboard_normalize_outcome(outcome_raw)
        if outcome == "success": row["success"] += 1
        elif outcome == "failure": row["failure"] += 1
        outcome_key = str(outcome_raw or outcome or "recorded").strip().lower() or "recorded"
        out = row["outcomes"].setdefault(outcome_key, {"key": outcome_key, "label": _dashboard_display_key(outcome_key), "count": 0})
        out["count"] += 1
        value_type = str(event.get("value_type") or event.get("valueType") or "").strip()
        if value_type:
            vt = row["value_types"].setdefault(value_type, {"key": value_type, "label": _dashboard_display_key(value_type), "count": 0, "success": 0, "failure": 0, "outcomes": {}})
            vt["count"] += 1
            if outcome == "success": vt["success"] += 1
            elif outcome == "failure": vt["failure"] += 1
            vt_out = vt["outcomes"].setdefault(outcome_key, {"key": outcome_key, "label": _dashboard_display_key(outcome_key), "count": 0})
            vt_out["count"] += 1
        sub_key = str(event.get("sub_key") or event.get("subKey") or "").strip()
        if sub_key:
            sk = row["sub_keys"].setdefault(sub_key, {"key": sub_key, "label": _dashboard_display_key(sub_key), "count": 0, "success": 0, "failure": 0, "outcomes": {}, "value_types": {}})
            sk["count"] += 1
            if outcome == "success": sk["success"] += 1
            elif outcome == "failure": sk["failure"] += 1
            sk_out = sk["outcomes"].setdefault(outcome_key, {"key": outcome_key, "label": _dashboard_display_key(outcome_key), "count": 0})
            sk_out["count"] += 1
            if value_type:
                sk_type = sk["value_types"].setdefault(value_type, {"key": value_type, "label": _dashboard_display_key(value_type), "count": 0})
                sk_type["count"] += 1
        row["events"].append(_dashboard_event_view(event))
    return result


def _dashboard_merge_metric_breakdowns(target: Dict[str, Dict[str, Any]], source: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Merge per-match breakdowns into one season-level breakdown."""
    for metric, src in (source or {}).items():
        dst = target.setdefault(metric, {"metric": metric, "label": src.get("label") or _dashboard_display_key(metric), "total": 0, "success": 0, "failure": 0, "outcomes": {}, "value_types": {}, "sub_keys": {}, "events": []})
        for key in ("total", "success", "failure"):
            dst[key] += _dashboard_numeric(src.get(key, 0))
        for group in ("outcomes", "value_types", "sub_keys"):
            for item_key, item in (src.get(group) or {}).items():
                if group == "value_types":
                    item_dst = dst[group].setdefault(item_key, {"key": item_key, "label": item.get("label") or _dashboard_display_key(item_key), "count": 0, "success": 0, "failure": 0, "outcomes": {}})
                    for key in ("count", "success", "failure"): item_dst[key] += _dashboard_numeric(item.get(key, 0))
                    for outcome_key, outcome in (item.get("outcomes") or {}).items():
                        out_dst = item_dst["outcomes"].setdefault(outcome_key, {"key": outcome_key, "label": outcome.get("label") or _dashboard_display_key(outcome_key), "count": 0})
                        out_dst["count"] += _dashboard_numeric(outcome.get("count", 0))
                elif group == "sub_keys":
                    item_dst = dst[group].setdefault(item_key, {"key": item_key, "label": item.get("label") or _dashboard_display_key(item_key), "count": 0, "success": 0, "failure": 0, "outcomes": {}, "value_types": {}})
                    for key in ("count", "success", "failure"): item_dst[key] += _dashboard_numeric(item.get(key, 0))
                    for outcome_key, outcome in (item.get("outcomes") or {}).items():
                        out_dst = item_dst["outcomes"].setdefault(outcome_key, {"key": outcome_key, "label": outcome.get("label") or _dashboard_display_key(outcome_key), "count": 0})
                        out_dst["count"] += _dashboard_numeric(outcome.get("count", 0))
                    for type_key, type_row in (item.get("value_types") or {}).items():
                        type_dst = item_dst["value_types"].setdefault(type_key, {"key": type_key, "label": type_row.get("label") or _dashboard_display_key(type_key), "count": 0})
                        type_dst["count"] += _dashboard_numeric(type_row.get("count", 0))
                else:
                    item_dst = dst[group].setdefault(item_key, {"key": item_key, "label": item.get("label") or _dashboard_display_key(item_key), "count": 0})
                    item_dst["count"] += _dashboard_numeric(item.get("count", 0))
    return target

def _dashboard_event_view(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return a stable event view for heatmaps and activity timelines."""
    view = {
        "event_id": str(event.get("event_id") or event.get("eventId") or event.get("_id") or ""),
        "client_event_id": str(event.get("client_event_id") or event.get("clientEventId") or event.get("event_id") or ""),
        "player_id": event.get("player_id") or event.get("playerId"),
        "assignment_id": event.get("assignment_id") or event.get("assignmentId"),
        "match_id": event.get("match_id") or event.get("matchId"),
        "team_id": event.get("team_id") or event.get("teamId"),
        "team_side": event.get("team_side") or event.get("teamSide"),
        "team_name": event.get("team_name") or event.get("teamName"),
        "position": event.get("position") or event.get("player_position"),
        "sub_key": event.get("sub_key", event.get("subKey", "")),
        "metric": event.get("metric", event.get("metric_key", "")),
        "metric_key": event.get("metric_key", event.get("metric", "")),
        "event_type": event.get("event_type", event.get("eventType", "")),
        "outcome": event.get("outcome", "success"),
        "outcome_detail": event.get("outcome_detail", event.get("outcomeDetail", "")),
        "value_type": event.get("value_type", event.get("valueType", "")),
        "period": event.get("period", event.get("half", 1)),
        "elapsed_seconds": event.get("elapsed_seconds", event.get("elapsedSeconds", 0)),
        "clock": event.get("clock") or {"period": event.get("period", event.get("half", 1)), "elapsedSeconds": event.get("elapsed_seconds", event.get("elapsedSeconds", 0))},
        "minute": event.get("minute", event.get("match_minute", "")),
        "multiplier": event.get("multiplier", 1),
        "status": event.get("status", "accepted"),
        "heatmap_required": bool(event.get("heatmap_required", event.get("heatmapRequired", False))),
        "heatmap_recorded": bool(event.get("heatmap_recorded", event.get("heatmapRecorded", False))),
    }
    for key in (
        "location",
        "metadata",
        "attributes",
        "derived_contributions",
        "related_event_id",
        "recorded_at",
        "created_at",
        "updated_at",
    ):
        value = event.get(key)
        if value is None and key in {
            "attributes",
            "derived_contributions",
        }:
            value = event.get(
                "".join(
                    part.capitalize() if index else part
                    for index, part in enumerate(key.split("_"))
                )
            )
        if value is None and key == "related_event_id":
            value = event.get("relatedEventId")
        if value not in (None, "") and value != {}:
            view[key] = value
    return view


def _dashboard_numeric(value: Any) -> int | float:
    """Return a finite non-negative number for a dashboard stat value."""
    if isinstance(value, dict):
        value = value.get("success", value.get("value", 0))
    try:
        number = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    if number != number or number in (float("inf"), float("-inf")) or number < 0:
        return 0
    return int(number) if number.is_integer() else number


def _dashboard_stats_for_position(
    raw_stats: Optional[Dict[str, Any]],
    position: str,
) -> Dict[str, int | float]:
    """Project legacy or normalized stats into the tracker field contract."""
    raw = raw_stats if isinstance(raw_stats, dict) else {}
    fields = _dashboard_stat_fields(position)
    stats: Dict[str, int | float] = {field: 0 for field in fields}

    aliases = {
        "fouls_given": ("fouls_given", "fouls", "foulsGiven"),
        "fouls_won": ("fouls_won", "foulsWon"),
        "yellow_cards": ("yellow_cards", "yellowCards"),
        "red_cards": ("red_cards", "redCards"),
        "goals_conceded": ("goals_conceded", "goalsConceded"),
        "penalty_saves": ("penalty_saves", "penaltySaves"),
        "clean_sheets": ("clean_sheets", "cleanSheets"),
    }

    for field in fields:
        keys = aliases.get(field, (field,))
        for key in keys:
            if key in raw:
                stats[field] = _dashboard_numeric(raw[key])
                break

    if not _is_goalkeeper_position(position):
        goals = raw.get("goals", 0)
        if isinstance(goals, dict):
            stats["shot_goals"] = _dashboard_numeric(
                goals.get("shot", goals.get("shots", 0))
            )
            stats["header_goals"] = _dashboard_numeric(goals.get("header", 0))
            stats["penalty_goals"] = _dashboard_numeric(goals.get("penalty", 0))
            stats["goals"] = (
                stats["shot_goals"]
                + stats["header_goals"]
                + stats["penalty_goals"]
            )
        else:
            stats["goals"] = _dashboard_numeric(goals)
            for field, key in (
                ("shot_goals", "shot_goals"),
                ("header_goals", "header_goals"),
                ("penalty_goals", "penalty_goals"),
            ):
                if key in raw:
                    stats[field] = _dashboard_numeric(raw[key])
        for field, legacy_key in (
            ("shot_goals", "shotGoals"),
            ("header_goals", "headerGoals"),
            ("penalty_goals", "penaltyGoals"),
        ):
            if legacy_key in raw:
                stats[field] = _dashboard_numeric(raw[legacy_key])
    else:
        # Goalkeepers never inherit outfield goal breakdown fields.
        for field in ("goals", "shot_goals", "header_goals", "penalty_goals"):
            stats.pop(field, None)

    def set_from_components(field: str, *components: str) -> None:
        if not stats.get(field):
            stats[field] = sum(_dashboard_numeric(stats.get(key, 0)) for key in components)

    set_from_components(
        "passes",
        "passes_attempted",
        "successful_short_passes",
        "unsuccessful_short_passes",
        "successful_long_passes",
        "unsuccessful_long_passes",
    )
    set_from_components("dribbles", "successful_dribbles", "unsuccessful_dribbles")
    set_from_components("crosses", "successful_crosses", "unsuccessful_crosses")
    set_from_components("tackles", "tackles_won", "tackles_lost")
    set_from_components(
        "duels",
        "duels_won",
        "duels_lost",
        "aerial_duels_won",
        "aerial_duels_lost",
    )
    set_from_components("cards", "yellow_cards", "red_cards")
    set_from_components("big_chances", "big_chances_created", "big_chances_missed")
    set_from_components("substitutions", "substitution")
    set_from_components("possession_losses", "dispossessed")
    if not stats.get("shots_faced"):
        stats["shots_faced"] = sum(
            _dashboard_numeric(stats.get(key, 0))
            for key in ("shots_on_target_faced", "goals_conceded")
        )
    if not stats.get("distribution"):
        stats["distribution"] = sum(
            _dashboard_numeric(stats.get(key, 0))
            for key in ("successful_distributions", "unsuccessful_distributions")
        )

    return stats


def _dashboard_first_value(source: Any, *keys: str) -> Any:
    """Return the first meaningful value from a mapping or object."""
    if source is None:
        return ""
    for key in keys:
        value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
        if value not in (None, "") and not (
            isinstance(value, str)
            and value.strip().lower() in {"-", "—", "null", "undefined", "none", "n/a"}
        ):
            return value
    return ""


def _dashboard_minutes_played(
    player: Dict[str, Any],
    events: Optional[List[Dict[str, Any]]] = None,
) -> int | float:
    """Use persisted minutes first, then the last recorded action time.

    A missing duration is not evidence of a full match.  Returning 90 here
    used to turn a 15-minute appearance into a false full-match record.
    """
    participation = _dashboard_first_value(
        player,
        "participation_seconds_by_period",
        "participationSecondsByPeriod",
    )
    if isinstance(participation, (list, tuple)):
        total_seconds = sum(
            max(0, _dashboard_numeric(value)) for value in participation[:2]
        )
        return int(round(total_seconds / 60))

    explicit = _dashboard_first_value(
        player,
        "minutes_played",
        "minutesPlayed",
        "minutes",
        "minutes_on_pitch",
        "minutesOnPitch",
        "playing_minutes",
        "playingMinutes",
        "duration_minutes",
        "durationMinutes",
    )
    if explicit not in (None, ""):
        return max(0, int(round(_dashboard_numeric(explicit))))

    observed_minutes: List[float] = []
    for event in events or []:
        seconds = _dashboard_first_value(
            event,
            "elapsed_seconds",
            "elapsedSeconds",
            "elapsed",
            "match_seconds",
            "matchSeconds",
        )
        if seconds not in (None, ""):
            try:
                seconds_value = float(seconds)
                if seconds_value >= 0:
                    period = _dashboard_numeric(
                        _dashboard_first_value(event, "period", "half") or 1
                    )
                    # Tracker elapsed_seconds is half-relative.  Preserve
                    # first-half values exactly and offset second-half values.
                    observed_minutes.append(
                        seconds_value / 60
                        + (45 if period == 2 and seconds_value < 45 * 60 else 0)
                    )
                    continue
            except (TypeError, ValueError, OverflowError):
                pass

        minute = _dashboard_first_value(
            event,
            "minute",
            "match_minute",
            "matchMinute",
            "minute_played",
            "minutePlayed",
            "clock",
        )
        if minute in (None, ""):
            continue
        if isinstance(minute, (int, float)):
            if minute >= 0:
                observed_minutes.append(float(minute))
            continue
        text = str(minute).strip()
        clock_match = re.search(r"(?:(\d+)\s*[Hh]\s*)?(\d+)(?::(\d{1,2}))?", text)
        if clock_match:
            hours = float(clock_match.group(1) or 0)
            minutes = float(clock_match.group(2) or 0)
            seconds_part = float(clock_match.group(3) or 0)
            observed_minutes.append(hours * 60 + minutes + seconds_part / 60)

    return max(0, int(round(max(observed_minutes, default=0))))


def _dashboard_team_name(match: Dict[str, Any], side: str) -> str:
    """Read a team/club name from every tracker naming convention."""
    nested = match.get("match") if isinstance(match.get("match"), dict) else {}
    teams = match.get("teams") if isinstance(match.get("teams"), dict) else {}
    side_value = _dashboard_first_value(
        match,
        f"{side}_team_name",
        f"{side}TeamName",
        f"{side}_team",
        f"{side}Team",
        f"{side}_club_name",
        f"{side}ClubName",
        f"{side}_club",
        f"{side}Club",
    )
    if isinstance(side_value, dict):
        side_value = _dashboard_first_value(
            side_value, "name", "team_name", "teamName", "club_name", "clubName"
        )
    if not side_value:
        side_value = _dashboard_first_value(
            teams,
            side,
            f"{side}_team",
            f"{side}Team",
            f"{side}_club",
            f"{side}Club",
        )
    if isinstance(side_value, dict):
        side_value = _dashboard_first_value(
            side_value, "name", "team_name", "teamName", "club_name", "clubName"
        )
    if not side_value:
        side_value = _dashboard_first_value(
            nested,
            f"{side}_team_name",
            f"{side}TeamName",
            f"{side}_team",
            f"{side}Team",
            f"{side}_club",
            f"{side}Club",
        )
    text = str(side_value or "").strip()
    return "" if text.lower() in {"null", "undefined", "none", "n/a", "—"} else text


def _dashboard_score(match: Dict[str, Any], side: str) -> Any:
    """Read a score without confusing a valid zero with a missing value."""
    raw_score = match.get("score")
    score = raw_score if isinstance(raw_score, dict) else {}
    nested = match.get("match") if isinstance(match.get("match"), dict) else {}
    nested_score = nested.get("score") if isinstance(nested.get("score"), dict) else {}
    suffix = "home" if side == "home" else "away"
    value = _dashboard_first_value(
        match,
        f"{side}_score",
        f"{side}Score",
        f"{side}_goals",
        f"{side}Goals",
    )
    if value in (None, ""):
        value = _dashboard_first_value(score, suffix, f"{suffix}_score", f"{suffix}Score")
    if value in (None, ""):
        value = _dashboard_first_value(
            nested, f"{side}_score", f"{side}Score", f"{side}_goals", f"{side}Goals"
        )
    if value in (None, ""):
        value = _dashboard_first_value(
            nested_score, suffix, f"{suffix}_score", f"{suffix}Score"
        )
    if value in (None, "") and isinstance(raw_score, str):
        score_parts = re.search(r"(-?\d+)\s*[-:]\s*(-?\d+)", raw_score)
        if score_parts:
            value = score_parts.group(1 if side == "home" else 2)
    return value


def _dashboard_venue_fields(match: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten the tracker venue object for the stats-tab match card."""
    raw_venue = match.get("venue")
    venue = raw_venue if isinstance(raw_venue, dict) else {}

    def pick(*keys: str) -> Any:
        for key in keys:
            value = match.get(key)
            if isinstance(value, dict):
                value = _dashboard_first_value(
                    value, "name", "venue_name", "venueName", "stadium", "address"
                )
            if value not in (None, ""):
                return value
            value = venue.get(key)
            if value not in (None, ""):
                return value
        if isinstance(raw_venue, str) and raw_venue.strip():
            return raw_venue.strip() if "name" in keys or "stadium" in keys else ""
        return ""

    fields = {
        "venue_name": pick("venue_name", "venueName", "stadium", "name"),
        "venue_address": pick(
            "venue_address", "venueAddress", "stadium_address", "address", "street"
        ),
        "venue_lga": pick("venue_lga", "venueLGA", "lga", "local_government_area"),
        "venue_city": pick("venue_city", "venueCity", "city"),
        "venue_province": pick("venue_province", "venueProvince", "province"),
        "venue_county": pick("venue_county", "venueCounty", "county"),
        "venue_state": pick("venue_state", "venueState", "state"),
        "venue_country": pick("venue_country", "venueCountry", "country"),
    }
    fields["venue_full_address"] = ", ".join(
        dict.fromkeys(
            str(fields[key]).strip()
            for key in (
                "venue_address",
                "venue_lga",
                "venue_city",
                "venue_province",
                "venue_county",
                "venue_state",
                "venue_country",
            )
            if str(fields[key]).strip()
        )
    )
    return fields


def _dashboard_match_record(
    submission: Dict[str, Any],
    player: Dict[str, Any],
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Map one normalized tracker submission to the dashboard match contract."""
    match = submission.get("match") or {}
    match_details = match.get("details") if isinstance(match.get("details"), dict) else {}
    position = player.get("position", "")
    stats = _dashboard_stats_for_position(
        _stats_from_normalized_events(events, position),
        position,
    )
    event_views = [_dashboard_event_view(event) for event in events]
    home_score = _dashboard_score(match, "home")
    away_score = _dashboard_score(match, "away")
    player_category = _dashboard_normalize_category(
        _dashboard_first_value(
            player,
            "player_category",
            "playerCategory",
            "category",
            "playing_category",
            "playingCategory",
        )
        or _dashboard_first_value(
            match, "player_category", "playerCategory", "category"
        )
        or _dashboard_first_value(
            submission, "player_category", "playerCategory", "category"
        )
    )
    player_level = _dashboard_first_value(
        player,
        "player_level",
        "playerLevel",
        "playing_level",
        "playingLevel",
        "level",
    )
    if not player_level:
        player_level = _dashboard_first_value(
            submission,
            "player_level",
            "playerLevel",
            "playing_level",
            "playingLevel",
            "level",
        )
    match_category = _dashboard_first_value(
        match, "match_category", "matchCategory", "category", "competition_level"
    ) or _dashboard_first_value(
        submission, "match_category", "matchCategory", "competition_level"
    )
    match_level = _dashboard_first_value(
        match, "match_level", "matchLevel", "level", "competition_level"
    ) or _dashboard_first_value(
        submission, "match_level", "matchLevel", "competition_level", "level"
    )
    available_metric_keys = _dashboard_available_metric_keys(
        stats, events, position, player_category
    )
    metric_breakdown = _dashboard_metric_breakdown(events, position, player_category)
    result = (
        _dashboard_first_value(match, "result", "match_result", "matchResult")
        or ""
    )
    venue_fields = _dashboard_venue_fields(match)
    for source_key, output_key in (("venue", "venue_name"), ("venueStadium", "venue_name"), ("venueAddress", "venue_address"), ("venueLGA", "venue_lga"), ("venueState", "venue_state"), ("venueCountry", "venue_country"), ("venueGpsLat", "venue_gps_lat"), ("venueGpsLon", "venue_gps_lon"), ("gpsLat", "gps_lat"), ("gpsLon", "gps_lon")):
        if not venue_fields.get(output_key) and match_details.get(source_key) not in (None, ""):
            venue_fields[output_key] = match_details.get(source_key)
    venue_fields.setdefault("venue_name", "")
    venue_fields.setdefault("venue_address", "")
    venue_fields.setdefault("venue_lga", "")
    venue_fields.setdefault("venue_state", "")
    venue_fields.setdefault("venue_country", "")
    goal_breakdown = {
        "shot": stats.get("shot_goals", 0),
        "header": stats.get("header_goals", 0),
        "penalty": stats.get("penalty_goals", 0),
    }
    if _is_goalkeeper_position(position) or not stats.get("goals", 0):
        goal_breakdown = None

    return {
        "_id": str(submission.get("_id", "")),
        "submission_id": str(submission.get("_id", "")),
        "player_id": player.get("player_id", ""),
        "player_name": player.get("player_name") or player.get("name", ""),
        "name": player.get("player_name") or player.get("name", ""),
        "club": player.get("club") or player.get("team_name") or player.get("teamName", ""),
        "team_id": player.get("team_id") or player.get("teamId"),
        "team_side": player.get("team_side") or player.get("teamSide") or player.get("team"),
        "team_name": player.get("team_name") or player.get("teamName") or player.get("club", ""),
        "assignment_id": player.get("assignment_id") or player.get("assignmentId"),
        "jersey_number": player.get("jersey_number") if player.get("jersey_number") is not None else player.get("jerseyNumber"),
        "main_position": player.get("main_position") or player.get("mainPosition") or position,
        "position_options": player.get("position_options") or player.get("positionOptions") or [position],
        "position_changed": bool(player.get("position_changed", player.get("positionChanged", False))),
        "position": position,
        "player_position": position,
        "player_category": player_category,
        "playerCategory": player_category,
        "player_level": player_level,
        "playerLevel": player_level,
        "match_category": match_category,
        "matchCategory": match_category,
        "match_level": match_level,
        "matchLevel": match_level,
        "available_metric_keys": available_metric_keys,
        "availableMetricKeys": available_metric_keys,
        "metric_sections": {
            section: list(metrics)
            for section, metrics in _DASHBOARD_TRACKER_METRICS_BY_SECTION.items()
            if _dashboard_category_policy(player_category)["sections"] is None
            or section in _dashboard_category_policy(player_category)["sections"]
        },
        "home_team": _dashboard_team_name(match, "home"),
        "away_team": _dashboard_team_name(match, "away"),
        "home_team_name": _dashboard_team_name(match, "home"),
        "away_team_name": _dashboard_team_name(match, "away"),
        "home_club": _dashboard_team_name(match, "home"),
        "away_club": _dashboard_team_name(match, "away"),
        "date": (
            match.get("match_date")
            or match.get("date")
            or match_details.get("matchDate")
            or match_details.get("date")
            or submission.get("match_date")
            or submission.get("submitted_at")
        ),
        "match_date": (
            match.get("match_date")
            or match.get("date")
            or match_details.get("matchDate")
            or match_details.get("date")
            or submission.get("match_date")
            or submission.get("submitted_at")
        ),
        "match_time": match.get("match_time") or match.get("time") or match_details.get("matchTime") or match_details.get("time", ""),
        "match_type": match.get("match_type") or match.get("matchType") or match_details.get("matchType", ""),
        "match_category": match.get("match_category") or match.get("matchCategory") or match_details.get("matchCategory", ""),
        "match_level": match.get("match_level") or match.get("matchLevel") or match_details.get("playerLevel") or match_details.get("matchLevel", ""),
        "status": match.get("status") or match.get("match_status") or match.get("matchStatus", ""),
        "approval_status": submission.get("status", ""),
        "result": result,
        "home_score": home_score,
        "away_score": away_score,
        "score": {"home": home_score, "away": away_score},
        "competition": match.get("competition") or match.get("league") or match.get("match_type") or match_details.get("competition") or "",
        "home_team_id": (match.get("teams") or {}).get("homeId") if isinstance(match.get("teams"), dict) else None,
        "away_team_id": (match.get("teams") or {}).get("awayId") if isinstance(match.get("teams"), dict) else None,
        **venue_fields,
        "venue": venue_fields.get("venue_name", ""),
        "minutes_played": _dashboard_minutes_played(player, events),
        "participation_seconds_by_period": player.get(
            "participation_seconds_by_period",
            player.get("participationSecondsByPeriod"),
        ),
        "role": position or player.get("status", ""),
        "player_status": player.get("status", ""),
        "performance_score": player.get("performance_score", 0),
        "stats": stats,
        "goal_breakdown": goal_breakdown,
        "metric_breakdown": metric_breakdown,
        "metricBreakdown": metric_breakdown,
        "match": _ser(match) or match,
        "match_id": str(match.get("match_id") or match.get("id") or match.get("_id") or submission.get("match_id") or ""),
        "assignment_id": player.get("assignment_id") or submission.get("assignment_id"),
        "submission_trigger": submission.get("submission_trigger") or submission.get("submissionTrigger"),
        "tracking_type": submission.get("tracking_type") or submission.get("trackingType"),
        "schema_version": submission.get("schema_version") or submission.get("schemaVersion"),
        "supervisor_id": submission.get("supervisor_id") or submission.get("supervisorId"),
        "geo": submission.get("geo") or {
            "status": submission.get("geo_status") or submission.get("geoStatus"),
            "lat": submission.get("geo_lat") if submission.get("geo_lat") is not None else submission.get("geoLat"),
            "lon": submission.get("geo_lon") if submission.get("geo_lon") is not None else submission.get("geoLon"),
        },
        # Keep the complete event object in every read alias. This preserves
        # metric, outcome, period, elapsed time, recorded time, and location
        # for the inline stats-tab filters.
        "events": event_views,
        "heatmap_events": event_views,
        "heatmap_data": [
            event for event in event_views if "location" in event
        ],
        "action_timeline": event_views,
    }


async def _load_normalized_player_matches(
    uid: str,
    pid_val: str,
    position: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Read approved tracker submissions for a player.

    The tracker stores one player row per submitted player and one event row
    per action.  Join those rows here without mutating or duplicating them.
    """
    if (
        stat_submissions_collection is None
        or stat_submission_players_collection is None
        or stat_events_collection is None
    ):
        return []

    player_ids = list({str(value) for value in (uid, pid_val) if value})
    if not player_ids:
        return []

    player_rows = await stat_submission_players_collection.find(
        {"player_id": {"$in": player_ids}}
    ).sort("player_order", 1).limit(max(1, limit * 3)).to_list(length=max(1, limit * 3))
    if not player_rows:
        return []

    player_by_submission: Dict[str, Dict[str, Any]] = {}
    player_row_ids: List[Any] = []
    for player in player_rows:
        submission_id = str(player.get("submission_id", ""))
        if not submission_id or submission_id in player_by_submission:
            continue
        player_by_submission[submission_id] = player
        if player.get("_id") is not None:
            player_row_ids.append(player["_id"])

    if not player_by_submission:
        return []

    submission_ids = [
        player.get("submission_id")
        for player in player_by_submission.values()
        if player.get("submission_id") is not None
    ]
    submissions = await stat_submissions_collection.find(
        {
            "_id": {"$in": submission_ids},
            "status": {
                "$in": [
                    "approved",
                    "verified",
                    "completed",
                    "published",
                ]
            },
        }
    ).sort("submitted_at", -1).limit(max(1, limit)).to_list(length=max(1, limit))
    if not submissions:
        return []

    event_rows = await stat_events_collection.find(
        {"submission_player_id": {"$in": player_row_ids}}
    ).sort("event_order", 1).to_list(length=max(1, limit * 100))
    events_by_player: Dict[str, List[Dict[str, Any]]] = {}
    seen_events_by_player: Dict[str, set[str]] = {}
    for event in event_rows:
        player_id = str(event.get("submission_player_id", ""))
        if not player_id:
            continue
        event_id = str(event.get("event_id") or event.get("client_event_id") or event.get("_id") or "").strip()
        seen = seen_events_by_player.setdefault(player_id, set())
        if event_id and event_id in seen:
            continue
        if event_id:
            seen.add(event_id)
        events_by_player.setdefault(player_id, []).append(event)

    records: List[Dict[str, Any]] = []
    for submission in submissions:
        submission_key = str(submission.get("_id", ""))
        player = player_by_submission.get(submission_key)
        if player is None:
            continue
        events = events_by_player.get(str(player.get("_id", "")), [])
        record = _dashboard_match_record(submission, player, events)
        records.append(_ser(record) or record)
    return records


async def _load_legacy_player_matches(
    uid: str,
    pid_val: str,
    position: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Read the pre-normalized player_stats collection for compatibility."""
    if player_stats_collection is None:
        return []

    stats_docs = await player_stats_collection.find(
        {
            "$or": [{"player_id": uid}, {"player_id": pid_val}],
            "status": {"$in": ["approved", "verified", "completed"]},
        }
    ).sort("match_date", -1).limit(max(1, min(limit, 200))).to_list(
        length=max(1, min(limit, 200))
    )

    match_data: List[Dict[str, Any]] = []
    for stat_doc in stats_docs:
        raw_stats = stat_doc.get("stats") or {}
        if not raw_stats:
            skip_keys = {
                "_id", "player_id", "scout_id", "home_team", "away_team",
                "match_date", "date", "created_at", "updated_at", "status",
                "reference_id", "request_id", "competition", "venue",
                "venue_name", "venue_address", "venue_lga", "venue_city",
                "venue_province", "venue_county", "venue_state", "venue_country",
                "venue_full_address", "match_time", "home_team_name",
                "away_team_name", "home_club", "away_club", "score",
                "result", "home_score", "away_score", "minutes_played",
                "role", "performance_score", "goal_breakdown",
                "events", "heatmap_events", "heatmap_data", "action_timeline",
            }
            raw_stats = {
                key: value
                for key, value in stat_doc.items()
                if key not in skip_keys
            }
        raw_stats = _dashboard_stats_for_position(raw_stats, position)

        performance = stat_doc.get("performance_score")
        if not performance and calculate_performance_score and raw_stats:
            performance = calculate_performance_score(raw_stats, position)

        legacy_events = stat_doc.get("events") or stat_doc.get("action_timeline") or []
        legacy_event_views = [
            _dashboard_event_view(event) if isinstance(event, dict) else event
            for event in legacy_events
        ]
        legacy_category = _dashboard_normalize_category(
            _dashboard_first_value(
                stat_doc,
                "player_category",
                "playerCategory",
                "category",
                "playing_category",
                "playingCategory",
            )
        )
        legacy_level = _dashboard_first_value(
            stat_doc,
            "player_level",
            "playerLevel",
            "playing_level",
            "playingLevel",
            "level",
        )
        legacy_match_category = _dashboard_first_value(
            stat_doc,
            "match_category",
            "matchCategory",
            "competition_level",
        )
        legacy_match_level = _dashboard_first_value(
            stat_doc,
            "match_level",
            "matchLevel",
            "competition_level",
            "level",
        )
        legacy_event_dicts = [event for event in legacy_events if isinstance(event, dict)]
        legacy_available_metric_keys = _dashboard_available_metric_keys(
            raw_stats, legacy_event_dicts, position, legacy_category
        )
        legacy_metric_breakdown = _dashboard_metric_breakdown(legacy_event_dicts, position, legacy_category)
        venue_fields = _dashboard_venue_fields(stat_doc)
        match_data.append(
            {
                "_id": str(stat_doc.get("_id", "")),
                "player_category": legacy_category,
                "playerCategory": legacy_category,
                "player_level": legacy_level,
                "playerLevel": legacy_level,
                "match_category": legacy_match_category,
                "matchCategory": legacy_match_category,
                "match_level": legacy_match_level,
                "matchLevel": legacy_match_level,
                "available_metric_keys": legacy_available_metric_keys,
                "availableMetricKeys": legacy_available_metric_keys,
                "home_team": stat_doc.get("home_team", ""),
                "away_team": stat_doc.get("away_team", ""),
                "home_team_name": stat_doc.get("home_team_name") or stat_doc.get("home_team", ""),
                "away_team_name": stat_doc.get("away_team_name") or stat_doc.get("away_team", ""),
                "date": stat_doc.get("match_date") or stat_doc.get("date"),
                "match_date": stat_doc.get("match_date") or stat_doc.get("date"),
                "match_time": stat_doc.get("match_time", ""),
                "result": stat_doc.get("result", ""),
                "home_score": stat_doc.get("home_score"),
                "away_score": stat_doc.get("away_score"),
                "score": {
                    "home": stat_doc.get("home_score"),
                    "away": stat_doc.get("away_score"),
                },
                "competition": stat_doc.get("competition", ""),
                **venue_fields,
                "venue": venue_fields.get("venue_name") or stat_doc.get("venue", ""),
                "minutes_played": _dashboard_minutes_played(stat_doc, legacy_events),
                "role": stat_doc.get("role", ""),
                "performance_score": performance,
                "stats": raw_stats,
                "metric_breakdown": legacy_metric_breakdown,
                "metricBreakdown": legacy_metric_breakdown,
                "match_id": str(stat_doc.get("match_id") or stat_doc.get("matchId") or stat_doc.get("_id", "")),
                "assignment_id": stat_doc.get("assignment_id") or stat_doc.get("assignmentId"),
                "match": _ser(stat_doc.get("match") or {}) or {},
                "goal_breakdown": (
                    stat_doc.get("goal_breakdown")
                    if not _is_goalkeeper_position(position)
                    and raw_stats.get("goals", 0)
                    else None
                ),
                "events": legacy_event_views,
                "heatmap_events": legacy_event_views,
                "heatmap_data": (
                    stat_doc.get("heatmap_data")
                    or [event for event in legacy_event_views if "location" in event]
                ),
                "action_timeline": legacy_event_views,
            }
        )
    return match_data


async def _load_player_matches(
    uid: str,
    pid_val: str,
    position: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Use tracker submissions first and legacy stats only when necessary."""
    normalized_matches = await _load_normalized_player_matches(
        uid, pid_val, position, limit
    )
    if normalized_matches:
        return normalized_matches
    return await _load_legacy_player_matches(uid, pid_val, position, limit)


async def _active_content_manager_for_player(player: dict) -> Optional[dict]:
    """Resolve the player's active Content Manager relationship, if any."""
    if content_manager_contracts_collection is None:
        return None
    ids = [
        str(player.get("player_id") or ""),
        str(player.get("user_id") or ""),
        str(player.get("_id") or ""),
    ]
    ids = [v for v in ids if v]
    if not ids:
        return None
    return await content_manager_contracts_collection.find_one({
        "$or": [
            {"player_id": {"$in": ids}},
            {"player_user_id": {"$in": ids}},
        ],
        "status": {"$in": ["Active", "active"]},
    }, sort=[("updated_at", -1), ("created_at", -1)])


async def _insert_notification(target: dict, *, notif_type: str, title: str, message: str,
                               reference_id: Optional[str] = None, extra: Optional[dict] = None) -> None:
    if notifications_collection is None:
        return
    doc = {
        "unique_id": str(target.get("unique_id") or target.get("user_id") or target.get("player_id") or target.get("manager_id") or ""),
        "user_id": str(target.get("user_id") or target.get("manager_id") or target.get("unique_id") or ""),
        "player_id": str(target.get("player_id") or "") if target.get("player_id") else None,
        "manager_id": str(target.get("manager_id") or "") if target.get("manager_id") else None,
        "user_type": target.get("user_type") or "player",
        "type": notif_type,
        "title": title,
        "message": message,
        "reference_id": reference_id,
        "read": False,
        "created_at": _now(),
    }
    if extra:
        doc.update(extra)
    # Do not persist null identity fields; this keeps existing notification
    # filters compatible with older documents.
    doc = {k: v for k, v in doc.items() if v is not None}
    await notifications_collection.insert_one(doc)


async def _ensure_player_stats_status_notifications(player: dict) -> None:
    """Backfill cross-dashboard notifications when the tracker changes a request status."""
    if stats_requests_collection is None or notifications_collection is None:
        return
    pid = _pid(player)
    uid = str(player.get("user_id") or pid)
    reqs = await stats_requests_collection.find({
        "$or": [{"player_id": pid}, {"player_id": uid}],
        "status": {"$in": [
            "Assigned", "assigned", "In Progress", "in_progress", "Completed", "completed",
            "Verified", "verified", "Approved", "approved", "Rejected", "rejected", "Cancelled", "cancelled",
        ]},
    }).sort("updated_at", -1).limit(50).to_list(length=50)
    for req in reqs:
        status = str(req.get("status") or "").strip().lower()
        ref = str(req.get("reference_id") or req.get("request_id") or req.get("_id") or "")
        if not ref or not status:
            continue
        marker = f"stats_request_status:{ref}:{status}"
        exists = await notifications_collection.find_one({
            "$or": [{"player_id": pid}, {"unique_id": pid}, {"unique_id": uid}],
            "type": "stats_request_status",
            "event_key": marker,
        })
        if exists:
            continue
        labels = {
            "assigned": ("Stats Request Assigned", "Your stats-tracking request has been assigned for processing."),
            "in_progress": ("Stats Tracking In Progress", "Your requested match statistics are now being processed."),
            "completed": ("Stats Tracking Completed", "Your requested match statistics have been completed and your match result is now available."),
            "verified": ("Match Statistics Verified", "Your match statistics have been verified and are now available in your Match Centre and Stats dashboard."),
            "approved": ("Match Statistics Approved", "Your requested match statistics have been approved and are now available in your Match Centre and Stats dashboard."),
            "rejected": ("Stats Request Rejected", "Your stats-tracking request was rejected. Review the request status for details."),
            "cancelled": ("Stats Request Cancelled", "Your stats-tracking request was cancelled. Any applicable token refund is reflected in your transaction history."),
        }
        title, message = labels.get(status, ("Stats Request Updated", f"Your stats request {ref} was updated to {req.get('status')}."))
        await _insert_notification(
            {"player_id": pid, "unique_id": pid, "user_id": pid_val, "user_type": "player"},
            notif_type="stats_request_status", title=title, message=message,
            reference_id=ref, extra={"event_key": marker, "request_status": req.get("status")},
        )


# ============================================================
# ENDPOINT: GET /player/{uid}/profile
# ============================================================

# ============================================================
# END: MODULE-SPECIFIC HELPERS

# ============================================================
# START: API ROUTES
# ============================================================

@router.get("/player/{uid}/profile")
async def get_player_profile(uid: str, request: Request):
    """Return the player's full profile document."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        serialized = _ser(doc) or {}
        serialized.pop("password", None)
        serialized.pop("hashed_password", None)
        serialized["achievements"] = _normalize_achievement_list(serialized.get("achievements"))
        serialized.setdefault("player_id", _pid(doc))
        serialized.setdefault("user_id", _pid(doc))
        serialized.setdefault("unique_id", _pid(doc))

        # Flatten settings.* subdocument so the frontend can read fields
        # (e.g. dob_visible, notif_email_contract) at the document root level
        # without needing to navigate the nested "settings" key.
        embedded_settings = serialized.get("settings") or {}
        if isinstance(embedded_settings, dict):
            # Write each settings key to root if not already present there
            for _sk, _sv in embedded_settings.items():
                if _sk not in ("updated_at",) and _sk not in serialized:
                    serialized[_sk] = _sv
            # Explicitly promote the fields the frontend init code reads
            for _promote in ("dob_visible", "notif_email_contract",
                             "notif_email_token", "notif_inapp_stats"):
                if _promote not in serialized and _promote in embedded_settings:
                    serialized[_promote] = embedded_settings[_promote]

        return JSONResponse({"player": serialized, **serialized})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_profile error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/stats/summary
# ============================================================

@router.get("/player/{uid}/stats/summary")
async def get_player_stats_summary(uid: str, request: Request):
    """Aggregate season stats and return match-by-match data."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        position = (
            doc.get("preferredPosition")
            or doc.get("preferred_position")
            or doc.get("position")
            or ""
        )
        player_category = _dashboard_normalize_category(
            _dashboard_first_value(
                doc,
                "player_category",
                "playerCategory",
                "playing_category",
                "playingCategory",
                "category",
            )
        )
        player_level = _dashboard_first_value(
            doc,
            "player_level",
            "playerLevel",
            "playing_level",
            "playingLevel",
            "level",
        )
        match_data = await _load_player_matches(uid, pid_val, position, 200)

        if not match_data:
            empty_season_stats = {
                field: 0 for field in _dashboard_stat_fields(position)
            }
            empty_season_stats["minutes_played_total"] = 0
            empty_season_stats["matches_started"] = 0
            return JSONResponse({
                "summary": {
                    "matchesPlayed": 0,
                    "matches_played": 0,
                    "matchesStarted": 0,
                    "matches_started": 0,
                    "averageRating": None,
                    "average_rating": None,
                    "totalGoals": 0,
                    "totalAssists": 0,
                    "minutesPlayed": 0,
                    "minutes_played": 0,
                    "position": position,
                    "positionGroup": (
                        "Goalkeeper"
                        if _is_goalkeeper_position(position)
                        else "Outfield"
                    ),
                    "playerCategory": player_category,
                    "player_category": player_category,
                    "playerLevel": player_level,
                    "player_level": player_level,
                    "availableMetricKeys": [],
                    "available_metric_keys": [],
                    "availableStatFields": list(_dashboard_stat_fields(position)),
                    "metricBreakdown": {},
                    "metric_breakdown": {},
                },
                "seasonStats": empty_season_stats,
                "seasonMetricBreakdown": {},
                "season_metric_breakdown": {},
                "season_stats": empty_season_stats,
                "matchData": [],
                "match_data": [],
                "matches": [],
            })

        total_rating = 0.0
        rated_count = 0

        for match in match_data:
            performance = match.get("performance_score")
            if performance:
                total_rating += performance
                rated_count += 1

        season_stats: Dict[str, Any] = {
            field: 0 for field in _dashboard_stat_fields(position)
        }
        total_minutes = 0
        matches_started = 0
        for match in match_data:
            match_stats = _dashboard_stats_for_position(
                match.get("stats"), position
            )
            for field, value in match_stats.items():
                season_stats[field] = round(
                    season_stats.get(field, 0) + _dashboard_numeric(value),
                    2,
                )
            minutes = _dashboard_numeric(match.get("minutes_played", 0))
            total_minutes += minutes
            status = str(
                match.get("player_status")
                or match.get("sub_status")
                or match.get("status")
                or ""
            ).lower()
            if status in {"starting", "starter", "started", "full_match"}:
                matches_started += 1

        season_stats["minutes_played_total"] = total_minutes
        season_stats["matches_started"] = matches_started

        season_metric_breakdown: Dict[str, Dict[str, Any]] = {}
        for match in match_data:
            _dashboard_merge_metric_breakdowns(season_metric_breakdown, match.get("metric_breakdown") or match.get("metricBreakdown") or {})

        avg_rating = round(total_rating / rated_count, 2) if rated_count else None
        available_metric_keys = sorted(
            {
                metric
                for match in match_data
                for metric in (
                    match.get("availableMetricKeys")
                    or match.get("available_metric_keys")
                    or []
                )
            }
        )

        summary = {
            "matchesPlayed": len(match_data),
            "matches_played": len(match_data),
            "matchesStarted": matches_started,
            "matches_started": matches_started,
            "averageRating": avg_rating,
            "average_rating": avg_rating,
            "totalGoals": season_stats.get("goals", 0),
            "totalAssists": season_stats.get("assists", 0),
            "minutesPlayed": total_minutes,
            "minutes_played": total_minutes,
            "position": position,
            "positionGroup": "Goalkeeper" if _is_goalkeeper_position(position) else "Outfield",
            "playerCategory": player_category,
            "player_category": player_category,
            "playerLevel": player_level,
            "player_level": player_level,
            "availableMetricKeys": available_metric_keys,
            "available_metric_keys": available_metric_keys,
            "availableStatFields": list(_dashboard_stat_fields(position)),
            "metricBreakdown": season_metric_breakdown,
            "metric_breakdown": season_metric_breakdown,
        }

        return JSONResponse({
            "summary": summary,
            "seasonStats": season_stats,
            "seasonMetricBreakdown": season_metric_breakdown,
            "season_metric_breakdown": season_metric_breakdown,
            "season_stats": season_stats,
            "matchData": match_data,
            "match_data": match_data,
            "matches": match_data,
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_stats_summary error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/matches
# ============================================================

@router.get("/player/{uid}/matches")
async def get_player_matches(uid: str, request: Request, limit: int = 50):
    """Return completed match history for this player."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        position = (doc.get("preferredPosition") or doc.get("preferred_position")
                    or doc.get("position") or "")

        match_data = await _load_player_matches(
            uid,
            pid_val,
            position,
            max(1, min(limit, 200)),
        )

        return JSONResponse({"matches": match_data, "match_data": match_data})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_matches error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/upcoming-fixtures
# ============================================================

@router.get("/player/{uid}/upcoming-fixtures")
async def get_upcoming_fixtures(uid: str, request: Request):
    """Return future player fixtures from pending tracking requests and scheduled fixtures."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        today = _now().date()
        fixtures: list = []

        pending_reqs = await stats_requests_collection.find({
            "$or": [{"player_id": uid}, {"player_id": pid_val}],
            "status": {"$in": ["Pending", "Assigned", "In Progress", "pending", "assigned", "in_progress"]},
        }).sort("match_date", 1).limit(50).to_list(length=50)
        for r in pending_reqs:
            raw_date = r.get("match_date") or r.get("date")
            keep = True
            if raw_date:
                try:
                    parsed = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
                    keep = parsed >= today
                except Exception:
                    keep = True
            if not keep:
                continue
            fixtures.append({
                "_id": str(r.get("_id", "")),
                "home_team": r.get("home_team") or r.get("homeTeam", ""),
                "away_team": r.get("away_team") or r.get("awayTeam", ""),
                "date": raw_date,
                "match_date": raw_date,
                "match_time": r.get("match_time", ""),
                "venue": r.get("venue_address") or r.get("venue", ""),
                "competition": r.get("match_type", ""),
                "status": r.get("status", "Pending"),
                "reference_id": r.get("reference_id", ""),
                "source": "stats_request",
                "token_cost": r.get("token_cost", 0),
            })

        if match_fixtures_collection is not None:
            extra = await match_fixtures_collection.find({
                "$or": [{"player_id": uid}, {"player_id": pid_val}],
                "status": {"$nin": ["Completed", "completed", "Cancelled", "cancelled", "Rejected", "rejected"]},
            }).sort("match_date", 1).limit(50).to_list(length=50)
            existing_refs = {str(f.get("reference_id")) for f in fixtures if f.get("reference_id")}
            for f in extra:
                raw_date = f.get("match_date") or f.get("date")
                if raw_date:
                    try:
                        if datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date() < today:
                            continue
                    except Exception:
                        pass
                ref = str(f.get("reference_id") or f.get("request_id") or "")
                if ref and ref in existing_refs:
                    continue
                fixtures.append({
                    "_id": str(f.get("_id", "")),
                    "home_team": f.get("home_team", ""),
                    "away_team": f.get("away_team", ""),
                    "date": raw_date,
                    "match_date": raw_date,
                    "match_time": f.get("match_time") or f.get("time", ""),
                    "venue": f.get("venue", ""),
                    "competition": f.get("competition", ""),
                    "status": f.get("status", "Scheduled"),
                    "reference_id": ref,
                    "source": "fixture",
                })
        fixtures.sort(key=lambda f: str(f.get("match_date") or f.get("date") or "9999"))
        return JSONResponse({"fixtures": fixtures[:50], "upcoming_fixtures": fixtures[:50]})
    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_upcoming_fixtures error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/tokens
# ============================================================

@router.get("/player/{uid}/tokens")
async def get_player_tokens(uid: str, request: Request):
    """Return token balance, locked amount, and available amount."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        token_doc = await player_tokens_collection.find_one(
            {"$or": [{"player_id": uid}, {"player_id": pid_val}]}
        )

        pending_reqs = await stats_requests_collection.find(
            {
                "$or": [{"player_id": uid}, {"player_id": pid_val}],
                "status": {"$in": ["Pending", "Assigned", "pending", "assigned"]},
                "$and": [{
                    "$or": [
                        {"token_deducted": {"$ne": True}},
                        {"token_deducted": {"$exists": False}},
                    ]
                }],
            },
            {"token_cost": 1},
        ).to_list(length=200)
        # Legacy/player-dashboard requests reserve tokens; content-manager
        # requests mark token_deducted=True and therefore must not be locked twice.
        locked = sum(int(r.get("token_cost", 0)) for r in pending_reqs)

        balance = 0
        expiry = None
        if token_doc:
            balance = int(token_doc.get("balance", 0))
            raw_expiry = token_doc.get("expiry_date")
            expiry = MongoSerializer.serialize_value(raw_expiry) if MongoSerializer and raw_expiry else None

        return JSONResponse({
            "tokens": {
                "balance": balance,
                "locked": locked,
                "available": max(0, balance - locked),
                "expiry_date": expiry,
            },
            "balance": balance,
            "locked": locked,
            "available": max(0, balance - locked),
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_tokens error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/notifications
# ============================================================

@router.get("/player/{uid}/notifications")
async def get_player_notifications(uid: str, request: Request, limit: int = 100):
    """Return notifications for this player, newest first."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        await _ensure_player_stats_status_notifications(doc)

        notifs = await notifications_collection.find(
            {"$or": [
                {"unique_id": uid}, {"unique_id": pid_val},
                {"player_id": uid}, {"player_id": pid_val},
            ]}
        ).sort("created_at", -1).limit(max(1, min(limit, 200))).to_list(length=200)

        return JSONResponse({"notifications": _ser_list(notifs)})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_notifications error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: PATCH /player/{uid}/notifications/read-all
# NOTE: defined before /{notif_id}/read to avoid path shadowing
# ============================================================

@router.patch("/player/{uid}/notifications/read-all")
async def mark_all_notifications_read(uid: str, request: Request):
    """Mark every notification for this player as read."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        pid_val = _pid(doc) if doc else uid

        await notifications_collection.update_many(
            {"$or": [
                {"unique_id": uid}, {"unique_id": pid_val},
                {"player_id": uid}, {"player_id": pid_val},
            ]},
            {"$set": {"read": True, "read_at": _now()}},
        )
        return JSONResponse({"success": True})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("mark_all_notifications_read error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: PATCH /player/{uid}/notifications/{notif_id}/read
# ============================================================

@router.patch("/player/{uid}/notifications/{notif_id}/read")
async def mark_notification_read(uid: str, notif_id: str, request: Request):
    """Mark a single notification as read."""
    try:
        await _require_player_auth(request, uid)

        try:
            filt: dict = {"_id": ObjectId(notif_id)}
        except Exception:
            filt = {"$or": [{"_id": notif_id}, {"id": notif_id}]}

        await notifications_collection.update_one(
            filt, {"$set": {"read": True, "read_at": _now()}}
        )
        return JSONResponse({"success": True})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("mark_notification_read error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: DELETE /player/{uid}/notifications/{notif_id}
# ============================================================

@router.delete("/player/{uid}/notifications/{notif_id}")
async def delete_notification(uid: str, notif_id: str, request: Request):
    """Delete a notification."""
    try:
        await _require_player_auth(request, uid)

        try:
            filt: dict = {"_id": ObjectId(notif_id)}
        except Exception:
            filt = {"$or": [{"_id": notif_id}, {"id": notif_id}]}

        await notifications_collection.delete_one(filt)
        return JSONResponse({"success": True})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("delete_notification error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/content-manager-contracts
# ============================================================

@router.get("/player/{uid}/content-manager-contracts")
async def get_player_content_manager_contracts(uid: str, request: Request):
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        cursor = content_manager_contracts_collection.find({"$or": [{"player_id": uid}, {"player_id": pid_val}, {"player_user_id": uid}, {"player_user_id": pid_val}]})
        docs = await cursor.sort("created_at", -1).limit(50).to_list(length=50)
        return JSONResponse({"success": True, "contracts": _ser_list(docs)})
    except HTTPException:
        raise
    except Exception as e:
        if logger: logger.exception("get_player_content_manager_contracts error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/content-manager-contracts/respond
# ============================================================

@router.post("/player/{uid}/content-manager-contracts/respond")
async def respond_content_manager_contract(uid: str, body: ContentManagerContractRespondBody, request: Request):
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc: raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        contract = await content_manager_contracts_collection.find_one({"contract_id":body.contract_id,"$or":[{"player_id":uid},{"player_id":pid_val},{"player_user_id":uid},{"player_user_id":pid_val}]})
        if not contract: raise HTTPException(status_code=404, detail="Content management agreement not found")
        if body.action not in {"accept","decline"}: raise HTTPException(status_code=400, detail="Action must be accept or decline")
        if str(contract.get("status","")).lower()!="pending": raise HTTPException(status_code=400, detail="This agreement is no longer pending")
        now=_now()
        if body.action=="accept":
            stored=str(contract.get("verification_code") or "")
            if len(body.code or "")!=12: raise HTTPException(status_code=400, detail="12-character verification code required")
            if stored and body.code.upper()!=stored.upper(): raise HTTPException(status_code=400, detail="Verification code does not match")
            # Only one active content manager relationship may exist at a time.
            others=await content_manager_contracts_collection.find({"$or":[{"player_id":uid},{"player_id":pid_val}],"status":{"$in":["Pending","pending","Active","active"]},"_id":{"$ne":contract["_id"]}}).to_list(length=200)
            if others:
                ids=[x["_id"] for x in others]
                await content_manager_contracts_collection.update_many({"_id":{"$in":ids},"status":{"$in":["Active","active"]}},{"$set":{"status":"Terminated","terminated_by":"system","termination_reason":"player_accepted_content_manager_relationship","terminated_at":now,"updated_at":now}})
                await content_manager_contracts_collection.update_many({"_id":{"$in":ids},"status":{"$in":["Pending","pending"]}},{"$set":{"status":"Declined","declined_by":"system","declined_reason":"player_accepted_another_content_manager","declined_at":now,"updated_at":now}})
            await content_manager_contracts_collection.update_one({"_id":contract["_id"]},{"$set":{"status":"Active","responded_by":"player","responded_at":now,"accepted_at":now,"signed_date":now,"verification_code_verified":True,"updated_at":now}})
            try:
                await players_collection.update_one(_pf(uid),{"$set":{"content_manager_id":str(contract.get("manager_id") or ""),"content_manager_assigned_at":now,"content_manager_contract_id":contract.get("contract_id"),"content_manager_contract_status":"active","updated_at":now}})
            except Exception: pass
            message="Content management agreement accepted"
        else:
            await content_manager_contracts_collection.update_one({"_id":contract["_id"]},{"$set":{"status":"Declined","responded_by":"player","responded_at":now,"declined_at":now,"updated_at":now}})
            message="Content management agreement declined"
        if notifications_collection is not None and contract.get("manager_id"):
            await notifications_collection.insert_one({"unique_id":str(contract.get("manager_id")),"manager_id":str(contract.get("manager_id")),"user_type":"content_manager","type":"content_manager_contract_response","title":"Content Management Agreement Response","message":f"{_pid(doc)} {'accepted' if body.action=='accept' else 'declined'} the content management agreement {body.contract_id}.","reference_id":body.contract_id,"read":False,"created_at":now})
        updated=await content_manager_contracts_collection.find_one({"_id":contract["_id"]})
        return JSONResponse({"success":True,"contract":_ser(updated),"message":message})
    except HTTPException: raise
    except Exception as e:
        if logger: logger.exception("respond_content_manager_contract error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/content-manager-contracts/{contract_id}/terminate
# ============================================================

@router.post("/player/{uid}/content-manager-contracts/{contract_id}/terminate")
async def terminate_content_manager_contract_by_player(uid: str, contract_id: str, body: ContentManagerContractTerminateBody, request: Request):
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)
        contract = await content_manager_contracts_collection.find_one({
            "contract_id": contract_id,
            "$or": [{"player_id": uid}, {"player_id": pid_val}, {"player_user_id": uid}, {"player_user_id": pid_val}],
        })
        if not contract:
            raise HTTPException(status_code=404, detail="Content management agreement not found")
        if str(contract.get("status", "")).lower() != "active":
            raise HTTPException(status_code=400, detail="Only active agreements can be terminated")
        now = _now()
        await content_manager_contracts_collection.update_one({"_id": contract["_id"]}, {"$set": {"status": "Terminated", "terminated_by": "player", "termination_reason": body.reason.strip(), "terminated_at": now, "updated_at": now}})
        try:
            await players_collection.update_one(_pf(uid), {"$unset": {"content_manager_id": "", "content_manager_assigned_at": "", "content_manager_contract_id": "", "content_manager_contract_status": ""}, "$set": {"updated_at": now}})
        except Exception: pass
        if notifications_collection is not None and contract.get("manager_id"):
            await notifications_collection.insert_one({
                "unique_id": str(contract.get("manager_id")), "manager_id": str(contract.get("manager_id")), "user_type": "content_manager",
                "type": "content_manager_contract_terminated", "title": "Content Management Agreement Terminated",
                "message": f"The player terminated content management agreement {contract_id}.",
                "reference_id": contract_id, "read": False, "created_at": now,
            })
        updated = await content_manager_contracts_collection.find_one({"_id": contract["_id"]})
        return JSONResponse({"success": True, "contract": _ser(updated), "message": "Content management agreement terminated"})
    except HTTPException:
        raise
    except Exception as e:
        if logger: logger.exception("terminate_content_manager_contract_by_player error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/contracts
# ============================================================

@router.get("/player/{uid}/contracts")
async def get_player_contracts(uid: str, request: Request):
    """Return active contract, pending requests, and contract history."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        pf = _player_filter_combined(uid, pid_val)
        active_contract = None
        contract_requests: list = []
        contract_history: list = []

        if agent_contracts_collection is not None:
            active_doc = await agent_contracts_collection.find_one(
                {**pf, "status": {"$in": ["Active", "active", "signed"]}}
            )
            if active_doc:
                active_contract = _ser(active_doc)

            pending_docs = await agent_contracts_collection.find(
                {**pf, "status": {"$in": ["Pending", "pending", "offered"]}}
            ).sort("created_at", -1).limit(20).to_list(length=20)
            contract_requests = _ser_list(pending_docs)

            history_docs = await agent_contracts_collection.find(
                {**pf, "status": {"$in": ["Expired", "expired", "Declined", "declined", "Terminated"]}}
            ).sort("end_date", -1).limit(20).to_list(length=20)
            contract_history = _ser_list(history_docs)

        return JSONResponse({
            "active_contract": active_contract,
            "contract_requests": contract_requests,
            "contract_history": contract_history,
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_contracts error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/contracts/respond
# ============================================================

@router.post("/player/{uid}/contracts/respond")
async def respond_to_contract(uid: str, body: ContractRespondBody, request: Request):
    """Accept or decline a pending agent contract request."""
    try:
        await _require_player_auth(request, uid)

        if body.action not in ("accept", "decline"):
            raise HTTPException(status_code=400, detail="Action must be 'accept' or 'decline'")
        if body.action == "accept" and len(body.code or "") != 12:
            raise HTTPException(status_code=400, detail="12-character verification code required")
        if agent_contracts_collection is None:
            raise HTTPException(status_code=503, detail="Contract service unavailable")

        try:
            filt: dict = {"_id": ObjectId(body.request_id)}
        except Exception:
            filt = {"$or": [{"request_id": body.request_id}, {"_id": body.request_id}]}

        req_doc = await agent_contracts_collection.find_one(filt)
        if not req_doc:
            raise HTTPException(status_code=404, detail="Contract request not found")

        # Validate verification code against the stored code (not just length)
        if body.action == "accept":
            stored_code = req_doc.get("verification_code", "")
            if stored_code and body.code != stored_code:
                raise HTTPException(
                    status_code=400,
                    detail="Verification code does not match. Check your notification or contract card.",
                )

        now = _now()

        if body.action == "accept":
            doc = await _resolve_player(uid)
            pid_val = _pid(doc) if doc else uid
            player_name_str = (
                doc.get("first_name", "") + " " + doc.get("last_name", "")
            ).strip() if doc else uid
            if not player_name_str:
                player_name_str = doc.get("name", "") if doc else uid

            await agent_contracts_collection.update_many(
                {
                    "$or": [{"player_id": uid}, {"player_id": pid_val}],
                    "status": {"$in": ["Active", "active"]},
                },
                {"$set": {"status": "Expired", "expired_at": now}},
            )
            duration_str = req_doc.get("contract_duration", "1 year")
            try:
                # ── FIX: hard-cap at 1 year regardless of stored string value
                years = min(1, int(re.search(r"\d+", duration_str).group()))
            except Exception:
                years = 1
            end_date = now.replace(year=now.year + years)

            signed_agent_id = req_doc.get("agent_id") or req_doc.get("agentId") or ""
            signed_request_id = req_doc.get("request_id") or str(req_doc.get("_id", ""))

            await agent_contracts_collection.update_one(
                {"_id": req_doc["_id"]},
                {"$set": {
                    "status": "Active",
                    "signed_date": now,
                    "start_date": now,
                    "end_date": end_date,
                    "signed_code": body.code,
                    # Keep original proposed dates for reference on agent side
                    "proposed_start_date": req_doc.get("start_date") or req_doc.get("proposedStartDate"),
                    "proposed_end_date": req_doc.get("end_date") or req_doc.get("proposedEndDate"),
                }},
            )

            # BF5: Update the player document so the agent association and
            # contract status are reflected in player profile queries.
            try:
                await players_collection.update_one(
                    _pf(uid),
                    {"$set": {
                        "agent_id":          signed_agent_id,
                        "agent_assigned_at": now,
                        "contract_status":   "active",
                        "updated_at":        now,
                    }},
                )
            except Exception as pup_exc:
                if logger:
                    logger.warning("BF5 player doc update failed: %s", pup_exc)

            # BF6: Notify the agent whose proposal was just accepted.
            if signed_agent_id and notifications_collection is not None:
                try:
                    await notifications_collection.insert_one({
                        "agent_id":   signed_agent_id,
                        "user_type":  "agent",
                        "type":       "contract_accepted",
                        "message":    (
                            f"Player {player_name_str or uid} has accepted your contract proposal "
                            f"(Request ID: {signed_request_id})."
                        ),
                        "extra_data": {
                            "player_id":   pid_val,
                            "player_name": player_name_str,
                            "contract_id": signed_request_id,
                            "request_id":  signed_request_id,
                        },
                        "isRead":    False,
                        "created_at": now,
                        "created_at": now,
                    })
                except Exception as n6_exc:
                    if logger:
                        logger.warning("BF6 agent notification failed: %s", n6_exc)

            # BF7 + BF8: Bulk-decline all OTHER pending proposals for this player
            # (from different agents) so the player doesn't have orphaned pending offers.
            try:
                other_pending_cursor = agent_contracts_collection.find({
                    "$or": [{"player_id": uid}, {"player_id": pid_val}],
                    "status": {"$in": ["pending", "Pending", "offered"]},
                    "_id": {"$ne": req_doc["_id"]},
                })
                other_pending = await other_pending_cursor.to_list(length=200)
                if other_pending:
                    other_ids = [p["_id"] for p in other_pending]
                    await agent_contracts_collection.update_many(
                        {"_id": {"$in": other_ids}},
                        {"$set": {
                            "status":           "Declined",
                            "declined_at":      now,
                            "declined_reason":  "player_signed_elsewhere",
                        }},
                    )
                    # BF8: Notify each auto-declined agent individually
                    if notifications_collection is not None:
                        for op in other_pending:
                            other_agent_id = op.get("agent_id") or op.get("agentId") or ""
                            if not other_agent_id:
                                continue
                            try:
                                await notifications_collection.insert_one({
                                    "agent_id":   other_agent_id,
                                    "user_type":  "agent",
                                    "type":       "proposal_auto_declined",
                                    "message":    (
                                        f"Your contract proposal for {player_name_str or uid} "
                                        f"was automatically declined because the player signed with another agent."
                                    ),
                                    "extra_data": {
                                        "player_id":       pid_val,
                                        "player_name":     player_name_str,
                                        "request_id":      op.get("request_id") or str(op.get("_id", "")),
                                        "declined_reason": "player_signed_elsewhere",
                                    },
                                    "isRead":    False,
                                    "created_at": now,
                                    "created_at": now,
                                })
                            except Exception as n8_exc:
                                if logger:
                                    logger.warning(
                                        "BF8 auto-decline notification failed for agent %s: %s",
                                        other_agent_id, n8_exc,
                                    )
            except Exception as bf7_exc:
                if logger:
                    logger.warning("BF7/BF8 bulk-decline failed: %s", bf7_exc)

            updated = await agent_contracts_collection.find_one({"_id": req_doc["_id"]})
            return JSONResponse({
                "success": True,
                "contract": _ser(updated),
                "message": "Contract signed successfully",
            })

        # ── DECLINE path ─────────────────────────────────────────────────────
        await agent_contracts_collection.update_one(
            {"_id": req_doc["_id"]},
            {"$set": {"status": "Declined", "declined_at": now}},
        )

        # BF9: Notify the originating agent that the player declined their proposal.
        declined_agent_id = req_doc.get("agent_id") or req_doc.get("agentId") or ""
        if declined_agent_id and notifications_collection is not None:
            try:
                doc = doc if "doc" in dir() else await _resolve_player(uid)
                pid_val_d = _pid(doc) if doc else uid
                player_name_d = (
                    (doc.get("first_name", "") + " " + doc.get("last_name", "")).strip()
                    if doc else uid
                ) or (doc.get("name", "") if doc else uid)
                declined_rid = req_doc.get("request_id") or str(req_doc.get("_id", ""))
                await notifications_collection.insert_one({
                    "agent_id":   declined_agent_id,
                    "user_type":  "agent",
                    "type":       "contract_declined",
                    "message":    (
                        f"Player {player_name_d or uid} has declined your contract proposal "
                        f"(Request ID: {declined_rid})."
                    ),
                    "extra_data": {
                        "player_id":   pid_val_d,
                        "player_name": player_name_d,
                        "request_id":  declined_rid,
                        "declined_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
                    },
                    "isRead":    False,
                    "created_at": now,
                    "created_at": now,
                })
            except Exception as n9_exc:
                if logger:
                    logger.warning("BF9 decline notification failed: %s", n9_exc)

        return JSONResponse({"success": True, "message": "Contract declined"})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("respond_to_contract error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/achievements
# ============================================================

@router.get("/player/{uid}/achievements")
async def get_player_achievements(uid: str, request: Request):
    """Return achievements/awards for this player."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        embedded = _normalize_achievement_list(_ser({"achievements": doc.get("achievements")}).get("achievements"))
        if embedded:
            return JSONResponse({"achievements": embedded})

        ach_col = database["achievements"] if database is not None else None
        if ach_col is not None:
            ach_docs = await ach_col.find(
                {"$or": [{"player_id": uid}, {"player_id": pid_val}]}
            ).sort("date", -1).limit(50).to_list(length=50)
            return JSONResponse({"achievements": _normalize_achievement_list(_ser_list(ach_docs))})

        return JSONResponse({"achievements": []})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_achievements error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/contact-card
# ============================================================

@router.get("/player/{uid}/contact-card")
async def get_player_contact_card(uid: str, request: Request):
    """
    Return contact info.
    Type is 'agent' when an active contract exists; otherwise 'direct'.
    """
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        contact_data: dict = {
            "type": "direct",
            "phone": doc.get("phone", ""),
            "whatsapp": doc.get("whatsapp", "") or doc.get("phone", ""),
            "email": doc.get("email", ""),
        }

        if agent_contracts_collection is not None:
            active = await agent_contracts_collection.find_one({
                "$or": [{"player_id": uid}, {"player_id": pid_val}],
                "status": {"$in": ["Active", "active"]},
            })
            if active:
                agent_id = active.get("agent_id", "")
                if agent_id and agents_collection is not None:
                    try:
                        agent_filt = {"$or": [{"agent_id": agent_id}]}
                        if len(str(agent_id)) == 24:
                            try:
                                agent_filt["$or"].append({"_id": ObjectId(agent_id)})
                            except Exception:
                                pass
                        agent_doc = await agents_collection.find_one(agent_filt)
                    except Exception:
                        agent_doc = None
                    if agent_doc:
                        contact_data = {
                            "type": "agent",
                            "phone": agent_doc.get("phone", ""),
                            "whatsapp": agent_doc.get("whatsapp") or agent_doc.get("phone", ""),
                            "email": agent_doc.get("email", ""),
                            "agent_name": " ".join(filter(None, [
                                agent_doc.get("firstName"), agent_doc.get("lastName")
                            ])),
                        }

        return JSONResponse({"contact_card": contact_data, **contact_data})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_contact_card error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/club-history
# ============================================================

@router.get("/player/{uid}/club-history")
async def get_player_club_history(uid: str, request: Request):
    """Return the player's club history."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        embedded = doc.get("club_history", [])
        if embedded:
            return JSONResponse({"club_history": embedded})

        hist_col = database["club_history"] if database is not None else None
        if hist_col is not None:
            hist = await hist_col.find(
                {"$or": [{"player_id": uid}, {"player_id": pid_val}]}
            ).sort("from", -1).limit(20).to_list(length=20)
            return JSONResponse({"club_history": _ser_list(hist)})

        return JSONResponse({"club_history": []})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_club_history error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/stats/requests
# ============================================================

@router.get("/player/{uid}/stats/requests")
async def get_player_stats_requests(uid: str, request: Request, limit: int = 50):
    """Return stats tracking requests submitted by this player."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        reqs = await stats_requests_collection.find(
            {"$or": [{"player_id": uid}, {"player_id": pid_val}]}
        ).sort("submitted_at", -1).limit(max(1, min(limit, 200))).to_list(length=200)

        return JSONResponse({"requests": _ser_list(reqs), "stats_requests": _ser_list(reqs)})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_stats_requests error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/stats/requests
# ============================================================

@router.post("/player/{uid}/stats/requests")
async def submit_stats_request(uid: str, body: StatsRequestBody, request: Request):
    """Submit a new match-stats tracking request, reserving tokens."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        category = doc.get("playing_category") or doc.get("category", "local")
        token_cost = 1
        if get_token_cost:
            try:
                token_cost = get_token_cost("player", category)
                if body.heatmap:
                    token_cost += 1
            except Exception:
                pass

        token_doc = await player_tokens_collection.find_one(
            {"$or": [{"player_id": uid}, {"player_id": pid_val}]}
        )
        balance = int(token_doc.get("balance", 0)) if token_doc else 0

        pending_locked = await stats_requests_collection.find(
            {
                "$or": [{"player_id": uid}, {"player_id": pid_val}],
                "status": {"$in": ["Pending", "Assigned", "pending", "assigned"]},
                "token_deducted": {"$ne": True},
            },
            {"token_cost": 1},
        ).to_list(length=200)
        locked = sum(int(r.get("token_cost", 0)) for r in pending_locked)
        available = max(0, balance - locked)

        if available < token_cost:
            raise HTTPException(status_code=402, detail="Insufficient available tokens")

        ref_id = _make_ref("SR")
        home_team = body.home_team or body.homeTeam or ""
        away_team = body.away_team or body.awayTeam or ""

        req_doc: dict = {
            "player_id": pid_val,
            "reference_id": ref_id,
            "home_team": home_team,
            "away_team": away_team,
            "match_date": body.match_date or "",
            "match_time": body.match_time or "",
            "jersey_number": body.jersey_number or "",
            "player_represents": body.player_represents or "home",
            "match_type": body.match_type or "",
            "heatmap": bool(body.heatmap),
            "venue_address": body.venue_address or "",
            "venue_country": body.venue_country or "",
            "venue_state": body.venue_state or "",
            "venue_lga": body.venue_lga or "",
            "contact_phone": body.contact_phone or "",
            "token_cost": token_cost,
            "status": "Pending",
            "submitted_at": _now(),
            "created_at": _now(),
        }

        # Debit immediately, consistently with Content Manager-submitted requests.
        # This prevents the same player tokens from being spent twice while the
        # request is pending. The dashboard reports the debit in transactions.
        if not token_doc:
            raise HTTPException(status_code=402, detail="No token wallet is available for this player")
        debit_filter = {"_id": token_doc["_id"], "balance": {"$gte": token_cost}}
        debit_result = await player_tokens_collection.update_one(
            debit_filter, {"$inc": {"balance": -token_cost}, "$set": {"updated_at": _now()}}
        )
        if debit_result.modified_count != 1:
            raise HTTPException(status_code=409, detail="Token balance changed while submitting the request")
        req_doc.update({
            "token_deducted": True,
            "deducted_from_player_wallet": True,
            "submitted_by": pid_val,
            "submitted_by_role": "player",
            "submitted_via": "player_dashboard",
        })
        try:
            await stats_requests_collection.insert_one(req_doc)
            if token_transactions_collection is not None:
                await token_transactions_collection.insert_one({
                    "player_id": pid_val, "unique_id": pid_val, "user_type": "player",
                    "type": "debit", "amount": f"-{token_cost}", "tokens_debited": token_cost,
                    "description": f"Match statistics request submitted — {token_cost} token(s)",
                    "status": "completed", "reference_id": ref_id, "created_at": _now(),
                })
            await _insert_notification(
                {"player_id": pid_val, "unique_id": pid_val, "user_id": pid_val, "user_type": "player"},
                notif_type="stats_request", title="Stats Request Submitted",
                message=f"Your {body.match_type or 'match'} stats request {ref_id} was submitted. {token_cost} token(s) were deducted from your wallet.",
                reference_id=ref_id, extra={"request_status": "Pending", "token_cost": token_cost},
            )

            manager = await _active_content_manager_for_player(doc)
            if manager:
                manager_id = str(manager.get("manager_id") or "")
                if manager_id:
                    await _insert_notification(
                        {"manager_id": manager_id, "unique_id": manager_id, "user_id": manager_id, "user_type": "content_manager"},
                        notif_type="player_stats_request", title="Player Submitted a Stats Request",
                        message=f"{_player_name(doc) or pid_val} submitted stats request {ref_id} for {home_team} vs {away_team}.",
                        reference_id=ref_id, extra={"player_id": pid_val, "request_status": "Pending"},
                    )
        except Exception:
            # Compensate the wallet if persistence/notification creation fails.
            await player_tokens_collection.update_one({"_id": token_doc["_id"]}, {"$inc": {"balance": token_cost}, "$set": {"updated_at": _now()}})
            raise

        return JSONResponse({
            "success": True,
            "reference_id": ref_id,
            "request_id": ref_id,
            "ref": ref_id,
            "token_cost": token_cost,
            "token_deducted": True,
            "message": f"Stats request submitted successfully. {token_cost} token(s) deducted from your wallet.",
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("submit_stats_request error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: DELETE /player/{uid}/stats/requests/{ref_id}
# ============================================================

@router.delete("/player/{uid}/stats/requests/{ref_id}")
async def cancel_stats_request(uid: str, ref_id: str, request: Request):
    """Cancel a pending stats request and surface the refundable token count."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        req_doc = await stats_requests_collection.find_one({
            "$and": [
                {"$or": [{"player_id": uid}, {"player_id": pid_val}]},
                {"$or": [{"reference_id": ref_id}, {"request_id": ref_id}]},
            ]
        })
        if not req_doc:
            raise HTTPException(status_code=404, detail="Stats request not found")

        status = req_doc.get("status", "")
        if status.lower() not in ("pending",):
            raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")

        refunded = int(req_doc.get("token_cost", 0))
        # Content-manager requests deduct the player's wallet immediately.
        # Refund that wallet on cancellation; legacy requests remain reservation-only.
        if req_doc.get("token_deducted") is True and refunded > 0:
            await player_tokens_collection.update_one(
                {"$or": [{"player_id": uid}, {"player_id": pid_val}]},
                {"$inc": {"balance": refunded}, "$set": {"updated_at": _now()}},
            )
            if token_transactions_collection is not None:
                await token_transactions_collection.insert_one({
                    "player_id": pid_val,
                    "unique_id": pid_val,
                    "user_type": "player",
                    "type": "refund",
                    "amount": f"+{refunded}",
                    "tokens_credited": refunded,
                    "description": f"Stats request cancellation refund — {refunded} token(s)",
                    "status": "completed",
                    "reference_id": ref_id,
                    "created_at": _now(),
                })
        await stats_requests_collection.update_one(
            {"_id": req_doc["_id"]},
            {"$set": {"status": "Cancelled", "cancelled_at": _now(), "updated_at": _now()}},
        )
        if req_doc.get("token_deducted") is True and refunded and player_tokens_collection is not None:
            await player_tokens_collection.update_one(
                {"$or": [{"player_id": uid}, {"player_id": pid_val}]},
                {"$inc": {"balance": refunded}, "$set": {"updated_at": _now()}},
            )
            if token_transactions_collection is not None:
                await token_transactions_collection.insert_one({
                    "player_id": pid_val, "unique_id": pid_val, "user_type": "player",
                    "type": "credit", "amount": f"+{refunded}", "tokens_credited": refunded,
                    "description": f"Refund for cancelled stats request {ref_id}",
                    "status": "completed", "reference_id": ref_id, "created_at": _now(),
                })
        await _insert_notification(
            {"player_id": pid_val, "unique_id": pid_val, "user_id": pid_val, "user_type": "player"},
            notif_type="stats_request_status", title="Stats Request Cancelled",
            message=f"Stats request {ref_id} was cancelled. {refunded} token(s) were refunded to your wallet." if refunded else f"Stats request {ref_id} was cancelled.",
            reference_id=ref_id, extra={"request_status": "Cancelled", "token_refunded": refunded, "event_key": f"stats_request_status:{ref_id}:cancelled"},
        )
        manager = await _active_content_manager_for_player(doc)
        if manager and manager.get("manager_id"):
            await _insert_notification(
                {"manager_id": str(manager.get("manager_id")), "unique_id": str(manager.get("manager_id")), "user_id": str(manager.get("manager_id")), "user_type": "content_manager"},
                notif_type="player_stats_request", title="Player Cancelled a Stats Request",
                message=f"{_player_name(doc) or pid_val} cancelled stats request {ref_id}.", reference_id=ref_id,
                extra={"player_id": pid_val, "request_status": "Cancelled"},
            )
        return JSONResponse({"success": True, "refunded": refunded, "reference_id": ref_id})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("cancel_stats_request error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: GET /player/{uid}/transactions
# ============================================================

@router.get("/player/{uid}/transactions")
async def get_player_transactions(uid: str, request: Request, limit: int = 100):
    """Return token transaction history for this player."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        col = (token_transactions_collection
               if token_transactions_collection is not None
               else transactions_collection)
        if col is None:
            return JSONResponse({"transactions": []})

        txs = await col.find(
            {"$or": [
                {"unique_id": uid}, {"unique_id": pid_val},
                {"player_id": uid}, {"player_id": pid_val},
            ]}
        ).sort("created_at", -1).limit(max(1, min(limit, 500))).to_list(length=500)

        return JSONResponse({"transactions": _ser_list(txs)})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("get_player_transactions error")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ENDPOINT: PATCH /player/{uid} — Edit profile
# Accepts multipart/form-data (optional photo upload) or JSON.
# ============================================================

@router.patch("/player/{uid}")
async def edit_player_profile(
    uid: str,
    request: Request,
    photo: Optional[UploadFile] = File(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    middle_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    nationality: Optional[str] = Form(None),
    height: Optional[str] = Form(None),
    weight: Optional[str] = Form(None),
    preferred_foot: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    preferred_position: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    current_club: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    dob_visible: Optional[str] = Form(None),
    instagram: Optional[str] = Form(None),
    twitter: Optional[str] = Form(None),
    facebook: Optional[str] = Form(None),
):
    """Update player profile fields and optionally replace the profile photo."""

    try:
        await _require_player_auth(request, uid)

        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        update_fields = {
            "updated_at": _now(),
        }

        str_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": middle_name,
            "phone": phone,
            "whatsapp": whatsapp,
            "nationality": nationality,
            "bio": bio,
            "current_club": current_club,
            "dob": dob,
            "instagram": instagram,
            "twitter": twitter,
            "facebook": facebook,
        }

        for field_key, value in str_fields.items():
            if value is not None:
                update_fields[field_key] = value

        if height is not None:
            try:
                update_fields["height"] = float(
                    re.sub(r"[^\d.]", "", height)
                )
            except Exception:
                update_fields["height"] = height

        if weight is not None:
            try:
                update_fields["weight"] = float(
                    re.sub(r"[^\d.]", "", weight)
                )
            except Exception:
                update_fields["weight"] = weight

        if preferred_foot is not None:
            update_fields["preferred_foot"] = preferred_foot

        if position is not None:
            update_fields["position"] = position

        if preferred_position is not None:
            update_fields["preferred_position"] = preferred_position

        if dob_visible is not None:
            update_fields["dob_visible"] = (
                str(dob_visible).lower() in ("true", "1", "yes")
            )

        if photo is not None and photo.filename:
            try:
                contents = await photo.read()

                if upload_to_cloudinary is not None:
                    photo_url = await upload_to_cloudinary(
                        contents,
                        folder="player_photos",
                        filename=photo.filename,
                        public_id=_pid(doc),
                        user_type="player",
                        file_category="profile",
                    )

                    update_fields["photo_url"] = photo_url

            except Exception as ue:
                if logger is not None:
                    logger.warning(
                        f"Profile photo upload failed for {uid}: {ue}"
                    )

        if len(update_fields) <= 1:
            return JSONResponse(
                {
                    "success": True,
                    "message": "No changes provided",
                }
            )

        await players_collection.update_one(
            _pf(uid),
            {
                "$set": update_fields,
            },
        )

        updated = await _resolve_player(uid)

        return JSONResponse(
            {
                "success": True,
                "player": _ser(updated),
                "message": "Profile updated successfully",
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        if logger is not None:
            logger.exception("edit_player_profile error")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# Alias route for frontend compatibility
router.add_api_route(
    "/player/{uid}/profile",
    edit_player_profile,
    methods=["PATCH"],
)

# ============================================================
# ENDPOINT: POST /player/{uid}/change-password
# ============================================================

@router.post("/player/{uid}/change-password")
async def change_player_password(uid: str, body: ChangePasswordBody, request: Request):
    """Verify current password then set a new one."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        current_hash = doc.get("password") or doc.get("hashed_password") or ""
        if not verify_password(body.current_password, current_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(body.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

        new_hash = hash_password(body.new_password)
        await players_collection.update_one(
            _pf(uid), {"$set": {"password": new_hash, "updated_at": _now()}}
        )
        return JSONResponse({"success": True, "message": "Password changed successfully"})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("change_player_password error")
        raise HTTPException(status_code=500, detail=str(e))




# ============================================================
# ENDPOINT: POST /player/{uid}/deactivate
# ============================================================

class DeactivateBody(BaseModel):
    reason: Optional[str] = ""

    class Config:
        extra = "allow"


@router.post("/player/{uid}/deactivate")
async def request_account_deactivation(uid: str, request: Request, body: DeactivateBody = None):
    """
    Record an account deactivation request from the player.

    Sets deactivation_requested=True and deactivation_requested_at on the player
    document.  Does NOT immediately delete or disable the account — an admin must
    confirm.  Sends an admin notification so the request is visible in the admin
    dashboard.

    Returns { "success": true, "message": "..." }
    """
    try:
        await _require_player_auth(request, uid)

        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        pid_val  = _pid(doc)
        now      = _now()
        reason   = (body.reason or "") if body else ""
        fullname = (
            (doc.get("first_name", "") + " " + doc.get("last_name", "")).strip()
            or doc.get("name", "")
            or uid
        )

        # Mark the request on the player document
        await players_collection.update_one(
            _pf(uid),
            {
                "$set": {
                    "deactivation_requested":    True,
                    "deactivation_requested_at": now,
                    "deactivation_reason":       reason,
                    "updated_at":                now,
                }
            },
        )

        # Notify admins so they can review and confirm the deactivation
        if notifications_collection is not None:
            try:
                await notifications_collection.insert_one({
                    "user_type":  "admin",
                    "type":       "account_deactivation_request",
                    "title":      "Account Deactivation Request",
                    "message":    (
                        f"Player {fullname} ({pid_val}) has requested account "
                        f"deactivation. Reason: {reason or 'Not specified'}."
                    ),
                    "extra_data": {
                        "player_id":   pid_val,
                        "player_name": fullname,
                        "reason":      reason,
                        "requested_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
                    },
                    "read":       False,
                    "isRead":     False,
                    "created_at": now,
                    "createdAt":  now,
                })
            except Exception as notify_exc:
                if logger:
                    logger.warning(
                        "deactivate: admin notification failed for %s: %s",
                        uid, notify_exc,
                    )

        if logger:
            logger.info(
                "[player_dashboard] deactivation request recorded for player %s", uid
            )

        return JSONResponse({
            "success": True,
            "message": (
                "Your account deactivation request has been submitted. "
                "An admin will review it within 2–3 business days. "
                "Your account remains active until confirmed."
            ),
        })

    except HTTPException:
        raise
    except Exception as exc:
        if logger:
            logger.exception("request_account_deactivation error for uid=%s", uid)
        raise HTTPException(status_code=500, detail=str(exc))

# ============================================================
# ENDPOINT: GET /token/costs
# ============================================================


# NOTE: GET /api/token/pricing is intentionally omitted here.
# It is defined in agent_dashboard_routes.py as a role-aware endpoint that
# returns the correct token packages for both agents and players based on the
# authenticated user's JWT role. Defining it here would create a duplicate route
# conflict; agent_dashboard_routes.py must be registered first in main.py.

# ============================================================
# ENDPOINT: GET /payment/config
# ============================================================



# ============================================================
# ENDPOINT: GET /competitions
# ============================================================



# ============================================================
# ENDPOINT: POST /player/{uid}/competitions/{comp_id}/apply
# ============================================================

@router.post("/player/{uid}/competitions/{comp_id}/apply")
async def apply_to_competition(
    uid: str, comp_id: str, body: CompetitionApplyBody, request: Request
):
    """Record a player's competition or trial application."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        col = database["competition_applications"] if database is not None else None
        if col is not None:
            existing = await col.find_one({
                "$or": [{"player_id": uid}, {"player_id": pid_val}],
                "competition_id": comp_id,
            })
            if existing:
                return JSONResponse({"success": True, "already_applied": True})

            await col.insert_one({
                "player_id": pid_val,
                "competition_id": comp_id,
                "competition_title": body.competition_title or "",
                "player_name": body.player_name or "",
                "player_category": body.player_category or "",
                "player_position": body.player_position or "",
                "player_club": body.player_club or "",
                "applied_at": _now(),
                "status": "applied",
            })

        return JSONResponse({
            "success": True,
            "message": "Application submitted",
            "competition_id": comp_id,
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("apply_to_competition error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/tokens/topup
# ============================================================

@router.post("/player/{uid}/tokens/topup")
async def initiate_token_topup(uid: str, body: TokenTopupBody, request: Request):
    """
    Initialise a Flutterwave token purchase.
    Returns the public key and tx_ref needed by FlutterwaveCheckout().
    """
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        if not FLUTTERWAVE_PUBLIC_KEY:
            raise HTTPException(status_code=503, detail="Payment gateway not configured")

        tx_ref = _make_ref("TX")

        if payment_intents_collection:
            await payment_intents_collection.insert_one({
                "player_id": _pid(doc),
                "tx_ref": tx_ref,
                "amount": body.amount,
                "tokens": body.tokens,
                "description": body.description or "",
                "status": "pending",
                "created_at": _now(),
            })

        return JSONResponse({
            "public_key": FLUTTERWAVE_PUBLIC_KEY,
            "tx_ref": tx_ref,
            "amount": body.amount,
            "tokens": body.tokens,
            "currency": "NGN",
        })

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("initiate_token_topup error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: POST /player/{uid}/tokens/verify
# ============================================================

@router.post("/player/{uid}/tokens/verify")
async def verify_token_payment(uid: str, body: TokenVerifyBody, request: Request):
    """Verify a completed Flutterwave payment and credit tokens to the wallet."""
    try:
        await _require_player_auth(request, uid)

        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")

        pid_val = _pid(doc)

        intent = None
        if payment_intents_collection is not None and body.tx_ref:
            intent = await payment_intents_collection.find_one(
                {
                    "tx_ref": body.tx_ref,
                    "$or": [
                        {"player_id": pid_val},
                        {"player_id": uid},
                    ],
                }
            )

        if not intent:
            raise HTTPException(
                status_code=404,
                detail="Payment record not found",
            )

        if intent.get("status") == "completed":
            return JSONResponse(
                {
                    "success": True,
                    "tokens_credited": 0,
                    "message": "Already processed",
                }
            )

        tokens_to_credit = int(intent.get("tokens", 0))

        token_doc = await player_tokens_collection.find_one(
            {
                "$or": [
                    {"player_id": uid},
                    {"player_id": pid_val},
                ]
            }
        )

        if token_doc:
            new_balance = (
                int(token_doc.get("balance", 0))
                + tokens_to_credit
            )

            await player_tokens_collection.update_one(
                {"_id": token_doc["_id"]},
                {
                    "$set": {
                        "balance": new_balance,
                        "updated_at": _now(),
                    }
                },
            )

        else:
            await player_tokens_collection.insert_one(
                {
                    "player_id": pid_val,
                    "balance": tokens_to_credit,
                    "created_at": _now(),
                    "updated_at": _now(),
                }
            )

        if payment_intents_collection is not None:
            await payment_intents_collection.update_one(
                {"_id": intent["_id"]},
                {
                    "$set": {
                        "status": "completed",
                        "transaction_id": body.transaction_id,
                        "completed_at": _now(),
                    }
                },
            )

        col = (
            token_transactions_collection
            if token_transactions_collection is not None
            else transactions_collection
        )

        if col is not None:
            await col.insert_one(
                {
                    "player_id": pid_val,
                    "unique_id": pid_val,
                    "user_type": "player",
                    "type": "credit",
                    "amount": f"+{tokens_to_credit}",
                    "tokens_credited": tokens_to_credit,
                    "description": (
                        f"Token purchase via Flutterwave — "
                        f"{tokens_to_credit} token(s)"
                    ),
                    "status": "completed",
                    "tx_ref": body.tx_ref,
                    "transaction_id": body.transaction_id,
                    "created_at": _now(),
                }
            )

        if notifications_collection is not None:
            await notifications_collection.insert_one(
                {
                    "unique_id": pid_val,
                    "player_id": pid_val,
                    "user_type": "player",
                    "type": "token_credit",
                    "title": "Tokens Credited",
                    "message": (
                        f"{tokens_to_credit} token(s) have been credited "
                        "to your account."
                    ),
                    "read": False,
                    "created_at": _now(),
                }
            )

        return JSONResponse(
            {
                "success": True,
                "tokens_credited": tokens_to_credit,
                "tokens_added": tokens_to_credit,
                "tokens": tokens_to_credit,
                "balance_change": tokens_to_credit,
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        if logger:
            logger.exception("verify_token_payment error")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# ============================================================
# ENDPOINT: POST /player/{uid}/media/youtube
# ============================================================

@router.post("/player/{uid}/media/youtube")
async def add_youtube_video(uid: str, body: YouTubeVideoBody, request: Request):
    """Save a YouTube video link to the player's media profile."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        yt_match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
            body.url,
        )
        if not yt_match:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        yt_id = yt_match.group(1)

        col = database["player_media"] if database is not None else None
        if col is not None:
            await col.update_one(
                {"player_id": pid_val},
                {"$push": {
                    "youtube_videos": {
                        "youtube_id": yt_id,
                        "url": body.url,
                        "title": body.title or "YouTube Video",
                        "added_at": _now(),
                    }
                }},
                upsert=True,
            )

        return JSONResponse({"success": True, "youtube_id": yt_id})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("add_youtube_video error")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENDPOINT: DELETE /player/{uid}/media/youtube/{yt_id}
# ============================================================

@router.delete("/player/{uid}/media/youtube/{yt_id}")
async def delete_youtube_video(uid: str, yt_id: str, request: Request):
    """Remove a YouTube video from the player's media profile."""
    try:
        await _require_player_auth(request, uid)
        doc = await _resolve_player(uid)
        if not doc:
            raise HTTPException(status_code=404, detail="Player not found")
        pid_val = _pid(doc)

        col = database["player_media"] if database is not None else None
        if col is not None:
            await col.update_one(
                {"player_id": pid_val},
                {"$pull": {"youtube_videos": {
                    "$or": [
                        {"youtube_id": yt_id},
                        {"id": yt_id},
                        {"video_id": yt_id},
                    ]
                }}},
            )

        return JSONResponse({"success": True})

    except HTTPException:
        raise
    except Exception as e:
        if logger:
            logger.exception("delete_youtube_video error")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# END: API ROUTES
# ============================================================
