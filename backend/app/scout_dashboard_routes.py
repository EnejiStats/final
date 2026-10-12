# ============================================================
# scout_dashboard_routes.py
# ENEJISTATS — Scout Dashboard API Routes
#
# Covers every API call made by the Scout Dashboard SPA
# (scout-dashboard.html / FILE C).  Integrates with main.py
# via the same _setup_dependencies() / APIRouter pattern used
# by auth.py, visitor_public_routes.py, player_dashboard_routes.py,
# and agent_dashboard_routes.py.
#
# ── Integration instructions ────────────────────────────────
# Add these three lines to main.py in the ROUTER MOUNTS block:
#
#     import scout_dashboard_routes as _sdr
#     _sdr._setup_dependencies(globals())
#     app.include_router(_sdr.router)
#
# ── Endpoint inventory (28 new routes) ──────────────────────
# /api/auth/me  and  /api/auth/logout  already exist in auth.py
# and are intentionally omitted here (Phase 7 duplication guard).
#
#   GET  /api/scout/{scout_id}/watchlist
#   POST /api/scout/{scout_id}/watchlist
#   DELETE /api/scout/{scout_id}/watchlist/{wl_id}
#   GET  /api/scout/{scout_id}/profile
#   PATCH /api/scout/{scout_id}/profile
#   POST /api/scout/{scout_id}/photo
#   GET  /api/players
#   GET  /api/players/search
#   GET  /api/clubs
#   GET  /api/clubs/search
#   GET  /api/player/{player_id}/public-profile
#   GET  /api/player/{player_id}/stats/summary
#   GET  /api/club/{club_id}/stats/summary
#   GET  /api/scout/{scout_id}/reports
#   POST /api/scout/{scout_id}/reports
#   GET  /api/scout/{scout_id}/reports/{report_id}
#   DELETE /api/scout/{scout_id}/reports/{report_id}
#   POST /api/scout/{scout_id}/background-check-requests
#   GET  /api/scout/{scout_id}/payment-history
#   GET  /api/subscription/pricing
#   GET  /api/token/pricing
#   POST /api/payment/bank-transfer/intent
#   GET  /api/bank-details/active
#   POST /api/payment/bank-transfer/receipt
#   GET  /api/scout/{scout_id}/notifications
#   PATCH /api/scout/{scout_id}/notifications/read-all     ← before {notif_id} route
#   PATCH /api/scout/{scout_id}/notifications/{notif_id}/read
#   PATCH /api/scout/{scout_id}/settings
# ============================================================
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from location_module import build_player_location_filter, build_club_location_filter

# ── Module-level router (same pattern as auth.py) ───────────
router = APIRouter()

# ── Injected globals — set by _setup_dependencies() ─────────
# Collections
_scouts_collection:          Any = None
_players_collection:         Any = None
_clubs_collection:           Any = None
_player_stats_collection:    Any = None
_notifications_collection:   Any = None
_transactions_collection:    Any = None
_payment_intents_collection: Any = None
_subscriptions_collection:   Any = None
_scout_tokens_collection:    Any = None
_database:                   Any = None

# Helpers / services
_MongoSerializer:            Any = None
_MongoJSONResponse:          Any = None
_upload_to_cloudinary:       Any = None
_pricing_service:            Any = None
_make_tx_ref:                Any = None
_calculate_performance_score: Any = None
_aggregate_player_stats:     Any = None
_find_user_doc:              Any = None
_get_current_user:           Any = None
_normalize_role:             Any = None
_get_scout_user:             Any = None
_BANK_TRANSFER_DETAILS:      Any = None
_logger:                     Any = None

_DEPS_READY = False
def _setup_dependencies(g: dict) -> None:
    """
    Inject runtime globals from main.py.

    Called by main.py immediately after::

        import scout_dashboard_routes as _sdr
        _sdr._setup_dependencies(globals())
        app.include_router(_sdr.router)

    This module never creates its own database connection. It reuses all
    shared objects injected from the parent FastAPI application.
    """
    global _DEPS_READY

    global _scouts_collection
    global _players_collection
    global _clubs_collection
    global _player_stats_collection
    global _notifications_collection
    global _transactions_collection
    global _payment_intents_collection
    global _subscriptions_collection
    global _scout_tokens_collection
    global _database

    global _MongoSerializer
    global _MongoJSONResponse
    global _upload_to_cloudinary
    global _pricing_service
    global _make_tx_ref
    global _calculate_performance_score
    global _aggregate_player_stats
    global _find_user_doc
    global _get_current_user
    global _normalize_role
    global _get_scout_user
    global _BANK_TRANSFER_DETAILS
    global _logger

    if _DEPS_READY:
        return

    # ── Database handle ──────────────────────────────────────
    _database = g.get("database")
    if _database is None:
        raise RuntimeError(
            "Database dependency was not injected into scout_dashboard_routes."
        )

    # ── Required collections ─────────────────────────────────
    _scouts_collection = g["scouts_collection"]
    _players_collection = g["players_collection"]
    _clubs_collection = g["clubs_collection"]
    _player_stats_collection = g["player_stats_collection"]
    _notifications_collection = g["notifications_collection"]
    _transactions_collection = g["transactions_collection"]
    _payment_intents_collection = g["payment_intents_collection"]
    _subscriptions_collection = g["subscriptions_collection"]
    _scout_tokens_collection = g["scout_tokens_collection"]

    # ── Optional collection fallbacks (future-proof) ─────────
    if _transactions_collection is None:
        _transactions_collection = _database["transactions"]

    if _payment_intents_collection is None:
        _payment_intents_collection = _database["payment_intents"]

    if _subscriptions_collection is None:
        _subscriptions_collection = _database["subscriptions"]

    if _scout_tokens_collection is None:
        _scout_tokens_collection = _database["scout_tokens"]

    # ── Shared helpers ───────────────────────────────────────
    _MongoSerializer = g["MongoSerializer"]
    _MongoJSONResponse = g["MongoJSONResponse"]
    _upload_to_cloudinary = g["upload_to_cloudinary"]
    _pricing_service = g["pricing_service"]
    _make_tx_ref = g["_make_tx_ref"]
    _calculate_performance_score = g["calculate_performance_score"]
    _aggregate_player_stats = g["aggregate_player_stats"]
    _find_user_doc = g["_find_user_doc"]
    _get_current_user = g["get_current_user"]
    _normalize_role = g["normalize_role"]
    _get_scout_user = g["get_scout_user"]

    _BANK_TRANSFER_DETAILS = g.get("BANK_TRANSFER_DETAILS", {})
    _logger = g["logger"]

    _DEPS_READY = True

    _logger.debug(
        "[scout_dashboard_routes] _setup_dependencies COMPLETE | "
        "scouts_collection=%s | scout_tokens_collection=%s",
        _scouts_collection.name if _scouts_collection is not None else "MISSING",
        _scout_tokens_collection.name if _scout_tokens_collection is not None else "MISSING",
    )
    
# ============================================================
# UTILITY HELPERS (module-level — no globals needed)
# ============================================================

def _try_objectid(value: str) -> Optional[ObjectId]:
    """Return ``ObjectId(value)`` if it is a valid 24-hex string, else ``None``."""
    try:
        return ObjectId(str(value))
    except Exception:
        return None


# ── Lazy collection accessors for new collections ───────────

def _watchlists():
    """Scout watchlist entries: {scout_id, player_id, added_at}."""
    return _database["scout_watchlists"]


def _reports():
    """Scout reports: {scout_id, report_type, title, content, …}."""
    return _database["scout_reports"]


def _bgc_col():
    """Background-check requests submitted by scouts."""
    return _database["background_check_requests"]


# ============================================================
# AUTH GUARD — shared by all scout-scoped endpoints
# ============================================================

async def _require_scout(request: Request, scout_id: str) -> dict:
    """
    Resolve the authenticated user and verify they are allowed to access
    ``scout_id``.

    Allowed:
      - The scout whose ``scout_id`` matches.
      - Any admin.

    Raises ``HTTPException(403)`` for everyone else.
    """
    user = await _get_current_user(request)
    try:
        role = _normalize_role(user.get("role") or user.get("user_type") or "")
    except (ValueError, TypeError):
        role = ""

    if role == "admin":
        return user

    if role != "scout":
        raise HTTPException(status_code=403, detail="Scout access required")

    # Compare every ID field the document might carry
    uid_candidates = [
        user.get("scout_id"),
        user.get("user_id"),
        user.get("id"),
        str(user.get("_id", "")),
    ]
    if not any(str(c) == str(scout_id) for c in uid_candidates if c):
        raise HTTPException(status_code=403, detail="Access denied: not your account")

    return user


# ============================================================
# PYDANTIC REQUEST BODIES
# ============================================================

class WatchlistAddBody(BaseModel):
    player_id: str


class ScoutProfileUpdate(BaseModel):
    firstName:   Optional[str] = None
    middleName:  Optional[str] = None
    lastName:    Optional[str] = None
    dob:         Optional[str] = None
    gender:      Optional[str] = None
    nationality: Optional[str] = None
    location:    Optional[str] = None
    phone:       Optional[str] = None
    bio:         Optional[str] = None

    class Config:
        extra = "allow"  # accept any extra profile fields


class ReportCreateBody(BaseModel):
    report_type:        str                       # player | club | watchlist_summary | player_comparison
    title:              Optional[str]             = None
    player_id:          Optional[str]             = None
    club_id:            Optional[str]             = None
    compare_player_ids: Optional[List[str]]       = None
    content:            Optional[Dict[str, Any]]  = None
    notes:              Optional[str]             = None

    class Config:
        extra = "allow"


class BgcRequestBody(BaseModel):
    subject_id:   str                # player_id or club_id
    subject_type: str                # "player" | "club"
    reason:       Optional[str] = None
    notes:        Optional[str] = None

    class Config:
        extra = "allow"


class PaymentIntentBody(BaseModel):
    payment_type: str          # "SUBSCRIPTION" | "TOKEN_PURCHASE"
    plan_key:     Optional[str] = None
    tokens:       Optional[int] = None
    amount:       float
    description:  Optional[str] = None

    class Config:
        extra = "allow"


class ScoutSettingsUpdate(BaseModel):
    notify_watchlist:  Optional[bool] = None
    notify_reports:    Optional[bool] = None
    notify_payments:   Optional[bool] = None
    notify_system:     Optional[bool] = None
    profile_visible:   Optional[bool] = None

    class Config:
        extra = "allow"


# ============================================================
# ① WATCHLIST
# ============================================================

@router.get("/api/scout/{scout_id}/watchlist")
async def get_scout_watchlist(scout_id: str, request: Request):
    """
    Return all watchlist entries for the scout with full player details
    embedded in each entry.

    Used by:
      - Overview tab (watchlist preview)
      - Watchlist tab (full listing)
    """
    await _require_scout(request, scout_id)
    try:
        entries = await _watchlists().find(
            {"scout_id": scout_id}
        ).sort("added_at", -1).to_list(length=500)

        enriched: List[Dict[str, Any]] = []
        for entry in entries:
            doc = _MongoSerializer.serialize_document(entry)
            pid = entry.get("player_id", "")
            if pid:
                player = await _players_collection.find_one(
                    {"$or": [
                        {"player_id": pid},
                        {"_id": _try_objectid(pid)},
                    ]},
                    {"password": 0},
                )
                if player:
                    doc["player"] = _MongoSerializer.serialize_document(player)
            enriched.append(doc)

        return JSONResponse({
            "success":   True,
            "watchlist": enriched,
            "count":     len(enriched),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_scout_watchlist error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/scout/{scout_id}/watchlist")
async def add_to_watchlist(
    scout_id: str,
    request:  Request,
    body:     WatchlistAddBody,
):
    """
    Add a player to the scout's watchlist.
    Idempotent — returns ``already_exists: true`` if the player is
    already on the list rather than creating a duplicate.
    """
    await _require_scout(request, scout_id)
    try:
        player_id = body.player_id.strip()

        # Verify player exists
        player = await _players_collection.find_one(
            {"$or": [
                {"player_id": player_id},
                {"_id": _try_objectid(player_id)},
            ]},
            {"password": 0},
        )
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        canonical_pid = player.get("player_id", player_id)

        # Idempotency guard
        existing = await _watchlists().find_one({
            "scout_id":  scout_id,
            "player_id": canonical_pid,
        })
        if existing:
            return JSONResponse({
                "success":        True,
                "message":        "Player already on watchlist",
                "entry_id":       str(existing["_id"]),
                "already_exists": True,
            })

        entry = {
            "scout_id":  scout_id,
            "player_id": canonical_pid,
            "added_at":  _MongoSerializer.now_utc(),
        }
        result = await _watchlists().insert_one(entry)
        return JSONResponse({
            "success":  True,
            "message":  "Player added to watchlist",
            "entry_id": str(result.inserted_id),
        }, status_code=201)
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("add_to_watchlist error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/scout/{scout_id}/watchlist/{wl_id}")
async def remove_from_watchlist(
    scout_id: str,
    wl_id:    str,
    request:  Request,
):
    """
    Remove a watchlist entry.

    ``wl_id`` can be either the MongoDB ``_id`` of the watchlist entry
    or the ``player_id`` stored in that entry — both are tried in order.
    """
    await _require_scout(request, scout_id)
    try:
        deleted = False

        # Try ObjectId (_id) first
        oid = _try_objectid(wl_id)
        if oid:
            res = await _watchlists().delete_one({"_id": oid, "scout_id": scout_id})
            deleted = res.deleted_count > 0

        # Fall back to player_id match
        if not deleted:
            res = await _watchlists().delete_one({
                "player_id": wl_id,
                "scout_id":  scout_id,
            })
            deleted = res.deleted_count > 0

        if not deleted:
            raise HTTPException(status_code=404, detail="Watchlist entry not found")

        return JSONResponse({"success": True, "message": "Removed from watchlist"})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("remove_from_watchlist error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ② PROFILE
# ============================================================

@router.get("/api/scout/{scout_id}/profile")
async def get_scout_profile(scout_id: str, request: Request):
    """
    Return the scout's full profile document with token balance and
    active subscription details appended.

    Used by:
      - Overview tab (avatar / stats)
      - Profile tab (view + edit form)
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        # Token wallet
        token_doc     = await _scout_tokens_collection.find_one({"scout_id": scout_id})
        token_balance = token_doc.get("balance", 0) if token_doc else 0
        token_expiry  = (
            _MongoSerializer.serialize_value(token_doc.get("expiry_date"))
            if token_doc else None
        )

        # Active subscription
        sub = await _subscriptions_collection.find_one(
            {"$or": [{"user_id": scout_id}, {"scout_id": scout_id}], "status": "active"},
            sort=[("created_at", -1)],
        )

        profile = _MongoSerializer.serialize_document(scout)
        profile.pop("password", None)
        profile["token_balance"] = token_balance
        profile["token_expiry"]  = token_expiry
        profile["subscription"]  = (
            _MongoSerializer.serialize_document(sub) if sub else None
        )

        return JSONResponse({"success": True, "profile": profile})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_scout_profile error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/scout/{scout_id}/profile")
async def update_scout_profile(
    scout_id: str,
    request:  Request,
    body:     ScoutProfileUpdate,
):
    """
    Patch one or more scout profile fields.
    Only the fields explicitly provided in the request body are updated.
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        update_data = {
            k: v
            for k, v in body.model_dump(exclude_unset=True).items()
            if v is not None
        }
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data["updated_at"] = _MongoSerializer.now_utc()
        await _scouts_collection.update_one(
            {"_id": scout["_id"]},
            {"$set": update_data},
        )

        updated = await _scouts_collection.find_one({"_id": scout["_id"]})
        result  = _MongoSerializer.serialize_document(updated)
        result.pop("password", None)
        return JSONResponse({"success": True, "profile": result})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("update_scout_profile error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/scout/{scout_id}/photo")
async def upload_scout_photo(
    scout_id: str,
    request:  Request,
    file:     UploadFile = File(...),
):
    """
    Upload / replace the scout's profile photo (multipart/form-data).
    Uploads to Cloudinary via ``upload_to_cloudinary`` from main.py
    and writes the returned URL back to the scout document.
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file upload")

        url = await _upload_to_cloudinary(
            file_content=content,
            filename=file.filename or "photo",
            user_type="scout",
            file_category="profiles",
            public_id=f"scout_{scout_id}_profile",
        )

        await _scouts_collection.update_one(
            {"_id": scout["_id"]},
            {"$set": {
                "photo":      url,
                "photo_url":  url,
                "updated_at": _MongoSerializer.now_utc(),
            }},
        )
        return JSONResponse({"success": True, "photo_url": url, "url": url})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("upload_scout_photo error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ③ PLAYERS — LIST & SEARCH
# ============================================================

@router.get("/api/players")
async def list_players(
    request:  Request,
    page:     int = 1,
    per_page: int = 20,
):
    """
    Paginated player list with no filter applied.
    Any authenticated user may call this endpoint.
    Password field is always stripped from results.
    """
    await _get_current_user(request)
    try:
        page     = max(1, page)
        per_page = max(1, min(per_page, 100))
        skip     = (page - 1) * per_page

        total   = await _players_collection.count_documents({})
        players = await _players_collection.find(
            {}, {"password": 0}
        ).skip(skip).limit(per_page).to_list(length=per_page)

        return JSONResponse({
            "success":  True,
            "players":  _MongoSerializer.serialize_documents(players),
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    max(1, -(-total // per_page)),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("list_players error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/players/search")
async def search_players(
    request:      Request,
    q:            Optional[str] = None,
    name:         Optional[str] = None,
    position:     Optional[str] = None,
    nationality:  Optional[str] = None,
    age_min:      Optional[int] = None,
    age_max:      Optional[int] = None,
    height_min:   Optional[int] = None,
    height_max:   Optional[int] = None,
    category:     Optional[str] = None,
    foot:         Optional[str] = None,
    state:        Optional[str] = None,
    city:         Optional[str] = None,
    has_agent:    Optional[str] = None,    # "true" | "false"
    has_contract: Optional[str] = None,    # "true" | "false"
    page:         int = 1,
    per_page:     int = 20,
):
    """
    Search / filter players by name, position, nationality, age, height,
    dominant foot, location (state/city), category, agent status, and
    contract status.  All filters are combined with AND logic.
    """
    await _get_current_user(request)
    try:
        page     = max(1, page)
        per_page = max(1, min(per_page, 100))
        skip     = (page - 1) * per_page

        and_clauses: List[Dict[str, Any]] = []

        # ── Free-text search (q or name)
        search_term = (q or name or "").strip()
        if search_term:
            pattern = {"$regex": search_term, "$options": "i"}
            and_clauses.append({"$or": [
                {"firstName":         pattern},
                {"lastName":          pattern},
                {"middleName":        pattern},
                {"name":              pattern},
                {"club":              pattern},
                {"player_id":         pattern},
                {"email":             pattern},
            ]})

        # ── Field filters
        if position:
            and_clauses.append({"$or": [
                {"preferredPosition": {"$regex": position, "$options": "i"}},
                {"preferred_position": {"$regex": position, "$options": "i"}},
                {"position":          {"$regex": position, "$options": "i"}},
            ]})

        if nationality:
            and_clauses.append({"nationality": {"$regex": nationality, "$options": "i"}})

        if category:
            and_clauses.append({"category": {"$regex": category, "$options": "i"}})

        if foot:
            and_clauses.append({"$or": [
                {"dominantFoot":  {"$regex": foot, "$options": "i"}},
                {"dominant_foot": {"$regex": foot, "$options": "i"}},
            ]})

        # Location filtering delegated to location_module (single source of truth)
        and_clauses.extend(build_player_location_filter(state=state, city=city))

        # ── Age filter (derived from dob string/datetime field)
        if age_min is not None or age_max is not None:
            now = _MongoSerializer.now_utc()
            dob_range: Dict[str, Any] = {}
            if age_max is not None:
                dob_range["$gte"] = datetime(
                    now.year - age_max, now.month, now.day,
                    tzinfo=timezone.utc
                )
            if age_min is not None:
                dob_range["$lte"] = datetime(
                    now.year - age_min, now.month, now.day,
                    tzinfo=timezone.utc
                )
            if dob_range:
                and_clauses.append({"dob": dob_range})

        # ── Height filter (stored as string "180" or int 180)
        if height_min is not None:
            and_clauses.append({"$or": [
                {"height": {"$gte": str(height_min)}},
                {"height": {"$gte": height_min}},
            ]})
        if height_max is not None:
            and_clauses.append({"$or": [
                {"height": {"$lte": str(height_max)}},
                {"height": {"$lte": height_max}},
            ]})

        # ── Agent / contract boolean flags
        _TRUE_VALUES  = ("true",  "1", "yes")
        _FALSE_VALUES = ("false", "0", "no")

        if has_agent is not None:
            lower_ha = has_agent.lower()
            if lower_ha in _TRUE_VALUES:
                and_clauses.append({"$or": [
                    {"has_agent": True},
                    {"agent_id": {"$exists": True, "$ne": None, "$ne": ""}},
                ]})
            elif lower_ha in _FALSE_VALUES:
                and_clauses.append({"$and": [
                    {"has_agent": {"$ne": True}},
                    {"agent_id": {"$exists": False}},
                ]})

        if has_contract is not None:
            lower_hc = has_contract.lower()
            if lower_hc in _TRUE_VALUES:
                and_clauses.append({"has_contract": True})
            elif lower_hc in _FALSE_VALUES:
                and_clauses.append({"has_contract": {"$ne": True}})

        query: Dict[str, Any] = {"$and": and_clauses} if and_clauses else {}

        total   = await _players_collection.count_documents(query)
        players = await _players_collection.find(
            query, {"password": 0}
        ).skip(skip).limit(per_page).to_list(length=per_page)

        return JSONResponse({
            "success":  True,
            "players":  _MongoSerializer.serialize_documents(players),
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    max(1, -(-total // per_page)),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("search_players error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ④ CLUBS — LIST & SEARCH
# ============================================================

@router.get("/api/clubs")
async def list_clubs(
    request:  Request,
    page:     int = 1,
    per_page: int = 20,
):
    """
    Paginated club list with no filter applied.
    Any authenticated user may call this endpoint.
    """
    await _get_current_user(request)
    try:
        page     = max(1, page)
        per_page = max(1, min(per_page, 100))
        skip     = (page - 1) * per_page

        total = await _clubs_collection.count_documents({})
        clubs = await _clubs_collection.find(
            {}, {"password": 0}
        ).skip(skip).limit(per_page).to_list(length=per_page)

        return JSONResponse({
            "success":  True,
            "clubs":    _MongoSerializer.serialize_documents(clubs),
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    max(1, -(-total // per_page)),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("list_clubs error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/scout/clubs/search")
async def search_clubs(
    request:    Request,
    q:          Optional[str] = None,
    name:       Optional[str] = None,
    category:   Optional[str] = None,
    reg_status: Optional[str] = None,
    state:      Optional[str] = None,
    city:       Optional[str] = None,
    page:       int = 1,
    per_page:   int = 20,
):
    """
    Search / filter clubs by name, category, registration status,
    state, and city.  All active filters combine with AND logic.
    """
    await _get_current_user(request)
    try:
        page     = max(1, page)
        per_page = max(1, min(per_page, 100))
        skip     = (page - 1) * per_page

        and_clauses: List[Dict[str, Any]] = []

        search_term = (q or name or "").strip()
        if search_term:
            pattern = {"$regex": search_term, "$options": "i"}
            and_clauses.append({"$or": [
                {"club_name":     pattern},
                {"club_nickname": pattern},
                {"club_id":       pattern},
                {"email":         pattern},
                {"address":       pattern},
                {"country":       pattern},
            ]})

        if category:
            and_clauses.append({"category": {"$regex": category, "$options": "i"}})

        if reg_status:
            and_clauses.append({
                "registration_status": {"$regex": reg_status, "$options": "i"}
            })

        # Club location filtering delegated to location_module
        and_clauses.extend(build_club_location_filter(state=state, city=city))

        query: Dict[str, Any] = {"$and": and_clauses} if and_clauses else {}

        total = await _clubs_collection.count_documents(query)
        clubs = await _clubs_collection.find(
            query, {"password": 0}
        ).skip(skip).limit(per_page).to_list(length=per_page)

        return JSONResponse({
            "success":  True,
            "clubs":    _MongoSerializer.serialize_documents(clubs),
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "pages":    max(1, -(-total // per_page)),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("search_clubs error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑤ PLAYER — PUBLIC PROFILE & STATS SUMMARY
# ============================================================

@router.get("/api/player/{player_id}/public-profile")
async def get_player_public_profile(player_id: str, request: Request):
    """
    Return a player's public profile (no password).
    Appends the most recent approved stats document for quick display.

    Used by:
      - Player comparison panel
      - Report preview
    """
    await _get_current_user(request)
    try:
        player = await _players_collection.find_one(
            {"$or": [
                {"player_id": player_id},
                {"_id": _try_objectid(player_id)},
            ]},
            {"password": 0},
        )
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        serialized = _MongoSerializer.serialize_document(player)

        # Latest approved stat entry (lightweight display)
        latest_stats = await _player_stats_collection.find_one(
            {"player_id": player.get("player_id", player_id), "status": "approved"},
            sort=[("match_date", -1)],
        )
        serialized["latest_stats"] = (
            _MongoSerializer.serialize_document(latest_stats)
            if latest_stats else None
        )

        return JSONResponse({"success": True, "player": serialized})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_player_public_profile error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/scout/player/{player_id}/stats/summary")
async def get_player_stats_summary(player_id: str, request: Request):
    """
    Return fully aggregated stats + calculated performance score for a player.

    Aggregation is performed by ``aggregate_player_stats`` from main.py;
    performance scoring is performed by ``calculate_performance_score``
    from main.py.  No token deduction is applied (read-only summary for scout).

    Used by:
      - Player comparison panel (stats breakdown)
      - Report creation (attach stats snapshot)
    """
    await _get_current_user(request)
    try:
        player = await _players_collection.find_one(
            {"$or": [
                {"player_id": player_id},
                {"_id": _try_objectid(player_id)},
            ]},
            {"password": 0},
        )
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        canonical_pid = player.get("player_id", player_id)

        stats_docs = await _player_stats_collection.find(
            {"player_id": canonical_pid, "status": "approved"}
        ).to_list(length=500)

        if not stats_docs:
            return JSONResponse({
                "success":           True,
                "player_id":         canonical_pid,
                "player":            _MongoSerializer.serialize_document(player),
                "matches_played":    0,
                "stats":             {},
                "performance_score": 0.0,
            })

        aggregated = await _aggregate_player_stats(canonical_pid, stats_docs)
        position   = (
            player.get("preferredPosition")
            or player.get("preferred_position")
            or player.get("position")
            or ""
        )
        score = _calculate_performance_score(aggregated, position)

        return JSONResponse({
            "success":           True,
            "player_id":         canonical_pid,
            "player":            _MongoSerializer.serialize_document(player),
            "matches_played":    len(stats_docs),
            "stats":             aggregated,
            "performance_score": score,
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_player_stats_summary error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑥ CLUB — STATS SUMMARY
# ============================================================

@router.get("/api/scout/club/{club_id}/stats/summary")
async def get_club_stats_summary(club_id: str, request: Request):
    """
    Return basic club stats summary for report creation.

    Returns:
      - club document
      - squad count (from ``club_squads`` collection)
      - aggregated match totals (goals, assists) from ``player_stats``
        for players whose club name matches.
    """
    await _get_current_user(request)
    try:
        club = await _clubs_collection.find_one(
            {"$or": [
                {"club_id": club_id},
                {"_id": _try_objectid(club_id)},
            ]},
            {"password": 0},
        )
        if not club:
            raise HTTPException(status_code=404, detail="Club not found")

        canonical_cid = club.get("club_id", club_id)
        serialized    = _MongoSerializer.serialize_document(club)

        # Squad size
        squad_col   = _database["club_squads"]
        squad_count = await squad_col.count_documents({"club_id": canonical_cid})

        # Aggregate approved player stats linked to this club
        club_name = club.get("club_name", "")
        if club_name:
            stats_docs = await _player_stats_collection.find(
                {"$or": [
                    {"club":      {"$regex": club_name, "$options": "i"}},
                    {"home_team": {"$regex": club_name, "$options": "i"}},
                    {"away_team": {"$regex": club_name, "$options": "i"}},
                ], "status": "approved"}
            ).limit(300).to_list(length=300)
        else:
            stats_docs = []

        goals   = sum(s.get("goals",   0) for s in stats_docs)
        assists = sum(s.get("assists",  0) for s in stats_docs)

        return JSONResponse({
            "success":     True,
            "club_id":     canonical_cid,
            "club":        serialized,
            "squad_count": squad_count,
            "stats": {
                "total_matches": len(stats_docs),
                "goals_scored":  goals,
                "total_assists": assists,
            },
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_club_stats_summary error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑦ REPORTS
# ============================================================

@router.get("/api/scout/{scout_id}/reports")
async def list_scout_reports(scout_id: str, request: Request):
    """
    Return all reports created by the scout, newest first.

    Used by:
      - Overview tab (recent reports preview)
      - Reports tab (full listing)
    """
    await _require_scout(request, scout_id)
    try:
        rpts = await _reports().find(
            {"scout_id": scout_id}
        ).sort("created_at", -1).to_list(length=500)

        return JSONResponse({
            "success": True,
            "reports": _MongoSerializer.serialize_documents(rpts),
            "count":   len(rpts),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("list_scout_reports error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/scout/{scout_id}/reports")
async def create_scout_report(
    scout_id: str,
    request:  Request,
    body:     ReportCreateBody,
):
    """
    Create a scout report.

    Supported ``report_type`` values:
      - ``player``             — single-player scouting report
      - ``club``               — club analysis report
      - ``watchlist_summary``  — snapshot of the entire watchlist
      - ``player_comparison``  — side-by-side comparison of two or more players

    Data snapshots are embedded at creation time so reports remain
    accurate even if the underlying records are later updated.
    """
    await _require_scout(request, scout_id)
    try:
        VALID_TYPES = {"player", "club", "watchlist_summary", "player_comparison"}
        if body.report_type not in VALID_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report_type. Must be one of: {', '.join(sorted(VALID_TYPES))}",
            )

        # ── Embed live snapshots at creation time ────────────
        snapshot: Dict[str, Any] = {}

        if body.report_type == "player" and body.player_id:
            p = await _players_collection.find_one(
                {"$or": [
                    {"player_id": body.player_id},
                    {"_id": _try_objectid(body.player_id)},
                ]},
                {"password": 0},
            )
            if p:
                snapshot["player_snapshot"] = _MongoSerializer.serialize_document(p)

        elif body.report_type == "club" and body.club_id:
            c = await _clubs_collection.find_one(
                {"$or": [
                    {"club_id": body.club_id},
                    {"_id": _try_objectid(body.club_id)},
                ]},
                {"password": 0},
            )
            if c:
                snapshot["club_snapshot"] = _MongoSerializer.serialize_document(c)

        elif body.report_type == "player_comparison" and body.compare_player_ids:
            snaps: List[Dict[str, Any]] = []
            for pid in body.compare_player_ids:
                p = await _players_collection.find_one(
                    {"$or": [
                        {"player_id": pid},
                        {"_id": _try_objectid(pid)},
                    ]},
                    {"password": 0},
                )
                if p:
                    snaps.append(_MongoSerializer.serialize_document(p))
            snapshot["comparison_snapshots"] = snaps

        elif body.report_type == "watchlist_summary":
            wl = await _watchlists().find({"scout_id": scout_id}).to_list(length=500)
            snapshot["watchlist_snapshot"] = _MongoSerializer.serialize_documents(wl)

        # ── Persist the report ──────────────────────────────
        report_doc: Dict[str, Any] = {
            "scout_id":           scout_id,
            "report_type":        body.report_type,
            "title":              body.title or f"{body.report_type.replace('_', ' ').title()} Report",
            "player_id":          body.player_id,
            "club_id":            body.club_id,
            "compare_player_ids": body.compare_player_ids,
            "content":            body.content or {},
            "notes":              body.notes,
            "created_at":         _MongoSerializer.now_utc(),
            "updated_at":         _MongoSerializer.now_utc(),
            **snapshot,
        }

        result         = await _reports().insert_one(report_doc)
        report_doc["_id"] = str(result.inserted_id)

        return JSONResponse(
            {"success": True, "report": _MongoSerializer.serialize_document(report_doc)},
            status_code=201,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("create_scout_report error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/scout/{scout_id}/reports/{report_id}")
async def get_scout_report(
    scout_id:  str,
    report_id: str,
    request:   Request,
):
    """Fetch a single scout report by its MongoDB ``_id``."""
    await _require_scout(request, scout_id)
    try:
        oid = _try_objectid(report_id)
        if not oid:
            raise HTTPException(status_code=400, detail="Invalid report ID format")

        rpt = await _reports().find_one({"_id": oid, "scout_id": scout_id})
        if not rpt:
            raise HTTPException(status_code=404, detail="Report not found")

        return JSONResponse({
            "success": True,
            "report":  _MongoSerializer.serialize_document(rpt),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_scout_report error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/scout/{scout_id}/reports/{report_id}")
async def delete_scout_report(
    scout_id:  str,
    report_id: str,
    request:   Request,
):
    """Permanently delete a scout report by its MongoDB ``_id``."""
    await _require_scout(request, scout_id)
    try:
        oid = _try_objectid(report_id)
        if not oid:
            raise HTTPException(status_code=400, detail="Invalid report ID format")

        res = await _reports().delete_one({"_id": oid, "scout_id": scout_id})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Report not found")

        return JSONResponse({"success": True, "message": "Report deleted"})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("delete_scout_report error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑧ BACKGROUND CHECK REQUESTS
# ============================================================

@router.post("/api/scout/{scout_id}/background-check-requests")
async def submit_background_check_request(
    scout_id: str,
    request:  Request,
    body:     BgcRequestBody,
):
    """
    Submit a background check request for a player or club.

    The request is stored with ``status: 'pending'`` and a unique
    reference code.  Admin staff review and update the status separately.
    """
    await _require_scout(request, scout_id)
    try:
        VALID_SUBJECT_TYPES = {"player", "club"}
        if body.subject_type not in VALID_SUBJECT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="subject_type must be 'player' or 'club'",
            )

        # Verify subject exists
        if body.subject_type == "player":
            subject = await _players_collection.find_one(
                {"$or": [
                    {"player_id": body.subject_id},
                    {"_id": _try_objectid(body.subject_id)},
                ]}
            )
        else:
            subject = await _clubs_collection.find_one(
                {"$or": [
                    {"club_id": body.subject_id},
                    {"_id": _try_objectid(body.subject_id)},
                ]}
            )

        if not subject:
            raise HTTPException(
                status_code=404,
                detail=f"{body.subject_type.capitalize()} not found",
            )

        bgc_doc: Dict[str, Any] = {
            "scout_id":     scout_id,
            "subject_id":   body.subject_id,
            "subject_type": body.subject_type,
            "reason":       body.reason,
            "notes":        body.notes,
            "status":       "pending",
            "reference":    f"BGC-{secrets.token_hex(6).upper()}",
            "created_at":   _MongoSerializer.now_utc(),
        }

        result      = await _bgc_col().insert_one(bgc_doc)
        bgc_doc["_id"] = str(result.inserted_id)

        return JSONResponse(
            {"success": True, "request": _MongoSerializer.serialize_document(bgc_doc)},
            status_code=201,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("submit_background_check_request error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑨ PAYMENT HISTORY
# ============================================================

@router.get("/api/scout/{scout_id}/payment-history")
async def get_payment_history(scout_id: str, request: Request):
    """
    Return the scout's billing / payment history.

    Queries two collections:
      - ``transactions`` (completed credits, debits, subscription charges)
      - ``payment_intents`` (pending / receipt-uploaded bank transfers)

    Both are matched by ``scout_id`` or ``user_id`` to cover legacy
    documents that stored the user under either field.
    """
    await _require_scout(request, scout_id)
    try:
        txns = await _transactions_collection.find(
            {"$or": [
                {"unique_id": scout_id},
                {"user_id":   scout_id},
            ]}
        ).sort("created_at", -1).limit(200).to_list(length=200)

        intents = await _payment_intents_collection.find(
            {"$or": [
                {"scout_id": scout_id},
                {"user_id":  scout_id},
            ]}
        ).sort("created_at", -1).limit(100).to_list(length=100)

        return JSONResponse({
            "success":      True,
            "transactions": _MongoSerializer.serialize_documents(txns),
            "intents":      _MongoSerializer.serialize_documents(intents),
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_payment_history error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑩ PRICING
# ============================================================

@router.get("/api/subscription/pricing")
async def get_subscription_pricing():
    """
    Return subscription plans for the scout role.
    Served by ``pricing_service.get_subscription_plans()`` from main.py —
    the single source of truth for all pricing.
    """
    plans = _pricing_service.get_subscription_plans("scout")
    return JSONResponse({"success": True, "plans": plans, "role": "scout"})


@router.get("/api/token/pricing")
async def get_token_pricing():
    """
    Return token packages available for scouts.
    Served by ``pricing_service.get_token_packages()`` from main.py.
    """
    packages = _pricing_service.get_token_packages("scout")
    return JSONResponse({"success": True, "packages": packages, "role": "scout"})


# ============================================================
# ⑪ PAYMENT — BANK TRANSFER
# ============================================================

@router.post("/api/scout/payment/bank-transfer/intent")
async def create_bank_transfer_intent(
    request: Request,
    body:    PaymentIntentBody,
):
    """
    Create a pending bank-transfer payment intent.

    Handles:
      - ``payment_type: "SUBSCRIPTION"``   — subscription purchase
      - ``payment_type: "TOKEN_PURCHASE"`` — token top-up

    The intent document is created with ``status: 'pending'`` and a
    unique ``tx_ref`` generated by ``_make_tx_ref`` from main.py.
    The intent expires after 48 hours (enforced by the TTL index on
    ``payment_intents``).
    """
    user = await _get_current_user(request)
    try:
        VALID_TYPES = {"SUBSCRIPTION", "TOKEN_PURCHASE"}
        if body.payment_type not in VALID_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"payment_type must be one of: {', '.join(VALID_TYPES)}",
            )
        if body.amount <= 0:
            raise HTTPException(status_code=400, detail="amount must be a positive number")

        role    = user.get("role", "scout")
        user_id = (
            user.get("scout_id")
            or user.get("user_id")
            or str(user.get("_id", ""))
        )
        tx_ref  = _make_tx_ref(body.payment_type, role)

        intent: Dict[str, Any] = {
            "scout_id":     user_id,
            "user_id":      user_id,
            "user_type":    role,
            "payment_type": body.payment_type,
            "plan_key":     body.plan_key,
            "tokens":       body.tokens,
            "amount":       body.amount,
            "description":  body.description or body.payment_type,
            "tx_ref":       tx_ref,
            "status":       "pending",
            "method":       "bank_transfer",
            "expires_at":   _MongoSerializer.now_utc() + timedelta(hours=48),
            "created_at":   _MongoSerializer.now_utc(),
        }
        result        = await _payment_intents_collection.insert_one(intent)
        intent["_id"] = str(result.inserted_id)

        return JSONResponse(
            {
                "success": True,
                "intent":  _MongoSerializer.serialize_document(intent),
                "tx_ref":  tx_ref,
            },
            status_code=201,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("create_bank_transfer_intent error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/scout/bank-details/active")
async def get_active_bank_details(request: Request):
    """
    Return the active bank account details for manual bank transfers.

    Resolution order:
      1. Admin-configured bank details stored in ``admin_settings`` (key: "platform")
      2. ``BANK_TRANSFER_DETAILS`` environment constants from main.py

    Raises ``HTTP 503`` when no account number is configured.
    """
    await _get_current_user(request)
    try:
        admin_settings_col = _database["admin_settings"]
        settings_doc       = await admin_settings_col.find_one({"key": "platform"})
        bank_info: Dict[str, Any] = {}

        if settings_doc:
            bt = settings_doc.get("bank_transfer", {})
            # Accept the DB record only if it has at least the account number
            if bt.get("account_number") or bt.get("bank_name"):
                bank_info = bt

        if not bank_info:
            bank_info = dict(_BANK_TRANSFER_DETAILS)

        if not bank_info.get("account_number"):
            raise HTTPException(
                status_code=503,
                detail="Bank transfer details are not configured on this platform",
            )

        return JSONResponse({"success": True, "bank_details": bank_info})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_active_bank_details error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/scout/payment/bank-transfer/receipt")
async def upload_bank_transfer_receipt(
    request: Request,
    tx_ref:  str         = Form(...),
    file:    UploadFile  = File(...),
):
    """
    Upload a bank-transfer payment receipt (multipart/form-data).

    Steps:
      1. Verify the authenticated user owns the payment intent identified by ``tx_ref``.
      2. Upload the file to Cloudinary (``user_type="scout"``, ``file_category="documents"``).
      3. Patch the intent document with ``receipt_url`` and ``status: 'receipt_uploaded'``.

    Admin staff then review the receipt and activate the subscription / tokens.
    """
    user = await _get_current_user(request)
    try:
        user_id = (
            user.get("scout_id")
            or user.get("user_id")
            or str(user.get("_id", ""))
        )

        intent = await _payment_intents_collection.find_one({"tx_ref": tx_ref})
        if not intent:
            raise HTTPException(status_code=404, detail="Payment intent not found")

        # Ownership check
        intent_owner = str(intent.get("user_id", "") or intent.get("scout_id", ""))
        if intent_owner and intent_owner != str(user_id) and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not your payment intent")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file upload")

        receipt_url = await _upload_to_cloudinary(
            file_content=content,
            filename=file.filename or "receipt",
            user_type="scout",
            file_category="documents",
            public_id=f"receipt_{tx_ref}_{secrets.token_hex(4)}",
        )

        await _payment_intents_collection.update_one(
            {"tx_ref": tx_ref},
            {"$set": {
                "receipt_url":  receipt_url,
                "status":       "receipt_uploaded",
                "submitted_at": _MongoSerializer.now_utc(),
            }},
        )

        return JSONResponse({
            "success":     True,
            "receipt_url": receipt_url,
            "tx_ref":      tx_ref,
            "status":      "receipt_uploaded",
            "message":     "Receipt uploaded successfully. Payment is pending admin verification.",
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("upload_bank_transfer_receipt error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑫ NOTIFICATIONS
# IMPORTANT: /notifications/read-all MUST be registered BEFORE
# /notifications/{notif_id}/read so FastAPI does not capture
# the literal segment "read-all" as a {notif_id} value.
# ============================================================

@router.get("/api/scout/{scout_id}/notifications")
async def get_scout_notifications(scout_id: str, request: Request):
    """
    Return all notifications for the scout plus a real-time unread count.

    Notifications are matched by ``unique_id``, ``user_id`` (string),
    or ``user_id`` (ObjectId string) to cover every write path in main.py.
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        oid_str = str(scout["_id"])

        notifs = await _notifications_collection.find(
            {"$or": [
                {"unique_id": scout_id},
                {"user_id":   oid_str},
                {"user_id":   scout_id},
            ]}
        ).sort("created_at", -1).limit(100).to_list(length=100)

        unread = sum(1 for n in notifs if not n.get("read", False))

        return JSONResponse({
            "success":       True,
            "notifications": _MongoSerializer.serialize_documents(notifs),
            "unread_count":  unread,
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("get_scout_notifications error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/scout/{scout_id}/notifications/read-all")
async def mark_all_notifications_read(scout_id: str, request: Request):
    """
    Mark every unread notification for the scout as read in one operation.

    Registered BEFORE the ``/{notif_id}/read`` route so the literal
    path segment ``read-all`` is matched correctly.
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        oid_str = str(scout["_id"])
        now     = _MongoSerializer.now_utc()

        res = await _notifications_collection.update_many(
            {"$or": [
                {"unique_id": scout_id},
                {"user_id":   oid_str},
                {"user_id":   scout_id},
            ]},
            {"$set": {"read": True, "read_at": now}},
        )

        return JSONResponse({
            "success":      True,
            "marked_count": res.modified_count,
            "message":      f"{res.modified_count} notification(s) marked as read",
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("mark_all_notifications_read error")
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/api/scout/{scout_id}/notifications/{notif_id}/read")
async def mark_notification_read(
    scout_id: str,
    notif_id: str,
    request:  Request,
):
    """
    Mark a single notification as read by its MongoDB ``_id``.

    Registered AFTER ``/read-all`` — see ordering note above.
    """
    await _require_scout(request, scout_id)
    try:
        oid = _try_objectid(notif_id)
        if not oid:
            raise HTTPException(status_code=400, detail="Invalid notification ID format")

        res = await _notifications_collection.update_one(
            {"_id": oid},
            {"$set": {"read": True, "read_at": _MongoSerializer.now_utc()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

        return JSONResponse({"success": True, "message": "Notification marked as read"})
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("mark_notification_read error")
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# ⑬ SETTINGS
# ============================================================

@router.patch("/api/scout/{scout_id}/settings")
async def update_scout_settings(
    scout_id: str,
    request:  Request,
    body:     ScoutSettingsUpdate,
):
    """
    Save scout notification preferences and profile visibility.

    Storage convention:
      - ``profile_visible``   stored at the root of the scout document.
      - All notification flags stored under a ``settings`` sub-document:
          settings.notify_watchlist
          settings.notify_reports
          settings.notify_payments
          settings.notify_system

    Only explicitly provided fields are written (PATCH semantics).
    """
    await _require_scout(request, scout_id)
    try:
        scout = await _find_user_doc("scout", scout_id)
        if not scout:
            raise HTTPException(status_code=404, detail="Scout not found")

        settings_data = body.model_dump(exclude_unset=True)
        if not settings_data:
            raise HTTPException(status_code=400, detail="No settings fields provided")

        set_payload: Dict[str, Any] = {}
        for key, val in settings_data.items():
            if key == "profile_visible":
                set_payload["profile_visible"] = val
            else:
                set_payload[f"settings.{key}"] = val
        set_payload["updated_at"] = _MongoSerializer.now_utc()

        await _scouts_collection.update_one(
            {"_id": scout["_id"]},
            {"$set": set_payload},
        )

        updated = await _scouts_collection.find_one({"_id": scout["_id"]})
        result  = _MongoSerializer.serialize_document(updated)
        result.pop("password", None)

        return JSONResponse({
            "success":  True,
            "settings": result.get("settings", {}),
            "profile":  result,
        })
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("update_scout_settings error")
        raise HTTPException(status_code=500, detail=str(exc))
