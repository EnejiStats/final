"""
ENEJISTATS — Club Dashboard Routes
====================================
Complete API router for every endpoint consumed by the club dashboard
frontend (club-dashboard.html / FILE C).

INTEGRATION — wire in main.py immediately after other sub-routers:

    import club_dashboard_routes as _cdr
    _cdr._setup_dependencies(globals())
    app.include_router(_cdr.router)
    logger.info("club_dashboard_routes mounted — %d routes", len(_cdr.router.routes))

WHY THIS PATTERN
────────────────
A plain `from main import (...)` causes a circular import loop.
This file NEVER imports from main at module-level.  All shared state
is injected by ``_setup_dependencies()`` which is called by main.py
AFTER main.py has fully executed and every symbol is bound.

ENDPOINTS COVERED (38 unique paths):
  GET    /api/club/{uid}/profile
  GET    /api/club/{uid}/stats/summary
  GET    /api/club/{uid}/matches
  GET    /api/club/{uid}/upcoming-fixtures
  GET    /api/club/{uid}/tokens
  GET    /api/club/{uid}/notifications
  PATCH  /api/club/{uid}/notifications/read-all
  PATCH  /api/club/{uid}/notifications/{notif_id}/read
  DELETE /api/club/{uid}/notifications/{notif_id}
  GET    /api/club/{uid}/achievements
  GET    /api/club/{uid}/transactions
  GET    /api/club/{uid}/stats-requests
  GET    /api/club/{uid}/match-requests/sent
  GET    /api/club/{uid}/match-requests/received
  GET    /api/club/{uid}/squad
  POST   /api/club/{uid}/logo
  PUT    /api/club/{uid}/management
  POST   /api/club/{uid}/change-password
  POST   /api/club/{uid}/tokens/topup
  POST   /api/club/{uid}/tokens/verify
  POST   /api/club/{uid}/media/youtube
  DELETE /api/club/{uid}/media/youtube/{yt_id}
  POST   /api/club/{uid}/stats-request
  POST   /api/club/{uid}/match-requests
  PATCH  /api/club/{uid}/match-requests/{req_id}/accept
  PATCH  /api/club/{uid}/match-requests/{req_id}/decline
  POST   /api/club/{uid}/competitions/{comp_id}/apply
  GET    /api/clubs/search
  GET    /api/competitions
  GET    /api/token/costs
  GET    /api/token/pricing
  GET    /api/subscription/pricing
  GET    /api/payment/config
  POST   /api/payment/bank-transfer/intent
  POST   /api/payment/bank-transfer/receipt
  GET    /api/bank-details/active
  GET    /api/stadiums/search
  POST   /api/support/tickets
  POST   /api/support/chat/{ticket_id}
"""

# ============================================================
# STANDARD-LIBRARY & THIRD-PARTY IMPORTS ONLY
# (No import from main — circular import avoided)
# ============================================================
import io
import secrets
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from location_module import build_club_location_filter, build_stadium_location_clauses

# ============================================================
# MODULE-LEVEL PLACEHOLDERS
# All set to None here; populated by _setup_dependencies().
# ============================================================

# ── Database handle ──────────────────────────────────────────
database = None

# ── Collections ──────────────────────────────────────────────
clubs_collection                = None
club_tokens_collection          = None
transactions_collection         = None
token_transactions_collection   = None
notifications_collection        = None
match_data_collection           = None
match_fixtures_collection       = None
stats_requests_collection       = None
match_requests_collection       = None
club_squads_collection          = None
# FIX: players_collection added so get_club_squad can find
# players who registered with a club_id but were never inserted
# into club_squads_collection (the root cause of the empty Squad tab).
players_collection              = None
competitions_collection         = None
support_tickets_collection      = None
support_messages_collection     = None
payment_intents_collection      = None
activity_history_collection     = None

# ── Helpers from main ────────────────────────────────────────
MongoSerializer       = None
MongoJSONResponse     = None
logger                = None
upload_to_cloudinary  = None
send_email            = None
hash_password         = None
verify_password       = None
verify_token          = None
normalize_level       = None
get_token_cost        = None
pricing_service       = None
get_current_user      = None
normalize_role         = None
_make_tx_ref          = None
_make_stats_request_ref       = None
_make_club_token_topup_ref    = None

# ── Config / env ─────────────────────────────────────────────
FLUTTERWAVE_SECRET_KEY  = None
FLUTTERWAVE_PUBLIC_KEY  = None
FLUTTERWAVE_BASE_URL    = "https://api.flutterwave.com/v3"

_DEPS_READY = False

# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Populate every module-level placeholder from main.py's namespace.
    """

    global _DEPS_READY

    global database
    global clubs_collection, club_tokens_collection
    global transactions_collection, token_transactions_collection
    global notifications_collection
    global match_data_collection, match_fixtures_collection
    global stats_requests_collection, match_requests_collection
    global club_squads_collection, players_collection, competitions_collection
    global support_tickets_collection, support_messages_collection
    global payment_intents_collection, activity_history_collection

    global MongoSerializer, MongoJSONResponse, logger
    global upload_to_cloudinary, send_email
    global hash_password, verify_password, verify_token
    global normalize_level, get_token_cost, pricing_service
    global get_current_user, normalize_role
    global _make_tx_ref, _make_stats_request_ref, _make_club_token_topup_ref

    global FLUTTERWAVE_SECRET_KEY, FLUTTERWAVE_PUBLIC_KEY

    if _DEPS_READY:
        return

    _m = main_globals

    # ── Database handle ──────────────────────────────────────
    database = _m.get("database")
    if database is None:
        raise RuntimeError(
            "Database dependency was not injected into club_dashboard_routes."
        )

    # ── Required collections (safe .get() + database fallback) ───────────────
    # NOTE: MongoDB Collection objects do not support bool()/truth-value testing.
    # Each assignment uses an explicit `is None` guard instead of `or`.
    clubs_collection = _m.get("clubs_collection")
    if clubs_collection is None:
        clubs_collection = database["clubs"]
    club_tokens_collection = _m.get("club_tokens_collection")
    if club_tokens_collection is None:
        club_tokens_collection = database["club_tokens"]
    notifications_collection = _m.get("notifications_collection")
    if notifications_collection is None:
        notifications_collection = database["notifications"]
    stats_requests_collection = _m.get("stats_requests_collection")
    if stats_requests_collection is None:
        stats_requests_collection = database["stats_requests"]
    club_squads_collection = _m.get("club_squads_collection")
    if club_squads_collection is None:
        club_squads_collection = database["club_squads"]
    # FIX: inject players_collection so squad endpoint can find affiliated players
    players_collection = _m.get("players_collection")
    if players_collection is None:
        players_collection = database["players"]
    payment_intents_collection = _m.get("payment_intents_collection")
    if payment_intents_collection is None:
        payment_intents_collection = database["payment_intents"]
    activity_history_collection = _m.get("activity_history_collection")
    if activity_history_collection is None:
        activity_history_collection = database["activity_history"]

    # ── Optional collections with safe fallbacks ─────────────
    transactions_collection = _m.get("transactions_collection")
    if transactions_collection is None:
        transactions_collection = database["transactions"]

    token_transactions_collection = _m.get("token_transactions_collection")
    if token_transactions_collection is None:
        token_transactions_collection = database["token_transactions"]

    match_data_collection = _m.get("match_data_collection")
    if match_data_collection is None:
        match_data_collection = database["match_data"]

    match_fixtures_collection = _m.get("match_fixtures_collection")
    if match_fixtures_collection is None:
        match_fixtures_collection = database["match_fixtures"]

    match_requests_collection = _m.get("match_requests_collection")
    if match_requests_collection is None:
        match_requests_collection = database["match_requests"]

    competitions_collection = _m.get("competitions_collection")
    if competitions_collection is None:
        competitions_collection = database["competitions"]

    support_tickets_collection = _m.get("support_tickets_collection")
    if support_tickets_collection is None:
        support_tickets_collection = database["support_tickets"]

    support_messages_collection = _m.get("support_messages_collection")
    if support_messages_collection is None:
        support_messages_collection = database["support_messages"]

    # ── Shared helpers ───────────────────────────────────────
    MongoSerializer = _m["MongoSerializer"]
    MongoJSONResponse = _m["MongoJSONResponse"]
    logger = _m["logger"]

    upload_to_cloudinary = _m["upload_to_cloudinary"]
    send_email = _m.get("send_email")

    hash_password = _m["hash_password"]
    verify_password = _m["verify_password"]
    verify_token = _m["verify_token"]

    normalize_level = _m["normalize_level"]
    get_token_cost = _m.get("get_token_cost")
    pricing_service = _m.get("pricing_service")

    get_current_user = _m["get_current_user"]
    normalize_role = _m["normalize_role"]

    _make_tx_ref = _m.get("_make_tx_ref")
    _make_stats_request_ref = _m.get("_make_stats_request_ref")
    _make_club_token_topup_ref = _m.get("_make_club_token_topup_ref")

    # ── Payment configuration ────────────────────────────────
    FLUTTERWAVE_SECRET_KEY = _m.get("FLUTTERWAVE_SECRET_KEY", "")
    FLUTTERWAVE_PUBLIC_KEY = _m.get("FLUTTERWAVE_PUBLIC_KEY", "")

    _DEPS_READY = True

    logger.debug(
        "[club_dashboard_routes] _setup_dependencies COMPLETE | "
        "clubs_collection=%s | club_tokens_collection=%s | players_collection=%s",
        clubs_collection.name if clubs_collection is not None else "MISSING",
        club_tokens_collection.name if club_tokens_collection is not None else "MISSING",
        players_collection.name if players_collection is not None else "MISSING",
    )
    
# ============================================================
# ROUTER
# ============================================================

router = APIRouter(prefix="/api", tags=["club-dashboard"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ManagementUpdateBody(BaseModel):
    management: List[Dict[str, Any]] = Field(default_factory=list)


class PasswordChangeBody(BaseModel):
    old_password: str
    new_password: str


class TokenTopupBody(BaseModel):
    amount: float
    tokens: int
    description: Optional[str] = "Token top-up"
    entity: Optional[str] = "club"
    entity_id: Optional[str] = None


class TokenVerifyBody(BaseModel):
    transaction_id: str
    tx_ref: str


class YouTubeAddBody(BaseModel):
    url: str
    title: Optional[str] = "Club Video"


class StatsRequestBody(BaseModel):
    match_date: str
    match_time: str
    match_type: Optional[str] = None
    home_team: str
    away_team: str
    club_role: Optional[str] = None
    venue_address: str
    venue_country: Optional[str] = "Nigeria"
    venue_country_code: Optional[str] = None
    venue_state: str
    venue_lga: str
    venue_city: Optional[str] = None
    venue_detailed_address: Optional[str] = None
    jersey_color: Optional[str] = ""
    tracking_type: str = "club_and_players"
    # IDs selected in the club dashboard for club-plus-player tracking.
    # Keep these on the persisted request; older Pydantic models silently
    # discarded the frontend's player_ids field.
    player_ids: List[str] = Field(default_factory=list)
    contact_phone: str
    notes: Optional[str] = None
    player_stat_categories: Optional[List[str]] = Field(default_factory=list)


class MatchRequestBody(BaseModel):
    requested_club_id: str
    requested_club_name: Optional[str] = ""
    match_date: Optional[str] = None
    match_time: Optional[str] = None
    team_position: Optional[str] = None
    venue_country: Optional[str] = None
    venue_country_code: Optional[str] = None
    venue_state: Optional[str] = None
    venue_lga: Optional[str] = None
    venue_city: Optional[str] = None
    venue_detailed_address: Optional[str] = None
    venue_address: Optional[str] = None
    jersey_color: Optional[str] = None
    tracking_type: Optional[str] = "no_tracking"
    contact_phone: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        # The frontend spreads ...mrForm which includes _stadiumSuggs (array of
        # stadium suggestion objects).  Without extra="ignore" Pydantic v1 raises
        # a validation error on unknown fields; v2 ignores them by default but this
        # makes the intent explicit and safe for both versions.
        extra = "ignore"


class CompetitionApplyBody(BaseModel):
    competition_id: Optional[str] = None
    club_id: Optional[str] = None
    club_name: Optional[str] = None


class SupportTicketBody(BaseModel):
    club_id: Optional[str] = None
    reason: str


class SupportChatBody(BaseModel):
    text: str


class BankTransferIntentBody(BaseModel):
    paymentType: str           # "TOKEN_PURCHASE" | "SUBSCRIPTION"
    selectedPlan: str
    role: Optional[str] = "club"
    level: Optional[str] = None
    tokens: Optional[int] = None


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _club_filter(uid: str) -> dict:
    """Return a MongoDB filter that matches a club by club_id or user_id."""
    return {"$or": [{"club_id": uid}, {"user_id": uid}]}


async def _resolve_club(uid: str) -> Optional[dict]:
    """Fetch a club document by club_id or user_id (or ObjectId)."""
    club = await clubs_collection.find_one(_club_filter(uid))
    if not club and len(uid) == 24:
        try:
            club = await clubs_collection.find_one({"_id": ObjectId(uid)})
        except Exception:
            pass
    return club


def _require_auth(current_user: dict, uid: str) -> None:
    """
    Raise 403 if the authenticated user is not the requested club,
    a supervisor, or an admin.
    """
    try:
        role = normalize_role(current_user.get("role") or current_user.get("user_type") or "")
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Access denied")
    if role in {"admin", "supervisor"}:
        return
    if role != "club":
        raise HTTPException(status_code=403, detail="Club access required")
    for field in ("club_id", "user_id", "unique_id", "_id"):
        val = current_user.get(field)
        if val and str(val) == str(uid):
            return
    raise HTTPException(status_code=403, detail="Access denied")


# ============================================================
# 1. CLUB PROFILE
# ============================================================

@router.get("/club/{uid}/profile")
async def get_club_profile(uid: str, request: Request):
    """Full club profile — used by the Overview and Settings tabs."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        doc = MongoSerializer.serialize_document(club)
        # Strip sensitive fields
        doc.pop("password", None)
        return MongoJSONResponse(doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_profile error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 2. STATS / SUMMARY
# ============================================================

@router.get("/club/{uid}/stats/summary")
async def get_club_stats_summary(uid: str, request: Request):
    """Season summary stats derived from match_data_collection."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        club_name = club.get("club_name", "")
        name_filter = {
            "$or": [
                {"home_team": {"$regex": club_name, "$options": "i"}},
                {"away_team": {"$regex": club_name, "$options": "i"}},
                {"club_id": uid},
                {"user_id": uid},
            ]
        } if club_name else {"club_id": uid}

        matches = await match_data_collection.find(name_filter).to_list(length=500)

        wins = draws = losses = goals_for = goals_against = clean_sheets = 0
        for m in matches:
            result = (m.get("result") or "").upper()
            if result == "W":
                wins += 1
            elif result == "D":
                draws += 1
            elif result == "L":
                losses += 1
            goals_for     += m.get("goals_for", 0) or 0
            goals_against += m.get("goals_against", 0) or 0
            if m.get("clean_sheet") or m.get("goals_conceded", -1) == 0:
                clean_sheets += 1

        # The frontend destructures as:
        #   setSeasonStats(data.season_stats || data.stats || {})
        #   setSummaryStats(data.summary_stats || data.summary || {})
        # Both states draw from the same computed numbers here.
        stats_payload = {
            "matches_played": len(matches),
            "matchesPlayed":  len(matches),
            "wins":           wins,
            "draws":          draws,
            "losses":         losses,
            "goals_for":      goals_for,
            "goalsFor":       goals_for,
            "goals_against":  goals_against,
            "goalsAgainst":   goals_against,
            "clean_sheets":   clean_sheets,
            "cleanSheets":    clean_sheets,
        }
        return MongoJSONResponse({
            # summary_stats → setSummaryStats (overview cards / match centre cards)
            "summary_stats": stats_payload,
            "summary":       stats_payload,
            # season_stats → setSeasonStats (ClubMatrixCard)
            "season_stats":  stats_payload,
            "stats":         stats_payload,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_stats_summary error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 3. MATCH HISTORY
# ============================================================

@router.get("/club/{uid}/matches")
async def get_club_matches(
    uid: str,
    request: Request,
    limit: int = 50,
    page: int = 1,
):
    """Past match results for the Match Centre tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        club_name = club.get("club_name", "")
        query: Dict[str, Any] = {
            "$or": [
                {"club_id": uid},
                {"user_id": uid},
            ]
        }
        if club_name:
            query["$or"].extend([
                {"home_team": {"$regex": club_name, "$options": "i"}},
                {"away_team": {"$regex": club_name, "$options": "i"}},
            ])

        skip = (max(1, page) - 1) * limit
        cursor = (
            match_data_collection.find(query)
            .sort("match_date", -1)
            .skip(skip)
            .limit(limit)
        )
        matches = await cursor.to_list(length=limit)
        return MongoJSONResponse(MongoSerializer.serialize_documents(matches))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_matches error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 4. UPCOMING FIXTURES
# ============================================================

@router.get("/club/{uid}/upcoming-fixtures")
async def get_club_upcoming_fixtures(uid: str, request: Request):
    """Upcoming fixtures for the Match Centre tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        club_name = club.get("club_name", "")
        now = MongoSerializer.now_utc()
        today_str = now.strftime("%Y-%m-%d")  # ISO date prefix for string comparisons

        # Owner filter
        owner_or: List[Dict[str, Any]] = [{"club_id": uid}, {"user_id": uid}]
        if club_name:
            owner_or.extend([
                {"home_team": {"$regex": club_name, "$options": "i"}},
                {"away_team": {"$regex": club_name, "$options": "i"}},
            ])

        # Only genuinely upcoming fixtures: match_date must be >= today.
        # The collection may store dates as datetime objects or ISO strings;
        # both comparisons are applied so either storage format works.
        query: Dict[str, Any] = {
            "$and": [
                {"$or": owner_or},
                {
                    "$or": [
                        # datetime stored in DB
                        {"match_date": {"$gte": now}},
                        # ISO-string stored in DB (lexicographic compare works for YYYY-MM-DD)
                        {"match_date": {"$gte": today_str}},
                    ]
                },
            ]
        }

        fixtures = await (
            match_fixtures_collection.find(query)
            .sort("match_date", 1)
            .limit(20)
            .to_list(length=20)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(fixtures))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_upcoming_fixtures error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 5. TOKEN BALANCE
# ============================================================

@router.get("/club/{uid}/tokens")
async def get_club_tokens(uid: str, request: Request):
    """Token balance + locked amount for the sidebar and Tokens tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        rec = await club_tokens_collection.find_one(
            {"$or": [{"club_id": uid}, {"user_id": uid}]}
        )
        if not rec:
            return MongoJSONResponse({"balance": 0, "locked": 0, "expiry_date": None})

        return MongoJSONResponse({
            "balance":     rec.get("balance", 0),
            "locked":      rec.get("locked", 0),
            "expiry_date": MongoSerializer.serialize_value(rec.get("expiry_date")),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_tokens error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 6. NOTIFICATIONS (list + polling)
# ============================================================

@router.get("/club/{uid}/notifications")
async def get_club_notifications(
    uid: str,
    request: Request,
    limit: int = 50,
):
    """Notification list — also used by the 60-second polling loop."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        club_oid = club["_id"] if club else None

        query: Dict[str, Any] = {
            "$or": [
                {"unique_id": uid},
                {"user_id": uid},
                {"club_id": uid},           # notifications keyed by club_id business key
            ]
        }
        if club_oid:
            query["$or"].append({"user_id": ObjectId(club_oid)})

        notifs = await (
            notifications_collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
            .to_list(length=limit)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(notifs))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_notifications error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ── NOTE: /read-all must be registered BEFORE /{notif_id}/read
#   to avoid FastAPI matching "read-all" as a notif_id value.
#   The path depths differ (3 vs 4 segments) so FastAPI handles
#   it correctly regardless, but the ordering is explicit here.

@router.patch("/club/{uid}/notifications/read-all")
async def mark_all_notifications_read(uid: str, request: Request):
    """Mark every notification for this club as read."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        result = await notifications_collection.update_many(
            {"$or": [{"unique_id": uid}, {"user_id": uid}, {"club_id": uid}]},
            {"$set": {"read": True, "read_at": MongoSerializer.now_utc()}},
        )
        return MongoJSONResponse({"modified": result.modified_count})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"mark_all_notifications_read error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/club/{uid}/notifications/{notif_id}/read")
async def mark_notification_read(uid: str, notif_id: str, request: Request):
    """Mark a single notification as read (scoped to the owning club)."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        # Always scope by owner so one club cannot touch another club's notifications
        owner_filter: Dict[str, Any] = {
            "$or": [{"unique_id": uid}, {"user_id": uid}, {"club_id": uid}]
        }
        _id_clause: Dict[str, Any] = {}
        try:
            _id_clause["_id"] = ObjectId(notif_id)
        except Exception:
            _id_clause["_id"] = notif_id

        query = {"$and": [_id_clause, owner_filter]}

        await notifications_collection.update_one(
            query,
            {"$set": {"read": True, "read_at": MongoSerializer.now_utc()}},
        )
        return MongoJSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"mark_notification_read error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/club/{uid}/notifications/{notif_id}")
async def delete_notification(uid: str, notif_id: str, request: Request):
    """Permanently delete a notification (scoped to the owning club)."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        owner_filter: Dict[str, Any] = {
            "$or": [{"unique_id": uid}, {"user_id": uid}, {"club_id": uid}]
        }
        _id_clause: Dict[str, Any] = {}
        try:
            _id_clause["_id"] = ObjectId(notif_id)
        except Exception:
            _id_clause["_id"] = notif_id

        query = {"$and": [_id_clause, owner_filter]}

        await notifications_collection.delete_one(query)
        return MongoJSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_notification error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 7. ACHIEVEMENTS
# ============================================================

@router.get("/club/{uid}/achievements")
async def get_club_achievements(uid: str, request: Request):
    """Club achievements list (stored on the club document)."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        achievements = club.get("achievements") or []
        # Frontend: setAchievements(Array.isArray(v(achieveData)) ? v(achieveData) : [])
        # Must be a direct array — object wrapper causes silent empty-state.
        return MongoJSONResponse(MongoSerializer.serialize_value(achievements))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_achievements error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 8. TRANSACTIONS
# ============================================================

@router.get("/club/{uid}/transactions")
async def get_club_transactions(
    uid: str,
    request: Request,
    limit: int = 50,
    page: int = 1,
):
    """Transaction history for the Tokens tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        club_oid = club["_id"] if club else None

        query: Dict[str, Any] = {
            "$or": [
                {"unique_id": uid},
                {"user_id": uid},
                {"club_id": uid},
            ]
        }
        if club_oid:
            query["$or"].append({"user_id": ObjectId(club_oid)})

        skip = (max(1, page) - 1) * limit
        txns = await (
            transactions_collection.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(txns))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_transactions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 9. COMPETITIONS (public list)
# ============================================================

@router.get("/competitions")
async def list_competitions(request: Request):
    """All available competitions — used by the Operations tab."""
    try:
        comps = await competitions_collection.find(
            {"is_active": {"$ne": False}}
        ).sort("created_at", -1).limit(100).to_list(length=100)
        return MongoJSONResponse({"competitions": MongoSerializer.serialize_documents(comps)})
    except Exception as e:
        logger.error(f"list_competitions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 10. TOKEN COST TABLE + PACKAGES
# ============================================================

@router.get("/token/costs")
async def get_token_costs(request: Request):
    """
    Token cost table and available packages — used by the
    Stats Tracking submit form to show the token cost display.
    """
    try:
        current_user = await get_current_user(request)
        role  = current_user.get("role", "club")
        level = current_user.get("category") or current_user.get("club_category") or "professional"

        try:
            packages = pricing_service.get_token_packages(role, level)
        except Exception:
            packages = []

        # Stats-request costs per tracking type (flat pricing)
        try:
            club_and_players_cost = pricing_service.get_stats_request_cost("club", level)
        except Exception:
            club_and_players_cost = 10

        try:
            club_only_cost = max(1, int(club_and_players_cost * 0.6))
        except Exception:
            club_only_cost = 6

        # Key names MUST match what the frontend reads (line 1632-1633 of club-dashboard.html):
        #   tokenCosts.club_stats_tracking || tokenCosts.club_tracking        (club_only)
        #   tokenCosts.club_and_player_tracking || tokenCosts.full_tracking   (club_and_players)
        return MongoJSONResponse({
            "packages": packages,
            "costs": {
                "club_and_player_tracking": club_and_players_cost,   # primary key (frontend line 1633)
                "full_tracking":            club_and_players_cost,   # fallback key  (frontend line 1633)
                "club_stats_tracking":      club_only_cost,          # primary key (frontend line 1632)
                "club_tracking":            club_only_cost,          # fallback key  (frontend line 1632)
                "no_tracking":              0,
                # Legacy/extra aliases kept for compatibility
                "club_and_players":         club_and_players_cost,
                "club_only":               club_only_cost,
            },
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_token_costs error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 11. TOKEN PRICING  (Payment Wizard — TOKEN_PURCHASE)
# ============================================================



# ============================================================
# 12. SUBSCRIPTION PRICING  (Payment Wizard — SUBSCRIPTION)
# ============================================================



# ============================================================
# 13. PAYMENT CONFIG  (bank transfer details — legacy endpoint)
# ============================================================



# ============================================================
# 14. STATS-REQUEST HISTORY
# ============================================================

@router.get("/club/{uid}/stats-requests")
async def get_club_stats_requests(
    uid: str,
    request: Request,
    limit: int = 50,
    page: int = 1,
):
    """Stats tracking request history for the Operations tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        skip = (max(1, page) - 1) * limit
        docs = await (
            stats_requests_collection.find(
                {"$or": [{"club_id": uid}, {"user_id": uid}]}
            )
            .sort("submitted_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(docs))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_stats_requests error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 15. MATCH REQUESTS — SENT
# ============================================================

@router.get("/club/{uid}/match-requests/sent")
async def get_sent_match_requests(uid: str, request: Request):
    """Sent match requests for the Operations tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        docs = await (
            match_requests_collection.find(
                {"$or": [{"requesting_club_id": uid}, {"club_id": uid}, {"user_id": uid}]}
            )
            .sort("created_at", -1)
            .limit(100)
            .to_list(length=100)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(docs))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_sent_match_requests error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 16. MATCH REQUESTS — RECEIVED
# ============================================================

@router.get("/club/{uid}/match-requests/received")
async def get_received_match_requests(uid: str, request: Request):
    """Received match requests for the Operations tab."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        docs = await (
            match_requests_collection.find({"requested_club_id": uid})
            .sort("created_at", -1)
            .limit(100)
            .to_list(length=100)
        )
        return MongoJSONResponse(MongoSerializer.serialize_documents(docs))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_received_match_requests error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 17. SQUAD
# ============================================================

@router.get("/club/{uid}/squad")
async def get_club_squad(uid: str, request: Request):
    """
    Squad player list for the Squad tab.

    FIX: Two sources of squad membership are now merged:

    1. club_squads_collection — players explicitly added to the club's
       squad document by an admin or via a squad-management flow.

    2. players_collection — players who registered via /api/auth/register
       with a club_id (or current_club_id) matching this club. auth.py
       stores club_id on the player document but does NOT insert a record
       into club_squads_collection, so these players were previously invisible
       on the Squad tab.

    Results from both sources are merged and deduplicated by player_id.
    """
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        # ── Source 1: explicit squad document ────────────────
        squad_doc = await club_squads_collection.find_one(
            {"$or": [{"club_id": uid}, {"user_id": uid}]}
        )
        explicit_players: List[dict] = []
        if squad_doc:
            explicit_players = squad_doc.get("players") or squad_doc.get("squad") or []

        # Build a set of already-known player_ids to use for deduplication
        seen_player_ids: set = set()
        for p in explicit_players:
            pid = p.get("player_id") or p.get("_id") or p.get("id")
            if pid:
                seen_player_ids.add(str(pid))

        # ── Source 2: players_collection (registered with club_id) ──
        # Players who self-registered with this club's ID end up here
        # but are never inserted into club_squads_collection.
        affiliated_players: List[dict] = []
        if players_collection is not None:
            raw_affiliated = await players_collection.find(
                {
                    "$or": [
                        {"club_id": uid},
                        {"current_club_id": uid},
                    ]
                }
            ).to_list(length=500)

            for p in raw_affiliated:
                pid = p.get("player_id") or str(p.get("_id", ""))
                if pid and pid not in seen_player_ids:
                    seen_player_ids.add(pid)
                    # Normalise to the same shape the frontend expects
                    affiliated_players.append({
                        "player_id":    pid,
                        "full_name":    p.get("full_name") or p.get("name") or "",
                        "name":         p.get("full_name") or p.get("name") or "",
                        "position":     p.get("position") or p.get("preferred_position") or "",
                        "jersey_number": p.get("jersey_number") or p.get("shirt_number") or "",
                        "photo_url":    p.get("photo_url") or p.get("profile_image") or "",
                        "nationality":  p.get("nationality") or "",
                        "date_of_birth": p.get("date_of_birth") or p.get("dob") or "",
                        "email":        p.get("email") or "",
                        "phone":        p.get("phone") or p.get("contact_phone") or "",
                        "status":       p.get("status") or "active",
                        "source":       "registered",   # indicates self-registered player
                    })

        # ── Merge: explicit squad entries first, then affiliated ──
        merged = list(explicit_players) + affiliated_players

        serialized = MongoSerializer.serialize_value(merged)
        # Frontend: setSquadPlayers(Array.isArray(v(squadData)) ? v(squadData) : v(squadData).squad || [])
        # Checks .squad key explicitly — must be present.
        return MongoJSONResponse({
            "squad":   serialized,   # key the frontend checks
            "players": serialized,   # alias for any other consumer
            "total":   len(merged),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_club_squad error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 18. UPLOAD CLUB LOGO
# ============================================================

@router.post("/club/{uid}/logo")
async def upload_club_logo(
    uid: str,
    request: Request,
    photo: UploadFile = File(...),
):
    """
    Upload (or replace) a club badge.
    Stores the Cloudinary URL on clubs_collection.photo_url.
    """
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        content_type = photo.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        file_bytes = await photo.read()
        club_name  = club.get("club_name", uid).replace(" ", "_")[:30]
        public_id  = f"club_{uid}_{club_name}_badge"

        photo_url = await upload_to_cloudinary(
            file_bytes,
            filename=photo.filename or "badge.png",
            folder="enejistats",
            resource_type="image",
            public_id=public_id,
            user_type="club",
            file_category="logos",
        )

        await clubs_collection.update_one(
            _club_filter(uid),
            {"$set": {"photo_url": photo_url, "updated_at": MongoSerializer.now_utc()}},
        )
        return MongoJSONResponse({"photo_url": photo_url, "ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"upload_club_logo error: {e}")
        raise HTTPException(status_code=500, detail="Logo upload failed")


# ============================================================
# 19. UPDATE MANAGEMENT TEAM
# ============================================================

@router.put("/club/{uid}/management")
async def update_management_team(uid: str, request: Request, body: ManagementUpdateBody):
    """Replace the management team array on the club document."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        await clubs_collection.update_one(
            _club_filter(uid),
            {
                "$set": {
                    "management": body.management,
                    "updated_at": MongoSerializer.now_utc(),
                }
            },
        )
        return MongoJSONResponse({"ok": True, "count": len(body.management)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_management_team error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 20. CHANGE PASSWORD
# ============================================================

@router.post("/club/{uid}/change-password")
async def change_club_password(uid: str, request: Request, body: PasswordChangeBody):
    """Change the club's account password after verifying the current one."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        stored_hash = club.get("password", "")
        if not verify_password(body.old_password, stored_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        if len(body.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

        new_hash = hash_password(body.new_password)
        await clubs_collection.update_one(
            _club_filter(uid),
            {"$set": {"password": new_hash, "updated_at": MongoSerializer.now_utc()}},
        )
        return MongoJSONResponse({"ok": True, "message": "Password updated successfully"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"change_club_password error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 21. FLUTTERWAVE TOKEN TOP-UP — INITIATE
# ============================================================

@router.post("/club/{uid}/tokens/topup")
async def initiate_club_token_topup(uid: str, request: Request, body: TokenTopupBody):
    """
    Initiate a Flutterwave payment for token top-up.
    Returns ``{ public_key, tx_ref }`` so the frontend can open
    the Flutterwave checkout modal.
    """
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        if not FLUTTERWAVE_PUBLIC_KEY:
            raise HTTPException(status_code=503, detail="Payment service not configured")

        tx_ref = (
            _make_club_token_topup_ref()
            if callable(_make_club_token_topup_ref)
            else f"CLB-TK-{uid[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        )

        # Persist a pending payment intent so we can verify later
        await payment_intents_collection.insert_one({
            "club_id":      uid,
            "user_id":      uid,
            "entity":       "club",
            "type":         "token_topup",
            "tx_ref":       tx_ref,
            "amount":       body.amount,
            "tokens":       body.tokens,
            "description":  body.description,
            "status":       "pending",
            "created_at":   MongoSerializer.now_utc(),
            "expires_at":   MongoSerializer.now_utc() + timedelta(hours=2),
        })

        return MongoJSONResponse({
            "public_key": FLUTTERWAVE_PUBLIC_KEY,
            "tx_ref":     tx_ref,
            "amount":     body.amount,
            "tokens":     body.tokens,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"initiate_club_token_topup error: {e}")
        raise HTTPException(status_code=500, detail="Payment initiation failed")


# ============================================================
# 22. FLUTTERWAVE TOKEN TOP-UP — VERIFY
# ============================================================

@router.post("/club/{uid}/tokens/verify")
async def verify_club_token_topup(uid: str, request: Request, body: TokenVerifyBody):
    """
    Verify a completed Flutterwave payment and credit tokens.
    Called by the Flutterwave checkout ``callback`` once payment is
    ``successful``.
    """
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        if not FLUTTERWAVE_SECRET_KEY:
            raise HTTPException(status_code=503, detail="Payment verification service not configured")

        # 1. Look up the pending intent FIRST (ownership + idempotency gate)
        intent = await payment_intents_collection.find_one({"tx_ref": body.tx_ref})
        if not intent:
            raise HTTPException(status_code=404, detail="Payment intent not found")

        # Ownership check: intent must belong to this club
        intent_owner = str(intent.get("club_id") or intent.get("user_id") or "")
        if intent_owner and intent_owner != str(uid):
            raise HTTPException(status_code=403, detail="Payment intent does not belong to this club")

        if intent.get("status") == "completed":
            # Idempotent — already credited
            return MongoJSONResponse({
                "ok": True,
                "tokens_credited": intent.get("tokens", 0),
                "already_processed": True,
            })

        # 2. Verify transaction with Flutterwave API
        async with httpx.AsyncClient(timeout=30) as client:
            fw_resp = await client.get(
                f"{FLUTTERWAVE_BASE_URL}/transactions/{body.transaction_id}/verify",
                headers={"Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}"},
            )

        if fw_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Flutterwave verification failed")

        fw_data = fw_resp.json()
        fw_tx   = fw_data.get("data", {})

        if fw_tx.get("status") != "successful":
            raise HTTPException(status_code=400, detail="Payment not successful")

        # tx_ref correlation: FW-returned tx_ref must match what we expect
        fw_tx_ref = fw_tx.get("tx_ref") or fw_tx.get("txRef") or ""
        if fw_tx_ref and fw_tx_ref != body.tx_ref:
            logger.warning(
                f"tx_ref mismatch: requested={body.tx_ref}, returned={fw_tx_ref} (uid={uid})"
            )
            raise HTTPException(status_code=400, detail="Payment reference mismatch")

        # Currency must be NGN
        if fw_tx.get("currency") and fw_tx["currency"] != "NGN":
            raise HTTPException(status_code=400, detail="Unexpected payment currency")

        tokens_to_credit = intent.get("tokens", 0)
        amount_paid      = float(fw_tx.get("amount", 0))

        # 3. Credit tokens to the club wallet
        token_rec = await club_tokens_collection.find_one(
            {"$or": [{"club_id": uid}, {"user_id": uid}]}
        )

        if token_rec:
            new_balance = token_rec.get("balance", 0) + tokens_to_credit
            await club_tokens_collection.update_one(
                {"_id": token_rec["_id"]},
                {
                    "$set": {
                        "balance":    new_balance,
                        "updated_at": MongoSerializer.now_utc(),
                    }
                },
            )
        else:
            new_balance = tokens_to_credit
            await club_tokens_collection.insert_one({
                "club_id":    uid,
                "user_id":    uid,
                "balance":    new_balance,
                "expiry_date": MongoSerializer.now_utc() + timedelta(days=365),
                "created_at": MongoSerializer.now_utc(),
                "updated_at": MongoSerializer.now_utc(),
            })

        # 4. Record transaction
        tx_reference = (
            _make_club_token_topup_ref()
            if callable(_make_club_token_topup_ref)
            else f"CLB-TK-{uid[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"
        )
        await transactions_collection.insert_one({
            "club_id":       uid,
            "user_id":       uid,
            "entity":        "club",
            "type":          "credit",
            "description":   f"Token top-up: {tokens_to_credit} tokens",
            "amount":        amount_paid,
            "tokens":        tokens_to_credit,
            "status":        "completed",
            "reference":     tx_reference,
            "tx_ref":        body.tx_ref,
            "transaction_id": body.transaction_id,
            "created_at":    MongoSerializer.now_utc(),
        })

        # 5. Mark intent complete
        await payment_intents_collection.update_one(
            {"_id": intent["_id"]},
            {
                "$set": {
                    "status":        "completed",
                    "completed_at":  MongoSerializer.now_utc(),
                    "tx_id":         body.transaction_id,
                    "amount_paid":   amount_paid,
                    "new_balance":   new_balance,
                }
            },
        )

        # 6. Notify
        club = await _resolve_club(uid)
        club_oid = club["_id"] if club else None
        await notifications_collection.insert_one({
            "user_id":    ObjectId(club_oid) if club_oid else uid,
            "unique_id":  uid,
            "user_type":  "club",
            "title":      "Tokens Credited",
            "message":    f"{tokens_to_credit} tokens have been credited to your account.",
            "type":       "token_credit",
            "read":       False,
            "created_at": MongoSerializer.now_utc(),
        })

        return MongoJSONResponse({
            "ok":             True,
            "tokens_credited": tokens_to_credit,
            "new_balance":    new_balance,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"verify_club_token_topup error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Payment verification failed")


# ============================================================
# 23. MEDIA — ADD YOUTUBE VIDEO
# ============================================================

@router.post("/club/{uid}/media/youtube")
async def add_youtube_video(uid: str, request: Request, body: YouTubeAddBody):
    """Append a YouTube video entry to the club's media list."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        # Extract YouTube ID from URL
        import re as _re
        yt_id_match = _re.search(
            r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", body.url
        )
        if not yt_id_match:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        yt_id = yt_id_match.group(1)
        video_entry = {
            "id":         yt_id,
            "youtube_id": yt_id,
            "title":      body.title or "Club Video",
            "url":        body.url,
            "added_at":   MongoSerializer.now_utc().isoformat(),
        }

        await clubs_collection.update_one(
            _club_filter(uid),
            {
                "$push": {"youtube_videos": video_entry},
                "$set":  {"updated_at": MongoSerializer.now_utc()},
            },
        )
        return MongoJSONResponse({"ok": True, "youtube_id": yt_id, "video": video_entry})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"add_youtube_video error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 24. MEDIA — DELETE YOUTUBE VIDEO
# ============================================================

@router.delete("/club/{uid}/media/youtube/{yt_id}")
async def delete_youtube_video(uid: str, yt_id: str, request: Request):
    """Remove a YouTube video entry from the club's media list."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        await clubs_collection.update_one(
            _club_filter(uid),
            {
                "$pull": {
                    "youtube_videos": {
                        "$or": [{"youtube_id": yt_id}, {"id": yt_id}]
                    }
                },
                "$set": {"updated_at": MongoSerializer.now_utc()},
            },
        )
        return MongoJSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_youtube_video error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 25. SUBMIT STATS TRACKING REQUEST
# ============================================================

@router.post("/club/{uid}/stats-request")
async def submit_stats_request(uid: str, request: Request, body: StatsRequestBody):
    """
    Submit a new stats tracking request.
    Deducts tokens if tracking_type != 'no_tracking'.
    """
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        # Determine token cost
        level = club.get("category") or club.get("club_category") or "professional"
        token_cost = 0
        if body.tracking_type != "no_tracking":
            try:
                raw_cost = pricing_service.get_stats_request_cost("club", level)
                if body.tracking_type == "club_only":
                    token_cost = max(1, int(raw_cost * 0.6))
                else:
                    token_cost = int(raw_cost)
            except Exception:
                token_cost = 10

            # Check balance
            token_rec = await club_tokens_collection.find_one(
                {"$or": [{"club_id": uid}, {"user_id": uid}]}
            )
            balance = token_rec.get("balance", 0) if token_rec else 0
            if balance < token_cost:
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient tokens. Required: {token_cost}, Available: {balance}",
                )

            # Lock tokens (add to locked, subtract from balance)
            await club_tokens_collection.update_one(
                {"$or": [{"club_id": uid}, {"user_id": uid}]},
                {
                    "$inc": {
                        "balance": -token_cost,
                        "locked":   token_cost,
                    },
                    "$set": {"updated_at": MongoSerializer.now_utc()},
                },
            )

        reference_id = (
            _make_stats_request_ref()
            if callable(_make_stats_request_ref)
            else f"SR-{uid[:6].upper()}-{uuid.uuid4().hex[:8].upper()}"
        )
        player_ids = list(dict.fromkeys(
            str(pid) for pid in (body.player_ids or []) if pid
        ))
        doc = {
            "reference_id":   reference_id,
            "club_id":        uid,
            "user_id":        uid,
            "club_name":      club.get("club_name", ""),
            # FIX: explicit requester_type so admin isPlayerRequest() always returns
            # False for club requests regardless of future field additions.
            "requester_type": "club",
            "match_date":     body.match_date,
            "match_time":     body.match_time,
            "match_type":     body.match_type,
            "home_team":      body.home_team,
            "away_team":      body.away_team,
            "club_role":      body.club_role,
            "venue_address":  body.venue_address,
            "venue_country":  body.venue_country,
            "venue_country_code": body.venue_country_code,
            "venue_state":    body.venue_state,
            "venue_lga":      body.venue_lga,
            "venue_city":     body.venue_city,
            "venue_detailed_address": body.venue_detailed_address,
            "jersey_color":   body.jersey_color,
            "tracking_type":           body.tracking_type,
            "player_ids":              player_ids,
            "player_request_states":   [
                {"player_id": pid, "status": "Pending"} for pid in player_ids
            ],
            "entity_type":             "club",
            "request_type":            "club",
            "contact_phone":           body.contact_phone,
            "notes":                   body.notes,
            "player_stat_categories":  body.player_stat_categories or [],
            "token_cost":              token_cost,
            "status":         "Pending",
            "submitted_at":   MongoSerializer.now_utc(),
            "updated_at":     MongoSerializer.now_utc(),
        }

        await stats_requests_collection.insert_one(doc)

        # Debit transaction record
        if token_cost > 0:
            await transactions_collection.insert_one({
                "club_id":     uid,
                "user_id":     uid,
                "entity":      "club",
                "type":        "debit",
                "description": f"Stats tracking request ({body.tracking_type})",
                "amount":      0,
                "tokens":      token_cost,
                "status":      "completed",
                "reference":   reference_id,
                "created_at":  MongoSerializer.now_utc(),
            })

        return MongoJSONResponse({
            "ok":           True,
            "reference_id": reference_id,
            "status":       "SUBMITTED",
            "tokens_locked": token_cost,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"submit_stats_request error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to submit stats request")


# ============================================================
# 26. CLUB SEARCH (for Match Request — find opponent clubs)
# ============================================================

@router.get("/clubs/search")
async def search_clubs(
    request: Request,
    q: str = "",
    category: str = "",
    country: str = "",
    state: str = "",
    lga: str = "",
    city: str = "",
    limit: int = 20,
    page: int = 1,
):
    """
    Search registered clubs — used by the Match Request form to
    select an opponent.
    """
    try:
        limit = max(1, min(limit, 50))
        skip  = (max(1, page) - 1) * limit

        query: Dict[str, Any] = {}

        if q and len(q.strip()) >= 2:
            q_stripped = q.strip()
            if q_stripped.upper().startswith("CL-"):
                query["club_id"] = q_stripped.upper()
            else:
                query["$or"] = [
                    {"club_name":     {"$regex": q_stripped, "$options": "i"}},
                    {"club_nickname": {"$regex": q_stripped, "$options": "i"}},
                    {"address":       {"$regex": q_stripped, "$options": "i"}},
                ]

        if category:
            query["category"] = {"$regex": category, "$options": "i"}
        # Club location filtering delegated to location_module (single source of truth)
        for _clause in build_club_location_filter(country=country, state=state, lga=lga, city=city):
            query.setdefault("$and", []).append(_clause)

        clubs = await (
            clubs_collection.find(query)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        results = []
        for c in clubs:
            results.append({
                "_id":        str(c.get("_id", "")),
                "club_id":    c.get("club_id", ""),
                "club_name":  c.get("club_name", ""),
                "name":       c.get("club_name", ""),
                "category":   c.get("category", ""),
                "state":      c.get("state", "") or c.get("region", ""),
                "lga":        c.get("lga", ""),
                "city":       c.get("city", "") or c.get("town", ""),
                "country":    c.get("country", ""),
                "photo_url":  c.get("photo_url", ""),
                "is_verified": c.get("is_verified", False),
            })

        return MongoJSONResponse({"clubs": results, "total": len(results)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"search_clubs error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 27. SEND MATCH REQUEST
# ============================================================

@router.post("/club/{uid}/match-requests")
async def send_match_request(uid: str, request: Request, body: MatchRequestBody):
    """Send a match request to another club."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        reference_id = f"MR-{uuid.uuid4().hex[:8].upper()}"

        doc = {
            "reference_id":         reference_id,
            "requesting_club_id":   uid,
            "requesting_club_name": club.get("club_name", ""),
            "club_id":              uid,
            "user_id":              uid,
            "requested_club_id":    body.requested_club_id,
            "requested_club_name":  body.requested_club_name,
            "match_date":           body.match_date,
            "match_time":           body.match_time,
            "team_position":        body.team_position,
            "venue_country":        body.venue_country,
            "venue_country_code":   body.venue_country_code,
            "venue_state":          body.venue_state,
            "venue_lga":            body.venue_lga,
            "venue_city":           body.venue_city,
            "venue_detailed_address": body.venue_detailed_address,
            "venue_address":        body.venue_address,
            "jersey_color":         body.jersey_color,
            "tracking_type":        body.tracking_type or "no_tracking",
            "contact_phone":        body.contact_phone,
            "notes":                body.notes,
            "status":               "pending",
            "created_at":           MongoSerializer.now_utc(),
            "updated_at":           MongoSerializer.now_utc(),
        }

        await match_requests_collection.insert_one(doc)

        # Notify the receiving club
        await notifications_collection.insert_one({
            "user_id":   body.requested_club_id,
            "unique_id": body.requested_club_id,
            "user_type": "club",
            "title":     "New Match Request",
            "message":   f"{club.get('club_name', 'A club')} has sent you a match request for {body.match_date or 'an upcoming date'}.",
            "type":      "match_request",
            "read":      False,
            "reference_id": reference_id,
            "created_at": MongoSerializer.now_utc(),
        })

        return MongoJSONResponse({
            "ok":           True,
            "reference_id": reference_id,
            "request_id":   reference_id,
            "status":       "pending",
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"send_match_request error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 28a. RESPOND TO MATCH REQUEST — ACCEPT
# ============================================================

@router.patch("/club/{uid}/match-requests/{req_id}/accept")
async def accept_match_request(uid: str, req_id: str, request: Request):
    """Accept a received match request."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        or_clauses: List[Dict[str, Any]] = [{"reference_id": req_id}]
        if len(req_id) == 24:
            try:
                or_clauses.append({"_id": ObjectId(req_id)})
            except Exception:
                pass

        result = await match_requests_collection.update_one(
            {"$or": or_clauses, "requested_club_id": uid},
            {
                "$set": {
                    "status":     "accepted",
                    "updated_at": MongoSerializer.now_utc(),
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Match request not found or not addressed to this club")

        return MongoJSONResponse({"ok": True, "status": "accepted"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"accept_match_request error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 28b. RESPOND TO MATCH REQUEST — DECLINE
# ============================================================

@router.patch("/club/{uid}/match-requests/{req_id}/decline")
async def decline_match_request(uid: str, req_id: str, request: Request):
    """Decline a received match request."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        _id_filter: Dict[str, Any] = {"reference_id": req_id}
        if len(req_id) == 24:
            try:
                _id_filter = {"$or": [{"reference_id": req_id}, {"_id": ObjectId(req_id)}]}
            except Exception:
                pass

        result = await match_requests_collection.update_one(
            {**_id_filter, "requested_club_id": uid},
            {
                "$set": {
                    "status":     "declined",
                    "updated_at": MongoSerializer.now_utc(),
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Match request not found or not addressed to this club")

        return MongoJSONResponse({"ok": True, "status": "declined"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"decline_match_request error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 29. APPLY TO COMPETITION
# ============================================================

@router.post("/club/{uid}/competitions/{comp_id}/apply")
async def apply_to_competition(
    uid: str,
    comp_id: str,
    request: Request,
    body: CompetitionApplyBody,
):
    """Apply the club to a competition."""
    try:
        current_user = await get_current_user(request)
        _require_auth(current_user, uid)

        club = await _resolve_club(uid)
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        # Resolve competition
        comp_filter: Dict[str, Any] = {"$or": []}
        if len(comp_id) == 24:
            try:
                comp_filter["$or"].append({"_id": ObjectId(comp_id)})
            except Exception:
                pass
        comp_filter["$or"].append({"competition_id": comp_id})
        comp_filter["$or"].append({"slug": comp_id})

        comp = await competitions_collection.find_one(comp_filter)

        # Record application (upsert so re-applications are idempotent)
        applications_col = database["competition_applications"]
        await applications_col.update_one(
            {"club_id": uid, "competition_id": comp_id},
            {
                "$set": {
                    "club_id":        uid,
                    "club_name":      body.club_name or club.get("club_name", ""),
                    "competition_id": comp_id,
                    "comp_name":      comp.get("title") or comp.get("name", "") if comp else "",
                    "status":         "pending",
                    "applied_at":     MongoSerializer.now_utc(),
                    "updated_at":     MongoSerializer.now_utc(),
                }
            },
            upsert=True,
        )

        # Notification for club
        await notifications_collection.insert_one({
            "user_id":    uid,
            "unique_id":  uid,
            "user_type":  "club",
            "title":      "Competition Application Submitted",
            "message":    f"Your application for \"{comp.get('title', comp_id) if comp else comp_id}\" has been received.",
            "type":       "competition",
            "read":       False,
            "created_at": MongoSerializer.now_utc(),
        })

        return MongoJSONResponse({
            "ok":             True,
            "competition_id": comp_id,
            "status":         "pending",
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"apply_to_competition error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 30. SUPPORT — OPEN TICKET
# ============================================================

@router.post("/support/tickets")
async def open_support_ticket(request: Request, body: SupportTicketBody):
    """Open a new support ticket from the Support tab chat widget."""
    try:
        current_user = await get_current_user(request)

        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        doc = {
            "ticket_id":   ticket_id,
            "club_id":     body.club_id or current_user.get("club_id") or current_user.get("user_id"),
            "user_id":     current_user.get("_id") or current_user.get("user_id"),
            "user_type":   current_user.get("role", "club"),
            "reason":      body.reason,
            "status":      "open",
            "created_at":  MongoSerializer.now_utc(),
            "updated_at":  MongoSerializer.now_utc(),
        }

        await support_tickets_collection.insert_one(doc)
        return MongoJSONResponse({"ok": True, "ticket_id": ticket_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"open_support_ticket error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 31. SUPPORT — SEND CHAT MESSAGE
# ============================================================

@router.post("/support/chat/{ticket_id}")
async def send_support_chat_message(
    ticket_id: str,
    request: Request,
    body: SupportChatBody,
):
    """Append a chat message to a support ticket conversation."""
    try:
        current_user = await get_current_user(request)

        msg = {
            "ticket_id":  ticket_id,
            "sender_id":  current_user.get("_id") or current_user.get("user_id"),
            "sender_type": current_user.get("role", "club"),
            "text":       body.text,
            "created_at": MongoSerializer.now_utc(),
        }
        await support_messages_collection.insert_one(msg)

        # Keep ticket updated_at fresh
        await support_tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"updated_at": MongoSerializer.now_utc(), "last_message": body.text}},
        )

        return MongoJSONResponse({"ok": True, "ticket_id": ticket_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"send_support_chat_message error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# 32. VENUE SEARCH  (handled by /api/public/venues in auth.py)
# ============================================================



# ============================================================
# 33. BANK TRANSFER INTENT  (Payment Wizard step 2)
# ============================================================



# ============================================================
# 34. BANK DETAILS  (Payment Wizard step 3)
# ============================================================



# ============================================================
# 35. BANK TRANSFER RECEIPT UPLOAD  (Payment Wizard step 4)
# ============================================================

