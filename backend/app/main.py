# ============================================================
# ENEJISTATS — FASTAPI APPLICATION
# African Football Statistics Platform
# Clean production build — all routes, models, auth, middleware,
# WebSocket, upload, admin, dashboard, startup/shutdown
# + Unified /api/auth/register, /api/liveness, config & public endpoints
# + Integrated app.core.pricing (single-file, no external module needed)
# ============================================================

# ============================================================
# START: IMPORTS
# ============================================================

import os
import re
import uuid
import json
import math
import copy
import asyncio
import logging
import random
import secrets
import traceback
from calendar import monthrange
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone, date, time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import bcrypt
import httpx
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import (
    BackgroundTasks, Depends, FastAPI, File, Form,
    HTTPException, Request, Response, UploadFile,
    WebSocket, WebSocketDisconnect,
)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo import ReturnDocument

# Optional imports — soft-fail if not installed
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    _cloudinary_available = True
except ImportError:
    _cloudinary_available = False

try:
    import openai as _openai_module
    _openai_available = True
except ImportError:
    _openai_available = False

try:
    from email_validator import validate_email, EmailNotValidError
    _email_validator_available = True
except ImportError:
    _email_validator_available = False

# ============================================================
# PRICING MODULE — loaded from pricing_module.py
# All pricing classes, constants, and helpers are defined there.
# ============================================================
import sys as _sys
import pathlib as _pathlib
_APP_DIR = _pathlib.Path(__file__).resolve().parent
if str(_APP_DIR) not in _sys.path:
    _sys.path.insert(0, str(_APP_DIR))

# ============================================================
# PRICING MODULE  (imported from pricing_module.py)
# ============================================================
from email_helper_updated import (
    _email_html, _build_otp_email, _build_trial_email,
    _build_sub_confirm_email, _build_verification_email,
    build_welcome_email, send_email,
    BREVO_API_KEY, FROM_EMAIL, FROM_NAME,
)

from pricing_module import (
    PricingService,
    pricing_service,          # singleton — injected into route modules via _setup_dependencies(globals())
    get_token_cost,           # used by player_dashboard_routes and other route modules
    register_pricing_routes,  # registers public /api/public/pricing/* endpoints
    # data constants used elsewhere in main.py (add/remove as needed)
    DEFAULT_SUBSCRIPTION_PRICES,
    DEFAULT_SUBSCRIPTION_PLANS,
    DEFAULT_ADMIN_SETTINGS,
    DEFAULT_DCO_RATES,
    DEFAULT_SUPERVISOR_RATES,
    DEFAULT_COUNTRY_MULTIPLIERS,
    REGION_GROUPS,
    TOKEN_PACKAGES,
    PLAYER_STATS_REQUEST_TOKENS,
    CLUB_STATS_REQUEST_TOKENS,
    FLAT_TOKEN_COSTS,
    normalize_level,
    normalize_plan_key,
    PLAYER_LEVELS_CONFIG,
    POSITIONS_CONFIG,
    BANK_TRANSFER_DETAILS,
)
# ============================================================
# END OF PRICING MODULE
# ============================================================

# ============================================================
# LOCATION MODULE IMPORT
# ============================================================
from location_module import register_location_routes

# ============================================================
# LOGGING SETUP
# ============================================================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("enejistats")
logger.setLevel(logging.DEBUG)

leaderboard_logger = logging.getLogger("leaderboard_debug")
leaderboard_logger.setLevel(logging.DEBUG)
_lb_handler = logging.StreamHandler()
_lb_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
_lb_handler.setFormatter(_lb_formatter)
if not leaderboard_logger.handlers:
    leaderboard_logger.addHandler(_lb_handler)

# ============================================================
# START: ENVIRONMENT CONFIGURATION
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/enejistats")
SECRET_KEY = os.getenv("SECRET_KEY", "enejistats-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

cloudinary_url = os.getenv("CLOUDINARY_URL", "")
openai_api_key = os.getenv("OPENAI_API_KEY", "")

FLUTTERWAVE_PUBLIC_KEY = os.getenv("FLUTTERWAVE_PUBLIC_KEY", "")
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY", "")
FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"

# Monitoring: env format "name=url;interval,name2=url2;interval2"
MONITORING_URLS: Dict[str, Any] = {}
_ping_env = os.getenv("PING_PLATFORMS", os.getenv("MONITORING_URLS", ""))
if _ping_env:
    for _entry in _ping_env.split(","):
        try:
            _url_part, _interval = _entry.split(";", 1)
            _interval = int(_interval.strip())
            _name, _url = _url_part.split("=", 1)
            MONITORING_URLS[_name.strip()] = {
                "url": _url.strip(),
                "interval": _interval,
                "last_log": None,
                "last_ping": None,
            }
        except Exception:
            if _entry.strip():
                MONITORING_URLS[_entry.strip()] = {
                    "url": _entry.strip(),
                    "interval": 300,
                    "last_log": None,
                    "last_ping": None,
                }


# Cloudinary init
if cloudinary_url and _cloudinary_available:
    cloudinary.config(secure=True, cloudinary_url=cloudinary_url)
elif not cloudinary_url:
    pass  # warning emitted after logger is set up below

# OpenAI init
openai_client = None
if openai_api_key and _openai_available:
    openai_client = _openai_module.OpenAI(api_key=openai_api_key)

security = HTTPBearer(auto_error=False)
last_ping_time = None


# ============================================================
# PAYMENT REFERENCE HELPERS
# ============================================================

def _make_tx_ref(payment_type: str, role: str) -> str:
    """Generate a unique payment transaction reference.

    Format: ``ES-<TYPE>-<ROLE>-<10-HEX-UPPER>``
    """
    prefix     = "TKN" if payment_type == "TOKEN_PURCHASE" else "SUB"
    role_short = {"player": "PLY", "club": "CLB", "scout": "SCT", "agent": "AGT"}.get(role, "USR")
    return f"ES-{prefix}-{role_short}-{uuid.uuid4().hex[:10].upper()}"


def _make_stats_request_ref() -> str:
    """Return a unique stats-request reference.  Format: ``SR-<8-HEX>``."""
    return f"SR-{uuid.uuid4().hex[:8].upper()}"


def _make_supervisor_payout_ref() -> str:
    """Return a unique supervisor payout reference.  Format: ``SPAY-<8-HEX>``."""
    return f"SPAY-{uuid.uuid4().hex[:8].upper()}"


def _make_club_token_topup_ref() -> str:
    """Return a unique club token top-up reference.  Format: ``CLUB-TKN-<8-HEX>``."""
    return f"CLUB-TKN-{uuid.uuid4().hex[:8].upper()}"


# ============================================================
# START: MONGODB / COLLECTION REGISTRY
# ============================================================

mongo_client = AsyncIOMotorClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
)
database = mongo_client.get_database("enejistats")

# =========================
# User Collections
# =========================
players_collection                   = database["players"]
clubs_collection                     = database["clubs"]
scouts_collection                    = database["scouts"]
agents_collection                    = database["agents"]
dco_collection                       = database["dcos"]
supervisors_collection               = database["supervisors"]
communication_officers_collection    = database["communication_officers"]
customer_care_collection             = database["customer_care"]
admins_collection                    = database["admins"]
content_managers_collection          = database["content_managers"]
sub_admins_collection                = database["sub_admins"]
users_collection                     = database["users"]

# Legacy alias — retained so existing documents are still found.
# dcos_collection: canonical alias used throughout helpers and sub-routers.
dcos_collection                      = dco_collection


# =========================
# Football / Match Collections
# =========================
player_stats_collection              = database["player_stats"]
match_stats_collection               = database["match_stats"]
stats_requests_collection            = database["stats_requests"]
match_requests_collection            = database["match_requests"]
match_data_collection                = database["match_data"]
match_fixtures_collection            = database["match_fixtures"]
club_squads_collection               = database["club_squads"]
competitions_collection              = database["competitions"]
dco_assignments_collection         = database["dco_assignments"]


# =========================
# Token / Payments
# =========================
player_tokens_collection             = database["player_tokens"]
club_tokens_collection               = database["club_tokens"]
scout_tokens_collection              = database["scout_tokens"]
dco_tokens_collection                = database["dco_tokens"]
agent_tokens_collection              = database["agent_tokens"]

token_packages_collection            = database["token_packages"]
topup_packages_collection            = database["topup_packages"]

transactions_collection              = database["transactions"]
token_transactions_collection        = database["token_transactions"]
payment_intents_collection           = database["payment_intents"]


# =========================
# Subscription Collections
# =========================
subscription_plans_collection        = database["subscription_plans"]
subscriptions_collection             = database["subscriptions"]
subscription_audit_collection        = database["subscription_audit"]


# =========================
# Communication Collections
# =========================
notifications_collection             = database["notifications"]
admin_notifications_collection       = database["admin_notifications"]
messages_collection                  = database["messages"]
broadcasts_collection                = database["broadcasts"]
announcements_collection             = database["announcements"]
newsletters_collection               = database["newsletters"]
newsletter_subscribers_collection    = database["newsletter_subscribers"]

contact_collection                   = database["contact"]
contact_messages_collection          = database["contact_messages"]

support_tickets_collection           = database["support_tickets"]
support_messages_collection          = database["support_messages"]


# =========================
# Website / CMS
# =========================
page_content_collection              = database["page_content"]


# =========================
# Analytics & System
# =========================
leaderboard_collection               = database["leaderboard"]
analytics_data_collection            = database["analytics_data"]
activity_history_collection          = database["activity_history"]
system_logs_collection               = database["system_logs"]
platform_settings_collection         = database["platform_settings"]
config_collection                    = database["config"]


# =========================
# Authentication & Security
# =========================
user_sessions_collection             = database["user_sessions"]
verification_codes_collection        = database["verification_codes"]
password_reset_tokens_collection     = database["password_reset_tokens"]
email_verification_tokens_collection = database["email_verification_tokens"]
referral_codes_collection            = database["referral_codes"]
liveness_sessions_collection         = database["liveness_sessions"]


# =========================
# Utility Collections
# =========================
counters_collection                  = database["counters"]
# ============================================================
# START: CANONICAL ROLE / ID / PERMISSION REGISTRY
# ============================================================

ROLE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Core platform identities. This registry is the single source of truth for
    # role names, collections, public IDs, permissions and eligibility rules.
    "player": {"collection_name": "players_collection", "id_field": "player_id", "id_prefix": None, "token_eligible": True, "subscription_eligible": True},
    "club": {"collection_name": "clubs_collection", "id_field": "club_id", "id_prefix": None, "token_eligible": True, "subscription_eligible": True},
    "scout": {"collection_name": "scouts_collection", "id_field": "scout_id", "id_prefix": "SCT-ES", "token_eligible": True, "subscription_eligible": True},
    "dco": {"collection_name": "dco_collection", "id_field": "dco_id", "id_prefix": "DCO-ES", "token_eligible": True, "subscription_eligible": True},
    "agent": {"collection_name": "agents_collection", "id_field": "agent_id", "id_prefix": "AGT-ES", "token_eligible": True, "subscription_eligible": True},
    "supervisor": {"collection_name": "supervisors_collection", "id_field": "supervisor_id", "id_prefix": "SVR-ES", "token_eligible": False, "subscription_eligible": False},
    "communication_officer": {"collection_name": "communication_officers_collection", "id_field": "co_id", "id_prefix": "ES-COM", "token_eligible": False, "subscription_eligible": False},
    "customer_care": {"collection_name": "customer_care_collection", "id_field": "cc_id", "id_prefix": "ES-CCA", "token_eligible": False, "subscription_eligible": False},
    "admin": {"collection_name": "admins_collection", "id_field": "admin_id", "id_prefix": "ADM", "token_eligible": False, "subscription_eligible": False},
    "content_manager": {"collection_name": "content_managers_collection", "id_field": "cm_id", "id_prefix": "CM-ES", "token_eligible": False, "subscription_eligible": False},
    "sub_admin": {"collection_name": "sub_admins_collection", "id_field": "sub_admin_id", "id_prefix": "SAD-ES", "token_eligible": False, "subscription_eligible": False},
}

CANONICAL_ROLES = frozenset(ROLE_REGISTRY)
TOKEN_ELIGIBLE_ROLES = frozenset(role for role, meta in ROLE_REGISTRY.items() if meta["token_eligible"])
SUBSCRIPTION_ELIGIBLE_ROLES = frozenset(role for role, meta in ROLE_REGISTRY.items() if meta["subscription_eligible"])
ROLE_COLLECTION_MAP: Dict[str, tuple[str, str]] = {
    role: (meta["collection_name"], meta["id_field"])
    for role, meta in ROLE_REGISTRY.items()
}

# Human-facing role metadata is deliberately centralized so dashboards/admin
# tooling cannot silently drift from the authentication contract.
ROLE_LABELS = {
    "player": "Player", "club": "Club", "scout": "Scout", "dco": "Data Collection Officer",
    "agent": "Agent", "supervisor": "Supervisor", "communication_officer": "Communications Officer",
    "customer_care": "Customer Care", "admin": "Admin", "content_manager": "Content Manager", "sub_admin": "Sub-Admin",
}

# Explicit permission matrix: Sub-Admin and Content Manager are not aliases of Admin.
ROLE_PERMISSIONS: Dict[str, frozenset[str]] = {
    "admin": frozenset({"users.read", "users.create", "users.update", "users.delete", "content.read", "content.create", "content.update", "content.publish", "dco.assign", "dco.review", "dco.approve", "payments.read", "payments.approve", "settings.read", "settings.update"}),
    "sub_admin": frozenset({"users.read", "users.create", "users.update", "content.read", "dco.assign", "dco.review", "payments.read", "settings.read"}),
    "content_manager": frozenset({"content.read", "content.create", "content.update", "content.publish"}),
    "dco": frozenset({"dco.review"}),
    "supervisor": frozenset({"dco.review", "dco.approve", "payments.read"}),
    "communication_officer": frozenset({"content.read", "content.create", "content.update"}),
    "customer_care": frozenset(),
    "player": frozenset(), "club": frozenset(), "scout": frozenset(), "agent": frozenset(),
}

def normalize_role(role: str) -> str:
    value = (role or "").strip().lower()
    aliases = {"comms_officer": "communication_officer", "co": "communication_officer", "cc": "customer_care", "cc_agent": "customer_care", "data_collection_officer": "dco"}
    value = aliases.get(value, value)
    if value not in CANONICAL_ROLES:
        raise ValueError(f"Unsupported user role: {role}")
    return value

def role_has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), frozenset())

def role_collection(role: str):
    canonical = normalize_role(role)
    collection_name, _ = ROLE_COLLECTION_MAP[canonical]
    return globals()[collection_name]

# Backward-compatible public registry expected by route modules.
USER_COLLECTIONS = {
    role: {"collection": role_collection(role), "id_field": meta["id_field"], "alt_fields": ["user_id"]}
    for role, meta in ROLE_REGISTRY.items()
}



async def resolve_user_doc(user_id: str, role: str) -> Optional[dict]:
    """Fetch a user document from the role-appropriate MongoDB collection.

    Tries the role-specific primary-ID field first, then falls back to
    the generic ``user_id`` field so that legacy documents are still found.

    Args:
        user_id: The user's unique ID (player_id, club_id, admin_id ...).
        role:    One of the keys in ``ROLE_COLLECTION_MAP``.

    Returns:
        Raw MongoDB document dict or ``None``.
    """
    role = normalize_role(role)
    col_name, id_field = ROLE_COLLECTION_MAP[role]
    col = globals().get(col_name)
    if col is None:
        return None
    doc = await col.find_one({id_field: user_id})
    if not doc:
        doc = await col.find_one({"user_id": user_id})
    return doc


def extract_display_name(doc: dict, fallback: str = "") -> str:
    """Return the best human-readable display name from any user document.

    Resolution order: name → full_name → firstName+lastName → email → fallback.
    """
    return (
        doc.get("name")
        or doc.get("full_name")
        or (f"{doc.get('firstName', '')} {doc.get('lastName', '')}".strip() or None)
        or doc.get("email")
        or fallback
    )

# ============================================================
# END: CANONICAL ROLE / ID / PERMISSION REGISTRY
# ============================================================

# ============================================================
# MONGO SERIALIZER
# ============================================================

class MongoSerializer:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def ensure_timezone_aware(dt: datetime) -> datetime:
        if not isinstance(dt, datetime):
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def serialize_value(value: Any) -> Any:
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: MongoSerializer.serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [MongoSerializer.serialize_value(item) for item in value]
        else:
            return value

    @staticmethod
    def serialize_document(doc: Optional[Dict]) -> Dict:
        if not doc:
            return {}
        result = {}
        for key, value in doc.items():
            result[key] = MongoSerializer.serialize_value(value)
        if "_id" in result and isinstance(doc.get("_id"), ObjectId):
            result["_id"] = str(doc["_id"])
        return result

    @staticmethod
    def serialize_documents(docs: List[Dict]) -> List[Dict]:
        if not docs:
            return []
        return [MongoSerializer.serialize_document(d) if isinstance(d, dict) else d for d in docs]

    @staticmethod
    def serialize_list(docs: List[Dict]) -> List[Dict]:
        """Alias for serialize_documents."""
        return MongoSerializer.serialize_documents(docs)

    @staticmethod
    def prepare_for_insert(doc: Dict[str, Any]) -> Dict[str, Any]:
        return {k: MongoSerializer.prepare_value_for_insert(k, v) for k, v in doc.items()}

    @staticmethod
    def prepare_value_for_insert(key: str, value: Any) -> Any:
        if isinstance(value, str) and key in ["_id", "user_id", "unique_id", "player_id", "club_id", "scout_id", "agent_id", "dco_id", "supervisor_id", "co_id", "cc_id", "admin_id", "cm_id", "sub_admin_id"] and len(value) == 24:
            try:
                return ObjectId(value)
            except Exception:
                return value
        elif isinstance(value, str):
            try:
                if "T" in value and ("Z" in value or "+" in value or value.endswith("00:00")):
                    parsed_dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if parsed_dt.tzinfo is None:
                        parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                    return parsed_dt
            except Exception:
                pass
            return value
        elif isinstance(value, dict):
            return {k: MongoSerializer.prepare_value_for_insert(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [MongoSerializer.prepare_value_for_insert("", item) for item in value]
        return value


# ============================================================
# CUSTOM JSON RESPONSE
# ============================================================

class MongoJSONResponse(JSONResponse):
    def __init__(self, content: Any = None, status_code: int = 200, **kwargs):
        if content is not None:
            if isinstance(content, dict):
                content = MongoSerializer.serialize_document(content)
            elif isinstance(content, list):
                content = MongoSerializer.serialize_documents(content)
            else:
                content = MongoSerializer.serialize_value(content)
        super().__init__(content=content, status_code=status_code, **kwargs)

# ============================================================
# START: PYDANTIC / API MODELS
# ============================================================

class PlayerRegistration(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    middle_name: Optional[str] = ""
    dob: Optional[str] = ""
    gender: Optional[str] = ""
    height: Optional[str] = ""
    nationality: Optional[str] = "Nigeria"
    dominant_foot: Optional[str] = ""
    preferred_position: Optional[str] = ""
    player_level: Optional[str] = "other"
    club_name: Optional[str] = ""
    jersey_number: Optional[str] = None
    confirm_password: Optional[str] = None

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if v is not None and "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v


class ClubRegistration(BaseModel):
    email: str
    password: str
    club_name: Optional[str] = ""
    club_nickname: Optional[str] = ""
    year_established: Optional[int] = 2000
    country: Optional[str] = "Nigeria"
    stadium: Optional[str] = ""
    address: Optional[str] = ""
    category: Optional[str] = "other"
    confirm_password: Optional[str] = None

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if v is not None and "password" in info.data and v != info.data["password"]:
            raise ValueError("passwords do not match")
        return v


class DataScoutRegistration(BaseModel):
    email: str
    password: Optional[str] = "defaultPassword123"
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    phone: Optional[str] = ""
    country: Optional[str] = "Nigeria"
    state: Optional[str] = ""
    lga: Optional[str] = ""
    nin: Optional[str] = ""
    position: Optional[str] = ""


class GoalBreakdown(BaseModel):
    header: int = 0
    shot: int = 0
    penalty: int = 0


class MatchStatsResponse(BaseModel):
    match_id: str
    title: str
    date: str
    minutes: int
    performance_score: float
    stats: dict
    goal_breakdown: GoalBreakdown


class UserType(str, Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"

    PLAYER = "player"
    CLUB = "club"
    SCOUT = "scout"
    DCO = "dco"
    AGENT = "agent"

    COMMUNICATION_OFFICER = "communication_officer"
    CUSTOMER_CARE = "customer_care"
    CONTENT_MANAGER = "content_manager"
    SUB_ADMIN = "sub_admin"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PlayerProfile(BaseModel):
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    dob: Optional[str] = None
    height: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    dominantFoot: Optional[str] = None
    preferredPosition: Optional[str] = None
    preferredPositionCategory: Optional[str] = None
    club: Optional[str] = None
    category: Optional[str] = None
    bio: Optional[str] = None
    achievements: Optional[List[str]] = None


class ScoutProfile(BaseModel):
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class PlayerStats(BaseModel):
    player_id: Optional[str] = None
    match_date: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    home_score: Optional[int] = 0
    away_score: Optional[int] = 0
    match_duration: Optional[int] = 0
    half: Optional[str] = None
    additional_minutes: Optional[int] = 0
    goals: Optional[int] = 0
    goal_breakdown: Optional[Dict[str, int]] = Field(
        default_factory=lambda: {"shot": 0, "header": 0, "penalty": 0}
    )
    assists: Optional[int] = 0
    shots_on_target: Optional[int] = 0
    shots_off_target: Optional[int] = 0
    successful_dribbles: Optional[int] = 0
    unsuccessful_dribbles: Optional[int] = 0
    successful_crosses: Optional[int] = 0
    unsuccessful_crosses: Optional[int] = 0
    fouls_won: Optional[int] = 0
    successful_short_passes: Optional[int] = 0
    unsuccessful_short_passes: Optional[int] = 0
    successful_long_passes: Optional[int] = 0
    unsuccessful_long_passes: Optional[int] = 0
    dispossessed: Optional[int] = 0
    aerial_duels_won: Optional[int] = 0
    aerial_duels_lost: Optional[int] = 0
    tackles_won: Optional[int] = 0
    tackles_lost: Optional[int] = 0
    interceptions: Optional[int] = 0
    clearances: Optional[int] = 0
    saves: Optional[int] = 0
    goals_conceded: Optional[int] = 0
    penalty_saves: Optional[int] = 0
    clean_sheets: Optional[int] = 0
    yellow_cards: Optional[int] = 0
    red_cards: Optional[int] = 0
    fouls_given: Optional[int] = 0
    offsides: Optional[int] = 0
    minutes_played: Optional[int] = 0
    status: Optional[str] = "submitted"
    scout_id: Optional[str] = None
    submitted_at: datetime = Field(default_factory=lambda: MongoSerializer.now_utc())
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    performance_score: Optional[float] = None
    request_id: Optional[str] = None

    class Config:
        extra = "allow"


class StatsRequest(BaseModel):
    matchDate: str
    matchTime: str
    homeTeam: str
    awayTeam: str
    venueState: str
    venueLGA: str
    venueAddress: str
    contactPhone: str
    additionalNotes: Optional[str] = None


class MatchHistoryResponse(BaseModel):
    date: str
    match: str
    score: str
    venue: Optional[str] = None
    time: Optional[str] = None
    upcoming: Optional[bool] = False


class FixtureRequest(BaseModel):
    matchDate: date
    matchTime: time
    homeTeam: str
    awayTeam: str
    venueState: str
    venueLGA: str
    venueAddress: str
    contactPhone: str
    additionalNotes: Optional[str] = None


class FixtureResponse(BaseModel):
    reference_id: str
    status: str


class Transaction(BaseModel):
    id: str
    type: str
    description: str
    amount: Optional[float] = 0
    status: str
    reference: str
    date: str
    read: bool = False


class CreditTokenRequest(BaseModel):
    unique_id: str
    entity_type: str
    tokens: int
    reason: Optional[str] = "Admin credit"

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v):
        if not v or not v.strip():
            return "Admin credit"
        return v.strip()

    class Config:
        extra = "ignore"


class TokenInfo(BaseModel):
    balance: int
    expiry: str
    price: float


class ScoutAssignment(BaseModel):
    scout_id: str
    requestId: str
    notes: Optional[str] = None


class PaymentInitiation(BaseModel):
    amount: float
    tokens: int
    description: str


class PaymentVerification(BaseModel):
    transaction_id: str
    tx_ref: str


class MessageCreate(BaseModel):
    content: str
    recipientType: Optional[str] = None
    specificUser: Optional[str] = None
    subject: Optional[str] = None


class AdminMessageCreate(BaseModel):
    recipientType: str
    subject: str
    content: str
    specificUser: Optional[str] = None


class StatsSubmission(BaseModel):
    scout_id: str
    scout_name: str
    assignment_id: str
    submission_timestamp: str
    match: Dict[str, Any]
    player: Dict[str, Any]


class NewsletterSubscription(BaseModel):
    email: EmailStr


class ContactForm(BaseModel):
    type: str
    name: str
    email: EmailStr
    message: str
    timestamp: Optional[str] = None


class BioUpdate(BaseModel):
    bio: str

# ============================================================
# END: PYDANTIC / API MODELS
# ============================================================

# ============================================================
# PING / AUTO-PING
# ============================================================

async def ping_platform(name: str, url: str):
    now = MongoSerializer.now_utc()
    last_log = MONITORING_URLS[name].get("last_log")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.get(url)
        if not last_log or (now - last_log) >= timedelta(minutes=10):
            logger.info(f"Auto-pinged '{name}' at {now.isoformat()} UTC")
            MONITORING_URLS[name]["last_log"] = now
    except Exception as e:
        logger.warning(f"Failed to ping '{name}': {e}")


async def auto_ping_task():
    while True:
        now = MongoSerializer.now_utc()
        tasks = []
        for name, info in MONITORING_URLS.items():
            last_ping = info.get("last_ping")
            interval = info.get("interval", 300)
            if not last_ping or (now - last_ping).total_seconds() >= interval:
                tasks.append(ping_platform(name, info["url"]))
                MONITORING_URLS[name]["last_ping"] = now
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(5)

# ============================================================
# DATE RANGE HELPERS
# ============================================================

def get_week_date_range(week: int, year: int):
    first_day = datetime(year, 1, 1, tzinfo=timezone.utc)
    if first_day.weekday() <= 3:
        start_date = first_day - timedelta(days=first_day.weekday())
    else:
        start_date = first_day + timedelta(days=(7 - first_day.weekday()))
    week_start = start_date + timedelta(weeks=week - 1)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start, week_end


def get_month_date_range(month: int, year: int):
    _, num_days = monthrange(year, month)
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    end_date = datetime(year, month, num_days, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date


def fix_timestamp(ts):
    if ts is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if isinstance(ts, str):
        for fmt_func in [
            lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
            lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
            lambda s: datetime.strptime(s, "%Y-%m-%d"),
        ]:
            try:
                dt = fmt_func(ts)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            except Exception:
                continue
    return datetime.min.replace(tzinfo=timezone.utc)


def to_utc(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def is_future(dt):
    utc_dt = to_utc(dt)
    return utc_dt > datetime.now(timezone.utc) if utc_dt else False

# ============================================================
# START: CANONICAL ID GENERATION
# ============================================================

async def get_next_sequence(name: str) -> int:
    result = await counters_collection.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["seq"]


async def generate_user_id(user_type: str, player_level: str = "") -> str:
    """
    Generate a unique Enejistats platform ID.

    Canonical staff IDs:
        Content Manager       -> CM-ES-00001
        Sub-Admin             -> SAD-ES-00001

    Player IDs:
        Professional       -> ES-PP-00001
        Semi-Professional  -> ES-SP-00001
        Academy            -> ES-AP-00001
        University         -> ES-UP-00001
        Other/Local        -> ES-OP-00001

    Club IDs:
        Professional       -> ES-PC-00001
        Semi-Professional  -> ES-SC-00001
        Academy            -> ES-AC-00001
        University         -> ES-UC-00001
        Other/Local        -> ES-OC-00001

    """

    user_type = normalize_role(user_type)

    ID_CONFIG = {
        "player": {
            "sequence": "player_id",
            "player_levels": {"professional": "PP", "semi-professional": "SP", "academy": "AP", "university": "UP", "other": "OP"},
        },
        "club": {
            "sequence": "club_id",
            "club_levels": {"professional": "PC", "semi-professional": "SC", "academy": "AC", "university": "UC", "other": "OC"},
        },
    }
    for _role, _meta in ROLE_REGISTRY.items():
        if _role in ID_CONFIG:
            continue
        ID_CONFIG[_role] = {
            "sequence": _meta["id_field"],
            "prefix": _meta["id_prefix"],
        }


    # normalize_role() already resolves all supported compatibility aliases.
    resolved_type = user_type
    config = ID_CONFIG[resolved_type]

    # Player IDs require level-specific prefixes
    if resolved_type == "player":
        level = (player_level or "other").lower().strip()
        sub_prefix = config["player_levels"].get(
            level,
            config["player_levels"]["other"],
        )
        sequence = await get_next_sequence(config["sequence"])
        return f"ES-{sub_prefix}-{sequence:05d}"

    # Club IDs require level-specific prefixes
    if resolved_type == "club":
        level = (player_level or "other").lower().strip()
        sub_prefix = config["club_levels"].get(
            level,
            config["club_levels"]["other"],
        )
        sequence = await get_next_sequence(config["sequence"])
        return f"ES-{sub_prefix}-{sequence:05d}"

    # All remaining user types
    sequence = await get_next_sequence(config["sequence"])
    return f"{config['prefix']}-{sequence:05d}"

# ============================================================
# END: CANONICAL ID GENERATION
# ============================================================

# ============================================================
# CLOUDINARY UPLOAD
# ============================================================

# ── Extension → Cloudinary resource_type lookup ────────────────────────────
_VIDEO_EXTENSIONS: frozenset = frozenset({
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
    ".flv", ".wmv", ".3gp", ".ogv", ".ts", ".mts", ".mpg", ".mpeg",
})
_IMAGE_EXTENSIONS: frozenset = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".tiff", ".tif", ".svg", ".heic", ".heif", ".avif",
})
_DOC_EXTENSIONS: frozenset = frozenset({
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt",
})

def _detect_cloudinary_resource_type(filename: str) -> str:
    """Return the Cloudinary resource_type for the given filename."""
    ext = os.path.splitext((filename or "").lower())[1]
    if ext in _VIDEO_EXTENSIONS:
        return "video"
    if ext in _IMAGE_EXTENSIONS:
        return "image"
    if ext in _DOC_EXTENSIONS:
        return "raw"
    return "auto"


# Large-file threshold: use upload_large (chunked) above this limit.
_CLOUDINARY_LARGE_FILE_THRESHOLD = 15 * 1024 * 1024  # 15 MB
_CLOUDINARY_CHUNK_SIZE            =  6 * 1024 * 1024  #  6 MB chunks


async def upload_to_cloudinary(
    file_content: bytes,
    filename: str = "",
    folder: str = "enejistats",
    resource_type: str = "auto",
    public_id: Optional[str] = None,
    user_type: Optional[str] = None,
    file_category: str = "general",
) -> str:
    """
    Upload *bytes* to Cloudinary **asynchronously**.

    Key fixes vs. original implementation
    ──────────────────────────────────────
    1. The blocking ``cloudinary.uploader.upload`` / ``upload_large`` SDK calls
       are executed in a thread-pool via ``asyncio.to_thread`` so the async
       event loop is never blocked — critical for large video uploads.

    2. ``resource_type`` is auto-detected from the filename extension when the
       caller leaves it at ``"auto"``.  Videos are uploaded as
       ``resource_type="video"``, images as ``"image"``, documents as ``"raw"``.
       Explicit detection prevents Cloudinary from misclassifying raw video bytes.

    3. The caller-supplied ``folder`` is used **as-is** when ``user_type`` is
       not provided.  The previous code appended ``/general`` unconditionally,
       corrupting paths like ``"enejistats/venues/photos"``.

    4. Files above 15 MB are uploaded with ``cloudinary.uploader.upload_large``
       in 6 MB chunks to avoid memory pressure and request timeouts.

    5. Empty byte strings are rejected early with a clear error.

    Supported ``user_type`` values:
        player, club, scout, dco, agent, supervisor, communication_officer,
        customer_care, admin, content_manager, sub_admin

    Resulting folder layout (when user_type is supplied):
        enejistats/players/<file_category>/
        enejistats/clubs/<file_category>/
        enejistats/scouts/<file_category>/
        enejistats/dco/<file_category>/
        enejistats/agents/<file_category>/
        enejistats/supervisors/<file_category>/
        enejistats/admin/<file_category>/

    When user_type is None the ``folder`` argument is used verbatim
    (e.g. ``"enejistats/venues/photos"``).

    Raises:
        HTTPException 503 — Cloudinary not configured.
        HTTPException 400 — empty file_content.
        HTTPException 500 — any upload error.
    """
    import functools
    import io as _io

    if not cloudinary_url or not _cloudinary_available:
        logger.error("Cloudinary not configured — cannot upload file")
        raise HTTPException(
            status_code=503,
            detail="File storage service not configured",
        )

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="Cannot upload an empty file.",
        )

    try:
        VALID_USER_TYPES = {
            *CANONICAL_ROLES,
        }

        safe_filename = (
            re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
            if filename
            else "file"
        )

        # ── Auto-detect resource_type from filename extension ─────────────
        if resource_type == "auto" and filename:
            resource_type = _detect_cloudinary_resource_type(filename)

        # ── Build folder structure ─────────────────────────────────────────
        if user_type:
            user_type = user_type.lower().strip()
            if user_type not in VALID_USER_TYPES:
                raise ValueError(f"Unsupported user type: {user_type}")
            folder_names = {
                "player": "players",
                "club":   "clubs",
                "scout":  "scouts",
                "dco":    "dco",
                "agent":  "agents",
                "supervisor": "supervisors",
                "communication_officer": "communication_officers",
                "customer_care": "customer-care",
                "admin":  "admin",
                "content_manager": "content-managers",
                "sub_admin": "sub-admins",
            }
            folder = (
                f"enejistats/"
                f"{folder_names[user_type]}/"
                f"{file_category.lower()}"
            )
        # ── When no user_type, use the caller-supplied folder verbatim ────
        # Do NOT append "/general" — the caller already provides a complete
        # path (e.g. "enejistats/venues/photos", "enejistats/clubs/logos").

        # ── Generate a unique public_id ────────────────────────────────────
        if public_id is None:
            timestamp = MongoSerializer.now_utc().strftime("%Y%m%d%H%M%S")
            prefix    = user_type or "file"
            public_id = (
                f"{prefix}_{safe_filename}_{timestamp}_{secrets.token_hex(4)}"
            )

        upload_kwargs = {
            "folder":        folder,
            "resource_type": resource_type,
            "overwrite":     True,
            "public_id":     public_id,
            "use_filename":  False,   # we control public_id ourselves
        }

        # ── Choose upload method based on file size ────────────────────────
        # Cloudinary recommends upload_large (chunked) for files > 20 MB;
        # we threshold at 15 MB for headroom.
        if len(file_content) > _CLOUDINARY_LARGE_FILE_THRESHOLD:
            logger.info(
                "Large file detected (%d bytes) — using chunked upload for '%s'",
                len(file_content), safe_filename,
            )
            upload_kwargs["chunk_size"] = _CLOUDINARY_CHUNK_SIZE
            _uploader_fn   = cloudinary.uploader.upload_large
            _upload_target = _io.BytesIO(file_content)
        else:
            _uploader_fn   = cloudinary.uploader.upload
            _upload_target = file_content

        # ── Off-load the blocking SDK call to a thread-pool executor ──────
        # cloudinary.uploader.upload / upload_large are synchronous.
        # Calling them directly in an async def blocks the event loop,
        # causing timeouts on video uploads and starving concurrent requests.
        upload_result = await asyncio.to_thread(
            functools.partial(_uploader_fn, _upload_target, **upload_kwargs)
        )

        secure_url = upload_result.get("secure_url")
        if not secure_url:
            raise ValueError("Cloudinary returned no secure_url.")

        logger.info(
            "Uploaded '%s' → folder='%s' resource_type=%s size=%d bytes",
            safe_filename, folder, resource_type, len(file_content),
        )
        return secure_url

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Cloudinary upload failed for '%s'", filename)
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}",
        )

# ============================================================
# START: AUTHENTICATION / JWT / PASSWORD SERVICES
# ============================================================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Expected payload keys include:
        - sub
        - user_id
        - unique_id
        - user_type
        - role

    Supported user types:
        - player
        - club
        - scout
        - dco
        - agent
        - supervisor
        - admin
        - communication_officer
        - customer_care
        - content_manager
        - sub_admin
    """

    to_encode = data.copy()

    # One canonical authorization claim. role/user_type are mirrored aliases.
    raw_role = to_encode.get("role") or to_encode.get("user_type")
    canonical_role = normalize_role(raw_role)
    to_encode["role"] = canonical_role
    to_encode["user_type"] = canonical_role
    if "user_id" not in to_encode and "unique_id" in to_encode:
        to_encode["user_id"] = to_encode["unique_id"]
    if "unique_id" not in to_encode and "user_id" in to_encode:
        to_encode["unique_id"] = to_encode["user_id"]
    if "sub" not in to_encode:
        raise ValueError("JWT payload requires 'sub'")

    expire = (
        MongoSerializer.now_utc()
        + (
            expires_delta
            or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        )
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT access token.

    Returns:
        Payload dictionary if valid.
        None if invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        # Validate minimum required claims
        required_fields = {
            "sub",
            "user_type",
            "role",
        }

        if not required_fields.issubset(payload.keys()):
            return None

        role = normalize_role(payload.get("role"))
        user_type = normalize_role(payload.get("user_type"))
        if role != user_type:
            return None
        payload["role"] = role
        payload["user_type"] = role
        if "user_id" not in payload and "unique_id" in payload:
            payload["user_id"] = payload["unique_id"]
        if "unique_id" not in payload and "user_id" in payload:
            payload["unique_id"] = payload["user_id"]
        return payload

    except jwt.ExpiredSignatureError:
        return None

    except (jwt.PyJWTError, ValueError, TypeError):
        return None


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """

    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plaintext password against its bcrypt hash.
    """

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
            if isinstance(hashed_password, str)
            else hashed_password,
        )

    except Exception:
        return False

# ============================================================
# END: AUTHENTICATION / JWT / PASSWORD SERVICES
# ============================================================

# ============================================================
# CANONICAL IDENTITY NORMALIZATION HELPERS
# ============================================================

def normalize_email(email: str) -> str:
    """Return the canonical storage/login representation for an email address."""
    return str(email or "").strip().lower()


def build_user_access_token(user: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT from a normalized role document using the canonical claim contract."""
    role = normalize_role(user.get("role") or user.get("user_type"))
    id_field = ROLE_COLLECTION_MAP[role][1]
    canonical_id = user.get(id_field) or user.get("user_id") or user.get("unique_id")
    if not canonical_id:
        raise ValueError(f"User document has no canonical ID for role {role}")
    mongo_sub = user.get("_id")
    if not mongo_sub:
        raise ValueError("User document has no MongoDB _id")
    return create_access_token({
        "sub": str(mongo_sub),
        "user_id": str(canonical_id),
        "unique_id": str(canonical_id),
        "role": role,
        "user_type": role,
    }, expires_delta=expires_delta)


# ============================================================
# GPS HELPER
# ============================================================

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance in metres between two GPS points."""
    R    = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ============================================================
# GENERIC USER DOCUMENT HELPERS
# Supports: player, club, scout, dco, agent
# ============================================================


async def _find_user_doc(user_type: str, unique_id: str) -> Optional[dict]:
    """
    Find any supported user by its human-readable ID,
    alternative IDs, or MongoDB ObjectId.

    Supported:
        - player
        - club
        - scout
        - dco
        - agent
    """

    user_type = normalize_role(user_type)

    config = USER_COLLECTIONS.get(user_type)

    if config is None:
        raise ValueError(f"Unsupported user type: {user_type}")

    collection = config["collection"]
    id_field = config["id_field"]

    # Primary ID lookup
    doc = await collection.find_one({id_field: unique_id})
    if doc:
        return doc

    # Alternative ID lookups
    for field in config.get("alt_fields", []):
        doc = await collection.find_one({field: unique_id})
        if doc:
            return doc

    # MongoDB ObjectId lookup
    if len(str(unique_id)) == 24:
        try:
            doc = await collection.find_one(
                {"_id": ObjectId(unique_id)}
            )
            if doc:
                return doc
        except Exception:
            pass

    return None


def _user_id_from_doc(user_type: str, doc: dict) -> str:
    """
    Return the human-readable unique ID from any user document.
    """

    user_type = normalize_role(user_type)

    config = USER_COLLECTIONS.get(user_type)

    if config is None:
        raise ValueError(f"Unsupported user type: {user_type}")

    return doc.get(config["id_field"]) or str(doc.get("_id", ""))


def _user_auth_check(
    current_user: dict,
    target_user_id: str,
    user_type: str,
    allow_supervisor: bool = True,
) -> bool:
    """
    Authorization helper.

    Admin:
        Full access.

    Supervisor:
        Full access (optional).

    Others:
        May only access their own document.
    """

    role = current_user.get("role", "").lower()

    if role == "admin":
        return True

    if role == "supervisor" and allow_supervisor:
        return True

    config = USER_COLLECTIONS.get(user_type.lower())

    if config is None:
        return False

    possible_ids = [
        current_user.get(config["id_field"]),
        current_user.get("user_id"),
        current_user.get("id"),
    ]

    for uid in possible_ids:
        if uid and str(uid) == str(target_user_id):
            return True

    return False

# ============================================================
# CANONICAL DOMAIN IDENTIFIERS
# ============================================================

STATS_ID_FIELDS = {"player_id", "scout_id", "dco_id", "request_id", "assignment_id", "reference_id", "match_id"}
CANONICAL_STATS_REQUEST_FIELDS = {"request_id", "player_id", "scout_id", "dco_id", "assignment_id", "reference_id", "status", "created_at", "updated_at"}

def normalize_stats_identity_fields(document: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy camelCase stats identifiers into canonical snake_case fields."""
    doc = dict(document or {})
    aliases = {
        "requestId": "request_id", "statsRequestId": "request_id", "stats_request_id": "request_id",
        "assignmentId": "assignment_id", "scoutId": "scout_id", "playerId": "player_id",
        "dcoId": "dco_id", "matchId": "match_id", "referenceId": "reference_id",
    }
    for legacy, canonical in aliases.items():
        if canonical not in doc and legacy in doc:
            doc[canonical] = doc[legacy]
    return doc


# ============================================================
# TOKEN COST HELPERS
# ============================================================

def get_token_cost_for_user(user_type: str, category: str) -> int:
    """
    Get the token cost for a supported user type and category/level.

    Delegates to the module-level ``get_token_cost`` defined above —
    pricing is the single source of truth.

    Args:
        user_type: One of ``"player"``, ``"club"``, ``"scout"``,
                   ``"dco"``, ``"agent"``.
        category:  Player/club level (canonical or alias) or ignored
                   for flat-rate roles.

    Returns:
        Integer token cost.

    Raises:
        ValueError: Unknown user type.
    """
    canonical_role = normalize_role(user_type)
    if canonical_role not in TOKEN_ELIGIBLE_ROLES:
        raise ValueError(f"Token pricing is not available for '{canonical_role}' accounts.")
    return get_token_cost(canonical_role, category)


def get_position_category(position: str) -> str:
    pos = position.lower() if position else ""
    if any(p in pos for p in ["striker", "forward", "winger", "attacker"]):
        return "ATTACK"
    if any(p in pos for p in ["midfielder", "midfield", "cam", "cdm"]):
        return "MIDFIELD"
    if any(p in pos for p in ["defender", "defence", "back", "centre-back", "fullback"]):
        return "DEFENCE"
    if any(p in pos for p in ["goalkeeper", "keeper", "gk"]):
        return "GOALKEEPER"
    return "MIDFIELD"

# ============================================================
# STAT NORMALIZATION
# ============================================================

def normalize_stat_key(key: str) -> str:
    key_lower = key.lower()
    stat_mappings = {
        "goals": ["goals", "goal", "totalgoals"],
        "assists": ["assists", "assist", "totalassists"],
        "shots_on_target": ["shots_on_target", "shotontarget", "shotsontarget", "ontarget"],
        "shots_off_target": ["shots_off_target", "shotofftarget", "shotsofftarget", "offtarget"],
        "successful_dribbles": ["successful_dribbles", "successfuldribbles", "dribbles_success"],
        "unsuccessful_dribbles": ["unsuccessful_dribbles", "unsuccessfuldribbles", "dribbles_fail"],
        "successful_crosses": ["successful_crosses", "successfulcrosses", "crosses_success"],
        "unsuccessful_crosses": ["unsuccessful_crosses", "unsuccessfulcrosses", "crosses_fail"],
        "successful_short_passes": ["successful_short_passes", "successfulshortpasses", "shortpasses", "passes"],
        "unsuccessful_short_passes": ["unsuccessful_short_passes", "unsuccessfulshortpasses"],
        "successful_long_passes": ["successful_long_passes", "successfullongpasses", "longpasses"],
        "unsuccessful_long_passes": ["unsuccessful_long_passes", "unsuccessfullongpasses"],
        "tackles_won": ["tackles_won", "tackleswon", "tackles_success", "tackles"],
        "tackles_lost": ["tackles_lost", "tackleslost", "tackles_fail"],
        "aerial_duels_won": ["aerial_duels_won", "aerialduels_won", "aerialduels", "duels_won"],
        "aerial_duels_lost": ["aerial_duels_lost", "aerialduels_lost", "duels_lost"],
        "interceptions": ["interceptions", "interception"],
        "clearances": ["clearances", "clearance"],
        "saves": ["saves", "save"],
        "goals_conceded": ["goals_conceded", "goalsconceded", "conceded"],
        "penalty_saves": ["penalty_saves", "penaltysaves"],
        "clean_sheets": ["clean_sheets", "cleansheets"],
        "yellow_cards": ["yellow_cards", "yellowcards", "yellow"],
        "red_cards": ["red_cards", "redcards", "red"],
        "fouls_given": ["fouls_given", "foulsgiven", "fouls"],
        "fouls_won": ["fouls_won", "foulswon"],
        "offsides": ["offsides", "offside"],
        "dispossessed": ["dispossessed", "dispossess"],
    }
    for standard_key, variants in stat_mappings.items():
        if key_lower in variants:
            return standard_key
    return key_lower


async def aggregate_player_stats(player_id: str, stats_list: List[Dict]) -> Dict[str, float]:
    if not stats_list:
        return {}
    all_stat_fields = [
        "goals", "assists", "shots_on_target", "shots_off_target",
        "successful_dribbles", "unsuccessful_dribbles",
        "successful_crosses", "unsuccessful_crosses",
        "successful_short_passes", "unsuccessful_short_passes",
        "successful_long_passes", "unsuccessful_long_passes",
        "tackles_won", "tackles_lost", "aerial_duels_won", "aerial_duels_lost",
        "interceptions", "clearances", "saves", "goals_conceded",
        "penalty_saves", "clean_sheets", "yellow_cards", "red_cards",
        "fouls_given", "fouls_won", "offsides", "dispossessed", "minutes_played",
    ]
    stat_totals = {f: 0 for f in all_stat_fields}
    stat_counts = {f: 0 for f in all_stat_fields}
    goal_breakdown_totals = {"shot": 0, "header": 0, "penalty": 0}
    for stat in stats_list:
        if "goal_breakdown" in stat:
            gb = stat["goal_breakdown"]
            goal_breakdown_totals["shot"] += gb.get("shot", 0)
            goal_breakdown_totals["header"] += gb.get("header", 0)
            goal_breakdown_totals["penalty"] += gb.get("penalty", 0)
        for key, value in stat.items():
            normalized_key = normalize_stat_key(key)
            if normalized_key in stat_totals:
                if isinstance(value, (int, float)):
                    stat_totals[normalized_key] += value
                    stat_counts[normalized_key] += 1
                elif isinstance(value, dict) and "success" in value:
                    stat_totals[normalized_key] += value.get("success", 0)
                    stat_counts[normalized_key] += 1
    aggregated_stats: Dict[str, Any] = {}
    for field in all_stat_fields:
        if stat_counts[field] > 0:
            aggregated_stats[field] = round(stat_totals[field] / stat_counts[field], 2)
        else:
            aggregated_stats[field] = 0
    aggregated_stats["goal_breakdown"] = goal_breakdown_totals
    total_passes = (
        aggregated_stats.get("successful_short_passes", 0)
        + aggregated_stats.get("unsuccessful_short_passes", 0)
        + aggregated_stats.get("successful_long_passes", 0)
        + aggregated_stats.get("unsuccessful_long_passes", 0)
    )
    successful_passes = (
        aggregated_stats.get("successful_short_passes", 0)
        + aggregated_stats.get("successful_long_passes", 0)
    )
    aggregated_stats["pass_accuracy"] = round(
        (successful_passes / total_passes * 100) if total_passes > 0 else 0, 1
    )
    return aggregated_stats


async def upsert_leaderboard_entries(period_type: str, period_identifier: str, leaderboard_players: list):
    try:
        for player in leaderboard_players:
            filter_query = {
                "player_id": ObjectId(player["id"]),
                "period_type": period_type,
                "period": period_identifier,
            }
            stats_field = f"{period_type}_stats"
            update_doc = {
                "$set": {
                    "player_id": ObjectId(player["id"]),
                    "name": player.get("name", "Unknown Player"),
                    "position": player.get("position", "Unknown"),
                    "position_category": player.get("position_category", "Unknown"),
                    "club": player.get("club", "Free Agent"),
                    "score": player.get("score", 0),
                    "rank": player.get("rank", 0),
                    "category": player.get("category", "local"),
                    "photo_url": player.get("photo_url"),
                    stats_field: player.get("aggregated_stats", {}),
                    "updated_at": MongoSerializer.now_utc(),
                }
            }
            await leaderboard_collection.update_one(filter_query, update_doc, upsert=True)
    except Exception:
        logger.exception(f"Error upserting leaderboard entries for {period_identifier}")

# ============================================================
# PERFORMANCE SCORE
# ============================================================

def calculate_performance_score(stats: dict, position: str = None) -> float:
    minutes = stats.get("minutes_played", 0) or 1
    factor = 90 / minutes if minutes > 0 else 1
    weights = {
        "goals": 2.8, "assists": 1.8,
        "shots_on_target": 0.9, "shots_off_target": 0.2,
        "successful_dribbles": 0.4, "unsuccessful_dribbles": -0.25,
        "successful_crosses": 0.5, "unsuccessful_crosses": -0.25,
        "fouls_won": 0.3,
        "successful_short_passes": 0.08, "unsuccessful_short_passes": -0.05,
        "successful_long_passes": 0.15, "unsuccessful_long_passes": -0.08,
        "aerial_duels_won": 0.4, "aerial_duels_lost": -0.25,
        "tackles_won": 0.6, "tackles_lost": -0.35,
        "interceptions": 0.5, "clearances": 0.6,
        "saves": 0.8, "goals_conceded": -0.6,
        "penalty_saves": 3.0, "clean_sheets": 2.5,
        "yellow_cards": -1.2, "red_cards": -3.5,
        "fouls_given": -0.4, "offsides": -0.2,
        "dispossessed": -0.3,
    }
    multipliers = {
        "ATTACK":     {"goals": 1.4, "assists": 1.1, "tackles_won": 1.2, "clearances": 1.3},
        "MIDFIELD":   {"successful_short_passes": 1.6, "successful_long_passes": 1.8, "assists": 1.3, "interceptions": 1.2, "tackles_won": 1.1},
        "DEFENCE":    {"goals": 1.5, "assists": 1.3, "clearances": 1.3, "interceptions": 1.2, "tackles_won": 1.3, "aerial_duels_won": 1.1},
        "GOALKEEPER": {"saves": 1.8, "penalty_saves": 2.0, "clean_sheets": 1.3, "goals": 2.5, "assists": 1.5},
    }
    category = get_position_category(position) if position else "MIDFIELD"
    pos_multiplier = multipliers.get(category, {})
    total_score = 3.5
    for stat, value in stats.items():
        if stat == "minutes_played" or not isinstance(value, (int, float)):
            continue
        base_weight = weights.get(stat, 0)
        multiplier = pos_multiplier.get(stat, 1.0)
        adjusted_value = value ** 0.9
        total_score += adjusted_value * base_weight * multiplier
    total_score = total_score * factor
    total_score = 10 * (1 - pow(2.71828, -0.2 * total_score))
    return round(max(0, min(10, total_score)), 2)

# ============================================================
# MATCH DEDUPLICATION UTILITIES
# ============================================================

def create_match_signature(home_team: str, away_team: str, match_date: str, player_id: str = None) -> str:
    base = f"{home_team.lower().strip()}_{away_team.lower().strip()}_{match_date}"
    if player_id:
        base += f"_{player_id}"
    return base


async def deduplicate_match_data(matches: List[Dict], key_func=None) -> List[Dict]:
    if not matches:
        return []
    seen = set()
    unique_matches = []
    for match in matches:
        if key_func:
            key = key_func(match)
        else:
            key = create_match_signature(
                match.get("home_team", match.get("homeTeam", "")),
                match.get("away_team", match.get("awayTeam", "")),
                match.get("match_date", match.get("date", "")),
            )
        if key not in seen:
            seen.add(key)
            unique_matches.append(match)
    return unique_matches


async def sync_match_lifecycle(stats_request_id: ObjectId, new_status: str) -> None:
    try:
        await stats_requests_collection.update_one(
            {"_id": stats_request_id},
            {"$set": {"status": new_status, "last_updated": MongoSerializer.now_utc()}},
        )
        if new_status == "completed":
            await dco_assignments_collection.update_many(
                {"$or": [{"request_id": stats_request_id}, {"requestId": stats_request_id}]},
                {"$set": {"status": "completed", "completed_at": MongoSerializer.now_utc()}},
            )
        elif new_status == "cancelled":
            await dco_assignments_collection.update_many(
                {"$or": [{"request_id": stats_request_id}, {"requestId": stats_request_id}]},
                {"$set": {"status": "cancelled", "cancelled_at": MongoSerializer.now_utc()}},
            )
    except Exception as e:
        logger.error(f"Error syncing match lifecycle: {e}")

# ============================================================
# TOKEN MANAGEMENT HELPERS
# ============================================================

async def search_users(
    user_type: str,
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Search supported platform users.

    Supported:
        - player
        - club
        - scout
        - dco
        - agent
    """

    user_type = user_type.lower().strip()

    USER_CONFIG = {
        "player": {
            "collection": players_collection,
            "token_collection": player_tokens_collection,
            "id_field": "player_id",
            "id_prefix": "ES-",
            "search_fields": [
                "firstName",
                "middleName",
                "lastName",
                "club",
                "email",
            ],
        },
        "club": {
            "collection": clubs_collection,
            "token_collection": club_tokens_collection,
            "id_field": "club_id",
            "id_prefix": "CL-",
            "search_fields": [
                "club_name",
                "club_nickname",
                "country",
                "address",
                "email",
            ],
        },
        "scout": {
            "collection": scouts_collection,
            "token_collection": scout_tokens_collection,
            "id_field": "scout_id",
            "id_prefix": "SC-",
            "search_fields": [
                "firstName",
                "middleName",
                "lastName",
                "region",
                "email",
            ],
        },
        "dco": {
            "collection": dco_collection,
            "token_collection": dco_tokens_collection,
            "id_field": "dco_id",
            "id_prefix": "DCO-",
            "search_fields": [
                "firstName",
                "middleName",
                "lastName",
                "department",
                "email",
            ],
        },
        "agent": {
            "collection": agents_collection,
            "token_collection": agent_tokens_collection,
            "id_field": "agent_id",
            "id_prefix": "AG-",
            "search_fields": [
                "firstName",
                "middleName",
                "lastName",
                "agency_name",
                "email",
            ],
        },
    }

    if user_type not in USER_CONFIG:
        raise ValueError(f"Unsupported user type: {user_type}")

    config = USER_CONFIG[user_type]

    collection = config["collection"]
    token_collection = config["token_collection"]
    id_field = config["id_field"]

    search_patterns = []

    if query.upper().startswith(config["id_prefix"]):
        search_patterns.append({id_field: query.upper()})
    else:
        for part in query.split():
            for field in config["search_fields"]:
                search_patterns.append(
                    {
                        field: {
                            "$regex": part,
                            "$options": "i",
                        }
                    }
                )

    if not search_patterns:
        search_patterns = [{}]

    users = await collection.find(
        {"$or": search_patterns}
    ).limit(limit).to_list(length=limit)

    results = []

    for user in users:

        token_info = await token_collection.find_one(
            {
                id_field: user.get(id_field)
            }
        )

        full_name = " ".join(
            filter(
                None,
                [
                    user.get("firstName", ""),
                    user.get("middleName", ""),
                    user.get("lastName", ""),
                ],
            )
        )

        display_name = (
            full_name
            if full_name
            else user.get("club_name")
            or user.get("agency_name")
            or ""
        )

        results.append(
            {
                "_id": str(user["_id"]),
                "unique_id": user.get(id_field),
                "user_type": user_type,
                "name": display_name,
                "email": user.get("email", ""),
                "category": user.get("category", ""),
                "tokens": token_info.get("balance", 0)
                if token_info
                else 0,
                "token_expiry": (
                    MongoSerializer.serialize_value(
                        token_info.get("expiry_date")
                    )
                    if token_info
                    else None
                ),
                "data": MongoSerializer.serialize_document(user),
            }
        )

    return results


async def credit_tokens(
    unique_id: str,
    user_type: str,
    amount: int,
    admin_id: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Credit tokens to a supported platform user.

    Supported:
        - player
        - club
        - scout
        - dco
        - agent

    Unsupported:
        - supervisor
        - admin
    """

    try:
        user_type = normalize_role(user_type)
        if user_type not in TOKEN_ELIGIBLE_ROLES:
            raise ValueError(f"Token credits are not supported for '{user_type}' accounts.")

        _TOKEN_COLS = {
            "player": player_tokens_collection, "club": club_tokens_collection,
            "scout": scout_tokens_collection, "dco": dco_tokens_collection,
            "agent": agent_tokens_collection,
        }
        user_collection = role_collection(user_type)
        id_field = ROLE_REGISTRY[user_type]["id_field"]
        token_collection = _TOKEN_COLS[user_type]

        # Find user
        user = await user_collection.find_one({id_field: unique_id})

        if not user:
            raise ValueError(
                f"{user_type.capitalize()} not found with ID: {unique_id}"
            )

        user_object_id = user["_id"]

        # Find wallet
        token_record = await token_collection.find_one(
            {id_field: unique_id}
        )

        previous_balance = (
            token_record.get("balance", 0)
            if token_record
            else 0
        )

        if token_record is None:
            new_balance = amount
            expiry_date = MongoSerializer.now_utc() + timedelta(days=365)

            await token_collection.insert_one(
                {
                    id_field: unique_id,
                    "balance": new_balance,
                    "expiry_date": expiry_date,
                    "created_at": MongoSerializer.now_utc(),
                    "updated_at": MongoSerializer.now_utc(),
                }
            )

        else:
            new_balance = previous_balance + amount

            expiry_date = token_record.get("expiry_date")

            if expiry_date:
                expiry_date = MongoSerializer.ensure_timezone_aware(
                    expiry_date
                )

            if (
                not expiry_date
                or expiry_date < MongoSerializer.now_utc()
            ):
                expiry_date = (
                    MongoSerializer.now_utc() + timedelta(days=365)
                )

            await token_collection.update_one(
                {"_id": token_record["_id"]},
                {
                    "$set": {
                        "balance": new_balance,
                        "expiry_date": expiry_date,
                        "updated_at": MongoSerializer.now_utc(),
                    }
                },
            )

        # Transaction
        transaction = {
            "user_id": user_object_id,
            "unique_id": unique_id,
            "user_type": user_type,
            "type": "credit",
            "amount": amount,
            "description": f"Admin credit: {reason}",
            "balance_before": previous_balance,
            "balance_after": new_balance,
            "admin_id": admin_id,
            "status": "completed",
            "reference": f"ADMIN-CREDIT-{secrets.token_hex(8).upper()}",
            "created_at": MongoSerializer.now_utc(),
        }

        await transactions_collection.insert_one(transaction)

        # Notification
        await notifications_collection.insert_one(
            {
                "user_id": user_object_id,
                "unique_id": unique_id,
                "user_type": user_type,
                "title": "Tokens Credited",
                "message": (
                    f"{amount} tokens have been credited to your account. "
                    f"Reason: {reason}"
                ),
                "type": "token_credit",
                "read": False,
                "created_at": MongoSerializer.now_utc(),
            }
        )

        logger.info(
            f"Admin {admin_id} credited {amount} tokens to "
            f"{user_type}:{unique_id}. New balance: {new_balance}"
        )

        return {
            "success": True,
            "user_id": str(user_object_id),
            "unique_id": unique_id,
            "user_type": user_type,
            "previous_balance": previous_balance,
            "new_balance": new_balance,
            "amount_credited": amount,
            "expiry_date": MongoSerializer.serialize_value(expiry_date),
            "transaction_reference": transaction["reference"],
        }

    except Exception as e:
        logger.error(
            f"Error crediting tokens to {user_type}:{unique_id}: {e}"
        )
        raise


async def deduct_tokens(
    user_id: str,
    user_type: str,
    amount: int,
    admin_id: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Deduct tokens from a supported platform user.

    Supported:
        - player
        - club
        - scout
        - agent
        - dco

    Unsupported:
        - supervisor
        - admin
    """

    try:
        user_type = normalize_role(user_type)
        if user_type not in TOKEN_ELIGIBLE_ROLES:
            raise ValueError(f"Token deductions are not supported for '{user_type}' accounts.")

        _TOKEN_COLS = {
            "player": player_tokens_collection, "agent": agent_tokens_collection,
            "club": club_tokens_collection, "scout": scout_tokens_collection,
            "dco": dco_tokens_collection,
        }
        collection = _TOKEN_COLS[user_type]

        # Fetch token wallet
        token_record = await collection.find_one(
            {f"{user_type}_id": user_id}
        )

        if not token_record:
            raise ValueError(
                f"No token wallet found for {user_type}."
            )

        current_balance = token_record.get("balance", 0)

        if current_balance < amount:
            raise ValueError(
                f"Insufficient balance. Current: {current_balance}, Required: {amount}"
            )

        new_balance = current_balance - amount

        # Update wallet balance
        await collection.update_one(
            {"_id": token_record["_id"]},
            {
                "$set": {
                    "balance": new_balance,
                    "updated_at": MongoSerializer.now_utc(),
                }
            },
        )

        # Create transaction record
        transaction = {
            "user_id": user_id,
            "user_type": user_type,
            "type": "debit",
            "amount": amount,
            "description": f"Admin deduction: {reason}",
            "balance_before": current_balance,
            "balance_after": new_balance,
            "admin_id": admin_id,
            "status": "completed",
            "reference": f"ADMIN-DEBIT-{secrets.token_hex(8).upper()}",
            "created_at": MongoSerializer.now_utc(),
        }

        await transactions_collection.insert_one(transaction)

        # Notify user
        await notifications_collection.insert_one(
            {
                "user_id": user_id,
                "user_type": user_type,
                "title": "Tokens Deducted",
                "message": (
                    f"{amount} tokens have been deducted from your account.\n"
                    f"Reason: {reason}"
                ),
                "type": "token_debit",
                "read": False,
                "created_at": MongoSerializer.now_utc(),
            }
        )

        logger.info(
            f"Admin {admin_id} deducted {amount} tokens from "
            f"{user_type}:{user_id}. New balance: {new_balance}"
        )

        return {
            "success": True,
            "user_id": user_id,
            "user_type": user_type,
            "previous_balance": current_balance,
            "new_balance": new_balance,
            "amount_deducted": amount,
            "transaction_reference": transaction["reference"],
        }

    except Exception as e:
        logger.error(
            f"Error deducting tokens from {user_type}:{user_id}: {e}"
        )
        raise

# ============================================================
# AI HELPER
# ============================================================

async def enhance_bio_with_ai(bio_text: str, achievements: str = None) -> dict:
    try:
        if not openai_client:
            return {"bio": bio_text, "achievements": achievements}
        prompt = (
            f"Please enhance the following player biography and achievements to make them more "
            f"professional and engaging while maintaining factual accuracy:\n"
            f"Biography: {bio_text}\n"
            f"Achievements: {achievements or 'No achievements listed'}\n"
            f"Please return a JSON response with 'bio' and 'achievements' fields."
        )
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional sports biography writer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        enhanced_content = response.choices[0].message.content
        try:
            enhanced_data = json.loads(enhanced_content)
            return {
                "bio": enhanced_data.get("bio", bio_text),
                "achievements": enhanced_data.get("achievements", achievements),
            }
        except Exception:
            return {"bio": bio_text, "achievements": achievements}
    except Exception as e:
        logger.error(f"OpenAI enhancement error: {e}")
        return {"bio": bio_text, "achievements": achievements}

# ============================================================
# AUTH HELPERS — one guard per role, all roles covered
# ============================================================

async def get_current_user(request: Request) -> dict:
    """Resolve the authenticated user through the canonical role registry."""
    token = request.cookies.get("auth_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    role = normalize_role(payload.get("role"))
    user_ref = payload.get("sub")
    canonical_id = payload.get("user_id") or payload.get("unique_id")
    if not user_ref and not canonical_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    col = role_collection(role)
    user = None
    if user_ref and len(str(user_ref)) == 24:
        try:
            user = await col.find_one({"_id": ObjectId(str(user_ref))})
        except Exception:
            user = None
    if not user and canonical_id:
        _, id_field = ROLE_COLLECTION_MAP[role]
        user = await col.find_one({id_field: canonical_id})
        if not user:
            user = await col.find_one({"user_id": canonical_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")

    normalized = MongoSerializer.serialize_document(user)
    normalized.setdefault("role", role)
    normalized.setdefault("user_type", role)
    normalized.setdefault("user_id", normalized.get(ROLE_COLLECTION_MAP[role][1]))
    normalized.setdefault("unique_id", normalized.get(ROLE_COLLECTION_MAP[role][1]))
    normalized["role"] = role
    normalized["user_type"] = role
    return normalized


async def get_optional_current_user(request: Request) -> Optional[dict]:
    """Return the authenticated user or ``None`` — never raises 401.

    Use in page routes that redirect authenticated users but should still
    render for unauthenticated visitors.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def get_admin_user(request: Request) -> dict:
    """Require role == 'admin'."""
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_player_user(request: Request) -> dict:
    """Require role == 'player'."""
    user = await get_current_user(request)
    if user.get("role") != "player":
        raise HTTPException(status_code=403, detail="Player access required")
    return user


async def get_club_user(request: Request) -> dict:
    """Require role == 'club'."""
    user = await get_current_user(request)
    if user.get("role") != "club":
        raise HTTPException(status_code=403, detail="Club access required")
    return user


async def get_scout_user(request: Request) -> dict:
    """Require role == 'scout'."""
    user = await get_current_user(request)
    if user.get("role") != "scout":
        raise HTTPException(status_code=403, detail="Scout access required")
    return user


async def get_agent_user(request: Request) -> dict:
    """Require role == 'agent'."""
    user = await get_current_user(request)
    if user.get("role") != "agent":
        raise HTTPException(status_code=403, detail="Agent access required")
    return user


async def get_dco_user(request: Request) -> dict:
    """Require role == 'dco'."""
    user = await get_current_user(request)
    if user.get("role") != "dco":
        raise HTTPException(status_code=403, detail="dco access required")
    return user


async def get_supervisor_user(request: Request) -> dict:
    """Require role == 'supervisor'."""
    user = await get_current_user(request)
    if user.get("role") != "supervisor":
        raise HTTPException(status_code=403, detail="Supervisor access required")
    return user


async def get_co_user(request: Request) -> dict:
    """Require role == 'communication_officer'."""
    user = await get_current_user(request)
    if user.get("role") != "communication_officer":
        raise HTTPException(status_code=403, detail="Communications Officer access required")
    return user


async def get_cc_user(request: Request) -> dict:
    """Require role in ('customer_care', 'cc', 'cc_agent')."""
    user = await get_current_user(request)
    if user.get("role") not in ("customer_care", "cc", "cc_agent"):
        raise HTTPException(status_code=403, detail="Customer Care access required")
    return user


async def get_content_manager_user(request: Request) -> dict:
    """Require the canonical Content Manager role."""
    user = await get_current_user(request)
    if user.get("role") != "content_manager":
        raise HTTPException(status_code=403, detail="Content Manager access required")
    return user


async def get_sub_admin_user(request: Request) -> dict:
    """Require the canonical Sub-Admin role."""
    user = await get_current_user(request)
    if user.get("role") != "sub_admin":
        raise HTTPException(status_code=403, detail="Sub-Admin access required")
    return user


def require_permission(permission: str):
    """Return a FastAPI dependency enforcing the central permission matrix."""
    async def _dependency(request: Request) -> dict:
        user = await get_current_user(request)
        if not role_has_permission(user.get("role", ""), permission):
            raise HTTPException(status_code=403, detail=f"Permission required: {permission}")
        return user
    return _dependency

# ============================================================
# ADDITIONAL AUTH HELPERS
# ============================================================

async def find_player_by_uid(uid: str) -> Optional[dict]:
    """Look up a player document by user_id, player_id, or _id (ObjectId)."""
    player = await players_collection.find_one(
        {"$or": [{"user_id": uid}, {"player_id": uid}]}
    )
    if not player and len(uid) == 24:
        try:
            player = await players_collection.find_one({"_id": ObjectId(uid)})
        except Exception:
            pass
    return player


def _player_filter(uid: str) -> dict:
    """Return a MongoDB filter that matches a player by user_id or player_id."""
    return {"$or": [{"user_id": uid}, {"player_id": uid}]}


async def get_player_position(player_id: str, payload: dict = None) -> str:
    try:
        if payload and payload.get("position"):
            return payload["position"]
        if not player_id or len(player_id) != 24:
            return "Unknown"
        try:
            ObjectId(player_id)
        except Exception:
            return "Unknown"
        player = await players_collection.find_one({"_id": ObjectId(player_id)})
        if player:
            pos = player.get("preferredPosition") or player.get("preferred_position") or player.get("position")
            if pos:
                return pos
        return "Unknown"
    except Exception as e:
        logger.error(f"Error fetching player position: {e}")
        return "Unknown"

# ============================================================
# STAFF USER HELPER (CO / CC — collection-aware lookup)
# ============================================================

async def _get_staff_user(request: Request, required_role: str) -> dict:
    """Backward-compatible staff dependency backed by the canonical auth resolver."""
    required_role = normalize_role(required_role)
    user = await get_current_user(request)
    if user.get("role") not in {required_role, "admin"}:
        raise HTTPException(
            status_code=403,
            detail=f"{ROLE_LABELS.get(required_role, required_role)} access required",
        )
    return user


# ============================================================
# CO ACTIVITY LOGGER (fire-and-forget)
# ============================================================

def _log_co_activity(actor_id: str, activity_type: str, description: str) -> None:
    """Schedule a non-blocking Communications Officer activity record insert."""
    async def _inner() -> None:
        try:
            await activity_history_collection.insert_one({
                "actor_id":    actor_id,
                "actor_role":  "communication_officer",
                "type":        activity_type,
                "description": description,
                "created_at":  MongoSerializer.now_utc(),
            })
        except Exception as exc:
            logger.warning(f"CO activity log error: {exc}")

    asyncio.ensure_future(_inner())

# ============================================================
# CANONICAL USER CREATION SERVICE
# ============================================================

async def create_platform_user(
    *,
    role: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    middle_name: str = "",
    player_level: str = "",
    user_id: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
    create_general_account: bool = True,
) -> Dict[str, Any]:
    """Create a platform identity using the canonical role/ID contract.

    All public registration, administrative creation, staff onboarding and seed
    code should converge on this service. It intentionally generates the public
    role ID before insertion and uses the atomic counters collection.
    """
    canonical_role = normalize_role(role)
    normalized_email = normalize_email(email)
    if not normalized_email:
        raise ValueError("Email is required")
    if not password:
        raise ValueError("Password is required")

    collection = role_collection(canonical_role)
    _, id_field = ROLE_COLLECTION_MAP[canonical_role]
    existing = await collection.find_one({"email": normalized_email})
    if existing:
        raise ValueError("A user with this email already exists")
    if create_general_account:
        existing_general = await users_collection.find_one({"email": normalized_email})
        if existing_general:
            raise ValueError("A user with this email already exists")

    canonical_id = user_id or await generate_user_id(canonical_role, player_level)
    now = MongoSerializer.now_utc()
    document: Dict[str, Any] = {
        "user_id": canonical_id,
        id_field: canonical_id,
        "unique_id": canonical_id,
        "role": canonical_role,
        "user_type": canonical_role,
        "email": normalized_email,
        "password_hash": hash_password(password),
        "firstName": (first_name or "").strip(),
        "middleName": (middle_name or "").strip(),
        "lastName": (last_name or "").strip(),
        "is_active": True,
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    if extra_fields:
        for key, value in extra_fields.items():
            if key not in {"_id", "password", "password_hash", "role", "user_type", id_field, "user_id", "unique_id"}:
                document[key] = value

    result = await collection.insert_one(document)
    document["_id"] = result.inserted_id

    if create_general_account:
        try:
            await users_collection.insert_one({
                "user_id": canonical_id,
                "unique_id": canonical_id,
                "role": canonical_role,
                "user_type": canonical_role,
                "email": normalized_email,
                "is_active": True,
                "email_verified": False,
                "role_collection": ROLE_REGISTRY[canonical_role]["collection_name"],
                "role_id_field": id_field,
                "created_at": now,
                "updated_at": now,
            })
        except Exception:
            # Do not leave a role document without its corresponding general account.
            await collection.delete_one({"_id": result.inserted_id})
            raise

    return MongoSerializer.serialize_document(document)


# ============================================================
# START: DATABASE INITIALIZATION / INDEXES
# ============================================================

async def initialize_collections():
    try:
        # Identity indexes — every canonical role receives the same uniqueness contract.
        try:
            await users_collection.create_index("email", unique=True, sparse=True)
            await users_collection.create_index("user_id", unique=True, sparse=True)
        except Exception as exc:
            logger.warning("users email uniqueness index could not be created: %s", exc)
        for _role, _meta in ROLE_REGISTRY.items():
            _collection = role_collection(_role)
            for _field, _options in (("email", {"unique": True}), (_meta["id_field"], {"unique": True}), ("user_id", {"sparse": True})): 
                try:
                    await _collection.create_index(_field, **_options)
                except Exception as exc:
                    logger.warning("%s.%s index initialization skipped: %s", _role, _field, exc)
        try:
            await stats_requests_collection.create_index("reference_id", unique=True)
        except Exception:
            pass
        await stats_requests_collection.create_index("player_id")
        await stats_requests_collection.create_index("status")
        await stats_requests_collection.create_index("submitted_at")
        await stats_requests_collection.create_index("assigned_scout")
        try:
            await stats_requests_collection.create_index(
                [("player_id", 1), ("home_team", 1), ("away_team", 1), ("match_date", 1)],
                unique=True, name="unique_match_request",
            )
        except Exception:
            pass
        await player_stats_collection.create_index("player_id")
        await player_stats_collection.create_index("scout_id")
        await player_stats_collection.create_index("match_date")
        await player_stats_collection.create_index("created_at")
        await player_stats_collection.create_index("status")
        try:
            await player_stats_collection.create_index(
                [("player_id", 1), ("home_team", 1), ("away_team", 1), ("match_date", 1)],
                unique=True, name="unique_player_match_stats",
            )
        except Exception:
            pass
        await dco_assignments_collection.create_index("scout_id")
        await dco_assignments_collection.create_index("request_id")
        # Legacy indexes retained during migration so existing assignment documents remain fast.
        await dco_assignments_collection.create_index("scoutId")
        await dco_assignments_collection.create_index("requestId")
        await dco_assignments_collection.create_index("status")
        try:
            await dco_assignments_collection.create_index("assignment_id", unique=True)
        except Exception:
            pass
        try:
            await payment_intents_collection.create_index("tx_ref", unique=True)
        except Exception:
            pass
        await payment_intents_collection.create_index("player_id")
        await payment_intents_collection.create_index("status")
        await payment_intents_collection.create_index("expires_at", expireAfterSeconds=0)
        try:
            await player_tokens_collection.create_index("player_id", unique=True)
            await club_tokens_collection.create_index("club_id", unique=True)
            await scout_tokens_collection.create_index("scout_id", unique=True)
            await dco_tokens_collection.create_index("dco_id", unique=True)
            await agent_tokens_collection.create_index("agent_id", unique=True)
        except Exception:
            pass
        await activity_history_collection.create_index("player_id")
        await activity_history_collection.create_index("timestamp")
        await activity_history_collection.create_index("scout_id")
        await activity_history_collection.create_index("type")
        await messages_collection.create_index("senderId")
        await messages_collection.create_index("recipientId")
        await messages_collection.create_index("timestamp")
        await notifications_collection.create_index("recipientId")
        await notifications_collection.create_index("timestamp")
        try:
            await newsletter_subscribers_collection.create_index("email", unique=True)
        except Exception:
            pass
        await contact_messages_collection.create_index("timestamp")
        try:
            await leaderboard_collection.create_index(
                [("player_id", 1), ("period_type", 1), ("period", 1)],
                unique=True, name="player_period_unique",
            )
        except Exception:
            pass
        await leaderboard_collection.create_index(
            [("period_type", 1), ("period", 1), ("score", -1)], name="period_score_index"
        )
        await leaderboard_collection.create_index([("updated_at", -1)], name="updated_at_index")
        try:
            await liveness_sessions_collection.create_index("session_id", unique=True)
        except Exception:
            pass
        await liveness_sessions_collection.create_index(
            "created_at", expireAfterSeconds=600, name="liveness_ttl_index"
        )
        logger.info("Collections and indexes initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing collections: {e}")

# ============================================================
# END: DATABASE INITIALIZATION / INDEXES
# ============================================================

# ============================================================
# TEST DATA SEED
# ============================================================


# ============================================================

# FASTAPI APP INITIALIZATION

# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Enejistats API...")
    logger.info(f"  - MongoDB:      {'OK' if MONGO_URI else 'NOT SET'}")
    logger.info(f"  - Cloudinary:   {'OK' if cloudinary_url else 'NOT SET'}")
    logger.info(f"  - OpenAI:       {'OK' if openai_api_key else 'NOT SET'}")
    logger.info(f"  - Flutterwave:  {'OK' if FLUTTERWAVE_SECRET_KEY else 'NOT SET'}")
    logger.info(f"  - Brevo API:    {'OK' if BREVO_API_KEY else 'NOT SET'}")
    logger.info(f"  - Email Sender: {FROM_EMAIL}")
    logger.info(f"  - Sender Name:  {FROM_NAME}")

    if not cloudinary_url:
        logger.warning("CLOUDINARY_URL not set — image uploads will fail")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not set — AI features will be disabled")

    async def _safe_startup():
        try:
            await asyncio.wait_for(initialize_collections(), timeout=15)
            await asyncio.wait_for(_run_seed(globals()), timeout=60)
            logger.info("DB initialization and seed complete")
        except asyncio.TimeoutError:
            logger.warning(
                "DB startup timed out — app running without DB init (set MONGO_URI)"
            )
        except Exception as e:
            logger.warning(f"DB startup error — app will start anyway: {e}")

    asyncio.create_task(_safe_startup())

    if MONITORING_URLS:
        asyncio.create_task(auto_ping_task())

    logger.info("Application startup complete")
    yield
    logger.info("Shutting down Enejistats API...")
    
app = FastAPI(
    title="Enejistats API",
    version="1.0.0",
    lifespan=lifespan,
)

# Production-safe CORS: explicit origins are configured through CORS_ORIGINS.
# Comma-separated values are accepted; development can override with localhost origins.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "https://enejistats.onrender.com,http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# PATH CONFIGURATION
# ============================================================

_APP_DIR = Path(__file__).resolve().parent
_BASE_DIR = _APP_DIR.parent
_TEMPLATES_DIR = (_BASE_DIR / "templates").resolve()
_STATIC_DIR = (_BASE_DIR / "static").resolve()
_DCO_DASHBOARD_STATIC_DIR = (_STATIC_DIR / "dco-dashboard").resolve()

logger.info(f"APP DIR:       {_APP_DIR}")
logger.info(f"BASE DIR:      {_BASE_DIR}")
logger.info(f"TEMPLATES DIR: {_TEMPLATES_DIR}")
logger.info(f"STATIC DIR:    {_STATIC_DIR}")

try:
    _STATIC_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Static directory ready")
except Exception as e:
    logger.error(f"Failed to create static directory: {e}")

# ============================================================
# STATIC FILES
# ============================================================

# The single /static mount below serves the DCO dashboard's nested
# tabs, shared scripts, and styles at /static/dco-dashboard/ as well.
# Keep this on the existing mount to avoid duplicate static routes.
app.mount(
    "/static",
    StaticFiles(directory=str(_STATIC_DIR)),
    name="static",
)

logger.info(f"Static files mounted at '/static' -> {_STATIC_DIR}")
if _DCO_DASHBOARD_STATIC_DIR.is_dir():
    logger.info(
        "DCO dashboard assets served at '/static/dco-dashboard' -> %s",
        _DCO_DASHBOARD_STATIC_DIR,
    )
else:
    logger.warning(
        "DCO dashboard static directory is missing: %s",
        _DCO_DASHBOARD_STATIC_DIR,
    )

# ============================================================
# HTML SERVE HELPER
# ============================================================

def serve_html(template_name: str) -> HTMLResponse:
    html_file = _TEMPLATES_DIR / template_name
    logger.info(f"Looking for template: {html_file}")

    if html_file.exists():
        try:
            return HTMLResponse(
                html_file.read_text(encoding="utf-8")
            )
        except Exception as e:
            logger.error(f"Error reading template {template_name}: {e}")
            return HTMLResponse(
                f"<h1>Error Loading Template</h1>"
                f"<p>{template_name}</p>"
                f"<pre>{str(e)}</pre>",
                status_code=500,
            )

    logger.error(f"Template not found: {html_file}")

    available_files = []
    try:
        available_files = [f.name for f in _TEMPLATES_DIR.glob("*")]
    except Exception:
        pass

    return HTMLResponse(
        f"<h1>{template_name}</h1>"
        f"<p>Page not found.</p>"
        f"<hr><h3>Debug</h3>"
        f"<p><strong>Expected:</strong></p><pre>{html_file}</pre>"
        f"<p><strong>Available:</strong></p><pre>{available_files}</pre>",
        status_code=404,
    )

# ============================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        if room not in self.active_connections:
            self.active_connections[room] = []
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            try:
                self.active_connections[room].remove(websocket)
            except ValueError:
                pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception:
            pass

    async def broadcast(self, message: str, room: str):
        if room in self.active_connections:
            dead = []
            for ws in self.active_connections[room]:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, room)


ws_manager = ConnectionManager()

# ============================================================
# WEBSOCKET ENDPOINT — real-time notifications for all roles
# ============================================================

@app.websocket("/ws/member/{user_id}")
async def websocket_member(websocket: WebSocket, user_id: str, token: str = ""):
    """Real-time notification channel.
    Accepts any authenticated user (player, club, scout, agent, dco, supervisor, co, cc).
    Rejects with code 4001/4003 if token is missing or invalid.
    """
    if not token:
        await websocket.close(code=4001, reason="Authentication token required")
        return
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    room = f"user:{user_id}"
    await ws_manager.connect(websocket, room)
    logger.info(f"WebSocket connected: user={user_id} role={payload.get('role','?')}")
    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Connected to Enejistats real-time",
        })
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    try:
                        msg = json.loads(data)
                        await websocket.send_json({"type": "ack", "received": msg.get("type", "unknown")})
                    except Exception:
                        pass
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}")
    except Exception as e:
        logger.warning(f"WebSocket error for user={user_id}: {e}")
    finally:
        ws_manager.disconnect(websocket, room)

# ============================================================
# SERVICE WORKER
# ============================================================

@app.get("/sw.js")
async def serve_service_worker(response: Response):
    """Serve the service worker with correct headers so it can control the full origin."""
    sw_path = _STATIC_DIR / "sw.js"
    if sw_path.exists():
        content = sw_path.read_text(encoding="utf-8")
    else:
        content = """
const CACHE = 'enejistats-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (
    e.request.method !== 'GET' ||
    u.pathname.startsWith('/api/') ||
    u.pathname.startsWith('/ws/')
  ) return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r && r.ok) {
          const c = r.clone();
          caches.open(CACHE).then(cache => cache.put(e.request, c));
        }
        return r;
      })
      .catch(() => caches.match(e.request))
  );
});
"""
    return Response(
        content=content,
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )

# ============================================================
# HEALTH & PING
# ============================================================

@app.get("/health")
async def health_check():
    try:
        await database.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    return MongoJSONResponse({
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "timestamp": MongoSerializer.now_utc().isoformat(),
        "environment": {
            "mongo_uri_set":    bool(os.getenv("MONGO_URI")),
            "secret_key_set":   bool(os.getenv("SECRET_KEY") and os.getenv("SECRET_KEY") != "enejistats-secret-key-change-in-production"),
            "cloudinary_set":   bool(cloudinary_url),
            "openai_set":       bool(openai_api_key),
            "flutterwave_set":  bool(FLUTTERWAVE_PUBLIC_KEY),
            "brevo_set":        bool(BREVO_API_KEY),
        },
    })


@app.get("/ping")
async def ping(request: Request, platform: str = None):
    global last_ping_time
    now = MongoSerializer.now_utc()
    last_ping_time = now
    msg = "Enejistats backend alive"
    if platform:
        msg += f" (pinged by {platform})"
    logger.info(f"Ping received from {platform or 'unknown'} at {now.isoformat()} UTC")
    return JSONResponse({"status": msg, "timestamp": now.isoformat() + "Z", "message": "Ping received successfully"})


@app.get("/ping-status")
async def ping_status():
    if last_ping_time:
        return JSONResponse({"status": "alive", "last_ping": last_ping_time.isoformat() + "Z"})
    return JSONResponse({"status": "no pings yet"})

# ============================================================
# CONFIG ENDPOINTS — served to the registration form
# (POSITIONS_CONFIG and PLAYER_LEVELS_CONFIG defined above in pricing section)
# ============================================================

@app.get("/api/config/positions")
async def get_positions_config():
    """Return position categories and their sub-positions."""
    return JSONResponse({"positions": POSITIONS_CONFIG})


@app.get("/api/config/player-levels")
async def get_player_levels_config():
    """Return valid player level options."""
    return JSONResponse(PLAYER_LEVELS_CONFIG)

# ============================================================
# PUBLIC DATA ENDPOINTS — no auth required
# (COUNTRIES_CONFIG defined above in pricing section)
# ============================================================


# NOTE: /api/public/countries route moved to location_module.py
#       (registered automatically via register_location_routes(app) below)


@app.get("/api/public/clubs")
async def get_clubs_public(q: str = "", level: str = "", limit: int = 20):
    """Search registered clubs for the player registration club-search widget."""
    try:
        if not q or len(q.strip()) < 2:
            return JSONResponse({"clubs": []})
        query_str = q.strip()
        search_patterns = []
        if query_str.upper().startswith("CL-"):
            search_patterns.append({"club_id": query_str.upper()})
        else:
            search_patterns.extend([
                {"club_name":     {"$regex": query_str, "$options": "i"}},
                {"club_nickname": {"$regex": query_str, "$options": "i"}},
                {"address":       {"$regex": query_str, "$options": "i"}},
                {"country":       {"$regex": query_str, "$options": "i"}},
            ])
        mongo_query: Dict[str, Any] = {"$or": search_patterns}
        if level:
            mongo_query["category"] = {"$regex": level, "$options": "i"}
        clubs = await clubs_collection.find(mongo_query).limit(max(1, min(limit, 50))).to_list(length=50)
        results = [
            {
                "id":        str(c.get("_id", "")),
                "club_id":   c.get("club_id", ""),
                "name":      c.get("club_name", ""),
                "club_name": c.get("club_name", ""),
                "level":     c.get("category", ""),
                "country":   c.get("country", ""),
            }
            for c in clubs
        ]
        return JSONResponse({"clubs": results})
    except Exception as e:
        logger.error(f"Error searching clubs: {e}")
        return JSONResponse({"clubs": [], "error": str(e)})




# NOTE: /api/public/states and /api/public/lgas routes moved to location_module.py
#       (registered automatically via register_location_routes(app) below)


@app.get("/api/public/terms")
async def get_terms():
    """Return Terms of Service content for the registration overlay."""
    year = MongoSerializer.now_utc().year
    content = f"""
<h4>1. Terms of Service</h4>
<p>By registering on Enejistats you agree to use the platform solely for lawful football-related purposes.
You must provide accurate information and keep your credentials secure.
Misrepresentation of identity, role, or football statistics will result in immediate account suspension.</p>
<h4>2. Data Usage</h4>
<p>Your personal data is collected to power the Enejistats intelligence platform. We use your data to match
players with scouts, provide clubs with verified statistics, and facilitate legitimate agent-player
relationships across Africa. We do not sell your personal data to third parties.</p>
<h4>3. Liveness Video Policy</h4>
<p>Your liveness verification video is encrypted at rest using AES-256 and is automatically deleted after
14 days. It is processed algorithmically solely to confirm you are a real person and is never shared with
any third party.</p>
<h4>4. GPS Data</h4>
<p>GPS coordinates captured during registration are used to facilitate location-based matching. Location
data is stored securely and is only visible to authorised platform operators.</p>
<h4>5. Subscriptions &amp; Tokens</h4>
<p>Certain platform features require active subscriptions or token expenditure. Token costs are determined
by the Enejistats admin team and may change with notice. Tokens are non-refundable once consumed.</p>
<h4>6. Data Scout / DCO Programme</h4>
<p>DCOs and Supervisors are independent contractors, not employees of Enejistats. Falsified match data
will result in immediate termination and forfeiture of pending payments.</p>
<h4>7. Governing Law</h4>
<p>These Terms are governed by the laws of the Federal Republic of Nigeria. Disputes shall be resolved
through arbitration in Lagos, Nigeria.</p>
<p style="color:#475569;font-size:.78rem;margin-top:24px">Last updated: {year}. These terms supersede all previous versions.</p>
"""
    return JSONResponse({"content": content})


@app.get("/api/public/privacy")
async def get_privacy():
    """Return Privacy Policy content for the registration overlay."""
    year = MongoSerializer.now_utc().year
    content = f"""
<h4>Privacy Policy</h4>
<p>We are committed to protecting your privacy. All data transmission uses TLS 1.3 encryption.
You have the right to request access, correction, or deletion of your personal data by contacting
<a href="mailto:enejistats@gmail.com" style="color:#ffd700">enejistats@gmail.com</a>. We comply with
the Nigeria Data Protection Regulation (NDPR) and applicable international data protection laws.</p>
<h4>Data We Collect</h4>
<p>Your personal data is collected to power the Enejistats intelligence platform. We use your data to
match players with scouts, provide clubs with verified statistics, and facilitate legitimate agent-player
relationships across Africa. We do not sell your personal data to third parties.</p>
<h4>GPS &amp; Location Data</h4>
<p>GPS coordinates captured during registration are used to facilitate location-based matching. Location
data is stored securely and is only visible to authorised platform operators.</p>
<h4>Liveness Video Policy</h4>
<p>Your liveness verification video is encrypted at rest using AES-256 and is automatically deleted after
14 days. It is processed algorithmically solely to confirm you are a real person and is never shared with
any third party.</p>
<h4>Cookies</h4>
<p>We use essential cookies for session management and authentication. We do not use tracking or
advertising cookies without your consent.</p>
<p style="color:#475569;font-size:.78rem;margin-top:24px">Last updated: {year}. This policy supersedes all previous versions.</p>
"""
    return JSONResponse({"content": content})

# ============================================================
# HTML PAGE ROUTES
# ============================================================

@app.head("/")
async def home_head():
    """Accept HEAD / from uptime monitors."""
    return Response(status_code=200)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        user = await get_optional_current_user(request)

        if user:
            role = user.get("role", "")
            target = {
                "admin": "/admin-dashboard",
                "player": "/player-dashboard",
                "club": "/club-dashboard",
                "agent": "/agent-dashboard",
                "scout": "/scout-dashboard",
                "dco": "/dco-dashboard",
                "supervisor": "/supervisor-dashboard",
                "communication_officer": "/co-dashboard",
                "co": "/co-dashboard",
                "customer_care": "/cc-dashboard",
                "cc": "/cc-dashboard",
                "cc_agent": "/cc-dashboard",
            }.get(role)

            if target:
                return RedirectResponse(url=target)

        return serve_html("index.html")

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


# ------------------------------------------------------------
# PUBLIC / GENERAL HTML PAGES
# ------------------------------------------------------------

@app.get("/about", response_class=HTMLResponse)
@app.get("/about.html", response_class=HTMLResponse)
async def about_page(request: Request):
    return serve_html("about.html")


@app.get("/browse", response_class=HTMLResponse)
@app.get("/browse.html", response_class=HTMLResponse)
async def browse_page(request: Request):
    return serve_html("browse.html")


@app.get("/leaderboard", response_class=HTMLResponse)
@app.get("/leaderboard.html", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return serve_html("leaderboard.html")


@app.get("/contact", response_class=HTMLResponse)
@app.get("/contact.html", response_class=HTMLResponse)
async def contact_page(request: Request):
    return serve_html("contact.html")


@app.get("/pricing", response_class=HTMLResponse)
@app.get("/pricing.html", response_class=HTMLResponse)
async def pricing_page(request: Request):
    return serve_html("pricing.html")


@app.get("/player", response_class=HTMLResponse)
@app.get("/player.html", response_class=HTMLResponse)
async def player_page(request: Request):
    return serve_html("player.html")


@app.get("/club-profile", response_class=HTMLResponse)
@app.get("/club-profile.html", response_class=HTMLResponse)
async def club_profile_page(request: Request):
    return serve_html("club-profile.html")


@app.get("/terms", response_class=HTMLResponse)
@app.get("/terms.html", response_class=HTMLResponse)
async def terms_page(request: Request):
    return serve_html("terms.html")


@app.get("/privacy", response_class=HTMLResponse)
@app.get("/privacy.html", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return serve_html("privacy.html")


@app.get("/terms-privacy", response_class=HTMLResponse)
@app.get("/terms-privacy.html", response_class=HTMLResponse)
async def terms_privacy_page():
    return serve_html("terms-privacy.html")


@app.get("/privacy-terms", response_class=HTMLResponse)
@app.get("/privacy-terms.html", response_class=HTMLResponse)
async def privacy_terms_page():
    return serve_html("privacy-terms.html")


@app.get("/venues-subtab", response_class=HTMLResponse)
@app.get("/venues-subtab.html", response_class=HTMLResponse)
async def venues_subtab_page():
    return serve_html("venues-subtab.html")


@app.get("/cookies", response_class=HTMLResponse)
@app.get("/cookies.html", response_class=HTMLResponse)
async def cookies_page(request: Request):
    return serve_html("cookies.html")


@app.get("/competitions", response_class=HTMLResponse)
@app.get("/competitions.html", response_class=HTMLResponse)
async def competitions_page(request: Request):
    return serve_html("competitions.html")


# ------------------------------------------------------------
# PLAYER PROFILE
# ------------------------------------------------------------

@app.get("/player-profile", response_class=HTMLResponse)
@app.get("/player-profile.html", response_class=HTMLResponse)
async def player_profile_page(
    request: Request,
    id: str | None = None,
):
    """
    Serve the normal player profile page.

    When a player ID is supplied, preserve the existing SEO/legacy
    profile handling through _seo.legacy_player_profile().
    """
    if id:
        return await _seo.legacy_player_profile(request)

    return serve_html("player-profile.html")


# ------------------------------------------------------------
# AUTHENTICATION / ACCOUNT PAGES
# ------------------------------------------------------------

@app.get("/register", response_class=HTMLResponse)
@app.get("/register.html", response_class=HTMLResponse)
async def register_page(request: Request):
    try:
        user = await get_optional_current_user(request)

        if user:
            return RedirectResponse(url="/")

        return serve_html("register.html")

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@app.get("/login", response_class=HTMLResponse)
@app.get("/login.html", response_class=HTMLResponse)
async def login_page(request: Request):
    try:
        user = await get_optional_current_user(request)

        if user:
            return RedirectResponse(url="/")

        return serve_html("login.html")

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@app.get("/auth", response_class=HTMLResponse)
@app.get("/auth.html", response_class=HTMLResponse)
async def auth_page(request: Request):
    return serve_html("auth.html")


# ------------------------------------------------------------
# SEARCH / STATISTICS PAGES
# ------------------------------------------------------------

@app.get("/search", response_class=HTMLResponse)
@app.get("/search.html", response_class=HTMLResponse)
async def search_page(request: Request):
    return serve_html("search.html")


@app.get("/stats-area", response_class=HTMLResponse)
@app.get("/stats-area.html", response_class=HTMLResponse)
async def stats_area_page(request: Request):
    return serve_html("stats_area.html")


# /stats/browse is retained as an existing alias.
@app.get("/stats/browse", response_class=HTMLResponse)
@app.get("/player-stats", response_class=HTMLResponse)
@app.get("/player-stats.html", response_class=HTMLResponse)
async def player_stats_page(request: Request):
    return serve_html("player-stats.html")


@app.get("/stats-tracker", response_class=HTMLResponse)
@app.get("/stats-tracker.html", response_class=HTMLResponse)
async def stats_tracker_page():
    return serve_html("stats-tracker.html")


@app.get("/stats-tab", response_class=HTMLResponse)
@app.get("/stats-tab.html", response_class=HTMLResponse)
async def stats_tab_page(request: Request):
    return serve_html("stats-tab.html")


# ------------------------------------------------------------
# ACCOUNT / OPERATIONS PAGES
# ------------------------------------------------------------

@app.get("/register-subtab", response_class=HTMLResponse)
@app.get("/register-subtab.html", response_class=HTMLResponse)
async def register_subtab_page():
    return serve_html("register-subtab.html")

@app.get("/dco-finance-activity", response_class=HTMLResponse)
@app.get("/dco-finance-activity.html", response_class=HTMLResponse)
async def dco_finance_activity_page():
    return serve_html("dco-finance-activity.html")


@app.get("/payment-center", response_class=HTMLResponse)
@app.get("/payment-center.html", response_class=HTMLResponse)
async def payment_center_page():
    return serve_html("payment-center.html")


@app.get("/payouts", response_class=HTMLResponse)
@app.get("/payouts.html", response_class=HTMLResponse)
async def payouts_page():
    return serve_html("payouts.html")


@app.get("/stats-requests", response_class=HTMLResponse)
@app.get("/stats-requests.html", response_class=HTMLResponse)
async def stats_requests_page():
    return serve_html("stats-requests.html")


@app.get("/scout-assignments", response_class=HTMLResponse)
@app.get("/scout-assignments.html", response_class=HTMLResponse)
async def scout_assignments_page():
    return serve_html("scout-assignments.html")


@app.get("/background-checks", response_class=HTMLResponse)
@app.get("/background-checks.html", response_class=HTMLResponse)
async def background_checks_page():
    return serve_html("background-checks.html")


@app.get("/bank-accounts", response_class=HTMLResponse)
@app.get("/bank-accounts.html", response_class=HTMLResponse)
async def bank_accounts_page():
    return serve_html("bank-accounts.html")


@app.get("/match-centre", response_class=HTMLResponse)
@app.get("/match-centre.html", response_class=HTMLResponse)
async def match_centre_page(request: Request):
    return serve_html("match-centre.html")


# ------------------------------------------------------------
# CLUB DASHBOARD SUPPORT / SUB-PAGES
# ------------------------------------------------------------

@app.get("/club-dashboard-host", response_class=HTMLResponse)
@app.get("/club-dashboard-host.html", response_class=HTMLResponse)
async def club_dashboard_host_page():
    return serve_html("club-dashboard-host.html")


@app.get("/club-dashboard-stats", response_class=HTMLResponse)
@app.get("/club-dashboard-stats.html", response_class=HTMLResponse)
async def club_dashboard_stats_page():
    return serve_html("club-dashboard-stats.html")


@app.get("/club-dashboard-squad", response_class=HTMLResponse)
@app.get("/club-dashboard-squad.html", response_class=HTMLResponse)
async def club_dashboard_squad_page():
    return serve_html("club-dashboard-squad.html")


@app.get("/club-dashboard-operations", response_class=HTMLResponse)
@app.get("/club-dashboard-operations.html", response_class=HTMLResponse)
async def club_dashboard_operations_page():
    return serve_html("club-dashboard-operations.html")


# ============================================================
# DASHBOARD ROUTES
# ============================================================

@app.get("/admin-dashboard", response_class=HTMLResponse)
@app.get("/admin-dashboard.html", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return serve_html("admin-dashboard.html")


@app.get("/admin-dashboard2", response_class=HTMLResponse)
@app.get("/admin-dashboard2.html", response_class=HTMLResponse)
async def admin_dashboard2(request: Request):
    return serve_html("admin-dashboard2.html")


@app.get("/player-dashboard", response_class=HTMLResponse)
@app.get("/player-dashboard.html", response_class=HTMLResponse)
async def player_dashboard(request: Request, id: str | None = None):
    return serve_html("player-dashboard.html")


@app.get("/club-dashboard", response_class=HTMLResponse)
@app.get("/club-dashboard.html", response_class=HTMLResponse)
async def club_dashboard(request: Request):
    return serve_html("club-dashboard.html")


@app.get("/agent-dashboard", response_class=HTMLResponse)
@app.get("/agent-dashboard.html", response_class=HTMLResponse)
async def agent_dashboard(request: Request):
    return serve_html("agent-dashboard.html")


@app.get("/scout-dashboard", response_class=HTMLResponse)
@app.get("/scout-dashboard.html", response_class=HTMLResponse)
async def scout_dashboard(request: Request):
    return serve_html("scout-dashboard.html")


@app.get("/dco-dashboard", response_class=HTMLResponse)
@app.get("/dco-dashboard.html", response_class=HTMLResponse)
async def dco_dashboard(request: Request):
    return serve_html("dco-dashboard.html")


@app.get("/supervisor-dashboard", response_class=HTMLResponse)
@app.get("/supervisor-dashboard.html", response_class=HTMLResponse)
async def supervisor_dashboard(request: Request):
    return serve_html("supervisor-dashboard.html")


# ------------------------------------------------------------
# COMMUNICATION OFFICER DASHBOARD
# ------------------------------------------------------------
# All existing CO aliases intentionally resolve to one canonical
# template: co-dashboard.html.

@app.get("/co-dashboard", response_class=HTMLResponse)
@app.get("/co-dashboard.html", response_class=HTMLResponse)
@app.get("/communication-dashboard", response_class=HTMLResponse)
@app.get("/communications-officer-dashboard", response_class=HTMLResponse)
@app.get("/communications-officer-dashboard.html", response_class=HTMLResponse)
async def co_dashboard(request: Request):
    return serve_html("co-dashboard.html")


# ------------------------------------------------------------
# CUSTOMER CARE DASHBOARD
# ------------------------------------------------------------
# All existing CC aliases intentionally resolve to one canonical
# template: cc-dashboard.html.

@app.get("/cc-dashboard", response_class=HTMLResponse)
@app.get("/cc-dashboard.html", response_class=HTMLResponse)
@app.get("/customer-care-dashboard", response_class=HTMLResponse)
@app.get("/customer-care-dashboard.html", response_class=HTMLResponse)
async def cc_dashboard(request: Request):
    return serve_html("cc-dashboard.html")


# ============================================================
# START: API ROUTER MOUNTS
# Keep API/application router mounting separate from HTML page routes.
# ============================================================


# ============================================================
# ENEJISTATS ADMIN DASHBOARD — PREACT UMD STATIC TAB FILES
# ============================================================
#
# The parent template:
#     backend/templates/admin-dashboard.html
#
# loads these standalone tab documents from:
#     /static/admin-dashboard/tabs/
#
# This section intentionally remains independent of the normal
# HTML page routes above.
# ============================================================

from pathlib import Path as _AdminDashboardPath
from fastapi.responses import FileResponse as _AdminDashboardFileResponse


_ADMIN_DASHBOARD_TABS_DIR = (
    _AdminDashboardPath(__file__).resolve().parents[1]
    / "static"
    / "admin-dashboard"
    / "tabs"
)


_ADMIN_DASHBOARD_TAB_FILES = frozenset(
    {
        "dashboard.html",
        "users.html",
        "sub-admins.html",
        "subscriptions.html",
        "trials.html",
        "receipts.html",
        "tokens.html",
        "dco-tiers.html",
        "broadcasts.html",
        "support.html",
        "settings.html",
        "operations.html",
        "payments.html",
        "payouts.html",
        "match-centre.html",
        "assignments.html",
        "background-checks.html",
        "bank-accounts.html",
    }
)


@app.get(
    "/static/admin-dashboard/tabs/{tab_name}.html",
    include_in_schema=False,
)
async def serve_admin_dashboard_preact_tab(tab_name: str):
    """
    Serve one allow-listed external Preact UMD dashboard tab.

    Only explicitly registered tab filenames are accessible.
    """
    filename = f"{tab_name}.html"

    if filename not in _ADMIN_DASHBOARD_TAB_FILES:
        raise HTTPException(
            status_code=404,
            detail="Dashboard tab not found",
        )

    tab_path = _ADMIN_DASHBOARD_TABS_DIR / filename

    if not tab_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Dashboard tab file missing",
        )

    return _AdminDashboardFileResponse(
        path=tab_path,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
# ============================================================
# ROUTER MOUNTS — each sub-module gets a unique alias
# ============================================================

# sys.path was already patched at module load time (top of file).
# _APP_DIR is already defined — no re-insertion needed.
logger.info(f"sys.path confirmed — {str(_APP_DIR)!r} is in path")

# -- Auth routes
import auth as _auth
_auth._setup_dependencies(globals())
app.include_router(_auth.router)
logger.info("auth routes mounted — %d routes", len(_auth.router.routes))

# -- Seed runner (imported here so sys.path is already patched)
try:
    from seed.runner import run_seed as _run_seed_fn
    async def _run_seed(ctx):
        await _run_seed_fn(ctx)
except ImportError as _seed_import_err:
    logger.warning(f"seed.runner not found — using no-op seed: {_seed_import_err}")
    async def _run_seed(ctx):
        logger.warning("[seed] seed.runner unavailable — no seed data inserted")

# -- Location routes
try:
    from location_module import register_location_routes
    register_location_routes(app)
    logger.info("location_module routes registered")
except Exception as _le:
    logger.warning(f"location_module registration skipped: {_le}")

# -- Pricing module routes  (public, unauthenticated — /api/public/pricing/*)
try:
    register_pricing_routes(app)          # already imported at the top of this file
    logger.info("pricing_module routes registered")
except Exception as _pe:
    logger.warning(f"pricing_module route registration skipped: {_pe}")

# -- Visitor / public routes
import visitor_public_routes as _vpr
_vpr._setup_dependencies(globals())
app.include_router(_vpr.router)
logger.info("visitor_public_routes mounted — %d routes", len(_vpr.router.routes))

# -- Player dashboard routes
import player_dashboard_routes as _pdr
_pdr._setup_dependencies(globals())
app.include_router(_pdr.router)
logger.info("player_dashboard_routes mounted — %d routes", len(_pdr.router.routes))

from pathlib import Path
import seo_routes as _seo

_seo.setup_dependencies(
    globals(),
    profile_page_path=_TEMPLATES_DIR / "player-profile.html",
    public_site_url="https://enejistats.onrender.com",
)
app.include_router(_seo.router)

# -- Agent dashboard routes
import agent_discovery_routes as _agent_disc
_agent_disc._setup_dependencies(globals())
app.include_router(_agent_disc.router)

# ── Agent Dashboard Routes ───────────────────────────────────
import agent_dashboard_routes as _agent_dash
_agent_dash._setup_dependencies(globals())
app.include_router(_agent_dash.router)

# -- Club dashboard routes
import club_dashboard_routes as _cdr
_cdr._setup_dependencies(globals())
app.include_router(_cdr.router)
logger.info("club_dashboard_routes mounted — %d routes", len(_cdr.router.routes))


# -- Communications Officer dashboard routes
import communications_officer as _co
_co._setup_dependencies(globals())
app.include_router(_co.router)

# -- Customer Care dashboard routes
try:
    import customer_care as _cc
    _cc._setup_dependencies(globals())
    app.include_router(_cc.router)
    logger.info("customer_care routes mounted — %d routes", len(_cc.router.routes))
except ImportError as _cc_import_err:
    logger.warning("customer_care module not available — role remains supported by core auth: %s", _cc_import_err)

# -- Admin dashboard routes MAIN
import admin_dashboard_routes as _admin_dr
_admin_dr._setup_dependencies(globals())
app.include_router(_admin_dr.router)

# -- Pricing management routes
import pricing_routes as _pricing_r
_pricing_r._setup_dependencies(globals())
app.include_router(_pricing_r.router)
logger.info("pricing_routes mounted — %d routes", len(_pricing_r.router.routes))

# -- Public & Config routes  (countries, states, LGAs, clubs, positions,
#    player/club levels, payment intent, bank details, receipt upload)
import public_routes as _pub
_pub._setup_dependencies(globals())
app.include_router(_pub.router)
logger.info("public_routes mounted — %d routes", len(_pub.router.routes))

# -- DCO dashboard routes
import dco_dashboard_routes as _dco_dashboard
_dco_dashboard._setup_dependencies(globals())
app.include_router(_dco_dashboard.router)
logger.info("dco_dashboard_routes mounted — %d routes", len(_dco_dashboard.router.routes))

import stats_tracker_routes as _stats_tracker
_stats_tracker._setup_dependencies(globals())
app.include_router(_stats_tracker.router)
logger.info("stats_tracker_routes mounted — %d routes", len(_stats_tracker.router.routes))


import supervisor_dashboard_routes as _svdr
_svdr._setup_dependencies(globals())
app.include_router(_svdr.router)

# -- DCO Venue routes (optional legacy/domain module)
try:
    import dco_venue_routes as _venue_r
    _venue_r._setup_dependencies(globals())
    app.include_router(_venue_r.router)
    logger.info("dco_venue_routes mounted — %d routes", len(_venue_r.router.routes))
except ImportError as _venue_import_err:
    logger.info("dco_venue_routes not mounted; venue ownership remains in the active DCO dashboard API: %s", _venue_import_err)

# ============================================================
# END: API ROUTER MOUNTS
# ============================================================

# ============================================================
# START: APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)