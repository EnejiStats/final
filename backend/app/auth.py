
"""
ENEJISTATS — Authentication Routes
====================================
Standalone FastAPI router module covering every auth-related API endpoint
consumed by:
  • register.html   — POST /api/auth/register, verify-registration-otp,
                      resend-registration-otp
  • login.html      — POST /api/auth/login, verify-login-otp, logout
  • forgot-password.html — POST /api/auth/forgot-password,
                           verify-reset-code, reset-password-otp,
                           reset-password, resend-reset-code

HOW TO INTEGRATE (already wired in main.py):
─────────────────────────────────────────────
    import auth as _auth
    _auth._setup_dependencies(globals())
    app.include_router(_auth.router)

WHY THIS PATTERN — CIRCULAR IMPORT EXPLAINED
─────────────────────────────────────────────
A plain `from main import (...)` at the top of this file causes a
circular import loop.  The fix: this file NEVER imports from main at
module-level.  Instead, all shared state is injected by
_setup_dependencies() which is called by main.py AFTER main.py has
fully executed and all symbols are bound in its namespace.

HOW TO REMOVE DEBUG LOGGING
────────────────────────────
Each route has debug blocks marked:
    # ── DEBUG BLOCK START ──
    ...
    # ── DEBUG BLOCK END ────
Delete every line between the markers (and the markers themselves)
to strip debug output without touching any route logic.

CANONICAL ROLE / COLLECTION CONTRACT
───────────────────────────────────
Role metadata, role collections, public-ID fields, permissions and eligibility
are injected from main.py's ROLE_REGISTRY/ROLE_COLLECTION_MAP.  This module
does not define a competing role registry.  Content Manager and Sub-Admin are
first-class canonical roles and resolve to content_managers/cm_id and
sub_admins/sub_admin_id respectively.
TOKEN COLLECTIONS (wallet bootstrap on registration)
──────────────────────────────────────────────────────
  player → player_tokens_collection
  agent  → agent_tokens_collection
  club   → club_tokens_collection
  scout  → scout_tokens_collection
  dco    → dco_tokens_collection
  (supervisor, communication_officer, customer_care — no token wallet)

OTP STORAGE COLLECTIONS
────────────────────────
  registration_otps_col → database["registration_otps"]
  password_reset_otps_col → database["password_reset_otps"]

DUPLICATE PREVENTION
─────────────────────
Canonical create_platform_user() in main.py owns identity validation, email
normalization, password hashing, public-ID generation, duplicate protection,
role collection resolution and general users metadata creation.
"""

# ============================================================
# STANDARD-LIBRARY & THIRD-PARTY IMPORTS ONLY
# (No import from main — circular import avoided)
# ============================================================
import io as _auth_io
import json
import os
import re
import jwt
import random
import time as _time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

# ── Location data constants (states & LGAs) extracted to location_module.py ──
from location_module import (
    NIGERIAN_STATES,
    NIGERIAN_LGAS,
    get_country_name,
)


# ============================================================
# MODULE-LEVEL PLACEHOLDERS
# All set to None here; filled in by _setup_dependencies() below.
# ============================================================

# ── Database handle ──────────────────────────────────────────
database = None

# ── Role collections (primary profile stores) ────────────────
players_collection               = None
clubs_collection                 = None
scouts_collection                = None
agents_collection                = None
dco_collection                   = None
supervisors_collection           = None
communication_officers_collection = None
customer_care_collection         = None
admins_collection                = None

# ── Token wallet collections ──────────────────────────────────
player_tokens_collection  = None
agent_tokens_collection   = None
club_tokens_collection    = None
scout_tokens_collection   = None
dco_tokens_collection     = None

# ── OTP / temp-data collections (resolved dynamically) ───────
registration_otps_col   = None   # database["registration_otps"]
password_reset_otps_col = None   # database["password_reset_otps"]
notifications_collection = None

# ── Auth & security helpers ───────────────────────────────────
create_access_token = None
verify_token        = None
hash_password       = None
verify_password     = None

# Canonical platform services injected from main.py.
normalize_email        = None
normalize_role         = None
role_has_permission    = None
role_collection        = None
ROLE_REGISTRY          = None
ROLE_COLLECTION_MAP    = None
CANONICAL_ROLES        = None
TOKEN_ELIGIBLE_ROLES   = None
SUBSCRIPTION_ELIGIBLE_ROLES = None
generate_user_id       = None
create_platform_user   = None
build_user_access_token = None

# ── Business-logic helpers ────────────────────────────────────
MongoSerializer      = None
logger               = None
upload_to_cloudinary = None
send_email           = None
_email_html          = None
_build_otp_email     = None

# ── Pricing / config data (for public endpoints) ─────────────
POSITIONS_CONFIG     = None
PLAYER_LEVELS_CONFIG = None

_DEPS_READY = False

# ── Liveness
liveness_sessions_collection = None

# ── Extra collections
users_collection = None
venues_collection = None
get_current_user = None

# ── JWT secrets (injected)
SECRET_KEY = None
ALGORITHM  = None

# ── Verification codes (for login unverified-email gate)
verification_codes_collection = None

# ── Token expiry (hours) — injected from main.py
ACCESS_TOKEN_EXPIRE_HOURS = 24

credit_tokens = None
deduct_tokens = None

DCO_REGISTRATION_TOKEN_COSTS: Dict[str, Dict[str, float]] = {
    "player": {
        "professional": 5,
        "semi-professional": 3.5,
        "academy": 3,
        "university": 2,
        "local": 2,
        "other": 2,
    },
    "club": {
        "professional": 100,
        "university": 100,
        "semi-professional": 50,
        "academy": 50,
        "local": 20,
        "other": 20,
    },
}

# ============================================================
# DEPENDENCY INJECTION — called once from main.py's bottom
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Populate every module-level placeholder from the main module namespace.

    Called by main.py immediately after importing this module:

        import auth as _auth
        _auth._setup_dependencies(globals())
        app.include_router(_auth.router)
    """

    global _DEPS_READY

    global database

    global players_collection, clubs_collection, scouts_collection
    global agents_collection, dco_collection, supervisors_collection
    global communication_officers_collection, customer_care_collection
    global admins_collection

    global player_tokens_collection, agent_tokens_collection
    global club_tokens_collection, scout_tokens_collection, dco_tokens_collection

    global registration_otps_col, password_reset_otps_col
    global notifications_collection

    global create_access_token, verify_token, hash_password, verify_password
    global normalize_email, normalize_role, role_has_permission, role_collection, ROLE_REGISTRY
    global ROLE_COLLECTION_MAP, CANONICAL_ROLES, TOKEN_ELIGIBLE_ROLES
    global SUBSCRIPTION_ELIGIBLE_ROLES, generate_user_id, create_platform_user
    global build_user_access_token

    global MongoSerializer, logger, upload_to_cloudinary, send_email
    global _email_html, _build_otp_email

    global POSITIONS_CONFIG, PLAYER_LEVELS_CONFIG
    global liveness_sessions_collection
    global users_collection, venues_collection
    global get_current_user
    global SECRET_KEY, ALGORITHM
    global verification_codes_collection
    global ACCESS_TOKEN_EXPIRE_HOURS
    global credit_tokens, deduct_tokens

    if _DEPS_READY:
        return

    _main = main_globals

    # ── Database handle ──────────────────────────────────────
    database = _main["database"]

    # ── Role collections ─────────────────────────────────────
    players_collection = _main["players_collection"]
    clubs_collection = _main["clubs_collection"]
    scouts_collection = _main["scouts_collection"]
    agents_collection = _main["agents_collection"]
    dco_collection = _main["dco_collection"]
    supervisors_collection = _main["supervisors_collection"]
    communication_officers_collection = _main["communication_officers_collection"]
    customer_care_collection = _main["customer_care_collection"]
    admins_collection = _main["admins_collection"]

    # ── Token wallet collections ─────────────────────────────
    player_tokens_collection = _main["player_tokens_collection"]
    agent_tokens_collection = _main["agent_tokens_collection"]
    club_tokens_collection = _main["club_tokens_collection"]
    scout_tokens_collection = _main["scout_tokens_collection"]
    dco_tokens_collection = _main["dco_tokens_collection"]

    # ── OTP / temp collections ───────────────────────────────
    registration_otps_col = database["registration_otps"]
    password_reset_otps_col = database["password_reset_otps"]
    verification_codes_collection = database["verification_codes"]
    notifications_collection = _main["notifications_collection"]

    # ── Auth helpers ─────────────────────────────────────────
    create_access_token = _main["create_access_token"]
    verify_token = _main["verify_token"]
    hash_password = _main["hash_password"]
    verify_password = _main["verify_password"]
    normalize_email = _main["normalize_email"]
    normalize_role = _main["normalize_role"]
    role_has_permission = _main["role_has_permission"]
    role_collection = _main["role_collection"]
    ROLE_REGISTRY = _main["ROLE_REGISTRY"]
    ROLE_COLLECTION_MAP = _main["ROLE_COLLECTION_MAP"]
    CANONICAL_ROLES = _main["CANONICAL_ROLES"]
    TOKEN_ELIGIBLE_ROLES = _main["TOKEN_ELIGIBLE_ROLES"]
    SUBSCRIPTION_ELIGIBLE_ROLES = _main["SUBSCRIPTION_ELIGIBLE_ROLES"]
    generate_user_id = _main["generate_user_id"]
    create_platform_user = _main["create_platform_user"]
    build_user_access_token = _main["build_user_access_token"]

    # ── Business-logic helpers ───────────────────────────────
    MongoSerializer = _main["MongoSerializer"]
    logger = _main["logger"]
    upload_to_cloudinary = _main["upload_to_cloudinary"]
    send_email = _main["send_email"]
    _email_html = _main["_email_html"]
    _build_otp_email = _main["_build_otp_email"]

    # ── Pricing / configuration ──────────────────────────────
    # COUNTRIES_CONFIG is sourced from location_module — not injected from main.
    POSITIONS_CONFIG = _main["POSITIONS_CONFIG"]
    PLAYER_LEVELS_CONFIG = _main["PLAYER_LEVELS_CONFIG"]

    liveness_sessions_collection = _main["liveness_sessions_collection"]
    users_collection = _main.get("users_collection")
    venues_collection = _main.get("venues_collection")
    if venues_collection is None:
        venues_collection = _main.get("venue_collection")
    if venues_collection is None:
        venues_collection = database["venues"]
    get_current_user = _main.get("get_current_user")

    SECRET_KEY = _main["SECRET_KEY"]
    ALGORITHM = _main["ALGORITHM"]

    ACCESS_TOKEN_EXPIRE_HOURS = int(
        _main.get("ACCESS_TOKEN_EXPIRE_HOURS", 24)
    )
    credit_tokens = _main.get("credit_tokens")
    deduct_tokens = _main.get("deduct_tokens")

    _DEPS_READY = True

    # ── DEBUG BLOCK START ────────────────────────────────────
    logger.debug(
        "[auth] _setup_dependencies COMPLETE | "
        "role_collections_bound=%d | "
        "token_collections_bound=%d | "
        "dynamic_collections=%r",
        sum(
            1
            for v in [
                players_collection,
                clubs_collection,
                scouts_collection,
                agents_collection,
                dco_collection,
                supervisors_collection,
                communication_officers_collection,
                customer_care_collection,
                admins_collection,
            ]
            if v is not None
        ),
        sum(
            1
            for v in [
                player_tokens_collection,
                agent_tokens_collection,
                club_tokens_collection,
                scout_tokens_collection,
                dco_tokens_collection,
            ]
            if v is not None
        ),
        [
            registration_otps_col.name,
            password_reset_otps_col.name,
            verification_codes_collection.name,
        ],
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────

# ============================================================
# ROUTER
# ============================================================
router = APIRouter()


# ============================================================
# DEPENDENCY GUARD
# ============================================================

def _assert_deps_ready() -> None:
    """Raise a 503 if _setup_dependencies() has not been called yet."""
    if not _DEPS_READY:
        raise HTTPException(
            status_code=503,
            detail="Service not yet initialised. Try again in a moment.",
        )


def _canonical_role(value: Any) -> str:
    """Resolve a role through main.py's canonical role registry."""
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not raw:
        return ""
    if raw == "data_scout":
        raw = "dco"  # legacy compatibility alias
    try:
        return normalize_role(raw)
    except (ValueError, TypeError):
        return raw


def _decode_auth_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode access tokens exclusively through main.py's canonical verifier."""
    if not token or not callable(verify_token):
        return None
    try:
        payload = verify_token(token)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class LoginRequest(BaseModel):
    email:    str
    password: str


class OtpVerifyRequest(BaseModel):
    email: str
    otp:   str


class LoginOtpVerifyRequest(BaseModel):
    email: str
    otp:   str


class ForgotPasswordRequest(BaseModel):
    email: str


class VerifyResetCodeRequest(BaseModel):
    email: str
    otp:   str


class ResetPasswordOtpRequest(BaseModel):
    """Current flow: email + otp + new_password (no separate token step)."""
    email:        str
    otp:          str
    new_password: str


class ResetPasswordTokenRequest(BaseModel):
    """Future flow: reset_token (from verify-reset-code) + new_password."""
    reset_token:  str
    new_password: str


class ResendResetCodeRequest(BaseModel):
    email: str


class RegistrationOtpRequest(BaseModel):
    user_id: str
    role:    str
    otp:     str


class ResendRegistrationOtpRequest(BaseModel):
    user_id: str
    role:    str


# ============================================================
# PRIVATE HELPERS
# ============================================================

# ── Canonical role/collection helpers ─────────────────────────

def _role_collection(role: str):
    """Resolve a role collection through main.py's canonical registry."""
    try:
        return role_collection(_canonical_role(role))
    except (KeyError, ValueError, TypeError):
        return None


def _role_token_collection(role: str):
    """Return the token wallet for a role that main.py marks token-eligible."""
    canonical = _canonical_role(role)
    if canonical not in (TOKEN_ELIGIBLE_ROLES or frozenset()):
        return None
    return globals().get(f"{canonical}_tokens_collection")


def _role_redirect(role: str) -> str:
    """Return the existing dashboard route without redefining role identity."""
    redirects = {
        "player": "/player-dashboard", "club": "/club-dashboard",
        "scout": "/scout-dashboard", "agent": "/agent-dashboard",
        "dco": "/dco-dashboard", "supervisor": "/supervisor-dashboard",
        "communication_officer": "/communication-dashboard",
        "customer_care": "/customer-care-dashboard",
        "content_manager": "/content-manager-dashboard",
        "sub_admin": "/admin-dashboard", "admin": "/admin-dashboard",
    }
    return redirects.get(_canonical_role(role), "/")


def _role_id_field(role: str) -> str:
    """Resolve the canonical public-ID field from main.py."""
    canonical = _canonical_role(role)
    try:
        return ROLE_COLLECTION_MAP[canonical][1]
    except (KeyError, TypeError):
        return "user_id"


# ── OTP generator ────────────────────────────────────────────

def _generate_otp() -> str:
    """Return a cryptographically secure 6-digit OTP string."""
    return str(secrets.randbelow(1000000)).zfill(6)


# ── Duplicate-email guard (checks ALL role collections) ──────

async def _find_existing_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find a role-profile document using main.py's canonical role registry."""
    normalized_email = normalize_email(email)
    if not normalized_email:
        return None
    for role in CANONICAL_ROLES or ():
        col = _role_collection(role)
        if col is None:
            continue
        doc = await col.find_one({"email": normalized_email})
        if doc:
            doc["role"] = _canonical_role(doc.get("role") or role)
            return doc
    return None


# ── Token wallet bootstrap (called after successful registration) ──

async def _bootstrap_token_wallet(role: str, user_id: str, mongo_id: str) -> None:
    """Create an empty token wallet for roles that support it."""
    tok_col = _role_token_collection(role)
    if tok_col is None:
        return
    id_field = _role_id_field(role)
    existing = await tok_col.find_one({id_field: user_id})
    if existing:
        return
    await tok_col.insert_one({
        id_field:    user_id,
        "balance":   0,
        "created_at": MongoSerializer.now_utc(),
        "updated_at": MongoSerializer.now_utc(),
    })


def _dco_registration_token_cost(role: str, level: str) -> float:
    key = str(level or "").strip().lower().replace("_", "-")
    return float(
        DCO_REGISTRATION_TOKEN_COSTS.get(role, {}).get(
            key,
            DCO_REGISTRATION_TOKEN_COSTS.get(role, {}).get("other", 0),
        )
    )


async def _consume_dco_registration_tokens(
    dco_id: str,
    amount: float,
    reason: str,
) -> None:
    """Consume the authenticated DCO wallet before creating a registration."""
    if amount <= 0:
        return
    if deduct_tokens is not None:
        try:
            await deduct_tokens(dco_id, "dco", amount, "system", reason)
            return
        except ValueError as exc:
            raise HTTPException(status_code=402, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("[register] DCO token deduction failed: %s", exc)
            raise HTTPException(status_code=503, detail="Token service is unavailable") from exc

    query = {
        "$and": [
            {"$or": [{"dco_id": dco_id}, {"user_id": dco_id}]},
            {"balance": {"$gte": amount}},
        ]
    }
    result = await dco_tokens_collection.update_one(
        query,
        {"$inc": {"balance": -amount}, "$set": {"updated_at": MongoSerializer.now_utc()}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=402, detail="Insufficient DCO tokens")


async def _refund_dco_registration_tokens(
    dco_id: str,
    amount: float,
    reason: str,
) -> None:
    if amount <= 0:
        return
    try:
        if credit_tokens is not None:
            await credit_tokens(dco_id, "dco", amount, "system", reason)
        else:
            await dco_tokens_collection.update_one(
                {"$or": [{"dco_id": dco_id}, {"user_id": dco_id}]},
                {"$inc": {"balance": amount}, "$set": {"updated_at": MongoSerializer.now_utc()}},
            )
    except Exception as exc:
        logger.warning("[register] DCO token refund failed: %s", exc)


# ── Deliver registration OTP (store + send email) ─────────────

async def _issue_registration_otp(
    user_id: str,
    role:    str,
    email:   str,
    display_name: str,
) -> str:
    """
    Generate an OTP, persist it in registration_otps_col with a
    30-minute expiry, and fire the OTP email.
    Returns the raw OTP string (for debugging only — never send to client).
    """
    otp     = _generate_otp()
    expires = MongoSerializer.now_utc() + timedelta(minutes=30)

    # Upsert so resend overwrites the previous OTP
    await registration_otps_col.update_one(
        {"user_id": user_id, "role": role},
        {
            "$set": {
                "user_id":    user_id,
                "role":       role,
                "email":      email,
                "otp":        otp,
                "expires_at": expires,
                "attempts":   0,
                "verified":   False,
                "created_at": MongoSerializer.now_utc(),
            }
        },
        upsert=True,
    )

    plain, html_body = _build_otp_email(display_name, otp)
    try:
        await send_email(
            to_email=email,
            subject="EnejiStats — Verify Your Email",
            body=plain,
            html_body=html_body,
        )
    except Exception as exc:
        logger.error("[auth] Failed to send registration OTP email to %r: %s", email, exc)

    return otp


# ── Deliver password-reset OTP ────────────────────────────────

async def _issue_password_reset_otp(email: str, display_name: str) -> str:
    """
    Generate a reset OTP, persist it in password_reset_otps_col with a
    10-minute expiry, and fire the reset email.
    Returns the raw OTP string (internal use only).
    """
    if password_reset_otps_col is None:
        raise RuntimeError("password_reset_otps_col is not initialised.")

    otp     = _generate_otp()
    expires = MongoSerializer.now_utc() + timedelta(minutes=10)

    await password_reset_otps_col.update_one(
        {"email": email},
        {
            "$set": {
                "email":       email,
                "otp":         otp,
                "expires_at":  expires,
                "attempts":    0,
                "used":        False,
                "verified":    False,
                "reset_token": None,
                "created_at":  MongoSerializer.now_utc(),
            }
        },
        upsert=True,
    )

    inner_html = (
        "<h2 style='margin:0 0 8px;font-size:1.2rem;font-weight:700;color:#fff'>"
        "Reset Your Password</h2>"
        f"<p style='margin:0 0 18px;color:#94a3b8;font-size:.88rem'>"
        f"Hi <strong style='color:#f5b800'>{display_name}</strong>,<br/>"
        "Enter the code below on the EnejiStats reset-password screen.</p>"
        "<div style='text-align:center;margin:28px 0'>"
        f"<div style='display:inline-block;background:#f5b800;color:#1e1e2f;"
        "padding:18px 48px;border-radius:12px;font-size:2rem;font-weight:900;"
        f"letter-spacing:8px'>{otp}</div></div>"
        "<p style='margin:18px 0 0;font-size:.78rem;color:#64748b'>"
        "This code expires in <strong>10 minutes</strong>. "
        "If you did not request a password reset, ignore this email — "
        "your account is safe.</p>"
    )
    html_body = _email_html("EnejiStats — Reset Your Password", inner_html)
    plain = (
        f"Hi {display_name},\n\nYour EnejiStats password reset code is:\n\n"
        f"  {otp}\n\nThis code expires in 10 minutes.\n"
        "If you did not request a reset, ignore this email.\n\n"
        "— The EnejiStats Team"
    )

    try:
        await send_email(
            to_email=email,
            subject="EnejiStats — Reset Your Password",
            body=plain,
            html_body=html_body,
        )
    except Exception as exc:
        logger.error("[auth] Failed to send reset OTP email to %r: %s", email, exc)

    return otp


# ── Deliver login 2FA OTP ─────────────────────────────────────────────────────

async def _issue_login_2fa_otp(email: str, display_name: str) -> str:
    """
    Generate a 6-digit login 2FA OTP, persist it in password_reset_otps_col
    under purpose='login_2fa' with a 10-minute expiry, and send the email.

    Returns the raw OTP string (internal use only — never forward to client).
    """
    if password_reset_otps_col is None:
        raise RuntimeError("password_reset_otps_col is not initialised.")

    otp     = _generate_otp()
    expires = MongoSerializer.now_utc() + timedelta(minutes=10)

    await password_reset_otps_col.update_one(
        {"email": email, "purpose": "login_2fa"},
        {
            "$set": {
                "email":      email,
                "purpose":    "login_2fa",
                "otp":        otp,
                "expires_at": expires,
                "attempts":   0,
                "used":       False,
                "created_at": MongoSerializer.now_utc(),
            }
        },
        upsert=True,
    )

    inner_html = (
        "<h2 style='margin:0 0 8px;font-size:1.2rem;font-weight:700;color:#fff'>"
        "Login Verification Code</h2>"
        f"<p style='margin:0 0 18px;color:#94a3b8;font-size:.88rem'>"
        f"Hi <strong style='color:#f5b800'>{display_name}</strong>,<br/>"
        "Use the code below to complete your EnejiStats login.</p>"
        "<div style='text-align:center;margin:28px 0'>"
        f"<div style='display:inline-block;background:#f5b800;color:#1e1e2f;"
        "padding:18px 48px;border-radius:12px;font-size:2rem;font-weight:900;"
        f"letter-spacing:8px'>{otp}</div></div>"
        "<p style='margin:18px 0 0;font-size:.78rem;color:#64748b'>"
        "This code expires in <strong>10 minutes</strong>. "
        "If you did not try to log in, please change your password immediately.</p>"
    )
    html_body = _email_html("EnejiStats — Login Verification", inner_html)
    plain = (
        f"Hi {display_name},\n\nYour EnejiStats login verification code is:\n\n"
        f"  {otp}\n\nThis code expires in 10 minutes.\n"
        "If you did not try to log in, secure your account immediately.\n\n"
        "— The EnejiStats Team"
    )

    try:
        await send_email(
            to_email=email,
            subject="EnejiStats — Login Verification Code",
            body=plain,
            html_body=html_body,
        )
    except Exception as exc:
        logger.error("[auth] Failed to send login 2FA OTP email to %r: %s", email, exc)

    return otp


# ── Password complexity validator ─────────────────────────────────────────────

def _validate_new_password(pw: str, email: str = "") -> None:
    """
    Enforces the same complexity rules shown in forgot-password.html:
      • 10+ characters
      • at least one uppercase letter
      • at least one lowercase letter
      • at least one digit
      • at least one special character
      • must not contain the email local-part
    Raises HTTP 422 on the first violation.
    """
    import re as _re
    if not pw or pw != pw.strip():
        raise HTTPException(status_code=422,
            detail="Password cannot start or end with spaces.")
    if len(pw) < 10:
        raise HTTPException(status_code=422,
            detail="Password must be at least 10 characters long.")
    if not _re.search(r"[A-Z]", pw):
        raise HTTPException(status_code=422,
            detail="Password must contain at least one uppercase letter.")
    if not _re.search(r"[a-z]", pw):
        raise HTTPException(status_code=422,
            detail="Password must contain at least one lowercase letter.")
    if not _re.search(r"[0-9]", pw):
        raise HTTPException(status_code=422,
            detail="Password must contain at least one number.")
    if not _re.search(r"[^A-Za-z0-9]", pw):
        raise HTTPException(status_code=422,
            detail="Password must contain at least one special character.")
    local = (email or "").split("@")[0].lower()
    if local and local in pw.lower():
        raise HTTPException(status_code=422,
            detail="Password cannot contain your email address.")




# ── Forgot-password rate limiter (in-memory, per IP) ─────────────────────────
_pw_reset_attempts: dict = {}   # ip → [timestamp, ...]
_PW_RESET_MAX      = 5          # max requests per window
_PW_RESET_WINDOW   = 300        # 5 minutes

def _check_pw_reset_rate(ip: str) -> None:
    now     = _time.time()
    history = _pw_reset_attempts.get(ip, [])
    recent  = [t for t in history if now - t < _PW_RESET_WINDOW]
    _pw_reset_attempts[ip] = recent
    if len(recent) >= _PW_RESET_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many password reset requests. Please wait 5 minutes before trying again.",
        )

def _record_pw_reset(ip: str) -> None:
    h = _pw_reset_attempts.get(ip, [])
    h.append(_time.time())
    _pw_reset_attempts[ip] = h


# ── Timezone-aware datetime comparison ───────────────────────────────────────

def _ensure_aware(dt) -> "datetime":
    """Return a timezone-aware UTC datetime regardless of whether dt is naive."""
    if dt is None:
        return MongoSerializer.now_utc()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── Safe FormData field reader ────────────────────────────────

def _form_str(value: Optional[str], default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _form_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in ("true", "1", "yes")


def _form_json(value: Optional[str], default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default





# ============================================================
# LIVENESS — CHALLENGE CONSTANTS & RATE-LIMIT HELPERS
# ============================================================
_CHALLENGE_WORDS = [
    "EAGLE","LION","FALCON","HAWK","TIGER","COBRA","RAVEN",
    "WOLF","PHOENIX","JAGUAR","PANTHER","VIPER","CHEETAH","BEAR","SHARK",
]
_CHALLENGE_SYMBOLS = ["@","#","$","%","&","!","*"]
_LIVENESS_FAIL_MAX = 5
_liveness_fail_attempts: dict = {}

def _get_client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd: return fwd.split(",")[0].strip()
    return getattr(request.client, "host", "unknown")

async def _check_liveness_rate_limit(client_ip: str) -> None:
    now = _time.time()
    history = _liveness_fail_attempts.get(client_ip, [])
    recent  = [t for t in history if now - t < 600]
    _liveness_fail_attempts[client_ip] = recent
    if len(recent) >= _LIVENESS_FAIL_MAX:
        raise HTTPException(status_code=429,
            detail="Too many failed attempts. Please wait 10 minutes before trying again.")

async def _record_liveness_failure(client_ip: str) -> None:
    h = _liveness_fail_attempts.get(client_ip, [])
    h.append(_time.time())
    _liveness_fail_attempts[client_ip] = h

async def _clear_liveness_failures(client_ip: str) -> None:
    _liveness_fail_attempts.pop(client_ip, None)


# ============================================================
# 1. EMAIL AVAILABILITY CHECK
# ============================================================

@router.get("/api/auth/check-email")
async def check_email_availability(email: str):
    """Return whether an email address is already registered in any collection."""
    if not email or "@" not in email or "." not in email:
        return JSONResponse({"available": False, "exists": True, "reason": "invalid_format"})
    email = normalize_email(email)
    if users_collection is not None:
        try:
            if await users_collection.find_one({"email": email}):
                return JSONResponse({"available": False, "exists": True, "reason": "already_registered"})
        except Exception:
            pass
    for role_name in CANONICAL_ROLES or ():
        col = _role_collection(role_name)
        if col is None:
            continue
        try:
            if await col.find_one({"email": email}):
                return JSONResponse({"available": False, "exists": True, "reason": "already_registered"})
        except Exception:
            pass
    return JSONResponse({"available": True, "exists": False})




def _auth_club_location_clauses(country="", country_code="", state="", region="", lga="", subregion="", city=""):
    """Location predicates matching the fields written by /api/auth/register."""
    clauses=[]
    cc=_form_str(country_code).upper()
    cname=_form_str(country)
    if cc:
        resolved=get_country_name(cc) or ""
        ors=[{"country_code":cc}]
        for value in (cname, resolved):
            if value:
                ors.append({"country":{"$regex":re.escape(value),"$options":"i"}})
        clauses.append({"$or":ors})
    elif cname:
        clauses.append({"$or":[
            {"country":{"$regex":re.escape(cname),"$options":"i"}},
            {"country_code":{"$regex":re.escape(cname),"$options":"i"}},
        ]})
    sv=_form_str(state or region)
    if sv:
        clauses.append({"$or":[
            {"state":{"$regex":re.escape(sv),"$options":"i"}},
            {"region":{"$regex":re.escape(sv),"$options":"i"}},
            {"province":{"$regex":re.escape(sv),"$options":"i"}},
            {"county":{"$regex":re.escape(sv),"$options":"i"}},
        ]})
    lv=_form_str(lga or subregion)
    if lv:
        clauses.append({"$or":[
            {"lga":{"$regex":re.escape(lv),"$options":"i"}},
            {"local_area":{"$regex":re.escape(lv),"$options":"i"}},
            {"subregion":{"$regex":re.escape(lv),"$options":"i"}},
            {"district":{"$regex":re.escape(lv),"$options":"i"}},
        ]})
    cv=_form_str(city)
    if cv:
        clauses.append({"$or":[
            {"city":{"$regex":re.escape(cv),"$options":"i"}},
            {"town":{"$regex":re.escape(cv),"$options":"i"}},
        ]})
    return clauses


async def _auth_resolve_registered_venue(venue_id):
    """Resolve primary_ground_id/secondary_ground_id against the registered venue collection."""
    vid=_form_str(venue_id)
    if not vid or venues_collection is None:
        return None
    ors=[{"venue_id":vid},{"id":vid}]
    try:
        ors.insert(0,{"_id":ObjectId(vid)})
    except Exception:
        pass
    try:
        doc=await venues_collection.find_one({"$or":ors})
    except Exception:
        doc=None
    return MongoSerializer.serialize_document(doc) if doc else None


def _auth_venue_name(v):
    if not v: return ""
    return str(v.get("venue_name") or v.get("name") or v.get("stadium") or v.get("ground_name") or v.get("field_name") or "").strip()


def _auth_venue_address(v):
    if not v: return ""
    return str(v.get("full_address") or v.get("address") or v.get("venue_address") or v.get("stadium_address") or v.get("ground_address") or v.get("field_address") or "").strip()


def _auth_num(v):
    if v in (None, ""): return None
    try: return float(v)
    except (TypeError, ValueError): return v


def _auth_merge_registered_venue(club, venue, secondary=False):
    """Merge canonical venue data with the club registration snapshot."""
    if secondary:
        name=_auth_venue_name(venue) or str(club.get("stadium2") or "").strip()
        address=_auth_venue_address(venue) or str(club.get("stadium2_address") or "").strip()
        lat=_auth_num((venue or {}).get("gps_lat") if (venue or {}).get("gps_lat") not in (None,"") else club.get("stadium_gps2_lat"))
        lng=_auth_num((venue or {}).get("gps_lng") if (venue or {}).get("gps_lng") not in (None,"") else club.get("stadium_gps2_lng"))
        ref=club.get("secondary_ground_id")
    else:
        name=_auth_venue_name(venue) or str(club.get("stadium") or "").strip()
        address=_auth_venue_address(venue) or str(club.get("stadium_address") or "").strip()
        lat=_auth_num((venue or {}).get("gps_lat") if (venue or {}).get("gps_lat") not in (None,"") else club.get("stadium_gps_lat"))
        lng=_auth_num((venue or {}).get("gps_lng") if (venue or {}).get("gps_lng") not in (None,"") else club.get("stadium_gps_lng"))
        ref=club.get("primary_ground_id")
    if not name: return None
    vid=str((venue or {}).get("venue_id") or (venue or {}).get("id") or (venue or {}).get("_id") or ref or "")
    country=(venue or {}).get("country") or club.get("country") or ""
    code=str((venue or {}).get("country_code") or club.get("country_code") or "").upper()
    state=(venue or {}).get("state") or (venue or {}).get("region") or club.get("state") or ""
    lga=(venue or {}).get("lga") or club.get("lga") or ""
    city=(venue or {}).get("city") or (venue or {}).get("town") or club.get("city") or ""
    gps={"lat":lat,"lng":lng} if lat is not None and lng is not None else None
    return {
        "id":vid,"venue_id":vid,"name":name,"venue_name":name,"stadium":name,"home_ground":name,
        "address":address,"full_address":address,"venue_address":address,"venue_full_address":address,
        "country":country,"country_code":code,"state":state,"region":state,"lga":lga,"city":city,
        "venue_country":country,"venue_country_code":code,"venue_state":state,"venue_lga":lga,"venue_city":city,
        "gps":gps,"venue_gps":gps,"gps_lat":lat,"gps_lng":lng,"venue_gps_lat":lat,"venue_gps_lng":lng,
        "capacity":(venue or {}).get("capacity"),"venue_type":(venue or {}).get("venue_type"),
        "surface_type":(venue or {}).get("surface_type"),"photo_url":(venue or {}).get("photo_url"),
        "registered_by_dco_id":(venue or {}).get("registered_by_dco_id"),
        "registered_by_dco_name":(venue or {}).get("registered_by_dco_name"),
        "source":"registered_venue" if venue else "club_registration_snapshot",
    }


@router.get("/api/public/clubs")
async def public_clubs(
    search: str = "", q: str = "", level: str = "", category: str = "",
    country: str = "", country_code: str = "", state: str = "", region: str = "",
    lga: str = "", subregion: str = "", city: str = "",
    page: int = Query(1, ge=1), limit: int = Query(30, ge=1, le=100),
):
    """Public club directory using the exact registration-backed club/venue schema."""
    _assert_deps_ready()
    query_text=(search or q).strip()
    clauses=[]
    if query_text:
        safe=re.escape(query_text)
        clauses.append({"$or":[
            {"club_name":{"$regex":safe,"$options":"i"}},
            {"club_nickname":{"$regex":safe,"$options":"i"}},
            {"team_name":{"$regex":safe,"$options":"i"}},
            {"name":{"$regex":safe,"$options":"i"}},
            {"full_name":{"$regex":safe,"$options":"i"}},
            {"club_id":{"$regex":safe,"$options":"i"}},
        ]})
    lv=(level or category).strip()
    if lv:
        safe=re.escape(lv)
        clauses.append({"$or":[
            {"club_level":{"$regex":safe,"$options":"i"}},
            {"category":{"$regex":safe,"$options":"i"}},
            {"level":{"$regex":safe,"$options":"i"}},
        ]})
    clauses.extend(_auth_club_location_clauses(country,country_code,state,region,lga,subregion,city))
    query={"$and":clauses} if clauses else {}
    skip=(page-1)*limit
    total=await clubs_collection.count_documents(query)
    rows=await clubs_collection.find(query).sort("club_name",1).skip(skip).limit(limit).to_list(length=limit)
    clubs=[]
    for row in rows:
        item=MongoSerializer.serialize_document(row)
        cid=str(item.get("club_id") or item.get("user_id") or item.get("_id") or "")
        primary_doc=await _auth_resolve_registered_venue(item.get("primary_ground_id"))
        secondary_doc=await _auth_resolve_registered_venue(item.get("secondary_ground_id"))
        primary=_auth_merge_registered_venue(item,primary_doc,False)
        secondary=_auth_merge_registered_venue(item,secondary_doc,True)
        p=primary or {}
        clubs.append({
            **item,
            "id":cid,"name":item.get("club_name") or item.get("full_name") or item.get("name") or "",
            "club_name":item.get("club_name") or item.get("full_name") or item.get("name") or "",
            "team_name":item.get("team_name") or item.get("club_name") or item.get("full_name") or "",
            "level":item.get("club_level") or item.get("category") or item.get("level") or "",
            "nickname":item.get("club_nickname") or "",
            "country":item.get("country") or "","country_code":str(item.get("country_code") or "").upper(),
            "state":item.get("state") or item.get("region") or item.get("province") or item.get("county") or "",
            "lga":item.get("lga") or item.get("local_area") or item.get("subregion") or item.get("district") or "",
            "city":item.get("city") or item.get("town") or "",
            "primary_ground_id":p.get("id") or item.get("primary_ground_id"),"secondary_ground_id":(secondary or {}).get("id") or item.get("secondary_ground_id"),
            "primary_ground":primary,"secondary_ground":secondary,
            "home_ground":p.get("name") or item.get("stadium") or "",
            "venue_id":p.get("id") or item.get("primary_ground_id") or "",
            "venue_name":p.get("name") or item.get("stadium") or "",
            "stadium":p.get("name") or item.get("stadium") or "",
            "venue_address":p.get("address") or item.get("stadium_address") or "",
            "venue_full_address":p.get("full_address") or item.get("stadium_address") or "",
            "venue_country":p.get("country") or item.get("country") or "",
            "venue_country_code":str(p.get("country_code") or item.get("country_code") or "").upper(),
            "venue_state":p.get("state") or item.get("state") or "",
            "venue_lga":p.get("lga") or item.get("lga") or "",
            "venue_city":p.get("city") or item.get("city") or "",
            "venue_gps_lat":p.get("gps_lat"),"venue_gps_lng":p.get("gps_lng"),"venue_gps":p.get("gps"),
            "gps_lat":p.get("gps_lat") if p.get("gps_lat") is not None else item.get("stadium_gps_lat"),
            "gps_lng":p.get("gps_lng") if p.get("gps_lng") is not None else item.get("stadium_gps_lng"),
            "gps":p.get("gps") or ({"lat":item.get("stadium_gps_lat"),"lng":item.get("stadium_gps_lng")} if item.get("stadium_gps_lat") not in (None,"") and item.get("stadium_gps_lng") not in (None,"") else None),
            "venue_type":p.get("venue_type") or "","surface_type":p.get("surface_type") or "","capacity":p.get("capacity"),
            "logo_url":item.get("logo_url") or item.get("logo") or item.get("avatar") or item.get("badge") or "",
            "secondary_venue_id":(secondary or {}).get("id") or item.get("secondary_ground_id") or "",
            "secondary_venue_name":(secondary or {}).get("name") or item.get("stadium2") or "",
            "secondary_venue_address":(secondary or {}).get("address") or item.get("stadium2_address") or "",
            "secondary_venue_gps_lat":(secondary or {}).get("gps_lat"),"secondary_venue_gps_lng":(secondary or {}).get("gps_lng"),
            "secondary_venue_gps":(secondary or {}).get("gps"),
        })
    pages=max(1,(total+limit-1)//limit) if total else 0
    return JSONResponse({"clubs":clubs,"results":clubs,"data":clubs,"total":total,"pages":pages,"page":page})


@router.get("/api/config/club-levels")
async def config_club_levels():
    return JSONResponse(
        {"levels": ["Professional", "Semi-professional", "Academy", "University", "Local"]}
    )



# ============================================================
# 3. LIVENESS — CHALLENGE-PHRASE SESSION
# ============================================================

@router.post("/api/liveness/session")
async def create_liveness_challenge_session():
    """
    Generate a server-issued challenge phrase (e.g. "EAGLE@4-LION#72").
    Phrase expires in 90 s; enforced by /api/liveness/complete.
    """
    w1  = random.choice(_CHALLENGE_WORDS)
    w2  = random.choice([x for x in _CHALLENGE_WORDS if x != w1])
    sc1 = random.choice(_CHALLENGE_SYMBOLS)
    sc2 = random.choice([x for x in _CHALLENGE_SYMBOLS if x != sc1])
    d1  = random.randint(1, 9)
    d2  = random.randint(10, 99)

    phrase     = f"{w1}{sc1}{d1}-{w2}{sc2}{d2}"
    session_id = f"LVC-{secrets.token_hex(12).upper()}"

    await liveness_sessions_collection.insert_one({
        "session_id":       session_id,
        "challenge_phrase": phrase,
        "status":           "pending",
        "type":             "challenge_phrase",
        "created_at":       MongoSerializer.now_utc(),
    })
    logger.info("[liveness/session] Created: %s", session_id)
    return JSONResponse({"session_id": session_id, "challenge_phrase": phrase})


@router.post("/api/liveness/complete")
async def complete_liveness_challenge_session(request: Request):
    """
    Validate challenge_response against the stored phrase (case-insensitive
    after normalisation). On success marks session as completed (single-use)
    and returns a signed liveness_token JWT valid for 2 hours.

    Body: ``{"session_id": "...", "challenge_response": "..."}``
    """
    client_ip = _get_client_ip(request)

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    session_id         = (data.get("session_id") or "").strip()
    challenge_response = (data.get("challenge_response") or "").strip().upper()

    if not session_id or not challenge_response:
        raise HTTPException(
            status_code=400,
            detail="session_id and challenge_response are required",
        )

    await _check_liveness_rate_limit(client_ip)

    session = await liveness_sessions_collection.find_one(
        {"session_id": session_id, "type": "challenge_phrase"}
    )
    if not session:
        await _record_liveness_failure(client_ip)
        raise HTTPException(status_code=400, detail="Invalid or expired liveness session")

    if session.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Liveness session already used")

    created_at = session.get("created_at")
    if created_at:
        aware_ts   = MongoSerializer.ensure_timezone_aware(created_at)
        age_seconds = (MongoSerializer.now_utc() - aware_ts).total_seconds()
        if age_seconds > 90:
            raise HTTPException(
                status_code=400,
                detail="Challenge phrase has expired. Please start the liveness check again.",
            )

    expected = session.get("challenge_phrase", "").strip().upper()
    if challenge_response != expected:
        await _record_liveness_failure(client_ip)
        history   = _liveness_fail_attempts.get(client_ip, [])
        remaining = max(_LIVENESS_FAIL_MAX - len(history), 0)
        logger.warning(
            "[liveness/complete] Phrase mismatch from %s (session %s); %d attempt(s) remaining",
            client_ip, session_id, remaining,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Incorrect challenge phrase. "
                f"{remaining} attempt(s) remaining before your IP is temporarily blocked."
            ),
        )

    await liveness_sessions_collection.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed", "completed_at": MongoSerializer.now_utc()}},
    )
    await _clear_liveness_failures(client_ip)

    now_ts = int(MongoSerializer.now_utc().timestamp())
    liveness_token = jwt.encode(
        {"sub": session_id, "type": "liveness_verification",
         "iat": now_ts, "exp": now_ts + 7200},
        SECRET_KEY, algorithm=ALGORITHM,
    )
    logger.info("[liveness/complete] Verified: %s from %s", session_id, client_ip)
    return JSONResponse({
        "status":         "verified",
        "liveness_token": liveness_token,
        "message":        "Liveness verified successfully",
    })


# ============================================================
# REGISTRATION ENDPOINT — unified, role-dispatched
# ============================================================

@router.post("/api/auth/register")
async def register(
    request:  Request,
    role:     str           = Form(...),
    email:    str           = Form(...),
    password: str           = Form(...),
    confirm_password: Optional[str] = Form(None),
    phone:    Optional[str] = Form(None),
    whatsapp: Optional[str] = Form(None),
    country:  Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    state:    Optional[str] = Form(None),
    lga:      Optional[str] = Form(None),

    # Liveness / consent
    liveness_verified:  Optional[str] = Form(None),
    liveness_token:     Optional[str] = Form(None),
    gps_lat:            Optional[str] = Form(None),
    gps_lng:            Optional[str] = Form(None),
    gps_acc:            Optional[str] = Form(None),
    terms_accepted_at:  Optional[str] = Form(None),
    privacy_policy:     Optional[str] = Form(None),
    terms_of_service:   Optional[str] = Form(None),
    privacy_accepted:   Optional[str] = Form(None),
    terms_accepted:     Optional[str] = Form(None),

    # Player-specific
    player_level:         Optional[str] = Form(None),
    first_name:           Optional[str] = Form(None),
    middle_name:          Optional[str] = Form(None),
    last_name:            Optional[str] = Form(None),
    dob:                  Optional[str] = Form(None),
    dob_visible:          Optional[str] = Form(None),
    gender:               Optional[str] = Form(None),
    height:               Optional[str] = Form(None),
    weight:               Optional[str] = Form(None),
    nationality:          Optional[str] = Form(None),
    dominant_foot:        Optional[str] = Form(None),
    position_category:    Optional[str] = Form(None),
    preferred_position:   Optional[str] = Form(None),
    secondary_positions:  Optional[str] = Form(None),   # JSON array string
    club_id:              Optional[str] = Form(None),
    current_club:         Optional[str] = Form(None),

    # Club-specific
    full_name:             Optional[str] = Form(None),
    club_level:            Optional[str] = Form(None),
    club_name:             Optional[str] = Form(None),
    city:                  Optional[str] = Form(None),
    founded:               Optional[str] = Form(None),
    stadium:               Optional[str] = Form(None),
    club_email:            Optional[str] = Form(None),
    club_phone:            Optional[str] = Form(None),
    website:               Optional[str] = Form(None),
    stadium_gps_lat:       Optional[str] = Form(None),
    stadium_gps_lng:       Optional[str] = Form(None),
    is_registered:         Optional[str] = Form(None),
    cac_number:            Optional[str] = Form(None),
    club_nickname:         Optional[str] = Form(None),
    stadium_address:       Optional[str] = Form(None),
    has_secondary_stadium: Optional[str] = Form(None),
    stadium2:              Optional[str] = Form(None),
    stadium2_address:      Optional[str] = Form(None),
    stadium_gps2_lat:      Optional[str] = Form(None),
    stadium_gps2_lng:      Optional[str] = Form(None),
    # Venue-record references (IDs stored in the venues/grounds collection)
    primary_ground_id:     Optional[str] = Form(None),
    secondary_ground_id:   Optional[str] = Form(None),
    # Club office / HQ GPS (separate from the primary stadium GPS)
    club_office_gps_lat:   Optional[str] = Form(None),
    club_office_gps_lng:   Optional[str] = Form(None),
    club_office_gps_acc:   Optional[str] = Form(None),

    # Scout-specific
    affiliation_type:      Optional[str] = Form(None),
    affiliated_club:       Optional[str] = Form(None),
    role_in_org:           Optional[str] = Form(None),
    operating_region:      Optional[str] = Form(None),
    years_experience:      Optional[str] = Form(None),
    specialization:        Optional[str] = Form(None),
    linkedin:              Optional[str] = Form(None),
    instagram:             Optional[str] = Form(None),
    bio:                   Optional[str] = Form(None),

    # Agent-specific
    account_type:          Optional[str] = Form(None),
    fifa_license:          Optional[str] = Form(None),
    agency_name:           Optional[str] = Form(None),
    registration_number:   Optional[str] = Form(None),
    country_of_registration: Optional[str] = Form(None),

    # DCO / Supervisor
    languages:             Optional[str] = Form(None),   # JSON array string
    education_level:       Optional[str] = Form(None),
    applicant_type:        Optional[str] = Form(None),
    states_of_operation:   Optional[str] = Form(None),  # JSON array string

    # Shared — all roles
    detailed_address:      Optional[str] = Form(None),

    # Legal acceptance record (JSON string — rendered & hashed by the frontend)
    legal_acceptance:      Optional[str] = Form(None),

    # DCO registration-subtab may explicitly bypass the standalone registration
    # email OTP. This is NOT trusted by itself: below it is accepted only when
    # the request is authenticated as a DCO and the target role is player/club.
    skip_registration_otp: Optional[str] = Form(None),

    # DCO-registration metadata (optional — sent only when DCO registers on behalf of player/club)
    registered_by:         Optional[str] = Form(None),   # e.g. "dco"
    registered_by_dco_id:  Optional[str] = Form(None),
    registered_by_dco_name: Optional[str] = Form(None),
    registered_by_dco_email: Optional[str] = Form(None),
    registered_by_dco_country_code: Optional[str] = Form(None),
    registered_by_dco_country: Optional[str] = Form(None),
    registered_by_dco_state: Optional[str] = Form(None),
    registered_by_dco_lga: Optional[str] = Form(None),

    # File uploads
    photo: Optional[UploadFile] = File(None),
    logo:  Optional[UploadFile] = File(None),
    cv:    Optional[UploadFile] = File(None),
):
    """
    Unified registration endpoint for all self-registering roles:
      player, club, scout, agent, dco, supervisor

    Accepts multipart/form-data.  Returns:
      { requires_otp: true, user_id, role, email, name }
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[register] ENTRY | role=%r | email=%r | phone_provided=%r "
        "| liveness_verified=%r | photo=%r | logo=%r | cv=%r",
        role, email, bool(phone), liveness_verified,
        photo.filename if photo else None,
        logo.filename  if logo  else None,
        cv.filename    if cv    else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    # ── 1. Validate role ─────────────────────────────────────
    ALLOWED_REGISTRATION_ROLES = {"player", "club", "scout", "agent", "dco", "supervisor"}
    role = _canonical_role(_form_str(role))
    if role not in ALLOWED_REGISTRATION_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Must be one of: {', '.join(sorted(ALLOWED_REGISTRATION_ROLES))}",
        )

    # ── 2. Validate required fields ──────────────────────────
    email    = normalize_email(_form_str(email))
    password = _form_str(password)
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    if confirm_password is not None and _form_str(confirm_password) != password:
        raise HTTPException(status_code=422, detail="Passwords do not match.")

    # ── 2c. Resolve registered_by from authenticated context ─
    # registered_by_* fields are accepted from form input ONLY when the
    # caller is an authenticated DCO. Unauthenticated callers (self-
    # registration) may not spoof DCO attribution.
    _caller_dco_id   = None
    _caller_dco_name = None
    try:
        _caller = await get_current_user(request)
        _caller_role = _canonical_role(_caller.get("role") or "")
        if _caller_role == "dco":
            _caller_dco_id   = (
                _caller.get("dco_id")
                or _caller.get("user_id")
                or str(_caller.get("_id", ""))
            )
            _caller_dco_name = (
                _caller.get("full_name")
                or _caller.get("name")
                or _caller.get("email")
                or ""
            )
    except Exception:
        pass   # unauthenticated or token missing — that is fine for self-registration

    # Stamp from server context; ignore client-supplied values when no DCO is authenticated
    if _caller_dco_id:
        registered_by         = "dco"
        registered_by_dco_id  = _caller_dco_id
        registered_by_dco_name = _caller_dco_name or _form_str(registered_by_dco_name)
    else:
        # Unauthenticated caller — wipe any DCO attribution from form input
        registered_by         = None
        registered_by_dco_id  = None
        registered_by_dco_name = None

    # Registration-subtab OTP bypass is deliberately server-authorized.
    # A browser cannot self-authorize this merely by posting the flag.
    skip_registration_otp_requested = _form_bool(skip_registration_otp)
    skip_registration_otp_allowed = bool(
        skip_registration_otp_requested
        and _caller_dco_id
        and role in {"player", "club"}
    )

    # ── 2b. Role-specific required-field validation ───────────
    def _require(val, field_label: str):
        if not _form_str(val):
            raise HTTPException(status_code=422, detail=f"{field_label} is required.")

    if role == "player":
        _require(first_name,         "First name")
        _require(last_name,          "Last name")
        _require(dob,                "Date of birth")
        _require(gender,             "Gender")
        # height and weight are optional for DCO-registered players
        _require(dominant_foot,      "Dominant foot")
        _require(player_level,       "Player level")
        # position_category is recommended but can be derived from preferred_position
        _require(preferred_position, "Preferred position")

    elif role == "club":
        _require(club_name,      "Club name")
        _require(club_level,     "Club level")
        _require(city,           "City / District")
        _require(stadium,        "Stadium / Home Ground name")
        # stadium_address is auto-populated from the selected venue record;
        # no separate manual entry is required or enforced.

    elif role == "scout":
        _require(full_name,        "Full name")
        _require(affiliation_type, "Affiliation type")
        _require(years_experience, "Years of experience")

    elif role == "agent":
        _require(account_type,     "Account type")
        _require(years_experience, "Years of experience")

    elif role in ("dco", "supervisor"):
        _require(full_name,       "Full name")
        _require(dob,             "Date of birth")
        _require(gender,          "Gender")
        _require(education_level, "Educational qualification")

    # ── Shared: location fields mandatory for ALL roles ───────────────────
    _require(country or country_code,  "Country")
    _require(state,    "State / Region")
    _require(lga,      "LGA / Local area")
    # Clubs get their address from the selected venue record (auto-populated);
    # all other roles must supply a street / detailed address explicitly.
    if role != "club":
        _require(detailed_address, "Street / detailed address")

    # ── 3/4. Duplicate protection and password hashing are owned by
    # main.py's canonical create_platform_user() service.

    # ── 5. Upload files to Cloudinary ────────────────────────
    photo_url = None
    logo_url  = None
    cv_url    = None

    _REG_VIDEO_EXTS: frozenset = frozenset({
        ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
        ".flv", ".wmv", ".3gp", ".ogv",
    })
    _REG_IMAGE_EXTS: frozenset = frozenset({
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
        ".tiff", ".tif", ".heic", ".heif",
    })

    async def _upload(upload_file: UploadFile, folder: str) -> Optional[str]:
        """
        Upload a single registration file (photo, logo, CV) to Cloudinary.

        Fixes vs. original
        ──────────────────
        • resource_type is derived from the filename extension so photos are
          stored as ``"image"`` and video CVs as ``"video"``.
        • Empty file bytes are skipped rather than forwarded to Cloudinary.
        • Returns None (non-fatal) on any upload error so registration
          can complete even when Cloudinary is unreachable.
        """
        if not upload_file or not upload_file.filename:
            return None
        try:
            data = await upload_file.read()
            if not data:
                logger.warning(
                    "[register] Skipping empty file upload for %r",
                    upload_file.filename,
                )
                return None
            _ext   = os.path.splitext(upload_file.filename.lower())[1]
            _rtype = (
                "video" if _ext in _REG_VIDEO_EXTS
                else "image" if _ext in _REG_IMAGE_EXTS
                else "auto"
            )
            result = await upload_to_cloudinary(
                data,
                filename=upload_file.filename,
                folder=folder,
                resource_type=_rtype,
            )
            if isinstance(result, str):
                return result
            if isinstance(result, dict):
                return result.get("secure_url") or result.get("url")
            return None
        except Exception as exc:
            logger.warning(
                "[register] Cloudinary upload failed for %r: %s",
                upload_file.filename, exc,
            )
            return None

    if photo:
        photo_url = await _upload(photo, f"enejistats/{role}/photos")
    if logo:
        logo_url  = await _upload(logo,  "enejistats/clubs/logos")
    if cv:
        cv_url    = await _upload(cv,    f"enejistats/{role}/cvs")

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[register] UPLOADS | photo_url=%r | logo_url=%r | cv_url=%r",
        photo_url, logo_url, cv_url,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    # ── 6. Generate the canonical public ID ─────────────────
    level_for_id = _form_str(
        player_level if role == "player" else club_level if role == "club" else ""
    )
    # ── 7. Build module-specific fields ───────────────────────
    now = MongoSerializer.now_utc()
    resolved_country_code = _form_str(country_code) or _form_str(country)
    resolved_country_name = _form_str(country) or resolved_country_code
    resolved_privacy_accepted = _form_bool(
        privacy_accepted if privacy_accepted is not None else privacy_policy
    )
    resolved_terms_accepted = _form_bool(
        terms_accepted if terms_accepted is not None else terms_of_service
    )
    common_fields = {
        "phone": _form_str(phone), "whatsapp": _form_str(whatsapp) or _form_str(phone),
        "country": _form_str(resolved_country_name, "NG"), "country_code": resolved_country_code,
        "state": _form_str(state), "lga": _form_str(lga),
        "liveness_verified": _form_bool(liveness_verified), "liveness_token": _form_str(liveness_token),
        "gps_lat": _form_str(gps_lat) or None, "gps_lng": _form_str(gps_lng) or None,
        "gps_acc": _form_str(gps_acc) or None, "terms_accepted_at": _form_str(terms_accepted_at),
        "privacy_policy": resolved_privacy_accepted, "privacy_accepted": resolved_privacy_accepted,
        "terms_of_service": resolved_terms_accepted, "terms_accepted": resolved_terms_accepted,
        "legal_acceptance": _form_json(legal_acceptance),
        "is_verified": bool(skip_registration_otp_allowed),
        "email_verified": bool(skip_registration_otp_allowed),
        "created_at": now, "updated_at": now,
    }

    # ── 8. Build role-specific document fields ────────────────
    if role == "player":
        display_name = " ".join(filter(None, [_form_str(first_name), _form_str(middle_name), _form_str(last_name)])).strip() or email
        role_doc = {
            "player_level": _form_str(player_level), "first_name": _form_str(first_name),
            "middle_name": _form_str(middle_name), "last_name": _form_str(last_name), "full_name": display_name,
            "dob": _form_str(dob), "dob_visible": _form_bool(dob_visible, True), "gender": _form_str(gender),
            "height": _form_str(height), "weight": _form_str(weight), "nationality": _form_str(nationality),
            "dominant_foot": _form_str(dominant_foot), "position_category": _form_str(position_category),
            "preferred_position": _form_str(preferred_position), "secondary_positions": _form_json(secondary_positions, []),
            "club_id": _form_str(club_id), "current_club": _form_str(current_club),
            "avatar": photo_url, "profile_photo": photo_url, "detailed_address": _form_str(detailed_address),
            "subscription_status": "trial", "performance_score": 0.0, "stats_requests_count": 0,
            "registered_by": _form_str(registered_by), "registered_by_dco_id": _form_str(registered_by_dco_id),
            "registered_by_dco_name": _form_str(registered_by_dco_name),
            "primary_ground_id": _form_str(primary_ground_id) or None, "secondary_ground_id": _form_str(secondary_ground_id) or None,
            "club_office_gps_lat": _form_str(club_office_gps_lat) or None, "club_office_gps_lng": _form_str(club_office_gps_lng) or None,
            "club_office_gps_acc": _form_str(club_office_gps_acc) or None,
        }
    elif role == "club":
        display_name = _form_str(club_name) or _form_str(full_name) or email
        _ir = _form_str(is_registered or "")
        registered_flag = _ir.lower() in ("registered", "true", "1", "yes")
        role_doc = {
            "full_name": _form_str(full_name), "club_name": _form_str(club_name), "club_nickname": _form_str(club_nickname),
            "club_level": _form_str(club_level), "city": _form_str(city), "founded": _form_str(founded),
            "stadium": _form_str(stadium), "stadium_address": _form_str(stadium_address),
            "has_secondary_stadium": _form_bool(has_secondary_stadium), "stadium2": _form_str(stadium2),
            "stadium2_address": _form_str(stadium2_address), "stadium_gps2_lat": _form_str(stadium_gps2_lat) or None,
            "stadium_gps2_lng": _form_str(stadium_gps2_lng) or None, "club_email": _form_str(club_email) or email,
            "club_phone": _form_str(club_phone) or _form_str(phone), "website": _form_str(website),
            "stadium_gps_lat": _form_str(stadium_gps_lat) or None, "stadium_gps_lng": _form_str(stadium_gps_lng) or None,
            "is_registered": registered_flag, "cac_number": _form_str(cac_number) if registered_flag else "",
            "logo": logo_url, "avatar": logo_url, "approval_status": "pending", "subscription_status": "trial",
            "registered_by": _form_str(registered_by), "registered_by_dco_id": _form_str(registered_by_dco_id),
            "registered_by_dco_name": _form_str(registered_by_dco_name),
            "primary_ground_id": _form_str(primary_ground_id) or None, "secondary_ground_id": _form_str(secondary_ground_id) or None,
            "club_office_gps_lat": _form_str(club_office_gps_lat) or None, "club_office_gps_lng": _form_str(club_office_gps_lng) or None,
            "club_office_gps_acc": _form_str(club_office_gps_acc) or None,
        }
    elif role == "scout":
        display_name = _form_str(full_name) or email
        role_doc = {
            "full_name": display_name, "dob": _form_str(dob), "nationality": _form_str(nationality), "gender": _form_str(gender),
            "affiliation_type": _form_str(affiliation_type), "affiliated_club": _form_str(affiliated_club), "role_in_org": _form_str(role_in_org),
            "operating_region": _form_str(operating_region), "years_experience": _form_str(years_experience), "specialization": _form_str(specialization),
            "linkedin": _form_str(linkedin), "instagram": _form_str(instagram), "bio": _form_str(bio), "avatar": photo_url, "cv_url": cv_url,
            "detailed_address": _form_str(detailed_address), "subscription_status": "trial",
        }
    elif role == "agent":
        display_name = _form_str(full_name) or email
        role_doc = {
            "full_name": display_name, "account_type": _form_str(account_type), "dob": _form_str(dob), "nationality": _form_str(nationality),
            "gender": _form_str(gender), "fifa_license": _form_str(fifa_license), "agency_name": _form_str(agency_name),
            "registration_number": _form_str(registration_number), "country_of_registration": _form_str(country_of_registration),
            "website": _form_str(website), "instagram": _form_str(instagram), "linkedin": _form_str(linkedin),
            "years_experience": _form_str(years_experience), "bio": _form_str(bio), "avatar": photo_url, "cv_url": cv_url,
            "detailed_address": _form_str(detailed_address), "subscription_status": "trial",
        }
    elif role == "dco":
        display_name = _form_str(full_name) or email
        role_doc = {
            "full_name": display_name, "dob": _form_str(dob), "gender": _form_str(gender), "languages": _form_str(languages),
            "education_level": _form_str(education_level), "applicant_type": "dco", "avatar": photo_url,
            "detailed_address": _form_str(detailed_address), "approval_status": "pending",
        }
    elif role == "supervisor":
        display_name = _form_str(full_name) or email
        role_doc = {
            "full_name": display_name, "dob": _form_str(dob), "gender": _form_str(gender), "languages": _form_str(languages),
            "states_of_operation": _form_json(states_of_operation, []), "years_experience": _form_str(years_experience),
            "education_level": _form_str(education_level), "applicant_type": "supervisor", "avatar": photo_url,
            "detailed_address": _form_str(detailed_address), "approval_status": "pending",
        }
    else:
        display_name = email
        role_doc = {}

    extra_fields = {**common_fields, **role_doc}

    # ── 9. Canonical identity creation + DCO token charge ─────
    dco_charge = 0.0
    if _caller_dco_id and role in {"player", "club"}:
        level = player_level if role == "player" else club_level
        dco_charge = _dco_registration_token_cost(role, level)
        await _consume_dco_registration_tokens(_caller_dco_id, dco_charge, f"DCO registration of {role} at {level}")

    try:
        document = await create_platform_user(
            role=role, email=email, password=password,
            first_name=_form_str(first_name), last_name=_form_str(last_name), middle_name=_form_str(middle_name),
            player_level=level_for_id, extra_fields=extra_fields, create_general_account=True,
        )
    except ValueError as exc:
        if dco_charge:
            await _refund_dco_registration_tokens(_caller_dco_id, dco_charge, f"Refund for failed DCO registration of {role}")
        detail = str(exc)
        if "already exists" in detail.lower():
            raise HTTPException(status_code=409, detail=detail) from exc
        raise HTTPException(status_code=422, detail=detail) from exc
    except DuplicateKeyError as exc:
        if dco_charge:
            await _refund_dco_registration_tokens(_caller_dco_id, dco_charge, f"Refund for failed DCO registration of {role}")
        raise HTTPException(status_code=409, detail="An account with this email or public ID already exists.") from exc
    except Exception:
        if dco_charge:
            await _refund_dco_registration_tokens(_caller_dco_id, dco_charge, f"Refund for failed DCO registration of {role}")
        raise

    user_id = str(document.get("user_id") or document.get(_role_id_field(role)) or "")
    mongo_id = str(document.get("_id", ""))
    if not user_id:
        raise HTTPException(status_code=500, detail="Canonical user creation returned no public user ID.")
    if skip_registration_otp_allowed and users_collection is not None:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"email_verified": True, "updated_at": MongoSerializer.now_utc()}},
        )

    # ── 10. Bootstrap token wallet ───────────────────────────
    try:
        await _bootstrap_token_wallet(role, user_id, mongo_id)
    except Exception as exc:
        logger.warning("[register] Token wallet bootstrap failed for %r:%r: %s", role, user_id, exc)

    # ── 11. Registration email OTP ──────────────────────────
    # Standalone/public registration keeps the existing OTP flow unchanged.
    # DCO registration-subtab player/club creation deliberately bypasses it.
    if not skip_registration_otp_allowed:
        try:
            otp_raw = await _issue_registration_otp(
                user_id=user_id,
                role=role,
                email=email,
                display_name=display_name,
            )
            # ── DEBUG BLOCK START ────────────────────────────────────────────────
            logger.debug(
                "[register] OTP ISSUED | user_id=%r | email=%r | otp_len=%d",
                user_id, email, len(otp_raw),
            )
            # ── DEBUG BLOCK END ──────────────────────────────────────────────────
        except Exception as exc:
            logger.error("[register] OTP issue failed: %s", exc)

        return JSONResponse({
            "requires_otp": True,
            "user_id":      user_id,
            "role":         role,
            "email":        email,
            "name":         display_name,
            "message":      "Account created. Enter the 6-digit code sent to your email.",
        }, status_code=201)

    logger.info(
        "[register] DCO SUBTAB REGISTRATION | role=%r | user_id=%r | "
        "registration OTP/email bypassed",
        role, user_id,
    )
    return JSONResponse({
        "requires_otp": False,
        "user_id":      user_id,
        "role":         role,
        "email":        email,
        "name":         display_name,
        "email_verified": True,
        "message":      "Account created successfully.",
    }, status_code=201)


# ============================================================
# DCO VENUE REGISTRATION / LIST / UPDATE
# ============================================================

async def _require_dco_user(request: Request) -> Dict[str, Any]:
    """Resolve the authenticated DCO for venue-scoped operations."""
    _assert_deps_ready()
    if not callable(get_current_user):
        raise HTTPException(status_code=503, detail="Authentication is not initialised.")
    try:
        actor = await get_current_user(request)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="DCO authentication is required.")
    if not actor or str(actor.get("role", "")).lower() != "dco":
        raise HTTPException(status_code=403, detail="Only authenticated DCO users may manage venues.")
    return actor


def _dco_identity(actor: Dict[str, Any]) -> tuple[str, str]:
    actor_id = str(
        actor.get("dco_id")
        or actor.get("user_id")
        or actor.get("_id")
        or actor.get("id")
        or ""
    )
    actor_name = str(
        actor.get("full_name")
        or actor.get("name")
        or actor.get("email")
        or ""
    )
    if not actor_id:
        raise HTTPException(status_code=401, detail="Authenticated DCO identity is missing.")
    return actor_id, actor_name


def _cloudinary_upload_is_disabled(error: Exception) -> bool:
    """Identify Cloudinary account/configuration failures that cannot be retried."""
    message = str(error).lower()
    return (
        "uploading is disabled" in message
        or "upload is disabled" in message
        or "cloudinary upload is disabled" in message
    )


_VENUE_VIDEO_EXTS: frozenset = frozenset({
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
    ".flv", ".wmv", ".3gp", ".ogv", ".ts", ".mts", ".mpg", ".mpeg",
})
_VENUE_IMAGE_EXTS: frozenset = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".tiff", ".tif", ".heic", ".heif", ".avif",
})

def _venue_resource_type(filename: str) -> str:
    """Return the correct Cloudinary resource_type for a venue file."""
    ext = os.path.splitext((filename or "").lower())[1]
    if ext in _VENUE_VIDEO_EXTS:
        return "video"
    if ext in _VENUE_IMAGE_EXTS:
        return "image"
    return "auto"


async def _upload_venue_file(upload_file: Optional[UploadFile], folder: str) -> Optional[str]:
    """
    Upload a venue photo or video to Cloudinary.

    Fixes vs. original
    ──────────────────
    • resource_type is now derived from the filename extension so videos are
      stored as ``resource_type="video"`` and images as ``"image"``.  The
      original always used ``"auto"``, which caused Cloudinary to sometimes
      misclassify raw video bytes.
    • Empty uploads are rejected early with a clear HTTP 400.
    • Error messages include the original exception text for debuggability.
    """
    if not upload_file or not upload_file.filename:
        return None
    if not callable(upload_to_cloudinary):
        raise HTTPException(
            status_code=503,
            detail="Venue media storage is not initialised.",
        )
    try:
        data = await upload_file.read()
        if not data:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file '{upload_file.filename}' is empty.",
            )
        rtype  = _venue_resource_type(upload_file.filename)
        result = await upload_to_cloudinary(
            data,
            filename=upload_file.filename,
            folder=folder,
            resource_type=rtype,
        )
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("secure_url") or result.get("url")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "[venue] Media upload failed for %r: %s",
            upload_file.filename,
            exc,
            exc_info=True,
        )
        if _cloudinary_upload_is_disabled(exc):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Venue media uploads are currently disabled for the configured "
                    "Cloudinary account. Enable Cloudinary uploads and verify the "
                    "deployment configuration before registering a venue."
                ),
            )
        raise HTTPException(
            status_code=502,
            detail=f"Venue media upload failed: {exc}",
        )
    raise HTTPException(
        status_code=502,
        detail="Venue media upload returned no URL.",
    )


def _venue_query_id(venue_id: str) -> Dict[str, Any]:
    conditions: List[Dict[str, Any]] = [{"venue_id": venue_id}, {"id": venue_id}]
    try:
        conditions.insert(0, {"_id": ObjectId(venue_id)})
    except Exception:
        pass
    return {"$or": conditions}


def _serialize_venue(document: Dict[str, Any]) -> Dict[str, Any]:
    out = MongoSerializer.serialize_document(document)
    out.setdefault("id", out.get("venue_id") or out.get("_id"))
    out.setdefault("name", out.get("venue_name", ""))
    out.setdefault("address", out.get("full_address", ""))
    return out


@router.post("/api/dco/register-venue")
async def register_dco_venue(
    request: Request,
    venue_name: str = Form(...),
    venue_type: str = Form(...),
    # Frontend sends 'country' (display name e.g. "Nigeria").
    # 'country_code' is accepted for backward-compat but is never required —
    # the DCO dashboard venue tab never submits it.
    country: Optional[str] = Form(None),
    country_code: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    lga: Optional[str] = Form(None),
    full_address: str = Form(...),
    capacity: Optional[str] = Form(None),
    surface_type: Optional[str] = Form(None),
    contact_phone: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    registered_by_dco_id: Optional[str] = Form(None),
    registered_by_dco_name: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
):
    """
    Persist a venue submitted by the DCO dashboard Venue Registration tab.

    FormData fields sent by the frontend:
        venue_name, venue_type, country, state, lga, full_address,
        capacity, surface_type, contact_phone, notes,
        registered_by_dco_id, registered_by_dco_name,
        video (required), photo (optional — omit if not captured).

    GPS coordinates are intentionally NOT submitted by the frontend
    (display-only liveness check).  country_code is optional and stored
    as-is; the primary country identifier is the full country name.
    """
    actor = await _require_dco_user(request)
    actor_id, actor_name = _dco_identity(actor)

    if not _form_str(venue_name) or not _form_str(venue_type):
        raise HTTPException(status_code=422, detail="Venue name and venue type are required.")
    if not _form_str(country):
        raise HTTPException(status_code=422, detail="Country is required.")
    if not _form_str(full_address):
        raise HTTPException(status_code=422, detail="Full address is required.")
    if not video:
        raise HTTPException(status_code=422, detail="Venue video is required.")

    photo_url = await _upload_venue_file(photo, "enejistats/venues/photos")
    video_url = await _upload_venue_file(video, "enejistats/venues/videos")
    now = MongoSerializer.now_utc()
    venue_id = f"VEN-{secrets.token_hex(8).upper()}"

    # Resolve country_code: use the submitted value when present, leave blank otherwise.
    # The full country name is always the primary country field in this workflow.
    _resolved_country      = _form_str(country)
    _resolved_country_code = _form_str(country_code).upper() if country_code else ""

    document = {
        "venue_id":               venue_id,
        "venue_name":             _form_str(venue_name),
        "venue_type":             _form_str(venue_type),
        "country":                _resolved_country,
        "country_code":           _resolved_country_code,
        "state":                  _form_str(state),
        "region":                 _form_str(state),   # alias for legacy queries
        "lga":                    _form_str(lga),
        "full_address":           _form_str(full_address),
        "capacity":               _form_str(capacity),
        "surface_type":           _form_str(surface_type),
        "contact_phone":          _form_str(contact_phone),
        "notes":                  _form_str(notes),
        "photo_url":              photo_url,
        "video_url":              video_url,
        "registered_by_dco_id":   actor_id,
        "registered_by_dco_name": actor_name,
        "created_at":             now,
        "updated_at":             now,
    }
    await venues_collection.insert_one(document)
    return JSONResponse({
        "success": True,
        "venue":   _serialize_venue(document),
        "message": "Venue registered successfully.",
    }, status_code=201)


@router.get("/api/dco/venues")
async def list_dco_venues(request: Request, count_only: bool = False):
    """Return the authenticated DCO's venues, or their count."""
    actor = await _require_dco_user(request)
    actor_id, _ = _dco_identity(actor)
    query = {"registered_by_dco_id": actor_id}
    if count_only:
        return JSONResponse({"total": await venues_collection.count_documents(query)})
    documents = await venues_collection.find(query).sort("created_at", -1).to_list(length=500)
    return JSONResponse({"venues": [_serialize_venue(doc) for doc in documents]})


@router.patch("/api/dco/venues/{venue_id}")
async def update_dco_venue(request: Request, venue_id: str):
    """Update a venue owned by the authenticated DCO after GPS re-capture."""
    actor = await _require_dco_user(request)
    actor_id, actor_name = _dco_identity(actor)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")
    if not isinstance(payload, dict) or not payload.get("gps"):
        raise HTTPException(status_code=422, detail="GPS re-capture is required to update a venue.")

    allowed = {
        "venue_name", "venue_type", "country_code", "country", "state", "lga",
        "full_address", "capacity", "surface_type", "contact_phone", "notes",
    }
    changes = {key: payload[key] for key in allowed if key in payload}
    if "state" in changes:
        changes["region"] = changes["state"]
    changes["updated_at"] = MongoSerializer.now_utc()
    changes["updated_by_dco_id"] = actor_id
    changes["updated_by_dco_name"] = actor_name

    query = {
        "$and": [
            _venue_query_id(venue_id),
            {"registered_by_dco_id": actor_id},
        ]
    }
    result = await venues_collection.update_one(query, {"$set": changes})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Venue not found.")
    document = await venues_collection.find_one(query)
    return JSONResponse({
        "success": True,
        "venue": _serialize_venue(document),
        "message": "Venue updated successfully.",
    })

@router.get(
    "/api/public/venues",
    tags=["Public"],
    summary="List all registered venues",
)
async def get_public_venues(
    count_only: bool = Query(False, description="Return only the total count."),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    country: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    lga: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    venue_type: Optional[str] = Query(None),
    competition_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> JSONResponse:
    """
    Public endpoint for retrieving registered venues.

    Supports:
    - Pagination
    - Count-only mode
    - Search by venue name
    - Country filtering
    - State filtering
    - LGA filtering
    - City/district filtering
    - Venue type filtering
    - Competition level filtering
    """

    query = {}

    if country:
        # The registration UI normally submits an ISO code (for example,
        # "NG"), while venue documents may store the display name
        # ("Nigeria") and older documents may have a blank country_code.
        # Resolve the code through location_module so both representations
        # match without requiring a data migration.
        country_value = country.strip()
        country_code = country_value.upper()
        country_name = get_country_name(country_code)
        if country_name:
            query["$or"] = [
                {"country": country_name},
                {"country_code": country_code},
            ]
        else:
            query["country"] = country_value

    if state:
        query["state"] = state.strip()

    if lga:
        query["lga"] = lga.strip()

    if city:
        query["city"] = city.strip()

    if venue_type:
        query["venue_type"] = venue_type.strip()

    if competition_level:
        query["competition_levels"] = competition_level.strip()

    if search:
        query["venue_name"] = {
            "$regex": search.strip(),
            "$options": "i",
        }

    if count_only:
        total = await venues_collection.count_documents(query)
        return JSONResponse(
            status_code=200,
            content={
                "total": total,
                "count": total,
            },
        )

    skip = (page - 1) * limit

    cursor = (
        venues_collection
        .find(query)
        .sort("venue_name", 1)
        .skip(skip)
        .limit(limit)
    )

    docs = await cursor.to_list(length=limit)

    total = await venues_collection.count_documents(query)

    return JSONResponse(
        status_code=200,
        content={
            "page": page,
            "limit": limit,
            "total": total,
            "count": len(docs),
            "venues": MongoSerializer.serialize_documents(docs),
        },
    )

# ============================================================
# VERIFY REGISTRATION OTP
# ============================================================

@router.post("/api/auth/verify-registration-otp")
async def verify_registration_otp(payload: RegistrationOtpRequest):
    """
    Verify the 6-digit OTP sent after registration.
    Marks the user's email as verified on success.
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_registration_otp] ENTRY | user_id=%r | role=%r | otp_len=%d",
        payload.user_id, payload.role, len(payload.otp or ""),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    user_id = (payload.user_id or "").strip()
    role    = (payload.role    or "").strip().lower()
    otp     = (payload.otp     or "").strip()

    if not user_id or not role or not otp:
        raise HTTPException(status_code=400, detail="user_id, role, and otp are required.")

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_registration_otp] DB QUERY registration_otps | user_id=%r | role=%r",
        user_id, role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    otp_doc = await registration_otps_col.find_one({"user_id": user_id, "role": role})

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_registration_otp] OTP DOC | found=%r | already_verified=%r",
        otp_doc is not None,
        otp_doc.get("verified") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(status_code=404, detail="OTP record not found. Please register again.")

    if otp_doc.get("verified"):
        raise HTTPException(status_code=409, detail="Email already verified.")

    # Rate-limit: max 10 attempts
    attempts = otp_doc.get("attempts", 0)
    if attempts >= 10:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please register again.",
        )

    # Expiry check
    expires_at = otp_doc.get("expires_at")
    if expires_at and MongoSerializer.now_utc() > _ensure_aware(expires_at):
        raise HTTPException(
            status_code=410,
            detail="OTP has expired. Use the resend option to get a new code.",
        )

    # OTP match
    if otp_doc.get("otp") != otp:
        await registration_otps_col.update_one(
            {"_id": otp_doc["_id"]},
            {"$inc": {"attempts": 1}},
        )
        raise HTTPException(status_code=400, detail="Invalid code. Please try again.")

    # ── Mark OTP as verified ─────────────────────────────────
    await registration_otps_col.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"verified": True, "verified_at": MongoSerializer.now_utc()}},
    )

    # ── Mark email_verified on the user document ─────────────
    col = _role_collection(role)
    id_field = _role_id_field(role)
    if col is not None:
        await col.update_one(
            {id_field: user_id},
            {"$set": {"email_verified": True, "is_verified": True, "updated_at": MongoSerializer.now_utc()}},
        )
    if users_collection is not None:
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"email_verified": True, "updated_at": MongoSerializer.now_utc()}},
        )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_registration_otp] SUCCESS | user_id=%r | role=%r | email_verified=True",
        user_id, role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return JSONResponse({
        "success": True,
        "message": "Email verified successfully. You can now sign in.",
        "user_id": user_id,
        "role":    role,
    })


# ============================================================
# RESEND REGISTRATION OTP
# ============================================================

@router.post("/api/auth/resend-registration-otp")
async def resend_registration_otp(payload: ResendRegistrationOtpRequest):
    """
    Resend the 6-digit registration OTP.
    The user must have a pending (unverified) OTP record.
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[resend_registration_otp] ENTRY | user_id=%r | role=%r",
        payload.user_id, payload.role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    user_id = (payload.user_id or "").strip()
    role    = (payload.role    or "").strip().lower()

    if not user_id or not role:
        raise HTTPException(status_code=400, detail="user_id and role are required.")

    # ── Look up the OTP record to get email / display name ───
    otp_doc = await registration_otps_col.find_one({"user_id": user_id, "role": role})

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[resend_registration_otp] OTP DOC | found=%r | already_verified=%r",
        otp_doc is not None,
        otp_doc.get("verified") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(
            status_code=404,
            detail="No pending registration found. Please start registration again.",
        )
    if otp_doc.get("verified"):
        raise HTTPException(status_code=409, detail="Email already verified.")

    email = normalize_email(otp_doc.get("email", ""))
    if not email:
        # Fall back: look up email from the user collection
        col      = _role_collection(role)
        id_field = _role_id_field(role)
        if col is not None:
            user_doc = await col.find_one({id_field: user_id})
            email = normalize_email((user_doc or {}).get("email", ""))

    if not email:
        raise HTTPException(status_code=500, detail="Could not resolve email for resend.")

    # ── Get display name from user collection ─────────────────
    display_name = email
    col      = _role_collection(role)
    id_field = _role_id_field(role)
    if col is not None:
        user_doc = await col.find_one({id_field: user_id})
        if user_doc:
            display_name = (
                user_doc.get("full_name")
                or user_doc.get("first_name")
                or user_doc.get("club_name")
                or email
            )

    # ── Issue fresh OTP ───────────────────────────────────────
    await _issue_registration_otp(
        user_id=user_id,
        role=role,
        email=email,
        display_name=display_name,
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[resend_registration_otp] OTP RESENT | user_id=%r | email=%r",
        user_id, email,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return JSONResponse({"success": True, "message": "New verification code sent to your email."})


# ============================================================
# AUTH — SESSION RESTORE
# ============================================================

@router.get("/api/auth/me")
async def auth_me(request: Request):
    """Restore the session through main.py's canonical current-user resolver."""
    _assert_deps_ready()
    bearer = ""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        candidate = auth_header[7:].strip()
        if candidate and _decode_auth_token(candidate):
            bearer = candidate

    effective_request = request
    if bearer:
        scope = dict(request.scope)
        headers = [
            (key, value) for key, value in scope.get("headers", [])
            if key.lower() not in {b"authorization", b"cookie"}
        ]
        headers.append((b"authorization", f"Bearer {bearer}".encode("latin-1")))
        scope["headers"] = headers
        effective_request = Request(scope)

    try:
        user = await get_current_user(effective_request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[auth_me] canonical current-user resolution failed: %s", exc)
        raise HTTPException(status_code=401, detail="Not authenticated") from exc

    role = _canonical_role(user.get("role") or user.get("user_type"))
    id_field = _role_id_field(role)
    canonical_id = user.get(id_field) or user.get("user_id") or user.get("unique_id")
    if not canonical_id:
        raise HTTPException(status_code=401, detail="Authenticated identity is incomplete")

    out = dict(user)
    for field in ("password", "password_hash", "hashed_password", "hashed_pw"):
        out.pop(field, None)
    out["role"] = role
    out["user_type"] = role
    out["user_id"] = str(canonical_id)
    out["unique_id"] = str(user.get("unique_id") or canonical_id)
    out["name"] = (
        user.get("name") or user.get("full_name")
        or " ".join(filter(None, [user.get("first_name", ""), user.get("last_name", "")])).strip()
        or user.get("club_name") or user.get("email", "")
    )
    out["avatar"] = user.get("avatar") or user.get("photo") or user.get("profile_picture") or user.get("profile_image") or ""

    if role == "player" and player_tokens_collection is not None:
        token_doc = await player_tokens_collection.find_one({"player_id": str(canonical_id)})
        out["token_balance"] = token_doc.get("balance", 0) if token_doc else 0

    json_response = JSONResponse(MongoSerializer.serialize_document(out))
    if bearer and bearer != request.cookies.get("auth_token"):
        json_response.set_cookie(
            key="auth_token", value=bearer, httponly=True, secure=True,
            samesite="none", max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600, path="/",
        )
    return json_response


# ============================================================
# AUTH — LOGIN
# ============================================================

@router.post("/api/auth/login")
async def unified_login(payload: LoginRequest, response: Response):
    """
    Unified email + password login for all roles.
    Tries each collection in priority order and issues an auth_token cookie.
    """
    _assert_deps_ready()
    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[unified_login] ENTRY | email=%r | password_provided=%r",
        normalize_email(payload.email),
        bool(payload.password),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email = normalize_email(payload.email)
    # Keep the unified login contract identical to the dedicated CO/CC
    # login routes.  Those routes trim the value received from the browser;
    # doing it here prevents an accidental input-space from producing a
    # misleading "invalid password" response.
    password = (payload.password or "").strip()
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = None
    user_role = None
    for role_name in CANONICAL_ROLES or ():
        col = _role_collection(role_name)
        if col is None:
            continue
        doc = await col.find_one({"email": email})
        if doc:
            user = doc
            user_role = _canonical_role(doc.get("role") or role_name)
            break

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[unified_login] DB RESULT | user_found=%r | role=%r",
        user is not None, user_role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Passwords created by older admin tooling have existed under a few
    # equivalent field names.  Prefer the canonical field, but accept the
    # legacy names so CO and CC accounts use exactly the same authentication
    # path as every other dashboard.  Never compare plaintext values here.
    password_hash = next(
        (
            user.get(field)
            for field in ("password_hash", "password", "hashed_password", "hashed_pw")
            if isinstance(user.get(field), str) and user.get(field).strip()
        ),
        "",
    )
    pwd_ok = bool(password_hash) and verify_password(
        password, password_hash.strip()
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[unified_login] PASSWORD CHECK | verified=%r | has_hashed_pw=%r",
        pwd_ok, bool(user.get("password")),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not pwd_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Roles that require admin approval before login
    APPROVAL_REQUIRED = {"club", "dco", "supervisor"}
    if user_role in APPROVAL_REQUIRED:
        approval = user.get("approval_status", "approved")
        if approval == "pending":
            raise HTTPException(
                status_code=403,
                detail=(
                    "Your account is pending admin review. "
                    "You will be notified by email once approved."
                ),
            )
        if approval == "rejected":
            raise HTTPException(
                status_code=403,
                detail="Your account application was not approved. Contact enejistats@gmail.com.",
            )

    # If user registered but hasn't verified their email yet, re-send a verification OTP
    if not user.get("is_verified", True) and not user.get("email_verified", True):
        otp = f"{random.randint(100000, 999999)}"
        now_otp = MongoSerializer.now_utc()
        if verification_codes_collection is not None:
            await verification_codes_collection.insert_one({
                "user_id":    email,
                "email":      email,
                "role":       "login_verify",
                "otp":        otp,
                "used":       False,
                "sent_at":    now_otp,
                "expires_at": now_otp + timedelta(minutes=15),
            })
        display_name = (
            user.get("name") or user.get("full_name")
            or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            or email
        )
        plain_txt, html_body = _build_otp_email(display_name, otp)
        try:
            await send_email(
                to_email=email,
                subject="EnejiStats — Verify Your Email to Log In",
                body=plain_txt,
                html_body=html_body,
            )
        except Exception as _e:
            logger.warning("[unified_login] OTP email send failed: %s", _e)

        raise HTTPException(
            status_code=403,
            detail={
                "code":    "EMAIL_NOT_VERIFIED",
                "message": "Your email is not verified. A verification code has been sent.",
                "email":   email,
                "role":    user_role,
            },
        )

    # Build sub_role (dco/supervisor are top-level roles but keep sub_role for legacy)
    sub_role = ""
    if user_role in ("dco", "supervisor"):
        sub_role = user_role

    redirect_url = _role_redirect(user_role)
    token = build_user_access_token(user)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[unified_login] JWT CREATED | sub=%r | role=%r | sub_role=%r",
        str(user["_id"]), user_role, sub_role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    out = MongoSerializer.serialize_document(user)
    for _secret_field in ("password", "password_hash", "hashed_password", "hashed_pw"):
        out.pop(_secret_field, None)

    _login_display_name = (
        user.get("name") or user.get("full_name")
        or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        or email
    )
    _login_user_id = (
        user.get(_role_id_field(user_role))
        or user.get("user_id")
        or user.get("unique_id")
        or str(user.get("_id", ""))
    )
    _login_avatar  = (
        user.get("avatar") or user.get("profile_picture")
        or user.get("profile_image") or ""
    )

    json_response = JSONResponse({
        "success":      True,
        "message":      "Login successful",
        "access_token": token,
        "role":         user_role,
        "sub_role":     sub_role,
        "email":        email,
        "redirect":     redirect_url,
        "user_id":      _login_user_id,
        "name":         _login_display_name,
        "avatar":       _login_avatar,
        "user":         out,
    })
    json_response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    logger.info("[unified_login] SUCCESS | email=%r | role=%r", email, user_role)
    return json_response

# ============================================================
# AUTH — VERIFY LOGIN 2FA OTP
# ============================================================

@router.post("/api/auth/verify-login-otp")
async def verify_login_otp(payload: LoginOtpVerifyRequest):
    """
    Verify the 6-digit 2FA OTP issued at login.

    On success:
      • Marks the OTP as used (single-use enforcement).
      • Looks up the user, builds a JWT, sets the auth_token cookie,
        and returns the same envelope as /api/auth/login.

    Error codes returned:
      400 — missing fields or invalid OTP
      404 — no pending 2FA session for this email
      410 — OTP has expired
      429 — too many incorrect attempts
    """
    _assert_deps_ready()

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_login_otp] ENTRY | email=%r | otp_len=%d",
        normalize_email(payload.email), len(payload.otp or ""),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email = normalize_email(payload.email)
    otp   = (payload.otp   or "").strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="email and otp are required.")

    # ── Fetch the pending 2FA OTP record ─────────────────────
    otp_doc = await password_reset_otps_col.find_one(
        {"email": email, "purpose": "login_2fa"}
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_login_otp] OTP DOC | found=%r | used=%r",
        otp_doc is not None,
        otp_doc.get("used") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(
            status_code=404,
            detail="No pending 2FA session found. Please log in again.",
        )

    if otp_doc.get("used"):
        raise HTTPException(
            status_code=400,
            detail="This code has already been used. Please log in again.",
        )

    if otp_doc.get("attempts", 0) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please log in again.",
        )

    expires_at = otp_doc.get("expires_at")
    if expires_at and MongoSerializer.now_utc() > _ensure_aware(expires_at):
        raise HTTPException(
            status_code=410,
            detail="Verification code has expired. Please log in again.",
        )

    # ── OTP match ─────────────────────────────────────────────
    if otp_doc.get("otp") != otp:
        await password_reset_otps_col.update_one(
            {"_id": otp_doc["_id"]},
            {"$inc": {"attempts": 1}},
        )
        remaining = max(10 - otp_doc.get("attempts", 0) - 1, 0)

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[verify_login_otp] MISMATCH | remaining_attempts=%d", remaining,
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        raise HTTPException(
            status_code=400,
            detail=f"Invalid code. {remaining} attempt(s) remaining.",
        )

    # ── Mark OTP as used (single-use) ─────────────────────────
    await password_reset_otps_col.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"used": True, "used_at": MongoSerializer.now_utc()}},
    )

    # ── Look up the user to build a full JWT ──────────────────
    user_doc = await _find_existing_user_by_email(email)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_login_otp] USER LOOKUP | found=%r | role=%r",
        user_doc is not None,
        user_doc.get("role") if user_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not user_doc:
        raise HTTPException(status_code=404, detail="User account not found.")

    user_role = _canonical_role(user_doc.get("role", ""))
    sub_role  = ""
    if user_role in ("dco", "supervisor"):
        sub_role = user_role

    id_field = _role_id_field(user_role)
    business_user_id = (
        user_doc.get(id_field)
        or user_doc.get("user_id")
        or user_doc.get("unique_id")
        or str(user_doc.get("_id", ""))
    )
    token = build_user_access_token(user_doc)
    redirect_url = _role_redirect(user_role)


    out = MongoSerializer.serialize_document(user_doc)
    for _secret_field in ("password", "password_hash", "hashed_password", "hashed_pw"):
        out.pop(_secret_field, None)

    display_name = (
        user_doc.get("name") or user_doc.get("full_name")
        or f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip()
        or email
    )
    avatar = (
        user_doc.get("avatar") or user_doc.get("profile_picture")
        or user_doc.get("profile_image") or ""
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_login_otp] SUCCESS | email=%r | role=%r | sub_role=%r",
        email, user_role, sub_role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    logger.info("[verify_login_otp] 2FA verified and JWT issued | email=%r | role=%r", email, user_role)

    json_response = JSONResponse({
        "success":      True,
        "message":      "Login verified successfully",
        "access_token": token,
        "role":         user_role,
        "sub_role":     sub_role,
        "email":        email,
        "redirect":     redirect_url,
        "user_id":      business_user_id,
        "name":         display_name,
        "avatar":       avatar,
        "user":         out,
    })
    json_response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    return json_response
  
# ============================================================
# AUTH — LOGOUT
# ============================================================

_AUTH_COOKIE_NAMES: List[str] = [
    "auth_token",
    "access_token",
    "refresh_token",
    "remember_me",
    "session",
    "token",
    "enejistats_token",
    "enejistats_session",
]


def _clear_auth_cookies(response: Response) -> Response:
    """Apply the platform-wide authentication cookie cleanup to a response."""
    for cookie_name in _AUTH_COOKIE_NAMES:
        response.delete_cookie(key=cookie_name, path="/")
    return response


@router.post("/api/auth/logout")
async def auth_logout(request: Request):
    """
    Centralised logout endpoint — shared by every dashboard role.

    Actions:
      1. Clears every authentication/session cookie the platform may have set.
      2. Returns Cache-Control: no-store so the browser does not cache this response.
      3. Returns 200 JSON regardless of auth state — double-clicks are always safe.
    """
    _assert_deps_ready()
    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[auth_logout] ENTRY | incoming_cookies=%r",
        list(request.cookies.keys()),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    response = JSONResponse(
        {"success": True, "message": "Logged out successfully"},
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma":        "no-cache",
            "Expires":       "0",
        },
    )

    _clear_auth_cookies(response)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[auth_logout] COMPLETE | cookies_cleared=%r",
        _AUTH_COOKIE_NAMES,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return response


@router.get("/logout")
async def legacy_logout(request: Request):
    """
    Compatibility endpoint for older deployed pages that navigate to /logout.

    The dashboard uses POST /api/auth/logout. This GET route prevents stale
    clients or cached links from receiving a 404 while reusing the exact same
    cookie cleanup and sending the user to the login page.
    """
    _assert_deps_ready()
    response = RedirectResponse(
        url="/login",
        status_code=303,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma":        "no-cache",
            "Expires":       "0",
        },
    )
    _clear_auth_cookies(response)
    return response

# ============================================================
# FORGOT PASSWORD — step 1: send reset OTP
# ============================================================

@router.post("/api/auth/forgot-password")
async def forgot_password(request: Request, payload: ForgotPasswordRequest):
    """
    Send a 6-digit password reset code to the given email.

    Always returns 200 with a neutral message — regardless of whether
    the email exists — to avoid email-enumeration attacks.
    """
    if password_reset_otps_col is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # ── IP rate limit ─────────────────────────────────────────
    _check_pw_reset_rate(_get_client_ip(request))
    _record_pw_reset(_get_client_ip(request))

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[forgot_password] ENTRY | email=%r",
        normalize_email(payload.email),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    # ── Find user (neutral branch: no 404 disclosure) ─────────
    user_doc = await _find_existing_user_by_email(email)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[forgot_password] USER LOOKUP | found=%r | role=%r",
        user_doc is not None,
        user_doc.get("role") if user_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if user_doc:
        display_name = (
            user_doc.get("full_name")
            or user_doc.get("club_name")
            or " ".join(filter(None, [
                user_doc.get("first_name", ""),
                user_doc.get("last_name", ""),
            ])).strip()
            or email
        )
        try:
            await _issue_password_reset_otp(email=email, display_name=display_name)
        except Exception as exc:
            logger.error("[forgot_password] OTP issue failed for %r: %s", email, exc)

    # Always return neutral 200 — never reveal whether account exists
    return JSONResponse({
        "success": True,
        "message": "If an account with that email exists, a reset code has been sent.",
    })


# ============================================================
# FORGOT PASSWORD — step 2: verify reset OTP
# ============================================================

@router.post("/api/auth/verify-reset-code")
async def verify_reset_code(payload: VerifyResetCodeRequest):
    if password_reset_otps_col is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
    """
    Verify the password-reset OTP.

    On success, marks the OTP as consumed (but not deleted) and
    returns a short-lived reset_token the client may use in the
    /reset-password endpoint.  Also retains (email + otp) for the
    legacy /reset-password-otp flow.
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_reset_code] ENTRY | email=%r | otp_len=%d",
        normalize_email(payload.email), len(payload.otp or ""),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email = normalize_email(payload.email)
    otp   = (payload.otp   or "").strip()

    if not email or not otp:
        raise HTTPException(status_code=400, detail="email and otp are required.")

    otp_doc = await password_reset_otps_col.find_one({"email": email})

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_reset_code] OTP DOC | found=%r | used=%r",
        otp_doc is not None,
        otp_doc.get("used") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired code. Please request a new reset code.",
        )

    if otp_doc.get("used"):
        raise HTTPException(
            status_code=400,
            detail="This code has already been used. Please request a new one.",
        )

    # Rate limit
    if otp_doc.get("attempts", 0) >= 10:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Please request a new code.",
        )

    # Expiry
    expires_at = otp_doc.get("expires_at")
    if expires_at and MongoSerializer.now_utc() > _ensure_aware(expires_at):
        raise HTTPException(
            status_code=410,
            detail="Code has expired. Please request a new reset code.",
        )

    # OTP match
    if otp_doc.get("otp") != otp:
        await password_reset_otps_col.update_one(
            {"_id": otp_doc["_id"]},
            {"$inc": {"attempts": 1}},
        )
        raise HTTPException(status_code=400, detail="Invalid code. Please try again.")

    # ── Generate reset_token ──────────────────────────────────
    reset_token = secrets.token_urlsafe(32)
    reset_token_expiry = MongoSerializer.now_utc() + timedelta(minutes=15)

    await password_reset_otps_col.update_one(
        {"_id": otp_doc["_id"]},
        {
            "$set": {
                "verified":           True,
                "reset_token":        reset_token,
                "reset_token_expiry": reset_token_expiry,
            }
        },
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[verify_reset_code] SUCCESS | email=%r | reset_token_issued=True",
        email,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return JSONResponse({
        "success":     True,
        "reset_token": reset_token,
        "message":     "Code verified. You may now reset your password.",
    })


# ============================================================
# FORGOT PASSWORD — step 3 (current flow): reset with email+otp+password
# ============================================================

@router.post("/api/auth/reset-password-otp")
async def reset_password_otp(payload: ResetPasswordOtpRequest):
    if password_reset_otps_col is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
    """
    Reset password using the original email + OTP combination.

    This is the current flow used by forgot-password.html when
    /verify-reset-code returns a 404 (older backend) or when the client
    chooses not to use the token-based flow.
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_otp] ENTRY | email=%r | otp_len=%d | new_password_provided=%r",
        normalize_email(payload.email), len(payload.otp or ""),
        bool(payload.new_password),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email        = normalize_email(payload.email)
    otp          = (payload.otp          or "").strip()
    new_password = (payload.new_password or "").strip()

    if not email or not otp or not new_password:
        raise HTTPException(status_code=400, detail="email, otp, and new_password are required.")

    _validate_new_password(new_password, email)

    otp_doc = await password_reset_otps_col.find_one({"email": email})

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_otp] OTP DOC | found=%r | used=%r",
        otp_doc is not None,
        otp_doc.get("used") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code. Please request a new one.",
        )

    if otp_doc.get("used"):
        raise HTTPException(status_code=400, detail="Reset code already used.")

    if otp_doc.get("attempts", 0) >= 10:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    expires_at = otp_doc.get("expires_at")
    if expires_at and MongoSerializer.now_utc() > _ensure_aware(expires_at):
        raise HTTPException(status_code=410, detail="Code has expired. Request a new one.")

    if otp_doc.get("otp") != otp:
        await password_reset_otps_col.update_one(
            {"_id": otp_doc["_id"]}, {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid code.")

    # ── Find and update the user document ────────────────────
    user_doc = await _find_existing_user_by_email(email)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_otp] USER LOOKUP | found=%r | role=%r",
        user_doc is not None, user_doc.get("role") if user_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not user_doc:
        raise HTTPException(status_code=404, detail="Account not found.")

    role = _canonical_role(user_doc.get("role"))
    col  = _role_collection(role)
    if col is None:
        raise HTTPException(status_code=500, detail="Internal error: collection not configured.")

    hashed_pw = hash_password(new_password)
    await col.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"password_hash": hashed_pw, "updated_at": MongoSerializer.now_utc()}, "$unset": {"password": ""}},
    )

    # Mark OTP as used
    await password_reset_otps_col.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"used": True, "used_at": MongoSerializer.now_utc()}},
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_otp] PASSWORD UPDATED | email=%r | role=%r",
        email, role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return JSONResponse({"success": True, "message": "Password reset successfully. You can now sign in."})


# ============================================================
# FORGOT PASSWORD — step 3 (token flow): reset with reset_token+password
# ============================================================

@router.post("/api/auth/reset-password")
async def reset_password_token(payload: ResetPasswordTokenRequest):
    if password_reset_otps_col is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")
    """
    Reset password using the reset_token issued by /verify-reset-code.
    Future-compatible endpoint (token-based flow).
    """

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_token] ENTRY | reset_token_provided=%r | new_password_provided=%r",
        bool(payload.reset_token), bool(payload.new_password),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    reset_token  = (payload.reset_token  or "").strip()
    new_password = (payload.new_password or "").strip()

    if not reset_token or not new_password:
        raise HTTPException(status_code=400, detail="reset_token and new_password are required.")

    # Extract email for complexity check (look up OTP doc first)
    _pre_doc = await password_reset_otps_col.find_one({"reset_token": reset_token})
    _email_for_check = (_pre_doc or {}).get("email", "")
    _validate_new_password(new_password, _email_for_check)

    otp_doc = _pre_doc  # reuse — already fetched

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_token] OTP DOC | found=%r | used=%r",
        otp_doc is not None,
        otp_doc.get("used") if otp_doc else None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if not otp_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token. Please start again.")

    if otp_doc.get("used"):
        raise HTTPException(status_code=400, detail="Reset token already used.")

    expiry = otp_doc.get("reset_token_expiry")
    if expiry and MongoSerializer.now_utc() > _ensure_aware(expiry):
        raise HTTPException(status_code=410, detail="Reset token has expired. Please start again.")

    email    = otp_doc.get("email", "")
    user_doc = await _find_existing_user_by_email(email)

    if not user_doc:
        raise HTTPException(status_code=404, detail="Account not found.")

    role = _canonical_role(user_doc.get("role"))
    col  = _role_collection(role)
    if col is None:
        raise HTTPException(status_code=500, detail="Internal error: collection not configured.")

    hashed_pw = hash_password(new_password)
    await col.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"password_hash": hashed_pw, "updated_at": MongoSerializer.now_utc()}, "$unset": {"password": ""}},
    )

    await password_reset_otps_col.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"used": True, "used_at": MongoSerializer.now_utc()}},
    )

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[reset_password_token] PASSWORD UPDATED | email=%r | role=%r",
        email, role,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    return JSONResponse({"success": True, "message": "Password reset successfully. You can now sign in."})


# ============================================================
# RESEND PASSWORD RESET CODE
# ============================================================

@router.post("/api/auth/resend-reset-code")
async def resend_reset_code(request: Request, payload: ResendResetCodeRequest):
    """
    Resend the password-reset OTP.

    Always returns 200 with a neutral message — never discloses
    whether the email exists.
    """
    if password_reset_otps_col is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    # ── IP rate limit ─────────────────────────────────────────
    _check_pw_reset_rate(_get_client_ip(request))
    _record_pw_reset(_get_client_ip(request))

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[resend_reset_code] ENTRY | email=%r",
        normalize_email(payload.email),
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")

    user_doc = await _find_existing_user_by_email(email)

    # ── DEBUG BLOCK START ────────────────────────────────────────────────────
    logger.debug(
        "[resend_reset_code] USER LOOKUP | found=%r",
        user_doc is not None,
    )
    # ── DEBUG BLOCK END ──────────────────────────────────────────────────────

    if user_doc:
        display_name = (
            user_doc.get("full_name")
            or user_doc.get("club_name")
            or " ".join(filter(None, [
                user_doc.get("first_name", ""),
                user_doc.get("last_name", ""),
            ])).strip()
            or email
        )
        try:
            await _issue_password_reset_otp(email=email, display_name=display_name)
        except Exception as exc:
            logger.error("[resend_reset_code] Failed to resend OTP for %r: %s", email, exc)

    return JSONResponse({
        "success": True,
        "message": "A new code has been sent if the account exists.",
    })
