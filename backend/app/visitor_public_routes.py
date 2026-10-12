"""

════════════════════════
EnejiStats – Visitor / Public-Facing API Routes
================================================
Serves every API call made by the 9 visitor-facing HTML pages:
  about, browse, club-profile, competitions, contact,
  index, leaderboard, player-profile, pricing

SYNTAX FIX (this file)
──────────────────────
Python ≤ 3.11 does not allow parentheses in a `global` statement.
The original line 101:

    global (
        players_collection, clubs_collection, ...
    )

raises:
    SyntaxError: invalid syntax

Fix: each name is declared on its own `global` line inside
_setup_dependencies().  The visitor-facing mapping layer below also
accepts the canonical snake_case fields written by auth.py and the
normalized tracker fields read by player_dashboard_routes.py.

Design contract
───────────────
• All collection handles and helper callables are module-level
  placeholders (None) filled by _setup_dependencies(main_globals)
  before the router is mounted – matching the player_dashboard_routes.py
  dependency-injection pattern exactly.
• Debug blocks are delimited by:
      # ── DEBUG BLOCK START ──────────────────────────────────────────────────
      # ── DEBUG BLOCK END ────────────────────────────────────────────────────
  Remove entire blocks to silence debug output per-endpoint.
• Zero modifications to any frontend HTML file are required.
"""

from __future__ import annotations

import logging
import html as html_lib
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import traceback
import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from bson import ObjectId
from pymongo import ReturnDocument
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

# ============================================================
# MODULE-LEVEL LOGGER
# ============================================================

logger = logging.getLogger("enejistats.public")

# ============================================================
# MODULE-LEVEL PLACEHOLDERS  (populated by _setup_dependencies)
# ============================================================

# ── MongoDB collections ───────────────────────────────────────
database                      = None
players_collection            = None
player_stats_collection       = None
stat_submissions_collection   = None
stat_submission_players_collection = None
stat_events_collection        = None
clubs_collection              = None
venues_collection             = None
match_stats_collection        = None
competitions_collection       = None
contact_collection            = None
subscriptions_collection      = None
token_packages_collection     = None
topup_packages_collection     = None
leaderboard_collection        = None
player_tokens_collection      = None
dco_collection         = None
supervisor_collection         = None
config_collection             = None
counters_collection           = None
notifications_collection      = None
pages_collection              = None
competition_abuse_collection  = None
competition_email_verifications_collection = None

# ── Helper callables from main.py ────────────────────────────
MongoSerializer               = None
_make_tx_ref                  = None
_make_stats_request_ref       = None
aggregate_player_stats        = None
calculate_performance_score   = None
get_position_category         = None
send_email                    = None
upload_to_cloudinary          = None
verify_token                  = None
create_access_token           = None
normalize_role                = None
get_co_user                   = None

# ── App config constants ──────────────────────────────────────
FLUTTERWAVE_SECRET_KEY        = None
FLUTTERWAVE_PUBLIC_KEY        = None
ADMIN_EMAIL                   = None
SUPPORT_EMAIL                 = None

# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Called once from main.py (or app startup) to bind all collection
    handles and utility callables into this module's global namespace.

    Usage in main.py:
        import visitor_public_routes as vpr
        vpr._setup_dependencies(globals())
        app.include_router(vpr.router)

    SYNTAX FIX: Python ≤ 3.11 does not allow parenthesised global
    declarations.  Each name now has its own `global` statement.
    """
    # ── Collections ───────────────────────────────────────────
    global database
    global players_collection
    global player_stats_collection
    global stat_submissions_collection
    global stat_submission_players_collection
    global stat_events_collection
    global clubs_collection
    global venues_collection
    global match_stats_collection
    global competitions_collection
    global contact_collection
    global subscriptions_collection
    global token_packages_collection
    global topup_packages_collection
    global leaderboard_collection
    global player_tokens_collection
    global dco_collection
    global supervisor_collection
    global config_collection
    global counters_collection
    global notifications_collection
    global pages_collection
    global competition_abuse_collection
    global competition_email_verifications_collection

    # ── Callables ─────────────────────────────────────────────
    global MongoSerializer
    global _make_tx_ref
    global _make_stats_request_ref
    global aggregate_player_stats
    global calculate_performance_score
    global get_position_category
    global send_email
    global upload_to_cloudinary
    global verify_token
    global create_access_token
    global normalize_role
    global get_co_user

    # ── Config ────────────────────────────────────────────────
    global FLUTTERWAVE_SECRET_KEY
    global FLUTTERWAVE_PUBLIC_KEY
    global ADMIN_EMAIL
    global SUPPORT_EMAIL

    g = main_globals
    database = g.get("database")

    # Collections – try multiple plausible naming conventions from main.py
    def _col(name: str, *aliases):
        for k in (name, *aliases):
            v = g.get(k)
            if v is not None:
                return v
        logger.warning("[public_routes._setup_dependencies] collection not found: %s (tried %s)", name, (name,)+aliases)
        return None

    players_collection         = _col("players_collection")
    player_stats_collection    = _col("player_stats_collection", "match_stats_collection", "stats_collection")
    stat_submissions_collection = _col("stat_submissions_collection")
    stat_submission_players_collection = _col("stat_submission_players_collection")
    stat_events_collection     = _col("stat_events_collection")
    clubs_collection           = _col("clubs_collection", "club_collection")
    # The venue-registration route persists documents in MongoDB collection
    # "venues". Prefer the application's shared handle, but bind the same
    # database collection when main.py does not export that handle.
    venues_collection          = _col("venues_collection")
    if venues_collection is None and database is not None:
        venues_collection = database["venues"]
        logger.info(
            "[public_routes] Bound venues_collection | database=%s collection=venues",
            database.name,
        )
    match_stats_collection     = _col("match_stats_collection", "stats_collection", "matches_collection", "player_stats_collection")
    # Competitions are written by the Communications Officer router to the
    # canonical `competitions` collection. Prefer that exact shared handle;
    # when main.py does not export it, bind the database collection directly.
    competitions_collection = _col("competitions_collection")
    if competitions_collection is None and database is not None:
        competitions_collection = database["competitions"]
        logger.info(
            "[public_routes] Bound competitions_collection directly | database=%s collection=competitions",
            database.name,
        )
    contact_collection         = _col("contact_collection", "contacts_collection", "support_collection")
    subscriptions_collection   = _col("subscriptions_collection", "subscription_collection")
    token_packages_collection  = _col("token_packages_collection", "token_package_collection", "packages_collection")
    topup_packages_collection  = _col("topup_packages_collection", "topup_collection", "addon_collection")
    leaderboard_collection     = _col("leaderboard_collection")
    player_tokens_collection   = _col("player_tokens_collection", "tokens_collection")
    dco_collection      = _col("dco_collection", "dco_collection")
    supervisor_collection      = _col("supervisor_collection", "supervisors_collection")
    config_collection          = _col("config_collection", "settings_collection")
    counters_collection        = _col("counters_collection")
    notifications_collection   = _col("notifications_collection")
    pages_collection            = _col(
        "pages_collection", "page_content_collection", "content_collection",
    )
    if pages_collection is None and database is not None:
        pages_collection = database["page_content"]

    # The dashboard's normalized tracker collections are database-backed when
    # main.py does not expose named handles.  Public reads use the same source
    # of truth as the authenticated dashboard, and fall back to legacy stats.
    if database is not None:
        if stat_submissions_collection is None:
            stat_submissions_collection = database["stat_submissions"]
        if stat_submission_players_collection is None:
            stat_submission_players_collection = database["stat_submission_players"]
        if stat_events_collection is None:
            stat_events_collection = database["stat_events"]

    # Callables
    MongoSerializer              = g.get("MongoSerializer")
    _make_tx_ref                 = g.get("_make_tx_ref")
    _make_stats_request_ref      = g.get("_make_stats_request_ref")
    aggregate_player_stats       = g.get("aggregate_player_stats")
    calculate_performance_score  = g.get("calculate_performance_score")
    get_position_category        = g.get("get_position_category")
    send_email                   = g.get("send_email")
    upload_to_cloudinary         = g.get("upload_to_cloudinary")
    verify_token                 = g.get("verify_token")
    create_access_token          = g.get("create_access_token")
    normalize_role               = g.get("normalize_role")
    get_co_user                  = g.get("get_co_user")

    # Config
    FLUTTERWAVE_SECRET_KEY = g.get("FLUTTERWAVE_SECRET_KEY") or os.getenv("FLUTTERWAVE_SECRET_KEY", "")
    FLUTTERWAVE_PUBLIC_KEY = g.get("FLUTTERWAVE_PUBLIC_KEY") or os.getenv("FLUTTERWAVE_PUBLIC_KEY", "")
    ADMIN_EMAIL            = g.get("ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL", "enejistats@gmail.com")
    SUPPORT_EMAIL          = g.get("SUPPORT_EMAIL") or os.getenv("SUPPORT_EMAIL", "enejistats@gmail.com")

    logger.info("[public_routes] _setup_dependencies complete | collections_bound=%d", sum(1 for x in [
        players_collection, clubs_collection, venues_collection, match_stats_collection,
        competitions_collection, contact_collection, subscriptions_collection,
        token_packages_collection, topup_packages_collection,
         player_tokens_collection, dco_collection, supervisor_collection, config_collection,
         pages_collection,
    ] if x is not None))


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

# ============================================================
# INTERNAL UTILITIES
# ============================================================

def _json_safe(value: Any) -> Any:
    """Use the canonical serializer, with explicit support for Python dates."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    return MongoSerializer.serialize_value(value)

def _ser(doc: dict) -> dict:
    """Serialize a Mongo document through main.py's canonical service."""
    return MongoSerializer.serialize_document(doc) if doc else {}

def _ser_list(docs: list) -> list:
    return [_ser(d) for d in docs]


_ABOUT_JSON_KEYS = {
    "mission_cards", "story_paragraphs", "what_we_do_tabs", "values", "team",
}


def _clean_text(value: Any) -> str:
    """Decode pasted HTML entities and remove control characters from text."""
    return html_lib.unescape(str(value or "")).replace("\x00", "").strip()


def _clean_markup(value: Any) -> str:
    """Keep only the small formatting subset supported by the dashboard RTE."""
    text = html_lib.unescape(str(value or "")).replace("\x00", "")
    text = re.sub(r"(?is)<(script|style|iframe|object|embed|form|input|button)"
                  r"\b[^>]*>.*?</\1\s*>", "", text)
    text = re.sub(r"(?is)<(script|style|iframe|object|embed|form|input|button)"
                  r"\b[^>]*/?>", "", text)
    text = re.sub(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
                  "", text, flags=re.I)
    text = re.sub(r"(?i)(href|src)\s*=\s*(['\"])\s*javascript:[^'\"]*\2",
                  "", text)
    allowed = r"b|strong|i|em|u|br|p|ul|ol|li|h3|h4|a|img"
    text = re.sub(rf"(?is)</?(?!{allowed})(?:[a-z][^>]*)>", "", text)
    return text.strip()


def _deep_clean(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return [_deep_clean(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _deep_clean(v) for k, v in value.items()}
    return value


def _parse_section_value(key: str, value: Any) -> Any:
    if key in _ABOUT_JSON_KEYS:
        if isinstance(value, str):
            try:
                return _deep_clean(json.loads(html_lib.unescape(value)))
            except (TypeError, ValueError, json.JSONDecodeError):
                return []
        return _deep_clean(value) if isinstance(value, (dict, list)) else []
    if key.endswith("_html") or key in {"body", "message"}:
        return _clean_markup(value)
    return _clean_text(value)


def _about_defaults() -> dict:
    """Safe, complete defaults used only when a section has not been saved."""
    return {
        "hero_title": "About EnejiStats",
        "hero_subtitle": "Nigeria's trusted football data platform. Tracking talent with precision, integrity and reliability.",
        "mission_heading": "Our Mission",
        "mission_intro": "Three pillars drive everything we build at EnejiStats.",
        "mission_cards": [
            {"icon": "fa-crosshairs", "title": "Precision", "desc": "Every stat is verified by trained Data Collection Officers and reviewed by supervisors before publication."},
            {"icon": "fa-shield-halved", "title": "Integrity", "desc": "We do not manipulate data. Verified badges only appear when data has passed our multi-stage review process."},
            {"icon": "fa-rotate", "title": "Reliability", "desc": "Live leaderboards, real-time updates, and 99%+ platform uptime so you can trust the data when it matters most."},
        ],
        "story_heading": "Our Story",
        "story_paragraphs": [
            "EnejiStats was born out of a simple but powerful frustration: African football is full of exceptional talent that the world never gets to see — not because the players are not good enough, but because there is no reliable, verified data to prove it.",
            "Founded in Lagos, Nigeria, we set out to build Nigeria's trusted football data platform. Our proprietary Data Collection Officer (DCO) network now spans multiple Nigerian states, with trained officers attending matches, collecting granular performance data, and submitting it for supervisor review.",
            "The result is a growing database of verified match statistics — goals, assists, tackles, passes, saves, and more — for players across the grassroots and professional levels. This data powers our live leaderboards, public player profiles, and scouting tools.",
            "We believe African talent deserves the same quality of data infrastructure that exists in European football. EnejiStats is how we build that future — one verified match report at a time.",
        ],
        "what_we_do_heading": "What We Do",
        "what_we_do_tabs": [
            {"id": "players", "label": "Players", "icon": "fa-futbol", "heading": "For Players", "points": ["Create a verified public profile with live match statistics", "Get discovered by scouts and clubs across Africa", "Track your performance history across all competitions", "Earn a Data Scout rating based on verified match data"], "cta": "/register.html?role=player"},
            {"id": "clubs", "label": "Clubs", "icon": "fa-shield-halved", "heading": "For Clubs", "points": ["Monitor your full squad performance in real-time", "Request verified match data for any fixture", "Compare your squad against other clubs in your league", "Find new talent through our scouting network"], "cta": "/register.html?role=club"},
            {"id": "scouts", "label": "Scouts", "icon": "fa-binoculars", "heading": "For Scouts", "points": ["Access verified stats for players across Nigeria and Africa", "Filter players by position, age, height, and performance score", "Generate professional scouting reports", "Connect directly with clubs and agents"], "cta": "/register.html?role=scout"},
            {"id": "agents", "label": "Agents", "icon": "fa-handshake", "heading": "For Agents", "points": ["Manage up to 10 player profiles from your dashboard", "Track each client's verified performance data", "Showcase your players with professional PDF reports", "Commission tracking and payment management"], "cta": "/register.html?role=agent"},
        ],
        "values_heading": "Our Values",
        "values": [
            {"icon": "fa-star", "title": "Excellence", "desc": "We hold every data point to the highest standard of accuracy and professionalism."},
            {"icon": "fa-users", "title": "Community", "desc": "We exist to serve the African football community — players, clubs, scouts, and fans."},
            {"icon": "fa-lightbulb", "title": "Innovation", "desc": "We continuously improve our platform to stay ahead of the needs of modern football."},
            {"icon": "fa-handshake", "title": "Trust", "desc": "Every verified badge represents a promise we have kept to players and clubs."},
        ],
        "team_heading": "The Team",
        "team_intro": "Passionate about football, data, and African talent.",
        "team": [
            {"name": "Chukwuemeka Eneji", "role": "Founder & CEO", "bio": "Former football analyst with 10+ years in African football scouting and data management.", "photo_url": ""},
            {"name": "Adaeze Okonkwo", "role": "Head of Data Operations", "bio": "Oversees the DCO network and ensures data integrity across all match reports.", "photo_url": ""},
            {"name": "Biodun Adeyemi", "role": "CTO", "bio": "Full-stack engineer with expertise in real-time sports data systems and analytics platforms.", "photo_url": ""},
        ],
        "stats_players_label": "Players Registered",
        "stats_clubs_label": "Clubs Onboarded",
        "stats_matches_label": "Matches Tracked",
        "stats_data_scouts_label": "Active Data Scouts",
        "cta_title": "Ready to Join Nigeria's Football Data Revolution?",
        "cta_text": "Register free today and start tracking your football journey with verified data.",
        "cta_button_text": "Get Started Free",
        "cta_contact_text": "Contact Us",
    }


async def _load_page_sections(slug: str) -> list:
    """Read both the canonical section collection and older page documents."""
    docs = []
    if pages_collection is not None:
        try:
            cursor = pages_collection.find({
                "$or": [{"slug": slug}, {"page_slug": slug}, {"page": slug}],
            }).sort("updated_at", -1)
            docs = await cursor.to_list(length=500)
        except Exception:
            logger.exception("[_load_page_sections] failed for slug=%s", slug)
    sections = {}
    for doc in docs:
        if isinstance(doc.get("sections"), list):
            for sec in doc["sections"]:
                if isinstance(sec, dict) and sec.get("key"):
                    sections[sec["key"]] = sec
        elif isinstance(doc.get("sections"), dict):
            for key, value in doc["sections"].items():
                sections[str(key)] = {"key": str(key), "value": value}
        elif doc.get("key"):
            sections[str(doc["key"])] = doc
    return [
        {
            "key": key,
            "label": item.get("label") or key.replace("_", " ").title(),
            "type": item.get("type") or ("rich" if key in _ABOUT_JSON_KEYS else "text"),
            "value": item.get("value", ""),
            "updated_at": item.get("updated_at"),
        }
        for key, item in sections.items()
    ]


async def _load_about_content() -> dict:
    result = _about_defaults()
    for section in await _load_page_sections("about"):
        key = section["key"]
        if key in result:
            result[key] = _parse_section_value(key, section.get("value", ""))
    return result


def _canonical_role(value: Any) -> str:
    """Normalize roles through the platform registry."""
    if not callable(normalize_role):
        return ""
    try:
        return normalize_role(value)
    except (ValueError, TypeError):
        return ""

async def _require_co_access(request: Request) -> dict:
    """Require an authenticated Communications Officer via main.py."""
    if not callable(get_co_user):
        raise HTTPException(status_code=503, detail="Communications Officer auth is unavailable")
    return await get_co_user(request)

def _normalise_competition(doc: dict, public: bool = False) -> dict:
    item = _ser(doc)
    raw_status = str(_first_value(item, "status", default="Draft")).strip()
    status_lower = raw_status.lower()
    if public:
        if status_lower in {"ongoing", "active"}:
            display_status = "active"
        elif status_lower in {"completed", "closed", "finished"}:
            display_status = "completed"
        else:
            display_status = "upcoming"
    else:
        display_status = raw_status.title() if raw_status else "Draft"
    item.update({
        "id": _first_value(item, "id", "competition_id", "event_id", default=""),
        "title": _first_value(item, "title", "name", default="Event"),
        "name": _first_value(item, "name", "title", default="Event"),
        "event_type": _first_value(item, "event_type", "type", "category", default="Event"),
        "type": _first_value(item, "type", "event_type", "category", default="Event"),
        "status": display_status,
        "location": _first_value(item, "location", "region", "venue", "state", default="Nigeria"),
        "state": _first_value(item, "state", "region", default=""),
        "start_at": _first_value(item, "start_at", "start_date", "startDate", "date", default=""),
        "end_at": _first_value(item, "end_at", "end_date", "endDate", default=""),
        "organiser": _first_value(item, "organiser", "organizer", "contact", default="EnejiStats"),
        "description": _clean_text(_first_value(item, "description", default="")),
        "registration_fee": _safe_float(_first_value(item, "registration_fee", "registrationFee", "fee", default=0)),
        "maxTeams": _safe_int(_first_value(item, "maxTeams", "max_teams", "participants", default=0)),
        "registeredTeams": _safe_int(_first_value(item, "registeredTeams", "registered_teams", "registration_count", default=0)),
        "bookedTeams": _safe_int(_first_value(item, "bookedTeams", "booked_teams", "reservedTeams", "reserved_teams", default=0)),
        "maxBookingSlots": _safe_int(_first_value(item, "maxBookingSlots", "max_booking_slots", "booking_limit", default=0)),
        "registrationAvailableSlots": (lambda m, r: max(0, m-r) if m > 0 else None)(_safe_int(_first_value(item, "maxTeams", "max_teams", "participants", default=0)), _safe_int(_first_value(item, "registeredTeams", "registered_teams", "registration_count", default=0))),
        "bookingAvailableSlots": (lambda m, b: max(0, m-b) if m > 0 else None)(_safe_int(_first_value(item, "maxBookingSlots", "max_booking_slots", "booking_limit", default=0)), _safe_int(_first_value(item, "bookedTeams", "booked_teams", "reservedTeams", "reserved_teams", default=0))),
        "customFields": _first_value(item, "customFields", "custom_fields", default=[]),
        "custom_fields": _first_value(item, "custom_fields", "customFields", default=[]),
        # Canonical fields written by the Communications Officer dashboard.
        # Keep these aliases explicit so the public API is driven by the exact
        # CO document shape instead of requiring frontend-side field guessing.
        "prize": _first_value(item, "prize", default=""),
        "contact": _first_value(item, "contact", default=""),
        "rules": _first_value(item, "rules", default=""),
        "eligibleTypes": _first_value(item, "eligibleTypes", "eligible_types", default=""),
        "eligibleClubs": _first_value(item, "eligibleClubs", "eligible_clubs", default=""),
        "ageGroup": _first_value(item, "ageGroup", "age_group", default=""),
        "regLink": _first_value(item, "regLink", "reg_link", default=""),
        "organiserName": _first_value(item, "organiserName", "organiser", "organizer", default=""),
        "organiserPhone": _first_value(item, "organiserPhone", "organizer_phone", default=""),
        "detailedAddress": _first_value(item, "detailedAddress", "detailed_address", default=""),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "venueId": _first_value(item, "venueId", "venue_id", default=""),
        "maxTeams": _safe_int(_first_value(item, "maxTeams", "max_teams", "participants", default=0)),
        "maxBookingSlots": _safe_int(_first_value(item, "maxBookingSlots", "max_booking_slots", "booking_limit", default=0)),
        "bookedTeams": _safe_int(_first_value(item, "bookedTeams", "booked_teams", "reservedTeams", "reserved_teams", default=0)),
        "created_by": _first_value(item, "created_by", default=""),
        "created_at": _first_value(item, "created_at", default=""),
        "updated_at": _first_value(item, "updated_at", default=""),
        "last_edited_by": _first_value(item, "last_edited_by", default=""),
    })
    if not item["id"]:
        item["id"] = str(uuid.uuid4())
    return _json_safe(item)


def _competition_write_payload(payload: dict) -> dict:
    """Store both dashboard camelCase and public snake_case aliases."""
    out = {str(k): v for k, v in payload.items() if str(k) not in {"_id", "id"}}
    name = _clean_text(_first_value(out, "name", "title"))
    category = _clean_text(_first_value(out, "category", "event_type", "type"))
    status = _clean_text(_first_value(out, "status", default="Draft")).title()
    start = _clean_text(_first_value(out, "startDate", "start_date", "start_at"))
    end = _clean_text(_first_value(out, "endDate", "end_date", "end_at"))
    region = _clean_text(_first_value(out, "region", "location", "state"))
    out.update({
        "name": name, "title": name, "category": category, "event_type": category,
        "type": category, "status": status, "startDate": start, "start_date": start,
        "start_at": start, "endDate": end, "end_date": end, "end_at": end,
        "region": region, "location": region,
        "participants": _safe_int(_first_value(out, "participants", default=0)),
        "registration_fee": _safe_float(_first_value(out, "registration_fee", "fee", default=0)),
        "customFields": out.get("customFields", out.get("custom_fields", [])),
        "custom_fields": out.get("custom_fields", out.get("customFields", [])),
        "updated_at": _now_iso(),
    })
    return out


def _safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _first_value(source: Optional[dict], *keys: str, default: Any = "") -> Any:
    """Read the first populated value across the project's naming cases."""
    if not isinstance(source, dict):
        return default
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            if not (isinstance(value, str) and value.strip().lower()
                    in {"null", "undefined", "none", "n/a", "-", "—"}):
                return value
    return default


def _player_position(p: dict) -> str:
    return str(_first_value(
        p, "preferred_position", "preferredPosition", "position",
        "position_category", "positionCategory", default="",
    ))


def _player_name(p: dict) -> str:
    return str(_first_value(
        p, "full_name", "fullName", "name", default="",
    ) or " ".join(filter(None, [
        _first_value(p, "first_name", "firstName"),
        _first_value(p, "middle_name", "middleName"),
        _first_value(p, "last_name", "lastName"),
    ])).strip() or _first_value(p, "email", default="—"))


def _is_goalkeeper(position: Any) -> bool:
    value = str(position or "").strip().lower().replace("_", " ").replace("-", " ")
    return "keeper" in value or "goalie" in value or value in {"gk", "g", "goalkeeper"}


def _canonical_stat_value(raw: Any) -> int | float:
    if isinstance(raw, dict):
        raw = raw.get("success", raw.get("value", 0))
    try:
        number = float(raw or 0)
        if not math.isfinite(number) or number < 0:
            return 0
        return int(number) if number.is_integer() else number
    except (TypeError, ValueError, OverflowError):
        return 0


_PUBLIC_OUTFIELD_STATS = (
    "goals", "shot_goals", "header_goals", "penalty_goals", "assists",
    "shots_on_target", "shots_off_target", "successful_short_passes",
    "unsuccessful_short_passes", "successful_long_passes",
    "unsuccessful_long_passes", "successful_dribbles", "unsuccessful_dribbles",
    "successful_crosses", "unsuccessful_crosses", "tackles_won", "tackles_lost",
    "aerial_duels_won", "aerial_duels_lost", "interceptions", "clearances",
    "dispossessed", "yellow_cards", "red_cards", "fouls_given", "fouls_won",
    "offsides", "key_passes", "carries", "big_chances_created",
    "big_chances_missed", "progressive_passes", "progressive_carries",
    "final_third_entries", "penalty_area_entries", "recoveries", "blocks",
    "defensive_errors", "pressure_actions", "fouls_committed",
)
_PUBLIC_GK_STATS = (
    "saves", "goals_conceded", "penalty_saves", "clean_sheets",
    "successful_distributions", "unsuccessful_distributions", "punches",
    "successful_short_passes", "unsuccessful_short_passes",
    "successful_long_passes", "unsuccessful_long_passes", "interceptions",
    "clearances", "aerial_duels_won", "aerial_duels_lost", "tackles_won",
    "tackles_lost", "fouls_won", "dispossessed", "yellow_cards", "red_cards",
    "fouls_given", "offsides", "shots_faced", "claims", "defensive_errors",
    "recoveries", "blocks", "key_passes", "carries", "progressive_passes",
    "progressive_carries", "final_third_entries", "penalty_area_entries",
    "pressure_actions",
)


def _public_stats(raw: Any, position: str) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    # Keep position-specific fields first, but retain the complete union. A
    # goalkeeper can score, assist, pass, or receive cards; an outfield
    # player can also record goalkeeper-style events in the source data.
    primary_fields = _PUBLIC_GK_STATS if _is_goalkeeper(position) else _PUBLIC_OUTFIELD_STATS
    fields = tuple(dict.fromkeys(primary_fields + _PUBLIC_OUTFIELD_STATS + _PUBLIC_GK_STATS))
    aliases = {
        "fouls_given": ("fouls_given", "fouls", "foulsGiven"),
        "fouls_won": ("fouls_won", "foulsWon"),
        "yellow_cards": ("yellow_cards", "yellowCards"),
        "red_cards": ("red_cards", "redCards"),
        "goals_conceded": ("goals_conceded", "goalsConceded"),
        "penalty_saves": ("penalty_saves", "penaltySaves"),
        "clean_sheets": ("clean_sheets", "cleanSheets"),
    }
    stats = {field: _canonical_stat_value(_first_value(raw, *aliases.get(field, (field,))))
             for field in fields}
    goals = raw.get("goals", 0)
    if isinstance(goals, dict):
        stats["shot_goals"] = _canonical_stat_value(goals.get("shot", goals.get("shots", 0)))
        stats["header_goals"] = _canonical_stat_value(goals.get("header", 0))
        stats["penalty_goals"] = _canonical_stat_value(goals.get("penalty", 0))
        stats["goals"] = sum(stats[k] for k in ("shot_goals", "header_goals", "penalty_goals"))
    else:
        stats["goals"] = _canonical_stat_value(goals)
        for field, camel in (("shot_goals", "shotGoals"),
                             ("header_goals", "headerGoals"),
                             ("penalty_goals", "penaltyGoals")):
            if camel in raw:
                stats[field] = _canonical_stat_value(raw[camel])
    return stats


def _now_iso() -> str:
    return MongoSerializer.now_utc().isoformat()


def _resolve_id_filter(entity_id: str) -> list:
    """Build a $or filter that matches player_id, club_id, user_id, or _id."""
    filters: list = [
        {"player_id": entity_id},
        {"club_id": entity_id},
        {"user_id": entity_id},
        {"unique_id": entity_id},
    ]
    if len(entity_id) == 24:
        try:
            filters.append({"_id": ObjectId(entity_id)})
        except Exception:
            pass
    return filters


async def _find_player(player_id: str) -> Optional[dict]:
    """Fetch a player document by any known ID field."""
    if players_collection is None:
        return None
    doc = await players_collection.find_one({"$or": [
        {"player_id": player_id}, {"user_id": player_id},
        {"unique_id": player_id},
    ]})
    if not doc and len(player_id) == 24:
        try:
            doc = await players_collection.find_one({"_id": ObjectId(player_id)})
        except Exception:
            pass
    return doc


async def _find_club(club_id: str) -> Optional[dict]:
    """Fetch a club document by any known ID field."""
    if clubs_collection is None:
        return None
    doc = await clubs_collection.find_one({"club_id": club_id})
    if not doc:
        doc = await clubs_collection.find_one({"unique_id": club_id})
    if not doc and len(club_id) == 24:
        try:
            doc = await clubs_collection.find_one({"_id": ObjectId(club_id)})
        except Exception:
            pass
    return doc


def _build_player_card(p: dict) -> dict:
    """
    Produce the minimal player card expected by browse.html and leaderboard.html.
    Fields: id, name, position, club, nationality, age, photo_url, verified, rating.
    """
    pid  = _first_value(p, "player_id", "user_id", "unique_id",
                        default=str(p.get("_id", "")))
    name = _player_name(p)

    dob_raw = _first_value(p, "dob", "date_of_birth", "dateOfBirth")
    age = None
    if dob_raw:
        try:
            dob = datetime.fromisoformat(str(dob_raw).replace("Z", "+00:00"))
            if dob.tzinfo is None:
                dob = dob.replace(tzinfo=timezone.utc)
            today = MongoSerializer.now_utc()
            age = max(0, today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            ))
        except Exception:
            pass

    position = _player_position(p)
    raw_stats = (
        p.get("stats") or p.get("statistics") or p.get("season_stats")
        or p.get("seasonStats") or {}
    )
    return {
        "id":          pid,
        "name":        name,
        "position":    _player_position(p),
        "position_category": _first_value(p, "position_category", "positionCategory", default=""),
        "club":        _first_value(p, "current_club", "currentClub", "club", "club_name", default=""),
        "club_id":     _first_value(p, "club_id", "clubId", default=""),
        "nationality": _first_value(p, "nationality", default=""),
        "country":     _first_value(p, "country", "country_code", default=""),
        "state":       _first_value(p, "state", default=""),
        "player_level": _first_value(p, "player_level", "playerLevel", "level", default=""),
        "age":         age,
        "photo_url":   _first_value(
            p, "photo_url", "photo", "avatar", "profile_photo",
            "profileImage", "imageUrl", default="",
        ),
        "verified":    bool(_first_value(p, "verified", "email_verified", "is_verified", default=False)),
        "rating":      _safe_float(_first_value(p, "performance_score", "rating", "average_rating", default=0), 0.0),
        "performance_score": _safe_float(_first_value(p, "performance_score", "rating", default=0), 0.0),
        # Browse cards consume player.stats for their position-aware preview.
        # Keep the complete public metric union so exceptional out-of-position
        # events remain visible when they are present on the player document.
        "stats": _public_stats(raw_stats, position),
    }


def _build_club_card(c: dict) -> dict:
    """Produce the minimal club card expected by browse.html."""
    cid = _first_value(c, "club_id", "unique_id", "user_id",
                       default=str(c.get("_id", "")))
    return {
        "id":         cid,
        "name":       _first_value(c, "club_name", "name", "full_name", default="—"),
        "badge_url":  _first_value(c, "logo", "avatar", "badge_url", "badge", "logo_url", default=""),
        "verified":   bool(_first_value(c, "verified", "email_verified", "is_verified", default=False)),
        "city":       _first_value(c, "city", "town", default=""),
        "lga":        _first_value(c, "lga", "local_government", "district", "county", default=""),
        "state":      _first_value(c, "state", default=""),
        "country":    _first_value(c, "country", "country_code", default=""),
        "category":   _first_value(c, "club_level", "category", "league", default=""),
        "squad_size": _safe_int(_first_value(c, "squad_size", "players_count", "squadSize", default=0), 0),
        "founded":    _first_value(c, "founded", default=None),
    }


# ============================================================
# SECTION 1 – PLATFORM STATS  (homepage counter strip)
# ============================================================

@router.get("/api/public/stats")
async def get_platform_stats(request: Request):
    """
    Return aggregate platform counters used by index.html hero section.

    Response:
    {
        "players": int,
        "clubs": int,
        "venues": int,
        "matches": int,
        "dcos": int,
        "supervisors": int,
        "data_scouts": int
    }
    """
    logger.debug(
        "[get_platform_stats] ENTRY | client=%s",
        request.client.host if request.client else "unknown",
    )

    try:
        counts = await _gather_platform_counts()

        logger.debug(
            "[get_platform_stats] RESULT | %r",
            counts,
        )

        return JSONResponse(content=counts)

    except Exception:
        # Do NOT hide the real database/application error.
        logger.exception("[get_platform_stats] ERROR")

        # Keep the API response predictable if something unexpected
        # happens outside the individual collection counters.
        return JSONResponse(
            status_code=500,
            content={
                "players": 0,
                "clubs": 0,
                "venues": 0,
                "matches": 0,
                "dcos": 0,
                "supervisors": 0,
                "data_scouts": 0,
            },
        )


async def _gather_platform_counts() -> dict:
    """
    Count all platform entities used by the public homepage metrics.

    Uses the complete injected collection for each entity. No filtering is
    applied. Venues are counted as one collection total; venue_type is
    descriptive and is not used as a filter.

    A widget submission creates one root document in
    stat_submissions_collection. Player statistics and events are child
    documents in separate collections, so the public match metric counts
    root submissions rather than player-stat or event rows. The
    submission_key makes retries idempotent. The submitted schema has no
    separate match_id, so independently-created submissions cannot be
    safely merged as the same match.

    dcos is the DCO-only count. data_scouts is the combined DCO +
    supervisor count required by the public API.
    """

    collections = {
        "players": players_collection,
        "clubs": clubs_collection,
        "venues": venues_collection,
        # submit_widget_stats() persists one canonical match root here.
        "matches": stat_submissions_collection,
        "dcos": dco_collection,
        "supervisors": supervisor_collection,
    }

    results = {}

    counting_methods = {
        "players": "count_documents({})",
        "clubs": "count_documents({})",
        "venues": "count_documents({})",
        "matches": "count_documents({}) on stat_submissions root documents",
        "dcos": "count_documents({})",
        "supervisors": "count_documents({})",
    }

    for name, collection in collections.items():

        # A missing collection should be visible in the logs rather than
        # silently looking like a legitimate zero.
        if collection is None:
            logger.error(
                "[_gather_platform_counts] Collection is None | metric=%s method=%s",
                name,
                counting_methods[name],
            )
            results[name] = 0
            continue

        try:
            count = await collection.count_documents({})

            results[name] = count

            logger.info(
                "[_gather_platform_counts] COUNT | metric=%s database=%s "
                "collection=%s method=%s result=%s",
                name,
                collection.database.name,
                collection.name,
                counting_methods[name],
                count,
            )

        except Exception as exc:
            # Log the actual exception instead of silently returning 0.
            logger.exception(
                "[_gather_platform_counts] COUNT FAILED | metric=%s database=%s "
                "collection=%s method=%s exception=%s",
                name,
                getattr(getattr(collection, "database", None), "name", "?"),
                getattr(collection, "name", "?"),
                counting_methods[name],
                exc,
            )
            results[name] = 0

    # Keep the individual DCO count intact. Only data_scouts is combined.
    results["data_scouts"] = (
        results.get("dcos", 0)
        + results.get("supervisors", 0)
    )

    logger.info(
        "[_gather_platform_counts] COUNT | metric=data_scouts database=%s "
        "collection=dco_collection+supervisor_collection method="
        "dcos+supervisors result=%s",
        getattr(getattr(dco_collection, "database", None), "name", "?"),
        results["data_scouts"],
    )
    logger.info(
        "[_gather_platform_counts] FINAL COUNTS | %r",
        results,
    )

    return results


@router.get("/api/public/about")
async def get_public_about(request: Request):
    """Return the published About page content saved by the CO dashboard."""
    try:
        return JSONResponse(content=_json_safe(await _load_about_content()))
    except Exception as exc:
        logger.error("[get_public_about] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content=_json_safe(_about_defaults()))


@router.get("/api/public/pages/{slug}")
async def get_public_page_content(request: Request, slug: str):
    """Read published plain/rich page sections for public visitor pages."""
    sections = await _load_page_sections(slug)
    content = {}
    for section in sections:
        key = section["key"]
        value = section.get("value", "")
        content[key] = _parse_section_value(key, value)
    return JSONResponse(content=_json_safe({"slug": slug, "content": content}))


# ============================================================
# SECTION 2 – LEADERBOARD  (homepage teaser + full pages)
# ============================================================

@router.get("/api/public/leaderboard")
async def get_leaderboard_teaser(
    request: Request,
    limit: int = Query(default=5, ge=1, le=20),
):
    """
    Homepage leaderboard teaser (index.html).
    Response: { players: [...], clubs: [...] }
    Each player card: id, name, position, club, state, rating, goals,
                      assists, matches, verified, rank, trend
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_leaderboard_teaser] ENTRY | limit=%d", limit)
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        players_data = await _fetch_top_players(limit=limit)
        clubs_data   = await _fetch_top_clubs(limit=limit)

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[get_leaderboard_teaser] RESULT | players=%d clubs=%d",
            len(players_data), len(clubs_data),
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"players": players_data, "clubs": clubs_data})

    except Exception as exc:
        logger.error("[get_leaderboard_teaser] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content={"players": [], "clubs": []})


@router.get("/api/public/leaderboard/players")
async def get_players_leaderboard(
    request: Request,
    period:   str = Query(default="all",  description="all|week|month"),
    state:    str = Query(default="",     description="Nigerian state filter"),
    position: str = Query(default="",     description="Position filter"),
    limit:    int = Query(default=20, ge=1, le=100),
):
    """
    Full player leaderboard (leaderboard.html).
    Response: { data: [...], pages: N, total: N }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[get_players_leaderboard] ENTRY | period=%r state=%r position=%r limit=%d",
        period, state, position, limit,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        data = await _fetch_top_players(
            limit=limit, period=period, state=state, position=position,
        )

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_players_leaderboard] RESULT | count=%d", len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data, "pages": 1, "total": len(data)})

    except Exception as exc:
        logger.error("[get_players_leaderboard] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content={"data": [], "pages": 1, "total": 0})


@router.get("/api/public/leaderboard/clubs")
async def get_clubs_leaderboard(
    request: Request,
    period: str = Query(default="all"),
    state:  str = Query(default=""),
    limit:  int = Query(default=20, ge=1, le=100),
):
    """
    Full club leaderboard (leaderboard.html).
    Response: { data: [...], pages: N, total: N }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[get_clubs_leaderboard] ENTRY | period=%r state=%r limit=%d",
        period, state, limit,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        data = await _fetch_top_clubs(limit=limit, state=state)

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_clubs_leaderboard] RESULT | count=%d", len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data, "pages": 1, "total": len(data)})

    except Exception as exc:
        logger.error("[get_clubs_leaderboard] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content={"data": [], "pages": 1, "total": 0})


@router.get("/api/public/leaderboard/spotlight")
async def get_leaderboard_spotlight(request: Request):
    """
    Top / spotlight player card (leaderboard.html hero strip).
    Response: single player object with extended stats.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_leaderboard_spotlight] ENTRY")
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        players = await _fetch_top_players(limit=1)
        result  = players[0] if players else {}

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_leaderboard_spotlight] RESULT | player_id=%r", result.get("id"))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=result)

    except Exception as exc:
        logger.error("[get_leaderboard_spotlight] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content={})


# ── Internal leaderboard helpers ─────────────────────────────

async def _fetch_top_players(
    limit: int = 20,
    period: str = "all",
    state: str = "",
    position: str = "",
) -> list:
    if players_collection is None:
        return []

    period = {
        "all_time": "all",
        "all-time": "all",
        "weekly": "week",
        "monthly": "month",
    }.get(str(period or "").strip().lower(), str(period or "all").strip().lower())

    filt: dict = {}
    if state and state.lower() not in ("", "all"):
        filt["state"] = {"$regex": re.escape(state), "$options": "i"}
    if position and position.lower() not in ("", "all"):
        filt["$or"] = [
            {"preferredPosition": {"$regex": re.escape(position), "$options": "i"}},
            {"preferred_position": {"$regex": re.escape(position), "$options": "i"}},
            {"position": {"$regex": re.escape(position), "$options": "i"}},
                {"position_category": {"$regex": re.escape(position), "$options": "i"}},
        ]

    sort_field = "rating"
    if period == "week":
        sort_field = "weekly_rating"
    elif period == "month":
        sort_field = "monthly_rating"

    cursor = players_collection.find(filt).sort(sort_field, -1).limit(limit)
    docs   = await cursor.to_list(length=limit)

    result = []
    for rank, p in enumerate(docs, start=1):
        card = _build_player_card(p)
        card.update({
            "rank":    rank,
            "goals":   _safe_int(p.get("goals") or p.get("total_goals"), 0),
            "assists": _safe_int(p.get("assists") or p.get("total_assists"), 0),
            "matches": _safe_int(p.get("matches_played") or p.get("total_matches"), 0),
            "trend":   p.get("trend", "stable"),
        })
        result.append(card)
    return result


async def _fetch_top_clubs(limit: int = 20, state: str = "") -> list:
    if clubs_collection is None:
        return []

    filt: dict = {}
    if state and state.lower() not in ("", "all"):
        filt["state"] = {"$regex": re.escape(state), "$options": "i"}

    cursor = clubs_collection.find(filt).sort("points", -1).limit(limit)
    docs   = await cursor.to_list(length=limit)

    result = []
    for rank, c in enumerate(docs, start=1):
        card = _build_club_card(c)
        card.update({
            "rank":   rank,
            "points": _safe_int(c.get("points") or c.get("season_points"), 0),
            "wins":   _safe_int(c.get("wins") or c.get("season_wins"), 0),
        })
        result.append(card)
    return result


# ============================================================
# SECTION 3 – BROWSE PLAYERS  (browse.html)
# ============================================================

@router.get("/api/public/players")
async def browse_players(
    request:  Request,
    q:        str = Query(default="", description="Name search"),
    page:     int = Query(default=1,  ge=1),
    limit:    int = Query(default=12, ge=1, le=50),
    position: str = Query(default=""),
    state:    str = Query(default=""),
    verified: str = Query(default=""),
):
    """
    Paginated player browse (browse.html).
    Response: { data: [...], pages: N, total: N }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[browse_players] ENTRY | q=%r page=%d limit=%d position=%r state=%r verified=%r",
        q, page, limit, position, state, verified,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if players_collection is None:
        return JSONResponse(content={"data": [], "pages": 0, "total": 0})

    try:
        filt: dict = {}
        if q:
            filt["$or"] = [
                {"first_name": {"$regex": re.escape(q), "$options": "i"}},
                {"firstName":  {"$regex": re.escape(q), "$options": "i"}},
                {"last_name":  {"$regex": re.escape(q), "$options": "i"}},
                {"lastName":   {"$regex": re.escape(q), "$options": "i"}},
                {"full_name":  {"$regex": re.escape(q), "$options": "i"}},
                {"name":       {"$regex": re.escape(q), "$options": "i"}},
                {"current_club": {"$regex": re.escape(q), "$options": "i"}},
                {"club":       {"$regex": re.escape(q), "$options": "i"}},
            ]
        if position and position.lower() != "all":
            position_aliases = {
                "forward": ("forward", "attacker", "striker", "st", "cf", "lw", "rw"),
                "attacker": ("forward", "attacker", "striker", "st", "cf", "lw", "rw"),
                "midfielder": ("midfielder", "midfield", "cm", "cdm", "cam", "lm", "rm"),
                "defender": ("defender", "defence", "defense", "cb", "lb", "rb", "lwb", "rwb"),
                "goalkeeper": ("goalkeeper", "goal keeper", "keeper", "goalie", "gk"),
            }
            aliases = position_aliases.get(position.strip().lower(), (position,))
            position_clauses = []
            for alias in aliases:
                pattern = re.escape(alias)
                position_clauses.extend([
                    {"preferredPosition": {"$regex": pattern, "$options": "i"}},
                    {"preferred_position": {"$regex": pattern, "$options": "i"}},
                    {"position": {"$regex": pattern, "$options": "i"}},
                    {"position_category": {"$regex": pattern, "$options": "i"}},
                ])
            if filt.get("$or"):
                filt["$and"] = [{"$or": filt.pop("$or")}, {"$or": position_clauses}]
            else:
                filt["$or"] = position_clauses
        if state and state.lower() not in ("", "all"):
            filt["state"] = {"$regex": re.escape(state), "$options": "i"}
        if verified.lower() == "true":
            filt["verified"] = True

        total  = await players_collection.count_documents(filt)
        pages  = max(1, math.ceil(total / limit))
        skip   = (page - 1) * limit
        cursor = players_collection.find(filt).sort("performance_score", -1).skip(skip).limit(limit)
        docs   = await cursor.to_list(length=limit)

        data = [_build_player_card(p) for p in docs]

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[browse_players] RESULT | total=%d pages=%d returned=%d",
            total, pages, len(data),
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data, "pages": pages, "total": total})

    except Exception as exc:
        logger.error("[browse_players] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content={"data": [], "pages": 0, "total": 0})


# ============================================================
# SECTION 4 – BROWSE CLUBS  (browse.html)
# ============================================================



# ============================================================
# SECTION 5 – PLAYER PROFILE  (player-profile.html)
# ============================================================

@router.get("/api/public/players/{player_id}")
async def get_public_player(request: Request, player_id: str):
    """
    Public player profile page (player-profile.html).
    Returns full profile document stripped of private fields.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_public_player] ENTRY | player_id=%r", player_id)
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if players_collection is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    try:
        doc = await _find_player(player_id)
        if not doc:
            # ── DEBUG BLOCK START ──────────────────────────────────────────
            logger.debug("[get_public_player] NOT FOUND | player_id=%r", player_id)
            # ── DEBUG BLOCK END ────────────────────────────────────────────
            raise HTTPException(status_code=404, detail="Player not found")

        out = _ser(doc)
        for private_key in (
            "password", "email", "phone", "whatsapp", "reset_token",
            "liveness_token", "legal_acceptance", "gps_lat", "gps_lng",
            "gps_acc", "detailed_address",
        ):
            out.pop(private_key, None)

        # Ensure a canonical id field for the frontend
        if "id" not in out:
            out["id"] = _first_value(
                doc, "player_id", "user_id", "unique_id",
                default=str(doc.get("_id", "")),
            )

        # Coerce name fields into a single display_name for convenience
        if not out.get("display_name"):
            out["display_name"] = _player_name(out)
        # Auth registration stores snake_case fields.  Keep the original
        # document while exposing the same canonical aliases used by cards.
        out.setdefault("player_id", _first_value(doc, "player_id", "user_id", default=out["id"]))
        out.setdefault("full_name", _player_name(doc))
        out.setdefault("position", _player_position(doc))
        out.setdefault("preferred_position", _player_position(doc))
        out.setdefault(
            "photo_url",
            _first_value(
                doc, "photo_url", "photo", "avatar", "profile_photo",
                "profileImage", "imageUrl", default="",
            ),
        )
        settings = out.get("settings")
        if isinstance(settings, dict):
            for key, value in settings.items():
                out.setdefault(key, value)

        # Embed the same dashboard-compatible aggregate shape in the public
        # profile response so unauthenticated profile pages can render the
        # season and match metrics without calling protected dashboard routes.
        public_matches = await _load_public_player_matches(
            player_id, str(out.get("player_id") or out.get("id") or player_id),
            _player_position(out), 200,
        )
        position = _player_position(out)
        season_stats = {
            field: 0 for field in (
                _PUBLIC_GK_STATS if _is_goalkeeper(position)
                else _PUBLIC_OUTFIELD_STATS
            )
        }
        total_minutes = 0
        for match in public_matches:
            raw_stats = match.get("stats") if isinstance(match, dict) else {}
            for key, value in _public_stats(raw_stats, position).items():
                season_stats[key] = season_stats.get(key, 0) + _canonical_stat_value(value)
            total_minutes += _safe_int(match.get("minutes_played"), 0)
        season_stats["minutes_played_total"] = total_minutes
        summary_stats = {
            "matchesPlayed": len(public_matches),
            "matches_played": len(public_matches),
            "totalGoals": season_stats.get("goals", 0),
            "totalAssists": season_stats.get("assists", 0),
            "minutesPlayed": total_minutes,
            "minutes_played": total_minutes,
            "position": position,
            "positionGroup": "Goalkeeper" if _is_goalkeeper(position) else "Outfield",
            "availableStatFields": list(season_stats.keys()),
        }
        # Always return one stable public contract, including when the player
        # has no completed matches. The frontend must not fall back to demo
        # values merely because a stats collection is empty.
        out.update({
            "summary": summary_stats,
            "summary_stats": summary_stats,
            "seasonStats": season_stats,
            "season_stats": season_stats,
            "matchData": public_matches,
            "match_data": public_matches,
            "matches": public_matches,
        })

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_public_player] RESULT | id=%r verified=%r", out.get("id"), out.get("verified"))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=_json_safe(out))

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[get_public_player] ERROR | player_id=%r | %s\n%s", player_id, exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/public/players/{player_id}/matches")
async def get_player_matches(
    request:   Request,
    player_id: str,
    page:      int = Query(default=1, ge=1),
    limit:     int = Query(default=10, ge=1, le=50),
):
    """
    Player match history (player-profile.html matches tab).
    Response: { data: [...], pages: N, total: N }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[get_player_matches] ENTRY | player_id=%r page=%d limit=%d",
        player_id, page, limit,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if match_stats_collection is None:
        return JSONResponse(content={"data": [], "pages": 0, "total": 0})

    try:
        player_doc = await _find_player(player_id)
        if not player_doc:
            return JSONResponse(content={"data": [], "pages": 1, "total": 0})
        pid = str(_first_value(player_doc, "player_id", "user_id",
                               default=str(player_doc.get("_id", player_id))))
        position = _player_position(player_doc)
        all_data = await _load_public_player_matches(player_id, pid, position, 200)
        total = len(all_data)
        pages = max(1, math.ceil(total / limit)) if total else 1
        data = all_data[(page - 1) * limit: page * limit]

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_player_matches] RESULT | total=%d pages=%d returned=%d", total, pages, len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={
            "data": _json_safe(data), "pages": pages, "total": total,
        })

    except Exception as exc:
        logger.error("[get_player_matches] ERROR | player_id=%r | %s\n%s", player_id, exc, traceback.format_exc())
        return JSONResponse(content={"data": [], "pages": 0, "total": 0})


async def _load_public_player_matches(
    uid: str, pid: str, position: str, limit: int = 200
) -> list:
    """Read the same normalized tracker rows and legacy rows as the dashboard."""
    ids = [value for value in {str(uid), str(pid)} if value]
    records = []
    if (stat_submissions_collection is not None
            and stat_submission_players_collection is not None
            and stat_events_collection is not None):
        rows = await stat_submission_players_collection.find(
            {"player_id": {"$in": ids}}
        ).sort("player_order", 1).limit(max(1, limit * 3)).to_list(
            length=max(1, limit * 3)
        )
        by_submission = {}
        row_ids = []
        for row in rows:
            key = str(row.get("submission_id", ""))
            if key and key not in by_submission:
                by_submission[key] = row
                if row.get("_id") is not None:
                    row_ids.append(row["_id"])
        if by_submission:
            submissions = await stat_submissions_collection.find({
                "_id": {"$in": [row.get("submission_id") for row in by_submission.values()]},
                "status": {"$in": [
                    "approved", "verified", "completed", "pending_approval",
                    "pending_validation", "submitted",
                ]},
            }).sort("submitted_at", -1).limit(max(1, limit)).to_list(length=max(1, limit))
            events = await stat_events_collection.find(
                {"submission_player_id": {"$in": row_ids}}
            ).sort("event_order", 1).to_list(length=max(1, limit * 100))
            events_by_row = {}
            for event in events:
                events_by_row.setdefault(str(event.get("submission_player_id", "")), []).append(event)
            for submission in submissions:
                row = by_submission.get(str(submission.get("_id", "")))
                if not row:
                    continue
                match = submission.get("match") or {}
                event_rows = events_by_row.get(str(row.get("_id", "")), [])
                row_stats = row.get("stats") if isinstance(row.get("stats"), dict) else {}
                stats = _public_stats({
                    **row_stats,
                    **_events_to_public_stats(event_rows),
                }, position)
                date = (_first_value(match, "match_date", "date", default="")
                        or submission.get("match_date")
                        or submission.get("submitted_at"))
                home = _team_name(match, "home")
                away = _team_name(match, "away")
                home_score = _score_value(match, "home")
                away_score = _score_value(match, "away")
                records.append({
                    "_id": str(submission.get("_id", "")),
                    "submission_id": str(submission.get("_id", "")),
                    "player_id": pid, "home_team": home, "away_team": away,
                    "home_team_name": home, "away_team_name": away,
                    "home_club": home, "away_club": away,
                    "date": date, "match_date": date,
                    "match_time": _first_value(match, "match_time", "time", default=""),
                    "status": _first_value(match, "status", "match_status", default=""),
                    "approval_status": submission.get("status", ""),
                    "result": _first_value(match, "result", "match_result", default=""),
                    "home_score": home_score, "away_score": away_score,
                    "score": {"home": home_score, "away": away_score},
                    "competition": _first_value(match, "competition", "league", "match_type", default=""),
                    "venue": _first_value(match, "venue_name", "venueName", "stadium", "venue", default=""),
                    "minutes_played": _minutes_from_events(row, event_rows),
                    "role": position, "stats": stats,
                    "events": [_public_event(e) for e in event_rows],
                    "heatmap_events": [_public_event(e) for e in event_rows],
                    "heatmap_data": [_public_event(e) for e in event_rows if e.get("location") is not None],
                    "action_timeline": [_public_event(e) for e in event_rows],
                })
    if records:
        return records
    if player_stats_collection is None:
        return []
    docs = await player_stats_collection.find({
        "$or": [{"player_id": uid}, {"player_id": pid}],
        "status": {"$in": ["approved", "verified", "completed"]},
    }).sort("match_date", -1).limit(max(1, min(limit, 200))).to_list(
        length=max(1, min(limit, 200))
    )
    for doc in docs:
        item = _ser(doc) or {}
        raw_stats = item.get("stats") or {
            key: value for key, value in item.items()
            if key not in {"_id", "player_id", "status", "match_date", "date",
                           "created_at", "updated_at", "events"}
        }
        item["stats"] = _public_stats(raw_stats, position)
        item.setdefault("date", item.get("match_date"))
        item.setdefault("match_date", item.get("date"))
        item.setdefault("home_team_name", item.get("home_team", ""))
        item.setdefault("away_team_name", item.get("away_team", ""))
        item.setdefault("score", {"home": item.get("home_score"), "away": item.get("away_score")})
        item.setdefault("events", item.get("action_timeline", []))
        item.setdefault("heatmap_events", item["events"])
        item.setdefault("action_timeline", item["events"])
        records.append(item)
    return records


def _events_to_public_stats(events: list) -> dict:
    """Project atomic tracker events into the dashboard's persisted stat names."""
    out = {}
    pairs = {
        "passes": ("successful_short_passes", "unsuccessful_short_passes"),
        "longpass": ("successful_long_passes", "unsuccessful_long_passes"),
        "shots": ("shots_on_target", "shots_off_target"),
        "dribbles": ("successful_dribbles", "unsuccessful_dribbles"),
        "crosses": ("successful_crosses", "unsuccessful_crosses"),
        "duels": ("aerial_duels_won", "aerial_duels_lost"),
        "tackles": ("tackles_won", "tackles_lost"),
        "distribution": ("successful_distributions", "unsuccessful_distributions"),
    }
    singles = {
        "assists": "assists", "foulsWon": "fouls_won", "foulsCommitted": "fouls_given",
        "interceptions": "interceptions", "clearances": "clearances", "saves": "saves",
        "goalsConceded": "goals_conceded", "penaltySaves": "penalty_saves",
        "cleanSheets": "clean_sheets", "punches": "punches", "yellowCards": "yellow_cards",
        "redCards": "red_cards", "offsides": "offsides", "keyPasses": "key_passes",
        "carries": "carries", "recoveries": "recoveries", "blocks": "blocks",
        "defensiveErrors": "defensive_errors", "pressureActions": "pressure_actions",
        "progressivePasses": "progressive_passes", "progressiveCarries": "progressive_carries",
        "finalThirdEntries": "final_third_entries", "penaltyAreaEntries": "penalty_area_entries",
    }
    for event in events:
        metric = event.get("metric")
        if metric == "goals":
            out["goals"] = out.get("goals", 0) + 1
            continue
        if metric in pairs:
            success, failure = pairs[metric]
            if metric == "passes" and "long" in str(event.get("value_type", "")).lower():
                success, failure = "successful_long_passes", "unsuccessful_long_passes"
            key = failure if str(event.get("outcome", "success")).lower() == "failure" else success
            out[key] = out.get(key, 0) + 1
        elif metric in singles:
            key = singles[metric]
            out[key] = out.get(key, 0) + 1
    return out


def _public_event(event: dict) -> dict:
    return {key: value for key, value in {
        "event_id": str(event.get("event_id") or event.get("_id", "")),
        "metric": event.get("metric", ""), "outcome": event.get("outcome", "success"),
        "value_type": event.get("value_type", "success"), "period": event.get("period", 1),
        "elapsed_seconds": event.get("elapsed_seconds", 0),
        "multiplier": event.get("multiplier", 1), "location": event.get("location"),
        "metadata": event.get("metadata"), "recorded_at": event.get("recorded_at"),
    }.items() if value is not None}


def _team_name(match: dict, side: str) -> str:
    value = _first_value(match, f"{side}_team_name", f"{side}TeamName",
                          f"{side}_team", f"{side}Team", f"{side}_club_name",
                          f"{side}ClubName", f"{side}_club", f"{side}Club", default="")
    if isinstance(value, dict):
        value = _first_value(value, "name", "team_name", "teamName", "club_name", "clubName")
    return str(value or "")


def _score_value(match: dict, side: str) -> Any:
    value = _first_value(match, f"{side}_score", f"{side}Score",
                          f"{side}_goals", f"{side}Goals", default="")
    score = match.get("score") if isinstance(match.get("score"), dict) else {}
    if value == "":
        value = _first_value(score, side, f"{side}_score", f"{side}Score", default="")
    return value


def _minutes_from_events(player: dict, events: list) -> int:
    value = _first_value(player, "minutes_played", "minutesPlayed", "minutes",
                         "minutes_on_pitch", "minutesOnPitch", default="")
    if value != "":
        return max(0, int(round(_canonical_stat_value(value))))
    seconds = []
    for event in events:
        raw = _first_value(event, "elapsed_seconds", "elapsedSeconds", "elapsed", default="")
        if raw != "":
            seconds.append(float(raw) / 60)
    return max(0, int(round(max(seconds, default=0))))


# ============================================================
# SECTION 6 – CLUB PROFILE  (club-profile.html)
# ============================================================

@router.get("/api/public/clubs/{club_id}")
async def get_public_club(request: Request, club_id: str):
    """
    Public club profile page (club-profile.html).
    Returns full club document with season stats embedded.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_public_club] ENTRY | club_id=%r", club_id)
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if clubs_collection is None:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    try:
        doc = await _find_club(club_id)
        if not doc:
            # ── DEBUG BLOCK START ──────────────────────────────────────────
            logger.debug("[get_public_club] NOT FOUND | club_id=%r", club_id)
            # ── DEBUG BLOCK END ────────────────────────────────────────────
            raise HTTPException(status_code=404, detail="Club not found")

        out = _ser(doc)
        if "id" not in out:
            out["id"] = doc.get("club_id") or doc.get("unique_id") or str(doc.get("_id", ""))

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_public_club] RESULT | id=%r name=%r", out.get("id"), out.get("name"))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=out)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[get_public_club] ERROR | club_id=%r | %s\n%s", club_id, exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/public/clubs/{club_id}/squad")
async def get_club_squad(
    request: Request,
    club_id: str,
):
    """
    Club squad member list (club-profile.html squad tab).
    Response: { data: [...] }  — each item has id, name, position, number, photo_url.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_club_squad] ENTRY | club_id=%r", club_id)
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        club_doc = await _find_club(club_id)
        if not club_doc:
            return JSONResponse(content={"data": []})

        # Squad may be embedded in the club document
        embedded = club_doc.get("squad") or club_doc.get("players") or []
        if embedded:
            # ── DEBUG BLOCK START ──────────────────────────────────────────
            logger.debug("[get_club_squad] EMBEDDED | count=%d", len(embedded))
            # ── DEBUG BLOCK END ────────────────────────────────────────────
            return JSONResponse(content={"data": embedded})

        # Otherwise pull from players_collection
        if players_collection is None:
            return JSONResponse(content={"data": []})

        resolved_id = club_doc.get("club_id") or club_doc.get("unique_id") or str(club_doc.get("_id", club_id))
        filt = {"$or": [
            {"club_id":   resolved_id},
            {"club_id":   club_id},
            {"club":      club_doc.get("name", "__NOMATCH__")},
        ]}
        cursor = players_collection.find(filt).sort("lastName", 1).limit(100)
        docs   = await cursor.to_list(length=100)
        data   = [_build_player_card(p) for p in docs]

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_club_squad] DB RESULT | count=%d", len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data})

    except Exception as exc:
        logger.error("[get_club_squad] ERROR | club_id=%r | %s\n%s", club_id, exc, traceback.format_exc())
        return JSONResponse(content={"data": []})


@router.get("/api/public/clubs/{club_id}/matches")
async def get_club_matches(
    request: Request,
    club_id: str,
    page:    int = Query(default=1,  ge=1),
    limit:   int = Query(default=10, ge=1, le=50),
):
    """
    Club match history (club-profile.html matches tab).
    Response: { data: [...], pages: N, total: N }
    Each item: id, date, opponent, location, competition, result, score.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_club_matches] ENTRY | club_id=%r page=%d limit=%d", club_id, page, limit)
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        club_doc = await _find_club(club_id)
        if not club_doc:
            return JSONResponse(content={"data": [], "pages": 0, "total": 0})

        # Matches may be embedded
        embedded = club_doc.get("matches") or []
        if embedded:
            total  = len(embedded)
            pages  = max(1, math.ceil(total / limit))
            sliced = embedded[(page - 1) * limit : page * limit]
            return JSONResponse(content={"data": sliced, "pages": pages, "total": total})

        if match_stats_collection is None:
            return JSONResponse(content={"data": [], "pages": 0, "total": 0})

        resolved_id = club_doc.get("club_id") or club_doc.get("unique_id") or str(club_doc.get("_id", club_id))
        filt = {"$or": [
            {"club_id":   resolved_id},
            {"club_id":   club_id},
            {"home_club": resolved_id},
            {"away_club": resolved_id},
        ]}

        total  = await match_stats_collection.count_documents(filt)
        pages  = max(1, math.ceil(total / limit)) if total else 1
        skip   = (page - 1) * limit
        cursor = match_stats_collection.find(filt).sort("match_date", -1).skip(skip).limit(limit)
        docs   = await cursor.to_list(length=limit)
        data   = _ser_list(docs)

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_club_matches] RESULT | total=%d pages=%d returned=%d", total, pages, len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data, "pages": pages, "total": total})

    except Exception as exc:
        logger.error("[get_club_matches] ERROR | club_id=%r | %s\n%s", club_id, exc, traceback.format_exc())
        return JSONResponse(content={"data": [], "pages": 0, "total": 0})


# ============================================================
# SECTION 7 – COMPETITIONS / TRIALS  (competitions.html)
# ============================================================

@router.get("/api/public/competitions")
async def get_competitions(
    request: Request,
    q:       str = Query(default=""),
    type:    str = Query(default="",  alias="type"),
    status:  str = Query(default=""),
    state:   str = Query(default=""),
    page:    int = Query(default=1,  ge=1),
    limit:   int = Query(default=50, ge=1, le=100),
):
    """
    Competitions & trials listing (competitions.html).
    Response: { data: [...], pages: N, total: N }
    Each item: id, title, event_type, status, location, state,
               start_at, organiser, description, registration_fee.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[get_competitions] ENTRY | q=%r type=%r status=%r page=%d limit=%d",
        q, type, status, page, limit,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if competitions_collection is None:
        return JSONResponse(content={"data": [], "pages": 1, "total": 0})

    try:
        clauses = []
        if q:
            clauses.append({"$or": [
                {"title": {"$regex": re.escape(q), "$options": "i"}},
                {"name": {"$regex": re.escape(q), "$options": "i"}},
                {"description": {"$regex": re.escape(q), "$options": "i"}},
            ]})
        if type and type.lower() not in ("", "all"):
            clauses.append({"$or": [
                {"event_type": {"$regex": re.escape(type), "$options": "i"}},
                {"type": {"$regex": re.escape(type), "$options": "i"}},
                {"category": {"$regex": re.escape(type), "$options": "i"}},
            ]})
        if state and state.lower() not in ("", "all"):
            clauses.append({"$or": [
                {"state": {"$regex": re.escape(state), "$options": "i"}},
                {"region": {"$regex": re.escape(state), "$options": "i"}},
                {"location": {"$regex": re.escape(state), "$options": "i"}},
            ]})
        # The CO dashboard writes one of: Published, Ongoing, Draft, Completed.
        # The public page intentionally never exposes Draft competitions.
        # Accept the canonical CO values plus legacy public aliases so records
        # created by older dashboard versions remain discoverable.
        public_statuses = {
            "published": ["published", "Published", "active", "Active", "upcoming", "Upcoming"],
            "ongoing": ["ongoing", "Ongoing", "active", "Active"],
            "active": ["ongoing", "Ongoing", "active", "Active"],
            "upcoming": ["published", "Published", "upcoming", "Upcoming"],
            "completed": ["completed", "Completed", "closed", "Closed", "finished", "Finished"],
        }
        status_key = str(status or "").strip().lower()
        status_values = public_statuses.get(status_key) if status_key else [
            "published", "Published", "ongoing", "Ongoing", "active", "Active",
            "upcoming", "Upcoming", "completed", "Completed",
        ]
        if status_key and not status_values:
            # Unknown status filters must return no records rather than
            # accidentally returning the full public competition catalogue.
            clauses.append({"_id": {"$exists": False}})
        else:
            clauses.append({"status": {"$in": status_values}})
        filt = {"$and": clauses} if clauses else {}

        total  = await competitions_collection.count_documents(filt)
        pages  = max(1, math.ceil(total / limit)) if total else 1
        skip   = (page - 1) * limit
        cursor = competitions_collection.find(filt).sort(
            [("start_at", -1), ("startDate", -1), ("created_at", -1)]
        ).skip(skip).limit(limit)
        docs   = await cursor.to_list(length=limit)
        data = []
        reg_col = database["competition_registrations"] if database is not None else None
        for doc in docs:
            item = _normalise_competition(doc, public=True)

            # Always expose the identifiers/aliases used by the public page and
            # by the reservation workflow.  CO-created records are Mongo
            # ObjectId-backed, while older records may have a string `id`.
            mongo_id = str(doc.get("_id") or "")
            stored_id = str(doc.get("id") or "")
            public_id = stored_id or mongo_id
            item["id"] = public_id
            item["_id"] = mongo_id or public_id
            item["competition_id"] = public_id

            # Preserve the full CO-created field set so the public card and
            # future registration/detail UI never have to guess field names.
            item["category"] = _first_value(doc, "category", "event_type", "type", default="")
            item["event_type"] = _first_value(doc, "event_type", "category", "type", default=item["category"])
            item["type"] = _first_value(doc, "type", "event_type", "category", default=item["category"])
            item["title"] = _first_value(doc, "title", "name", default="Event")
            item["name"] = _first_value(doc, "name", "title", default=item["title"])
            item["start_at"] = _first_value(doc, "start_at", "startDate", "start_date", "date", default="")
            item["end_at"] = _first_value(doc, "end_at", "endDate", "end_date", default="")
            item["deadline"] = _first_value(doc, "deadline", "registration_deadline", default="")
            item["location"] = _first_value(doc, "location", "detailedAddress", "venue", "state", "region", default="Nigeria")
            item["state"] = _first_value(doc, "state", "region", default="")
            item["region"] = _first_value(doc, "region", "state", default="")
            item["venue"] = _first_value(doc, "venue", default="")
            item["country"] = _first_value(doc, "country", default="")
            item["lga"] = _first_value(doc, "lga", default="")
            item["city"] = _first_value(doc, "city", default="")
            item["detailedAddress"] = _first_value(doc, "detailedAddress", "detailed_address", default="")
            item["organiser"] = _first_value(doc, "organiserName", "organiser", "organizer", "contact", default="EnejiStats")
            item["organiserName"] = _first_value(doc, "organiserName", "organiser", "organizer", default=item["organiser"])
            item["organiserPhone"] = _first_value(doc, "organiserPhone", "organizer_phone", default="")
            item["registration_fee"] = _safe_float(_first_value(doc, "registration_fee", "registrationFee", "fee", default=0))
            item["image_url"] = _first_value(doc, "image_url", "image", "banner_url", "bannerUrl", default="")
            item["customFields"] = _first_value(doc, "customFields", "custom_fields", default=[])
            item["custom_fields"] = _first_value(doc, "custom_fields", "customFields", default=item["customFields"])

            if reg_col is not None:
                comp_ids = {x for x in (stored_id, mongo_id, public_id) if x}
                try:
                    registered_count = await _registered_team_count(reg_col, comp_ids)
                    booking_count = await _active_booking_count(reg_col, comp_ids)
                    item["registeredTeams"] = registered_count
                    item["registered_teams"] = registered_count
                    item["registration_count"] = registered_count
                    item["bookedTeams"] = booking_count
                    item["booked_teams"] = booking_count
                    item["reservedTeams"] = booking_count
                    max_teams = _registration_capacity(doc)
                    max_bookings = _booking_capacity(doc)
                    item["maxTeams"] = max_teams
                    item["max_teams"] = max_teams
                    item["maxBookingSlots"] = max_bookings
                    item["max_booking_slots"] = max_bookings
                    item["registrationAvailableSlots"] = None if max_teams <= 0 else max(0, max_teams - registered_count)
                    item["availableSlots"] = item["registrationAvailableSlots"]
                    item["bookingAvailableSlots"] = None if max_bookings <= 0 else max(0, max_bookings - booking_count)
                    item["availableBookingSlots"] = item["bookingAvailableSlots"]
                except Exception:
                    # Keep the stored counters already normalized above if
                    # registration storage is temporarily unavailable.
                    pass
            data.append(_json_safe(item))

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_competitions] RESULT | total=%d pages=%d returned=%d", total, pages, len(data))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"data": data, "pages": pages, "total": total})

    except Exception as exc:
        logger.error("[get_competitions] ERROR | %s\n%s", exc, traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Unable to load competitions catalogue.",
        ) from exc



# ============================================================
# SECTION 7B – PUBLIC COMPETITION TEAM RESERVATION
# ============================================================

def _ensure_aware(value: Any) -> datetime:
    """Return a timezone-aware UTC datetime for stored booking timestamps.

    MongoDB normally returns BSON datetimes as ``datetime`` objects, but older
    records or imported data may contain ISO/date strings.  The booking
    continuation endpoints use this helper before comparing an
    expiry/deadline with ``MongoSerializer.now_utc()`` so a malformed or
    naive timestamp cannot crash the API with a NameError/TypeError.
    """
    if value is None:
        return MongoSerializer.now_utc()

    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).replace(tzinfo=timezone.utc)

    raw = str(value).strip()
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            try:
                return datetime.strptime(raw[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

    # Preserve the existing safety behaviour used by the rest of the public
    # routes: an unusable timestamp is treated as "now" rather than allowing
    # the request to fail because of datetime conversion.
    return MongoSerializer.now_utc()


def _public_competition_id_filter(value: str) -> dict:
    clauses = [{"id": value}, {"competition_id": value}, {"event_id": value}]
    if len(value) == 24:
        try:
            clauses.append({"_id": ObjectId(value)})
        except Exception:
            pass
    return {"$or": clauses}


# ============================================================
# PUBLIC COMPETITION RESERVATION / REGISTRATION WORKFLOW
#
# A reservation is a HOLD only. It never consumes a registration slot.
# Only status="registered" increments registeredTeams / registration_count.
# ============================================================

def _competition_title(comp: dict) -> str:
    return str(comp.get("name") or comp.get("title") or "Competition").strip()


def _competition_deadline(comp: dict):
    """Resolve the CO dashboard's ``deadline`` as an inclusive calendar date.

    CO competition documents store dates such as ``2026-09-28``.  A date-only
    deadline means the whole saved calendar day is available for booking, so
    it is normalized to 23:59:59.999999 UTC instead of midnight at the start
    of the deadline date.  Explicit timestamps retain their supplied time.
    """
    raw = (
        comp.get("deadline")
        or comp.get("registration_deadline")
        or comp.get("registration_close")
        or comp.get("registration_close_date")
        or comp.get("registration_end")
        or comp.get("registration_end_date")
        or comp.get("closing_date")
        or comp.get("close_date")
    )
    if not raw:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return datetime.combine(raw, datetime.max.time()).replace(tzinfo=timezone.utc)
    value = str(raw).strip()
    if not value:
        return None
    # The CO dashboard saves date-only values as YYYY-MM-DD.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            )
        except ValueError:
            return None
    try:
        return _ensure_aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
    except Exception:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
            )
        except Exception:
            return None


def _validate_competition_open(comp: dict) -> None:
    status = str(comp.get("status", "Draft")).strip().lower()
    if status not in {"published", "active", "ongoing", "upcoming", "open"}:
        raise HTTPException(status_code=409, detail="This competition is not currently accepting registrations.")
    deadline = _competition_deadline(comp)
    if deadline and MongoSerializer.now_utc() > deadline:
        raise HTTPException(status_code=409, detail="The registration deadline for this competition has passed.")


def _parse_custom_answers(custom_fields, raw_answers: Optional[str]) -> dict:
    answers = {}
    if raw_answers:
        try:
            parsed = json.loads(raw_answers)
            if isinstance(parsed, dict):
                answers = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            raise HTTPException(status_code=400, detail="Invalid custom registration data.")
    for field in custom_fields if isinstance(custom_fields, list) else []:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or field.get("id") or "").strip()
        if field.get("required") and not str(answers.get(key, "")).strip():
            raise HTTPException(status_code=400, detail=f"{field.get('label') or key} is required.")
    return answers


def _clean_team_registration_fields(team_name, contact_name, contact_phone, contact_email, country, state, lga, city, detailed_address):
    clean = lambda value: str(value or "").strip()
    vals = list(map(clean, (team_name, contact_name, contact_phone, contact_email, country, state, lga, city, detailed_address)))
    team_name, contact_name, contact_phone, contact_email, country, state, lga, city, detailed_address = vals
    if not team_name:
        raise HTTPException(status_code=400, detail="Team name is required.")
    if not contact_name:
        raise HTTPException(status_code=400, detail="Contact person's name is required.")
    if len(re.sub(r"\D", "", contact_phone)) < 7:
        raise HTTPException(status_code=400, detail="A valid contact phone number is required.")
    if not contact_email or "@" not in contact_email or "." not in contact_email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=400, detail="A valid contact email address is required for booking and registration notifications.")
    if not country or not state or not lga or not city or not detailed_address:
        raise HTTPException(status_code=400, detail="Country, state/region, LGA/local area, city/district and detailed address are required.")
    return vals



# ============================================================
# COMPETITION ANTI-ABUSE / DUPLICATE-PREVENTION HELPERS
# ============================================================
# Browser JavaScript cannot reliably obtain a device MAC address, and a
# public website should not try to defeat platform privacy controls to obtain
# one.  Instead we use short-lived pseudonymous signals: HMACs of normalized
# email/phone/team/IP and an HttpOnly browser token.  Raw IP/device identifiers
# are never persisted by this layer.  The HMAC secret should be configured via
# COMPETITION_ANTI_ABUSE_SECRET (or an existing application secret).
_COMPETITION_ABUSE_SECRET = (
    os.getenv("COMPETITION_ANTI_ABUSE_SECRET")
    or os.getenv("JWT_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or secrets.token_hex(32)
).encode("utf-8")
_COMPETITION_ABUSE_COOKIE = "enj_comp_guard"
_COMPETITION_ABUSE_TTL_SECONDS = 24 * 60 * 60
_COMPETITION_BOOKING_WINDOW_SECONDS = 15 * 60
_COMPETITION_BOOKING_MAX_PER_IP = 5
_COMPETITION_BOOKING_MAX_PER_DEVICE = 3
_COMPETITION_BOOKING_MAX_PER_EMAIL = 2
_COMPETITION_BOOKING_MAX_PER_PHONE = 2


def _norm_abuse(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _abuse_hmac(value: Any) -> str:
    raw = _norm_abuse(value).encode("utf-8")
    return hmac.new(_COMPETITION_ABUSE_SECRET, raw, hashlib.sha256).hexdigest()


def _client_ip(request: Request) -> str:
    # Do not trust X-Forwarded-For unless the deployment explicitly places a
    # trusted proxy in front of FastAPI.  request.client.host is the safest
    # default for this module.
    return str(request.client.host if request.client else "unknown")


def _active_statuses() -> list[str]:
    return ["reserved", "payment_pending"]

_COMPETITION_EMAIL_VERIFY_TTL_SECONDS = 10 * 60
_COMPETITION_EMAIL_VERIFY_MAX_ATTEMPTS = 5
_COMPETITION_EMAIL_VERIFY_RESEND_SECONDS = 60
_COMPETITION_BOOKING_MAX_DAYS = 7

def _competition_otp_hash(verification_id: str, otp: str) -> str:
    raw = f"{verification_id}:{str(otp).strip()}".encode("utf-8")
    return hmac.new(_COMPETITION_ABUSE_SECRET, raw, hashlib.sha256).hexdigest()


_COMPETITION_INDEXES_READY = False
_COMPETITION_INDEXES_LOCK = None


async def _ensure_competition_registration_indexes(registrations) -> None:
    """Create database-level duplicate guards. Safe to call repeatedly."""
    global _COMPETITION_INDEXES_READY, _COMPETITION_INDEXES_LOCK
    if _COMPETITION_INDEXES_READY:
        return
    try:
        await registrations.create_index("booking_code", unique=True, name="uq_competition_booking_code")
        active = {"status": {"$in": ["reserved", "payment_pending", "registered"]}}
        await registrations.create_index(
            [("competition_id", 1), ("team_name_lc", 1)],
            unique=True, name="uq_competition_active_team", partialFilterExpression=active,
        )
        await registrations.create_index(
            [("competition_id", 1), ("contact_email_lc", 1)],
            unique=True, name="uq_competition_active_email", partialFilterExpression=active,
        )
        await registrations.create_index(
            [("competition_id", 1), ("contact_phone_lc", 1)],
            unique=True, name="uq_competition_active_phone", partialFilterExpression=active,
        )
        _COMPETITION_INDEXES_READY = True
    except Exception as exc:
        logger.warning("[competition_registration] duplicate-guard index setup failed: %s", exc)


async def _ensure_competition_abuse_indexes() -> None:
    if competition_abuse_collection is None:
        return
    try:
        await competition_abuse_collection.create_index("expires_at", expireAfterSeconds=0)
        await competition_abuse_collection.create_index([("competition_id", 1), ("signal", 1), ("created_at", -1)])
    except Exception as exc:
        logger.warning("[competition_abuse] index setup failed: %s", exc)


async def _ensure_competition_email_verification_indexes() -> None:
    if competition_email_verifications_collection is None:
        return
    try:
        await competition_email_verifications_collection.create_index(
            "expires_at", expireAfterSeconds=0, name="ttl_competition_email_verification"
        )
        await competition_email_verifications_collection.create_index(
            [("competition_id", 1), ("email_lc", 1), ("status", 1)],
            name="idx_competition_email_verification_lookup",
        )
        await competition_email_verifications_collection.create_index(
            "verification_id", unique=True, name="uq_competition_verification_id"
        )
    except Exception as exc:
        logger.warning("[competition_email_verification] index setup failed: %s", exc)


async def _record_abuse_signal(competition_id: str, signal: str, now: datetime) -> None:
    if competition_abuse_collection is None:
        return
    try:
        await competition_abuse_collection.insert_one({
            "competition_id": str(competition_id),
            "signal": str(signal),
            "created_at": now,
            "expires_at": now + timedelta(seconds=_COMPETITION_ABUSE_TTL_SECONDS),
        })
    except Exception as exc:
        logger.warning("[competition_abuse] signal record failed: %s", exc)


async def _count_recent_abuse(competition_id: str, signal: str, since: datetime) -> int:
    if competition_abuse_collection is None:
        return 0
    try:
        return await competition_abuse_collection.count_documents({
            "competition_id": str(competition_id),
            "signal": str(signal),
            "created_at": {"$gte": since},
        })
    except Exception:
        return 0


async def _enforce_competition_anti_abuse(
    request: Request,
    competition_id: str,
    contact_email: str,
    contact_phone: str,
    team_name: str,
) -> str:
    """Return a pseudonymous browser token and reject obvious booking abuse.

    Strong duplicate rules are enforced against the registration collection;
    this helper adds privacy-preserving rate limits and a browser-level guard.
    """
    if competition_abuse_collection is not None:
        await _ensure_competition_abuse_indexes()

    device_token = request.cookies.get(_COMPETITION_ABUSE_COOKIE) or secrets.token_urlsafe(24)
    now = MongoSerializer.now_utc()
    since = now - timedelta(seconds=_COMPETITION_BOOKING_WINDOW_SECONDS)
    comp = str(competition_id)

    signals = {
        "ip:" + _abuse_hmac(_client_ip(request)),
        "device:" + _abuse_hmac(device_token),
    }
    ip_signal = next(s for s in signals if s.startswith("ip:"))
    device_signal = next(s for s in signals if s.startswith("device:"))

    if await _count_recent_abuse(comp, ip_signal, since) >= _COMPETITION_BOOKING_MAX_PER_IP:
        raise HTTPException(status_code=429, detail="Too many booking attempts from this network. Please try again later.")
    if await _count_recent_abuse(comp, device_signal, since) >= _COMPETITION_BOOKING_MAX_PER_DEVICE:
        raise HTTPException(status_code=429, detail="Too many booking attempts from this browser. Please try again later.")

    # Exact contact identifiers are strong duplicate signals.  They are only
    # HMACed for the abuse log and are never stored there in plaintext.
    if contact_email:
        email_signal = "email:" + _abuse_hmac(contact_email)
        if await _count_recent_abuse(comp, email_signal, since) >= _COMPETITION_BOOKING_MAX_PER_EMAIL:
            raise HTTPException(status_code=429, detail="Too many booking attempts for this email address. Please try again later.")
        signals.add(email_signal)
    if contact_phone:
        phone_signal = "phone:" + _abuse_hmac(re.sub(r"\D", "", contact_phone))
        if await _count_recent_abuse(comp, phone_signal, since) >= _COMPETITION_BOOKING_MAX_PER_PHONE:
            raise HTTPException(status_code=429, detail="Too many booking attempts for this phone number. Please try again later.")
        signals.add(phone_signal)

    team_signal = "team:" + _abuse_hmac(team_name)
    signals.add(team_signal)
    for signal in signals:
        await _record_abuse_signal(comp, signal, now)
    return device_token


def _competition_duplicate_filter(comp_key: str, comp_ids: set[str], team_name: str, email: str, phone: str) -> dict:
    """Match active duplicates by strong exact identifiers, not fuzzy guesses."""
    return {
        "competition_id": {"$in": list(comp_ids)},
        "status": {"$nin": ["cancelled", "rejected", "expired"]},
        "$or": [
            {"team_name_lc": _norm_abuse(team_name)},
            {"contact_email_lc": _norm_abuse(email)},
            {"contact_phone_lc": re.sub(r"\D", "", phone or "")},
        ],
    }

def _registration_capacity(comp: dict) -> int:
    return max(0, _safe_int(_first_value(comp, "maxTeams", "max_teams", "participants", default=0)))


def _booking_capacity(comp: dict) -> int:
    # 0 means unlimited booking holds; the actual registration capacity is still enforced.
    return max(0, _safe_int(_first_value(comp, "maxBookingSlots", "max_booking_slots", "booking_limit", default=0)))


async def _active_booking_count(registrations, competition_ids):
    now = MongoSerializer.now_utc()
    return await registrations.count_documents({
        "competition_id": {"$in": list(competition_ids)},
        "status": {"$in": ["reserved", "payment_pending"]},
        "$or": [{"expires_at": {"$gt": now}}, {"expires_at": {"$exists": False}}],
    })

async def _registered_team_count(registrations, competition_ids):
    return await registrations.count_documents({
        "competition_id": {"$in": list(competition_ids)},
        "status": "registered",
    })


async def _send_competition_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email or send_email is None:
        return False
    try:
        result = await send_email(to_email=to_email, subject=subject, body=body)
        return bool(result)
    except Exception as exc:
        logger.warning("[competition_email] delivery failed to %s: %s", to_email, exc)
        return False


def _mask_email(email: str) -> str:
    value = str(email or "").strip()
    if "@" not in value:
        return "your email address"
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        masked = local[:1] + "*" * max(0, len(local) - 1)
    else:
        masked = local[:2] + "*" * max(1, len(local) - 2)
    return masked + "@" + domain


async def _get_public_bank_details() -> dict:
    """Use the same active-bank-details concept as the player payment wizard.
    Installations may store details in config_collection or environment variables.
    """
    doc = None
    if config_collection is not None:
        try:
            doc = await config_collection.find_one({"$or": [
                {"key": "bank_details"}, {"key": "active_bank_details"},
                {"type": "bank_details"}, {"slug": "bank_details"},
                {"name": "bank_details"},
            ]})
        except Exception:
            doc = None
    data = (doc or {}).get("data") if isinstance((doc or {}).get("data"), dict) else (doc or {})
    return {
        "bankName": data.get("bankName") or data.get("bank_name") or os.getenv("BANK_NAME", ""),
        "accountName": data.get("accountName") or data.get("account_name") or os.getenv("BANK_ACCOUNT_NAME", ""),
        "accountNumber": data.get("accountNumber") or data.get("account_number") or os.getenv("BANK_ACCOUNT_NUMBER", ""),
    }


@router.post("/api/public/competitions/{comp_id}/register")
async def reserve_team_slot(
    comp_id: str,
    request: Request,
    team_name: str = Form(...),
    contact_name: str = Form(...),
    contact_phone: str = Form(...),
    contact_email: str = Form(...),
    country: str = Form(...),
    state: str = Form(...),
    lga: str = Form(...),
    city: str = Form(...),
    detailed_address: str = Form(...),
    gps_lat: Optional[float] = Form(default=None),
    gps_lng: Optional[float] = Form(default=None),
    custom_answers: Optional[str] = Form(default=None),
):
    """Create a booking hold. It does NOT consume a registration slot."""
    if competitions_collection is None or database is None:
        raise HTTPException(status_code=503, detail="Competition registration is temporarily unavailable.")
    vals = _clean_team_registration_fields(team_name, contact_name, contact_phone, contact_email, country, state, lga, city, detailed_address)
    team_name, contact_name, contact_phone, contact_email, country, state, lga, city, detailed_address = vals
    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id))
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    _validate_competition_open(competition)
    custom_fields = competition.get("customFields", competition.get("custom_fields", []))
    answers = _parse_custom_answers(custom_fields, custom_answers)
    registrations = database["competition_registrations"]
    await _ensure_competition_registration_indexes(registrations)
    comp_key = str(competition.get("id") or competition.get("_id") or comp_id)
    comp_ids = {comp_key, str(comp_id), str(competition.get("_id", comp_key))}
    # Privacy-preserving rate limit before any booking/verification record is created.
    device_token = await _enforce_competition_anti_abuse(request, comp_key, contact_email, contact_phone, team_name)
    duplicate_filter = _competition_duplicate_filter(comp_key, comp_ids, team_name, contact_email, contact_phone)
    existing = await registrations.find_one(duplicate_filter)
    if existing:
        if existing.get("status") == "email_verification_pending":
            raise HTTPException(
                status_code=409,
                detail="This team already has a pending email verification. Enter the verification code sent to the email address, or wait before requesting another code.",
            )
        if existing.get("status") in {"reserved", "payment_pending"} and existing.get("booking_code"):
            return JSONResponse({"success": True, "existing": True, "message": "This team already has an active booking. Use the booking code sent by email to continue.", "registration": _json_safe(existing)})
        raise HTTPException(status_code=409, detail="This team is already registered for this competition.")

    # IMPORTANT: email verification happens BEFORE a booking hold exists.
    # Therefore no booking capacity is checked, no bookedTeams counter is
    # incremented, and no registration slot is locked at this stage.
    now = MongoSerializer.now_utc()
    verification_id = uuid.uuid4().hex
    otp = f"{secrets.randbelow(1000000):06d}"
    expires_at = now + timedelta(seconds=_COMPETITION_EMAIL_VERIFY_TTL_SECONDS)
    pending_doc = {
        "id": uuid.uuid4().hex,
        "registration_id": uuid.uuid4().hex,
        "verification_id": verification_id,
        "competition_id": comp_key,
        "competition_title": _competition_title(competition),
        "team_name": team_name,
        "team_name_lc": _norm_abuse(team_name),
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "contact_phone_lc": re.sub(r"\D", "", contact_phone),
        "contact_email": contact_email,
        "contact_email_lc": _norm_abuse(contact_email),
        "anti_abuse_device": _abuse_hmac(device_token),
        "country": country, "state": state, "lga": lga, "city": city,
        "detailed_address": detailed_address,
        "gps_lat": gps_lat, "gps_lng": gps_lng,
        "custom_answers": answers,
        "status": "email_verification_pending",
        "verification_otp_hash": _competition_otp_hash(verification_id, otp),
        "verification_attempts": 0,
        "verification_sent_at": now,
        "verification_expires_at": expires_at,
        "created_at": now, "updated_at": now,
        "expires_at": expires_at,
    }
    try:
        await registrations.insert_one(pending_doc)
    except Exception as exc:
        logger.warning("[competition_registration] pending verification insert failed: %s", exc)
        raise HTTPException(status_code=409, detail="A booking verification request already exists for these details. Please check your email.")

    # The central EnejiStats/Brevo sender is used; the OTP itself is never
    # stored in plaintext.
    sent = await _send_competition_email(
        contact_email,
        f"EnejiStats — Verify your email for {pending_doc['competition_title']}",
        f"Hello {contact_name},\n\nTo continue your {pending_doc['competition_title']} booking request, enter this verification code on the competition page:\n\n{otp}\n\nThis code expires in 10 minutes and can only be used for this booking request.\n\nNo competition booking slot has been locked yet. A booking hold is created only after this email address is successfully verified.\n\nIf you did not request this, you can safely ignore this email.\n\nEnejiStats",
    )
    if not sent:
        await registrations.delete_one({"_id": pending_doc.get("_id"), "status": "email_verification_pending"})
        raise HTTPException(status_code=503, detail="We could not send the verification email. Please try again shortly.")

    response = JSONResponse({
        "success": True,
        "verification_required": True,
        "message": "A verification code has been sent to your email. No booking slot has been locked yet.",
        "verification_id": verification_id,
        "email_hint": _mask_email(contact_email),
    })
    response.set_cookie(
        key=_COMPETITION_ABUSE_COOKIE, value=device_token, max_age=_COMPETITION_ABUSE_TTL_SECONDS,
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return response


@router.post("/api/public/competitions/{comp_id}/verify-booking-email")
async def verify_competition_booking_email(
    comp_id: str,
    request: Request,
    verification_id: str = Form(...),
    otp: str = Form(...),
):
    """Verify the booking email and ONLY THEN create/lock the booking hold."""
    if database is None or competitions_collection is None:
        raise HTTPException(status_code=503, detail="Competition email verification is temporarily unavailable.")
    verification_id = str(verification_id or "").strip()
    otp = str(otp or "").strip()
    if not verification_id or not re.fullmatch(r"\d{6}", otp):
        raise HTTPException(status_code=400, detail="Enter the 6-digit verification code sent to your email.")

    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id))
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    _validate_competition_open(competition)
    await _ensure_competition_registration_indexes(database["competition_registrations"])
    col = database["competition_registrations"]
    vdoc = await col.find_one({"verification_id": verification_id, "competition_id": str(competition.get("id") or competition.get("_id") or comp_id), "status": "email_verification_pending"})
    if not vdoc:
        raise HTTPException(status_code=404, detail="Verification request not found or already completed. Please start the booking again.")
    now = MongoSerializer.now_utc()
    if vdoc.get("verification_expires_at") and _ensure_aware(vdoc["verification_expires_at"]) < now:
        await col.update_one({"_id": vdoc["_id"]}, {"$set": {"status": "expired", "updated_at": now}})
        raise HTTPException(status_code=410, detail="This verification code has expired. Please start the booking again.")
    attempts = int(vdoc.get("verification_attempts", 0) or 0)
    if attempts >= _COMPETITION_EMAIL_VERIFY_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many incorrect verification attempts. Please start the booking again.")
    if not hmac.compare_digest(str(vdoc.get("verification_otp_hash", "")), _competition_otp_hash(verification_id, otp)):
        await col.update_one({"_id": vdoc["_id"]}, {"$inc": {"verification_attempts": 1}, "$set": {"updated_at": now}})
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    # Atomically claim the pending verification request before touching
    # competition capacity. This prevents two simultaneous requests using
    # the same valid OTP from both creating a booking hold.
    claimed = await col.find_one_and_update(
        {
            "_id": vdoc["_id"],
            "status": "email_verification_pending",
            "verification_otp_hash": vdoc.get("verification_otp_hash", ""),
        },
        {"$set": {"status": "verification_processing", "updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        raise HTTPException(status_code=409, detail="This verification request is already being processed or has already been completed.")
    vdoc = claimed

    comp_key = str(competition.get("id") or competition.get("_id") or comp_id)
    comp_ids = {comp_key, str(comp_id), str(competition.get("_id", comp_key))}
    # Re-check all duplicate signals after verification; the request may have
    # been waiting while another booking was created.
    existing = await col.find_one(_competition_duplicate_filter(comp_key, comp_ids, vdoc.get("team_name", ""), vdoc.get("contact_email", ""), vdoc.get("contact_phone", "")))
    if existing and existing.get("_id") != vdoc.get("_id"):
        await col.update_one({"_id": vdoc["_id"], "status": "verification_processing"}, {"$set": {"status": "email_verification_pending", "updated_at": MongoSerializer.now_utc()}})
        raise HTTPException(status_code=409, detail="This team, email address, or phone number is already registered or booked for this competition.")

    max_bookings = _booking_capacity(competition)
    # Atomically reserve a booking counter only after email verification.
    if max_bookings > 0:
        capacity_filter = _public_competition_id_filter(comp_id)
        capacity_filter["$or"] = [
            {"bookedTeams": {"$lt": max_bookings}},
            {"bookedTeams": {"$exists": False}},
        ]
        updated_comp = await competitions_collection.find_one_and_update(
            capacity_filter,
            {"$inc": {"bookedTeams": 1}, "$set": {"updated_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if not updated_comp:
            await col.update_one({"_id": vdoc["_id"], "status": "verification_processing"}, {"$set": {"status": "email_verification_pending", "updated_at": MongoSerializer.now_utc()}})
            raise HTTPException(status_code=409, detail="All booking holds are currently occupied. Please try again later.")
    else:
        await competitions_collection.update_one(_public_competition_id_filter(comp_id), {"$inc": {"bookedTeams": 1}, "$set": {"updated_at": now}})

    booking_code = "ENJ-" + secrets.token_hex(5).upper()
    registration_id = vdoc.get("registration_id") or uuid.uuid4().hex
    deadline = _competition_deadline(competition)
    booking_window = timedelta(days=_COMPETITION_BOOKING_MAX_DAYS)
    default_expiry = now + booking_window
    if deadline and deadline > now:
        expires_at = min(default_expiry, deadline)
    elif deadline and deadline <= now:
        raise HTTPException(status_code=409, detail="The registration closing date has passed; a booking cannot be created.")
    else:
        expires_at = default_expiry
    final_doc = {
        **{k: v for k, v in vdoc.items() if k not in {"_id", "verification_id", "verification_otp_hash", "verification_attempts", "verification_sent_at", "verification_expires_at", "expires_at"}},
        "id": registration_id, "registration_id": registration_id,
        "competition_id": comp_key, "competition_title": _competition_title(competition),
        "status": "reserved", "registration_status": "pending", "registered": False,
        "payment_status": "unpaid", "booking_code": booking_code,
        "created_at": vdoc.get("created_at", now), "updated_at": now, "expires_at": expires_at,
        "booking_duration_days": max(0, min(_COMPETITION_BOOKING_MAX_DAYS, math.ceil((expires_at - now).total_seconds() / 86400))),
        "email_verified_at": now, "email_verified": True,
        # Snapshot the CO-authored competition fields used by the booking so
        # a later dashboard edit cannot make the booking lose its original
        # competition context. The live competition document remains the
        # authoritative source for capacity/deadline validation.
        "competition_snapshot": {
            "id": comp_key,
            "name": _competition_title(competition),
            "category": _first_value(competition, "category", "event_type", "type", default=""),
            "status": _first_value(competition, "status", default=""),
            "startDate": _first_value(competition, "startDate", "start_date", "start_at", default=""),
            "endDate": _first_value(competition, "endDate", "end_date", "end_at", default=""),
            "deadline": _first_value(competition, "deadline", "registration_deadline", default=""),
            "registration_fee": _safe_float(_first_value(competition, "registration_fee", "registrationFee", "fee", default=0)),
            "region": _first_value(competition, "region", "state", default=""),
            "description": _first_value(competition, "description", default=""),
            "prize": _first_value(competition, "prize", default=""),
            "contact": _first_value(competition, "contact", default=""),
            "rules": _first_value(competition, "rules", default=""),
            "eligibleTypes": _first_value(competition, "eligibleTypes", "eligible_types", default=""),
            "eligibleClubs": _first_value(competition, "eligibleClubs", "eligible_clubs", default=""),
            "ageGroup": _first_value(competition, "ageGroup", "age_group", default=""),
            "city": _first_value(competition, "city", default=""),
            "country": _first_value(competition, "country", default=""),
            "state": _first_value(competition, "state", default=""),
            "lga": _first_value(competition, "lga", default=""),
            "venue": _first_value(competition, "venue", default=""),
            "venueId": _first_value(competition, "venueId", "venue_id", default=""),
            "detailedAddress": _first_value(competition, "detailedAddress", "detailed_address", default=""),
            "organiserName": _first_value(competition, "organiserName", "organiser", "organizer", default=""),
            "organiserPhone": _first_value(competition, "organiserPhone", "organizer_phone", default=""),
            "latitude": competition.get("latitude"),
            "longitude": competition.get("longitude"),
            "maxTeams": _registration_capacity(competition),
            "maxBookingSlots": _booking_capacity(competition),
            "customFields": competition.get("customFields", competition.get("custom_fields", [])),
        },
    }
    try:
        await col.replace_one({"_id": vdoc["_id"]}, final_doc, upsert=False)
    except Exception:
        # Release the slot if the final persistence failed.
        await competitions_collection.update_one(
            {"$and": [_public_competition_id_filter(comp_id), {"bookedTeams": {"$gt": 0}}]},
            {"$inc": {"bookedTeams": -1}, "$set": {"updated_at": MongoSerializer.now_utc()}},
        )
        raise HTTPException(status_code=500, detail="The booking could not be finalized. Please try again.")
    await _send_competition_email(
        final_doc.get("contact_email", ""),
        f"EnejiStats — {final_doc['competition_title']} booking confirmed ({booking_code})",
        f"Hello {final_doc.get('contact_name','')},\n\nYour email has been verified and your booking hold for {final_doc['competition_title']} is now active.\n\nBooking code: {booking_code}\nTeam: {final_doc.get('team_name')}\nBooking hold expires: {expires_at.isoformat()}\n\nThis booking hold is now active, but the competition registration slot is not consumed until final registration is completed and, where applicable, payment is approved.\n\nEnejiStats",
    )
    response = JSONResponse({"success": True, "verified": True, "message": "Email verified. Your booking hold is now active.", "registration": _json_safe(final_doc)})
    device_token = request.cookies.get(_COMPETITION_ABUSE_COOKIE) or secrets.token_urlsafe(24)
    response.set_cookie(key=_COMPETITION_ABUSE_COOKIE, value=device_token, max_age=_COMPETITION_ABUSE_TTL_SECONDS, httponly=True, secure=True, samesite="lax", path="/")
    return response


@router.post("/api/public/competitions/continue-booking")
async def continue_competition_booking_global(
    request: Request,
    booking_code: str = Form(...),
    contact_email: Optional[str] = Form(default=None),
):
    """Resume a booking using only the emailed booking code."""
    del request
    if database is None or competitions_collection is None:
        raise HTTPException(status_code=503, detail="Competition registration is temporarily unavailable.")
    code = str(booking_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Booking code is required.")
    col = database["competition_registrations"]
    doc = await col.find_one({"booking_code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking code not found.")
    if contact_email and str(doc.get("contact_email", "")).lower() != str(contact_email).strip().lower():
        raise HTTPException(status_code=403, detail="The email address does not match this booking.")
    comp = await competitions_collection.find_one(_public_competition_id_filter(str(doc.get("competition_id", ""))))
    if not comp:
        raise HTTPException(status_code=404, detail="The competition linked to this booking could not be found.")
    if doc.get("status") != "registered" and doc.get("expires_at") and _ensure_aware(doc.get("expires_at")) < MongoSerializer.now_utc():
        await col.update_one({"_id": doc["_id"]}, {"$set": {"status": "expired", "updated_at": MongoSerializer.now_utc()}})
        await competitions_collection.update_one(
            {"$and": [_public_competition_id_filter(str(doc.get("competition_id", ""))), {"bookedTeams": {"$gt": 0}}]},
            {"$inc": {"bookedTeams": -1}, "$set": {"updated_at": MongoSerializer.now_utc()}},
        )
        raise HTTPException(status_code=410, detail="This booking has expired. Please create a new booking.")
    return JSONResponse({"success": True, "registration": _json_safe(doc), "competition": _normalise_competition(comp, public=True)})


@router.post("/api/public/competitions/{comp_id}/continue")
async def continue_competition_booking(
    comp_id: str,
    request: Request,
    booking_code: str = Form(...),
    contact_email: Optional[str] = Form(default=None),
):
    del request
    if database is None:
        raise HTTPException(status_code=503, detail="Competition registration is temporarily unavailable.")
    code = str(booking_code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Booking code is required.")
    col = database["competition_registrations"]
    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id)) if competitions_collection is not None else None
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    filt = {"booking_code": code, "competition_id": {"$in": [str(competition.get("id") or competition.get("_id") or comp_id), comp_id, str(competition.get("_id", comp_id))]}}
    doc = await col.find_one(filt)
    if not doc:
        raise HTTPException(status_code=404, detail="Booking code not found for this competition.")
    if contact_email and str(doc.get("contact_email", "")).lower() != str(contact_email).strip().lower():
        raise HTTPException(status_code=403, detail="The email address does not match this booking.")
    if doc.get("status") == "registered":
        return JSONResponse({"success": True, "already_registered": True, "registration": _json_safe(doc)})
    if doc.get("expires_at") and _ensure_aware(doc.get("expires_at")) < MongoSerializer.now_utc():
        await col.update_one({"_id": doc["_id"]}, {"$set": {"status": "expired", "updated_at": MongoSerializer.now_utc()}})
        await competitions_collection.update_one(
            {"$and": [_public_competition_id_filter(comp_id), {"bookedTeams": {"$gt": 0}}]},
            {"$inc": {"bookedTeams": -1}, "$set": {"updated_at": MongoSerializer.now_utc()}},
        )
        raise HTTPException(status_code=410, detail="This booking has expired. Please create a new booking.")
    return JSONResponse({"success": True, "registration": _json_safe(doc), "competition": _normalise_competition(competition, public=True)})


@router.post("/api/public/competitions/{comp_id}/complete-registration")
async def complete_competition_registration(
    comp_id: str,
    request: Request,
    booking_code: str = Form(...),
    custom_answers: Optional[str] = Form(default=None),
):
    del request
    if database is None or competitions_collection is None:
        raise HTTPException(status_code=503, detail="Competition registration is temporarily unavailable.")
    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id))
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    _validate_competition_open(competition)
    col = database["competition_registrations"]
    code = str(booking_code or "").strip().upper()
    doc = await col.find_one({"booking_code": code, "competition_id": {"$in": [str(competition.get("id") or competition.get("_id") or comp_id), comp_id, str(competition.get("_id", comp_id))]}})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking code not found.")
    if doc.get("status") == "registered":
        return JSONResponse({"success": True, "message": "Team is already registered.", "registration": _json_safe(doc)})
    if doc.get("expires_at") and _ensure_aware(doc.get("expires_at")) < MongoSerializer.now_utc():
        raise HTTPException(status_code=410, detail="This booking has expired. Please create a new booking.")
    answers = _parse_custom_answers(competition.get("customFields", competition.get("custom_fields", [])), custom_answers)
    # Booking codes are unique, but also re-check strong identity fields so an
    # attacker cannot create several bookings with different team names.
    comp_ids = {str(competition.get("id") or competition.get("_id") or comp_id), str(comp_id), str(competition.get("_id", comp_id))}
    duplicate = await col.find_one({
        "competition_id": {"$in": list(comp_ids)},
        "_id": {"$ne": doc["_id"]},
        "status": {"$nin": ["cancelled", "rejected", "expired"]},
        "$or": [
            {"contact_email_lc": _norm_abuse(doc.get("contact_email"))},
            {"contact_phone_lc": re.sub(r"\D", "", str(doc.get("contact_phone", "")))},
        ],
    })
    if duplicate:
        raise HTTPException(status_code=409, detail="An active booking already exists for this contact email or phone number in this competition.")
    if answers:
        await col.update_one({"_id": doc["_id"]}, {"$set": {"custom_answers": answers, "updated_at": MongoSerializer.now_utc()}})
        doc["custom_answers"] = answers
    fee = _safe_float(competition.get("registration_fee", 0))
    if fee > 0 and str(doc.get("payment_status", "unpaid")) not in {"verified", "approved", "paid"}:
        raise HTTPException(status_code=409, detail="Payment is required before this team can be registered. Use the bank-transfer payment wizard and submit the payment receipt.")
    max_teams = _registration_capacity(competition)
    registered = await _registered_team_count(col, {str(competition.get("id") or competition.get("_id") or comp_id), comp_id, str(competition.get("_id", comp_id))})
    if max_teams > 0 and registered >= max_teams:
        raise HTTPException(status_code=409, detail="All registration slots have now been filled.")
    await competitions_collection.update_one(_public_competition_id_filter(comp_id), {"$set": {"registeredTeams": registered, "registration_count": registered}})
    now = MongoSerializer.now_utc()
    capacity_filter = _public_competition_id_filter(comp_id)
    if max_teams > 0:
        capacity_filter = {"$and": [
            _public_competition_id_filter(comp_id),
            {"$or": [{"registeredTeams": {"$lt": max_teams}}, {"registeredTeams": {"$exists": False}}]},
        ]}
    updated = await competitions_collection.find_one_and_update(
        capacity_filter,
        {"$inc": {"registeredTeams": 1, "registration_count": 1}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="All registration slots have now been filled.")
    result = await col.update_one({"_id": doc["_id"], "status": {"$ne": "registered"}}, {"$set": {"status": "registered", "registration_status": "registered", "registered": True, "registered_at": now, "updated_at": now}})
    if result.modified_count == 0:
        await competitions_collection.update_one(_public_competition_id_filter(comp_id), {"$inc": {"registeredTeams": -1, "registration_count": -1}})
        raise HTTPException(status_code=409, detail="This booking has already been registered.")
    await competitions_collection.update_one(_public_competition_id_filter(comp_id), {"$inc": {"bookedTeams": -1}, "$set": {"updated_at": now}})
    doc.update({"status": "registered", "registration_status": "registered", "registered": True, "registered_at": now})
    await _send_competition_email(doc.get("contact_email", ""), f"EnejiStats — {doc.get('competition_title')} registration confirmed", f"Hello {doc.get('contact_name','')},\n\nYour team {doc.get('team_name')} is now fully registered for {doc.get('competition_title')}.\n\nBooking code: {code}\nRegistration status: CONFIRMED\n\nThank you,\nEnejiStats")
    return JSONResponse({"success": True, "message": "Team registration completed successfully.", "registration": _json_safe(doc), "remaining_registration_slots": None if max_teams <= 0 else max(0, max_teams - (registered + 1))})


@router.post("/api/public/competitions/{comp_id}/payment/intent")
async def create_competition_payment_intent(
    comp_id: str,
    request: Request,
    booking_code: str = Form(...),
    custom_answers: Optional[str] = Form(default=None),
):
    del request
    if database is None or competitions_collection is None:
        raise HTTPException(status_code=503, detail="Payment is temporarily unavailable.")
    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id))
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    _validate_competition_open(competition)
    col = database["competition_registrations"]
    code = str(booking_code or "").strip().upper()
    doc = await col.find_one({"booking_code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking code not found.")
    answers = _parse_custom_answers(competition.get("customFields", competition.get("custom_fields", [])), custom_answers)
    fee = _safe_float(competition.get("registration_fee", 0))
    if fee <= 0:
        raise HTTPException(status_code=400, detail="This competition has no registration fee.")
    bank = await _get_public_bank_details()
    if not bank.get("bankName") or not bank.get("accountName") or not bank.get("accountNumber"):
        raise HTTPException(status_code=503, detail="Bank transfer details are not configured yet. Please contact the competition organiser.")
    intent_id = uuid.uuid4().hex
    reference = "COMP-" + secrets.token_hex(5).upper()
    now = MongoSerializer.now_utc()
    payment_update = {"payment_intent_id": intent_id, "payment_reference": reference, "payment_status": "awaiting_transfer", "payment_amount": fee, "updated_at": now}
    if answers:
        payment_update["custom_answers"] = answers
    await col.update_one({"_id": doc["_id"]}, {"$set": payment_update})
    return JSONResponse({"success": True, "intentId": intent_id, "reference": reference, "amount": fee, "currency": "NGN", "bankDetails": bank})


@router.post("/api/public/competitions/{comp_id}/payment/receipt")
async def upload_competition_payment_receipt(
    comp_id: str,
    request: Request,
    booking_code: str = Form(...),
    receiptFile: UploadFile = File(...),
):
    if database is None or competitions_collection is None:
        raise HTTPException(status_code=503, detail="Payment is temporarily unavailable.")
    competition = await competitions_collection.find_one(_public_competition_id_filter(comp_id))
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found.")
    code = str(booking_code or "").strip().upper()
    col = database["competition_registrations"]
    doc = await col.find_one({"booking_code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking code not found.")
    if not receiptFile or not receiptFile.filename:
        raise HTTPException(status_code=400, detail="Payment receipt is required.")
    ext = (receiptFile.filename.rsplit(".", 1)[-1] if "." in receiptFile.filename else "").lower()
    if ext not in {"pdf", "png", "jpg", "jpeg"}:
        raise HTTPException(status_code=415, detail="Only PDF, PNG, JPG and JPEG receipts are allowed.")
    content = await receiptFile.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Receipt must be under 10 MB.")
    receipt_url = ""
    if upload_to_cloudinary:
        try:
            receipt_url = await upload_to_cloudinary(content, filename=receiptFile.filename, folder="competition_payment_receipts", resource_type="auto")
        except TypeError:
            receipt_url = await upload_to_cloudinary(content, filename=receiptFile.filename, folder="competition_payment_receipts")
        except Exception as exc:
            logger.error("[competition_receipt] Cloudinary upload failed: %s", exc)
            raise HTTPException(status_code=500, detail="Could not store the payment receipt.")
    else:
        raise HTTPException(status_code=503, detail="Receipt storage is not configured.")
    now = MongoSerializer.now_utc()
    await col.update_one({"_id": doc["_id"]}, {"$set": {"payment_status": "pending_review", "status": "payment_pending", "receipt_url": receipt_url, "receipt_filename": receiptFile.filename, "receipt_submitted_at": now, "updated_at": now}})
    admin_dest = ADMIN_EMAIL or "enejistats@gmail.com"
    await _send_competition_email(admin_dest, f"[Competition Payment Review] {competition.get('name') or competition.get('title')} — {code}", f"A team has submitted bank-transfer payment evidence.\n\nCompetition: {_competition_title(competition)}\nTeam: {doc.get('team_name')}\nContact: {doc.get('contact_name')}\nEmail: {doc.get('contact_email')}\nPhone: {doc.get('contact_phone')}\nBooking code: {code}\nPayment reference: {doc.get('payment_reference','—')}\nAmount: ₦{_safe_float(doc.get('payment_amount', competition.get('registration_fee', 0))):,.2f}\nReceipt: {receipt_url}\n\nPlease review the evidence and register/approve the team from the CO dashboard.")
    await _send_competition_email(doc.get("contact_email", ""), f"EnejiStats — payment evidence received ({code})", f"Hello {doc.get('contact_name','')},\n\nWe received the payment evidence for {doc.get('competition_title')}.\n\nBooking code: {code}\nPayment reference: {doc.get('payment_reference','—')}\nStatus: Payment under review\n\nYour registration slot is not counted as consumed until the payment is approved and the team is registered.\n\nEnejiStats")
    return JSONResponse({"success": True, "status": "pending_review", "reference": doc.get("payment_reference", ""), "message": "Payment receipt submitted. The evidence has been sent to the admin for review."})


# Backward-compatible alias for older frontend callers.
register_team_for_competition = reserve_team_slot


# ============================================================
# SECTION 8 – COMMUNICATIONS OFFICER CONTENT API
# ============================================================

async def _count(collection, filt=None) -> int:
    if collection is None:
        return 0
    try:
        return await collection.count_documents(filt or {})
    except Exception:
        logger.exception("[co] count failed")
        return 0


def _mongo_id_filter(value: str) -> dict:
    clauses = [{"id": value}, {"competition_id": value}, {"event_id": value}]
    if len(value) == 24:
        try:
            clauses.append({"_id": ObjectId(value)})
        except Exception:
            pass
    return {"$or": clauses}


@router.post("/api/public/contact")
async def submit_contact_form(
    request:     Request,
    fullName:    str           = Form(...),
    email:       str           = Form(...),
    subject:     str           = Form(...),
    message:     str           = Form(...),
    phone:       Optional[str] = Form(default=None),
    accountId:   Optional[str] = Form(default=None),
    replyMethod: Optional[str] = Form(default="Email"),
    honeypot:    Optional[str] = Form(default=None),
    attachment:  Optional[UploadFile] = None,
):
    """
    Contact / support form submission (contact.html).
    Accepts multipart/form-data. Includes honeypot spam detection.
    Stores inquiry in contact_collection and sends notification email.
    Response: { success: true, referenceId: "XXXXXXXX" }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[submit_contact_form] ENTRY | name=%r email=%r subject=%r "
        "reply_method=%r has_attachment=%r",
        fullName, email, subject, replyMethod, attachment is not None,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    # Honeypot check
    if honeypot:
        logger.warning("[submit_contact_form] HONEYPOT triggered | email=%r", email)
        return JSONResponse(content={"success": True, "referenceId": _gen_ref()})

    # Basic validation
    if not fullName or not fullName.strip():
        raise HTTPException(status_code=422, detail="Full name is required")
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Valid email is required")
    if not subject or not subject.strip():
        raise HTTPException(status_code=422, detail="Subject is required")
    if not message or not message.strip():
        raise HTTPException(status_code=422, detail="Message is required")
    if len(message) > 2000:
        raise HTTPException(status_code=422, detail="Message must be under 2000 characters")

    reference_id = _gen_ref()

    try:
        # Handle optional file attachment
        attachment_url = None
        if attachment and attachment.filename:
            # ── DEBUG BLOCK START ──────────────────────────────────────────
            logger.debug(
                "[submit_contact_form] ATTACHMENT | filename=%r size_hint=%r",
                attachment.filename, attachment.size,
            )
            # ── DEBUG BLOCK END ────────────────────────────────────────────
            content = await attachment.read()
            if len(content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Attachment must be ≤ 5MB")
            try:
                attachment_url = await upload_to_cloudinary(
                    content,
                    filename=attachment.filename or "attachment",
                    folder="contact_attachments",
                )
            except Exception as e:
                logger.warning("[submit_contact_form] Cloudinary upload failed: %s", e)

        record = {
            "reference_id":  reference_id,
            "full_name":     fullName.strip(),
            "email":         email.strip().lower(),
            "phone":         phone or "",
            "account_id":    accountId or "",
            "subject":       subject.strip(),
            "message":       message.strip(),
            "reply_method":  replyMethod or "Email",
            "attachment_url": attachment_url,
            "status":        "open",
            "created_at":    _now_iso(),
            "source":        "public_contact_form",
        }

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[submit_contact_form] INSERTING | reference_id=%r", reference_id)
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        if contact_collection is not None:
            await contact_collection.insert_one(record.copy())

        # Send notification email to admin
        admin_dest = ADMIN_EMAIL or "enejistats@gmail.com"
        if send_email is not None:
            email_body = (
                f"New contact form submission\n\n"
                f"Reference: #{reference_id}\n"
                f"From:      {fullName} <{email}>\n"
                f"Phone:     {phone or '—'}\n"
                f"Account:   {accountId or '—'}\n"
                f"Subject:   {subject}\n"
                f"Reply via: {replyMethod}\n\n"
                f"Message:\n{message}\n\n"
                f"{'Attachment: ' + attachment_url if attachment_url else 'No attachment'}"
            )
            try:
                await send_email(
                    to_email=admin_dest,
                    subject=f"[EnejiStats Contact] {subject} — #{reference_id}",
                    body=email_body,
                )
            except Exception as e:
                logger.warning("[submit_contact_form] Email send failed: %s", e)

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[submit_contact_form] SUCCESS | reference_id=%r", reference_id)
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content={"success": True, "referenceId": reference_id})

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[submit_contact_form] ERROR | %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to submit contact form. Please try again.")


def _gen_ref() -> str:
    """Generate a short uppercase alphanumeric reference ID."""
    return secrets.token_hex(4).upper()


# ============================================================
# SECTION 9 – PRICING CONFIG  (pricing.html)
# ============================================================

@router.get("/api/config/pricing")
async def get_public_pricing_config(request: Request, country: str = Query("NG", min_length=2, max_length=2)):
    """
    Canonical public pricing payload for pricing.html.

    Prices are resolved through pricing_module.PricingService so the public
    pricing page and the authenticated/admin pricing APIs share the same
    database-backed source of truth, including country multipliers.
    Top-up packages remain sourced from the existing public top-up catalogue.
    """
    try:
        from pricing_module import (
            pricing_service, DEFAULT_SUBSCRIPTION_PLANS, TOKEN_PACKAGES,
            CANONICAL_LEVELS, PLAYER_LEVELS_CONFIG, CANONICAL_PLAN_KEYS,
        )

        country_code = (country or "NG").upper().strip()
        multiplier = pricing_service.get_country_multiplier(country_code)

        subscription_plans: Dict[str, Any] = {}
        for role in DEFAULT_SUBSCRIPTION_PLANS:
            if role in ("player", "club"):
                subscription_plans[role] = {}
                for level in CANONICAL_LEVELS:
                    subscription_plans[role][level] = pricing_service.get_subscription_plans(
                        role=role, level=level, country_code=country_code
                    )
            else:
                subscription_plans[role] = pricing_service.get_subscription_plans(
                    role=role, country_code=country_code
                )

        token_packages: Dict[str, Any] = {}
        for role in TOKEN_PACKAGES:
            if role in ("player", "club"):
                token_packages[role] = {}
                for level in CANONICAL_LEVELS:
                    token_packages[role][level] = pricing_service.get_token_packages(
                        role=role, level=level, country_code=country_code
                    )
            else:
                token_packages[role] = pricing_service.get_token_packages(
                    role=role, country_code=country_code
                )

        topups = await _load_topup_packages()
        return JSONResponse(content={
            "country": country_code,
            "country_multiplier": multiplier,
            "subscription_plans": subscription_plans,
            "token_packages": token_packages,
            "topup_packages": topups,
            "levels": PLAYER_LEVELS_CONFIG,
            "canonical_levels": CANONICAL_LEVELS,
            "plan_keys": CANONICAL_PLAN_KEYS,
        })
    except Exception as exc:
        logger.error("[get_public_pricing_config] ERROR | %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unable to load pricing configuration")


@router.get("/api/config/subscriptions")
async def get_subscription_plans(request: Request):
    """
    Subscription / pricing plans for pricing.html.
    Response: grouped by role { player: [...], club: [...], scout: [...], agent: [...] }
    or a flat array – the frontend handles both.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_subscription_plans] ENTRY")
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        plans = await _load_config_plans()

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[get_subscription_plans] RESULT | type=%s keys=%r",
            type(plans).__name__,
            list(plans.keys()) if isinstance(plans, dict) else len(plans),
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=plans)

    except Exception as exc:
        logger.error("[get_subscription_plans] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content=_default_plans())


@router.get("/api/config/tokens")
async def get_token_packages(request: Request):
    """
    Token purchase packages for pricing.html.
    Response: array of { id, tokens/amount, price, bonus_tokens/bonus }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_token_packages] ENTRY")
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        packages = await _load_token_packages()

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_token_packages] RESULT | count=%d", len(packages))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=packages)

    except Exception as exc:
        logger.error("[get_token_packages] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content=_default_token_packages())


@router.get("/api/config/topup-packages")
async def get_topup_packages(request: Request):
    """
    One-time top-up / add-on packages for pricing.html.
    Response: array of { id, name, price, description }
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug("[get_topup_packages] ENTRY")
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    try:
        packages = await _load_topup_packages()

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug("[get_topup_packages] RESULT | count=%d", len(packages))
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        return JSONResponse(content=packages)

    except Exception as exc:
        logger.error("[get_topup_packages] ERROR | %s\n%s", exc, traceback.format_exc())
        return JSONResponse(content=_default_topup_packages())


# ── Config data loaders ──────────────────────────────────────

async def _load_config_plans() -> Any:
    """Load subscription plans from DB config_collection or token_packages_collection."""
    if config_collection is not None:
        doc = await config_collection.find_one({"type": "subscription_plans"})
        if doc and "data" in doc:
            return doc["data"]
        doc = await config_collection.find_one({"key": "plans"})
        if doc and "value" in doc:
            return doc["value"]

    if subscriptions_collection is not None:
        # Pull distinct plan templates (not user subscriptions)
        cursor = subscriptions_collection.find(
            {"is_template": True},
            {"_id": 0, "is_template": 0},
        ).limit(20)
        docs = await cursor.to_list(length=20)
        if docs:
            grouped: Dict[str, list] = {}
            for p in docs:
                role = (p.get("role_group") or p.get("role") or "player").lower()
                grouped.setdefault(role, []).append(p)
            if grouped:
                return grouped

    return _default_plans()


async def _load_token_packages() -> list:
    if token_packages_collection is not None:
        cursor = token_packages_collection.find({}, {"_id": 0}).sort("price", 1).limit(20)
        docs   = await cursor.to_list(length=20)
        if docs:
            return docs
    if config_collection is not None:
        doc = await config_collection.find_one({"type": "token_packages"})
        if doc and "data" in doc:
            return doc["data"]
    return _default_token_packages()


async def _load_topup_packages() -> list:
    if topup_packages_collection is not None:
        cursor = topup_packages_collection.find({}, {"_id": 0}).sort("price", 1).limit(20)
        docs   = await cursor.to_list(length=20)
        if docs:
            return docs
    if config_collection is not None:
        doc = await config_collection.find_one({"type": "topup_packages"})
        if doc and "data" in doc:
            return doc["data"]
    return _default_topup_packages()


# ── Hard-coded fallback plan definitions ─────────────────────

def _default_plans() -> dict:
    return {
        "player": [
            {
                "id": "player-free", "name": "Free", "price": 0, "popular": False,
                "description": "Get started with your basic player profile.",
                "features": [
                    {"text": "Public player profile",           "inc": True},
                    {"text": "Basic match stats (last 3)",      "inc": True},
                    {"text": "Leaderboard visibility",          "inc": True},
                    {"text": "Verified match reports",          "inc": False},
                    {"text": "Token discount",                  "inc": False},
                    {"text": "PDF report export",               "inc": False},
                ],
            },
            {
                "id": "player-pro", "name": "Player Pro", "price": 2500,
                "annual_price": 24000, "popular": True,
                "description": "Full stats, verified badge and priority support.",
                "features": [
                    {"text": "Everything in Free",              "inc": True},
                    {"text": "Full match history (all time)",   "inc": True},
                    {"text": "Verified badge on profile",       "inc": True},
                    {"text": "10% token discount",              "inc": True},
                    {"text": "PDF report export",               "inc": True},
                    {"text": "Priority support",                "inc": True},
                ],
            },
        ],
        "club": [
            {
                "id": "club-standard", "name": "Club Standard", "price": 8000,
                "annual_price": 76800, "popular": False,
                "description": "For grassroots and amateur clubs.",
                "features": [
                    {"text": "Club profile page",               "inc": True},
                    {"text": "Up to 25 squad members",          "inc": True},
                    {"text": "Match stats tracking",            "inc": True},
                    {"text": "Scout access",                    "inc": False},
                    {"text": "Analytics dashboard",             "inc": False},
                    {"text": "Token discount",                  "inc": False},
                ],
            },
            {
                "id": "club-pro", "name": "Club Pro", "price": 15000,
                "annual_price": 144000, "popular": True,
                "description": "Full suite for professional and semi-pro clubs.",
                "features": [
                    {"text": "Everything in Standard",          "inc": True},
                    {"text": "Unlimited squad members",         "inc": True},
                    {"text": "Scout & agent access",            "inc": True},
                    {"text": "15% token discount",              "inc": True},
                    {"text": "Analytics dashboard",             "inc": True},
                    {"text": "Priority support",                "inc": True},
                ],
            },
        ],
        "scout": [
            {
                "id": "scout-individual", "name": "Scout Individual", "price": 5000,
                "annual_price": 48000, "popular": False,
                "description": "For independent scouts.",
                "features": [
                    {"text": "Access to all player profiles",   "inc": True},
                    {"text": "Advanced filters",                "inc": True},
                    {"text": "5 scouting reports/month",        "inc": True},
                    {"text": "Player contact info",             "inc": False},
                    {"text": "PDF report export",               "inc": False},
                    {"text": "Token discount",                  "inc": False},
                ],
            },
            {
                "id": "scout-pro", "name": "Scout Pro", "price": 10000,
                "annual_price": 96000, "popular": True,
                "description": "Unlimited scouting for agencies.",
                "features": [
                    {"text": "Everything in Individual",        "inc": True},
                    {"text": "Unlimited scouting reports",      "inc": True},
                    {"text": "Player contact details",          "inc": True},
                    {"text": "10% token discount",              "inc": True},
                    {"text": "PDF report export",               "inc": True},
                    {"text": "Priority access to new talent",   "inc": True},
                ],
            },
        ],
        "agent": [
            {
                "id": "agent-individual", "name": "Agent Individual", "price": 8000,
                "annual_price": 76800, "popular": False,
                "description": "For agents managing up to 10 players.",
                "features": [
                    {"text": "Up to 10 player portfolios",      "inc": True},
                    {"text": "Agent dashboard",                 "inc": True},
                    {"text": "Verified player reports",         "inc": True},
                    {"text": "Commission tracker",              "inc": False},
                    {"text": "Token discount",                  "inc": False},
                    {"text": "Priority support",                "inc": False},
                ],
            },
            {
                "id": "agent-agency", "name": "Agent Agency", "price": 20000,
                "annual_price": 192000, "popular": True,
                "description": "For agencies managing larger rosters.",
                "features": [
                    {"text": "Unlimited player portfolios",     "inc": True},
                    {"text": "Full agency dashboard",           "inc": True},
                    {"text": "Commission tracking",             "inc": True},
                    {"text": "15% token discount",              "inc": True},
                    {"text": "Custom branded reports",          "inc": True},
                    {"text": "Dedicated account manager",       "inc": True},
                ],
            },
        ],
    }


def _default_token_packages() -> list:
    return [
        {"id": "t5",  "amount": 5,  "tokens": 5,  "price": 1000, "bonus": None},
        {"id": "t10", "amount": 10, "tokens": 10, "price": 1800, "bonus": "Free 1 extra"},
        {"id": "t20", "amount": 20, "tokens": 20, "price": 3200, "bonus": "Best value"},
        {"id": "t50", "amount": 50, "tokens": 50, "price": 7000, "bonus": "Save 30%"},
    ]


def _default_topup_packages() -> list:
    return [
        {"id": "su1",     "name": "Single Stat Request",  "price": 500,  "description": "1 match stats report from a DCO."},
        {"id": "su5",     "name": "5-Report Bundle",       "price": 2200, "description": "5 match stat reports. Save ₦300."},
        {"id": "su10",    "name": "10-Report Bundle",      "price": 4000, "description": "10 match stat reports. Save ₦1,000."},
        {"id": "express", "name": "Express Processing",    "price": 800,  "description": "24hr guaranteed turnaround on any stat request."},
    ]


# ============================================================
# SECTION 10 – PAYMENT ENDPOINTS  (pricing.html checkout flow)
# ============================================================
#
# NOTE: The pricing.html page uses the Flutterwave inline JS SDK
# (FlutterwaveCheckout) which handles the payment UI client-side.
# These endpoints are provided for backend-initiated / server-side
# payment flows and for webhook/verification callbacks.
# ============================================================

class PublicPaymentInitiatePayload(BaseModel):
    amount:      float
    description: str
    type:        str  # "subscription" | "token" | "topup"
    plan_id:     Optional[str] = None
    package_id:  Optional[str] = None
    role:        Optional[str] = None
    level:       Optional[str] = None
    plan_key:    Optional[str] = None
    tokens:      Optional[float] = None
    email:       Optional[str] = None
    name:        Optional[str] = None


class PublicPaymentVerifyPayload(BaseModel):
    transaction_id: str
    tx_ref:         str


@router.post("/api/public/payments/initiate")
async def initiate_public_payment(
    request: Request,
    payload: PublicPaymentInitiatePayload,
):
    """
    Initiate a Flutterwave payment session server-side.
    Returns a payment link or tx_ref for the client to resume.
    Used by pricing.html when FlutterwaveCheckout inline is unavailable.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[initiate_public_payment] ENTRY | type=%r amount=%r plan_id=%r",
        payload.type, payload.amount, payload.plan_id,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    if not payload.amount or payload.amount <= 0:
        raise HTTPException(status_code=422, detail="Invalid payment amount")

    payment_type = (payload.type or "").strip().lower()
    if payment_type not in {"subscription", "token", "topup"}:
        raise HTTPException(status_code=422, detail="Unsupported payment type")

    # Validate the payable amount against the canonical pricing service for
    # subscription/token purchases. Never trust a client-supplied amount for
    # these server-defined catalogue items. Top-ups remain on their existing
    # catalogue because that catalogue is managed by the public routes.
    if payment_type in {"subscription", "token"}:
        try:
            from pricing_module import pricing_service
            role = (payload.role or "").strip().lower()
            level = (payload.level or "").strip() or None
            country = (request.query_params.get("country") or "NG").upper().strip()

            if payment_type == "subscription":
                plan_key = (payload.plan_key or payload.plan_id or "").strip()
                if not role or not plan_key:
                    raise HTTPException(status_code=422, detail="Subscription role and plan are required")
                expected = pricing_service.get_subscription_price(
                    role=role, level=level, plan_key=plan_key, country_code=country
                )
            else:
                if not role or payload.tokens is None:
                    raise HTTPException(status_code=422, detail="Token package role and token amount are required")
                packages = pricing_service.get_token_packages(
                    role=role, level=level, country_code=country
                )
                target = next((p for p in packages if float(p.get("tokens", 0)) == float(payload.tokens)), None)
                if not target:
                    raise HTTPException(status_code=422, detail="Token package not found")
                expected = int(target.get("price", 0))

            if abs(float(payload.amount) - float(expected)) > 0.001:
                raise HTTPException(status_code=422, detail="Payment amount does not match the current pricing configuration")
        except HTTPException:
            raise
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:
            logger.error("[initiate_public_payment] pricing validation error | %s", exc)
            raise HTTPException(status_code=503, detail="Pricing service unavailable")

    elif payment_type == "topup":
        # Top-ups use the public top-up catalogue. Validate the client amount
        # against the selected catalogue item before asking Flutterwave to
        # create a charge.
        try:
            packages = await _load_topup_packages()
            package_id = str(payload.package_id or payload.plan_id or "")
            selected = next((p for p in packages if str(p.get("id") or p.get("package_id") or "") == package_id), None)
            if selected is None and payload.description:
                selected = next((p for p in packages if str(p.get("name") or p.get("label") or "").strip() in str(payload.description)), None)
            if selected is None:
                raise HTTPException(status_code=422, detail="Top-up package not found")
            expected = float(selected.get("price", 0))
            if abs(float(payload.amount) - expected) > 0.001:
                raise HTTPException(status_code=422, detail="Payment amount does not match the selected top-up package")
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("[initiate_public_payment] top-up validation error | %s", exc)
            raise HTTPException(status_code=503, detail="Top-up catalogue unavailable")

    tx_ref = (
        _make_tx_ref(payload.type) if _make_tx_ref is not None
        else f"ES-{payload.type[:3].upper()}-{secrets.token_hex(8).upper()}"
    )

    secret = FLUTTERWAVE_SECRET_KEY or os.getenv("FLUTTERWAVE_SECRET_KEY", "")
    if not secret:
        logger.warning("[initiate_public_payment] FLUTTERWAVE_SECRET_KEY not set")
        return JSONResponse(content={
            "tx_ref":    tx_ref,
            "link":      None,
            "message":   "Payment gateway not configured",
        }, status_code=503)

    try:
        fw_payload = {
            "tx_ref":           tx_ref,
            "amount":           str(payload.amount),
            "currency":         "NGN",
            "redirect_url":     f"{_origin(request)}/pricing.html?payment=complete",
            "payment_options":  "card,ussd,banktransfer",
            "meta": {
                "type":       payload.type,
                "plan_id":    payload.plan_id or "",
                "package_id": payload.package_id or "",
            },
            "customer": {
                "email":       payload.email or "customer@enejistats.com",
                "name":        payload.name or "EnejiStats Customer",
                "phonenumber": "",
            },
            "customizations": {
                "title":       "EnejiStats",
                "description": payload.description,
                "logo":        f"{_origin(request)}/logo.png",
            },
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.flutterwave.com/v3/payments",
                json=fw_payload,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type":  "application/json",
                },
            )

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[initiate_public_payment] FW RESPONSE | status=%d body_length=%d",
            resp.status_code, len(resp.content),
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        if resp.status_code not in (200, 201):
            logger.error("[initiate_public_payment] FW ERROR | %s", resp.text[:400])
            raise HTTPException(status_code=502, detail="Payment gateway error")

        fw_data = resp.json()
        link    = fw_data.get("data", {}).get("link") or fw_data.get("link")

        return JSONResponse(content={"tx_ref": tx_ref, "link": link, "status": "created"})

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[initiate_public_payment] ERROR | %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to initiate payment")


@router.post("/api/public/payments/verify")
async def verify_public_payment(
    request: Request,
    payload: PublicPaymentVerifyPayload,
):
    """
    Verify a Flutterwave transaction after the customer completes payment.
    Called by the pricing page redirect callback.
    """
    # ── DEBUG BLOCK START ──────────────────────────────────────────────────
    logger.debug(
        "[verify_public_payment] ENTRY | transaction_id=%r tx_ref=%r",
        payload.transaction_id, payload.tx_ref,
    )
    # ── DEBUG BLOCK END ────────────────────────────────────────────────────

    secret = FLUTTERWAVE_SECRET_KEY or os.getenv("FLUTTERWAVE_SECRET_KEY", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.flutterwave.com/v3/transactions/{payload.transaction_id}/verify",
                headers={"Authorization": f"Bearer {secret}"},
            )

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[verify_public_payment] FW VERIFY RESPONSE | status=%d",
            resp.status_code,
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        if resp.status_code != 200:
            logger.error("[verify_public_payment] FW ERROR | %s", resp.text[:400])
            raise HTTPException(status_code=502, detail="Payment verification failed")

        fw_data   = resp.json()
        tx_data   = fw_data.get("data", {})
        tx_status = tx_data.get("status", "")
        tx_amount = tx_data.get("amount", 0)
        tx_curr   = tx_data.get("currency", "NGN")
        tx_ref_fw = tx_data.get("tx_ref", "")

        # ── DEBUG BLOCK START ──────────────────────────────────────────────
        logger.debug(
            "[verify_public_payment] FW STATUS | status=%r amount=%r currency=%r tx_ref=%r",
            tx_status, tx_amount, tx_curr, tx_ref_fw,
        )
        # ── DEBUG BLOCK END ────────────────────────────────────────────────

        verified = tx_status == "successful" and tx_ref_fw == payload.tx_ref

        if verified:
            # Log successful payment — subscription fulfilment happens in
            # the authenticated dashboard routes once the user is signed in.
            logger.info(
                "[verify_public_payment] SUCCESS | tx_id=%r tx_ref=%r amount=%.2f",
                payload.transaction_id, payload.tx_ref, tx_amount,
            )

        return JSONResponse(content={
            "verified":       verified,
            "status":         tx_status,
            "amount":         tx_amount,
            "currency":       tx_curr,
            "transaction_id": payload.transaction_id,
            "tx_ref":         payload.tx_ref,
        })

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[verify_public_payment] ERROR | %s\n%s", exc, traceback.format_exc())
        raise HTTPException(status_code=500, detail="Verification error")


# ── Shared utility ────────────────────────────────────────────

def _origin(request: Request) -> str:
    """Return the base origin URL from the incoming request."""
    return str(request.base_url).rstrip("/")


# ============================================================
# SECTION 11 – HEALTH CHECK  (optional – for monitoring)
# ============================================================

@router.get("/api/public/health")
async def public_health(request: Request):
    """Lightweight liveness probe for the public routes module."""
    return JSONResponse(content={"status": "ok", "module": "visitor_public_routes"})


# ============================================================
# END OF MODULE
# ============================================================
