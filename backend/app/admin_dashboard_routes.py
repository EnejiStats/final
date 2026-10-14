"""
admin_dashboard_routes.py
=========================
EnejiStats — Admin Dashboard API Routes (Merged).

Architecture
------------
- Uses APIRouter (NOT app = FastAPI())
- Match Centre stats-request routes are owned by match_centre_routes.py and mounted there; they are intentionally not duplicated here.
- Module-level placeholders set to None at import time
- _setup_dependencies(main_globals) injected from main.py at startup
- Mount in main.py:
      import admin_dashboard_routes as _admin_dr
      _admin_dr._setup_dependencies(globals())
      app.include_router(_admin_dr.router)

Endpoints — exact 1:1 map with every frontend fetch() call
-----------------------------------------------------------
# ── AUTH ─────────────────────────────────────────────────────────────
POST   /api/admin/login
GET    /api/admin/me
GET    /api/auth/me
POST   /api/auth/logout

# ── USERS ────────────────────────────────────────────────────────────
GET    /api/admin/users
GET    /api/admin/users/{uid}
POST   /api/admin/users/{uid}/message
POST   /api/admin/users/{uid}/tokens/credit
POST   /api/admin/users/{uid}/tokens/debit
POST   /api/admin/users/{uid}/{action}          (activate|suspend|unsuspend|verify|delete)

# ── PENDING APPROVALS ────────────────────────────────────────────────
GET    /api/admin/pending-scouts
GET    /api/admin/pending-players
POST   /api/admin/approve-scout/{scout_id}
POST   /api/admin/reject-scout/{scout_id}
POST   /api/admin/approve-player/{player_id}
POST   /api/admin/reject-player/{player_id}

# ── SUB-ADMINS ───────────────────────────────────────────────────────
GET    /api/admin/sub-admins
POST   /api/admin/sub-admins
DELETE /api/admin/sub-admins/{admin_id}

# ── PAYMENT RECEIPTS ─────────────────────────────────────────────────
GET    /api/admin/payment-receipts
GET    /api/admin/payment-receipts/{tx_ref}
POST   /api/admin/payment-receipts/{tx_ref}/approve
POST   /api/admin/payment-receipts/{tx_ref}/reject

# ── PAYMENT INTENTS ──────────────────────────────────────────────────
GET    /api/admin/payment-intents
POST   /api/admin/payment-intents/{tx_ref}/approve
POST   /api/admin/payment-intents/{tx_ref}/reject
POST   /api/admin/payment-intents/{tx_ref}/mark-pnr
POST   /api/admin/payment-intents/{tx_ref}/confirm-payment

# ── PAYMENTS ALIASES (frontend fallback) ─────────────────────────────
POST   /api/admin/payments/{tx_ref}/approve
POST   /api/admin/payments/{tx_ref}/reject
POST   /api/admin/payments/{tx_ref}/mark-pnr
POST   /api/admin/payments/{tx_ref}/confirm-payment

# ── SUBSCRIPTIONS ────────────────────────────────────────────────────
GET    /api/admin/subscriptions
POST   /api/admin/subscriptions/grant
POST   /api/admin/subscriptions/{uid}/extend
POST   /api/admin/subscriptions/{uid}/cancel
POST   /api/admin/subscriptions/send-trial-warnings
GET    /api/admin/subscriptions/receipts

# ── TOKENS ───────────────────────────────────────────────────────────
GET    /api/admin/tokens/overview
GET    /api/admin/tokens/history
POST   /api/admin/tokens/credit
POST   /api/admin/tokens/debit
GET    /api/admin/entity-details/{role}/{query}

# ── DCO TIER MANAGEMENT ──────────────────────────────────────────────
GET    /api/admin/tier-management
PATCH  /api/admin/data-scouts/{scout_id}/tier

# ── MESSAGES / BROADCASTS ────────────────────────────────────────────
GET    /api/admin/messages/history
POST   /api/admin/messages/send

# ── SUPPORT TICKETS ──────────────────────────────────────────────────
GET    /api/admin/support/tickets
GET    /api/admin/support/tickets/{ticket_id}
POST   /api/admin/support/tickets/{ticket_id}/reply
PATCH  /api/admin/support/tickets/{ticket_id}/status

# ── PAYOUT REQUESTS ──────────────────────────────────────────────────
GET    /api/admin/payout-requests
POST   /api/admin/payout-requests/{payout_id}/approve
POST   /api/admin/payout-requests/{payout_id}/reject


# ── ASSIGNMENTS ──────────────────────────────────────────────────────
GET    /api/admin/assignments
POST   /api/admin/assignments

# ── BACKGROUND CHECKS ────────────────────────────────────────────────
GET    /api/admin/background-checks
POST   /api/admin/background-checks/{uid}/approve
POST   /api/admin/background-checks/{uid}/reject

# ── BANK DETAILS ─────────────────────────────────────────────────────
GET    /api/admin/bank-details
POST   /api/admin/bank-details
GET    /api/admin/settings/bank     (alias for GET  /api/admin/bank-details)
PATCH  /api/admin/settings/bank     (alias for POST /api/admin/bank-details)

# ── PLATFORM SETTINGS ────────────────────────────────────────────────
GET    /api/admin/settings
PATCH  /api/admin/settings
"""

# ==============================================================
# START OF FILE
# ==============================================================

from __future__ import annotations

import asyncio
import secrets
from calendar import monthrange as _mr
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from location_module import build_venue_location_filter, get_country_name
import match_centre_routes as _match_centre_routes
import pricing_module as _pricing_module

# ============================================================
# MODULE-LEVEL PLACEHOLDERS — set in _setup_dependencies()
# ============================================================

logger = None

# Database handle (for dynamic collection access)
database = None
users_collection = None

# Collections
players_collection                = None
clubs_collection                  = None
scouts_collection                 = None
agents_collection                 = None
dco_collection                    = None
supervisors_collection            = None
communication_officers_collection = None
customer_care_collection          = None
admins_collection                 = None
content_managers_collection       = None
sub_admins_collection              = None
player_tokens_collection          = None
club_tokens_collection            = None
scout_tokens_collection           = None
dco_tokens_collection             = None
agent_tokens_collection           = None
transactions_collection           = None
token_transactions_collection     = None
notifications_collection          = None
subscriptions_collection          = None
subscription_audit_collection     = None
stats_requests_collection         = None
dco_assignments_collection        = None
support_tickets_collection        = None
support_messages_collection       = None
broadcasts_collection             = None
activity_history_collection       = None
platform_settings_collection      = None
payment_intents_collection        = None
payout_requests_collection        = None

# Core helpers from main.py
MongoSerializer     = None
get_admin_user      = None
credit_tokens       = None
deduct_tokens       = None
send_email          = None
_email_html         = None
pricing_service     = None

# Canonical auth/identity services injected from main.py
verify_password        = None
normalize_email        = None
normalize_role         = None
role_collection        = None
ROLE_COLLECTION_MAP    = None
CANONICAL_ROLES        = None
TOKEN_ELIGIBLE_ROLES   = None
create_platform_user   = None
build_user_access_token = None

# Readiness flag
_DEPS_READY = False

# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

# Match Centre is a standalone router mounted under the admin dashboard
# router.  It owns its complete route/logic surface.
router.include_router(_match_centre_routes.router)

# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Inject all shared objects from main.py globals().
    Call once at startup, before app.include_router().
    """
    global _DEPS_READY
    global logger, MongoSerializer, get_admin_user
    global credit_tokens, deduct_tokens, send_email, _email_html, pricing_service
    global verify_password, normalize_email, normalize_role, role_collection
    global ROLE_COLLECTION_MAP, CANONICAL_ROLES, TOKEN_ELIGIBLE_ROLES
    global create_platform_user, build_user_access_token
    global database, users_collection
    global players_collection, clubs_collection, scouts_collection
    global agents_collection, dco_collection, supervisors_collection
    global communication_officers_collection, customer_care_collection
    global admins_collection, content_managers_collection, sub_admins_collection
    global player_tokens_collection, club_tokens_collection
    global scout_tokens_collection, dco_tokens_collection, agent_tokens_collection
    global transactions_collection, token_transactions_collection
    global notifications_collection, subscriptions_collection
    global subscription_audit_collection, stats_requests_collection
    global dco_assignments_collection, support_tickets_collection
    global support_messages_collection, broadcasts_collection
    global activity_history_collection, platform_settings_collection
    global payment_intents_collection, payout_requests_collection

    g = main_globals or {}

    logger                            = g.get("logger")
    MongoSerializer                   = g.get("MongoSerializer")
    get_admin_user                   = g.get("get_admin_user")
    credit_tokens                     = g.get("credit_tokens")
    deduct_tokens                     = g.get("deduct_tokens")
    send_email                        = g.get("send_email")
    _email_html                       = g.get("_email_html")
    pricing_service                   = g.get("pricing_service")
    verify_password                   = g.get("verify_password")
    normalize_email                   = g.get("normalize_email")
    normalize_role                    = g.get("normalize_role")
    role_collection                   = g.get("role_collection")
    ROLE_COLLECTION_MAP               = g.get("ROLE_COLLECTION_MAP")
    CANONICAL_ROLES                   = g.get("CANONICAL_ROLES")
    TOKEN_ELIGIBLE_ROLES              = g.get("TOKEN_ELIGIBLE_ROLES")
    create_platform_user              = g.get("create_platform_user")
    build_user_access_token           = g.get("build_user_access_token")
    database                          = g.get("database")
    users_collection                  = g.get("users_collection")

    players_collection                = g.get("players_collection")
    clubs_collection                  = g.get("clubs_collection")
    scouts_collection                 = g.get("scouts_collection")
    agents_collection                 = g.get("agents_collection")
    dco_collection                    = g.get("dco_collection")
    supervisors_collection            = g.get("supervisors_collection")
    communication_officers_collection = g.get("communication_officers_collection")
    customer_care_collection          = g.get("customer_care_collection")
    admins_collection                 = g.get("admins_collection")
    content_managers_collection       = g.get("content_managers_collection")
    sub_admins_collection              = g.get("sub_admins_collection")
    player_tokens_collection          = g.get("player_tokens_collection")
    club_tokens_collection            = g.get("club_tokens_collection")
    scout_tokens_collection           = g.get("scout_tokens_collection")
    dco_tokens_collection             = g.get("dco_tokens_collection")
    agent_tokens_collection           = g.get("agent_tokens_collection")
    transactions_collection           = g.get("transactions_collection")
    token_transactions_collection     = g.get("token_transactions_collection")
    notifications_collection          = g.get("notifications_collection")
    subscriptions_collection          = g.get("subscriptions_collection")
    subscription_audit_collection     = g.get("subscription_audit_collection")
    stats_requests_collection         = g.get("stats_requests_collection")
    dco_assignments_collection        = g.get("dco_assignments_collection")
    support_tickets_collection        = g.get("support_tickets_collection")
    support_messages_collection       = g.get("support_messages_collection")
    broadcasts_collection             = g.get("broadcasts_collection")
    activity_history_collection       = g.get("activity_history_collection")
    platform_settings_collection      = g.get("platform_settings_collection")
    payment_intents_collection        = g.get("payment_intents_collection")
    payout_requests_collection        = g.get("payout_requests_collection")
    # Match Centre is mounted as a standalone child router.  It receives the
    # application's original main.py dependency namespace directly and does
    # not import this admin module, preventing circular imports.
    _match_centre_routes._setup_dependencies(main_globals)

    _DEPS_READY = True

    if logger:
        logger.info(
            "[admin_dashboard_routes] Dependencies injected — %d routes registered",
            len(router.routes),
        )


# ============================================================
# INTERNAL HELPERS — CORE
# ============================================================

async def _require_admin(request: Request) -> dict:
    return await _get_admin_from_request(request)


def _s(doc: Optional[dict]) -> dict:
    if not doc:
        return {}
    return MongoSerializer.serialize_document(doc)


def _ss(docs: List[dict]) -> List[dict]:
    return MongoSerializer.serialize_documents(docs)


def _now() -> datetime:
    return MongoSerializer.now_utc()


def _sv(v) -> Any:
    return MongoSerializer.serialize_value(v)


def _display_name(doc: dict) -> str:
    return (
        doc.get("full_name")
        or doc.get("name")
        or doc.get("club_name")
        or " ".join(filter(None, [
            doc.get("first_name", "") or doc.get("firstName", ""),
            doc.get("last_name", "")  or doc.get("lastName", ""),
        ])).strip()
        or doc.get("email", "")
    )


def _role_col_map() -> Dict[str, tuple]:
    """Return the canonical main.py role → (collection, public-ID field) map."""
    if not ROLE_COLLECTION_MAP:
        return {}
    return {
        role: (globals().get(collection_name), id_field)
        for role, (collection_name, id_field) in ROLE_COLLECTION_MAP.items()
    }


def _token_col(role: str):
    """Resolve a token wallet only when main.py marks the role token-eligible."""
    if not TOKEN_ELIGIBLE_ROLES:
        return None
    try:
        canonical = normalize_role(role)
    except Exception:
        return None
    if canonical not in TOKEN_ELIGIBLE_ROLES:
        return None
    return globals().get(f"{canonical}_tokens_collection")


async def _find_user(uid: str) -> Optional[tuple]:
    """Search all role collections for uid. Returns (doc, role, id_field) or None."""
    for role, (col, id_field) in _role_col_map().items():
        if col is None:
            continue
        doc = await col.find_one({id_field: uid})
        if not doc:
            doc = await col.find_one({"user_id": uid})
        if not doc and len(uid) == 24:
            try:
                doc = await col.find_one({"_id": ObjectId(uid)})
            except Exception:
                pass
        if doc:
            return doc, role, id_field
    return None


def _log(actor_id: str, actor_role: str, atype: str, desc: str) -> None:
    async def _inner():
        try:
            await activity_history_collection.insert_one({
                "actor_id":    actor_id,
                "actor_role":  actor_role,
                "type":        atype,
                "description": desc,
                "created_at":  _now(),
            })
        except Exception:
            pass
    asyncio.ensure_future(_inner())


def _html_email(subject: str, html_inner: str) -> str:
    if _email_html:
        return _email_html(subject, html_inner)
    return html_inner


async def _send_bg(to: str, subject: str, plain: str, html: str) -> None:
    if send_email and to:
        asyncio.ensure_future(send_email(to, subject, plain, html))


# ============================================================
# INTERNAL HELPERS — EXTENDED
# ============================================================

def _require_collection(col, name: str):
    """Raise a 503 if a collection placeholder was not injected."""
    if col is None:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: collection '{name}' not initialised.",
        )
    return col


async def _get_admin_from_request(request: Request) -> dict:
    """Resolve the authenticated administrator through main.py's canonical guard."""
    if get_admin_user is None:
        raise HTTPException(status_code=503, detail="Auth service not ready")
    user = await get_admin_user(request)
    return MongoSerializer.serialize_document(user)


def _serialize(doc: dict) -> dict:
    """Serialize a single MongoDB document (alias used by extended routes)."""
    return MongoSerializer.serialize_document(doc)


def _now_utc() -> datetime:
    """Compatibility wrapper around main.py's canonical UTC serializer."""
    return MongoSerializer.now_utc()


def _build_month_filter(month: Optional[str]) -> Optional[dict]:
    """
    Return a MongoDB ``created_at`` range filter for YYYY-MM strings,
    or None when month is falsy.
    """
    if not month:
        return None
    try:
        year, mon = int(month[:4]), int(month[5:7])
        _, last_day = _mr(year, mon)
        start = datetime(year, mon, 1, tzinfo=timezone.utc)
        end   = datetime(year, mon, last_day, 23, 59, 59, tzinfo=timezone.utc)
        return {"$gte": start, "$lte": end}
    except Exception:
        return None


async def _send_notification(user_id: str, user_type: str,
                             title: str, message: str, notif_type: str) -> None:
    """Fire-and-forget notification insert (swallows all errors)."""
    try:
        col = notifications_collection
        if col is None:
            return
        await col.insert_one({
            "user_id":    user_id,
            "user_type":  user_type,
            "title":      title,
            "message":    message,
            "type":       notif_type,
            "read":       False,
            "created_at": _now_utc(),
        })
    except Exception:
        pass


async def _find_payment(tx_ref: str) -> Optional[dict]:
    """Look up a payment by tx_ref across intents and transactions."""
    pi_col = payment_intents_collection
    tx_col = transactions_collection

    doc = None
    if pi_col is not None:
        doc = await pi_col.find_one(
            {"$or": [{"tx_ref": tx_ref}, {"_id": _try_oid(tx_ref)}]}
        )
    if doc is None and tx_col is not None:
        doc = await tx_col.find_one(
            {"$or": [{"tx_ref": tx_ref}, {"_id": _try_oid(tx_ref)}]}
        )
    return doc


async def _update_payment(tx_ref: str, update: dict) -> bool:
    """Update a payment document in whichever collection it lives in."""
    pi_col = payment_intents_collection
    tx_col = transactions_collection

    filter_q = {"$or": [{"tx_ref": tx_ref}, {"_id": _try_oid(tx_ref)}]}

    if pi_col is not None:
        res = await pi_col.update_one(filter_q, update)
        if res.matched_count:
            return True

    if tx_col is not None:
        res = await tx_col.update_one(filter_q, update)
        if res.matched_count:
            return True

    return False


def _try_oid(value: str):
    """Return ObjectId(value) or a dummy that will never match."""
    try:
        return ObjectId(value)
    except Exception:
        return ObjectId("000000000000000000000000")


def _coerce_heatmap_admin(value):
    """Normalise various heatmap representations to Python bool or None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        n = value.strip().lower()
        if n in ('true', 'yes', '1', 'on'):
            return True
        if n in ('false', 'no', '0', 'off', ''):
            return False
    return None



async def _find_user_for_bgcheck(uid: str) -> tuple:
    """
    Look up a user by uid across DCO, scout, and supervisor collections.
    Returns (document, collection, role) or (None, None, None).
    """
    _cols = [
        (dco_collection,         "dco"),
        (scouts_collection,      "scout"),
        (supervisors_collection, "supervisor"),
        (players_collection,     "player"),
        (agents_collection,      "agent"),
    ]
    filter_q = {
        "$or": [
            {"user_id":   uid},
            {"dco_id":    uid},
            {"scout_id":  uid},
            {"player_id": uid},
            {"agent_id":  uid},
            {"_id":       _try_oid(uid)},
        ]
    }
    for col, role in _cols:
        if col is None:
            continue
        doc = await col.find_one(filter_q)
        if doc:
            return doc, col, role
    return None, None, None


_BANK_SETTINGS_KEY = "platform_bank_details"


# ─── REPLACE THE ENTIRE _get_bank_document FUNCTION ──────────────────────
async def _get_bank_document() -> dict:
    """Retrieve bank details from platform_settings_collection."""
    col = platform_settings_collection

    # Try platform_settings_collection first (preferred)
    if col is not None:
        doc = await col.find_one({"key": _BANK_SETTINGS_KEY})
        if doc:
            return doc

    # Fall back to admin_settings collection via Motor dict-access
    if database is not None:
        try:
            admin_settings_col = database["admin_settings"]   # ← Motor uses [] not .get()
            doc = await admin_settings_col.find_one({"key": "platform"})
            if doc:
                bank = doc.get("bank_transfer") or doc.get("bank_details") or {}
                return {"key": _BANK_SETTINGS_KEY, "bank_details": bank}
        except Exception:
            pass

    return {}


# ============================================================
# PYDANTIC REQUEST MODELS
# ============================================================

class AdminLoginBody(BaseModel):
    email: str
    password: str


class PayoutApproveBody(BaseModel):
    transaction_ref: Optional[str] = None
    reference: Optional[str] = None


class PayoutRejectBody(BaseModel):
    reason: Optional[str] = None


class PaymentActionBody(BaseModel):
    reason: Optional[str] = None

class StatsAssignBody(BaseModel):
    request_id: Optional[str] = None
    assignee_id: str
    role: Optional[str] = "dco"
    notes: Optional[str] = None
    supervisor_id: Optional[str] = None

class StatsRejectBody(BaseModel):
    reason: Optional[str] = None


class AssignmentBody(BaseModel):
    stats_request_id: str
    assigned_dco_id: Optional[str] = None
    assigned_supervisor_id: Optional[str] = None
    notes: Optional[str] = None


class BankDetailsBody(BaseModel):
    account_name:      Optional[str] = None
    account_number:    Optional[str] = None
    bank_name:         Optional[str] = None
    sort_code:         Optional[str] = None
    swift:             Optional[str] = None
    payment_reference: Optional[str] = None
    instructions:      Optional[str] = None


# ============================================================
# ── AUTH ────────────────────────────────────────────────────
# ============================================================

@router.post("/api/admin/login")
async def admin_login(request: Request):
    """Authenticate an administrator using main.py's canonical password/JWT services."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = normalize_email(body.get("email", "")) if normalize_email else str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    admin = await _require_collection(admins_collection, "admins_collection").find_one({"email": email})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is suspended")

    stored = admin.get("password_hash") or admin.get("password") or admin.get("hashed_password") or admin.get("hashed_pw") or ""
    if verify_password is None or not stored:
        raise HTTPException(status_code=503, detail="Auth service not ready")
    try:
        valid = verify_password(password, stored)
    except Exception:
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if build_user_access_token is None:
        raise HTTPException(status_code=503, detail="Auth service not ready")
    canonical_admin = dict(admin)
    canonical_admin["role"] = "admin"
    canonical_admin["user_type"] = "admin"
    canonical_admin.setdefault("admin_id", canonical_admin.get("user_id") or str(canonical_admin.get("_id", "")))
    try:
        token = build_user_access_token(canonical_admin)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to issue access token: {exc}")

    name = (
        admin.get("name")
        or admin.get("admin_name")
        or f"{admin.get('firstName', '')} {admin.get('lastName', '')}".strip()
        or email
    )
    resp = JSONResponse({
        "token": token,
        "access_token": token,
        "role": "admin",
        "user_type": "admin",
        "name": name,
        "admin_id": canonical_admin["admin_id"],
        "user_id": canonical_admin["admin_id"],
        "unique_id": canonical_admin["admin_id"],
    })
    resp.set_cookie("auth_token", token, httponly=True, samesite="lax", max_age=86400)
    return resp


@router.get("/api/admin/me")
async def admin_me(request: Request):
    user = await _get_admin_from_request(request)
    return JSONResponse(_s(user))

# ============================================================
# ── USERS ───────────────────────────────────────────────────
# ============================================================

@router.get("/api/admin/users")
async def list_users(
    request: Request,
    search: str = "",
    q: str = "",
    type: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 15,
):
    await _require_admin(request)
    query = search or q
    page  = max(1, page)
    limit = min(200, max(1, limit))
    skip  = (page - 1) * limit

    if type:
        try:
            target_roles = [_canonical_staff_role(type)]
        except HTTPException:
            raise
    else:
        target_roles = [r for r in (CANONICAL_ROLES or ()) if r != "admin"]

    mongo_filt: Dict[str, Any] = {}
    if query:
        rx = {"$regex": query, "$options": "i"}
        mongo_filt["$or"] = [
            {"email": rx}, {"full_name": rx}, {"name": rx},
            {"first_name": rx}, {"last_name": rx},
            {"firstName": rx}, {"lastName": rx}, {"club_name": rx},
            {"user_id": rx}, {"unique_id": rx},
        ]
        for _, id_field in (ROLE_COLLECTION_MAP or {}).values():
            if id_field not in {"user_id", "unique_id"}:
                mongo_filt["$or"].append({id_field: rx})
    if status == "active":
        mongo_filt["is_active"] = True
    elif status in ("suspended", "inactive"):
        mongo_filt["is_active"] = False
    elif status == "pending":
        mongo_filt["approval_status"] = "pending"

    all_docs = []
    for role in target_roles:
        ci = _role_col_map().get(role)
        if not ci or ci[0] is None:
            continue
        col, id_field = ci
        try:
            docs = await col.find(mongo_filt).limit(2000).to_list(length=2000)
            for d in docs:
                d["_role"]     = role
                d["_id_field"] = id_field
                all_docs.append(d)
        except Exception:
            pass

    total = len(all_docs)
    all_docs.sort(key=lambda d: d.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    paged = all_docs[skip: skip + limit]

    out = []
    for doc in paged:
        role    = doc.pop("_role", "")
        id_fld  = doc.pop("_id_field", "")
        uid     = doc.get(id_fld) or doc.get("user_id") or str(doc.get("_id", ""))
        is_act  = doc.get("is_active", True)
        out.append({
            "uid":           uid,
            "user_id":       uid,
            "role":          role,
            "type":          role,
            "name":          _display_name(doc),
            "email":         doc.get("email", ""),
            "is_active":     is_act,
            "is_verified":   doc.get("is_verified") or doc.get("email_verified"),
            "status":        "active" if is_act else "suspended",
            "created_at":    _sv(doc.get("created_at")),
            "token_balance": doc.get("token_balance") or doc.get("tokens") or 0,
        })

    return JSONResponse({
        "users":       out,
        "total":       total,
        "page":        page,
        "total_pages": max(1, (total + limit - 1) // limit),
    })


@router.get("/api/admin/users/{uid}")
async def get_user_detail(uid: str, request: Request):
    await _require_admin(request)
    result = await _find_user(uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    doc, role, id_field = result

    tok_col = _token_col(role)
    token_balance, token_expiry = 0, None
    if tok_col is not None:
        wallet = await tok_col.find_one({id_field: doc.get(id_field)})
        if wallet:
            token_balance = wallet.get("balance", 0)
            token_expiry  = _sv(wallet.get("expiry_date"))

    user_uid = doc.get(id_field) or str(doc.get("_id", ""))
    sub = await subscriptions_collection.find_one(
        {"user_id": user_uid, "status": "active"}
    ) if subscriptions_collection is not None else None

    out = _s(doc)
    out.update({
        "role":          role,
        "type":          role,
        "uid":           user_uid,
        "user_id":       user_uid,
        "token_balance": token_balance,
        "token_expiry":  token_expiry,
        "subscription":  _s(sub) if sub else None,
    })
    return JSONResponse(out)


# ORDERING NOTE — FastAPI/Starlette resolves parametric routes in registration order.
# Routes with literal final segments must be registered BEFORE /{uid}/{action} so that
# e.g. POST /users/X/message is not swallowed by the catch-all with action='message'.
# Order here: /message (2-seg literal) → /tokens/credit (3-seg) → /tokens/debit (3-seg)
#             → /{action} catch-all LAST.

@router.post("/api/admin/users/{uid}/message")
async def user_message(uid: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    subject  = (body.get("subject") or "Message from Admin").strip()
    content  = (body.get("message") or body.get("content") or "").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    if not content:
        raise HTTPException(status_code=400, detail="message is required")

    result = await _find_user(uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    doc, role, _ = result
    email = doc.get("email", "")
    name  = _display_name(doc)

    await notifications_collection.insert_one({
        "unique_id":  uid, "user_type": role,
        "title":      subject, "message": content,
        "type":       "admin_message", "sent_by": admin_id,
        "read":       False, "created_at": _now(),
    })
    if email:
        inner = (
            f"<h2 style='margin:0 0 8px;color:#fff'>{subject}</h2>"
            f"<p style='color:#94a3b8;font-size:.88rem'>Hi <strong style='color:#f5b800'>{name}</strong>,</p>"
            f"<p style='color:#e2e8f0;font-size:.9rem;white-space:pre-wrap'>{content}</p>"
        )
        await _send_bg(email, subject, content, _html_email(subject, inner))

    _log(admin_id, "admin", "message_sent", f"Sent message to {role}:{uid}")
    return JSONResponse({"success": True, "message": "Message sent"})


@router.post("/api/admin/users/{uid}/tokens/credit")
async def user_token_credit(uid: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    amount   = int(body.get("amount", 0))
    reason   = (body.get("reason") or "Admin credit").strip()
    requested_role = (body.get("user_type") or body.get("role") or "").strip()
    admin_id = admin.get("admin_id") or admin.get("user_id") or admin.get("unique_id") or str(admin.get("_id", ""))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    res = await _find_user(uid)
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    _, role, _ = res
    if requested_role:
        try:
            if (normalize_role(requested_role) if normalize_role else requested_role.lower()) != role:
                raise HTTPException(status_code=422, detail="Role does not match the target user")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid role")
    try:
        out = await credit_tokens(uid, role, amount, admin_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _log(admin_id, "admin", "token_credit", f"Credited {amount} to {role}:{uid} — {reason}")
    return JSONResponse(out)


@router.post("/api/admin/users/{uid}/tokens/debit")
async def user_token_debit(uid: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    amount   = int(body.get("amount", 0))
    reason   = (body.get("reason") or "Admin debit").strip()
    requested_role = (body.get("user_type") or body.get("role") or "").strip()
    admin_id = admin.get("admin_id") or admin.get("user_id") or admin.get("unique_id") or str(admin.get("_id", ""))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    res = await _find_user(uid)
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    _, role, _ = res
    if requested_role:
        try:
            if (normalize_role(requested_role) if normalize_role else requested_role.lower()) != role:
                raise HTTPException(status_code=422, detail="Role does not match the target user")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid role")
    try:
        out = await deduct_tokens(uid, role, amount, admin_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _log(admin_id, "admin", "token_debit", f"Debited {amount} from {role}:{uid} — {reason}")
    return JSONResponse(out)


@router.post("/api/admin/users/{uid}/{action}")
async def user_action(uid: str, action: str, request: Request):
    """
    General user action catch-all: activate | suspend | unsuspend | verify | delete.
    MUST be registered AFTER all more-specific POST /users/{uid}/... routes above,
    otherwise FastAPI's registration-order routing will shadow them.
    """
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    reason   = (body.get("reason") or "").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    result = await _find_user(uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    doc, role, id_field = result
    col = _role_col_map()[role][0]
    doc_id = doc.get(id_field)

    action = action.lower()
    if action == "delete" and role == "admin" and uid == (admin.get("admin_id") or admin.get("user_id") or admin.get("unique_id")):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if action == "activate":
        await col.update_one({id_field: doc_id}, {"$set": {"is_active": True, "updated_at": _now()}})
        _log(admin_id, "admin", "user_activated", f"Activated {role}:{uid}")
        return JSONResponse({"success": True, "message": "User activated"})

    elif action == "suspend":
        await col.update_one(
            {id_field: doc_id},
            {"$set": {"is_active": False, "suspended_at": _now(), "suspend_reason": reason, "updated_at": _now()}},
        )
        _log(admin_id, "admin", "user_suspended", f"Suspended {role}:{uid}" + (f" — {reason}" if reason else ""))
        return JSONResponse({"success": True, "message": "User suspended"})

    elif action == "unsuspend":
        await col.update_one(
            {id_field: doc_id},
            {"$set": {"is_active": True, "unsuspended_at": _now(), "updated_at": _now()},
             "$unset": {"suspended_at": "", "suspend_reason": ""}},
        )
        _log(admin_id, "admin", "user_unsuspended", f"Unsuspended {role}:{uid}")
        return JSONResponse({"success": True, "message": "User unsuspended"})

    elif action == "verify":
        await col.update_one(
            {id_field: doc_id},
            {"$set": {"is_verified": True, "email_verified": True, "verified_at": _now(), "updated_at": _now()}},
        )
        _log(admin_id, "admin", "user_verified", f"Email verified for {role}:{uid}")
        return JSONResponse({"success": True, "message": "User email verified"})

    elif action == "delete":
        await col.delete_one({id_field: doc_id})
        tok_col = _token_col(role)
        if tok_col is not None:
            await tok_col.delete_many({id_field: doc_id})
        if users_collection is not None:
            await users_collection.delete_many({"$or": [{"user_id": uid}, {"unique_id": uid}]})
        _log(admin_id, "admin", "user_deleted", f"Deleted {role}:{uid}")
        return JSONResponse({"success": True, "message": "User deleted"})

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


# ============================================================
# ── PENDING APPROVALS ────────────────────────────────────────
# ============================================================

@router.get("/api/admin/pending-scouts")
async def pending_scouts(request: Request):
    await _require_admin(request)
    filt = {"approval_status": {"$in": ["pending", None]}}
    docs = await scouts_collection.find(filt).sort("created_at", -1).limit(100).to_list(100)
    return JSONResponse({"scouts": _ss(docs)})


@router.get("/api/admin/pending-players")
async def pending_players(request: Request):
    await _require_admin(request)
    filt = {"approval_status": "pending"}
    docs = await players_collection.find(filt).sort("created_at", -1).limit(100).to_list(100)
    return JSONResponse({"players": _ss(docs)})


async def _approval_update(col, id_field: str, entity_id: str,
                           approved: bool, admin_id: str, reason: str = "") -> bool:
    filt = {id_field: entity_id}
    doc = await col.find_one(filt)
    if not doc:
        return False
    upd = {
        "approval_status": "approved" if approved else "rejected",
        "is_active":       approved,
        "updated_at":      _now(),
    }
    if approved:
        upd["approved_at"] = _now()
        upd["approved_by"] = admin_id
    else:
        upd["rejected_at"]   = _now()
        upd["rejected_by"]   = admin_id
        upd["reject_reason"] = reason
    await col.update_one(filt, {"$set": upd})
    return True


@router.post("/api/admin/approve-scout/{scout_id}")
async def approve_scout(scout_id: str, request: Request):
    admin    = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    ok = await _approval_update(scouts_collection, "scout_id", scout_id, True, admin_id)
    if not ok:
        ok = await _approval_update(dco_collection, "dco_id", scout_id, True, admin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Scout not found")
    _log(admin_id, "admin", "scout_approved", f"Approved scout: {scout_id}")
    return JSONResponse({"success": True, "message": "Scout approved"})


@router.post("/api/admin/reject-scout/{scout_id}")
async def reject_scout(scout_id: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    reason   = (body.get("reason") or "Application not approved").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    ok = await _approval_update(scouts_collection, "scout_id", scout_id, False, admin_id, reason)
    if not ok:
        ok = await _approval_update(dco_collection, "dco_id", scout_id, False, admin_id, reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Scout not found")
    _log(admin_id, "admin", "scout_rejected", f"Rejected scout: {scout_id} — {reason}")
    return JSONResponse({"success": True, "message": "Scout rejected"})


@router.post("/api/admin/approve-player/{player_id}")
async def approve_player(player_id: str, request: Request):
    admin    = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    ok = await _approval_update(players_collection, "player_id", player_id, True, admin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Player not found")
    _log(admin_id, "admin", "player_approved", f"Approved player: {player_id}")
    return JSONResponse({"success": True, "message": "Player approved"})


@router.post("/api/admin/reject-player/{player_id}")
async def reject_player(player_id: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    reason   = (body.get("reason") or "Application not approved").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    ok = await _approval_update(players_collection, "player_id", player_id, False, admin_id, reason)
    if not ok:
        raise HTTPException(status_code=404, detail="Player not found")
    _log(admin_id, "admin", "player_rejected", f"Rejected player: {player_id} — {reason}")
    return JSONResponse({"success": True, "message": "Player rejected"})


# ============================================================
# ── STAFF / SUB-ADMINS ───────────────────────────────────────
# ============================================================
# Canonical staff roles created by the admin dashboard.
# CO/CC profiles live in their existing role collections so their
# dedicated dashboards can authenticate them without migration logic.
# Sub-admin/content-manager profiles live in admins_collection, but keep
# their real role value instead of being incorrectly stored as "admin".

_STAFF_ROLE_ALIASES = {
    "communications_officer": "communication_officer",
    "co": "communication_officer",
    "customer_care_officer": "customer_care",
    "cc": "customer_care",
    "subadmin": "sub_admin",
}


def _canonical_staff_role(value: Any) -> str:
    """Normalize staff-role aliases through main.py's canonical role service."""
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    key = _STAFF_ROLE_ALIASES.get(key, key)
    if normalize_role is None:
        return key
    try:
        return normalize_role(key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _staff_collection(role: str):
    canonical = _canonical_staff_role(role)
    if role_collection is None:
        return _role_col_map().get(canonical, (None, ""))[0]
    try:
        return role_collection(canonical)
    except Exception:
        return None


def _staff_id_field(role: str) -> str:
    canonical = _canonical_staff_role(role)
    if ROLE_COLLECTION_MAP and canonical in ROLE_COLLECTION_MAP:
        return ROLE_COLLECTION_MAP[canonical][1]
    return "user_id"


def _validate_staff_password(password: str, email: str) -> None:
    """Validate the dashboard's module-specific password complexity requirements."""
    if not password or password != password.strip():
        raise HTTPException(status_code=422, detail="Password cannot start or end with spaces.")
    if len(password) < 10:
        raise HTTPException(status_code=422, detail="Password must be at least 10 characters long.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one special character.")
    local = (email or "").split("@")[0].lower()
    if local and local in password.lower():
        raise HTTPException(status_code=422, detail="Password cannot contain your email address.")


async def _staff_insert_document(role: str, body: dict, actor: dict) -> tuple[str, dict]:
    """Create staff through main.py's canonical platform identity service."""
    role = _canonical_staff_role(role)
    allowed = {"communication_officer", "customer_care", "content_manager", "sub_admin", "supervisor"}
    if role not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported staff role: {role}")
    if create_platform_user is None:
        raise HTTPException(status_code=503, detail="Canonical user creation service not ready")

    name = (body.get("name") or body.get("full_name") or "").strip()
    email = normalize_email(body.get("email", "")) if normalize_email else str(body.get("email") or "").strip().lower()
    password = str(body.get("password") or "")
    state = (body.get("state") or body.get("location") or "").strip()
    lga = (body.get("lga") or "").strip()
    city = (body.get("city") or "").strip()
    phone = (body.get("phone") or "").strip()
    status = (body.get("status") or "active").strip().lower()
    if not name or not email or not password or not state:
        raise HTTPException(status_code=400, detail="name, email, password, and state are required")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    _validate_staff_password(password, email)
    if status not in {"active", "pending", "suspended", "inactive"}:
        raise HTTPException(status_code=422, detail="Invalid staff status")

    permissions = body.get("permissions")
    if permissions is not None and not isinstance(permissions, list):
        raise HTTPException(status_code=422, detail="permissions must be an array")
    if permissions is not None:
        permissions = sorted({str(x).strip() for x in permissions if str(x).strip()})
    else:
        permissions = []

    parts = name.split()
    first_name = parts[0] if parts else name
    last_name = parts[-1] if len(parts) > 1 else ""
    middle_name = " ".join(parts[1:-1]) if len(parts) > 2 else ""
    actor_id = actor.get("admin_id") or actor.get("user_id") or actor.get("unique_id") or str(actor.get("_id", ""))

    extra_fields = {
        "name": name,
        "full_name": name,
        "phone": phone,
        "country": "Nigeria",
        "state": state,
        "location": state,
        "region": state,
        "lga": lga,
        "city": city,
        "permissions": permissions,
        "is_active": status == "active",
        "account_status": status,
        "email_verified": True,
        "is_verified": True,
        "approval_status": "approved",
        "created_by": actor_id,
        "created_via": "admin_dashboard",
    }
    try:
        doc = await create_platform_user(
            role=role,
            email=email,
            password=password,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            extra_fields=extra_fields,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="An account with this identity already exists") from exc

    id_field = _staff_id_field(role)
    user_id = doc.get(id_field) or doc.get("user_id") or doc.get("unique_id")
    if not user_id:
        raise HTTPException(status_code=500, detail="Canonical user creation returned no public ID")
    if users_collection is not None:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"email_verified": True, "is_active": status == "active", "updated_at": _now()}},
        )
    return str(user_id), doc

@router.get("/api/admin/sub-admins")
async def list_sub_admins(
    request: Request,
    page: int = 1,
    limit: int = 15,
    search: str = "",
    role: str = "",
    state: str = "",
):
    await _require_admin(request)
    page = max(1, page)
    limit = max(1, min(limit, 100))
    search = (search or "").strip().lower()
    role_filter = _canonical_staff_role(role) if role else ""
    state_filter = (state or "").strip()

    role_sources = [
        (r, _role_col_map().get(r, (None, ""))[0])
        for r in ("communication_officer", "customer_care", "content_manager", "sub_admin", "supervisor")
    ]
    docs = []
    for source_role, col in role_sources:
        if col is None or (role_filter and role_filter != source_role):
            continue
        query: Dict[str, Any] = {"role": source_role}
        # Legacy CO/CC rows may not have role set; accept their role-specific IDs.
        if source_role == "communication_officer":
            query = {"$or": [{"role": source_role}, {"co_id": {"$exists": True}}]}
        elif source_role == "customer_care":
            query = {"$or": [{"role": source_role}, {"cc_id": {"$exists": True}}]}
        elif source_role == "supervisor":
            query = {"$or": [{"role": source_role}, {"supervisor_id": {"$exists": True}}]}
        if state_filter:
            query = {"$and": [query, {"$or": [{"state": state_filter}, {"location": state_filter}, {"region": state_filter}]}]}
        if search:
            rx = {"$regex": search, "$options": "i"}
            query = {"$and": [query, {"$or": [{"name": rx}, {"full_name": rx}, {"email": rx}, {"user_id": rx}, {"unique_id": rx}, {"co_id": rx}, {"cc_id": rx}, {"cm_id": rx}, {"sub_admin_id": rx}, {"supervisor_id": rx}]}]}
        rows = await col.find(query, {"password": 0}).to_list(1000)
        for row in rows:
            row["role"] = _canonical_staff_role(row.get("role") or source_role)
            row["state"] = row.get("state") or row.get("location") or row.get("region") or ""
            row["user_id"] = row.get("user_id") or row.get("unique_id") or row.get(_staff_id_field(source_role)) or str(row.get("_id", "")) or str(row.get("_id", ""))
            docs.append(row)

    docs.sort(key=lambda d: d.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    total = len(docs)
    skip = (page - 1) * limit
    page_docs = docs[skip:skip + limit]
    return JSONResponse({
        "admins": _ss(page_docs),
        "sub_admins": _ss(page_docs),
        "staff": _ss(page_docs),
        "total": total,
        "page": page,
        "total_pages": max(1, (total + limit - 1) // limit),
    })


@router.post("/api/admin/sub-admins")
async def create_sub_admin(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    role = _canonical_staff_role(body.get("role") or body.get("staff_role") or body.get("user_type") or "sub_admin")
    user_id, doc = await _staff_insert_document(role, body, admin)

    # Never return password/hash fields to the browser.
    safe = dict(doc)
    safe.pop("password", None)
    safe.pop("password_hash", None)
    safe.pop("hashed_password", None)
    return JSONResponse({
        "success": True,
        "created": True,
        "user_id": user_id,
        "sub_admin_id": user_id if role == "sub_admin" else None,
        "cm_id": user_id if role == "content_manager" else None,
        "role": role,
        "staff": _s(safe),
        "message": f"{role.replace('_', ' ').title()} created successfully",
    }, status_code=201)


@router.delete("/api/admin/sub-admins/{admin_id_param}")
async def delete_sub_admin(admin_id_param: str, request: Request):
    admin = await _require_admin(request)
    current_id = admin.get("admin_id") or str(admin.get("_id", ""))
    if admin_id_param == current_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Search all staff stores because the frontend action operates on the
    # unified staff list rather than only the admins collection.
    sources = [
        (role, *_role_col_map().get(role, (None, "")))
        for role in ("communication_officer", "customer_care", "content_manager", "sub_admin", "supervisor")
    ]
    for role, col, id_field in sources:
        if col is None:
            continue
        doc = await col.find_one({"$or": [{id_field: admin_id_param}, {"user_id": admin_id_param}, {"_id": _try_oid(admin_id_param)}]})
        if doc:
            await col.delete_one({"_id": doc["_id"]})
            canonical_id = doc.get(id_field) or doc.get("user_id") or doc.get("unique_id") or admin_id_param
            if users_collection is not None:
                await users_collection.delete_many({"$or": [{"user_id": canonical_id}, {"unique_id": canonical_id}]})
            return JSONResponse({"success": True, "message": f"{role.replace('_', ' ').title()} deleted"})
    raise HTTPException(status_code=404, detail="Staff account not found")


# ============================================================
# ── PAYMENT RECEIPTS ────────────────────────────────────────
# ============================================================

@router.get("/api/admin/payment-receipts")
async def list_payment_receipts(
    request: Request,
    status: str = "",
    page: int = 1,
    limit: int = 50,
):
    await _require_admin(request)
    filt = {}
    if status and status != "all":
        filt["status"] = status
    total = await payment_intents_collection.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await payment_intents_collection.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return JSONResponse({"receipts": _ss(docs), "intents": _ss(docs), "total": total, "page": page})


@router.get("/api/admin/payment-receipts/{tx_ref}")
async def get_receipt(tx_ref: str, request: Request):
    await _require_admin(request)
    doc = await payment_intents_collection.find_one({"tx_ref": tx_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return JSONResponse(_s(doc))


@router.post("/api/admin/payment-receipts/{tx_ref}/approve")
async def approve_receipt(tx_ref: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    note     = (body.get("note") or body.get("reason") or "").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    doc = await payment_intents_collection.find_one({"tx_ref": tx_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if doc.get("status") not in ("pending_review", "pending"):
        raise HTTPException(status_code=400, detail="Receipt is not pending review")

    await payment_intents_collection.update_one(
        {"tx_ref": tx_ref},
        {"$set": {"status": "active", "approved_at": _now(), "approved_by": admin_id, "admin_note": note, "updated_at": _now()}},
    )

    user_id  = doc.get("user_id") or doc.get("player_id") or doc.get("scout_id") or doc.get("club_id")
    user_role = doc.get("user_type") or doc.get("role") or ""
    plan = doc.get("plan") or doc.get("subscription_plan") or ""
    if user_id and plan and subscriptions_collection is not None:
        days = 30
        for key, d in [("annual", 365), ("yearly", 365), ("6month", 180), ("6_month", 180), ("monthly", 30)]:
            if key in plan.lower():
                days = d
                break
        expires_at = _now() + timedelta(days=days)
        await subscriptions_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "user_type": user_role, "plan": plan, "status": "active",
                      "started_at": _now(), "expires_at": expires_at, "tx_ref": tx_ref, "updated_at": _now()}},
            upsert=True,
        )

    email = doc.get("email", "")
    if email:
        inner = (
            "<h2 style='color:#22c55e'>Payment Approved!</h2>"
            f"<p style='color:#94a3b8'>Your payment <strong style='color:#ffd700'>{tx_ref}</strong> has been verified. "
            "Your subscription is now active.</p>"
        )
        await _send_bg(email, "EnejiStats — Payment Approved",
                       f"Your payment {tx_ref} has been approved.", _html_email("EnejiStats — Payment Approved", inner))

    _log(admin_id, "admin", "receipt_approved", f"Approved receipt: {tx_ref}")
    return JSONResponse({"success": True, "message": "Receipt approved"})


@router.post("/api/admin/payment-receipts/{tx_ref}/reject")
async def reject_receipt(tx_ref: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    note     = (body.get("note") or body.get("reason") or "").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    doc = await payment_intents_collection.find_one({"tx_ref": tx_ref})
    if not doc:
        raise HTTPException(status_code=404, detail="Receipt not found")

    await payment_intents_collection.update_one(
        {"tx_ref": tx_ref},
        {"$set": {"status": "rejected", "rejected_at": _now(), "rejected_by": admin_id, "admin_note": note, "updated_at": _now()}},
    )
    email = doc.get("email", "")
    if email:
        inner = (
            "<h2 style='color:#ef4444'>Payment Not Verified</h2>"
            f"<p style='color:#94a3b8'>Your payment <strong style='color:#ffd700'>{tx_ref}</strong> "
            "could not be verified.</p>"
            + (f"<p style='color:#94a3b8'><strong>Note:</strong> {note}</p>" if note else "")
        )
        await _send_bg(email, "EnejiStats — Payment Update",
                       f"Your payment {tx_ref} was rejected.", _html_email("EnejiStats — Payment Update", inner))

    _log(admin_id, "admin", "receipt_rejected", f"Rejected receipt: {tx_ref}")
    return JSONResponse({"success": True, "message": "Receipt rejected"})


# ============================================================
# ── PAYMENT INTENTS ─────────────────────────────────────────
# ============================================================

@router.get("/api/admin/payment-intents")
async def admin_list_payment_intents(
    request: Request,
    status: Optional[str] = None,
    limit:  int           = 200,
    page:   int           = 1,
    month:  Optional[str] = None,
):
    """
    List payment intents (awaiting or processed).

    Response: { total, intents: [...], payments: [...] }
    """
    await _require_admin(request)
    col = _require_collection(payment_intents_collection, "payment_intents_collection")

    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    month_filter = _build_month_filter(month)
    if month_filter:
        query["created_at"] = month_filter

    total = await col.count_documents(query)
    skip  = (page - 1) * limit
    docs  = await col.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    intents = [_serialize(d) for d in docs]
    return JSONResponse({"total": total, "intents": intents, "payments": intents})


def _payment_intent_action_route(action: str):
    """
    Factory that returns a POST handler for a payment intent action.
    action: approve | reject | mark-pnr | confirm-payment
    """
    async def _handler(tx_ref: str, body: PaymentActionBody, request: Request):
        admin = await _require_admin(request)
        admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

        doc = await _find_payment(tx_ref)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Payment '{tx_ref}' not found")

        if action == "approve":
            new_status  = "approved"
            notif_title = "Payment Approved"
            notif_msg   = "Your payment has been approved. Your subscription or tokens have been activated."
        elif action == "reject":
            new_status  = "rejected"
            notif_title = "Payment Rejected"
            notif_msg   = f"Your payment has been rejected. Reason: {body.reason or 'N/A'}"
        elif action == "mark-pnr":
            new_status  = "payment_not_received"
            notif_title = "Payment Not Received"
            notif_msg   = "We could not confirm your payment. Please retry or contact support."
        elif action == "confirm-payment":
            new_status  = "approved"
            notif_title = "Payment Confirmed"
            notif_msg   = "Your payment has been confirmed and your account has been activated."
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        update: Dict[str, Any] = {
            "$set": {
                "status":     new_status,
                "updated_at": _now_utc(),
                "admin_id":   admin_id,
            }
        }
        if body.reason:
            update["$set"]["rejection_reason"] = body.reason
        if action in ("approve", "confirm-payment"):
            update["$set"]["approved_at"] = _now_utc()
        if action == "reject":
            update["$set"]["rejected_at"] = _now_utc()

        updated = await _update_payment(tx_ref, update)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Payment '{tx_ref}' not found")

        user_id   = doc.get("user_id") or doc.get("club_id") or doc.get("player_id") or ""
        user_type = doc.get("user_type") or doc.get("role") or ""
        if user_id and user_type:
            await _send_notification(
                user_id, user_type, notif_title, notif_msg,
                f"payment_{action.replace('-', '_')}",
            )

        return JSONResponse({
            "success": True,
            "tx_ref":  tx_ref,
            "status":  new_status,
            "action":  action,
        })

    _handler.__name__ = f"payment_intent_{action.replace('-', '_')}"
    return _handler


@router.post("/api/admin/payment-intents/{tx_ref}/approve")
async def payment_intent_approve(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("approve")(tx_ref, body, request)


@router.post("/api/admin/payment-intents/{tx_ref}/reject")
async def payment_intent_reject(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("reject")(tx_ref, body, request)


@router.post("/api/admin/payment-intents/{tx_ref}/mark-pnr")
async def payment_intent_mark_pnr(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("mark-pnr")(tx_ref, body, request)


@router.post("/api/admin/payment-intents/{tx_ref}/confirm-payment")
async def payment_intent_confirm_payment(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("confirm-payment")(tx_ref, body, request)


# ── /api/admin/payments/{tx_ref}/… aliases ──────────────────
# The frontend falls back to these if the /payment-intents/ route fails.

@router.post("/api/admin/payments/{tx_ref}/approve")
async def payment_approve_alias(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("approve")(tx_ref, body, request)


@router.post("/api/admin/payments/{tx_ref}/reject")
async def payment_reject_alias(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("reject")(tx_ref, body, request)


@router.post("/api/admin/payments/{tx_ref}/mark-pnr")
async def payment_mark_pnr_alias(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("mark-pnr")(tx_ref, body, request)


@router.post("/api/admin/payments/{tx_ref}/confirm-payment")
async def payment_confirm_payment_alias(tx_ref: str, body: PaymentActionBody, request: Request):
    return await _payment_intent_action_route("confirm-payment")(tx_ref, body, request)


# ============================================================
# ── SUBSCRIPTIONS ────────────────────────────────────────────
# ============================================================

@router.get("/api/admin/subscriptions")
async def list_subscriptions(
    request: Request,
    status: str = "",
    user_type: str = "",
    page: int = 1,
    limit: int = 15,
):
    await _require_admin(request)
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if user_type:
        filt["user_type"] = user_type
    total = await subscriptions_collection.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await subscriptions_collection.find(filt).sort("started_at", -1).skip(skip).limit(limit).to_list(limit)
    return JSONResponse({
        "subscriptions": _ss(docs),
        "total":         total,
        "page":          page,
        "total_pages":   max(1, (total + limit - 1) // limit),
    })


# NOTE: /subscriptions/grant and /subscriptions/send-trial-warnings must be
# registered BEFORE /subscriptions/{uid}/extend to avoid FastAPI treating
# "grant" and "send-trial-warnings" as a {uid} path parameter.

@router.post("/api/admin/subscriptions/grant")
async def grant_subscription(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    uid      = (body.get("user_id") or body.get("uid") or "").strip()
    plan     = (body.get("plan") or "").strip()
    days     = int(body.get("days") or 30)
    note     = (body.get("note") or "Admin grant").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    if not uid or not plan:
        raise HTTPException(status_code=400, detail="user_id and plan are required")
    result = await _find_user(uid)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    _, role, _ = result
    expires_at = _now() + timedelta(days=days)
    await subscriptions_collection.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "user_type": role, "plan": plan, "status": "active",
                  "started_at": _now(), "expires_at": expires_at,
                  "granted_by": admin_id, "grant_note": note, "updated_at": _now()}},
        upsert=True,
    )
    if subscription_audit_collection is not None:
        await subscription_audit_collection.insert_one({
            "user_id": uid, "user_type": role, "action": "grant",
            "plan": plan, "days": days, "note": note, "admin_id": admin_id, "created_at": _now(),
        })
    _log(admin_id, "admin", "sub_granted", f"Granted {plan} ({days}d) to {uid}")
    return JSONResponse({"success": True, "message": "Subscription granted", "expires_at": _sv(expires_at)})


@router.post("/api/admin/subscriptions/send-trial-warnings")
async def send_trial_warnings(request: Request):
    admin    = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    async def _inner():
        try:
            for col_name, (col, id_field) in _role_col_map().items():
                if col is None or col_name == "admin":
                    continue
                cursor = col.find({"subscription_status": "trial"})
                async for doc in cursor:
                    email = doc.get("email", "")
                    name  = _display_name(doc)
                    trial_ends = doc.get("trial_ends_at") or _now() + timedelta(days=0)
                    try:
                        if isinstance(trial_ends, str):
                            trial_ends = datetime.fromisoformat(trial_ends.replace("Z", "+00:00"))
                        if trial_ends.tzinfo is None:
                            trial_ends = trial_ends.replace(tzinfo=timezone.utc)
                        days_left = max(0, (trial_ends - _now()).days)
                    except Exception:
                        days_left = 0
                    if email and send_email:
                        inner = (
                            f"<h2 style='color:#f59e0b'>{days_left} Day{'s' if days_left != 1 else ''} Left on Your Free Trial</h2>"
                            f"<p style='color:#94a3b8'>Hi <strong style='color:#f5b800'>{name}</strong>,<br/>"
                            "Your EnejiStats free trial is ending soon. Subscribe to keep access.</p>"
                        )
                        subj = f"EnejiStats — Trial Expires in {days_left} Day{'s' if days_left != 1 else ''}"
                        asyncio.ensure_future(send_email(email, subj, subj, _html_email(subj, inner)))
        except Exception as exc:
            if logger:
                logger.error("[trial_warnings] Error: %s", exc)

    asyncio.ensure_future(_inner())
    _log(admin_id, "admin", "trial_warnings_sent", "Trial warning emails dispatched")
    return JSONResponse({"success": True, "message": "Trial warning emails dispatched"})


@router.post("/api/admin/subscriptions/{uid}/extend")
async def extend_subscription(uid: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    days     = int(body.get("days") or 0)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")
    sub = await subscriptions_collection.find_one({"user_id": uid})
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")
    current = sub.get("expires_at")
    if current:
        if isinstance(current, str):
            try:
                current = datetime.fromisoformat(current.replace("Z", "+00:00"))
            except Exception:
                current = _now()
        if getattr(current, "tzinfo", None) is None:
            current = current.replace(tzinfo=timezone.utc)
        base = max(current, _now())
    else:
        base = _now()
    new_expiry = base + timedelta(days=days)
    await subscriptions_collection.update_one(
        {"user_id": uid},
        {"$set": {"expires_at": new_expiry, "extended_by": admin_id,
                  "extended_at": _now(), "status": "active", "updated_at": _now()}},
    )
    _log(admin_id, "admin", "sub_extended", f"Extended sub for {uid} by {days}d")
    return JSONResponse({"success": True, "message": f"Extended by {days} days", "expires_at": _sv(new_expiry)})


@router.post("/api/admin/subscriptions/{uid}/cancel")
async def cancel_subscription(uid: str, request: Request):
    admin    = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    sub = await subscriptions_collection.find_one({"user_id": uid})
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found")
    await subscriptions_collection.update_one(
        {"user_id": uid},
        {"$set": {"status": "cancelled", "cancelled_at": _now(), "cancelled_by": admin_id, "updated_at": _now()}},
    )
    _log(admin_id, "admin", "sub_cancelled", f"Cancelled sub for {uid}")
    return JSONResponse({"success": True, "message": "Subscription cancelled"})


@router.get("/api/admin/subscriptions/receipts")
async def subscriptions_receipts(request: Request, status: str = "", limit: int = 15):
    await _require_admin(request)
    filt = {}
    if status:
        filt["status"] = status
    docs = await payment_intents_collection.find(filt).sort("created_at", -1).limit(limit).to_list(limit)
    return JSONResponse({"intents": _ss(docs), "receipts": _ss(docs)})


# ============================================================
# ── TOKENS ──────────────────────────────────────────────────
# ============================================================

@router.get("/api/admin/tokens/overview")
async def tokens_overview(request: Request):
    await _require_admin(request)

    async def _stats(col):
        if col is None:
            return {"wallets": 0, "balance": 0}
        try:
            agg = await col.aggregate([
                {"$group": {"_id": None, "total": {"$sum": "$balance"}, "count": {"$sum": 1}}}
            ]).to_list(1)
            if agg:
                return {"wallets": agg[0]["count"], "balance": agg[0]["total"]}
        except Exception:
            pass
        return {"wallets": 0, "balance": 0}

    p, c, s, d, a = await asyncio.gather(
        _stats(player_tokens_collection),
        _stats(club_tokens_collection),
        _stats(scout_tokens_collection),
        _stats(dco_tokens_collection),
        _stats(agent_tokens_collection),
    )
    total = p["balance"] + c["balance"] + s["balance"] + d["balance"] + a["balance"]
    return JSONResponse({
        "total_tokens_in_circulation": total,
        "total_player_tokens":         p["balance"],
        "total_club_tokens":           c["balance"],
        "total_scout_tokens":          s["balance"],
        "scout_tokens":                s["balance"],
        "total_dco_tokens":            d["balance"],
        "total_agent_tokens":          a["balance"],
        "agent_tokens":                a["balance"],
        "by_type": {
            "player": p["balance"],
            "club":   c["balance"],
            "scout":  s["balance"],
            "dco":    d["balance"],
            "agent":  a["balance"],
        },
        "by_role": {
            "player": p,
            "club":   c,
            "scout":  s,
            "dco":    d,
            "agent":  a,
        },
        "wallet_count": p["wallets"] + c["wallets"] + s["wallets"] + d["wallets"] + a["wallets"],
    })


@router.get("/api/admin/tokens/history")
async def tokens_history(
    request: Request,
    limit: int = 500,
    sort: str = "desc",
    type: str = "",
):
    await _require_admin(request)
    limit = min(2000, max(1, limit))
    filt: Dict[str, Any] = {}
    if type in ("credit", "debit"):
        filt["type"] = type

    sort_dir = -1 if sort in ("desc", "newest") else 1

    # Pull from both transaction collections
    all_txns = []
    for col in [c for c in [transactions_collection, token_transactions_collection] if c is not None]:
        try:
            docs = await col.find(filt).sort("created_at", sort_dir).limit(limit).to_list(limit)
            all_txns.extend(docs)
        except Exception:
            pass

    # Deduplicate by _id
    seen, unique = set(), []
    for doc in all_txns:
        key = str(doc.get("_id", id(doc)))
        if key not in seen:
            seen.add(key)
            unique.append(doc)
    unique.sort(key=lambda d: d.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=(sort_dir == -1))

    return JSONResponse({"transactions": _ss(unique[:limit]), "history": _ss(unique[:limit]), "total": len(unique)})


@router.post("/api/admin/tokens/credit")
async def standalone_token_credit(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    uid      = (body.get("user_id") or body.get("uid") or "").strip()
    amount   = int(body.get("amount") or 0)
    reason   = (body.get("reason") or "Admin credit").strip()
    requested_role = (body.get("user_type") or body.get("role") or "").strip()
    admin_id = admin.get("admin_id") or admin.get("user_id") or admin.get("unique_id") or str(admin.get("_id", ""))
    if not uid or amount <= 0:
        raise HTTPException(status_code=400, detail="user_id and positive amount are required")
    res = await _find_user(uid)
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    _, role, _ = res
    if requested_role:
        try:
            if (normalize_role(requested_role) if normalize_role else requested_role.lower()) != role:
                raise HTTPException(status_code=422, detail="Role does not match the target user")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid role")
    try:
        out = await credit_tokens(uid, role, amount, admin_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _log(admin_id, "admin", "token_credit", f"Credited {amount} to {role}:{uid} — {reason}")
    return JSONResponse(out)


@router.post("/api/admin/tokens/debit")
async def standalone_token_debit(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    uid      = (body.get("user_id") or body.get("uid") or "").strip()
    amount   = int(body.get("amount") or 0)
    reason   = (body.get("reason") or "Admin debit").strip()
    requested_role = (body.get("user_type") or body.get("role") or "").strip()
    admin_id = admin.get("admin_id") or admin.get("user_id") or admin.get("unique_id") or str(admin.get("_id", ""))
    if not uid or amount <= 0:
        raise HTTPException(status_code=400, detail="user_id and positive amount are required")
    res = await _find_user(uid)
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    _, role, _ = res
    if requested_role:
        try:
            if (normalize_role(requested_role) if normalize_role else requested_role.lower()) != role:
                raise HTTPException(status_code=422, detail="Role does not match the target user")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid role")
    try:
        out = await deduct_tokens(uid, role, amount, admin_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _log(admin_id, "admin", "token_debit", f"Debited {amount} from {role}:{uid} — {reason}")
    return JSONResponse(out)


@router.get("/api/admin/entity-details/{role}/{query}")
async def entity_details(role: str, query: str, request: Request):
    await _require_admin(request)
    try:
        canonical_role = normalize_role(role) if normalize_role else role.strip().lower()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
    ci = _role_col_map().get(canonical_role)
    if not ci or ci[0] is None:
        raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
    col, id_field = ci
    doc = await col.find_one({id_field: query})
    if not doc:
        doc = await col.find_one({"email": {"$regex": f"^{query}$", "$options": "i"}})
    if not doc:
        doc = await col.find_one({"$or": [
            {"full_name": {"$regex": query, "$options": "i"}},
            {"name":      {"$regex": query, "$options": "i"}},
        ]})
    if not doc:
        raise HTTPException(status_code=404, detail="Entity not found")
    uid = doc.get(id_field) or str(doc.get("_id", ""))
    tok_col = _token_col(canonical_role)
    wallet = await tok_col.find_one({id_field: uid}) if tok_col is not None else None
    out = _s(doc)
    out["token_balance"] = wallet.get("balance", 0) if wallet else 0
    out["uid"] = uid
    return JSONResponse({"entity": out, "user": out})


# ============================================================
# ── DCO TIER MANAGEMENT ──────────────────────────────────────
# ============================================================

@router.get("/api/admin/tier-management")
async def tier_management(request: Request):
    await _require_admin(request)
    settings = await platform_settings_collection.find_one({"key": "dco_tiers"}) if platform_settings_collection is not None else None
    dcos_cursor = dco_collection.find({}).sort("created_at", -1).limit(500) if dco_collection is not None else None
    dcos = _ss(await dcos_cursor.to_list(500)) if dcos_cursor else []
    default_rates = {
        "tier1": {"grassroots": 1500, "academy": 2000, "university": 2000, "semi_professional": 2500, "professional": 3000, "club": 3500},
        "tier2": {"grassroots": 2000, "academy": 2500, "university": 2500, "semi_professional": 3000, "professional": 3500, "club": 4000},
        "tier3": {"grassroots": 2500, "academy": 3000, "university": 3000, "semi_professional": 3500, "professional": 4000, "club": 5000},
    }
    return JSONResponse({
        "dcos":  dcos,
        "tiers": (settings or {}).get("tiers", {}),
        "rates": (settings or {}).get("rates", default_rates),
    })


@router.patch("/api/admin/data-scouts/{scout_id}/tier")
async def change_dco_tier(scout_id: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    direction = (body.get("direction") or "").lower()  # "up" or "down"
    admin_id  = admin.get("admin_id") or str(admin.get("_id", ""))

    doc = await dco_collection.find_one({"dco_id": scout_id}) if dco_collection is not None else None
    if not doc:
        doc = await scouts_collection.find_one({"scout_id": scout_id}) if scouts_collection is not None else None
        col, id_field = scouts_collection, "scout_id"
    else:
        col, id_field = dco_collection, "dco_id"

    if not doc:
        raise HTTPException(status_code=404, detail="Scout/DCO not found")

    current_tier = int(doc.get("tier") or 1)
    if direction == "up":
        new_tier = min(current_tier + 1, 3)
    elif direction == "down":
        new_tier = max(current_tier - 1, 1)
    else:
        new_tier = int(body.get("tier") or current_tier)
        new_tier = max(1, min(3, new_tier))

    await col.update_one(
        {id_field: scout_id},
        {"$set": {"tier": new_tier, "tier_updated_by": admin_id, "tier_updated_at": _now(), "updated_at": _now()}},
    )
    _log(admin_id, "admin", "tier_changed", f"Changed tier for {scout_id}: {current_tier} → {new_tier}")
    return JSONResponse({"success": True, "tier": new_tier, "message": f"Tier updated to {new_tier}"})


# ============================================================
# ── BROADCASTS / MESSAGES ───────────────────────────────────
# ============================================================

@router.get("/api/admin/messages/history")
async def messages_history(request: Request, limit: int = 20):
    await _require_admin(request)
    limit = min(500, max(1, limit))
    # broadcasts_collection is the canonical store for admin messages
    docs = await broadcasts_collection.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    out = []
    for d in _ss(docs):
        # Normalise fields to what the frontend expects
        d.setdefault("title",   d.get("subject", ""))
        d.setdefault("target",  d.get("recipient_type", "all"))
        d.setdefault("sent_at", d.get("created_at"))
        out.append(d)
    return JSONResponse({"messages": out, "total": len(out)})


@router.post("/api/admin/messages/send")
async def messages_send(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    title   = (body.get("title") or body.get("subject") or "").strip()
    message = (body.get("message") or body.get("content") or "").strip()
    target  = (body.get("target_group") or body.get("recipient_type") or "all").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    if not title or not message:
        raise HTTPException(status_code=400, detail="title and message are required")

    doc = {
        "subject":        title,
        "title":          title,
        "content":        message,
        "message":        message,
        "recipient_type": target,
        "target":         target,
        "sent_by":        admin_id,
        "sent_at":        _now(),
        "created_at":     _now(),
    }
    res = await broadcasts_collection.insert_one(doc)
    asyncio.ensure_future(_broadcast_emails(title, message, target, admin_id))
    _log(admin_id, "admin", "broadcast_sent", f"Broadcast '{title}' → {target}")
    return JSONResponse({"success": True, "id": str(res.inserted_id), "message": "Broadcast sent"}, status_code=201)


async def _broadcast_emails(title: str, content: str, target: str, admin_id: str) -> None:
    try:
        inner = (
            f"<h2 style='color:#fff'>{title}</h2>"
            f"<p style='color:#e2e8f0;white-space:pre-wrap'>{content}</p>"
        )
        html_body = _html_email(title, inner)
        role_map = {
            "players":     players_collection,
            "clubs":       clubs_collection,
            "scouts":      scouts_collection,
            "agents":      agents_collection,
            "dcos":        dco_collection,
            "supervisors": supervisors_collection,
        }
        cols = list(role_map.values()) if target == "all" else [role_map.get(target)]
        emails: List[str] = []
        for col in cols:
            if col is None:
                continue
            docs = await col.find({}, {"email": 1}).to_list(10000)
            for d in docs:
                em = d.get("email", "")
                if em and em not in emails:
                    emails.append(em)
        for em in emails:
            if send_email:
                try:
                    await send_email(em, title, content, html_body)
                except Exception:
                    pass
    except Exception as exc:
        if logger:
            logger.error("[broadcast_emails] %s", exc)


# ============================================================
# ── SUPPORT TICKETS ─────────────────────────────────────────
# ============================================================

@router.get("/api/admin/support/tickets")
async def support_tickets_list(
    request: Request,
    status: str = "",
    page: int = 1,
    limit: int = 15,
):
    await _require_admin(request)
    filt = {}
    if status:
        filt["status"] = status
    total = await support_tickets_collection.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await support_tickets_collection.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    open_c     = await support_tickets_collection.count_documents({"status": "open"})
    in_prog_c  = await support_tickets_collection.count_documents({"status": "in_progress"})
    resolved_c = await support_tickets_collection.count_documents({"status": "resolved"})
    enriched: List[dict] = []
    for doc in _ss(docs):
        # Normalise: surface user_role at top level if stored under a different key
        if not doc.get("user_role"):
            doc["user_role"] = doc.get("role") or doc.get("user_type") or ""
        # If still missing, attempt a fast user lookup (best-effort, non-blocking)
        if not doc.get("user_role"):
            uid = doc.get("user_id") or ""
            if uid:
                try:
                    res = await _find_user(uid)
                    if res:
                        _, _role, _ = res
                        doc["user_role"] = _role
                except Exception:
                    pass
        enriched.append(doc)
    return JSONResponse({
        "tickets":     enriched,
        "total":       total,
        "page":        page,
        "total_pages": max(1, (total + limit - 1) // limit),
        "stats": {"open": open_c, "in_progress": in_prog_c, "resolved": resolved_c},
    })


@router.get("/api/admin/support/tickets/{ticket_id}")
async def support_ticket_detail(ticket_id: str, request: Request):
    await _require_admin(request)
    doc = await _get_ticket(ticket_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msgs = []
    if support_messages_collection is not None:
        raw = await support_messages_collection.find({"ticket_id": ticket_id}).sort("created_at", 1).to_list(500)
        msgs = _ss(raw)
    out = _s(doc)
    out["messages"] = msgs
    return JSONResponse({"ticket": out, **out, "messages": msgs})


@router.post("/api/admin/support/tickets/{ticket_id}/reply")
async def support_ticket_reply(ticket_id: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    message  = (body.get("message") or "").strip()
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    admin_nm = admin.get("name") or admin.get("full_name") or "Admin"
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    doc = await _get_ticket(ticket_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msg_doc = {
        "ticket_id":   ticket_id, "sender_id": admin_id,
        "sender_role": "admin",   "sender_name": admin_nm,
        "content":     message,   "created_at": _now(),
    }
    if support_messages_collection is not None:
        await support_messages_collection.insert_one(msg_doc)
    await support_tickets_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": "in_progress", "last_reply_at": _now(), "last_replied_by": admin_id, "updated_at": _now()}},
    )
    email = doc.get("email", "")
    user_name = doc.get("user_name") or "User"
    subj = f"Re: {doc.get('subject', 'Your Support Ticket')}"
    if email:
        inner = (
            f"<h2 style='color:#fff'>{subj}</h2>"
            f"<p style='color:#94a3b8'>Hi <strong style='color:#f5b800'>{user_name}</strong>,</p>"
            f"<p style='color:#e2e8f0;white-space:pre-wrap'>{message}</p>"
        )
        await _send_bg(email, subj, message, _html_email(subj, inner))
    _log(admin_id, "admin", "ticket_reply", f"Reply to ticket {ticket_id}")
    return JSONResponse({"success": True, "message": "Reply sent", "msg": _s(msg_doc)})


@router.patch("/api/admin/support/tickets/{ticket_id}/status")
async def support_ticket_status(ticket_id: str, request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    new_status = (body.get("status") or "").strip()
    admin_id   = admin.get("admin_id") or str(admin.get("_id", ""))
    if new_status not in {"open", "in_progress", "resolved", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    doc = await _get_ticket(ticket_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")
    upd = {"status": new_status, "status_updated_by": admin_id, "status_updated_at": _now(), "updated_at": _now()}
    if new_status == "resolved":
        upd["resolved_at"] = _now()
    await support_tickets_collection.update_one({"_id": doc["_id"]}, {"$set": upd})
    _log(admin_id, "admin", "ticket_status", f"Ticket {ticket_id} → {new_status}")
    return JSONResponse({"success": True, "status": new_status})


async def _get_ticket(ticket_id: str) -> Optional[dict]:
    doc = await support_tickets_collection.find_one({"ticket_id": ticket_id})
    if not doc and len(ticket_id) == 24:
        try:
            doc = await support_tickets_collection.find_one({"_id": ObjectId(ticket_id)})
        except Exception:
            pass
    return doc


# ============================================================
# ── PAYOUT REQUESTS ─────────────────────────────────────────
# ============================================================

# ─── REPLACE THE ENTIRE payout_requests ENDPOINT ─────────────────────────
@router.get("/api/admin/payout-requests")
async def payout_requests(
    request: Request,
    status: str = "",
    role:   str = "",   # NEW: comma-separated, e.g. "dco,supervisor"
    page:   int = 1,
    limit:  int = 20,
):
    await _require_admin(request)
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    if role:
        roles = [r.strip().lower() for r in role.split(",") if r.strip()]
        if roles:
            filt["$or"] = [{"user_type": {"$in": roles}}, {"role": {"$in": roles}}]
    # Try dedicated payout collection first, fall back to transactions
    col = payout_requests_collection
    if col is None:
        col = transactions_collection
    if col is None:
        return JSONResponse({"payouts": [], "total": 0})
    total = await col.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await col.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return JSONResponse({"payouts": _ss(docs), "payout_requests": _ss(docs), "total": total, "page": page})
      
@router.post("/api/admin/payout-requests/{payout_id}/approve")
async def admin_approve_payout(
    payout_id: str,
    body: PayoutApproveBody,
    request: Request,
):
    """Approve a pending payout request."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    col = _require_collection(payout_requests_collection, "payout_requests_collection")
    filter_q = {"$or": [{"payout_id": payout_id}, {"_id": _try_oid(payout_id)}]}

    doc = await col.find_one(filter_q)
    if not doc:
        raise HTTPException(status_code=404, detail="Payout request not found")

    tx_ref = (
        body.transaction_ref
        or body.reference
        or f"PAYOUT-APPROVED-{secrets.token_hex(8).upper()}"
    )

    result = await col.update_one(
        filter_q,
        {
            "$set": {
                "status":          "approved",
                "approved_at":     _now_utc(),
                "transaction_ref": tx_ref,
                "admin_id":        admin_id,
                "updated_at":      _now_utc(),
            }
        },
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Payout request not found")

    user_id   = doc.get("user_id") or doc.get("dco_id") or ""
    user_type = doc.get("user_type") or doc.get("role") or "dco"
    if user_id:
        await _send_notification(
            user_id, user_type,
            "Payout Approved",
            f"Your payout of ₦{doc.get('amount', 0):,.2f} has been approved and processed.",
            "payout_approved",
        )

    _log(admin_id, "admin", "payout_approved", f"Approved payout: {payout_id}")
    return JSONResponse({
        "success":         True,
        "payout_id":       payout_id,
        "status":          "approved",
        "transaction_ref": tx_ref,
    })


@router.post("/api/admin/payout-requests/{payout_id}/reject")
async def admin_reject_payout(
    payout_id: str,
    body: PayoutRejectBody,
    request: Request,
):
    """Reject a pending payout request."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    col = _require_collection(payout_requests_collection, "payout_requests_collection")
    filter_q = {"$or": [{"payout_id": payout_id}, {"_id": _try_oid(payout_id)}]}

    doc = await col.find_one(filter_q)
    if not doc:
        raise HTTPException(status_code=404, detail="Payout request not found")

    result = await col.update_one(
        filter_q,
        {
            "$set": {
                "status":           "rejected",
                "rejected_at":      _now_utc(),
                "rejection_reason": body.reason or "",
                "admin_id":         admin_id,
                "updated_at":       _now_utc(),
            }
        },
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Payout request not found")

    user_id   = doc.get("user_id") or doc.get("dco_id") or ""
    user_type = doc.get("user_type") or doc.get("role") or "dco"
    if user_id:
        await _send_notification(
            user_id, user_type,
            "Payout Rejected",
            f"Your payout request has been rejected. Reason: {body.reason or 'N/A'}",
            "payout_rejected",
        )

    _log(admin_id, "admin", "payout_rejected", f"Rejected payout: {payout_id}")
    return JSONResponse({
        "success":   True,
        "payout_id": payout_id,
        "status":    "rejected",
        "reason":    body.reason,
    })


# ============================================================
@router.get("/api/admin/dco/available")
async def get_available_dco(
    request: Request,
    country: str = "Nigeria",
    state: str = "",
    lga: str = "",
    city: str = "",
    match_date: str = "",          # ISO date string, e.g. "2025-08-15"
    match_time: str = "",          # "HH:MM" 24-hour
    role: str = "dco",             # "dco" | "supervisor"
    limit: int = 50,
):
    """
    Return DCOs or supervisors available for a match at the given
    country/state/LGA, on the given match_date/time, subject to:

      DCO rules:
        1. No same DCO for overlapping matches within 3 h 30 min.
        2. Max 3 players assigned per DCO per match_date.

      Supervisor rules:
        1. Max 11 DCOs monitored per supervisor per match_date.
    """
    await _require_admin(request)

    role = role.lower()
    if role not in ("dco", "supervisor"):
        raise HTTPException(status_code=400, detail="role must be 'dco' or 'supervisor'")

    col = dco_collection if role == "dco" else supervisors_collection
    id_field = "dco_id" if role == "dco" else "supervisor_id"
    if col is None:
        return JSONResponse({"dcos": [], "supervisors": [], "users": []})

    # ── Build location filter (via location_module — single source of truth) ──
    # Public clients may submit either ISO code (NG) or display name (Nigeria).
    country_filter = get_country_name(country) or country
    loc_filter: dict = build_venue_location_filter(
        country=country_filter, state=state, lga=lga, city=city
    )

    # Fetch matching users
    candidates = _ss(await col.find(loc_filter or {}).sort("created_at", -1).limit(limit * 3).to_list(limit * 3))

    if not candidates or not match_date:
        # No date supplied → skip conflict checks
        result = candidates[:limit]
        key = "dcos" if role == "dco" else "supervisors"
        return JSONResponse({key: result, "users": result})

    # ── Parse match datetime for conflict window ───────────────────
    match_dt = None
    if match_time:
        try:
            match_dt = datetime.fromisoformat(f"{match_date}T{match_time}:00+00:00")
        except Exception:
            pass
    if not match_dt:
        try:
            match_dt = datetime.fromisoformat(f"{match_date}T00:00:00+00:00")
        except Exception:
            pass

    # Conflict window: ±3 h 30 min around the match start
    CONFLICT_WINDOW = timedelta(hours=3, minutes=30)

    # Fetch all existing assignments for this match_date to check conflicts.
    # The status field may be stored in mixed case (e.g. "Pending" from some
    # client paths, "pending" from others), so use a case-insensitive regex
    # rather than $in to match both.
    existing_assignments: list = []
    if stats_requests_collection is not None:
        try:
            existing_assignments = _ss(await stats_requests_collection.find({
                "match_date": match_date,
                "status": {"$regex": "^(pending|assigned)$", "$options": "i"},
            }).to_list(5000))
        except Exception:
            existing_assignments = []

    # Build conflict maps
    dco_assignment_count: dict = {}    # dco_id → list of assigned match datetimes on this date
    supervisor_dco_count: dict = {}    # supervisor_id → count of DCOs on this date

    for asgn in existing_assignments:
        d_id  = asgn.get("assigned_dco_id", "")
        s_id  = asgn.get("assigned_supervisor_id", "")
        a_time = asgn.get("match_time", "")
        a_dt   = None
        if a_time:
            try:
                a_dt = datetime.fromisoformat(f"{match_date}T{a_time}:00+00:00")
            except Exception:
                pass
        if d_id:
            dco_assignment_count.setdefault(d_id, []).append(a_dt)
        if s_id:
            supervisor_dco_count[s_id] = supervisor_dco_count.get(s_id, 0) + 1

    # ── Apply conflict rules per candidate ────────────────────────
    result = []
    for c in candidates:
        uid = c.get(id_field) or c.get("user_id") or str(c.get("_id", ""))
        conflict_reason = ""

        if role == "dco":
            existing_times = dco_assignment_count.get(uid, [])

            # Rule 1: max 3 players per DCO per match_date
            if len(existing_times) >= 3:
                conflict_reason = "Max 3 players reached"

            # Rule 2: no overlapping match within ±3h30min
            if not conflict_reason and match_dt:
                for et in existing_times:
                    if et and abs((match_dt - et).total_seconds()) < CONFLICT_WINDOW.total_seconds():
                        conflict_reason = "Match overlap (< 3h30)"
                        break

        else:  # supervisor
            # Rule: max 11 DCOs per supervisor per match_date
            if supervisor_dco_count.get(uid, 0) >= 11:
                conflict_reason = "Max 11 DCOs reached"

        c["conflict_reason"] = conflict_reason
        result.append(c)

    # Sort: available first, then blocked
    result.sort(key=lambda x: (bool(x.get("conflict_reason")), x.get("name", "")))
    result = result[:limit]

    key = "dcos" if role == "dco" else "supervisors"
    return JSONResponse({key: result, "users": result, "total": len(result)})


# ============================================================
# ── ASSIGNMENTS ─────────────────────────────────────────────
# ============================================================

@router.get("/api/admin/assignments")
async def assignments(
    request: Request,
    status: str = "",
    limit: int = 20,
    page: int = 1,
):
    await _require_admin(request)
    filt: Dict[str, Any] = {}
    if status:
        filt["status"] = status
    limit = min(200, max(1, limit))
    col   = dco_assignments_collection
    if col is None:
        return JSONResponse({"assignments": [], "total": 0})
    total = await col.count_documents(filt)
    skip  = (page - 1) * limit
    docs  = await col.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return JSONResponse({"assignments": _ss(docs), "total": total, "page": page})


@router.post("/api/admin/assignments")
async def admin_create_assignment(
    body: AssignmentBody,
    request: Request,
):
    """
    Manually create a scout / DCO assignment.
    Fallback used by the frontend when the /stats-requests/{id}/assign
    endpoint is unavailable.
    """
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    asgn_col = _require_collection(dco_assignments_collection, "dco_assignments_collection")
    dco_col = _require_collection(dco_collection, "dco_collection")

    assignee_id = body.assigned_dco_id or body.assigned_supervisor_id or ""
    role = "dco" if body.assigned_dco_id else "supervisor"

    # Resolve the ID sent by the admin UI. Depending on which table/view
    # launched assignment, it may be Mongo _id, request_id, or reference_id.
    supplied_request_id = str(body.stats_request_id or "").strip()
    request_doc = None
    if stats_requests_collection is not None and supplied_request_id:
        request_clauses = [
            {"request_id": supplied_request_id},
            {"reference_id": supplied_request_id},
            {"referenceId": supplied_request_id},
            {"stats_request_id": supplied_request_id},
        ]
        if ObjectId.is_valid(supplied_request_id):
            request_clauses.append({"_id": ObjectId(supplied_request_id)})
        request_doc = await stats_requests_collection.find_one({"$or": request_clauses})

    # Use the persisted Mongo ID as the canonical link when the request is
    # available, while retaining the human-facing reference for old clients.
    canonical_request_id = (
        str(request_doc.get("_id"))
        if request_doc and request_doc.get("_id") is not None
        else supplied_request_id
    )
    request_reference_id = (
        str((request_doc or {}).get("reference_id")
            or (request_doc or {}).get("referenceId")
            or supplied_request_id)
    )

    assignment_id = f"ASGN-{secrets.token_hex(6).upper()}"
    assignment_doc = {
        "assignment_id": assignment_id,
        "request_id": canonical_request_id,
        "stats_request_id": canonical_request_id,
        "request_reference_id": request_reference_id,
        "dco_id": body.assigned_dco_id or "",
        "assigned_dco_id": body.assigned_dco_id or "",
        "supervisor_id": body.assigned_supervisor_id or "",
        "assigned_supervisor_id": body.assigned_supervisor_id or "",
        "assignee_id": assignee_id,
        "role": role,
        "notes": body.notes or "",
        "status": "assigned",
        "admin_id": admin_id,
        "created_at": _now_utc(),
        "updated_at": _now_utc(),
    }
    # Keep the assignment self-describing as a safe fallback if older request
    # documents cannot be fetched by a downstream tracker.
    if request_doc:
        for field in (
            "reference_id", "requester_type", "entity_type", "request_type",
            "tracking_type", "club_id", "club_name", "user_id", "player_id",
            "player_name", "home_team", "away_team", "match_date", "match_time",
            "match_type", "venue_address", "venue_state", "venue_lga",
            "venue_country", "contact_phone", "jersey_color", "player_ids",
            "player_stat_categories",
        ):
            if request_doc.get(field) is not None:
                assignment_doc[field] = request_doc[field]
    await asgn_col.insert_one(assignment_doc)

    # ── FIX 1-B: propagate supervisor_id to the DCO's own document ────────
    # Mirrors Fix 1-A. Admin override is allowed and logged.
    if body.assigned_dco_id and body.assigned_supervisor_id:
        _dco_doc = await dco_col.find_one(
            {
                "$or": [
                    {"dco_id": body.assigned_dco_id},
                    {"user_id": body.assigned_dco_id},
                ]
            }
        )
        if _dco_doc:
            _old_sup = _dco_doc.get("supervisor_id", "")
            if _old_sup and _old_sup != body.assigned_supervisor_id:
                logger.warning(
                    "Admin %s overriding supervisor_id on DCO %s: %s → %s",
                    admin_id,
                    body.assigned_dco_id,
                    _old_sup,
                    body.assigned_supervisor_id,
                )
            await dco_col.update_one(
                {"_id": _dco_doc["_id"]},
                {
                    "$set": {
                        "supervisor_id": body.assigned_supervisor_id,
                        "supervisor_id_source": "admin_assignment",
                        "updated_at": _now_utc(),
                    }
                },
            )
        else:
            logger.warning(
                "admin_create_assignment: DCO %s not found in dco_collection; "
                "supervisor_id not propagated.",
                body.assigned_dco_id,
            )

    # Update the exact resolved request and write every ownership alias used
    # by the DCO dashboard/tracker. Older documents remain readable as well.
    if stats_requests_collection is not None:
        assignee_fields = {
            "status": "assigned",
            "assigned_role": role,
            "updated_at": _now_utc(),
        }
        if role == "dco":
            assignee_fields.update({
                "dco_id": assignee_id,
                "assigned_dco_id": assignee_id,
                "assignee_id": assignee_id,
            })
        else:
            assignee_fields.update({
                "supervisor_id": assignee_id,
                "assigned_supervisor_id": assignee_id,
                "assignee_id": assignee_id,
            })
        if request_doc and request_doc.get("_id") is not None:
            await stats_requests_collection.update_one(
                {"_id": request_doc["_id"]}, {"$set": assignee_fields}
            )
        else:
            fallback_clauses = [
                {"request_id": supplied_request_id},
                {"reference_id": supplied_request_id},
                {"referenceId": supplied_request_id},
            ]
            if ObjectId.is_valid(supplied_request_id):
                fallback_clauses.append({"_id": ObjectId(supplied_request_id)})
            await stats_requests_collection.update_one(
                {"$or": fallback_clauses}, {"$set": assignee_fields}
            )

    if assignee_id:
        await _send_notification(
            assignee_id,
            role,
            "New Assignment",
            f"You have been assigned a new stats request (ID: {body.stats_request_id}).",
            "stats_request_assigned",
        )

    _log(
        admin_id,
        "admin",
        "assignment_created",
        f"Created assignment {assignment_id} for stats request {body.stats_request_id}",
    )

    return JSONResponse({
        "success":          True,
        "assignment_id":    assignment_id,
        "request_id":       canonical_request_id,
        "stats_request_id": canonical_request_id,
        "request_reference_id": request_reference_id,
        "assignee_id":      assignee_id,
        "role":             role,
        "status":           "assigned",
    })


# ============================================================
# ── BACKGROUND CHECKS ───────────────────────────────────────
# ============================================================

@router.get("/api/admin/background-checks")
async def admin_list_background_checks(
    request: Request,
    status: Optional[str] = None,
    page:   int           = 1,
    limit:  int           = 15,
):
    """
    List users with a background check record.

    Checks are stored as bg_check_status / bg_check_submitted_at fields
    on the user documents (DCO, scout, supervisor, player, agent).

    Response: { total, checks: [...], background_checks: [...] }
    """
    await _require_admin(request)

    _check_cols = [
        (dco_collection,         "dco"),
        (scouts_collection,      "scout"),
        (supervisors_collection, "supervisor"),
    ]

    query: Dict[str, Any] = {"bg_check_status": {"$exists": True}}
    if status:
        query["bg_check_status"] = status

    all_checks: List[dict] = []
    total_count = 0

    for col, role in _check_cols:
        if col is None:
            continue
        count = await col.count_documents(query)
        total_count += count
        docs = await col.find(query).sort("bg_check_submitted_at", -1).limit(limit).to_list(length=limit)
        for d in docs:
            serialized = _serialize(d)
            serialized["user_type"] = serialized.get("user_type") or serialized.get("role") or role
            serialized["user_name"] = (
                serialized.get("name")
                or f"{serialized.get('firstName', '')} {serialized.get('lastName', '')}".strip()
            )
            serialized["status"]       = serialized.get("bg_check_status", "pending")
            serialized["submitted_at"] = serialized.get("bg_check_submitted_at") or serialized.get("created_at")
            all_checks.append(serialized)

    all_checks.sort(key=lambda c: c.get("submitted_at") or "", reverse=True)
    skip  = (page - 1) * limit
    paged = all_checks[skip: skip + limit]
    return JSONResponse({"total": total_count, "checks": paged, "background_checks": paged})


@router.post("/api/admin/background-checks/{uid}/approve")
async def admin_approve_background_check(uid: str, request: Request):
    """Approve a user's background check."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    doc, col, role = await _find_user_for_bgcheck(uid)
    if doc is None or col is None:
        raise HTTPException(status_code=404, detail="User not found for background check")

    filter_q = {
        "$or": [
            {"user_id": uid}, {"dco_id": uid}, {"scout_id": uid},
            {"player_id": uid}, {"agent_id": uid},
            {"_id": _try_oid(uid)},
        ]
    }
    await col.update_one(
        filter_q,
        {
            "$set": {
                "bg_check_status":      "approved",
                "bg_check_approved_at": _now_utc(),
                "bg_check_admin_id":    admin_id,
                "updated_at":           _now_utc(),
            }
        },
    )

    await _send_notification(
        uid, role or "user",
        "Background Check Approved",
        "Your background check has been approved. You can now access all platform features.",
        "bg_check_approved",
    )

    _log(admin_id, "admin", "bgcheck_approved", f"Approved background check for {uid}")
    return JSONResponse({"success": True, "user_id": uid, "bg_check_status": "approved"})


@router.post("/api/admin/background-checks/{uid}/reject")
async def admin_reject_background_check(uid: str, body: StatsRejectBody, request: Request):
    """Reject a user's background check."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    doc, col, role = await _find_user_for_bgcheck(uid)
    if doc is None or col is None:
        raise HTTPException(status_code=404, detail="User not found for background check")

    filter_q = {
        "$or": [
            {"user_id": uid}, {"dco_id": uid}, {"scout_id": uid},
            {"player_id": uid}, {"agent_id": uid},
            {"_id": _try_oid(uid)},
        ]
    }
    await col.update_one(
        filter_q,
        {
            "$set": {
                "bg_check_status":        "rejected",
                "bg_check_rejected_at":   _now_utc(),
                "bg_check_reject_reason": body.reason or "",
                "bg_check_admin_id":      admin_id,
                "updated_at":             _now_utc(),
            }
        },
    )

    await _send_notification(
        uid, role or "user",
        "Background Check Rejected",
        f"Your background check was rejected. Reason: {body.reason or 'N/A'}",
        "bg_check_rejected",
    )

    _log(admin_id, "admin", "bgcheck_rejected", f"Rejected background check for {uid}")
    return JSONResponse({
        "success":         True,
        "user_id":         uid,
        "bg_check_status": "rejected",
        "reason":          body.reason,
    })


# ============================================================
# ── BANK DETAILS ────────────────────────────────────────────
# ============================================================

@router.get("/api/admin/bank-details")
async def admin_get_bank_details(request: Request):
    """
    Return the platform bank account details used for payment instructions.

    Response: { success, bank_details: { account_name, account_number, bank_name, ... }, bank: {...} }
    """
    await _require_admin(request)
    doc  = await _get_bank_document()
    bank = doc.get("bank_details") or doc.get("bank") or {}
    return JSONResponse({"success": True, "bank_details": bank, "bank": bank})


@router.post("/api/admin/bank-details")
async def admin_save_bank_details(body: BankDetailsBody, request: Request):
    """
    Save / update the platform bank account details.

    Response: { success, bank_details: {...} }
    """
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    bank_data = {k: v for k, v in body.model_dump().items() if v is not None}

    # Persist to platform_settings_collection or admin_settings
    col = platform_settings_collection

    if col is not None:
        await col.update_one(
            {"key": _BANK_SETTINGS_KEY},
            {
                "$set": {
                    "key":          _BANK_SETTINGS_KEY,
                    "bank_details": bank_data,
                    "updated_at":   _now_utc(),
                    "admin_id":     admin_id,
                }
            },
            upsert=True,
        )
    elif database is not None:
        try:
            admin_settings_col = database["admin_settings"]   # ← Motor: [] not .get()
            await admin_settings_col.update_one(
                {"key": "platform"},
                {
                    "$set": {
                        "bank_transfer": bank_data,
                        "updated_at":    _now_utc(),
                    }
                },
                upsert=True,
            )
        except Exception:
            pass

    else:
        raise HTTPException(status_code=503, detail="Bank settings database is unavailable")

    _log(admin_id, "admin", "bank_details_saved", "Bank details updated")
    return JSONResponse({"success": True, "bank_details": bank_data})


# ── /api/admin/settings/bank aliases ────────────────────────
# The frontend falls back to these when /bank-details routes fail.

@router.get("/api/admin/settings/bank")
async def admin_get_settings_bank(request: Request):
    """Alias for GET /api/admin/bank-details."""
    return await admin_get_bank_details(request)


@router.patch("/api/admin/settings/bank")
async def admin_patch_settings_bank(body: BankDetailsBody, request: Request):
    """Alias for POST /api/admin/bank-details."""
    return await admin_save_bank_details(body, request)


# ============================================================
# ── PLATFORM SETTINGS ────────────────────────────────────────
# ============================================================

# ─── REPLACE _DEFAULT_SETTINGS ───────────────────────────────────────────
_DEFAULT_SETTINGS = {
    "token_packages": _pricing_module.TOKEN_PACKAGES,
    "subscription_pricing": _pricing_module.DEFAULT_SUBSCRIPTION_PRICES,
    "token_costs": _pricing_module.DEFAULT_ADMIN_SETTINGS["token_costs"],
    "dco_rates": _pricing_module.DEFAULT_DCO_RATES,
    "supervisor_rates": _pricing_module.DEFAULT_SUPERVISOR_RATES,
    "country_multipliers": {},
    "bank_transfer": _pricing_module.DEFAULT_ADMIN_SETTINGS["bank_transfer"],
    "flutterwave": _pricing_module.DEFAULT_ADMIN_SETTINGS["flutterwave"],
    "platform_fee_percent": 0.0,
}


@router.get("/api/admin/settings")
async def get_settings(request: Request):
    await _require_admin(request)
    doc = await platform_settings_collection.find_one({"key": "platform"}) if platform_settings_collection is not None else None
    import copy
    merged = copy.deepcopy(_DEFAULT_SETTINGS)
    if doc:
        for fld in ("token_packages", "subscription_pricing", "token_costs",
                    "dco_rates", "supervisor_rates", "country_multipliers",
                    "bank_transfer", "flutterwave", "platform_fee_percent"):
            if fld in doc:
                merged[fld] = copy.deepcopy(doc[fld])
    return JSONResponse(merged)


@router.patch("/api/admin/settings")
async def save_settings(request: Request):
    admin = await _require_admin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="JSON body must be an object")
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    upd: Dict[str, Any] = {"key": "platform", "updated_at": _now(), "updated_by": admin_id}
    _EDITABLE = (
        "token_packages", "subscription_pricing", "token_costs",
        "dco_rates", "supervisor_rates", "country_multipliers",
        "bank_transfer", "flutterwave", "platform_fee_percent",
    )
    unknown = set(body) - set(_EDITABLE)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported settings fields: {sorted(unknown)}")
    for fld in _EDITABLE:
        if fld in body:
            upd[fld] = body[fld]
    fee = upd.get("platform_fee_percent")
    if fee is not None:
        import math
        if isinstance(fee, bool) or not isinstance(fee, (int, float)) or not math.isfinite(float(fee)) or not 0 <= float(fee) <= 100:
            raise HTTPException(status_code=422, detail="platform_fee_percent must be a finite number from 0 to 100")
    for field in ("token_packages", "subscription_pricing", "token_costs", "dco_rates", "supervisor_rates", "country_multipliers", "flutterwave", "bank_transfer"):
        if field in upd and not isinstance(upd[field], dict):
            raise HTTPException(status_code=422, detail=f"{field} must be an object")
    if "subscription_pricing" in upd:
        try:
            _pricing_module._assert_price_invariants(upd["subscription_pricing"])
        except (AssertionError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid subscription pricing: {exc}") from exc
    if not any(k in upd for k in _EDITABLE):
        raise HTTPException(status_code=400, detail="No recognised settings fields provided")
    if platform_settings_collection is None:
        raise HTTPException(status_code=503, detail="Platform settings database is unavailable")
    try:
        await platform_settings_collection.update_one({"key": "platform"}, {"$set": upd}, upsert=True)
        saved_doc = await platform_settings_collection.find_one({"key": "platform"})
    except Exception as exc:
        if logger:
            logger.exception("Failed to save platform settings")
        raise HTTPException(status_code=503, detail="Unable to save platform settings") from exc
    if saved_doc:
        _pricing_module.pricing_service = _pricing_module.PricingService.from_db_settings(saved_doc)
        global pricing_service
        pricing_service = _pricing_module.pricing_service
    saved = [k for k in _EDITABLE if k in upd]
    _log(admin_id, "admin", "settings_updated", f"Platform settings saved: {saved}")
    return JSONResponse({"success": True, "message": "Settings saved", "updated_fields": saved})

# ==============================================================
# END OF FILE
# ==============================================================
# ============================================================
