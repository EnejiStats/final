"""
EnejiStats Content Manager Dashboard API
=========================================
Modular FastAPI router for the special content-manager role.

Integration in main.py (same dependency-injection pattern as the player router):
    import content_manager_dashboard_routes as _cmdr
    _cmdr._setup_dependencies(globals())
    app.include_router(_cmdr.router)

The router deliberately reuses the application's existing Mongo collections and
helpers. It does not import main.py, preventing circular imports.

Core contract
-------------
* A content manager can only operate on players explicitly associated with that
  manager. Associations are resolved from the dedicated
  content_manager_players collection and from common manager-id fields on the
  player document for backwards compatibility.
* Stats requests are submitted against the PLAYER'S token wallet, never a
  manager wallet.
* Manager-submitted requests set token_deducted=True. This lets the existing
  player dashboard distinguish an actual debit from its legacy reservation
  model and prevents double-locking the same tokens.
* Bulk requests are all-or-nothing from the API consumer's perspective. If a
  debit or insert fails part way through, already debited wallets are refunded.
* The dashboard reads the same validated player statistics pipeline exposed by
  /api/player/{uid}/stats/summary, so the social card can be generated from the
  exact stats available to the player dashboard.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Dependency placeholders; populated by _setup_dependencies().
database = None
players_collection = None
player_tokens_collection = None
stats_requests_collection = None
token_transactions_collection = None
notifications_collection = None
stat_submissions_collection = None
stat_submission_players_collection = None
stat_events_collection = None
content_manager_contracts_collection = None

get_current_user = None
normalize_role = None
MongoSerializer = None
logger = None
_make_stats_request_ref = None
get_token_cost = None

_DEPS_READY = False

router = APIRouter(prefix="/api", tags=["content-manager-dashboard"])


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------

def _setup_dependencies(main_globals: dict) -> None:
    global _DEPS_READY
    global database, players_collection, player_tokens_collection
    global stats_requests_collection, token_transactions_collection
    global notifications_collection, stat_submissions_collection
    global stat_submission_players_collection, stat_events_collection, content_manager_contracts_collection
    global get_current_user, normalize_role, MongoSerializer, logger
    global _make_stats_request_ref, get_token_cost

    if _DEPS_READY:
        return

    g = main_globals
    database = g.get("database")
    if database is None:
        raise RuntimeError("Database dependency was not injected into content_manager_dashboard_routes")

    # IMPORTANT: PyMongo Collection objects deliberately do not implement
    # truth-value testing. Never use ``collection_a or collection_b`` here;
    # compare explicitly with None when selecting an injected collection.
    def _collection(name: str, fallback: str):
        value = g.get(name)
        return value if value is not None else database.get_collection(fallback)

    players_collection = _collection("players_collection", "players")
    player_tokens_collection = _collection("player_tokens_collection", "player_tokens")
    stats_requests_collection = _collection("stats_requests_collection", "stats_requests")
    token_transactions_collection = _collection("token_transactions_collection", "token_transactions")
    notifications_collection = _collection("notifications_collection", "notifications")
    stat_submissions_collection = _collection("stat_submissions_collection", "stat_submissions")
    stat_submission_players_collection = _collection("stat_submission_players_collection", "stat_submission_players")
    stat_events_collection = _collection("stat_events_collection", "stat_events")
    content_manager_contracts_collection = _collection("content_manager_contracts_collection", "content_manager_contracts")

    get_current_user = g.get("get_current_user")
    normalize_role = g.get("normalize_role")
    MongoSerializer = g.get("MongoSerializer")
    logger = g.get("logger")
    _make_stats_request_ref = g.get("_make_stats_request_ref")
    get_token_cost = g.get("get_token_cost")
    _DEPS_READY = True


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ContentManagerContractCreateBody(BaseModel):
    player_id: str
    title: str = "Content Management Agreement"
    start_date: str = ""
    end_date: str = ""
    responsibilities: str = ""
    notes: str = ""
    message: str = ""


class ContentManagerContractRespondBody(BaseModel):
    contract_id: str
    action: str


class ContentManagerContractTerminateBody(BaseModel):
    reason: str = ""


class BulkStatsRequestBody(BaseModel):
    player_ids: List[str] = Field(default_factory=list)
    heatmap_player_ids: List[str] = Field(default_factory=list)
    jersey_numbers: Dict[str, str] = Field(default_factory=dict)
    match_date: str = ""
    match_time: str = ""
    home_team: str = ""
    away_team: str = ""
    player_represents: str = "home"
    match_type: str = "League"
    venue_address: str = ""
    venue_country: str = ""
    venue_state: str = ""
    venue_lga: str = ""
    contact_phone: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    if MongoSerializer is not None:
        try:
            return MongoSerializer.now_utc()
        except Exception:
            pass
    return MongoSerializer.now_utc()


def _ser(value: Any) -> Any:
    return MongoSerializer.serialize_value(value)


def _pid(player: dict) -> str:
    return str(player.get("player_id") or player.get("user_id") or player.get("unique_id") or player.get("_id") or "")


def _object_ids(values: Set[str]) -> List[ObjectId]:
    """Return only valid Mongo ObjectIds from a set of external identifiers."""
    out = []
    for value in values:
        try:
            out.append(ObjectId(value))
        except Exception:
            continue
    return out


def _name(player: dict) -> str:
    full = player.get("name") or player.get("full_name") or player.get("player_name")
    if full:
        return str(full).strip()
    return " ".join(str(v or "").strip() for v in [
        player.get("first_name") or player.get("firstName"),
        player.get("middle_name") or player.get("middleName"),
        player.get("last_name") or player.get("lastName"),
    ] if v).strip()


def _manager_identity(user: dict) -> Set[str]:
    values = {
        user.get("cm_id"), user.get("user_id"), user.get("unique_id"),
        user.get("manager_id"),
        user.get("content_manager_id"),
        str(user.get("_id", "")),
    }
    return {str(v) for v in values if v not in (None, "", "None")}


def _manager_role(user: dict) -> str:
    raw_role = user.get("role") or user.get("user_type") or ""
    try:
        return normalize_role(raw_role)
    except (ValueError, TypeError):
        return ""


def _manager_id(user: dict) -> str:
    """Return the canonical Content Manager public ID for new references."""
    return str(
        user.get("cm_id")
        or user.get("user_id")
        or user.get("unique_id")
        or user.get("manager_id")
        or ""
    )


def _is_manager(user: dict) -> bool:
    role = _manager_role(user)
    return role == "content_manager"


async def _auth(request: Request) -> dict:
    if get_current_user is None:
        raise HTTPException(status_code=503, detail="Authentication dependency is unavailable")
    user = await get_current_user(request)
    if not _is_manager(user):
        raise HTTPException(status_code=403, detail="Content manager access required")
    return user


def _player_fields_for_manager(manager_ids: Set[str]) -> List[dict]:
    mids = list(manager_ids)
    if not mids:
        return [{"_id": {"$exists": False}}]
    return [
        {"content_manager_id": {"$in": mids}},
        {"content_manager_ids": {"$in": mids}},
        {"manager_id": {"$in": mids}},
        {"manager_ids": {"$in": mids}},
        {"managed_by": {"$in": mids}},
        {"managed_by_ids": {"$in": mids}},
        {"content_managers": {"$in": mids}},
    ]


async def _managed_players(user: dict) -> List[dict]:
    manager_ids = _manager_identity(user)
    docs: Dict[str, dict] = {}

    if players_collection is not None:
        cursor = players_collection.find({"$or": _player_fields_for_manager(manager_ids)})
        for doc in await cursor.limit(1000).to_list(length=1000):
            docs[_pid(doc)] = doc

    # Dedicated relation collection, if present. It is intentionally optional.
    try:
        rel_col = database.get_collection("content_manager_players")
        rels = await rel_col.find({
            "manager_id": {"$in": list(manager_ids)},
            "status": {"$nin": ["revoked", "inactive", "removed"]},
        }).limit(1000).to_list(length=1000)
        rel_ids = {str(r.get("player_id") or r.get("uid") or "") for r in rels}
        rel_ids.discard("")
        if rel_ids and players_collection is not None:
            object_ids = _object_ids(rel_ids)
            identity_queries = [
                {"player_id": {"$in": list(rel_ids)}},
                {"user_id": {"$in": list(rel_ids)}},
            ]
            if object_ids:
                identity_queries.append({"_id": {"$in": object_ids}})
            for doc in await players_collection.find({
                "$or": identity_queries
            }).limit(1000).to_list(length=1000):
                docs[_pid(doc)] = doc
    except Exception:
        # The dedicated collection is optional; do not make a deployment fail
        # merely because it has not been created yet.
        pass

    return list(docs.values())


async def _get_managed_player(user: dict, uid: str) -> dict:
    uid = str(uid)
    for p in await _managed_players(user):
        if uid in {_pid(p), str(p.get("user_id") or ""), str(p.get("player_id") or ""), str(p.get("_id") or "")}:
            return p
    raise HTTPException(status_code=404, detail="Player is not in your managed portfolio")


async def _get_player_for_manager_stats(uid: str) -> dict:
    """Resolve a player from discovery for read-only manager statistics.

    Find Players intentionally exposes eligible platform players before a
    management relationship exists, so the stats viewer cannot require the
    player to already be in the manager portfolio. The caller is still gated
    by the Content Manager auth dependency on the endpoint itself.
    """
    uid = str(uid).strip()
    if not uid:
        raise HTTPException(status_code=400, detail="Player ID is required")
    query = {"$or": [
        {"player_id": uid},
        {"user_id": uid},
    ]}
    try:
        query["$or"].append({"_id": ObjectId(uid)})
    except Exception:
        pass
    player = await players_collection.find_one(query)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def _category(player: dict) -> str:
    return str(
        player.get("playing_category")
        or player.get("playingCategory")
        or player.get("player_category")
        or player.get("playerCategory")
        or player.get("category")
        or "local"
    ).strip().lower()


def _base_cost(player: dict) -> int:
    category = _category(player)
    if get_token_cost is not None:
        try:
            return max(1, int(get_token_cost("player", category)))
        except Exception:
            pass
    defaults = {
        "professional": 3,
        "semi-professional": 2,
        "semi_professional": 2,
        "academy": 1,
        "national": 2,
        "international": 3,
        "continental": 3,
        "local": 1,
        "grassroots": 1,
    }
    return defaults.get(category, 1)


def _request_ref() -> str:
    if _make_stats_request_ref is not None:
        try:
            return _make_stats_request_ref()
        except Exception:
            pass
    return f"SR-{_now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


async def _legacy_locked_tokens(player: dict) -> int:
    pid = _pid(player)
    uid = str(player.get("user_id") or "")
    if stats_requests_collection is None:
        return 0
    pending = await stats_requests_collection.find({
        "$or": [{"player_id": pid}, {"player_id": uid}],
        "status": {"$in": ["Pending", "Assigned", "pending", "assigned"]},
        "token_deducted": {"$ne": True},
    }, {"token_cost": 1}).to_list(length=200)
    return sum(int(r.get("token_cost", 0)) for r in pending)


def _portfolio_card(player: dict, token_doc: Optional[dict], manager_ids: Set[str], available: Optional[int] = None) -> dict:
    pid = _pid(player)
    balance = int((token_doc or {}).get("balance", 0))
    spendable = max(0, int(available if available is not None else balance))
    return {
        "player_id": pid,
        "user_id": str(player.get("user_id") or pid),
        "name": _name(player) or "Unnamed Player",
        "first_name": player.get("first_name") or player.get("firstName") or "",
        "last_name": player.get("last_name") or player.get("lastName") or "",
        "photo_url": player.get("photo_url") or player.get("photoUrl") or player.get("profile_photo") or player.get("profileImage") or player.get("avatar") or "",
        "club": player.get("current_club") or player.get("club") or player.get("team_name") or player.get("teamName") or "Unattached",
        "position": player.get("position") or player.get("preferred_position") or player.get("preferredPosition") or "—",
        "position_category": player.get("position_category") or player.get("positionCategory") or player.get("position_group") or ("Goalkeeper" if "keeper" in str(player.get("position") or "").lower() else "Outfield"),
        "playing_category": _category(player),
        "level": player.get("playing_level") or player.get("playingLevel") or player.get("level") or "",
        "nationality": player.get("nationality") or "",
        "jersey_number": player.get("jersey_number") or player.get("jerseyNumber") or "",
        "token_balance": balance,
        "token_available": spendable,
        "managed": True,
    }


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

@router.get("/content-manager/me")
async def content_manager_me(request: Request):
    user = await _auth(request)
    players = await _managed_players(user)
    token_balances = []
    for p in players:
        pid = _pid(p)
        td = await player_tokens_collection.find_one({"$or": [{"player_id": pid}, {"player_id": str(p.get("user_id") or "")} ]}, {"balance": 1})
        token_balances.append(int((td or {}).get("balance", 0)))
    return JSONResponse({
        "success": True,
        "manager": _ser({
            "id": _manager_id(user),
            "name": user.get("name") or user.get("full_name") or user.get("email") or "Content Manager",
            "email": user.get("email") or "",
            "role": user.get("role") or "content_manager",
        }),
        "portfolio_count": len(players),
        "players_with_tokens": sum(1 for b in token_balances if b > 0),
    })


@router.get("/content-manager/players")
async def content_manager_players(request: Request, q: str = "", limit: int = 200):
    user = await _auth(request)
    players = await _managed_players(user)
    qn = (q or "").strip().lower()
    if qn:
        players = [p for p in players if qn in " ".join([
            _name(p),
            str(p.get("current_club") or p.get("club") or ""),
            str(p.get("position") or p.get("preferred_position") or ""),
        ]).lower()]
    players.sort(key=lambda p: _name(p).lower())
    cards = []
    for p in players[:max(1, min(limit, 500))]:
        pid = _pid(p)
        td = await player_tokens_collection.find_one({"$or": [{"player_id": pid}, {"player_id": str(p.get("user_id") or "")} ]}, {"balance": 1})
        locked = await _legacy_locked_tokens(p)
        cards.append(_portfolio_card(p, td, _manager_identity(user), max(0, int((td or {}).get("balance", 0)) - locked)))
    return JSONResponse({"success": True, "players": cards, "count": len(cards)})


@router.get("/content-manager/players/{uid}/tokens")
async def content_manager_player_tokens(uid: str, request: Request):
    user = await _auth(request)
    player = await _get_managed_player(user, uid)
    pid = _pid(player)
    td = await player_tokens_collection.find_one({"$or": [{"player_id": pid}, {"player_id": str(player.get("user_id") or "")} ]})
    balance = int((td or {}).get("balance", 0))
    pending = await stats_requests_collection.find({
        "$or": [{"player_id": pid}, {"player_id": str(player.get("user_id") or "")}],
        "status": {"$in": ["Pending", "Assigned", "pending", "assigned"]},
    }, {"token_cost": 1, "token_deducted": 1}).to_list(length=200)
    legacy_locked = sum(int(r.get("token_cost", 0)) for r in pending if r.get("token_deducted") is not True)
    return JSONResponse({"success": True, "balance": balance, "locked_legacy": legacy_locked, "available": max(0, balance - legacy_locked)})


# ---------------------------------------------------------------------------
# Validated player statistics for social cards
# ---------------------------------------------------------------------------

@router.get("/content-manager/players/{uid}/stats")
async def content_manager_player_stats(uid: str, request: Request, limit: int = 50):
    user = await _auth(request)
    player = await _get_player_for_manager_stats(uid)
    pid = _pid(player)

    # Reuse the same persisted collections as the player dashboard. We project
    # the approved/validated submission rows and their atomic events here so
    # the manager card is sourced from player-visible data.
    rows = []
    if stat_submission_players_collection is not None and stat_submissions_collection is not None:
        player_rows = await stat_submission_players_collection.find({"player_id": {"$in": [pid, str(player.get("user_id") or "")]}}).sort("created_at", -1).limit(max(1, min(limit * 2, 200))).to_list(length=200)
        sub_ids = [r.get("submission_id") for r in player_rows if r.get("submission_id") is not None]
        if sub_ids:
            submissions = await stat_submissions_collection.find({
                "_id": {"$in": sub_ids},
                "status": {"$in": ["approved", "verified", "completed", "pending_approval", "pending_validation", "submitted"]},
            }).sort("submitted_at", -1).limit(max(1, min(limit, 100))).to_list(length=max(1, min(limit, 100)))
            by_sub = {str(r.get("submission_id")): r for r in player_rows}
            for sub in submissions:
                pr = by_sub.get(str(sub.get("_id")), {})
                events = []
                if stat_events_collection is not None and pr.get("_id") is not None:
                    events = await stat_events_collection.find({"submission_player_id": pr.get("_id")}).sort("event_order", 1).limit(1000).to_list(length=1000)
                rows.append({
                    "submission_id": str(sub.get("_id")),
                    "status": sub.get("status", ""),
                    "submitted_at": sub.get("submitted_at"),
                    "match": sub.get("match") or sub.get("match_details") or {},
                    "player": pr,
                    "events": events,
                    "stats": sub.get("stats") or pr.get("stats") or {},
                    "performance_score": pr.get("performance_score") or sub.get("performance_score"),
                })

    # Fallback to the existing player_stats collection when normalized tracker
    # rows are unavailable. This keeps older deployments usable.
    if not rows and database is not None:
        legacy = database.get_collection("player_stats")
        legacy_rows = await legacy.find({"$or": [{"player_id": pid}, {"player_id": str(player.get("user_id") or "")}]}).sort("match_date", -1).limit(max(1, min(limit, 100))).to_list(length=100)
        rows = [{
            "submission_id": str(r.get("_id", "")),
            "status": r.get("status", "completed"),
            "submitted_at": r.get("created_at") or r.get("match_date"),
            "match": r,
            "player": r,
            "events": r.get("events") or [],
            "stats": r.get("stats") or r,
            "performance_score": r.get("performance_score"),
        } for r in legacy_rows]

    return JSONResponse({
        "success": True,
        "player": _portfolio_card(player, None, _manager_identity(user)),
        "matches": _ser(rows),
        "count": len(rows),
        "source": "validated_player_visible_stats",
    })


# ---------------------------------------------------------------------------
# Content manager ↔ player relationship contracts
# ---------------------------------------------------------------------------

def _contract_manager_id(user: dict) -> str:
    return _manager_id(user)


def _contract_name(player: dict) -> str:
    return _name(player) or _pid(player)


def _contract_filter_for_manager(manager_id: str) -> dict:
    return {"manager_id": manager_id}



def _verification_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(12))


def _discover_player_name(p: dict) -> str:
    return _name(p) or str(p.get("full_name") or p.get("display_name") or p.get("name") or "Player")


def _discover_player_stats(p: dict) -> dict:
    raw = p.get("stats") or p.get("season_stats") or p.get("seasonStats") or {}
    if not isinstance(raw, dict):
        raw = {}
    def num(*keys, default=0):
        for k in keys:
            v = raw.get(k)
            if v is not None and v != "":
                try: return float(v)
                except Exception: pass
        return default
    return {
        "matchesPlayed": int(num("matchesPlayed", "matches_played", "appearances")),
        "totalGoals": int(num("totalGoals", "goals", "goals_total")),
        "totalAssists": int(num("totalAssists", "assists", "assists_total")),
        "avgRating": num("avgRating", "avg_rating", "averageRating", "performance_score"),
        "avgPassAcc": num("avgPassAcc", "avg_pass_accuracy", "pass_accuracy"),
        "cleanSheets": int(num("cleanSheets", "clean_sheets")),
        "tackles": int(num("tackles", "tackles_won")),
        "interceptions": int(num("interceptions")),
    }


def _discover_contract_status_map(docs: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for d in docs:
        pid = str(d.get("player_id") or d.get("player_user_id") or "")
        if pid:
            out.setdefault(pid, []).append(d)
    return out


@router.get("/content-manager/search-players")
async def content_manager_search_players(
    request: Request,
    q: str = "",
    continents: List[str] = Query(default=[]),
    africa_regions: List[str] = Query(default=[]),
    countries: List[str] = Query(default=[]),
    states: List[str] = Query(default=[]),
    lgas: List[str] = Query(default=[]),
    levels: List[str] = Query(default=[]),
    position_categories: List[str] = Query(default=[]),
    positions: List[str] = Query(default=[]),
    preferred_foot: str = "",
    age_min: Optional[float] = None,
    age_max: Optional[float] = None,
    height_min: Optional[float] = None,
    height_max: Optional[float] = None,
    weight_min: Optional[float] = None,
    weight_max: Optional[float] = None,
    goals_min: Optional[float] = None,
    goals_max: Optional[float] = None,
    assists_min: Optional[float] = None,
    assists_max: Optional[float] = None,
    matches_min: Optional[float] = None,
    matches_max: Optional[float] = None,
    rating_min: Optional[float] = None,
    rating_max: Optional[float] = None,
    pass_accuracy_min: Optional[float] = None,
    pass_accuracy_max: Optional[float] = None,
    clean_sheets_min: Optional[float] = None,
    clean_sheets_max: Optional[float] = None,
    tackles_min: Optional[float] = None,
    tackles_max: Optional[float] = None,
    interceptions_min: Optional[float] = None,
    interceptions_max: Optional[float] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    user = await _auth(request)
    manager_id = _contract_manager_id(user)
    docs = await players_collection.find({}).limit(5000).to_list(length=5000)
    contract_docs = await content_manager_contracts_collection.find({
        "status": {"$in": ["Pending", "pending", "Active", "active"]}
    }).limit(10000).to_list(length=10000)
    status_map = _discover_contract_status_map(contract_docs)

    now = _now()
    def age_of(p):
        dob = p.get("dob") or p.get("date_of_birth") or p.get("dateOfBirth")
        if not dob: return None
        try:
            from datetime import date
            if isinstance(dob, datetime): d = dob.date()
            else: d = datetime.fromisoformat(str(dob).replace("Z", "+00:00")).date()
            today = now.date() if hasattr(now, "date") else date.today()
            return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        except Exception: return None
    def vals(p):
        pos = str(p.get("position") or p.get("preferred_position") or p.get("preferredPosition") or "")
        cat = str(p.get("position_category") or p.get("positionCategory") or p.get("category") or "")
        level = str(p.get("level") or p.get("playing_level") or p.get("playingLevel") or p.get("playing_category") or "")
        country = str(p.get("country") or p.get("nationality") or "")
        continent = str(p.get("continent") or "")
        region = str(p.get("africa_region") or p.get("africaRegion") or "")
        state = str(p.get("state") or p.get("region") or p.get("current_state") or "")
        lga = str(p.get("lga") or p.get("city") or p.get("subregion") or "")
        foot = str(p.get("preferred_foot") or p.get("preferredFoot") or "")
        height = p.get("height") or p.get("height_cm")
        weight = p.get("weight") or p.get("weight_kg")
        stats = _discover_player_stats(p)
        return pos,cat,level,country,continent,region,state,lga,foot,height,weight,stats
    def in_set(value, choices):
        if not choices: return True
        lv=value.lower()
        return any(lv==str(x).lower() for x in choices)
    def between(v, lo, hi):
        if v is None: return lo is None and hi is None
        try: v=float(v)
        except Exception: return False if lo is not None or hi is not None else True
        return (lo is None or v>=lo) and (hi is None or v<=hi)
    needle=q.strip().lower()
    rows=[]
    for p in docs:
        pid=_pid(p)
        rels=status_map.get(pid, [])
        own_pending=next((d for d in rels if str(d.get("manager_id") or "") == manager_id and str(d.get("status","")).lower()=="pending"), None)
        own_active=next((d for d in rels if str(d.get("manager_id") or "") == manager_id and str(d.get("status","")).lower()=="active"), None)
        other_active=any(str(d.get("manager_id") or "") != manager_id and str(d.get("status","")).lower()=="active" for d in rels)
        other_pending=any(str(d.get("manager_id") or "") != manager_id and str(d.get("status","")).lower()=="pending" for d in rels)
        if other_active or other_pending: continue
        if own_active: continue
        name=_discover_player_name(p); club=str(p.get("current_club") or p.get("club") or "Free Agent")
        pos,cat,level,country,continent,region,state,lga,foot,height,weight,stats=vals(p)
        hay=" ".join([name,club,pos,cat,level,country,state,lga,pid]).lower()
        if needle and needle not in hay: continue
        if not in_set(continent,continents) or not in_set(region,africa_regions) or not in_set(country,countries) or not in_set(state,states) or not in_set(lga,lgas): continue
        if not in_set(level,levels) or not in_set(cat,position_categories) or not in_set(pos,positions): continue
        if preferred_foot and foot.lower()!=preferred_foot.lower(): continue
        age=age_of(p)
        if age_min is not None or age_max is not None:
            if age is None or not between(age,age_min,age_max): continue
        if height_min is not None or height_max is not None:
            if height is None or not between(height,height_min,height_max): continue
        if weight_min is not None or weight_max is not None:
            if weight is None or not between(weight,weight_min,weight_max): continue
        checks=[(stats["totalGoals"],goals_min,goals_max),(stats["totalAssists"],assists_min,assists_max),(stats["matchesPlayed"],matches_min,matches_max),(stats["avgRating"],rating_min,rating_max),(stats["avgPassAcc"],pass_accuracy_min,pass_accuracy_max),(stats["cleanSheets"],clean_sheets_min,clean_sheets_max),(stats["tackles"],tackles_min,tackles_max),(stats["interceptions"],interceptions_min,interceptions_max)]
        if any((lo is not None or hi is not None) and not between(v,lo,hi) for v,lo,hi in checks): continue
        pending_id=str(own_pending.get("contract_id")) if own_pending else ""
        rows.append({
            "id":pid,"player_id":pid,"user_id":str(p.get("user_id") or pid),"name":name,
            "full_name":p.get("full_name") or name,
            "first_name":p.get("first_name") or p.get("firstName") or "",
            "middle_name":p.get("middle_name") or p.get("middleName") or "",
            "last_name":p.get("last_name") or p.get("lastName") or "",
            "photoUrl":p.get("photo_url") or p.get("photoUrl") or p.get("photo") or "",
            "club":club,"current_club":club,"position":pos,"position_category":cat,
            "category":cat or level or p.get("playing_category") or "local",
            "playing_category":p.get("playing_category") or p.get("playingCategory") or "",
            "level":level,"nationality":country,"country":country,"continent":continent,"africa_region":region,
            "state":state,"region":state,"lga":lga,"city":p.get("city") or lga,
            "preferredFoot":foot,"preferred_foot":foot,"height":height,"weight":weight,"age":age,
            "dob":_ser(p.get("dob") or p.get("date_of_birth") or p.get("dateOfBirth")),
            "jersey_number":p.get("jersey_number") or p.get("jerseyNumber") or "",
            "stats":stats,"contractStatus":"pending" if own_pending else "none","pendingProposalId":pending_id,
            "eligible":True,"contentManagerEligible":True,
        })
    reverse=str(sort_order).lower()=="desc"
    keymap={"name":lambda x:x["name"].lower(),"nationality":lambda x:x["nationality"].lower(),"position":lambda x:x["position"].lower(),"category":lambda x:x["category"].lower()}
    rows.sort(key=keymap.get(str(sort_by).lower(),keymap["name"]),reverse=reverse)
    total=len(rows); ps=max(1,min(int(page_size or 20),100)); pg=max(1,int(page or 1)); start=(pg-1)*ps
    return JSONResponse({"success":True,"players":_ser(rows[start:start+ps]),"total":total,"page":pg,"pageSize":ps,"hasMore":start+ps<total})


@router.get("/content-manager/contracts")
async def content_manager_contracts(request: Request, status: str = "", limit: int = 100):
    user = await _auth(request)
    manager_id = _contract_manager_id(user)
    query = _contract_filter_for_manager(manager_id)
    if status.strip():
        query["status"] = status.strip()
    docs = await content_manager_contracts_collection.find(query).sort("created_at", -1).limit(max(1, min(limit, 300))).to_list(length=max(1, min(limit, 300)))
    managed = {_pid(p): p for p in await _managed_players(user)}
    out = []
    for doc in docs:
        pid = str(doc.get("player_id") or "")
        p = managed.get(pid, {})
        item = _ser(doc)
        item["player_name"] = _name(p) or doc.get("player_name") or pid
        item["player_photo"] = p.get("photo_url") or p.get("photoUrl") or doc.get("player_photo") or ""
        item["player_club"] = p.get("current_club") or p.get("club") or doc.get("player_club") or ""
        item["player_position"] = p.get("position") or p.get("preferred_position") or doc.get("player_position") or ""
        out.append(item)
    return JSONResponse({"success": True, "contracts": out, "count": len(out)})


@router.post("/content-manager/contracts")
async def create_content_manager_contract(body: ContentManagerContractCreateBody, request: Request):
    user = await _auth(request)
    # Discovery proposals may target any eligible player, not only an existing portfolio member.
    uid = str(body.player_id).strip()
    player = None
    for candidate in await players_collection.find({}).limit(5000).to_list(length=5000):
        if uid in {_pid(candidate), str(candidate.get("user_id") or ""), str(candidate.get("player_id") or ""), str(candidate.get("_id") or "")}:
            player = candidate
            break
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    manager_id = _contract_manager_id(user)
    existing_any = await content_manager_contracts_collection.find_one({
        "player_id": _pid(player),
        "status": {"$in": ["Pending", "pending", "Active", "active"]},
    })
    if existing_any:
        if str(existing_any.get("manager_id") or "") == manager_id:
            raise HTTPException(status_code=409, detail="You already have a pending or active content management relationship with this player")
        raise HTTPException(status_code=409, detail="This player already has a pending or active content management relationship")
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="Contract title is required")
    if body.start_date and body.end_date:
        try:
            s = datetime.fromisoformat(body.start_date); e = datetime.fromisoformat(body.end_date)
            if e <= s:
                raise HTTPException(status_code=422, detail="End date must be after start date")
            try:
                max_end = s.replace(year=s.year + 1)
            except ValueError:
                # February 29 has no matching date in a non-leap year.
                max_end = s.replace(year=s.year + 1, month=2, day=28)
            if e > max_end: raise HTTPException(status_code=422, detail="Contract duration cannot exceed 1 year")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid contract date")
    now = _now(); ref = f"CM-{now.strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"; code=_verification_code()
    manager_name=user.get("name") or user.get("full_name") or user.get("email") or "Content Manager"
    doc={"contract_id":ref,"manager_id":manager_id,"manager_name":manager_name,"player_id":_pid(player),"player_user_id":str(player.get("user_id") or _pid(player)),"player_name":_contract_name(player),"player_photo":player.get("photo_url") or player.get("photoUrl") or "","player_club":player.get("current_club") or player.get("club") or "","player_position":player.get("position") or player.get("preferred_position") or "","title":body.title.strip(),"start_date":body.start_date.strip(),"end_date":body.end_date.strip(),"responsibilities":body.responsibilities.strip(),"notes":body.notes.strip(),"message":body.message.strip(),"verification_code":code,"status":"Pending","relationship_type":"content_manager","created_at":now,"updated_at":now}
    await content_manager_contracts_collection.insert_one(doc)
    if notifications_collection is not None:
        await notifications_collection.insert_one({"unique_id":_pid(player),"player_id":_pid(player),"user_type":"player","type":"content_manager_contract","title":"Content Management Agreement","message":f"{manager_name} sent you a content management agreement for review. Verification code: {code}","reference_id":ref,"read":False,"created_at":now})
    return JSONResponse({"success":True,"contract":_ser(doc),"message":"Content management agreement sent to the player"})


@router.post("/content-manager/contracts/{contract_id}/terminate")
async def terminate_content_manager_contract(contract_id: str, body: ContentManagerContractTerminateBody, request: Request):
    user = await _auth(request)
    manager_id = _contract_manager_id(user)
    doc = await content_manager_contracts_collection.find_one({"manager_id": manager_id, "contract_id": contract_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Content management agreement not found")
    if str(doc.get("status", "")).lower() not in {"active", "pending"}:
        raise HTTPException(status_code=400, detail="Only active or pending agreements can be terminated")
    now = _now()
    status = "Terminated" if str(doc.get("status", "")).lower() == "active" else "Withdrawn"
    await content_manager_contracts_collection.update_one({"_id": doc["_id"]}, {"$set": {"status": status, "terminated_by": "content_manager", "termination_reason": body.reason.strip(), "terminated_at": now, "updated_at": now}})
    if status == "Terminated":
        try:
            await players_collection.update_one({"$or":[{"player_id":str(doc.get("player_id") or "")},{"user_id":str(doc.get("player_id") or "")},{"content_manager_id":manager_id}]},{"$unset":{"content_manager_id":"","content_manager_assigned_at":"","content_manager_contract_id":""}})
        except Exception:
            pass
    if notifications_collection is not None:
        await notifications_collection.insert_one({
            "unique_id": str(doc.get("player_id") or ""), "player_id": str(doc.get("player_id") or ""), "user_type": "player",
            "type": "content_manager_contract_terminated", "title": "Content Management Agreement Updated",
            "message": f"The content management agreement {contract_id} was {status.lower()} by the content manager.",
            "reference_id": contract_id, "read": False, "created_at": now,
        })
    updated = await content_manager_contracts_collection.find_one({"_id": doc["_id"]})
    return JSONResponse({"success": True, "contract": _ser(updated)})


# ---------------------------------------------------------------------------
# Content manager notifications
# ---------------------------------------------------------------------------

async def _ensure_manager_stats_status_notifications(user: dict) -> None:
    """Create one professional manager notification for each request status transition."""
    if stats_requests_collection is None or notifications_collection is None:
        return
    manager_ids = list(_manager_identity(user))
    manager_id = _manager_id(user)
    if not manager_ids or not manager_id:
        return
    reqs = await stats_requests_collection.find({
        "manager_id": {"$in": manager_ids},
        "status": {"$in": [
            "Assigned", "assigned", "In Progress", "in_progress", "Completed", "completed",
            "Verified", "verified", "Approved", "approved", "Rejected", "rejected", "Cancelled", "cancelled",
        ]},
    }).sort("updated_at", -1).limit(100).to_list(length=100)
    for req in reqs:
        status = str(req.get("status") or "").strip().lower()
        ref = str(req.get("reference_id") or req.get("request_id") or req.get("_id") or "")
        if not status or not ref:
            continue
        event_key = f"manager_stats_request_status:{manager_id}:{ref}:{status}"
        if await notifications_collection.find_one({
            "manager_id": manager_id, "type": "stats_request_status", "event_key": event_key,
        }):
            continue
        labels = {
            "assigned": ("Stats Request Assigned", "A stats request you submitted has been assigned for processing."),
            "in_progress": ("Stats Tracking In Progress", "A player match-statistics request is now being processed."),
            "completed": ("Stats Tracking Completed", "A stats request has completed processing; the player's match result and statistics are now available."),
            "verified": ("Match Statistics Verified", "A player's match statistics have been verified and are now available in the shared statistics pipeline."),
            "approved": ("Match Statistics Approved", "A player's match statistics have been approved and are now available."),
            "rejected": ("Stats Request Rejected", "A stats request was rejected. Review the request activity for the latest status."),
            "cancelled": ("Stats Request Cancelled", "A stats request was cancelled. Any applicable player-wallet refund has been recorded."),
        }
        title, message = labels.get(status, ("Stats Request Updated", f"Stats request {ref} changed to {req.get('status')}."))
        await notifications_collection.insert_one({
            "unique_id": manager_id, "manager_id": manager_id, "user_id": manager_id,
            "user_type": "content_manager", "type": "stats_request_status", "title": title,
            "message": message, "reference_id": ref, "player_id": str(req.get("player_id") or ""),
            "request_status": req.get("status"), "event_key": event_key, "read": False, "created_at": _now(),
        })


def _manager_notification_filter(user: dict) -> dict:
    ids = list(_manager_identity(user))
    if not ids:
        return {"_id": {"$exists": False}}
    return {"$or": [
        {"unique_id": {"$in": ids}},
        {"manager_id": {"$in": ids}},
        {"content_manager_id": {"$in": ids}},
        {"user_id": {"$in": ids}},
    ]}


@router.get("/content-manager/notifications")
async def content_manager_notifications(request: Request, limit: int = 100):
    user = await _auth(request)
    await _ensure_manager_stats_status_notifications(user)
    docs = await notifications_collection.find(_manager_notification_filter(user)).sort("created_at", -1).limit(max(1, min(limit, 200))).to_list(length=200)
    return JSONResponse({"success": True, "notifications": _ser(docs)})


@router.patch("/content-manager/notifications/read-all")
async def content_manager_notifications_read_all(request: Request):
    user = await _auth(request)
    await notifications_collection.update_many(_manager_notification_filter(user), {"$set": {"read": True, "read_at": _now()}})
    return JSONResponse({"success": True})


@router.patch("/content-manager/notifications/{notif_id}/read")
async def content_manager_notification_read(notif_id: str, request: Request):
    user = await _auth(request)
    try:
        ident_filter = {"_id": ObjectId(notif_id)}
    except Exception:
        ident_filter = {"$or": [{"_id": notif_id}, {"id": notif_id}]}
    result = await notifications_collection.update_one(
        {"$and": [_manager_notification_filter(user), ident_filter]},
        {"$set": {"read": True, "read_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return JSONResponse({"success": True})


# ---------------------------------------------------------------------------
# Request history
# ---------------------------------------------------------------------------

@router.get("/content-manager/stats/requests")
async def content_manager_requests(request: Request, limit: int = 200):
    user = await _auth(request)
    managed = await _managed_players(user)
    ids = list({v for p in managed for v in (_pid(p), str(p.get("user_id") or "")) if v})
    if not ids:
        return JSONResponse({"success": True, "requests": []})
    reqs = await stats_requests_collection.find({"player_id": {"$in": ids}}).sort("submitted_at", -1).limit(max(1, min(limit, 500))).to_list(length=500)
    by_id = {_pid(p): p for p in managed}
    out = []
    for r in reqs:
        p = by_id.get(str(r.get("player_id")), {})
        out.append({
            **_ser(r),
            "player_name": _name(p),
            "player_photo": p.get("photo_url") or p.get("photoUrl") or "",
            "player_club": p.get("current_club") or p.get("club") or "",
            "player_position": p.get("position") or p.get("preferred_position") or "",
        })
    return JSONResponse({"success": True, "requests": out})


# ---------------------------------------------------------------------------
# Single/bulk stats request submission using PLAYER wallets
# ---------------------------------------------------------------------------

@router.post("/content-manager/stats/requests/bulk")
async def submit_bulk_stats_requests(body: BulkStatsRequestBody, request: Request):
    user = await _auth(request)
    requested_ids = []
    for raw in body.player_ids:
        v = str(raw or "").strip()
        if v and v not in requested_ids:
            requested_ids.append(v)
    if not requested_ids:
        raise HTTPException(status_code=400, detail="Select at least one managed player")
    if len(requested_ids) > 100:
        raise HTTPException(status_code=400, detail="A maximum of 100 players can be submitted at once")
    if not body.match_date or not body.home_team.strip() or not body.away_team.strip() or not body.venue_state.strip() or not body.venue_address.strip() or not body.contact_phone.strip():
        raise HTTPException(status_code=422, detail="Match date, both teams, venue address/state and contact phone are required")

    players = [await _get_managed_player(user, uid) for uid in requested_ids]
    heatmap_ids = {str(v) for v in body.heatmap_player_ids}
    plans = []
    total_cost = 0
    for p in players:
        heatmap = _pid(p) in heatmap_ids or str(p.get("user_id") or "") in heatmap_ids
        cost = _base_cost(p) + (1 if heatmap else 0)
        plans.append((p, heatmap, cost))
        total_cost += cost

    # Validate every wallet before mutating any wallet.
    wallets: Dict[str, dict] = {}
    for p, _, _ in plans:
        pid = _pid(p)
        td = await player_tokens_collection.find_one({"$or": [{"player_id": pid}, {"player_id": str(p.get("user_id") or "")} ]})
        wallets[pid] = td or {}
        balance = int((td or {}).get("balance", 0))
        locked = await _legacy_locked_tokens(p)
        available = max(0, balance - locked)
        requested_cost = _base_cost(p) + (1 if (pid in heatmap_ids or str(p.get("user_id") or "") in heatmap_ids) else 0)
        if available < requested_cost:
            raise HTTPException(status_code=402, detail=f"Insufficient available tokens for {_name(p) or pid}. Available: {available}")

    created: List[dict] = []
    debited: List[tuple[str, int]] = []
    try:
        for p, heatmap, cost in plans:
            pid = _pid(p)
            uid = str(p.get("user_id") or pid)
            # Atomic conditional decrement: concurrency-safe and never negative.
            td = wallets[pid]
            selector = {"_id": td["_id"], "balance": {"$gte": cost}} if td.get("_id") is not None else {"player_id": pid, "balance": {"$gte": cost}}
            result = await player_tokens_collection.update_one(selector, {"$inc": {"balance": -cost}, "$set": {"updated_at": _now()}})
            if result.modified_count != 1:
                raise HTTPException(status_code=409, detail=f"Token balance changed while submitting for {_name(p) or pid}; nothing else was submitted")
            debited.append((pid, cost, td.get("_id")))

            ref_id = _request_ref()
            req_doc = {
                "player_id": pid,
                "user_id": uid,
                "reference_id": ref_id,
                "request_id": ref_id,
                "home_team": body.home_team.strip(),
                "away_team": body.away_team.strip(),
                "match_date": body.match_date,
                "match_time": body.match_time,
                "jersey_number": str(body.jersey_numbers.get(pid) or body.jersey_numbers.get(uid) or p.get("jersey_number") or p.get("jerseyNumber") or ""),
                "player_represents": body.player_represents or "home",
                "match_type": body.match_type or "League",
                "heatmap": heatmap,
                "heatmap_required": heatmap,
                "token_cost": cost,
                "token_deducted": True,
                "deducted_from_player_wallet": True,
                "submitted_by": _manager_id(user),
                "submitted_by_role": _manager_role(user),
                "submitted_via": "content_manager_dashboard",
                "manager_id": _manager_id(user),
                "venue_address": body.venue_address.strip(),
                "venue_country": body.venue_country.strip(),
                "venue_state": body.venue_state.strip(),
                "venue_lga": body.venue_lga.strip(),
                "contact_phone": body.contact_phone.strip(),
                "status": "Pending",
                "submitted_at": _now(),
                "created_at": _now(),
            }
            insert_result = await stats_requests_collection.insert_one(req_doc)
            req_doc["_id"] = insert_result.inserted_id
            created.append(req_doc)

            if token_transactions_collection is not None:
                await token_transactions_collection.insert_one({
                    "player_id": pid,
                    "unique_id": pid,
                    "user_type": "player",
                    "type": "debit",
                    "amount": f"-{cost}",
                    "tokens_debited": cost,
                    "description": f"Stats request submitted by content manager — {cost} token(s)",
                    "status": "completed",
                    "reference_id": ref_id,
                    "manager_id": _manager_id(user),
                    "created_at": _now(),
                })

            if notifications_collection is not None:
                await notifications_collection.insert_one({
                    "unique_id": pid,
                    "player_id": pid,
                    "user_type": "player",
                    "type": "stats_request",
                    "title": "Stats Request Submitted",
                    "message": f"A content manager submitted a {body.match_type or 'match'} stats request for you. {cost} token(s) were deducted from your wallet.",
                    "reference_id": ref_id,
                    "read": False,
                    "created_at": _now(),
                })

    except HTTPException:
        # Compensating rollback for already-debited players.
        for pid, cost, wallet_id in debited:
            try:
                wallet_filter = {"_id": wallet_id} if wallet_id is not None else {"player_id": pid}
                await player_tokens_collection.update_one(wallet_filter, {"$inc": {"balance": cost}, "$set": {"updated_at": _now()}})
            except Exception:
                if logger:
                    logger.exception("content-manager token rollback failed for %s", pid)
        for doc in created:
            try:
                await stats_requests_collection.delete_one({"_id": doc.get("_id")})
            except Exception:
                pass
        raise
    except Exception as exc:
        for pid, cost, wallet_id in debited:
            try:
                wallet_filter = {"_id": wallet_id} if wallet_id is not None else {"player_id": pid}
                await player_tokens_collection.update_one(wallet_filter, {"$inc": {"balance": cost}, "$set": {"updated_at": _now()}})
            except Exception:
                if logger:
                    logger.exception("content-manager token rollback failed for %s", pid)
        for doc in created:
            try:
                await stats_requests_collection.delete_one({"_id": doc.get("_id")})
            except Exception:
                pass
        if logger:
            logger.exception("submit_bulk_stats_requests error")
        raise HTTPException(status_code=500, detail="Unable to complete the bulk stats request")

    return JSONResponse({
        "success": True,
        "count": len(created),
        "total_token_cost": total_cost,
        "requests": _ser(created),
        "message": f"{len(created)} stats request(s) submitted successfully. {total_cost} player token(s) deducted.",
    })


@router.delete("/content-manager/stats/requests/{ref_id}")
async def cancel_manager_request(ref_id: str, request: Request):
    user = await _auth(request)
    req = await stats_requests_collection.find_one({"$or": [{"reference_id": ref_id}, {"request_id": ref_id}]})
    if not req:
        raise HTTPException(status_code=404, detail="Stats request not found")
    await _get_managed_player(user, str(req.get("player_id") or ""))
    if str(req.get("status", "")).lower() != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
    refunded = int(req.get("token_cost", 0))
    pid = str(req.get("player_id") or "")
    managed_player = await _get_managed_player(user, pid)
    wallet_ids = [pid, str(managed_player.get("user_id") or "")]
    if req.get("token_deducted") is True and refunded:
        await player_tokens_collection.update_one({"$or": [{"player_id": v} for v in wallet_ids if v]}, {"$inc": {"balance": refunded}, "$set": {"updated_at": _now()}})
        if token_transactions_collection is not None:
            await token_transactions_collection.insert_one({
                "player_id": pid, "unique_id": pid, "user_type": "player", "type": "refund",
                "amount": f"+{refunded}", "tokens_credited": refunded,
                "description": f"Stats request cancellation refund — {refunded} token(s)",
                "status": "completed", "reference_id": ref_id, "manager_id": _manager_id(user), "created_at": _now(),
            })
    await stats_requests_collection.update_one({"_id": req["_id"]}, {"$set": {"status": "Cancelled", "cancelled_at": _now(), "updated_at": _now()}})
    if notifications_collection is not None:
        await notifications_collection.insert_one({
            "unique_id": pid, "player_id": pid, "user_type": "player", "type": "stats_request_status",
            "title": "Stats Request Cancelled",
            "message": f"Your content manager cancelled stats request {ref_id}. {refunded} token(s) were refunded to your wallet." if refunded else f"Your content manager cancelled stats request {ref_id}.",
            "reference_id": ref_id, "request_status": "Cancelled", "token_refunded": refunded,
            "event_key": f"stats_request_status:{ref_id}:cancelled", "read": False, "created_at": _now(),
        })
    return JSONResponse({"success": True, "refunded": refunded, "reference_id": ref_id})
