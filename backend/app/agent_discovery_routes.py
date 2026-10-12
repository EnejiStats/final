"""
ENEJISTATS — Agent Discovery Routes  (agent_discovery_routes.py)
================================================================
Standalone FastAPI router that provides the advanced player search /
discovery endpoint consumed by the enhanced "Find Players" section of
the Agent Dashboard.

ROUTES
------
  GET  /api/agent/search-players        advanced multi-filter player search
  GET  /api/agent/discovery/metadata    continents, africa-regions, levels, positions

HOW TO INTEGRATE IN main.py
----------------------------
    import agent_discovery_routes as _agent_disc
    _agent_disc._setup_dependencies(globals())
    app.include_router(_agent_disc.router)

Register this router AFTER all collection/helper symbols are bound in
main's namespace and BEFORE (or alongside) agent_dashboard_routes — the
critical ordering constraint is that /api/agent/search-players must
be declared before FastAPI's /api/agent/{agent_id}/... parameterised
routes so the literal segment "search-players" is not captured as an
agent_id value.

DEPENDENCY INJECTION PATTERN
-----------------------------
Identical to agent_dashboard_routes.py — no module-level import from
main.py avoids circular imports.  All shared state is injected by
_setup_dependencies() which is called once by main.py after its own
initialisation is complete.
"""

# ============================================================
# START: IMPORTS
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

from datetime import datetime, timedelta
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

# All geographic constants come from the single source of truth.
# Do NOT redefine CONTINENT_CODES, AFRICA_SUB_REGIONS, or country
# name mappings here — import them directly.
from location_module import (
    AFRICA_SUB_REGIONS,
    CONTINENT_CODES,
    COUNTRY_NAMES,
)

# ============================================================
# END: IMPORTS
# ============================================================

# ============================================================
# START: CANONICAL DEPENDENCY CONTRACT
# ============================================================

# ============================================================
# MODULE-LEVEL PLACEHOLDERS  (all filled by _setup_dependencies)
# ============================================================

database                  = None
agents_collection         = None
players_collection        = None
player_stats_collection   = None   # canonical main.py collection
proposals_collection      = None   # module-specific enrichment collection
get_agent_user            = None   # canonical main.py authentication/role guard
MongoSerializer           = None   # canonical main.py serializer
logger                    = None

_DEPS_READY = False


# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Populate every module-level placeholder from main.py's namespace.
    Called once by main.py immediately after importing this module::

        import agent_discovery_routes as _agent_disc
        _agent_disc._setup_dependencies(globals())
        app.include_router(_agent_disc.router)
    """
    global _DEPS_READY
    global database
    global agents_collection, players_collection, player_stats_collection
    global proposals_collection
    global get_agent_user
    global MongoSerializer, logger

    if _DEPS_READY:
        return

    _m = main_globals

    def _require(key: str):
        if key not in _m:
            raise RuntimeError(
                f"[agent_discovery] _setup_dependencies: required symbol "
                f"'{key}' is missing from main.py globals."
            )
        return _m[key]

    database = _require("database")
    agents_collection  = _require("agents_collection")
    players_collection = _require("players_collection")
    player_stats_collection = _require("player_stats_collection")
    get_agent_user     = _require("get_agent_user")
    MongoSerializer    = _require("MongoSerializer")
    logger             = _require("logger")

    # Module-specific proposal enrichment. main.py does not expose a
    # proposal collection, so this dependency remains domain-local.
    proposals_collection = _m.get("proposals_collection")
    if proposals_collection is None:
        proposals_collection = database["agent_proposals"]

    _DEPS_READY = True
    logger.debug("[agent_discovery] _setup_dependencies complete")


# ============================================================
# END: CANONICAL DEPENDENCY CONTRACT
# ============================================================

# ============================================================
# START: MODULE CONFIGURATION / DOMAIN CONSTANTS
# ============================================================
# POSITION CONSTANTS
# Geographic constants (CONTINENT_CODES, AFRICA_SUB_REGIONS,
# COUNTRY_NAMES) are imported from location_module — the single
# source of truth.  Do not duplicate them here.
# ============================================================

# Position category → specific position codes
POSITION_CATEGORIES: Dict[str, List[str]] = {
    "Goalkeeper": ["GK"],
    "Defender":   ["CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB", "SW"],
    "Midfielder": ["CDM", "DM", "CM", "B2B", "CAM", "AM", "LM", "RM"],
    "Forward":    ["LW", "RW", "CF", "SS", "ST", "IF"],
}

# Recognised playing levels / categories
PLAYER_LEVELS: List[str] = [
    "Professional", "Semi-Professional", "Academy", "University",
    "Amateur", "Grassroots", "Youth", "Local", "Other",
]


# ============================================================
# START: ROUTER EXPORT
# ============================================================

router = APIRouter()


# ============================================================
# END: ROUTER EXPORT
# ============================================================

# ============================================================
# START: MODULE-SPECIFIC HELPERS
# ============================================================
# PRIVATE HELPERS
# ============================================================

async def _resolve_agent(request: Request) -> Dict[str, Any]:
    """Resolve the authenticated agent through main.py's canonical guard."""
    agent = await get_agent_user(request)
    return MongoSerializer.serialize_document(agent)


def _resolve_country_values(codes: List[str]) -> List[str]:
    """
    Given ISO-2 codes return a flat list of [code, name, name_variants…]
    that can be used in a MongoDB $in query against nationality/country fields.
    Players may store country as name ("Nigeria") or code ("NG") — we match both.

    Country display names are resolved from COUNTRY_NAMES in location_module,
    the single source of truth for all ISO-code → name mappings.
    """
    values: List[str] = []
    for code in codes:
        code_upper = code.strip().upper()
        values.append(code_upper)
        name = COUNTRY_NAMES.get(code_upper)
        if name:
            values.append(name)
            # Some registrations store alternate forms
            values.append(name.lower())
            values.append(name.title())
    return list(dict.fromkeys(values))   # deduplicate, preserve order


def _resolve_all_country_codes(
    countries: List[str],
    continents: List[str],
    africa_regions: List[str],
) -> List[str]:
    """
    Combine explicit country codes with codes implied by continent/africa-region
    selections.  Returns deduplicated list of ISO-2 codes.

    CONTINENT_CODES and AFRICA_SUB_REGIONS are imported from location_module.
    """
    codes: set = set(c.strip().upper() for c in countries if c.strip())
    for cont in continents:
        codes.update(CONTINENT_CODES.get(cont, []))
    for reg in africa_regions:
        codes.update(AFRICA_SUB_REGIONS.get(reg, []))
    return list(codes)


def _build_player_query(
    q:                   Optional[str],
    country_codes:       List[str],
    states:              List[str],
    lgas:                List[str],
    cities:              List[str],
    levels:              List[str],
    positions:           List[str],
    age_min:             Optional[int],
    age_max:             Optional[int],
    height_min:          Optional[int],
    height_max:          Optional[int],
    weight_min:          Optional[int],
    weight_max:          Optional[int],
    preferred_foot:      Optional[str],
) -> Dict[str, Any]:
    """
    Build a MongoDB $and query dict from profile/location filter parameters.
    Only adds clauses for filters that are actually active (non-empty/non-None).
    """
    clauses: List[Dict[str, Any]] = []

    # ── Text search ──────────────────────────────────────────
    if q and q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        clauses.append({"$or": [
            {"name": rx},
            {"first_name": rx},
            {"last_name": rx},
            {"full_name": rx},
            {"fullName": rx},
            {"club": rx},
            {"current_club": rx},
            {"currentClub": rx},
            {"nationality": rx},
            {"player_id": rx},
            {"user_id": rx},
        ]})

    # ── Location: country / continent / africa-region ────────
    if country_codes:
        country_values = _resolve_country_values(country_codes)
        clauses.append({"$or": [
            {"nationality":  {"$in": country_values}},
            {"country":      {"$in": country_values}},
            {"country_code": {"$in": [c.upper() for c in country_codes]}},
        ]})

    # ── Location: state / province ───────────────────────────
    if states:
        normalized = [s.strip() for s in states if s.strip()]
        if normalized:
            clauses.append({"$or": [
                {"state":          {"$in": normalized}},
                {"state_province": {"$in": normalized}},
                {"province":       {"$in": normalized}},
                {"region":         {"$in": normalized}},
            ]})

    # ── Location: LGA / sub-region ───────────────────────────
    if lgas:
        normalized = [l.strip() for l in lgas if l.strip()]
        if normalized:
            clauses.append({"$or": [
                {"lga":       {"$in": normalized}},
                {"lga_name":  {"$in": normalized}},
                {"district":  {"$in": normalized}},
                {"county":    {"$in": normalized}},
                {"ward":      {"$in": normalized}},
            ]})

    # ── Location: city ───────────────────────────────────────
    if cities:
        normalized = [c.strip() for c in cities if c.strip()]
        if normalized:
            clauses.append({"$or": [
                {"city": {"$in": normalized}},
                {"town": {"$in": normalized}},
            ]})

    # ── Player level / category ──────────────────────────────
    if levels:
        # Accept case-insensitive matches
        level_values: List[str] = []
        for lvl in levels:
            for variant in (lvl, lvl.lower(), lvl.upper(), lvl.title()):
                level_values.append(variant)
        level_values = list(dict.fromkeys(level_values))
        clauses.append({"$or": [
            {"playing_category": {"$in": level_values}},
            {"playingCategory":  {"$in": level_values}},
            {"category":         {"$in": level_values}},
            {"level":            {"$in": level_values}},
            {"player_level":     {"$in": level_values}},
        ]})

    # ── Position ─────────────────────────────────────────────
    if positions:
        pos_upper = [p.strip().upper() for p in positions if p.strip()]
        if pos_upper:
            clauses.append({"$or": [
                {"position":          {"$in": pos_upper}},
                {"preferred_position":{"$in": pos_upper}},
                {"preferredPosition": {"$in": pos_upper}},
                {"position_category": {"$in": pos_upper}},
            ]})

    # ── Age range ────────────────────────────────────────────
    if age_min is not None or age_max is not None:
        now = MongoSerializer.now_utc()
        dob_filter: Dict[str, Any] = {}
        if age_max is not None:
            # Oldest allowed birth date for the requested maximum age.
            min_dob = now - timedelta(days=365.25 * (age_max + 1))
            dob_filter["$gte"] = min_dob.strftime("%Y-%m-%d")
        if age_min is not None:
            # Latest allowed birth date for the requested minimum age.
            max_dob = now - timedelta(days=365.25 * age_min)
            dob_filter["$lte"] = max_dob.strftime("%Y-%m-%d")
        if dob_filter:
            clauses.append({"$or": [
                {"dob":           dob_filter},
                {"date_of_birth": dob_filter},
                {"dateOfBirth":   dob_filter},
            ]})

    # ── Height ───────────────────────────────────────────────
    if height_min is not None or height_max is not None:
        h: Dict[str, Any] = {}
        if height_min is not None: h["$gte"] = height_min
        if height_max is not None: h["$lte"] = height_max
        clauses.append({"$or": [
            {"height": h},
            {"height_cm": h},
        ]})

    # ── Weight ───────────────────────────────────────────────
    if weight_min is not None or weight_max is not None:
        w: Dict[str, Any] = {}
        if weight_min is not None: w["$gte"] = weight_min
        if weight_max is not None: w["$lte"] = weight_max
        clauses.append({"$or": [
            {"weight": w},
            {"weight_kg": w},
        ]})

    # ── Preferred foot ───────────────────────────────────────
    if preferred_foot and preferred_foot.strip():
        rx = {"$regex": re.escape(preferred_foot.strip()), "$options": "i"}
        clauses.append({"$or": [
            {"dominant_foot":   rx},
            {"preferred_foot":  rx},
            {"preferredFoot":   rx},
            {"foot":            rx},
        ]})

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _has_stats_filters(
    goals_min, goals_max, assists_min, assists_max,
    matches_min, matches_max, rating_min, rating_max,
    pass_accuracy_min, pass_accuracy_max, tackles_min, tackles_max,
    interceptions_min, interceptions_max, clean_sheets_min, clean_sheets_max,
) -> bool:
    """Return True if any stats-range filter is active."""
    return any(v is not None for v in [
        goals_min, goals_max, assists_min, assists_max,
        matches_min, matches_max, rating_min, rating_max,
        pass_accuracy_min, pass_accuracy_max, tackles_min, tackles_max,
        interceptions_min, interceptions_max, clean_sheets_min, clean_sheets_max,
    ])


async def _get_stats_filtered_ids(
    candidate_ids:       List[str],
    goals_min:           Optional[float],
    goals_max:           Optional[float],
    assists_min:         Optional[float],
    assists_max:         Optional[float],
    matches_min:         Optional[float],
    matches_max:         Optional[float],
    rating_min:          Optional[float],
    rating_max:          Optional[float],
    pass_accuracy_min:   Optional[float],
    pass_accuracy_max:   Optional[float],
    tackles_min:         Optional[float],
    tackles_max:         Optional[float],
    interceptions_min:   Optional[float],
    interceptions_max:   Optional[float],
    clean_sheets_min:    Optional[float],
    clean_sheets_max:    Optional[float],
) -> List[str]:
    """
    Run a MongoDB aggregation over player_stats_collection to find
    player IDs whose *total/average* stats satisfy the provided ranges.

    Returns the list of qualifying player_id strings.
    An empty list means "stats filters are active but zero players match".
    """
    if player_stats_collection is None:
        return candidate_ids  # can't filter, pass through

    pipeline: List[Dict[str, Any]] = [
        # Stage 1: filter to candidates with approved/verified stats
        {"$match": {
            "player_id": {"$in": candidate_ids},
            "status": {"$in": ["approved", "verified", "completed", "published"]},
        }},
        # Stage 2: aggregate per player
        {"$group": {
            "_id":              "$player_id",
            "total_goals":      {"$sum": "$stats.goals"},
            "total_assists":    {"$sum": "$stats.assists"},
            "total_matches":    {"$sum": 1},
            "avg_rating":       {"$avg": "$performance_score"},
            "avg_pass_acc":     {"$avg": "$stats.pass_accuracy"},
            "total_tackles":    {"$sum": "$stats.tackles"},
            "total_inter":      {"$sum": "$stats.interceptions"},
            "total_cs":         {"$sum": "$stats.clean_sheets"},
        }},
    ]

    # Stage 3: build the stats filter clause
    def _rng(field: str, mn, mx) -> Optional[Dict]:
        if mn is None and mx is None:
            return None
        f: Dict[str, Any] = {}
        if mn is not None: f["$gte"] = mn
        if mx is not None: f["$lte"] = mx
        return {field: f}

    stats_and: List[Dict[str, Any]] = [
        c for c in [
            _rng("total_goals",   goals_min,         goals_max),
            _rng("total_assists", assists_min,        assists_max),
            _rng("total_matches", matches_min,        matches_max),
            _rng("avg_rating",    rating_min,         rating_max),
            _rng("avg_pass_acc",  pass_accuracy_min,  pass_accuracy_max),
            _rng("total_tackles", tackles_min,        tackles_max),
            _rng("total_inter",   interceptions_min,  interceptions_max),
            _rng("total_cs",      clean_sheets_min,   clean_sheets_max),
        ] if c is not None
    ]

    if stats_and:
        match_clause = stats_and[0] if len(stats_and) == 1 else {"$and": stats_and}
        pipeline.append({"$match": match_clause})

    pipeline.append({"$project": {"_id": 1}})

    results = await player_stats_collection.aggregate(pipeline).to_list(length=10_000)
    return [r["_id"] for r in results]


async def _fetch_stats_summaries(player_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch aggregated career stats for a list of player IDs.
    Returns a dict keyed by player_id.
    """
    if player_stats_collection is None or not player_ids:
        return {}

    pipeline = [
        {"$match": {"player_id": {"$in": player_ids}}},
        {"$group": {
            "_id":            "$player_id",
            "totalGoals":     {"$sum": "$stats.goals"},
            "totalAssists":   {"$sum": "$stats.assists"},
            "matchesPlayed":  {"$sum": 1},
            "avgRating":      {"$avg": "$performance_score"},
            "avgPassAcc":     {"$avg": "$stats.pass_accuracy"},
            "totalTackles":   {"$sum": "$stats.tackles"},
            "totalInter":     {"$sum": "$stats.interceptions"},
            "totalCS":        {"$sum": "$stats.clean_sheets"},
        }},
    ]

    results = await player_stats_collection.aggregate(pipeline).to_list(length=1_000)
    return {r["_id"]: r for r in results}


def _calc_age(dob_raw: Any) -> Optional[int]:
    """Return integer age from a date-of-birth value, or None."""
    if not dob_raw:
        return None
    try:
        if isinstance(dob_raw, datetime):
            dob = dob_raw
        else:
            dob = datetime.fromisoformat(str(dob_raw).replace("Z", "+00:00"))
        now = MongoSerializer.now_utc()
        if dob.tzinfo is None:
            dob = dob.replace(tzinfo=timezone.utc)
        delta = now - dob
        return int(delta.days / 365.25)
    except Exception:
        return None


def _compute_contract_status(contract: Optional[Dict[str, Any]]) -> str:
    """Derive contract status — replicates the logic in agent_dashboard_routes.py."""
    if not contract:
        return "none"
    end_raw = contract.get("endDate") or contract.get("end_date")
    if not end_raw:
        return "none"
    try:
        if isinstance(end_raw, datetime):
            end = end_raw if end_raw.tzinfo else end_raw.replace(tzinfo=timezone.utc)
        else:
            end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
        now = MongoSerializer.now_utc()
        if end < now:
            return "expired"
        if (end - now).days <= 60:
            return "expiring_soon"
        return "active"
    except Exception:
        return "none"


def _resolve_player_name(p: Dict[str, Any]) -> str:
    first  = (p.get("first_name")  or p.get("firstName")  or "").strip()
    last   = (p.get("last_name")   or p.get("lastName")   or "").strip()
    middle = (p.get("middle_name") or p.get("middleName") or "").strip()
    if first or last:
        return " ".join(x for x in [first, middle, last] if x)
    return (p.get("name") or p.get("fullName") or p.get("full_name") or "")


def _serialize_player_full(
    p: Dict[str, Any],
    stats: Optional[Dict[str, Any]] = None,
    pending_proposal_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extended serialiser — includes all fields _serialize_player returns PLUS
    location detail, physical attributes, and optional stats summary.
    """
    contract        = p.get("contract") or {}
    contract_status = _compute_contract_status(contract)

    player_id = (
        p.get("player_id") or p.get("user_id") or str(p.get("_id", ""))
    )
    dob = (
        p.get("dob") or p.get("date_of_birth") or p.get("dateOfBirth") or None
    )

    result: Dict[str, Any] = {
        # --- Core identity ---
        "id":             player_id,
        "name":           _resolve_player_name(p),
        "position":       (
            p.get("position") or p.get("preferredPosition")
            or p.get("preferred_position") or ""
        ),
        "positionCategory": (
            p.get("position_category") or p.get("positionCategory") or None
        ),
        "club":           (
            p.get("club") or p.get("current_club") or p.get("currentClub") or None
        ),
        "nationality":    p.get("nationality") or None,
        "dob":            dob,
        "age":            _calc_age(dob),
        "photoUrl":       p.get("photoUrl") or p.get("photo_url") or None,
        "category":       (
            p.get("playing_category") or p.get("playingCategory")
            or p.get("category") or p.get("level") or None
        ),
        "marketValue":    p.get("marketValue") or p.get("market_value") or None,
        # --- Location detail ---
        "country":        p.get("country") or p.get("nationality") or None,
        "state":          p.get("state") or p.get("state_province") or p.get("province") or p.get("region") or None,
        "lga":            p.get("lga") or p.get("lga_name") or p.get("district") or p.get("county") or p.get("ward") or None,
        "city":           p.get("city") or p.get("town") or None,
        # --- Physical ---
        "height":         p.get("height") or p.get("height_cm") or None,
        "weight":         p.get("weight") or p.get("weight_kg") or None,
        "preferredFoot":  (
            p.get("dominant_foot") or p.get("preferred_foot")
            or p.get("preferredFoot") or p.get("foot") or None
        ),
        "gender":         p.get("gender") or None,
        # --- Contract ---
        "contractStatus": contract_status,
        "contract": {
            "startDate": contract.get("startDate") or contract.get("start_date"),
            "endDate":   contract.get("endDate")   or contract.get("end_date"),
        } if contract else None,
        # --- Proposal state ---
        "pendingProposalId": pending_proposal_id,
    }

    # --- Stats summary (optional) ---
    if stats:
        result["stats"] = {
            "totalGoals":    round(stats.get("totalGoals", 0) or 0, 1),
            "totalAssists":  round(stats.get("totalAssists", 0) or 0, 1),
            "matchesPlayed": int(stats.get("matchesPlayed", 0) or 0),
            "avgRating":     round(stats.get("avgRating", 0) or 0, 2),
            "avgPassAcc":    round(stats.get("avgPassAcc", 0) or 0, 1),
            "totalTackles":  round(stats.get("totalTackles", 0) or 0, 1),
            "totalInter":    round(stats.get("totalInter", 0) or 0, 1),
            "totalCS":       round(stats.get("totalCS", 0) or 0, 1),
        }
    else:
        result["stats"] = None

    return result


# ============================================================
# END: MODULE-SPECIFIC HELPERS
# ============================================================

# ============================================================
# START: AUTHENTICATION / AUTHORIZATION INTEGRATION
# Authentication is delegated to main.py via get_agent_user().
# ============================================================
# END: AUTHENTICATION / AUTHORIZATION INTEGRATION
# ============================================================

# ============================================================
# START: API ROUTES
# ============================================================
# ROUTES
# ============================================================
# IMPORTANT: These static-path routes MUST be registered before
# the parameterised /api/agent/{agent_id}/... routes so that
# FastAPI does not treat "search-players" as an agent_id value.
# ============================================================


# ------------------------------------------------------------
# GET /api/agent/discovery/metadata
# Returns all dropdown/chip data the frontend needs to build
# the filter panel without any hardcoded values.
# ------------------------------------------------------------

@router.get("/api/agent/discovery/metadata")
async def get_discovery_metadata(request: Request):
    """
    Returns the static metadata the discovery filter panel needs:
    continents, africa sub-regions, player levels, and position data.
    Authentication is required so only agents can access it.

    Geographic data (continents, africa_regions, africa_region_codes)
    is sourced from location_module — the single source of truth.
    """
    await _resolve_agent(request)   # auth check only

    positions_flat: List[str] = []
    for pos_list in POSITION_CATEGORIES.values():
        positions_flat.extend(pos_list)

    return JSONResponse({
        "continents":          list(CONTINENT_CODES.keys()),
        "africa_regions":      list(AFRICA_SUB_REGIONS.keys()),
        "africa_region_codes": AFRICA_SUB_REGIONS,
        "player_levels":       PLAYER_LEVELS,
        "position_categories": {
            cat: codes for cat, codes in POSITION_CATEGORIES.items()
        },
        "all_positions":       list(dict.fromkeys(positions_flat)),
    })


# ------------------------------------------------------------
# GET /api/agent/search-players
# Advanced multi-filter player discovery endpoint.
# MUST be declared before /api/agent/{agent_id}/... routes.
# ------------------------------------------------------------

@router.get("/api/agent/search-players")
async def search_players(
    request: Request,

    # ── Text search ──────────────────────────────────────
    q: Optional[str] = Query(default=None, description="Text search: name, club, nationality, ID"),

    # ── Location ─────────────────────────────────────────
    countries:      List[str] = Query(default=[], description="ISO-2 country codes, e.g. NG, GH"),
    continents:     List[str] = Query(default=[], description="Continent names"),
    africa_regions: List[str] = Query(default=[], description="Africa sub-region names"),
    states:         List[str] = Query(default=[], description="State / province names"),
    lgas:           List[str] = Query(default=[], description="LGA / sub-region names"),
    cities:         List[str] = Query(default=[], description="City names"),

    # ── Player profile ───────────────────────────────────
    levels:              List[str] = Query(default=[], description="Playing levels/categories"),
    positions:           List[str] = Query(default=[], description="Specific position codes, e.g. GK, CB"),
    position_categories: List[str] = Query(default=[], description="Broad position categories"),

    # ── Age & physical ───────────────────────────────────
    age_min:       Optional[int] = Query(default=None, ge=10, le=60),
    age_max:       Optional[int] = Query(default=None, ge=10, le=60),
    height_min:    Optional[int] = Query(default=None, ge=100, le=230),
    height_max:    Optional[int] = Query(default=None, ge=100, le=230),
    weight_min:    Optional[int] = Query(default=None, ge=30, le=150),
    weight_max:    Optional[int] = Query(default=None, ge=30, le=150),
    preferred_foot: Optional[str] = Query(default=None),

    # ── Stats ranges ─────────────────────────────────────
    goals_min:          Optional[float] = Query(default=None, ge=0),
    goals_max:          Optional[float] = Query(default=None, ge=0),
    assists_min:        Optional[float] = Query(default=None, ge=0),
    assists_max:        Optional[float] = Query(default=None, ge=0),
    matches_min:        Optional[float] = Query(default=None, ge=0),
    matches_max:        Optional[float] = Query(default=None, ge=0),
    rating_min:         Optional[float] = Query(default=None, ge=0, le=10),
    rating_max:         Optional[float] = Query(default=None, ge=0, le=10),
    pass_accuracy_min:  Optional[float] = Query(default=None, ge=0, le=100),
    pass_accuracy_max:  Optional[float] = Query(default=None, ge=0, le=100),
    tackles_min:        Optional[float] = Query(default=None, ge=0),
    tackles_max:        Optional[float] = Query(default=None, ge=0),
    interceptions_min:  Optional[float] = Query(default=None, ge=0),
    interceptions_max:  Optional[float] = Query(default=None, ge=0),
    clean_sheets_min:   Optional[float] = Query(default=None, ge=0),
    clean_sheets_max:   Optional[float] = Query(default=None, ge=0),

    # ── Pagination & sort ────────────────────────────────
    sort_by:    str = Query(default="name",  description="Sort field: name, nationality, position, category, goals, rating"),
    sort_order: str = Query(default="asc",   description="asc | desc"),
    page:       int = Query(default=1,  ge=1),
    page_size:  int = Query(default=20, ge=1, le=100),
):
    """
    Advanced player search endpoint for the Agent Discovery system.

    Filters may be combined freely.  All location data (countries,
    regions, sub-regions) is resolved from the ISO codes supplied by
    the frontend, which loads those lists from the existing
    /api/public/countries/* endpoints — zero hardcoded location values.

    When stats filters are supplied the endpoint first aggregates
    player_stats_collection to identify qualifying player IDs, then
    intersects with the profile query — keeping the logic clean and
    each collection's query focused.
    """
    agent     = await _resolve_agent(request)
    agent_id  = (
        agent.get("agent_id")
        or agent.get("id")
        or str(agent.get("_id", ""))
    )

    # ── 1. Resolve all position codes (explicit + from categories) ──
    all_positions: List[str] = [p.strip().upper() for p in positions if p.strip()]
    for cat in position_categories:
        all_positions.extend(POSITION_CATEGORIES.get(cat, []))
    all_positions = list(dict.fromkeys(all_positions))  # deduplicate

    # ── 2. Resolve all country codes from explicit + geo selections ─
    all_country_codes = _resolve_all_country_codes(countries, continents, africa_regions)

    # ── 3. Build profile query ──────────────────────────────────────
    profile_query = _build_player_query(
        q=q,
        country_codes=all_country_codes,
        states=states,
        lgas=lgas,
        cities=cities,
        levels=levels,
        positions=all_positions,
        age_min=age_min,
        age_max=age_max,
        height_min=height_min,
        height_max=height_max,
        weight_min=weight_min,
        weight_max=weight_max,
        preferred_foot=preferred_foot,
    )

    # ── 4. Stats filtering (two-phase if stats filters are active) ──
    has_stats = _has_stats_filters(
        goals_min, goals_max, assists_min, assists_max,
        matches_min, matches_max, rating_min, rating_max,
        pass_accuracy_min, pass_accuracy_max, tackles_min, tackles_max,
        interceptions_min, interceptions_max, clean_sheets_min, clean_sheets_max,
    )

    if has_stats:
        # Phase A: get candidate player IDs from profile query (up to 5 000)
        projection = {"player_id": 1, "user_id": 1, "_id": 1}
        candidate_cursor = players_collection.find(profile_query, projection)
        candidates = await candidate_cursor.to_list(length=5_000)
        candidate_ids = [
            c.get("player_id") or c.get("user_id") or str(c.get("_id", ""))
            for c in candidates
        ]

        if not candidate_ids:
            return JSONResponse({
                "players": [], "total": 0,
                "page": page, "pageSize": page_size, "hasMore": False,
            })

        # Phase B: aggregate stats and intersect
        qualifying_ids = await _get_stats_filtered_ids(
            candidate_ids=candidate_ids,
            goals_min=goals_min,           goals_max=goals_max,
            assists_min=assists_min,       assists_max=assists_max,
            matches_min=matches_min,       matches_max=matches_max,
            rating_min=rating_min,         rating_max=rating_max,
            pass_accuracy_min=pass_accuracy_min, pass_accuracy_max=pass_accuracy_max,
            tackles_min=tackles_min,       tackles_max=tackles_max,
            interceptions_min=interceptions_min, interceptions_max=interceptions_max,
            clean_sheets_min=clean_sheets_min,   clean_sheets_max=clean_sheets_max,
        )

        if not qualifying_ids:
            return JSONResponse({
                "players": [], "total": 0,
                "page": page, "pageSize": page_size, "hasMore": False,
            })

        # Narrow profile query to qualifying stats IDs
        stats_id_clause = {"$or": [
            {"player_id": {"$in": qualifying_ids}},
            {"user_id":   {"$in": qualifying_ids}},
        ]}
        if profile_query:
            if "$and" in profile_query:
                profile_query["$and"].append(stats_id_clause)
            else:
                profile_query = {"$and": [profile_query, stats_id_clause]}
        else:
            profile_query = stats_id_clause

    # ── 5. Sort field mapping ────────────────────────────────────────
    _SORT_MAP: Dict[str, str] = {
        "name":        "first_name",
        "nationality": "nationality",
        "position":    "position",
        "category":    "playing_category",
        # For stats-based sort we fall back to profile field "name"
        # (true stats sort would require a different aggregation approach)
        "goals":       "first_name",
        "rating":      "first_name",
    }
    sort_field = _SORT_MAP.get(sort_by, "first_name")
    sort_dir   = 1 if sort_order.lower() == "asc" else -1

    # ── 6. Count + paginate ─────────────────────────────────────────
    total  = await players_collection.count_documents(profile_query)
    skip   = (page - 1) * page_size
    cursor = (
        players_collection
        .find(profile_query)
        .skip(skip)
        .limit(page_size)
        .sort(sort_field, sort_dir)
    )
    players_raw = await cursor.to_list(length=page_size)

    # ── 7. Enrich: stats summaries ──────────────────────────────────
    pid_keys = [
        p.get("player_id") or p.get("user_id") or str(p.get("_id", ""))
        for p in players_raw
    ]
    stats_by_id = await _fetch_stats_summaries(pid_keys)

    # ── 8. Enrich: pending proposals from this agent ────────────────
    pending_map: Dict[str, str] = {}
    if proposals_collection is not None and pid_keys:
        pending_cursor = proposals_collection.find(
            {
                "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
                "status": "pending",
                "player_id": {"$in": pid_keys},
            },
            {"player_id": 1, "request_id": 1, "_id": 1},
        )
        pending_docs = await pending_cursor.to_list(length=1_000)
        for prop in pending_docs:
            pid  = prop.get("player_id", "")
            rid  = prop.get("request_id") or str(prop.get("_id", ""))
            if pid:
                pending_map[pid] = rid

    # ── 9. Serialise and return ─────────────────────────────────────
    serialized = [
        _serialize_player_full(
            p,
            stats=stats_by_id.get(
                p.get("player_id") or p.get("user_id") or str(p.get("_id", ""))
            ),
            pending_proposal_id=pending_map.get(
                p.get("player_id") or p.get("user_id") or str(p.get("_id", ""))
            ),
        )
        for p in players_raw
    ]

    return JSONResponse({
        "players":  serialized,
        "total":    total,
        "page":     page,
        "pageSize": page_size,
        "hasMore":  (skip + page_size) < total,
    })

# ============================================================
# END: API ROUTES
# ============================================================
