"""
ENEJISTATS — Supervisor Dashboard Routes
==========================================
Standalone FastAPI router module covering every API endpoint consumed by
supervisor-dashboard.html (the Preact SPA).

ENDPOINT INVENTORY — 27 new routes (Phase 7 dedup applied)
────────────────────────────────────────────────────────────
SKIPPED (already registered by other modules):
  GET  /api/auth/me                        → auth.py
  POST /api/auth/logout                    → auth.py
  POST /api/auth/change-password           → auth.py
  GET  /api/subscription/pricing           → scout_dashboard_routes.py
  POST /api/payment/bank-transfer/intent   → scout_dashboard_routes.py
  GET  /api/bank-details/active            → scout_dashboard_routes.py
  POST /api/payment/bank-transfer/receipt  → scout_dashboard_routes.py
  GET  /api/support/tickets                → main.py
  POST /api/support/tickets                → main.py
  GET  /api/support/chat/{tid}             → main.py
  POST /api/support/chat/{tid}             → main.py

NEW ENDPOINTS (27):
  §1  Profile & Photo (3)
      GET   /api/supervisor/{supervisor_id}/profile
      PATCH /api/supervisor/{supervisor_id}/profile
      POST  /api/supervisor/{supervisor_id}/photo

  §2  Withdrawal Account (2)
      GET   /api/supervisor/{supervisor_id}/withdrawal-account
      PATCH /api/supervisor/{supervisor_id}/withdrawal-account

  §3  DCO Management (3)
      GET    /api/supervisor/{supervisor_id}/dcos
      POST   /api/supervisor/{supervisor_id}/dcos/add
      DELETE /api/supervisor/{supervisor_id}/dcos/{dco_id}/remove

  §4  Live Monitoring (1)
      GET /api/supervisor/{supervisor_id}/live-monitoring

  §5  Assignments (4)
      GET    /api/supervisor/{supervisor_id}/assignments
      POST   /api/supervisor/{supervisor_id}/assignments/create
      PATCH  /api/supervisor/{supervisor_id}/assignments/{assignment_id}
      DELETE /api/supervisor/{supervisor_id}/assignments/{assignment_id}/delete

  §6  Pending Approvals & Submissions (3)
      GET  /api/supervisor/{supervisor_id}/pending-approvals
      POST /api/supervisor/{supervisor_id}/submissions/{submission_id}/approve
      POST /api/supervisor/{supervisor_id}/submissions/{submission_id}/reject

  §7  Submissions History (1)
      GET /api/supervisor/{supervisor_id}/submissions-history

  §8  Earnings & Payouts (3)
      GET  /api/supervisor/{supervisor_id}/earnings
      GET  /api/supervisor/{supervisor_id}/payout-requests
      POST /api/supervisor/{supervisor_id}/payout-requests

  §9  Notifications (2)
      GET   /api/supervisor/{supervisor_id}/notifications
      PATCH /api/supervisor/{supervisor_id}/notifications/{notif_id}/read

  §10 Chat (3)
      GET  /api/supervisor/{supervisor_id}/chat/threads
      GET  /api/supervisor/{supervisor_id}/chat/threads/{thread_id}/messages
      POST /api/supervisor/{supervisor_id}/chat/threads/{thread_id}/send

  §11 Subscription (2)
      GET /api/supervisor/{supervisor_id}/subscription
      GET /api/supervisor/{supervisor_id}/subscription/history

ROUTE-ORDERING NOTE
────────────────────
All fixed-path routes within each section are registered before their
parameterised siblings so FastAPI never captures a literal segment as a
path parameter.

HOW TO INTEGRATE (main.py — in the ROUTER MOUNTS block)
─────────────────────────────────────────────────────────
    import supervisor_dashboard_routes as _svdr
    _svdr._setup_dependencies(globals())
    app.include_router(_svdr.router)

NEW COLLECTIONS (created lazily via database[name])
────────────────────────────────────────────────────
  supervisor_assignments_collection   → database["supervisor_assignments"]
  supervisor_payout_requests_col      → database["supervisor_payout_requests"]
  supervisor_chat_threads_col         → database["supervisor_chat_threads"]
  supervisor_chat_messages_col        → database["supervisor_chat_messages"]

WHY _setup_dependencies?
─────────────────────────
A plain `from main import …` at the top of this file creates a circular
import loop.  Instead every shared symbol is injected by _setup_dependencies()
which is called by main.py AFTER all of main.py's own symbols are bound.

LOCATION DATA
─────────────
All country, region (state/province/etc.) and subregion (LGA/county/etc.)
data is sourced exclusively from location_module.  No location lists or
country mappings are defined in this file.  Use the helpers imported below
to resolve, validate, and normalise any location field.
"""

# ============================================================
# STANDARD-LIBRARY & THIRD-PARTY IMPORTS ONLY
# (No import from main — circular import avoided)
# ============================================================
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ── Location source of truth ──────────────────────────────────────────────────
# All country / state / LGA data lives exclusively in location_module.
# Never define location lists or country name mappings here — import them
# from location_module instead so there is one single source of truth.
from location_module import (
    LOCATION_CONFIG,
    COUNTRY_NAMES,
    CONTINENT_CODES,
    AFRICA_SUB_REGIONS,
    get_location_config,
    get_regions_payload,
    get_subregions_payload,
    get_country_name,
    get_all_supported_country_codes,
    get_nigerian_states,
    get_nigerian_lgas,
    validate_country_code,
    validate_region,
    validate_subregion,
    build_player_location_filter,
    build_club_location_filter,
    build_venue_location_filter,
    build_stadium_location_clauses,
)

# ============================================================
# MODULE-LEVEL PLACEHOLDERS
# All None here; populated once by _setup_dependencies().
# ============================================================

# ── Database handle ──────────────────────────────────────────
database = None

# ── Role collections ─────────────────────────────────────────
supervisors_collection = None
dco_collection         = None          # also aliased as dcos_collection in main

# ── Shared collections ────────────────────────────────────────
player_stats_collection     = None     # legacy DCO submissions
stat_submissions_collection = None     # canonical stats-tracker submissions
stat_submission_players_collection = None
notifications_collection    = None
subscriptions_collection    = None
subscription_plans_collection = None
payment_intents_collection  = None
liveness_sessions_collection = None
transactions_collection     = None

# ── Lazy collections (created on first access) ────────────────
# These are resolved inside _setup_dependencies from database[]
supervisor_assignments_collection  = None   # database["supervisor_assignments"]
supervisor_payout_requests_col     = None   # database["supervisor_payout_requests"]
supervisor_chat_threads_col        = None   # database["supervisor_chat_threads"]
supervisor_chat_messages_col       = None   # database["supervisor_chat_messages"]

# ── Cross-module collections (injected from main, already exist) ──────────
dco_assignments_collection    = None   # assignments created by admin
stats_requests_collection     = None   # stats requests from clubs/admins
players_collection            = None   # player documents (for live enrichment)

# ── Auth helpers ─────────────────────────────────────────────
get_current_user    = None
normalize_role       = None
get_supervisor_user = None

# ── Business-logic helpers ────────────────────────────────────
MongoSerializer      = None
logger               = None
upload_to_cloudinary = None
pricing_service      = None

# ── Payment helpers ───────────────────────────────────────────
BANK_TRANSFER_DETAILS        = None
_make_tx_ref                 = None
_make_supervisor_payout_ref  = None

_DEPS_READY = False


# ============================================================
# DEPENDENCY INJECTION — called once from main.py
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Populate every module-level placeholder from the main module namespace.

    Called by main.py immediately after importing this module:

        import supervisor_dashboard_routes as _svdr
        _svdr._setup_dependencies(globals())
        app.include_router(_svdr.router)

    NOTE: Location data (countries, states, LGAs) is NOT injected here
    because it is imported directly from location_module at the top of this
    file — no duplication, no injection needed.
    """

    global _DEPS_READY

    global database
    global supervisors_collection, dco_collection
    global player_stats_collection, stat_submissions_collection, stat_submission_players_collection, notifications_collection
    global subscriptions_collection, subscription_plans_collection
    global payment_intents_collection, liveness_sessions_collection
    global transactions_collection
    global supervisor_assignments_collection, supervisor_payout_requests_col
    global supervisor_chat_threads_col, supervisor_chat_messages_col
    global dco_assignments_collection, stats_requests_collection, players_collection, matches_collection, supervisor_recruitments_collection
    global get_current_user, get_supervisor_user, normalize_role
    global MongoSerializer, logger, upload_to_cloudinary, pricing_service
    global BANK_TRANSFER_DETAILS, _make_tx_ref, _make_supervisor_payout_ref

    if _DEPS_READY:
        return

    _m = main_globals

    # ── Database handle ──────────────────────────────────────
    database = _m.get("database")
    if database is None:
        raise RuntimeError(
            "Database dependency was not injected into supervisor_dashboard_routes."
        )

    # ── Role collections ─────────────────────────────────────
    supervisors_collection = _m["supervisors_collection"]

    dco_collection = _m.get("dco_collection")
    if dco_collection is None:
        dco_collection = _m.get("dcos_collection")

    # ── Shared collections ───────────────────────────────────
    player_stats_collection = _m.get("player_stats_collection")
    stat_submissions_collection = _m.get("stat_submissions_collection")
    if stat_submissions_collection is None:
        stat_submissions_collection = database["stat_submissions"]
    stat_submission_players_collection = _m.get("stat_submission_players_collection")
    if stat_submission_players_collection is None:
        stat_submission_players_collection = database["stat_submission_players"]
    notifications_collection = _m["notifications_collection"]
    subscriptions_collection = _m["subscriptions_collection"]
    subscription_plans_collection = _m["subscription_plans_collection"]
    payment_intents_collection = _m["payment_intents_collection"]
    liveness_sessions_collection = _m["liveness_sessions_collection"]
    transactions_collection = _m["transactions_collection"]

    # ── Lazy collections (created automatically by MongoDB) ──
    supervisor_assignments_collection = database["supervisor_assignments"]
    supervisor_payout_requests_col = database["supervisor_payout_requests"]
    supervisor_chat_threads_col = database["supervisor_chat_threads"]
    supervisor_chat_messages_col = database["supervisor_chat_messages"]

    # ── Cross-module collections (from main) ─────────────────
    dco_assignments_collection   = _m.get("dco_assignments_collection")
    stats_requests_collection    = _m.get("stats_requests_collection")
    players_collection           = _m.get("players_collection")
    matches_collection            = _m.get("matches_collection")
    if matches_collection is None:
        matches_collection = database["matches"]
    supervisor_recruitments_collection = _m.get("supervisor_recruitments_collection")
    if supervisor_recruitments_collection is None:
        supervisor_recruitments_collection = database["supervisor_dco_recruitments"]

    # ── Auth helpers ─────────────────────────────────────────
    get_current_user = _m["get_current_user"]
    normalize_role = _m["normalize_role"]
    get_supervisor_user = _m["get_supervisor_user"]

    # ── Business logic helpers ───────────────────────────────
    MongoSerializer = _m["MongoSerializer"]
    logger = _m["logger"]
    upload_to_cloudinary = _m.get("upload_to_cloudinary")
    pricing_service = _m.get("pricing_service")

    # ── Payment helpers ──────────────────────────────────────
    BANK_TRANSFER_DETAILS = _m.get("BANK_TRANSFER_DETAILS", {})
    _make_tx_ref = _m.get("_make_tx_ref")
    _make_supervisor_payout_ref = _m.get("_make_supervisor_payout_ref")

    _DEPS_READY = True

    logger.debug(
        "[supervisor_dashboard_routes] _setup_dependencies COMPLETE | "
        "supervisors_collection=%s | dco_collection=%s",
        supervisors_collection.name if supervisors_collection is not None else "MISSING",
        dco_collection.name if dco_collection is not None else "MISSING",
    )
  
# ============================================================
# ROUTER
# ============================================================

router = APIRouter(prefix="/api", tags=["Supervisor Dashboard"])


# ============================================================
# PRIVATE HELPERS
# ============================================================

def _try_objectid(value: str) -> Optional[ObjectId]:
    """Convert *value* to ObjectId, or return None if invalid."""
    try:
        return ObjectId(value)
    except (InvalidId, Exception):
        return None


def _assignment_filter(value: str) -> dict:
    """Query canonical assignment_id first, with Mongo _id legacy fallback."""
    text = str(value or "")
    oid = _try_objectid(text)
    clauses = [{"assignment_id": text}, {"_id": text}]
    if oid is not None:
        clauses.append({"_id": oid})
    return {"$or": clauses}


async def _resolve_supervisor(supervisor_id: str) -> dict:
    """
    Fetch a supervisor document by supervisor_id, user_id, or _id.
    Raises 404 if not found.
    """
    doc = await supervisors_collection.find_one(
        {"$or": [{"supervisor_id": supervisor_id}, {"user_id": supervisor_id}]}
    )
    if not doc:
        oid = _try_objectid(supervisor_id)
        if oid:
            doc = await supervisors_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return doc


async def _require_supervisor_auth(request: Request, supervisor_id: str) -> dict:
    """
    Validate Bearer/cookie token and confirm the caller is either:
      - the supervisor identified by supervisor_id, OR
      - an admin.
    Returns the serialized supervisor document.
    """
    caller = await get_current_user(request)
    try:
        role = normalize_role(caller.get("role") or caller.get("user_type") or "")
    except (ValueError, TypeError):
        role = ""
    if role not in ("supervisor", "admin"):
        raise HTTPException(status_code=403, detail="Supervisor access required")
    # Supervisors may only access their own data; admins may access any.
    if role == "supervisor":
        caller_id = (
            caller.get("supervisor_id")
            or caller.get("user_id")
            or str(caller.get("_id", ""))
        )
        if caller_id != supervisor_id:
            raise HTTPException(status_code=403, detail="Access denied")
    return caller


def _now() -> datetime:
    return MongoSerializer.now_utc()


# ── Location helpers (re-exported from location_module) ──────────────────────
# The constants and functions below are imported from location_module at the top
# of this file.  They are listed here only for quick-reference documentation;
# do NOT redefine them.
#
#   get_country_name(code)               → display name for an ISO-3166 code
#   get_all_supported_country_codes()    → sorted list of supported codes
#   get_nigerian_states()                → list of all Nigerian states + FCT
#   get_nigerian_lgas(state)             → list of LGAs for a Nigerian state
#   validate_country_code(code)          → bool
#   validate_region(code, region)        → bool
#   validate_subregion(code, reg, sub)   → bool
#   get_regions_payload(code)            → {"country", "region_label", "regions"}
#   get_subregions_payload(code, region) → SubregionLookupResult
#   build_venue_location_filter(...)     → MongoDB filter dict


# ============================================================
# §1  PROFILE & PHOTO
# ============================================================

# ── Pydantic models ──────────────────────────────────────────

class SupervisorProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone:     Optional[str] = None
    languages: Optional[str] = None

    class Config:
        extra = "allow"


# ── Routes ───────────────────────────────────────────────────

@router.get("/supervisor/{supervisor_id}/profile")
async def get_supervisor_profile(supervisor_id: str, request: Request):
    """Return the supervisor's full profile document."""
    await _require_supervisor_auth(request, supervisor_id)
    doc = await _resolve_supervisor(supervisor_id)

    # Enrich with live stats: DCO count, approval counts
    dco_count = await dco_collection.count_documents({"supervisor_id": supervisor_id})

    total_submissions = sum(
        await col.count_documents({"supervisor_id": supervisor_id})
        for col in (stat_submissions_collection, player_stats_collection) if col is not None
    )
    total_approvals = sum(
        await col.count_documents({"supervisor_id": supervisor_id, "status": "approved"})
        for col in (stat_submissions_collection, player_stats_collection) if col is not None
    )

    profile = MongoSerializer.serialize_document(doc)
    profile.setdefault("name",  doc.get("name") or doc.get("full_name") or "")
    profile.setdefault("email", doc.get("email", ""))
    profile["dcosCount"]              = dco_count
    profile["totalMatchesSupervised"] = total_submissions
    profile["totalApprovals"]         = total_approvals

    return JSONResponse(content=profile)


@router.patch("/supervisor/{supervisor_id}/profile")
async def update_supervisor_profile(
    supervisor_id: str,
    request: Request,
    body: SupervisorProfileUpdate,
):
    """Update editable profile fields (name, phone, languages)."""
    await _require_supervisor_auth(request, supervisor_id)
    doc = await _resolve_supervisor(supervisor_id)

    update_fields: dict = {}
    payload = body.model_dump(exclude_none=True)

    if "full_name" in payload and payload["full_name"]:
        update_fields["name"]      = payload["full_name"].strip()
        update_fields["full_name"] = payload["full_name"].strip()
    if "phone" in payload:
        update_fields["phone"] = payload["phone"].strip()
    if "languages" in payload:
        update_fields["languages"] = payload["languages"].strip()

    # Allow any additional fields sent by the client
    for k, v in payload.items():
        if k not in ("full_name", "phone", "languages"):
            update_fields[k] = v

    if not update_fields:
        return JSONResponse(content={"message": "Nothing to update"})

    update_fields["updated_at"] = _now()

    await supervisors_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": update_fields},
    )

    updated = await supervisors_collection.find_one({"_id": doc["_id"]})
    return JSONResponse(content=MongoSerializer.serialize_document(updated))


@router.post("/supervisor/{supervisor_id}/photo")
async def upload_supervisor_photo(
    supervisor_id: str,
    request: Request,
    photo: UploadFile = File(...),
):
    """Upload and replace the supervisor's profile photo (Cloudinary)."""
    await _require_supervisor_auth(request, supervisor_id)
    doc = await _resolve_supervisor(supervisor_id)

    if not upload_to_cloudinary:
        raise HTTPException(status_code=503, detail="File upload service unavailable")

    contents = await photo.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    if photo.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        result = await upload_to_cloudinary(
            contents,
            folder="supervisor_photos",
            public_id=f"supervisor_{supervisor_id}",
            resource_type="image",
        )
        photo_url = result.get("secure_url") or result.get("url", "")
    except Exception as exc:
        logger.error(f"Cloudinary upload error for supervisor {supervisor_id}: {exc}")
        raise HTTPException(status_code=500, detail="Photo upload failed")

    await supervisors_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"photo": photo_url, "profileImage": photo_url, "updated_at": _now()}},
    )

    return JSONResponse(content={"photo_url": photo_url, "profileImage": photo_url})


# ============================================================
# §2  WITHDRAWAL ACCOUNT
# ============================================================

class WithdrawalAccountUpdate(BaseModel):
    bank_name:      Optional[str] = None
    account_number: Optional[str] = None
    account_name:   Optional[str] = None


@router.get("/supervisor/{supervisor_id}/withdrawal-account")
async def get_supervisor_withdrawal_account(supervisor_id: str, request: Request):
    """Return the supervisor's saved withdrawal/bank details."""
    await _require_supervisor_auth(request, supervisor_id)
    doc = await _resolve_supervisor(supervisor_id)

    withdrawal = doc.get("withdrawal_account") or {}
    return JSONResponse(content={
        "bank_name":      withdrawal.get("bank_name", ""),
        "account_number": withdrawal.get("account_number", ""),
        "account_name":   withdrawal.get("account_name", doc.get("name", "")),
    })


@router.patch("/supervisor/{supervisor_id}/withdrawal-account")
async def update_supervisor_withdrawal_account(
    supervisor_id: str,
    request: Request,
    body: WithdrawalAccountUpdate,
):
    """Save or update the supervisor's bank withdrawal account details."""
    await _require_supervisor_auth(request, supervisor_id)
    doc = await _resolve_supervisor(supervisor_id)

    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Merge into the nested withdrawal_account sub-document
    existing = doc.get("withdrawal_account") or {}
    existing.update(payload)
    existing["updated_at"] = _now().isoformat()

    await supervisors_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"withdrawal_account": existing, "updated_at": _now()}},
    )

    return JSONResponse(content={"message": "Withdrawal account updated", **existing})


# ============================================================
# §3  DCO MANAGEMENT
# ============================================================

class AddDCORequest(BaseModel):
    email: str


@router.get("/supervisor/{supervisor_id}/dcos")
async def get_supervisor_dcos(supervisor_id: str, request: Request):
    """
    Return all DCOs assigned to this supervisor.

    DCO documents carry a ``supervisor_id`` field set when they are added.
    """
    await _require_supervisor_auth(request, supervisor_id)

    cursor = dco_collection.find({"supervisor_id": supervisor_id})
    dcos: List[dict] = []
    async for dco in cursor:
        serialized = MongoSerializer.serialize_document(dco)
        dco_id = serialized.get("dco_id") or serialized.get("user_id") or str(dco["_id"])

        # Resolve online status from liveness_sessions
        live_session = await liveness_sessions_collection.find_one(
            {"user_id": dco_id, "is_active": True}
        )
        serialized["is_online"] = bool(live_session)
        serialized["status"]    = "online" if live_session else "offline"
        dcos.append(serialized)

    return JSONResponse(content=dcos)


# NOTE: /dcos/add (fixed path) MUST be registered before /dcos/{dco_id}/remove
@router.post("/supervisor/{supervisor_id}/dcos/add")
async def add_dco_to_supervisor(
    supervisor_id: str,
    request: Request,
    body: AddDCORequest,
):
    """
    Assign a DCO (identified by email) to this supervisor's team.
    Maximum 11 DCOs per supervisor enforced server-side.
    """
    await _require_supervisor_auth(request, supervisor_id)

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="DCO email is required")

    # Enforce 11-DCO limit
    current_count = await dco_collection.count_documents({"supervisor_id": supervisor_id})
    if current_count >= 11:
        raise HTTPException(status_code=400, detail="Maximum of 11 DCOs allowed per supervisor")

    # Find the DCO by email
    dco_doc = await dco_collection.find_one(
        {"$or": [{"email": email}, {"email": body.email.strip()}]}
    )
    if not dco_doc:
        raise HTTPException(status_code=404, detail=f"No DCO account found for email: {email}")

    # Check the DCO isn't already assigned to another supervisor
    existing_sup = dco_doc.get("supervisor_id")
    if existing_sup and existing_sup != supervisor_id:
        raise HTTPException(
            status_code=409,
            detail="This DCO is already assigned to another supervisor",
        )

    if existing_sup == supervisor_id:
        # Already in this team — return current doc
        return JSONResponse(content=MongoSerializer.serialize_document(dco_doc))

    # Assign
    await dco_collection.update_one(
        {"_id": dco_doc["_id"]},
        {"$set": {"supervisor_id": supervisor_id, "updated_at": _now()}},
    )

    # Notify the DCO
    dco_id = dco_doc.get("dco_id") or dco_doc.get("user_id") or str(dco_doc["_id"])
    sup_doc = await _resolve_supervisor(supervisor_id)
    sup_name = sup_doc.get("name") or sup_doc.get("full_name") or "Your supervisor"

    try:
        await notifications_collection.insert_one({
            "user_id":    dco_id,
            "user_type":  "dco",
            "title":      "Added to Supervisor Team",
            "message":    f"You have been added to {sup_name}'s supervisor team.",
            "type":       "team_assignment",
            "read":       False,
            "created_at": _now(),
        })
    except Exception as exc:
        logger.warning(f"Failed to notify DCO {dco_id} on team add: {exc}")

    updated = await dco_collection.find_one({"_id": dco_doc["_id"]})
    return JSONResponse(content=MongoSerializer.serialize_document(updated))


@router.delete("/supervisor/{supervisor_id}/dcos/{dco_id}/remove")
async def remove_dco_from_supervisor(
    supervisor_id: str,
    dco_id: str,
    request: Request,
):
    """Remove a DCO from this supervisor's team."""
    await _require_supervisor_auth(request, supervisor_id)

    # Find DCO document
    dco_doc = await dco_collection.find_one(
        {"$or": [{"dco_id": dco_id}, {"user_id": dco_id}]}
    )
    if not dco_doc:
        oid = _try_objectid(dco_id)
        if oid:
            dco_doc = await dco_collection.find_one({"_id": oid})

    if not dco_doc:
        raise HTTPException(status_code=404, detail="DCO not found")

    if dco_doc.get("supervisor_id") != supervisor_id:
        raise HTTPException(
            status_code=403, detail="This DCO is not in your team"
        )

    await dco_collection.update_one(
        {"_id": dco_doc["_id"]},
        {"$unset": {"supervisor_id": ""}, "$set": {"updated_at": _now()}},
    )

    dco_uid = dco_doc.get("dco_id") or dco_doc.get("user_id") or str(dco_doc["_id"])
    sup_doc  = await _resolve_supervisor(supervisor_id)
    sup_name = sup_doc.get("name") or sup_doc.get("full_name") or "Your supervisor"

    try:
        await notifications_collection.insert_one({
            "user_id":    dco_uid,
            "user_type":  "dco",
            "title":      "Removed from Supervisor Team",
            "message":    f"You have been removed from {sup_name}'s team.",
            "type":       "team_removal",
            "read":       False,
            "created_at": _now(),
        })
    except Exception as exc:
        logger.warning(f"Failed to notify DCO {dco_uid} on team removal: {exc}")

    return JSONResponse(content={"message": "DCO removed from your team"})



# ============================================================
# CANONICAL STATS-SUBMISSION BRIDGE
# ============================================================

async def _submission_collection_rows(query: dict, *, limit: int = 200, sort_field: str = "submitted_at") -> List[dict]:
    """Read canonical stat_submissions first, then legacy player_stats rows."""
    rows: List[dict] = []
    seen: set[str] = set()

    async def consume(col):
        if col is None:
            return
        try:
            cursor = col.find(query, sort=[(sort_field, -1)]).limit(limit)
            async for raw in cursor:
                sid = str(raw.get("_id") or raw.get("submission_id") or raw.get("id") or "")
                if sid and sid in seen:
                    continue
                if sid:
                    seen.add(sid)
                rows.append(raw)
        except Exception as exc:
            if logger:
                logger.warning("Submission bridge read failed: %s", exc)

    await consume(stat_submissions_collection)
    await consume(player_stats_collection)
    rows.sort(key=lambda x: x.get(sort_field) or x.get("updated_at") or x.get("created_at") or "", reverse=True)
    return rows[:limit]


async def _normalise_tracker_submission(raw: dict) -> dict:
    """Project v2 tracker rows into the flat shape used by supervisor screens."""
    d = MongoSerializer.serialize_document(raw) if MongoSerializer else dict(raw)
    match = raw.get("match") if isinstance(raw.get("match"), dict) else {}

    def first(*keys, default=""):
        for source in (d, match):
            if not isinstance(source, dict):
                continue
            for key in keys:
                value = source.get(key)
                if value not in (None, ""):
                    return value
        return default

    aliases = {
        "homeTeam": ("homeTeam", "home_team", "home_team_name", "homeTeamName"),
        "awayTeam": ("awayTeam", "away_team", "away_team_name", "awayTeamName"),
        "matchDate": ("matchDate", "match_date", "date"),
        "matchTime": ("matchTime", "match_time", "time"),
        "venue": ("venue", "venue_name", "stadium"),
        "venueAddress": ("venueAddress", "venue_address", "address"),
        "venueCountry": ("venueCountry", "venue_country", "country"),
        "venueState": ("venueState", "venue_state", "state"),
        "venueLGA": ("venueLGA", "venue_lga", "lga"),
        "competition": ("competition", "competition_name"),
        "matchType": ("matchType", "match_type"),
        "playerLevel": ("playerLevel", "player_level", "category"),
        "dcoName": ("dcoName", "dco_name", "scout_name"),
        "dco_id": ("dco_id", "scout_id"),
        "supervisor_id": ("supervisor_id",),
        "match_id": ("match_id",),
    }
    for out, keys in aliases.items():
        value = first(*keys, default=None)
        if value not in (None, ""):
            d[out] = value

    if stat_submission_players_collection is not None:
        try:
            sid = raw.get("_id")
            if sid is not None:
                children = await stat_submission_players_collection.find(
                    {"submission_id": sid}, sort=[("_id", 1)]
                ).limit(3).to_list(length=3)
                players = [MongoSerializer.serialize_document(x) for x in children]
                if players:
                    d["players"] = players
                    fp = players[0]
                    for out, keys in {
                        "playerName": ("player_name", "name"),
                        "player_id": ("player_id", "playerId"),
                        "position": ("position",),
                        "club": ("club", "club_name"),
                        "playerLevel": ("player_level", "playerLevel", "category"),
                        "jerseyNumber": ("jersey_number", "jerseyNumber"),
                    }.items():
                        if not d.get(out):
                            for key in keys:
                                if fp.get(key) not in (None, ""):
                                    d[out] = fp[key]
                                    break
                    if not d.get("stats") and isinstance(fp.get("stats"), dict):
                        d["stats"] = fp["stats"]
        except Exception as exc:
            if logger:
                logger.warning("Submission player enrichment failed: %s", exc)

    if not d.get("dcoName") and d.get("dco_id") and dco_collection is not None:
        try:
            dco = await dco_collection.find_one({
                "$or": [{"dco_id": d["dco_id"]}, {"user_id": d["dco_id"]}, {"data_scout_id": d["dco_id"]}]
            })
            if dco:
                d["dcoName"] = dco.get("full_name") or dco.get("name") or dco.get("email") or ""
        except Exception:
            pass

    d["_canonicalSubmission"] = True
    return d


async def _find_submission_record(submission_id: str):
    oid = _try_objectid(submission_id)
    queries = []
    if oid:
        queries.append({"_id": oid})
    queries.extend([{"submission_id": submission_id}, {"id": submission_id}])
    for col in (stat_submissions_collection, player_stats_collection):
        if col is None:
            continue
        for q in queries:
            try:
                doc = await col.find_one(q)
            except Exception:
                doc = None
            if doc:
                return col, doc
    return None, None


# ============================================================
# SUPERVISOR MATCHDAY CONTROL — API CONTRACT
# ============================================================

def _supervisor_id_from_user(user: dict) -> str:
    return str(user.get("supervisor_id") or user.get("user_id") or user.get("_id") or "")

async def _require_current_supervisor(request: Request) -> str:
    caller=await get_current_user(request)
    try:
        caller_role = normalize_role(caller.get("role") or caller.get("user_type") or "")
    except (ValueError, TypeError):
        caller_role = ""
    if caller_role not in {"supervisor", "admin"}:
        raise HTTPException(status_code=403,detail="Supervisor access required")
    sid=_supervisor_id_from_user(caller)
    if not sid:
        raise HTTPException(status_code=401,detail="Supervisor identifier missing")
    return sid

def _match_filter(match_id: str) -> dict:
    clauses=[{"match_id":str(match_id)},{"id":str(match_id)}]
    oid=_try_objectid(str(match_id))
    if oid: clauses.append({"_id":oid})
    return {"$or":clauses}

async def _resolve_supervisor_match(supervisor_id: str, match_id: str) -> dict:
    m=await matches_collection.find_one(_match_filter(match_id))
    if not m: raise HTTPException(status_code=404,detail="Match not found")
    supers=m.get("supervisor_ids") or m.get("supervisorIds") or []
    supers=[str(x.get("supervisor_id") or x.get("id") or x.get("_id") or x) if isinstance(x,dict) else str(x) for x in supers]
    if supervisor_id not in supers: raise HTTPException(status_code=403,detail="Match is not assigned to this supervisor")
    return m

def _match_clock_value(m: dict) -> Optional[datetime]:
    date=m.get("match_date") or m.get("date") or ""
    time=m.get("match_time") or m.get("time") or "00:00"
    try: return datetime.fromisoformat(f"{date}T{time}:00" if len(str(time))==5 else f"{date}T{time}")
    except Exception: return None

async def _dco_recruitment_conflict(dco_id: str, match: dict) -> Optional[str]:
    target=_match_clock_value(match)
    if target is None: return "Match date/time is invalid"
    async for rec in supervisor_recruitments_collection.find({"dco_id":str(dco_id),"status":"active"}):
        other=await matches_collection.find_one(_match_filter(str(rec.get("match_id") or "")))
        if not other: continue
        ot=_match_clock_value(other)
        if ot and abs((target-ot).total_seconds())<120*60:
            return "DCO unavailable because of an overlapping match (<2 hours)"
    return None

@router.get("/supervisor/matches")
async def supervisor_matchday_matches(request: Request):
    sid=await _require_current_supervisor(request)
    docs=await matches_collection.find({"$or":[{"supervisor_ids":sid},{"supervisorIds":sid}]}).sort([("match_date",1),("match_time",1)]).limit(250).to_list(length=250)
    result=[]
    for m in docs:
        s=MongoSerializer.serialize_document(m)
        supers=m.get("supervisor_ids") or m.get("supervisorIds") or []
        s.update({
            "id":str(m.get("match_id") or m.get("id") or m.get("_id")),
            "match_id":str(m.get("match_id") or m.get("id") or m.get("_id")),
            "home":m.get("home") or m.get("home_team") or m.get("home_team_name") or "",
            "away":m.get("away") or m.get("away_team") or m.get("away_team_name") or "",
            "date":m.get("date") or m.get("match_date") or "",
            "time":m.get("time") or m.get("match_time") or "",
            "venue":m.get("venue") or m.get("venue_name") or "",
            "country":m.get("country") or m.get("country_name") or "",
            "countryCode":m.get("country_code") or "",
            "state":m.get("state") or m.get("region") or "",
            "city":m.get("city") or m.get("venue_city") or "",
            "supervisorIds":[str(x.get("supervisor_id") or x.get("id") or x.get("_id") or x) if isinstance(x,dict) else str(x) for x in supers]
        })
        result.append(s)
    return JSONResponse({"matches":result,"data":result,"total":len(result)})

@router.get("/supervisor/available-dcos")
async def supervisor_available_dcos(request: Request, country: str="", state: str="", city: str=""):
    sid=await _require_current_supervisor(request)
    dcos=await dco_collection.find({"is_active":{"$ne":False}}).limit(500).to_list(length=500)
    result=[]
    for d in dcos:
        did=str(d.get("dco_id") or d.get("user_id") or d.get("_id"))
        if not did: continue
        owner=str(d.get("supervisor_id") or "")
        if owner and owner!=sid: continue
        vals=[str(d.get("country") or d.get("country_name") or ""),str(d.get("state") or d.get("region") or ""),str(d.get("city") or d.get("venue_city") or "")]
        if country and country.casefold() not in vals[0].casefold(): continue
        if state and state.casefold() not in vals[1].casefold(): continue
        if city and city.casefold() not in vals[2].casefold(): continue
        recs=await supervisor_recruitments_collection.find({"dco_id":did,"status":"active"}).to_list(length=100)
        active_ids=[str(r.get("match_id")) for r in recs if r.get("match_id")]
        result.append({
            **MongoSerializer.serialize_document(d),
            "id":did,"dco_id":did,
            "name":d.get("name") or d.get("full_name") or d.get("email") or "Unnamed DCO",
            "available":True,"activeMatchIds":active_ids,"active_match_ids":active_ids
        })
    return JSONResponse({"dcos":result,"users":result,"data":result,"total":len(result)})

class SupervisorRecruitDCOBody(BaseModel):
    match_id: str
    dco_id: str
    supervisor_id: Optional[str]=None
    standby: bool=False

@router.post("/supervisor/dcos/recruit")
async def supervisor_recruit_dco(request: Request, body: SupervisorRecruitDCOBody):
    sid=await _require_current_supervisor(request)
    if body.supervisor_id and str(body.supervisor_id)!=sid:
        raise HTTPException(status_code=403,detail="Supervisor mismatch")
    match=await _resolve_supervisor_match(sid,body.match_id)
    did=str(body.dco_id)
    dco=await dco_collection.find_one({"$or":[{"dco_id":did},{"user_id":did},{"_id":_try_objectid(did)}]})
    if not dco: raise HTTPException(status_code=404,detail="DCO not found")
    existing=await supervisor_recruitments_collection.find_one({"match_id":str(body.match_id),"dco_id":did,"status":"active"})
    if existing: return JSONResponse({"success":True,"recruitment":MongoSerializer.serialize_document(existing),"already_recruited":True})
    active=await supervisor_recruitments_collection.count_documents({"match_id":str(body.match_id),"status":"active","standby":{"$ne":True}})
    if not body.standby and active>=8: raise HTTPException(status_code=409,detail="Maximum 8 active DCOs reached for this match")
    conflict=await _dco_recruitment_conflict(did,match)
    if conflict: raise HTTPException(status_code=409,detail=conflict)
    now=_now()
    rec={"recruitment_id":f"REC-{secrets.token_hex(6).upper()}","match_id":str(body.match_id),"dco_id":did,"supervisor_id":sid,"standby":bool(body.standby),"status":"active","created_at":now,"updated_at":now}
    await supervisor_recruitments_collection.insert_one(rec)
    return JSONResponse({"success":True,"recruitment":MongoSerializer.serialize_document(rec)})

@router.get("/supervisor/matches/{match_id}/players")
async def supervisor_match_players(match_id: str, request: Request):
    sid=await _require_current_supervisor(request); match=await _resolve_supervisor_match(sid,match_id)
    players=list(match.get("players") or []) if isinstance(match.get("players"),list) else []
    seen={str(p.get("player_id") or p.get("id") or p.get("_id")) for p in players if isinstance(p,dict)}
    if stats_requests_collection is not None:
        async for req in stats_requests_collection.find({"match_id":str(match_id)}).limit(300):
            pid=str(req.get("player_id") or "")
            if not pid or pid in seen: continue
            p=await players_collection.find_one({"$or":[{"player_id":pid},{"user_id":pid},{"_id":_try_objectid(pid)}]}) if players_collection is not None else None
            src=p or req
            players.append({"id":pid,"player_id":pid,"name":src.get("full_name") or src.get("name") or req.get("player_name") or "Player","club":src.get("club") or src.get("club_name") or req.get("club_name") or req.get("club") or "","position":src.get("position") or src.get("preferredPosition") or req.get("position") or ""}); seen.add(pid)
    async for a in dco_assignments_collection.find({"match_id":str(match_id)}).limit(300):
        pid=str(a.get("player_id") or "")
        if not pid or pid in seen: continue
        players.append({"id":pid,"player_id":pid,"name":a.get("player_name") or "Player","club":a.get("club") or a.get("club_name") or "","position":a.get("position") or ""}); seen.add(pid)
    return JSONResponse({"players":players,"data":players,"total":len(players)})

@router.get("/supervisor/matches/{match_id}/player-dco-assignments")
async def supervisor_match_player_assignments(match_id: str, request: Request):
    sid=await _require_current_supervisor(request); await _resolve_supervisor_match(sid,match_id)
    rows=await dco_assignments_collection.find({"match_id":str(match_id),"assigned_supervisor_id":sid}).sort("created_at",-1).limit(500).to_list(length=500)
    result=[]
    for r in rows:
        s=MongoSerializer.serialize_document(r)
        result.append({**s,"id":str(r.get("assignment_id") or r.get("_id")),"matchId":str(r.get("match_id") or ""),"dcoId":str(r.get("assigned_dco_id") or r.get("assignee_id") or r.get("dco_id") or ""),"playerId":str(r.get("player_id") or ""),"status":r.get("status") or "assigned"})
    return JSONResponse({"assignments":result,"data":result,"total":len(result)})

class SupervisorAssignPlayersBody(BaseModel):
    match_id: str
    supervisor_id: Optional[str]=None
    dco_id: str
    player_ids: List[str]=[]

@router.post("/supervisor/matches/{match_id}/assign-dco")
async def supervisor_assign_dco_players(match_id: str, request: Request, body: SupervisorAssignPlayersBody):
    sid=await _require_current_supervisor(request)
    if str(body.match_id)!=str(match_id): raise HTTPException(status_code=400,detail="match_id mismatch")
    match=await _resolve_supervisor_match(sid,match_id)
    pids=list(dict.fromkeys(str(x) for x in body.player_ids if x not in (None,"")))
    if not pids: raise HTTPException(status_code=400,detail="At least one player is required")
    if len(pids)>3: raise HTTPException(status_code=400,detail="Maximum 3 players per DCO per match")
    rec=await supervisor_recruitments_collection.find_one({"match_id":str(match_id),"dco_id":str(body.dco_id),"status":"active","standby":{"$ne":True}})
    if not rec: raise HTTPException(status_code=409,detail="DCO must be actively recruited for this match first")
    existing=await dco_assignments_collection.find({"match_id":str(match_id),"assigned_dco_id":str(body.dco_id)}).to_list(length=100)
    existing_p={str(x.get("player_id")) for x in existing if x.get("player_id")}
    already_elsewhere=await dco_assignments_collection.find({
        "match_id":str(match_id),
        "player_id":{"$in":pids},
        "assigned_dco_id":{"$ne":str(body.dco_id)},
        "status":{"$nin":["declined","rejected","cancelled","deleted"]},
    }).to_list(length=100)
    occupied={str(x.get("player_id")) for x in already_elsewhere if x.get("player_id")}
    if occupied:
        raise HTTPException(status_code=409,detail="One or more selected players are already assigned to another DCO for this match")
    new_p=[p for p in pids if p not in existing_p]
    if len(existing)+len(new_p)>3: raise HTTPException(status_code=409,detail="This DCO already has the maximum 3 players for this match")
    if any(p in existing_p for p in pids): raise HTTPException(status_code=409,detail="One or more selected players are already assigned to this DCO")
    now=_now(); created=[]
    for pid in pids:
        player=await players_collection.find_one({"$or":[{"player_id":pid},{"user_id":pid},{"_id":_try_objectid(pid)}]}) if players_collection is not None else None
        doc={"assignment_id":f"ASGN-{secrets.token_hex(6).upper()}","match_id":str(match_id),"assigned_dco_id":str(body.dco_id),"assigned_supervisor_id":sid,"assignee_id":str(body.dco_id),"role":"dco","player_id":pid,
             "player_name":(player or {}).get("full_name") or (player or {}).get("name") or "","position":(player or {}).get("position") or (player or {}).get("preferredPosition") or "","club":(player or {}).get("club") or (player or {}).get("club_name") or "",
             "home_team":match.get("home_team") or match.get("home") or "","away_team":match.get("away_team") or match.get("away") or "","match_date":match.get("match_date") or match.get("date") or "","match_time":match.get("match_time") or match.get("time") or "","venue":match.get("venue") or "",
             "status":"assigned","created_at":now,"updated_at":now}
        await dco_assignments_collection.insert_one(doc); created.append(MongoSerializer.serialize_document(doc))
    return JSONResponse({"success":True,"assignments":created,"data":created})

# ============================================================
# §4  LIVE MONITORING
# ============================================================

@router.get("/supervisor/{supervisor_id}/live-monitoring")
async def get_live_monitoring(supervisor_id: str, request: Request):
    await _require_supervisor_auth(request, supervisor_id)
    dco_docs = await dco_collection.find({"supervisor_id": supervisor_id}).to_list(length=500)
    dco_ids = [str(d.get("dco_id") or d.get("user_id") or d.get("_id")) for d in dco_docs]
    if dco_assignments_collection is not None:
        async for a in dco_assignments_collection.find({
            "$or": [{"assigned_supervisor_id": supervisor_id}, {"supervisor_id": supervisor_id}]
        }).limit(500):
            did = str(a.get("assigned_dco_id") or a.get("assignee_id") or a.get("dco_id") or "")
            if did and did not in dco_ids:
                dco_ids.append(did)
    if not dco_ids:
        return JSONResponse(content=[])

    entries=[]
    for did in dco_ids:
        session=await liveness_sessions_collection.find_one({"user_id":did,"is_active":True},sort=[("updated_at",-1)])
        rows=await _submission_collection_rows({"dco_id":did,"status":{"$in":["in_progress","submitted","pending_approval","approved"]}},limit=20)
        sub=rows[0] if rows else None
        if not session and not sub:
            continue
        dco=await dco_collection.find_one({"$or":[{"dco_id":did},{"user_id":did}]}) or {}
        entry={
            "dcoId":did,
            "dcoName":dco.get("full_name") or dco.get("name") or dco.get("email") or "DCO",
            "isOnline":bool(session),
            "status":"online" if session else "offline",
            "sessionId":str(session.get("_id","")) if session else "",
            "lastSeen":MongoSerializer.serialize_value(
                (session or {}).get("updated_at") or (session or {}).get("created_at") or
                (sub or {}).get("submitted_at") or (sub or {}).get("updated_at")
            )
        }
        if sub:
            x=await _normalise_tracker_submission(sub)
            entry.update({
                "homeTeam":x.get("homeTeam",""),
                "awayTeam":x.get("awayTeam",""),
                "matchTitle":f"{x.get('homeTeam','')} vs {x.get('awayTeam','')}".strip(" vs ") or "Match activity",
                "venue":x.get("venue",""),
                "half":x.get("half") or (x.get("match") or {}).get("period"),
                "statsCount":int(sub.get("event_count") or 0),
                "submissionId":str(sub.get("_id") or sub.get("submission_id") or ""),
                "submissionStatus":sub.get("status",""),
                "matchId":x.get("match_id") or (x.get("match") or {}).get("match_id") or ""
            })
        entries.append(entry)
    return JSONResponse(content=entries)

# ============================================================
# §5  ASSIGNMENTS
# ============================================================

class AssignmentCreate(BaseModel):
    dcoId:         str
    homeTeam:      str
    awayTeam:      str
    matchDate:     str
    matchTime:     Optional[str] = ""
    venue:         Optional[str] = ""
    venueCountry:  Optional[str] = ""   # ISO-3166-1 alpha-2 code or display name
    venueState:    Optional[str] = ""   # region / state name
    venueLGA:      Optional[str] = ""   # subregion / LGA name
    venueCity:     Optional[str] = ""   # explicit city / district
    trackingScope: Optional[str] = "Player Stats Only"
    notes:         Optional[str] = ""


class AssignmentUpdate(BaseModel):
    dcoId:         Optional[str] = None
    homeTeam:      Optional[str] = None
    awayTeam:      Optional[str] = None
    matchDate:     Optional[str] = None
    matchTime:     Optional[str] = None
    venue:         Optional[str] = None
    venueCountry:  Optional[str] = None
    venueState:    Optional[str] = None
    venueLGA:      Optional[str] = None
    venueCity:     Optional[str] = None
    trackingScope: Optional[str] = None
    notes:         Optional[str] = None
    status:        Optional[str] = None

    class Config:
        extra = "allow"


@router.get("/supervisor/{supervisor_id}/assignments")
async def get_supervisor_assignments(supervisor_id: str, request: Request):
    """
    Return all assignments visible to this supervisor.

    Two sources merged and deduplicated:
      1. supervisor_assignments_collection — self-created assignments.
      2. dco_assignments_collection — admin-created assignments that
         reference this supervisor via assigned_supervisor_id.

    Every assignment is enriched with:
      - Live DCO name from dco_collection
      - Live player data (name, position, club, level) from players_collection
        using player_id stored on the assignment / stats-request snapshot
      - venueCountryName resolved via get_country_name() from location_module
    """
    await _require_supervisor_auth(request, supervisor_id)

    seen_ids: set = set()
    assignments: List[dict] = []

    # ── Local helpers ────────────────────────────────────────────────────

    async def _enrich_dco_name(serialized: dict, raw_doc: dict) -> dict:
        """Backfill dcoName from dco_collection when not already set."""
        dco_id = (
            raw_doc.get("dcoId")
            or raw_doc.get("dco_id")
            or raw_doc.get("assigned_dco_id", "")
        )
        if dco_id and not serialized.get("dcoName"):
            dco_doc = await dco_collection.find_one(
                {"$or": [{"dco_id": dco_id}, {"user_id": dco_id}]}
            )
            if dco_doc:
                serialized["dcoName"] = (
                    dco_doc.get("full_name")   # primary: DCO docs never store "name"
                    or dco_doc.get("name")
                    or dco_doc.get("email", "")
                )
        return serialized

    async def _enrich_player(serialized: dict) -> dict:
        """
        If the assignment carries a player_id, fetch the player document
        and backfill playerName / position / club / playerLevel when those
        fields are missing or empty in the snapshot.
        """
        pid = serialized.get("player_id") or serialized.get("playerId") or ""
        if not pid or players_collection is None:
            return serialized
        try:
            p_doc = await players_collection.find_one(
                {"$or": [{"player_id": pid}, {"user_id": pid}]}
            )
        except Exception:
            return serialized
        if not p_doc:
            return serialized
        live_name = " ".join(filter(None, [
            # camelCase = DCO-registered player; snake_case = self-registered (auth.py)
            p_doc.get("firstName", "") or p_doc.get("first_name", ""),
            p_doc.get("middleName", "") or p_doc.get("middle_name", ""),
            p_doc.get("lastName", "") or p_doc.get("last_name", ""),
        ])).strip()
        if not live_name:
            live_name = p_doc.get("full_name", "")
        if not serialized.get("playerName") and live_name:
            serialized["playerName"] = live_name
        if not serialized.get("position"):
            serialized["position"] = (
                p_doc.get("position") or
                p_doc.get("preferredPosition") or
                p_doc.get("preferred_position") or ""   # snake_case: auth.py self-reg
            )
        if not serialized.get("club"):
            serialized["club"] = p_doc.get("club") or p_doc.get("current_club") or ""
        if not serialized.get("playerLevel"):
            serialized["playerLevel"] = (
                p_doc.get("category") or p_doc.get("player_level") or ""
            )
        if not serialized.get("jerseyNumber"):
            serialized["jerseyNumber"] = str(p_doc.get("jerseyNumber") or p_doc.get("jersey_number") or "")
        return serialized

    def _enrich_country_name(serialized: dict) -> dict:
        """
        Backfill venueCountryName from location_module.get_country_name() when
        venueCountry holds an ISO-3166-1 alpha-2 code.  This keeps all country
        name resolution in the location module — no inline mapping here.
        """
        code = serialized.get("venueCountry", "")
        if code and len(code) <= 3:
            display = get_country_name(code)
            if display:
                serialized["venueCountryName"] = display
        return serialized

    # ── Source 1: supervisor-created assignments ──────────────────────────
    async for a in supervisor_assignments_collection.find(
        {"supervisor_id": supervisor_id},
        sort=[("created_at", -1)],
    ):
        doc_id = str(a["_id"])
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        s = MongoSerializer.serialize_document(a)
        s["_assignmentSource"] = "supervisor"
        # Normalise camelCase ↔ snake_case aliases
        s.setdefault("homeTeam",  a.get("home_team", ""))
        s.setdefault("awayTeam",  a.get("away_team", ""))
        s.setdefault("matchDate", a.get("match_date", ""))
        s.setdefault("matchTime", a.get("match_time") or a.get("matchTime", ""))
        s.setdefault("venue",     a.get("venue", ""))
        s.setdefault("venueAddress", a.get("venue_address") or a.get("venueAddress", ""))
        s.setdefault("contactPhone", a.get("contact_phone") or a.get("contactPhone", ""))
        s.setdefault("notes",     a.get("notes", ""))
        s.setdefault("requestType", a.get("request_type") or a.get("requestType") or "")
        s.setdefault("player_id", a.get("player_id", ""))
        s.setdefault("venueCountry", a.get("venue_country") or a.get("venueCountry", ""))
        s.setdefault("venueState",   a.get("venue_state")   or a.get("venueState", ""))
        s.setdefault("venueLGA",     a.get("venue_lga")     or a.get("venueLGA", ""))
        s = await _enrich_dco_name(s, a)
        s = await _enrich_player(s)
        s = _enrich_country_name(s)
        assignments.append(s)

    # ── Source 2: admin-created assignments referencing this supervisor ───
    if dco_assignments_collection is not None:
        query = {
            "$or": [
                {"assigned_supervisor_id": supervisor_id},
                {"supervisor_id": supervisor_id},
            ]
        }
        async for a in dco_assignments_collection.find(query, sort=[("created_at", -1)]):
            doc_id = str(a["_id"])
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            s = MongoSerializer.serialize_document(a)
            s["_assignmentSource"] = "admin"

            def _snap(*keys: str, default: str = "") -> str:
                """First truthy value across all keys in `a`."""
                for k in keys:
                    v = a.get(k)
                    if v is not None and v != "":
                        return v
                return default

            # ── Normalise all field names ────────────────────────────────
            s["homeTeam"]       = _snap("homeTeam", "home_team")
            s["awayTeam"]       = _snap("awayTeam", "away_team")
            s["matchDate"]      = _snap("matchDate", "match_date")
            s["matchTime"]      = _snap("matchTime", "match_time")
            s["venue"]          = _snap("venue", "stadium", "venue_name")
            s["venueAddress"]   = _snap("venueAddress", "venue_address", "stadium_address")
            s["venueLGA"]       = _snap("venueLGA", "venue_lga", "lga")
            s["venueState"]     = _snap("venueState", "venue_state", "state")
            # venueCountry: resolve display name via location_module (no inline mapping)
            raw_country_code    = _snap("venueCountry", "venue_country")
            s["venueCountry"]   = raw_country_code or get_country_name("NG") or "Nigeria"
            s["playerName"]     = _snap("playerName", "player_name")
            s["position"]       = _snap("position")
            s["club"]           = _snap("club", "club_name")
            s["playerLevel"]    = _snap("playerLevel", "player_level", "category", "matchCategory")
            s["jerseyNumber"]   = _snap("jerseyNumber", "jersey_number")
            s["playerRepresents"] = _snap("playerRepresents", "player_represents")
            s["competition"]    = _snap("competition", "league")
            s["matchType"]      = _snap("matchType", "match_type")
            s["heatmap"]        = a.get("heatmap")
            s["requestType"]    = _snap("requestType", "request_type", "stats_type")
            s["contactPhone"]   = _snap("contactPhone", "contact_phone", "phone")
            s["notes"]          = _snap("notes")
            s["player_id"]      = _snap("player_id")

            s = await _enrich_dco_name(s, a)
            s = await _enrich_player(s)
            s = _enrich_country_name(s)
            assignments.append(s)

    assignments.sort(
        key=lambda x: x.get("created_at") or x.get("createdAt") or "",
        reverse=True,
    )
    return JSONResponse(content=assignments)


# NOTE: /assignments/create (fixed path) MUST be registered BEFORE
#       /assignments/{assignment_id} (parameterised) to prevent "create"
#       from being captured as {assignment_id}.
@router.post("/supervisor/{supervisor_id}/assignments/create")
async def create_supervisor_assignment(
    supervisor_id: str,
    request: Request,
    body: AssignmentCreate,
):
    """
    Create a new match assignment for a DCO in this supervisor's team.

    venueCountry, venueState, and venueLGA are validated against
    location_module when supplied so only supported values are persisted.
    Country defaults to Nigeria (NG) when omitted.
    """
    await _require_supervisor_auth(request, supervisor_id)

    # ── Location validation via location_module ──────────────────────────
    # Resolve venue country: accept either an ISO code ("NG") or a display
    # name ("Nigeria").  Default to Nigeria when the field is blank.
    raw_venue_country = (body.venueCountry or "").strip()
    if raw_venue_country:
        # Try as ISO code first, then fall back to a reverse name lookup
        if validate_country_code(raw_venue_country):
            venue_country_code = raw_venue_country.upper()
        else:
            # Reverse-lookup: find the ISO code whose display name matches
            venue_country_code = next(
                (code for code, name in COUNTRY_NAMES.items()
                 if name.lower() == raw_venue_country.lower()),
                None,
            )
            if not venue_country_code:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported venue country: '{raw_venue_country}'. "
                           "Use an ISO-3166-1 alpha-2 code (e.g. 'NG') or a "
                           "supported country name.",
                )
    else:
        venue_country_code = "NG"   # default to Nigeria

    venue_country_name = get_country_name(venue_country_code) or venue_country_code

    # Validate state/region when supplied
    venue_state = (body.venueState or "").strip()
    if venue_state and not validate_region(venue_country_code, venue_state):
        # Soft validation: warn in logs but do not reject — region lists may
        # be incomplete for some countries.
        logger.warning(
            "[supervisor_dashboard_routes] unrecognised venueState '%s' for "
            "country '%s' — storing as-is",
            venue_state, venue_country_code,
        )

    # Validate LGA/subregion when both state and LGA are supplied
    venue_lga = (body.venueLGA or "").strip()
    venue_city = (body.venueCity or "").strip()
    if venue_state and venue_lga and not validate_subregion(
        venue_country_code, venue_state, venue_lga
    ):
        logger.warning(
            "[supervisor_dashboard_routes] unrecognised venueLGA '%s' for "
            "state '%s' / country '%s' — storing as-is",
            venue_lga, venue_state, venue_country_code,
        )

    # ── DCO ownership check ──────────────────────────────────────────────
    # Validate the DCO belongs to this supervisor
    dco_doc = await dco_collection.find_one(
        {
            "$and": [
                {"$or": [{"dco_id": body.dcoId}, {"user_id": body.dcoId}]},
                {"supervisor_id": supervisor_id},
            ]
        }
    )
    if not dco_doc:
        # Also try _id match
        oid = _try_objectid(body.dcoId)
        if oid:
            dco_doc = await dco_collection.find_one(
                {"_id": oid, "supervisor_id": supervisor_id}
            )
    if not dco_doc:
        raise HTTPException(
            status_code=404,
            detail="DCO not found in your team",
        )

    dco_name = (
        dco_doc.get("name")
        or dco_doc.get("full_name")
        or dco_doc.get("email", "")
    )

    assignment_doc = {
        "supervisor_id":  supervisor_id,
        "dcoId":          body.dcoId,
        "dco_id":         body.dcoId,
        "dcoName":        dco_name,
        "homeTeam":       body.homeTeam.strip(),
        "home_team":      body.homeTeam.strip(),
        "awayTeam":       body.awayTeam.strip(),
        "away_team":      body.awayTeam.strip(),
        "matchDate":      body.matchDate,
        "match_date":     body.matchDate,
        "matchTime":      body.matchTime or "",
        "venue":          body.venue or "",
        # ── Location fields (sourced from location_module) ──────────────
        "venueCountry":   venue_country_code,
        "venue_country":  venue_country_code,
        "venueCountryName": venue_country_name,
        "venueState":     venue_state,
        "venue_state":    venue_state,
        "venueLGA":       venue_lga,
        "venue_lga":      venue_lga,
        "venueCity":      venue_city,
        "venue_city":     venue_city,
        # ────────────────────────────────────────────────────────────────
        "trackingScope":  body.trackingScope or "Player Stats Only",
        "notes":          body.notes or "",
        "status":         "assigned",
        "created_at":     _now(),
        "updated_at":     _now(),
    }

    result = await supervisor_assignments_collection.insert_one(assignment_doc)
    assignment_doc["_id"] = str(result.inserted_id)

    # Notify the DCO
    dco_uid = dco_doc.get("dco_id") or dco_doc.get("user_id") or str(dco_doc["_id"])
    try:
        await notifications_collection.insert_one({
            "user_id":    dco_uid,
            "user_type":  "dco",
            "title":      "New Assignment",
            "message":    (
                f"You have been assigned to collect stats for "
                f"{body.homeTeam.strip()} vs {body.awayTeam.strip()} "
                f"on {body.matchDate}."
            ),
            "type":       "assignment_new",
            "read":       False,
            "created_at": _now(),
        })
    except Exception as exc:
        logger.warning(f"Assignment notification failed for DCO {dco_uid}: {exc}")

    return JSONResponse(
        content=MongoSerializer.serialize_document(assignment_doc),
        status_code=201,
    )


@router.patch("/supervisor/{supervisor_id}/assignments/{assignment_id}")
async def update_supervisor_assignment(
    supervisor_id: str,
    assignment_id: str,
    request: Request,
    body: AssignmentUpdate,
):
    """Update fields on an existing assignment."""
    await _require_supervisor_auth(request, supervisor_id)

    oid = _try_objectid(assignment_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid assignment ID")

    existing = await supervisor_assignments_collection.find_one(
        {"_id": oid, "supervisor_id": supervisor_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Assignment not found")

    payload = body.model_dump(exclude_none=True)
    if not payload:
        return JSONResponse(content={"message": "Nothing to update"})

    # Mirror camelCase → snake_case aliases
    if "homeTeam" in payload:
        payload["home_team"] = payload["homeTeam"]
    if "awayTeam" in payload:
        payload["away_team"] = payload["awayTeam"]
    if "matchDate" in payload:
        payload["match_date"] = payload["matchDate"]
    if "dcoId" in payload:
        payload["dco_id"] = payload["dcoId"]

    # ── Location field normalisation via location_module ──────────────────
    if "venueCountry" in payload:
        raw = payload["venueCountry"].strip()
        if raw:
            if validate_country_code(raw):
                payload["venueCountry"]     = raw.upper()
                payload["venue_country"]    = raw.upper()
                payload["venueCountryName"] = get_country_name(raw.upper()) or raw
            else:
                # Accept display names and store the code + resolved name
                code = next(
                    (c for c, n in COUNTRY_NAMES.items()
                     if n.lower() == raw.lower()),
                    None,
                )
                if code:
                    payload["venueCountry"]     = code
                    payload["venue_country"]    = code
                    payload["venueCountryName"] = get_country_name(code) or raw
                # If unrecognised, store as-is (backwards compatible)
    if "venueState" in payload:
        payload["venue_state"] = payload["venueState"]
    if "venueLGA" in payload:
        payload["venue_lga"] = payload["venueLGA"]
    if "venueCity" in payload:
        payload["venue_city"] = payload["venueCity"]

    payload["updated_at"] = _now()

    await supervisor_assignments_collection.update_one(
        {"_id": oid},
        {"$set": payload},
    )

    updated = await supervisor_assignments_collection.find_one({"_id": oid})
    return JSONResponse(content=MongoSerializer.serialize_document(updated))


@router.delete("/supervisor/{supervisor_id}/assignments/{assignment_id}/delete")
async def delete_supervisor_assignment(
    supervisor_id: str,
    assignment_id: str,
    request: Request,
):
    """Delete an assignment (only if not yet completed)."""
    await _require_supervisor_auth(request, supervisor_id)

    oid = _try_objectid(assignment_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid assignment ID")

    existing = await supervisor_assignments_collection.find_one(
        {"_id": oid, "supervisor_id": supervisor_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if existing.get("status") == "completed":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a completed assignment",
        )

    await supervisor_assignments_collection.delete_one({"_id": oid})
    return JSONResponse(content={"message": "Assignment deleted"})



def _normalise_submission_fields(d: dict) -> dict:
    """
    Ensure every submission dict exposes both camelCase and snake_case
    versions of key fields so the frontend always finds its data regardless
    of how the original record was saved.
    """
    _map = [
        ("homeTeam",     "home_team"),
        ("awayTeam",     "away_team"),
        ("matchDate",    "match_date"),
        ("matchTime",    "match_time"),
        ("playerName",   "player_name"),
        ("clubName",     "club_name"),
        ("dcoName",      "dco_name"),
        ("geoStatus",    "geo_status"),
        # ── extended fields ──────────────────────────────────────────────
        ("position",     "position"),
        ("club",         "club"),
        ("playerLevel",  "player_level"),
        ("playerLevel",  "category"),        # second alias for playerLevel
        ("competition",  "competition"),
        ("matchType",    "match_type"),
        ("venue",        "venue"),
        ("venueAddress", "venue_address"),
        ("venueCountry", "venue_country"),
        ("venueState",   "venue_state"),
        ("venueLGA",     "venue_lga"),
        ("jerseyNumber", "jersey_number"),
        ("contactPhone", "contact_phone"),
        ("requestType",  "request_type"),
        ("player_id",    "player_id"),
    ]
    for camel, snake in _map:
        if not d.get(camel) and d.get(snake):
            d[camel] = d[snake]
        if not d.get(snake) and d.get(camel):
            d[snake] = d[camel]
    # Alias: club preferred over club_name
    if not d.get("club") and d.get("club_name"):
        d["club"] = d["club_name"]
    # Flatten match sub-document into top level
    match_sub = d.get("match") or {}
    for key in ("homeTeam", "awayTeam", "scoreA", "scoreB", "half", "matchTime"):
        if not d.get(key) and match_sub.get(key):
            d[key] = match_sub[key]
    # Backfill venueCountryName from location_module when venueCountry is a code
    country_code = d.get("venueCountry", "")
    if country_code and len(country_code) <= 3 and not d.get("venueCountryName"):
        resolved = get_country_name(country_code)
        if resolved:
            d["venueCountryName"] = resolved
    return d

# ============================================================
# §6  PENDING APPROVALS & SUBMISSION REVIEW
# ============================================================

class ApproveSubmissionRequest(BaseModel):
    notes:       Optional[str] = ""
    editedStats: Optional[Dict[str, Any]] = None


class RejectSubmissionRequest(BaseModel):
    notes: str


@router.get("/supervisor/{supervisor_id}/pending-approvals")
async def get_pending_approvals(supervisor_id: str, request: Request):
    await _require_supervisor_auth(request, supervisor_id)
    dco_ids=[str(d.get("dco_id") or d.get("user_id") or d.get("_id")) async for d in dco_collection.find({"supervisor_id":supervisor_id})]
    ors=[{"supervisor_id":supervisor_id}]
    if dco_ids: ors += [{"dco_id":{"$in":dco_ids}},{"scout_id":{"$in":dco_ids}}]
    rows=await _submission_collection_rows({"$and":[{"$or":ors},{"status":{"$in":["pending_approval","submitted"]}}]},limit=200)
    return JSONResponse(content=[await _normalise_tracker_submission(x) for x in rows])

@router.post("/supervisor/{supervisor_id}/submissions/{submission_id}/approve")
async def approve_submission(supervisor_id: str, submission_id: str, request: Request, body: ApproveSubmissionRequest):
    await _require_supervisor_auth(request, supervisor_id)
    col,sub=await _find_submission_record(submission_id)
    if not sub: raise HTTPException(status_code=404,detail="Submission not found")
    sup=str(sub.get("supervisor_id") or ""); did=str(sub.get("dco_id") or sub.get("scout_id") or "")
    if sup and sup!=supervisor_id: raise HTTPException(status_code=403,detail="Submission belongs to a different supervisor")
    if not sup:
        d=await dco_collection.find_one({"$or":[{"dco_id":did},{"data_scout_id":did},{"user_id":did}]}) if did else None
        if not d or str(d.get("supervisor_id") or "")!=supervisor_id: raise HTTPException(status_code=403,detail="Submission not in your team")
        await col.update_one({"_id":sub["_id"]},{"$set":{"supervisor_id":supervisor_id}})
    if sub.get("status") not in ("pending_approval","submitted"): raise HTTPException(status_code=409,detail=f"Cannot approve a submission with status '{sub.get('status')}'")
    now=_now(); update={"status":"approved","supervisor_notes":body.notes or "","approved_by":supervisor_id,"approved_at":now,"updated_at":now}
    if body.editedStats:
        for k,v in body.editedStats.items(): update[f"stats.{k}"]=v
    await col.update_one({"_id":sub["_id"]},{"$set":update})
    if body.editedStats and col is stat_submissions_collection and stat_submission_players_collection is not None:
        child=await stat_submission_players_collection.find_one({"submission_id":sub["_id"]})
        if child:
            stats=dict(child.get("stats") or {}); stats.update(body.editedStats)
            await stat_submission_players_collection.update_one({"_id":child["_id"]},{"$set":{"stats":stats,"updated_at":now}})
    aids=list(dict.fromkeys([str(x) for x in (sub.get("assignment_ids") or []) if x]+([str(sub.get("assignment_id"))] if sub.get("assignment_id") else [])))
    if not aids and dco_assignments_collection is not None:
        linked = await dco_assignments_collection.find({
            "$or": [{"submission_id": str(sub.get("_id"))}, {"submission_id": sub.get("_id")}],
        }).limit(50).to_list(length=50)
        aids = [str(x.get("assignment_id") or x.get("_id")) for x in linked if x.get("assignment_id") or x.get("_id")]
    for aid in aids:
        if dco_assignments_collection is not None:
            await dco_assignments_collection.update_one(_assignment_filter(aid),{"$set":{"status":"completed","approved_at":now,"updated_at":now}})
    if did and notifications_collection is not None:
        try:
            label=f"{(sub.get('match') or {}).get('home_team_name') or sub.get('home_team') or ''} vs {(sub.get('match') or {}).get('away_team_name') or sub.get('away_team') or ''}".strip(" vs") or "your match"
            await notifications_collection.insert_one({"user_id":did,"user_type":"dco","title":"Submission Approved","message":f"Your stats submission for {label} has been approved.","type":"submission_approved","read":False,"created_at":now})
        except Exception: pass
    return JSONResponse({"message":"Submission approved","submission_id":submission_id,"status":"approved"})

@router.post("/supervisor/{supervisor_id}/submissions/{submission_id}/reject")
async def reject_submission(supervisor_id: str, submission_id: str, request: Request, body: RejectSubmissionRequest):
    await _require_supervisor_auth(request, supervisor_id)
    if not body.notes or not body.notes.strip(): raise HTTPException(status_code=400,detail="Rejection notes are required")
    col,sub=await _find_submission_record(submission_id)
    if not sub: raise HTTPException(status_code=404,detail="Submission not found")
    sup=str(sub.get("supervisor_id") or ""); did=str(sub.get("dco_id") or sub.get("scout_id") or "")
    if sup and sup!=supervisor_id: raise HTTPException(status_code=403,detail="Submission belongs to a different supervisor")
    if not sup:
        d=await dco_collection.find_one({"$or":[{"dco_id":did},{"data_scout_id":did},{"user_id":did}]}) if did else None
        if not d or str(d.get("supervisor_id") or "")!=supervisor_id: raise HTTPException(status_code=403,detail="Submission not in your team")
        await col.update_one({"_id":sub["_id"]},{"$set":{"supervisor_id":supervisor_id}})
    if sub.get("status") not in ("pending_approval","submitted"): raise HTTPException(status_code=409,detail=f"Cannot reject a submission with status '{sub.get('status')}'")
    now=_now()
    await col.update_one({"_id":sub["_id"]},{"$set":{"status":"rejected","supervisor_notes":body.notes.strip(),"rejected_by":supervisor_id,"rejected_at":now,"updated_at":now}})
    aids=list(dict.fromkeys([str(x) for x in (sub.get("assignment_ids") or []) if x]+([str(sub.get("assignment_id"))] if sub.get("assignment_id") else [])))
    for aid in aids:
        if dco_assignments_collection is not None: await dco_assignments_collection.update_one(_assignment_filter(aid),{"$set":{"status":"rejected","rejected_at":now,"updated_at":now}})
    if did and notifications_collection is not None:
        try:
            label=f"{(sub.get('match') or {}).get('home_team_name') or sub.get('home_team') or ''} vs {(sub.get('match') or {}).get('away_team_name') or sub.get('away_team') or ''}".strip(" vs") or "your match"
            await notifications_collection.insert_one({"user_id":did,"user_type":"dco","title":"Submission Rejected","message":f"Your stats submission for {label} was rejected. Notes: {body.notes.strip()}","type":"submission_rejected","read":False,"created_at":now})
        except Exception: pass

    return JSONResponse({"message":"Submission rejected","submission_id":submission_id,"status":"rejected"})

# ============================================================
# §7  SUBMISSIONS HISTORY
# ============================================================

@router.get("/supervisor/{supervisor_id}/submissions-history")
async def get_submissions_history(supervisor_id: str, request: Request, status: Optional[str]=None, limit: int=200, skip: int=0):
    await _require_supervisor_auth(request,supervisor_id)
    dco_ids=[str(d.get("dco_id") or d.get("user_id") or d.get("_id")) async for d in dco_collection.find({"supervisor_id":supervisor_id})]
    ors=[{"supervisor_id":supervisor_id}]
    if dco_ids: ors += [{"dco_id":{"$in":dco_ids}},{"scout_id":{"$in":dco_ids}}]
    q={"$or":ors}
    if status and status!="all": q["status"]=status
    rows=await _submission_collection_rows(q,limit=max(1,min(limit+skip,500)))
    rows=rows[max(0,skip):max(0,skip)+max(1,min(limit,500))]
    return JSONResponse(content=[await _normalise_tracker_submission(x) for x in rows])

# ============================================================
# §8  EARNINGS & PAYOUTS
# ============================================================

# Tier payout rates (₦) — mirrors the frontend TIER_RATES_SUP constant
_TIER_RATES: dict = {
    1: {"Professional": 200, "Semi-professional": 150, "Other": 100, "Club": 400},
    2: {"Professional": 350, "Semi-professional": 250, "Other": 150, "Club": 700},
    3: {"Professional": 500, "Semi-professional": 350, "Other": 250, "Club": 1000},
}


@router.get("/supervisor/{supervisor_id}/earnings")
async def get_supervisor_earnings(supervisor_id: str, request: Request):
    """
    Return the supervisor's earnings summary.

    Aggregates approved submissions to compute pending (unpaid) earnings,
    total earned, and a per-submission activities breakdown.
    """
    await _require_supervisor_auth(request, supervisor_id)
    sup_doc = await _resolve_supervisor(supervisor_id)

    try:
        tier = int(sup_doc.get("tier") or 1)
        if tier not in _TIER_RATES:
            tier = 1
    except (TypeError, ValueError):
        tier = 1
    rates: dict = _TIER_RATES.get(tier, _TIER_RATES[1])

    # All approved submissions — compute totals without a row-count limit
    # so pending_amount / total_earned are always accurate.
    # The activity detail list is capped at 200 rows for response size.
    activities: List[dict] = []
    total_pending = 0.0
    total_earned  = 0.0
    row_limit     = 200
    row_count     = 0

    approved_rows = await _submission_collection_rows(
        {"supervisor_id": supervisor_id, "status": "approved"},
        limit=100000, sort_field="approved_at",
    )
    for sub in approved_rows:
        player_level = sub.get("player_level") or sub.get("category") or "Other"
        is_club      = bool(sub.get("club_id") or sub.get("is_club_match"))

        if is_club:
            rate   = rates.get("Club", 400)
            category = "Club Match"
        elif "professional" in player_level.lower():
            if "semi" in player_level.lower():
                rate   = rates.get("Semi-professional", 150)
                category = "Semi-Pro Player"
            else:
                rate   = rates.get("Professional", 200)
                category = "Professional Player"
        else:
            rate   = rates.get("Other", 100)
            category = "Other Player"

        paid_status = sub.get("payout_status", "pending") or "pending"
        try:
            amount = float(rate)
        except (TypeError, ValueError):
            amount = 0.0

        # Accumulate summary totals over ALL rows (no row cap)
        if paid_status != "paid":
            total_pending += amount
        total_earned += amount

        # Cap the activity detail list at row_limit rows for response size
        if row_count < row_limit:
            activities.append({
                "match":    (
                    f"{sub.get('home_team', '')} vs {sub.get('away_team', '')}".strip(" vs")
                    or "Match"
                ),
                "dcoName":  sub.get("dco_name") or sub.get("scout_name") or "",
                "category": category,
                "amount":   amount,
                "status":   paid_status,
                "date":     MongoSerializer.serialize_value(
                                sub.get("approved_at") or sub.get("submitted_at")
                            ),
            })
        row_count += 1

    return JSONResponse(content={
        "pending_amount":   round(total_pending, 2),
        "total_earned":     round(total_earned, 2),
        "tier":             tier,
        "rates":            rates,
        "activities":       activities,
    })


class PayoutRequestBody(BaseModel):
    amount: float


@router.get("/supervisor/{supervisor_id}/payout-requests")
async def get_payout_requests(supervisor_id: str, request: Request):
    """Return the supervisor's payout request history."""
    await _require_supervisor_auth(request, supervisor_id)

    requests: List[dict] = []
    async for pr in supervisor_payout_requests_col.find(
        {"supervisor_id": supervisor_id},
        sort=[("created_at", -1)],
    ):
        requests.append(MongoSerializer.serialize_document(pr))

    return JSONResponse(content=requests)


@router.post("/supervisor/{supervisor_id}/payout-requests")
async def create_payout_request(
    supervisor_id: str,
    request: Request,
    body: PayoutRequestBody,
):
    """Submit a payout request for pending earnings."""
    await _require_supervisor_auth(request, supervisor_id)

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    sup_doc = await _resolve_supervisor(supervisor_id)

    # Verify the supervisor has a withdrawal account on file
    withdrawal = sup_doc.get("withdrawal_account") or {}
    if not withdrawal.get("account_number"):
        raise HTTPException(
            status_code=400,
            detail="Please save your withdrawal account details before requesting a payout",
        )

    # Check for an already-pending request
    existing_pending = await supervisor_payout_requests_col.find_one(
        {"supervisor_id": supervisor_id, "status": "pending"}
    )
    if existing_pending:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending payout request",
        )

    ref = (
        _make_supervisor_payout_ref()
        if _make_supervisor_payout_ref
        else f"SPAY-{secrets.token_hex(8).upper()}"
    )

    payout_doc = {
        "supervisor_id":     supervisor_id,
        "amount":            body.amount,
        "reference":         ref,
        "status":            "pending",
        "bank_name":         withdrawal.get("bank_name", ""),
        "account_number":    withdrawal.get("account_number", ""),
        "account_name":      withdrawal.get("account_name") or sup_doc.get("name", ""),
        "supervisor_name":   sup_doc.get("name") or sup_doc.get("full_name", ""),
        "created_at":        _now(),
        "updated_at":        _now(),
    }

    result = await supervisor_payout_requests_col.insert_one(payout_doc)
    payout_doc["_id"] = str(result.inserted_id)

    # Notify admin (fire-and-forget)
    try:
        await notifications_collection.insert_one({
            "user_id":    "admin",
            "user_type":  "admin",
            "title":      "Supervisor Payout Request",
            "message":    (
                f"Supervisor {payout_doc['supervisor_name']} has requested a payout "
                f"of ₦{body.amount:,.2f}. Reference: {ref}"
            ),
            "type":       "payout_request",
            "read":       False,
            "created_at": _now(),
        })
    except Exception as exc:
        logger.warning(f"Admin payout notification failed: {exc}")

    return JSONResponse(
        content=MongoSerializer.serialize_document(payout_doc),
        status_code=201,
    )


# ============================================================
# §9  NOTIFICATIONS
# ============================================================

# NOTE: PATCH .../notifications/{notif_id}/read is the only notifications
# sub-route; no ordering conflict exists here (unlike the scout module
# which had a /read-all literal that needed to precede /{notif_id}/read).

@router.get("/supervisor/{supervisor_id}/notifications")
async def get_supervisor_notifications(supervisor_id: str, request: Request):
    """Return all notifications for this supervisor, newest first."""
    await _require_supervisor_auth(request, supervisor_id)

    notifs: List[dict] = []
    async for n in notifications_collection.find(
        {
            "$or": [
                {"user_id": supervisor_id, "user_type": "supervisor"},
                {"user_id": supervisor_id},
            ]
        },
        sort=[("created_at", -1)],
        limit=100,
    ):
        notifs.append(MongoSerializer.serialize_document(n))

    return JSONResponse(content=notifs)


@router.patch("/supervisor/{supervisor_id}/notifications/{notif_id}/read")
async def mark_supervisor_notification_read(
    supervisor_id: str,
    notif_id: str,
    request: Request,
):
    """Mark a single notification as read."""
    await _require_supervisor_auth(request, supervisor_id)

    oid = _try_objectid(notif_id)
    if not oid:
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    result = await notifications_collection.update_one(
        {"_id": oid, "user_id": supervisor_id},
        {"$set": {"read": True, "read_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")

    return JSONResponse(content={"message": "Notification marked as read"})


# ============================================================
# §10  CHAT (Supervisor ↔ DCO)
# ============================================================

class ChatSendRequest(BaseModel):
    message: str
    sender:  Optional[str] = "supervisor"


@router.get("/supervisor/{supervisor_id}/chat/threads")
async def get_chat_threads(supervisor_id: str, request: Request):
    """
    Return all chat threads for this supervisor.

    Each thread represents a conversation channel between the supervisor
    and a specific DCO (or admin).
    """
    await _require_supervisor_auth(request, supervisor_id)

    threads: List[dict] = []
    async for t in supervisor_chat_threads_col.find(
        {"supervisor_id": supervisor_id},
        sort=[("updated_at", -1)],
    ):
        serialized = MongoSerializer.serialize_document(t)

        # Attach last message preview
        last_msg = await supervisor_chat_messages_col.find_one(
            {"thread_id": str(t["_id"])},
            sort=[("created_at", -1)],
        )
        if last_msg:
            serialized["lastMessage"] = last_msg.get("message", "")
            serialized["lastMessageAt"] = MongoSerializer.serialize_value(
                last_msg.get("created_at")
            )

        # Unread count
        unread_count = await supervisor_chat_messages_col.count_documents(
            {"thread_id": str(t["_id"]), "sender": {"$ne": "supervisor"}, "read": False}
        )
        serialized["unreadCount"] = unread_count
        threads.append(serialized)

    return JSONResponse(content=threads)


@router.get("/supervisor/{supervisor_id}/chat/threads/{thread_id}/messages")
async def get_chat_messages(
    supervisor_id: str,
    thread_id: str,
    request: Request,
    limit: int = 50,
    skip: int = 0,
):
    """Return messages in a chat thread, oldest-first (for natural chat order)."""
    await _require_supervisor_auth(request, supervisor_id)

    # Verify the thread belongs to this supervisor
    t_oid = _try_objectid(thread_id)
    thread = None
    if t_oid:
        thread = await supervisor_chat_threads_col.find_one(
            {"_id": t_oid, "supervisor_id": supervisor_id}
        )
    if not thread:
        thread = await supervisor_chat_threads_col.find_one(
            {"thread_id": thread_id, "supervisor_id": supervisor_id}
        )
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found")

    messages: List[dict] = []
    async for msg in supervisor_chat_messages_col.find(
        {"thread_id": thread_id},
        sort=[("created_at", 1)],
        skip=skip,
        limit=limit,
    ):
        messages.append(MongoSerializer.serialize_document(msg))

    # Mark all unread messages from the other party as read
    await supervisor_chat_messages_col.update_many(
        {"thread_id": thread_id, "sender": {"$ne": "supervisor"}, "read": False},
        {"$set": {"read": True, "read_at": _now()}},
    )

    return JSONResponse(content=messages)


@router.post("/supervisor/{supervisor_id}/chat/threads/{thread_id}/send")
async def send_chat_message(
    supervisor_id: str,
    thread_id: str,
    request: Request,
    body: ChatSendRequest,
):
    """
    Send a message in a chat thread.

    If the thread does not yet exist (first message), it is created
    atomically via upsert.  Thread access is scoped to the authenticated
    supervisor — cross-owner thread_id values are rejected with 404.
    """
    await _require_supervisor_auth(request, supervisor_id)

    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Atomic upsert: create the thread if absent, touch updated_at if present.
    # Scoped to supervisor_id so a caller cannot write into another supervisor's thread.
    await supervisor_chat_threads_col.find_one_and_update(
        filter={"supervisor_id": supervisor_id, "thread_id": thread_id},
        update={
            "$setOnInsert": {
                "supervisor_id": supervisor_id,
                "thread_id":     thread_id,
                "participants":  [supervisor_id],
                "created_at":    _now(),
            },
            "$set": {"updated_at": _now()},
        },
        upsert=True,
        return_document=False,   # we only need the side-effect, not the doc
    )

    # Verify the (now-guaranteed-existing) thread belongs to this supervisor.
    # This catches the case where thread_id was already owned by someone else
    # and was not just created above.
    owner_check = await supervisor_chat_threads_col.find_one(
        {"supervisor_id": supervisor_id, "thread_id": thread_id}
    )
    if not owner_check:
        raise HTTPException(status_code=404, detail="Chat thread not found")

    msg_doc = {
        "thread_id":  thread_id,
        "sender":     body.sender or "supervisor",
        "message":    body.message.strip(),
        "read":       False,
        "created_at": _now(),
    }

    result = await supervisor_chat_messages_col.insert_one(msg_doc)
    msg_doc["_id"] = str(result.inserted_id)

    return JSONResponse(
        content=MongoSerializer.serialize_document(msg_doc),
        status_code=201,
    )


# ============================================================
# §11  SUBSCRIPTION
# ============================================================

@router.get("/supervisor/{supervisor_id}/subscription")
async def get_supervisor_subscription(supervisor_id: str, request: Request):
    """
    Return the supervisor's active subscription record.

    Supervisors pay for platform access via the same subscription system as
    other roles.  The subscription document carries ``user_id == supervisor_id``
    and ``role == "supervisor"``.
    """
    await _require_supervisor_auth(request, supervisor_id)

    sub = await subscriptions_collection.find_one(
        {
            "$or": [
                {"user_id": supervisor_id, "role": "supervisor"},
                {"user_id": supervisor_id},
            ]
        },
        sort=[("created_at", -1)],
    )
    if not sub:
        return JSONResponse(content={"subscription_status": "TRIAL_ACTIVE", "message": "No active subscription"})

    return JSONResponse(content=MongoSerializer.serialize_document(sub))


@router.get("/supervisor/{supervisor_id}/subscription/history")
async def get_supervisor_subscription_history(supervisor_id: str, request: Request):
    """Return the full subscription payment history for this supervisor."""
    await _require_supervisor_auth(request, supervisor_id)

    history: List[dict] = []
    async for record in subscriptions_collection.find(
        {
            "$or": [
                {"user_id": supervisor_id, "role": "supervisor"},
                {"user_id": supervisor_id},
            ]
        },
        sort=[("created_at", -1)],
    ):
        history.append(MongoSerializer.serialize_document(record))

    # Also pull from payment_intents that are SUBSCRIPTION type
    async for intent in payment_intents_collection.find(
        {
            "user_id":     supervisor_id,
            "paymentType": "SUBSCRIPTION",
            "status":      {"$in": ["approved", "completed", "pending"]},
        },
        sort=[("created_at", -1)],
    ):
        # Deduplicate: skip if already represented by a subscriptions record
        ref = intent.get("reference", "")
        if not any(h.get("reference") == ref for h in history):
            history.append(MongoSerializer.serialize_document(intent))

    history.sort(
        key=lambda x: x.get("created_at") or x.get("date") or "",
        reverse=True,
    )

    return JSONResponse(content=history)
