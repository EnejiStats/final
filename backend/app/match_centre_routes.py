"""EnejiStats — standalone Match Centre backend router.

This module owns the complete Match Centre route/logic surface extracted from
admin_dashboard_routes_aligned.py.  It is deliberately independent of the
admin dashboard module: the dashboard injects the application's shared
dependencies and mounts this APIRouter.  No import of the admin dashboard is
performed here, preventing circular imports.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from location_module import build_venue_location_filter, get_country_name

logger = None
database = None
players_collection = clubs_collection = scouts_collection = agents_collection = None
dco_collection = supervisors_collection = admins_collection = None
notifications_collection = activity_history_collection = None
stats_requests_collection = dco_assignments_collection = None
matches_collection = match_requests_collection = venues_collection = None
MongoSerializer = verify_token = None
get_admin_user = None
ROLE_REGISTRY = None
role_collection = None
_DEPS_READY = False
_ROUTER_MOUNTED = False

router = APIRouter()


def _setup_dependencies(main_globals: dict) -> None:
    """Inject shared application objects; callable directly from main.py or admin routes."""
    global logger, database, players_collection, clubs_collection, scouts_collection, agents_collection
    global dco_collection, supervisors_collection, admins_collection, notifications_collection, activity_history_collection, stats_requests_collection
    global dco_assignments_collection, matches_collection, match_requests_collection, venues_collection
    global MongoSerializer, verify_token, get_admin_user, ROLE_REGISTRY, role_collection, _DEPS_READY
    g = main_globals or {}
    logger = g.get("logger")
    database = g.get("database")
    MongoSerializer = g.get("MongoSerializer")
    verify_token = g.get("verify_token")
    get_admin_user = g.get("get_admin_user")
    ROLE_REGISTRY = g.get("ROLE_REGISTRY")
    role_collection = g.get("role_collection")
    players_collection = g.get("players_collection")
    clubs_collection = g.get("clubs_collection")
    scouts_collection = g.get("scouts_collection")
    agents_collection = g.get("agents_collection")
    dco_collection = g.get("dco_collection")
    supervisors_collection = g.get("supervisors_collection")
    admins_collection = g.get("admins_collection")
    notifications_collection = g.get("notifications_collection")
    activity_history_collection = g.get("activity_history_collection")
    stats_requests_collection = g.get("stats_requests_collection")
    dco_assignments_collection = g.get("dco_assignments_collection")
    matches_collection = g.get("matches_collection")
    if matches_collection is None and database is not None:
        matches_collection = database["matches"]
    match_requests_collection = g.get("match_requests_collection")
    if match_requests_collection is None and database is not None:
        match_requests_collection = database["match_requests"]
    venues_collection = g.get("venues_collection")
    if venues_collection is None and database is not None:
        venues_collection = database["venues"]
    _DEPS_READY = True


def _try_oid(value):
    try: return ObjectId(str(value))
    except (InvalidId, TypeError, ValueError): return None


def _s(doc: Optional[dict]) -> dict:
    return MongoSerializer.serialize_document(doc) if doc else {}


def _ss(docs: List[dict]) -> List[dict]:
    return MongoSerializer.serialize_documents(docs)


def _now_utc() -> datetime:
    return MongoSerializer.now_utc()

def _log(actor_id: str, actor_role: str, atype: str, desc: str) -> None:
    async def _inner():
        try:
            if activity_history_collection is not None:
                await activity_history_collection.insert_one({
                    "actor_id": actor_id,
                    "actor_role": actor_role,
                    "type": atype,
                    "description": desc,
                    "created_at": _now_utc(),
                })
        except Exception:
            pass
    try:
        import asyncio
        asyncio.ensure_future(_inner())
    except Exception:
        pass


async def _send_notification(user_id: str, user_type: str,
                             title: str, message: str, notif_type: str) -> None:
    try:
        if notifications_collection is None:
            return
        await notifications_collection.insert_one({
            "user_id": user_id,
            "user_type": user_type,
            "title": title,
            "message": message,
            "type": notif_type,
            "read": False,
            "created_at": _now_utc(),
        })
    except Exception:
        pass


def _coerce_heatmap_admin(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        n = value.strip().lower()
        if n in ("true", "yes", "1", "on"):
            return True
        if n in ("false", "no", "0", "off", ""):
            return False
    return None


def _display_name(doc: dict) -> str:
    return (doc.get("full_name") or doc.get("name") or doc.get("club_name") or
            " ".join(filter(None, [doc.get("first_name", "") or doc.get("firstName", ""),
                                    doc.get("last_name", "") or doc.get("lastName", "")])).strip() or
            doc.get("email", ""))


def _require_collection(col, name: str):
    if col is None:
        raise HTTPException(status_code=503, detail=f"Service unavailable: collection '{name}' not initialised.")
    return col


def _role_col_map() -> Dict[str, tuple]:
    """Resolve profile collections and public IDs from main.py's role registry."""
    if not isinstance(ROLE_REGISTRY, dict) or not callable(role_collection):
        return {}
    result = {}
    for role, metadata in ROLE_REGISTRY.items():
        try:
            result[role] = (role_collection(role), metadata["id_field"])
        except (KeyError, TypeError, ValueError):
            continue
    return result


async def _find_user(uid: str) -> Optional[tuple]:
    for role, (col, id_field) in _role_col_map().items():
        if col is None: continue
        doc = await col.find_one({id_field: uid}) or await col.find_one({"user_id": uid})
        if not doc and len(str(uid)) == 24:
            oid = _try_oid(uid)
            if oid: doc = await col.find_one({"_id": oid})
        if doc: return doc, role, id_field
    return None


async def _get_admin_from_request(request: Request) -> dict:
    """Resolve admin identity through main.py's canonical guard."""
    if not callable(get_admin_user):
        raise HTTPException(status_code=503, detail="Admin auth service not ready")
    return await get_admin_user(request)


async def _require_admin(request: Request) -> dict:
    return await _get_admin_from_request(request)


def _db_collection_candidates(*names):
    if database is None: return []
    out=[]
    for name in names:
        try:
            col=database[name]
            if col is not None: out.append(col)
        except Exception: pass
    return out


async def _geo_documents(kind: str, country_code: str = "", region: str = "") -> List[dict]:
    """Build selector options from the location data already present in Mongo.

    The extracted router previously called this helper without defining it,
    making all three public geography endpoints fail at runtime.  Deriving
    values from the same clubs, venues, matches and request records used by
    Match Centre keeps the selectors useful without introducing another
    required collection or changing the application's schema.
    """
    kind = str(kind or "").strip().lower()
    field_groups = {
        "country": (
            ("country", "venue_country", "country_name"),
            ("country_code", "venue_country_code"),
        ),
        "region": (
            ("state", "venue_state", "region", "province", "county"),
            (),
        ),
        "subregion": (
            ("lga", "venue_lga", "local_area", "subregion", "district"),
            (),
        ),
    }
    if kind not in field_groups:
        return []

    name_fields, code_fields = field_groups[kind]
    sources = [
        clubs_collection, venues_collection, matches_collection,
        stats_requests_collection,
    ]
    # Support deployments which maintain dedicated location collections.
    if kind == "country":
        sources.extend(_db_collection_candidates("countries", "country"))
    elif kind == "region":
        sources.extend(_db_collection_candidates("states", "regions"))
    else:
        sources.extend(_db_collection_candidates("lgas", "subregions"))

    country_code = str(country_code or "").strip()
    country_name = str(get_country_name(country_code) or "").strip() if country_code else ""
    region = str(region or "").strip()
    country_ors = []
    region_ors = []
    if country_code:
        for field in ("country_code", "venue_country_code", "code", "iso2"):
            country_ors.append({field: {"$regex": f"^{re.escape(country_code)}$", "$options": "i"}})
        for field in ("country", "venue_country", "country_name"):
            for value in (country_code, country_name):
                if value:
                    country_ors.append({field: {"$regex": f"^{re.escape(value)}$", "$options": "i"}})
    if region:
        for field in ("state", "venue_state", "region", "province", "county"):
            region_ors.append({field: {"$regex": f"^{re.escape(region)}$", "$options": "i"}})
    clauses = []
    if country_ors:
        clauses.append({"$or": country_ors})
    if region_ors:
        clauses.append({"$or": region_ors})
    query = {"$and": clauses} if clauses else {}

    names, codes, seen_sources = set(), set(), set()
    for col in sources:
        if col is None:
            continue
        source_name = str(getattr(col, "name", "") or "").lower()
        # De-duplicate the same collection when it is exposed both through an
        # injected dependency and the database handle.
        identity = source_name or str(id(col))
        if identity in seen_sources:
            continue
        seen_sources.add(identity)

        source_name_fields = name_fields
        source_code_fields = code_fields
        if kind == "country" and source_name in {"countries", "country"}:
            source_name_fields = source_name_fields + ("name", "label")
            source_code_fields = source_code_fields + ("code", "iso2", "iso_code")
        elif kind == "region" and source_name in {"states", "regions"}:
            source_name_fields = source_name_fields + ("name", "label")
        elif kind == "subregion" and source_name in {"lgas", "subregions"}:
            source_name_fields = source_name_fields + ("name", "label")

        for field in source_name_fields:
            try:
                values = await col.distinct(field, query)
            except Exception:
                try:
                    values = await col.distinct(field)
                except Exception:
                    continue
            for value in values or []:
                if isinstance(value, dict):
                    value = value.get("name") or value.get("label") or value.get("value")
                if value not in (None, "") and not isinstance(value, (list, dict)):
                    names.add(str(value).strip())
        for field in source_code_fields:
            try:
                values = await col.distinct(field, query)
            except Exception:
                try:
                    values = await col.distinct(field)
                except Exception:
                    continue
            for value in values or []:
                if value not in (None, "") and not isinstance(value, (list, dict)):
                    codes.add(str(value).strip())

    if kind == "country":
        rows = {}
        for name in names:
            if not name:
                continue
            resolved = str(get_country_name(name) or "").strip()
            display = resolved or name
            rows.setdefault(display.casefold(), {
                "name": display, "country": display, "label": display,
                "value": display, "code": "", "country_code": "",
            })
        for code in codes:
            if not code:
                continue
            display = str(get_country_name(code) or code).strip()
            key = display.casefold()
            row = rows.setdefault(key, {
                "name": display, "country": display, "label": display,
                "value": code, "code": code, "country_code": code,
            })
            if not row.get("country_code"):
                row.update({"value": code, "code": code, "country_code": code})
        return sorted(rows.values(), key=lambda item: item["name"].casefold())

    values = sorted((value for value in names if value), key=str.casefold)
    key = "state" if kind == "region" else "lga"
    return [{"name": value, "label": value, "value": value, key: value} for value in values]


def _doc_value(doc: dict, *keys, default=""):
    for key in keys:
        value=doc.get(key)
        if value not in (None, ""): return value
    return default


class MatchCreateBody(BaseModel):
    category: str
    home_team: str
    away_team: str
    match_date: str
    match_time: str
    venue: str
    competition: Optional[str] = None
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    venue_id: Optional[str] = None
    gps: Optional[dict] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    tracking_requirement: Optional[str] = "optional"
    tracking: Optional[bool] = False
    country_name: Optional[str] = None
    local_area: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    lga: Optional[str] = None
    city: Optional[str] = None
    venue_country: Optional[str] = None
    venue_country_code: Optional[str] = None
    venue_state: Optional[str] = None
    venue_lga: Optional[str] = None
    venue_city: Optional[str] = None
    venue_detailed_address: Optional[str] = None
    notes: Optional[str] = None
    supervisor_ids: List[str] = Field(default_factory=list)


class MatchSupervisorsBody(BaseModel):
    supervisor_ids: List[str] = Field(default_factory=list)



# ============================================================
# MATCH CENTRE ROUTES
# ============================================================

# MATCH CENTRE
# ============================================================

def _match_name(doc: dict) -> str:
    return (doc.get("club_name") or doc.get("team_name") or doc.get("name")
            or doc.get("full_name") or doc.get("club_id") or str(doc.get("_id", "")))


async def _materialize_accepted_matches(col) -> None:
    """Create each accepted club fixture once, including legacy request schemas."""
    for source in (stats_requests_collection, match_requests_collection):
        if source is None:
            continue
        try:
            docs = await source.find({"status": {"$in": ["accepted", "approved", "confirmed"]}}).limit(250).to_list(250)
            for req in docs:
                home = req.get("home_team") or req.get("home_club") or req.get("requesting_club")
                away = req.get("away_team") or req.get("away_club") or req.get("opponent_club")
                date = req.get("match_date") or req.get("event_date")
                venue = req.get("venue") or req.get("stadium") or req.get("venue_name")
                if not home or not away or not date or not venue:
                    continue
                source_id = str(req.get("request_id") or req.get("_id"))
                if await col.find_one({"source_request_id": source_id}):
                    continue
                await col.insert_one({
                    "match_id": "MAT-" + secrets.token_hex(8).upper(),
                    "source_request_id": source_id, "source": "Accepted club request",
                    "status": "scheduled",
                    "category": req.get("category") or req.get("player_level") or "General",
                    "home_team": home, "away_team": away, "match_date": date,
                    "match_time": req.get("match_time") or "00:00", "venue": venue,
                    "notes": req.get("notes") or "", "supervisor_ids": [],
                    "created_at": _now_utc(), "updated_at": _now_utc(),
                })
        except Exception:
            continue


def _admin_club_location_clauses(country="", country_code="", state="", region="", lga="", subregion="", city=""):
    clauses=[]
    cc=str(country_code or "").strip().upper(); cname=str(country or "").strip()
    if cc:
        resolved=get_country_name(cc) or ""
        ors=[{"country_code":cc}]
        for value in (cname,resolved):
            if value: ors.append({"country":{"$regex":re.escape(value),"$options":"i"}})
        clauses.append({"$or":ors})
    elif cname:
        clauses.append({"$or":[{"country":{"$regex":re.escape(cname),"$options":"i"}},{"country_code":{"$regex":re.escape(cname),"$options":"i"}}]})
    sv=str(state or region or "").strip()
    if sv: clauses.append({"$or":[{"state":{"$regex":re.escape(sv),"$options":"i"}},{"region":{"$regex":re.escape(sv),"$options":"i"}},{"province":{"$regex":re.escape(sv),"$options":"i"}},{"county":{"$regex":re.escape(sv),"$options":"i"}}]})
    lv=str(lga or subregion or "").strip()
    if lv: clauses.append({"$or":[{"lga":{"$regex":re.escape(lv),"$options":"i"}},{"local_area":{"$regex":re.escape(lv),"$options":"i"}},{"subregion":{"$regex":re.escape(lv),"$options":"i"}},{"district":{"$regex":re.escape(lv),"$options":"i"}}]})
    cv=str(city or "").strip()
    if cv: clauses.append({"$or":[{"city":{"$regex":re.escape(cv),"$options":"i"}},{"town":{"$regex":re.escape(cv),"$options":"i"}}]})
    return clauses


async def _admin_resolve_venue(venue_id):
    vid=str(venue_id or "").strip()
    if not vid or venues_collection is None: return None
    ors=[{"venue_id":vid},{"id":vid}]
    try: ors.insert(0,{"_id":ObjectId(vid)})
    except Exception: pass
    try: doc=await venues_collection.find_one({"$or":ors})
    except Exception: doc=None
    return _s(doc) if doc else None


def _admin_merge_club_venue(club, venue, secondary=False):
    if secondary:
        name=(venue or {}).get("venue_name") or (venue or {}).get("name") or club.get("stadium2") or ""
        address=(venue or {}).get("full_address") or (venue or {}).get("address") or club.get("stadium2_address") or ""
        lat=(venue or {}).get("gps_lat") if (venue or {}).get("gps_lat") not in (None,"") else club.get("stadium_gps2_lat")
        lng=(venue or {}).get("gps_lng") if (venue or {}).get("gps_lng") not in (None,"") else club.get("stadium_gps2_lng")
        ref=club.get("secondary_ground_id")
    else:
        name=(venue or {}).get("venue_name") or (venue or {}).get("name") or club.get("stadium") or ""
        address=(venue or {}).get("full_address") or (venue or {}).get("address") or club.get("stadium_address") or ""
        lat=(venue or {}).get("gps_lat") if (venue or {}).get("gps_lat") not in (None,"") else club.get("stadium_gps_lat")
        lng=(venue or {}).get("gps_lng") if (venue or {}).get("gps_lng") not in (None,"") else club.get("stadium_gps_lng")
        ref=club.get("primary_ground_id")
    if not name: return None
    vid=str((venue or {}).get("venue_id") or (venue or {}).get("id") or (venue or {}).get("_id") or ref or "")
    country=(venue or {}).get("country") or club.get("country") or ""
    code=str((venue or {}).get("country_code") or club.get("country_code") or "").upper()
    state=(venue or {}).get("state") or (venue or {}).get("region") or club.get("state") or ""
    lga=(venue or {}).get("lga") or club.get("lga") or ""
    city=(venue or {}).get("city") or (venue or {}).get("town") or club.get("city") or ""
    gps={"lat":lat,"lng":lng} if lat not in (None,"") and lng not in (None,"") else None
    return {"id":vid,"venue_id":vid,"name":name,"venue_name":name,"stadium":name,"home_ground":name,"address":address,"full_address":address,"venue_address":address,"venue_full_address":address,"country":country,"country_code":code,"state":state,"region":state,"lga":lga,"city":city,"venue_country":country,"venue_country_code":code,"venue_state":state,"venue_lga":lga,"venue_city":city,"gps":gps,"venue_gps":gps,"gps_lat":lat,"gps_lng":lng,"venue_gps_lat":lat,"venue_gps_lng":lng,"capacity":(venue or {}).get("capacity"),"venue_type":(venue or {}).get("venue_type"),"surface_type":(venue or {}).get("surface_type")}




class StatsAssignBody(BaseModel):
    request_id: Optional[str] = None
    assignee_id: str
    role: Optional[str] = "dco"
    notes: Optional[str] = None
    supervisor_id: Optional[str] = None


class StatsRejectBody(BaseModel):
    reason: Optional[str] = None

def _request_entity_type(doc: dict) -> str:
    """Canonicalize legacy request-type labels before persisting assignments."""
    explicit = str(
        doc.get("entity_type")
        or doc.get("entityType")
        or doc.get("requester_type")
        or doc.get("requesterType")
        or doc.get("request_type")
        or doc.get("requestType")
        or doc.get("scope")
        or ""
    ).strip().lower().replace("-", "_").replace(" ", "_")
    if explicit.startswith("club") or explicit in {"team", "team_stats"}:
        return "club"
    if explicit.startswith("player"):
        return "player"
    return (
        "player"
        if doc.get("player_id")
        or doc.get("playerId")
        or doc.get("player_name")
        or doc.get("playerName")
        else "club"
    )


async def _admin_request_rows(doc: dict) -> List[dict]:
    """Expand a club-plus-players request into independently assignable rows."""
    base = dict(doc)
    base["entity_type"] = _request_entity_type(base)
    base["request_type"] = base["entity_type"]
    ids = list(dict.fromkeys(str(value) for value in (base.get("player_ids") or [])
                             if value not in (None, "")))
    if base.get("tracking_type") != "club_and_players" or not ids:
        return [base]

    rows = [base]
    parent_id = str(base.get("request_id") or base.get("_id") or "")
    player_states = {
        str(state.get("player_id")): state
        for state in (base.get("player_request_states") or [])
        if isinstance(state, dict) and state.get("player_id") not in (None, "")
    }
    for player_id in ids:
        player_doc = {}
        if players_collection is not None:
            player_doc = await players_collection.find_one({
                "$or": [{"player_id": player_id}, {"user_id": player_id}, {"_id": _try_oid(player_id)}]
            }) or {}
        row = dict(base)
        state = player_states.get(player_id) or {}
        row.update({
            "request_id": f"{parent_id}:player:{player_id}",
            "parent_request_id": parent_id,
            "entity_type": "player",
            "request_type": "player",
            "player_id": player_id,
            "player_name": (player_doc.get("full_name") or player_doc.get("name") or
                            " ".join(str(player_doc.get(k, "")) for k in
                                      ("firstName", "middleName", "lastName")).strip()),
            "position": player_doc.get("position") or player_doc.get("preferredPosition") or "",
            "jersey_number": player_doc.get("jersey_number") or player_doc.get("jerseyNumber") or "",
            "player_represents": player_doc.get("player_represents") or player_doc.get("represents") or "",
            "status": state.get("status") or base.get("status") or "Pending",
        })
        for field in (
            "assigned_dco_id", "assigned_supervisor_id", "assigned_role",
            "assigned_at", "rejection_reason", "rejected_at", "completed_at",
            "updated_at", "activity", "audit_trail",
        ):
            if state.get(field) not in (None, ""):
                row[field] = state[field]
        rows.append(row)
    return rows


async def _resolve_admin_request(request_id: str):
    """Resolve both real request IDs and virtual expanded player IDs."""
    parent_id = request_id.split(":player:", 1)[0] if ":player:" in request_id else request_id
    filter_q = {"$or": [{"request_id": parent_id}, {"_id": _try_oid(parent_id)}]}
    doc = await stats_requests_collection.find_one(filter_q)
    if not doc:
        return None, filter_q
    if ":player:" in request_id:
        rows = await _admin_request_rows(doc)
        doc = next((row for row in rows if row.get("request_id") == request_id), doc)
    return doc, filter_q


async def _update_stats_request_status(
    collection,
    filter_q: dict,
    request_id: str,
    doc: dict,
    status: str,
    changes: Optional[dict] = None,
    audit_event: Optional[dict] = None,
) -> None:
    """Update a request, keeping virtual club-player rows independent."""
    updates = dict(changes or {})
    updates.update({"status": status, "updated_at": _now_utc()})
    event = dict(audit_event or {})
    if event:
        updates["updated_at"] = _now_utc()
        for timestamp_field in ("assigned_at", "rejected_at", "completed_at"):
            if timestamp_field in updates:
                updates[timestamp_field] = updates["updated_at"]
        event["created_at"] = updates["updated_at"]
        event.setdefault("action", status)

    if ":player:" not in request_id:
        update = {"$set": updates}
        if event:
            current_activity = doc.get("activity")
            if isinstance(current_activity, list):
                update["$set"]["activity"] = current_activity + [event]
            elif current_activity is None:
                update["$push"] = {"activity": event}
            else:
                update["$set"]["activity"] = [event]
        await collection.update_one(filter_q, update)
        return

    player_id = str(doc.get("player_id") or "")
    if not player_id:
        raise HTTPException(status_code=400, detail="Player request ID is missing its player ID")

    states = [
        dict(state)
        for state in (doc.get("player_request_states") or [])
        if isinstance(state, dict)
    ]
    state = next((item for item in states if str(item.get("player_id") or "") == player_id), None)
    if state is None:
        state = {"player_id": player_id}
        states.append(state)
    state.update(updates)
    if event:
        current_activity = state.get("activity")
        if not isinstance(current_activity, list):
            current_activity = []
            state["activity"] = current_activity
        current_activity.append(event)
    await collection.update_one(
        filter_q,
        {"$set": {"player_request_states": states, "updated_at": updates["updated_at"]}},
    )


def _stats_status(value: Any) -> str:
    return re.sub(r"[\s-]+", "_", str(value or "pending").strip().lower())


def _stats_date(value: Any):
    if value in (None, ""):
        return None
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date()
        except Exception:
            pass
    try:
        text = str(value).strip().replace("Z", "+00:00")
        return datetime.fromisoformat(text).date()
    except Exception:
        try:
            return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
        except Exception:
            return None


def _stats_row_matches(row: dict, country: str = "", state: str = "",
                       lga: str = "", search: str = "",
                       date_from: str = "", date_to: str = "") -> bool:
    """Apply the same request-row filters exposed by the integrated Preact UI."""
    def norm(value):
        return str(value or "").strip().casefold()

    if country:
        selected = norm(country)
        resolved = norm(get_country_name(country) or "")
        country_codes = {
            norm(row.get("venue_country_code")),
            norm(row.get("country_code")),
        }
        country_names = {
            norm(row.get("venue_country")),
            norm(row.get("country")),
            norm(row.get("country_name")),
        }
        if selected not in country_codes | country_names and (
            not resolved or resolved not in country_names
        ):
            return False

    if state and norm(row.get("venue_state") or row.get("state")) != norm(state):
        return False
    if lga and norm(lga) not in norm(row.get("venue_lga") or row.get("lga")):
        return False

    if search:
        haystack = " ".join(
            str(row.get(key) or "")
            for key in (
                "club_name", "club_id", "player_name", "player_id",
                "request_id", "_id", "reference_id", "venue_state", "state",
                "scope", "match_type", "home_team", "away_team",
            )
        ).casefold()
        if norm(search) not in haystack:
            return False

    # Match the UI's submission/event date precedence.
    request_date = _stats_date(
        row.get("created_at") or row.get("match_date") or row.get("event_date")
    )
    start = _stats_date(date_from)
    end = _stats_date(date_to)
    if start and (request_date is None or request_date < start):
        return False
    if end and (request_date is None or request_date > end):
        return False
    return True



@router.get("/api/admin/stats-requests/all")
async def stats_requests_all(
    request: Request,
    status: str = "",
    limit: int = 25,
    sort: str = "newest",
    page: int = 1,
    country: str = "",
    state: str = "",
    lga: str = "",
    search: str = "",
    date_from: str = "",
    date_to: str = "",
):
    await _require_admin(request)
    status_filter = _stats_status(status) if status and status.strip().lower() != "all" else ""
    limit = min(500, max(1, limit))
    page = max(1, page)
    if stats_requests_collection is None:
        raise HTTPException(status_code=503, detail="Stats request storage is unavailable")
    sort_key = str(sort or "newest").strip().lower()
    sort_field = "updated_at" if sort_key in {"updated", "recently_updated"} else "submitted_at"
    direction = 1 if sort_key in {"oldest", "oldest_first", "oldest_updated"} else -1
    cursor = stats_requests_collection.find({}).sort(
        [(sort_field, direction), ("created_at", direction), ("_id", direction)]
    )

    # Page over expanded logical requests, not parent Mongo documents. A club
    # request can produce one club row plus multiple independently actionable
    # player rows, each with its own status and assignment.
    start_at = (page - 1) * limit
    end_at = start_at + limit
    selected = []
    total = 0
    summary = {
        "total": 0, "pending": 0, "submitted": 0, "assigned": 0,
        "in_progress": 0, "submitted_for_review": 0, "review": 0,
        "approved": 0, "completed": 0, "rejected": 0,
    }

    async for doc in cursor:
        for row in await _admin_request_rows(doc):
            if not _stats_row_matches(
                row, country=country, state=state, lga=lga, search=search,
                date_from=date_from, date_to=date_to,
            ):
                continue

            row_status = _stats_status(row.get("status") or "pending")
            summary["total"] += 1
            if row_status in summary:
                summary[row_status] += 1
            if status_filter and row_status != status_filter:
                continue

            if start_at <= total < end_at:
                selected.append(row)
            total += 1

    pages = max(1, (total + limit - 1) // limit)
    serialized = _ss(selected)
    pagination = {"page": page, "limit": limit, "total": total, "pages": pages}
    return JSONResponse({
        "requests": serialized,
        "stats_requests": serialized,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "pagination": pagination,
        "summary": summary,
        "status_summary": summary,
    })


@router.get("/api/admin/stats-requests/{request_id}")
async def admin_stats_request_detail(request_id: str, request: Request):
    """Return one complete stats-request record, including an expanded player row when applicable."""
    await _require_admin(request)
    doc, _ = await _resolve_admin_request(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Stats request not found")
    return JSONResponse(_s(doc))


@router.post("/api/admin/stats-requests/{request_id}/assign")
async def admin_assign_stats_request(
    request_id: str,
    body: StatsAssignBody,
    request: Request,
):
    """
    Assign a scout / DCO to a stats request.

    In addition to core assignment metadata, we snapshot all relevant
    fields from the stats request into the assignment document.  This
    provides a resilient second data path: if the stats request is later
    modified or deleted, the DCO backend can still surface complete
    player/match context from the assignment doc alone.
    """
    admin    = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    sr_col   = _require_collection(stats_requests_collection,    "stats_requests_collection")
    asgn_col = _require_collection(dco_assignments_collection, "dco_assignments_collection")

    doc, filter_q = await _resolve_admin_request(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Stats request not found")

    role         = (body.role or "dco").strip().lower()
    if role not in {"dco", "supervisor"}:
        raise HTTPException(status_code=400, detail="role must be 'dco' or 'supervisor'")
    if not body.assignee_id or not body.assignee_id.strip():
        raise HTTPException(status_code=400, detail="assignee_id is required")
    if body.request_id and body.request_id != request_id:
        raise HTTPException(status_code=400, detail="request_id must match the URL")
    assignee_key = "assigned_dco_id" if role == "dco" else "assigned_supervisor_id"

    # Make assignment retries idempotent before changing request state or
    # appending another activity event.
    existing_assignment = await asgn_col.find_one({
        "stats_request_id": request_id,
        "assignee_id": body.assignee_id,
        "status": {"$nin": ["declined", "rejected"]},
    })
    if existing_assignment:
        return JSONResponse({
            "success": True,
            "request_id": request_id,
            "assignee_id": body.assignee_id,
            "supervisor_id": body.supervisor_id,
            "assignment_id": existing_assignment.get("assignment_id") or str(existing_assignment.get("_id", "")),
            "status": existing_assignment.get("status", "assigned"),
            "duplicate": True,
        })

    assigned_at = _now_utc()
    # Keep statuses for a club's independently assignable player rows apart.
    status_changes = {
        assignee_key: body.assignee_id,
        "assigned_role": role,
        "admin_id": admin_id,
        "assigned_at": assigned_at,
    }
    if body.supervisor_id:
        status_changes["assigned_supervisor_id"] = body.supervisor_id
    await _update_stats_request_status(
        sr_col, filter_q, request_id, doc, "assigned", status_changes,
        {
            "title": "Request assigned",
            "description": f"Assigned to {role}: {body.assignee_id}"
                          + (f" · Supervisor: {body.supervisor_id}" if body.supervisor_id else ""),
            "actor_id": admin_id,
            "actor_role": "admin",
        },
    )

    # ── Build assignment document with full stats-request snapshot ─────────
    assignment_id = f"ASGN-{secrets.token_hex(6).upper()}"

    def _snap(doc, *keys, default=""):
        """Return first truthy value from doc for the given keys."""
        for k in keys:
            v = doc.get(k)
            if v is not None and v != "":
                return v
        return default

    assignment_doc = {
        # ── Core assignment metadata ───────────────────────────────────
        "assignment_id":          assignment_id,
        "stats_request_id":       request_id,
        "request_id":             request_id,
        "parent_request_id":      doc.get("parent_request_id") or doc.get("request_id") or request_id,
        "entity_type":             _request_entity_type(doc),
        "request_type":            _request_entity_type(doc),
        "tracking_type":           _snap(doc, "tracking_type", default="no_tracking"),
        assignee_key:             body.assignee_id,
        "assignee_id":            body.assignee_id,
        "role":                   role,
        "notes":                  body.notes or _snap(
            doc, "notes", "request_notes", "requestNotes",
            "additional_notes", "additionalNotes",
        ),
        "assignment_notes":      body.notes or "",
        "request_notes":         _snap(
            doc, "notes", "request_notes", "requestNotes",
        ),
        "request_additional_notes": _snap(
            doc, "additional_notes", "additionalNotes",
        ),
        "status":                 "assigned",
        "admin_id":               admin_id,
        "assigned_at":            assigned_at,
        "created_at":             _now_utc(),
        "updated_at":             _now_utc(),

        # ── Snapshot: player / entity ──────────────────────────────────
        "player_name":       _snap(doc, "player_name",  "playerName"),
        "position":          _snap(doc, "position"),
        "jersey_number":     _snap(doc, "jersey_number", "jerseyNumber"),
        "club":              _snap(doc, "club", "club_name"),
        "club_id":           _snap(doc, "club_id"),
        "club_name":         _snap(doc, "club_name", "club"),
        "club_role":         _snap(doc, "club_role", "clubRole"),
        "jersey_color":      _snap(doc, "jersey_color", "jerseyColor"),
        "player_id":         _snap(doc, "player_id"),
        "player_represents": _snap(doc, "player_represents", "playerRepresents", "represents"),

        # ── Snapshot: match category / level ──────────────────────────
        "category":     _snap(doc, "category", "player_level", "level"),
        "player_level": _snap(doc, "player_level", "category", "level"),
        "match_type":   _snap(doc, "match_type", "matchType", "competition_type"),
        "competition":  _snap(doc, "competition", "league"),

        # ── Snapshot: scheduling ──────────────────────────────────────
        "match_date": _snap(doc, "match_date", "matchDate"),
        "match_time": _snap(doc, "match_time", "matchTime"),

        # ── Snapshot: venue ───────────────────────────────────────────
        "venue":         _snap(doc, "venue", "stadium", "venue_name"),
        "venue_address": _snap(doc, "venue_address", "venueAddress", "stadium_address"),
        "venue_state":   _snap(doc, "venue_state", "state"),
        "venue_lga":     _snap(doc, "venue_lga", "lga"),
        "venue_country": _snap(doc, "venue_country", "country", default="Nigeria"),

        # ── Snapshot: teams ───────────────────────────────────────────
        "home_team": _snap(doc, "home_team", "homeTeam"),
        "away_team": _snap(doc, "away_team", "awayTeam"),
        "home_club": _snap(doc, "home_club", "homeClub"),
        "away_club": _snap(doc, "away_club", "awayClub"),

                # ── Snapshot: heatmap ─────────────────────────────────────────
        # Stored as a normalised Python bool (or None if not specified).
        # None is preserved intentionally: the DCO frontend treats None
        # the same as "enabled" for backward compatibility.
        "heatmap": _coerce_heatmap_admin(doc.get("heatmap")),

        # ── Snapshot: contact ─────────────────────────────────────────
        "contact_phone": _snap(doc, "contact_phone", "contactPhone", "phone"),
        "requested_by":  _snap(doc, "requested_by", "club_id"),
        "requested_by_name": _snap(
            doc, "requested_by_name", "requestedByName", "club_name", "club"
        ),
        "submitted_at":  _snap(doc, "submitted_at", "created_at"),
    }

    if body.supervisor_id:
        assignment_doc["assigned_supervisor_id"] = body.supervisor_id

    await asgn_col.insert_one(assignment_doc)

    if role == "dco" and body.assignee_id and body.supervisor_id and dco_collection is not None:
        _dco_doc = await dco_collection.find_one(
            {
                "$or": [
                    {"dco_id": body.assignee_id},
                    {"user_id": body.assignee_id},
                ]
            }
        )
        if _dco_doc:
            _old_sup = _dco_doc.get("supervisor_id", "")
            if _old_sup and _old_sup != body.supervisor_id and logger is not None:
                logger.warning(
                    "Admin %s overriding supervisor_id on DCO %s: %s → %s",
                    admin_id,
                    body.assignee_id,
                    _old_sup,
                    body.supervisor_id,
                )
            await dco_collection.update_one(
                {"_id": _dco_doc["_id"]},
                {
                    "$set": {
                        "supervisor_id": body.supervisor_id,
                        "supervisor_id_source": "admin_assignment",
                        "updated_at": _now_utc(),
                    }
                },
            )
        elif logger is not None:
            logger.warning(
                "admin_assign_stats_request: DCO %s not found in dco_collection; "
                "supervisor_id not propagated.",
                body.assignee_id,
            )

    # ── Notifications / audit log ─────────────────────────────────────────
    await _send_notification(
        body.assignee_id,
        role,
        "New Assignment",
        f"You have been assigned a new stats request (ID: {request_id}).",
        "stats_request_assigned",
    )

    _log(
        admin_id,
        "admin",
        "stats_assigned",
        f"Assigned stats request {request_id} to {role}:{body.assignee_id}",
    )

    return JSONResponse({
        "success":       True,
        "request_id":    request_id,
        "assignee_id":   body.assignee_id,
        "supervisor_id": body.supervisor_id,
        "assignment_id": assignment_id,
        "status":        "assigned",
    })
      
@router.post("/api/admin/stats-requests/{request_id}/reject")
async def admin_reject_stats_request(
    request_id: str,
    body: StatsRejectBody,
    request: Request,
):
    """Reject a stats request."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    col = _require_collection(stats_requests_collection, "stats_requests_collection")
    doc, filter_q = await _resolve_admin_request(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Stats request not found")

    await _update_stats_request_status(
        col,
        filter_q,
        request_id,
        doc,
        "rejected",
        {"rejected_at": _now_utc(), "rejection_reason": body.reason or "", "admin_id": admin_id},
        {
            "title": "Request rejected",
            "description": body.reason or "Request rejected by an administrator",
            "actor_id": admin_id,
            "actor_role": "admin",
        },
    )

    club_id = doc.get("club_id") or ""
    if club_id:
        await _send_notification(
            club_id, "club",
            "Stats Request Rejected",
            f"Your stats request has been rejected. Reason: {body.reason or 'N/A'}",
            "stats_request_rejected",
        )

    _log(admin_id, "admin", "stats_rejected", f"Rejected stats request {request_id}")
    return JSONResponse({
        "success":    True,
        "request_id": request_id,
        "status":     "rejected",
        "reason":     body.reason,
    })


@router.post("/api/admin/stats-requests/{request_id}/complete")
async def admin_complete_stats_request(
    request_id: str,
    request: Request,
):
    """Mark a stats request as completed."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    col = _require_collection(stats_requests_collection, "stats_requests_collection")
    doc, filter_q = await _resolve_admin_request(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Stats request not found")

    await _update_stats_request_status(
        col,
        filter_q,
        request_id,
        doc,
        "completed",
        {"completed_at": _now_utc(), "admin_id": admin_id},
        {
            "title": "Request completed",
            "description": "Request marked complete by an administrator",
            "actor_id": admin_id,
            "actor_role": "admin",
        },
    )

    club_id = doc.get("club_id") or ""
    if club_id:
        await _send_notification(
            club_id, "club",
            "Stats Request Completed",
            "Your stats request has been completed. Results are now available.",
            "stats_request_completed",
        )

    _log(admin_id, "admin", "stats_completed", f"Completed stats request {request_id}")
    return JSONResponse({
        "success":    True,
        "request_id": request_id,
        "status":     "completed",
    })


@router.get("/api/admin/match-centre/registered-clubs")
async def public_registered_clubs(
    q: str = "", level: str = "", category: str = "", mixed: bool = False,
    country: str = "", country_code: str = "",
    state: str = "", region: str = "", lga: str = "", subregion: str = "", city: str = "",
    limit: int = 30,
):
    """Registration-backed club directory with canonical venue resolution.

    Accepts both the legacy ``level`` and Match Centre ``category`` query names.
    Mixed fixtures deliberately omit the category constraint so cross-level
    competitions can select teams from different registered levels.
    """
    col=_require_collection(clubs_collection,"clubs_collection")
    limit=min(100,max(1,int(limit or 30)))
    terms=[]
    if q:
        safe=re.escape(q)
        terms.append({"$or":[{"club_name":{"$regex":safe,"$options":"i"}},{"team_name":{"$regex":safe,"$options":"i"}},{"name":{"$regex":safe,"$options":"i"}},{"full_name":{"$regex":safe,"$options":"i"}},{"club_id":{"$regex":safe,"$options":"i"}}]})
    requested_level = "" if mixed or str(mixed).strip().lower() in {"true", "1", "yes", "on"} else (category or level)
    if requested_level:
        safe=re.escape(requested_level)
        terms.append({"$or":[
            {"club_level":{"$regex":safe,"$options":"i"}},
            {"level":{"$regex":safe,"$options":"i"}},
            {"category":{"$regex":safe,"$options":"i"}},
            {"club_category":{"$regex":safe,"$options":"i"}},
            {"age_category":{"$regex":safe,"$options":"i"}},
            {"competition_level":{"$regex":safe,"$options":"i"}},
        ]})
    terms.extend(_admin_club_location_clauses(country,country_code,state,region,lga,subregion,city))
    query={"$and":terms} if terms else {}
    docs=await col.find(query).sort("club_name",1).limit(limit).to_list(limit)
    result=[];seen=set()
    for d in docs:
        x=_s(d); cid=str(x.get("club_id") or x.get("id") or x.get("_id") or ""); name=_match_name(x); key=(cid or name).casefold()
        if not name or key in seen: continue
        seen.add(key)
        primary=await _admin_resolve_venue(x.get("primary_ground_id")); secondary=await _admin_resolve_venue(x.get("secondary_ground_id"))
        pv=_admin_merge_club_venue(x,primary,False) or {}; sv=_admin_merge_club_venue(x,secondary,True) or {}
        result.append({
            **x,"id":cid,"club_id":cid,"name":name,"club_name":x.get("club_name") or name,"team_name":x.get("team_name") or x.get("club_name") or name,
            "level":x.get("club_level") or x.get("level") or x.get("category") or "","nickname":x.get("club_nickname") or "",
            "country":x.get("country") or "","country_code":str(x.get("country_code") or "").upper(),
            "state":x.get("state") or x.get("region") or x.get("province") or x.get("county") or "",
            "lga":x.get("lga") or x.get("local_area") or x.get("subregion") or x.get("district") or "","city":x.get("city") or x.get("town") or "",
            "primary_ground_id":pv.get("id") or x.get("primary_ground_id"),"secondary_ground_id":sv.get("id") or x.get("secondary_ground_id"),
            "primary_ground":pv or None,"secondary_ground":sv or None,
            "home_ground":pv.get("name") or x.get("stadium") or "","venue_id":pv.get("id") or x.get("primary_ground_id") or "",
            "venue_name":pv.get("name") or x.get("stadium") or "","stadium":pv.get("name") or x.get("stadium") or "",
            "venue_address":pv.get("address") or x.get("stadium_address") or "","venue_full_address":pv.get("full_address") or x.get("stadium_address") or "",
            "venue_country":pv.get("country") or x.get("country") or "","venue_country_code":str(pv.get("country_code") or x.get("country_code") or "").upper(),
            "venue_state":pv.get("state") or x.get("state") or "","venue_lga":pv.get("lga") or x.get("lga") or "","venue_city":pv.get("city") or x.get("city") or "",
            "venue_gps_lat":pv.get("gps_lat"),"venue_gps_lng":pv.get("gps_lng"),"venue_gps":pv.get("gps"),
            "gps_lat":pv.get("gps_lat") if pv.get("gps_lat") is not None else x.get("stadium_gps_lat"),
            "gps_lng":pv.get("gps_lng") if pv.get("gps_lng") is not None else x.get("stadium_gps_lng"),
            "gps":pv.get("gps") or ({"lat":x.get("stadium_gps_lat"),"lng":x.get("stadium_gps_lng")} if x.get("stadium_gps_lat") not in (None,"") and x.get("stadium_gps_lng") not in (None,"") else None),
            "venue_type":pv.get("venue_type") or "","surface_type":pv.get("surface_type") or "","capacity":pv.get("capacity"),
            "logo_url":x.get("logo_url") or x.get("logo") or x.get("avatar") or x.get("badge") or "",
            "secondary_venue_id":sv.get("id") or x.get("secondary_ground_id") or "","secondary_venue_name":sv.get("name") or x.get("stadium2") or "",
            "secondary_venue_address":sv.get("address") or x.get("stadium2_address") or "","secondary_venue_gps_lat":sv.get("gps_lat"),"secondary_venue_gps_lng":sv.get("gps_lng"),"secondary_venue_gps":sv.get("gps"),
        })
    return {"clubs":result,"results":result,"data":result,"total":len(result)}


@router.get("/api/admin/match-centre/teams")
async def match_centre_teams(request: Request, category: Optional[str] = None,
                             q: Optional[str] = None, country: Optional[str] = None,
                             state: Optional[str] = None, lga: Optional[str] = None,
                             city: Optional[str] = None):
    """Admin compatibility wrapper over registration-backed clubs."""
    await _require_admin(request)
    result = await public_registered_clubs(
        q=q or "", level=category or "", country=country or "",
        state=state or "", lga=lga or "", city=city or "", limit=100
    )
    return {"teams": result.get("clubs", []), "clubs": result.get("clubs", []), "results": result.get("clubs", [])}


@router.get("/api/admin/match-centre/venues")
async def match_centre_venues(request: Request, q: Optional[str] = None,
                              team: Optional[str] = None):
    await _require_admin(request)
    docs = []
    if database is not None:
        try:
            vc = database["venues"]
            query = {"$or": [{"name": {"$exists": True}}, {"venue_name": {"$exists": True}}]}
            if q:
                query = {"$and": [query, {"$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"venue_name": {"$regex": q, "$options": "i"}},
                    {"address": {"$regex": q, "$options": "i"}}]}]}
            docs = await vc.find(query).limit(80).to_list(80)
        except Exception:
            docs = []
    if team and clubs_collection is not None:
        club = await clubs_collection.find_one({"$or": [{"club_name": team}, {"team_name": team}, {"name": team}]})
        if club:
            docs.append({"name": club.get("venue_name") or club.get("stadium") or club.get("home_ground") or club.get("venue"),
                         "address": club.get("venue_address") or club.get("stadium_address"), "state": club.get("state")})
    seen, result = set(), []
    for d in docs:
        name = d.get("name") or d.get("venue_name") or d.get("stadium")
        if name and name not in seen:
            seen.add(name)
            result.append({"name": name, "address": d.get("address") or d.get("venue_address") or "",
                           "state": d.get("state") or d.get("venue_state") or ""})
    return {"venues": result[:100]}


@router.get("/api/admin/match-centre/supervisors")
async def match_centre_supervisors(request: Request):
    await _require_admin(request)
    col = _require_collection(supervisors_collection, "supervisors_collection")
    docs = await col.find({"is_active": {"$ne": False}}).limit(100).to_list(100)
    return {"supervisors": [_s(d) | {"name": _display_name(d)} for d in docs]}


@router.get("/api/admin/match-centre/matches")
async def match_centre_matches(request: Request, status: Optional[str] = None,
                               q: Optional[str] = None):
    await _require_admin(request)
    col = _require_collection(matches_collection, "matches_collection")
    await _materialize_accepted_matches(col)
    query: Dict[str, Any] = {"status": status} if status else {}
    if q:
        query["$or"] = [{"home_team": {"$regex": q, "$options": "i"}},
                        {"away_team": {"$regex": q, "$options": "i"}},
                        {"venue": {"$regex": q, "$options": "i"}},
                        {"category": {"$regex": q, "$options": "i"}}]
    docs = await col.find(query).limit(250).to_list(250)
    return {"matches": _ss(docs), "total": len(docs)}


@router.post("/api/admin/match-centre/matches")
async def create_match_centre_match(body: MatchCreateBody, request: Request):
    admin = await _require_admin(request)
    if body.home_team.strip().casefold() == body.away_team.strip().casefold():
        raise HTTPException(status_code=400, detail="Home and away teams must be different")
    ids = list(dict.fromkeys(body.supervisor_ids))
    if len(ids) > 3:
        raise HTTPException(status_code=400, detail="Assign between 0 and 3 supervisors")
    col = _require_collection(matches_collection, "matches_collection")
    doc = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    # Normalize the canonical geographic contract without collapsing tiers.
    doc["country"] = doc.get("country") or doc.get("country_name") or doc.get("venue_country") or ""
    doc["country_name"] = doc.get("country_name") or doc["country"]
    doc["country_code"] = (doc.get("country_code") or doc.get("venue_country_code") or "").upper()
    doc["state"] = doc.get("state") or doc.get("region") or doc.get("venue_state") or ""
    doc["region"] = doc["state"]
    doc["lga"] = doc.get("lga") or doc.get("local_area") or doc.get("venue_lga") or ""
    doc["local_area"] = doc["lga"]
    doc["city"] = doc.get("city") or doc.get("venue_city") or ""
    doc["venue_id"] = doc.get("venue_id") or ""
    if doc.get("gps") is None and doc.get("gps_lat") is not None and doc.get("gps_lng") is not None:
        doc["gps"] = {"lat": doc["gps_lat"], "lng": doc["gps_lng"]}
    if doc.get("gps") and isinstance(doc["gps"], dict):
        doc["gps_lat"] = doc["gps"].get("lat", doc.get("gps_lat"))
        doc["gps_lng"] = doc["gps"].get("lng", doc.get("gps_lng"))
    doc["venue_country"] = doc["country"]
    doc["venue_country_code"] = doc["country_code"]
    doc["venue_state"] = doc["state"]
    doc["venue_lga"] = doc["lga"]
    doc["venue_city"] = doc["city"]
    doc["venue_detailed_address"] = doc.get("venue_detailed_address") or ""
    doc.update({"match_id": "MAT-" + secrets.token_hex(8).upper(), "status": "scheduled",
                "supervisor_ids": ids, "created_by": admin.get("admin_id") or str(admin.get("_id")),
                "source": "Admin", "created_at": _now_utc(), "updated_at": _now_utc()})
    await col.insert_one(doc)
    return {"message": "Match created", "match": _s(doc)}


@router.patch("/api/admin/match-centre/matches/{match_id}/supervisors")
async def update_match_supervisors(match_id: str, body: MatchSupervisorsBody, request: Request):
    await _require_admin(request)
    ids = list(dict.fromkeys(body.supervisor_ids))
    if len(ids) > 3:
        raise HTTPException(status_code=400, detail="A match can have at most 3 supervisors")
    col = _require_collection(matches_collection, "matches_collection")
    result = await col.update_one({"$or": [{"match_id": match_id}, {"_id": _try_oid(match_id)}]},
                                  {"$set": {"supervisor_ids": ids, "updated_at": _now_utc()}})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"message": "Supervisors updated", "supervisor_ids": ids}



# ============================================================
# MATCH CENTRE API ALIASES
# ============================================================

@router.get("/api/admin/matches")
async def admin_matches_alias(request: Request, status: Optional[str]=None, q: Optional[str]=None):
    return await match_centre_matches(request=request,status=status,q=q)

@router.get("/api/admin/supervisors")
async def admin_supervisors_alias(request: Request):
    return await match_centre_supervisors(request=request)

@router.patch("/api/admin/matches/{match_id}/supervisors")
async def admin_match_supervisors_alias(match_id: str, body: MatchSupervisorsBody, request: Request):
    return await update_match_supervisors(match_id=match_id,body=body,request=request)

@router.post("/api/admin/matches")
async def admin_matches_create_alias(request: Request):
    admin=await _require_admin(request)
    try: data=await request.json()
    except Exception: raise HTTPException(status_code=400,detail="Invalid JSON body")
    home=str(data.get("home_team") or data.get("home") or data.get("home_team_name") or "").strip()
    away=str(data.get("away_team") or data.get("away") or data.get("away_team_name") or "").strip()
    date=str(data.get("match_date") or data.get("date") or "").strip()
    time=str(data.get("match_time") or data.get("time") or "").strip()
    venue=str(data.get("venue") or data.get("venue_name") or "").strip()
    if not home or not away or not date or not time or not venue: raise HTTPException(status_code=400,detail="home_team, away_team, match_date, match_time and venue are required")
    if home.casefold()==away.casefold(): raise HTTPException(status_code=400,detail="Home and away teams must be different")
    supers=list(dict.fromkeys(str(x) for x in (data.get("supervisor_ids") or data.get("supervisorIds") or []) if x not in (None,"")))
    if len(supers)>3: raise HTTPException(status_code=400,detail="A match can have at most 3 supervisors")
    doc={"match_id":"MAT-"+secrets.token_hex(8).upper(),"category":data.get("category") or data.get("match_category") or "","competition":data.get("competition") or data.get("competition_name") or "",
         "home_team_id":data.get("home_team_id") or "","away_team_id":data.get("away_team_id") or "","home_team":home,"away_team":away,"home":home,"away":away,
         "match_date":date,"match_time":time,"date":date,"time":time,"venue_id":data.get("venue_id") or "","venue":venue,"venue_name":venue,
         "country":data.get("country") or data.get("country_name") or "","country_code":str(data.get("country_code") or data.get("venue_country_code") or "").upper(),"country_name":data.get("country_name") or data.get("country") or "",
         "state":data.get("state") or data.get("region") or "","region":data.get("region") or data.get("state") or "","province":data.get("province") or "","county":data.get("county") or "",
         "lga":data.get("lga") or data.get("local_area") or data.get("venue_lga") or "","local_area":data.get("local_area") or data.get("lga") or data.get("venue_lga") or "","city":data.get("city") or data.get("venue_city") or "",
         "venue_country":data.get("venue_country") or data.get("country") or "","venue_country_code":str(data.get("venue_country_code") or data.get("country_code") or "").upper(),
         "venue_state":data.get("venue_state") or data.get("state") or data.get("region") or "","venue_lga":data.get("venue_lga") or data.get("lga") or "","venue_city":data.get("venue_city") or data.get("city") or "",
         "venue_detailed_address":data.get("venue_detailed_address") or data.get("detailed_address") or data.get("venue_address") or "",
         "gps":data.get("gps") or ({"lat":data.get("gps_lat"),"lng":data.get("gps_lng")} if data.get("gps_lat") is not None and data.get("gps_lng") is not None else None),
         "gps_lat":data.get("gps_lat") if data.get("gps_lat") is not None else (data.get("gps") or {}).get("lat"),
         "gps_lng":data.get("gps_lng") if data.get("gps_lng") is not None else (data.get("gps") or {}).get("lng"),
         "tracking_requirement":data.get("tracking_requirement") or ("required" if data.get("tracking") else "optional"),"tracking":bool(data.get("tracking")),
         "status":"scheduled","supervisor_ids":supers,"notes":data.get("notes") or "","source":data.get("source") or "Admin",
         "created_by":admin.get("admin_id") or str(admin.get("_id")),"created_at":_now_utc(),"updated_at":_now_utc()}
    col=_require_collection(matches_collection,"matches_collection")
    await col.insert_one(doc)
    return {"message":"Match created","match":_s(doc)}


# ============================================================
# MATCH CENTRE FRONTEND-COMPATIBILITY ALIASES
# ============================================================

@router.get("/api/admin/match-centre/match-categories")
async def match_centre_match_categories_alias(request: Request, q: Optional[str] = None):
    return await admin_match_categories(request=request, q=q)


@router.get("/api/admin/match-centre/competitions")
async def match_centre_competitions_alias(request: Request, q: Optional[str] = None):
    return await admin_competitions(request=request, q=q)


@router.get("/api/admin/match-centre/match-requests/accepted")
async def match_centre_accepted_requests_alias(request: Request, limit: int = 250):
    return await admin_accepted_match_requests_standalone(request=request, limit=limit)


@router.post("/api/admin/match-centre/match-requests/{request_id}/create-match")
async def match_centre_create_match_from_request_alias(request_id: str, request: Request):
    return await admin_create_match_from_request_standalone(request_id=request_id, request=request)


@router.get("/api/admin/teams")
async def admin_teams_alias(request: Request, category: Optional[str] = None, q: Optional[str] = None):
    return await match_centre_teams(request=request, category=category, q=q)

@router.get("/api/admin/venues")
async def admin_venues_alias(request: Request, q: Optional[str] = None, team: Optional[str] = None):
    return await match_centre_venues(request=request, q=q, team=team)

@router.get("/api/admin/match-categories")
async def admin_match_categories(request: Request, q: Optional[str] = None):
    await _require_admin(request)
    values = set()
    for col in (matches_collection, stats_requests_collection, clubs_collection):
        if col is None: continue
        try:
            docs = await col.find({}).limit(2000).to_list(2000)
            for d in docs:
                for key in ("category", "match_category", "category_name", "age_category", "team_category", "player_level"):
                    if d.get(key): values.add(str(d[key]).strip())
        except Exception: pass
    result = sorted(v for v in values if v)
    if q: result = [v for v in result if q.strip().lower() in v.lower()]
    return {"categories": [{"name": v, "value": v} for v in result]}

@router.get("/api/admin/competitions")
async def admin_competitions(request: Request, q: Optional[str] = None):
    await _require_admin(request)
    values = set()
    for col in (matches_collection, stats_requests_collection):
        if col is None: continue
        try:
            docs = await col.find({}).limit(2000).to_list(2000)
            for d in docs:
                for key in ("competition", "competition_name", "league"):
                    if d.get(key): values.add(str(d[key]).strip())
        except Exception: pass
    result = sorted(v for v in values if v)
    if q: result = [v for v in result if q.strip().lower() in v.lower()]
    return {"competitions": [{"name": v, "value": v} for v in result]}

@router.get("/api/admin/match-requests/accepted")
async def admin_accepted_match_requests_standalone(request: Request, limit: int = 250):
    await _require_admin(request)
    limit = min(500, max(1, limit)); rows = []
    for col in (match_requests_collection, stats_requests_collection):
        if col is None: continue
        try:
            rows.extend(await col.find({"status": {"$regex": "^(accepted|approved|confirmed)$", "$options": "i"}}).sort("created_at", -1).limit(limit).to_list(limit))
        except Exception: pass
    seen=set(); result=[]
    for d in rows:
        rid=str(d.get("request_id") or d.get("_id") or "")
        if rid and rid not in seen: seen.add(rid); result.append(_s(d))
    return {"requests": result[:limit], "results": result[:limit], "data": result[:limit]}

@router.post("/api/admin/match-requests/{request_id}/create-match")
async def admin_create_match_from_request_standalone(request_id: str, request: Request):
    admin=await _require_admin(request); col=_require_collection(matches_collection,"matches_collection")
    parent_id=request_id.split(":player:",1)[0] if ":player:" in request_id else request_id; source=None
    for src in (match_requests_collection, stats_requests_collection):
        if src is None: continue
        try: source=await src.find_one({"$or":[{"request_id":parent_id},{"_id":_try_oid(parent_id)}]})
        except Exception: source=None
        if source: break
    if not source: raise HTTPException(status_code=404,detail="Accepted match request not found")
    existing=await col.find_one({"$or":[{"source_request_id":parent_id},{"request_id":parent_id}]})
    if existing: return {"message":"Request already converted","match":_s(existing),"duplicate":True}
    def first(*keys,default=""):
        for k in keys:
            v=source.get(k)
            if v not in (None,""): return v
        return default
    home=str(first("home_team","home","home_club_name","club_a_name")); away=str(first("away_team","away","away_club_name","club_b_name"))
    date=str(first("match_date","date","event_date","proposed_date")); time=str(first("match_time","time","kickoff_time",default="00:00")); venue=str(first("venue","venue_name","proposed_venue","stadium"))
    if not home or not away or not date or not venue: raise HTTPException(status_code=400,detail="Accepted request is missing home team, away team, date or venue")
    if home.casefold()==away.casefold(): raise HTTPException(status_code=400,detail="Home and away teams must be different")
    doc={"match_id":"MAT-"+secrets.token_hex(8).upper(),"source_request_id":parent_id,"request_id":parent_id,"source":"Accepted club request","status":"scheduled","category":first("category","match_category","player_level",default="General"),"competition":first("competition","competition_name","league"),"home_team_id":first("home_team_id","home_club_id"),"away_team_id":first("away_team_id","away_club_id"),"home_team":home,"away_team":away,"home":home,"away":away,"match_date":date,"match_time":time,"date":date,"time":time,"venue_id":first("venue_id"),"venue":venue,"venue_name":venue,"country":first("country","country_name","venue_country"),"country_code":str(first("country_code","venue_country_code")).upper(),"state":first("state","region","venue_state"),"region":first("region","state","venue_state"),"lga":first("lga","venue_lga"),"city":first("city","venue_city"),"venue_country":first("venue_country","country","country_name"),"venue_country_code":str(first("venue_country_code","country_code")).upper(),"venue_state":first("venue_state","state","region"),"venue_lga":first("venue_lga","lga"),"venue_city":first("venue_city","city"),"venue_detailed_address":first("venue_detailed_address","venue_address","address"),"tracking_requirement":first("tracking_requirement",default="optional"),"tracking":bool(first("tracking",default=False)),"notes":first("notes"),"supervisor_ids":[],"created_by":admin.get("admin_id") or str(admin.get("_id")),"created_at":_now_utc(),"updated_at":_now_utc()}
    await col.insert_one(doc); return {"message":"Match created","match":_s(doc),"duplicate":False}


# ============================================================
# MATCH CENTRE FRONTEND CONTRACT BRIDGE
# ============================================================

@router.get("/api/admin/match-centre/session")
async def match_centre_auth_me(request: Request):
    """Compatibility auth check used by Match Centre page-show handling."""
    user = await _get_admin_from_request(request)
    return JSONResponse({
        "authenticated": True,
        "user": _s(user),
        "admin": _s(user),
        **_s(user),
    })


@router.post("/api/admin/match-centre/logout")
async def match_centre_auth_logout(request: Request):
    """Invalidate the browser auth cookie used by the Match Centre."""
    response = JSONResponse({"success": True, "message": "Logged out"})
    response.delete_cookie("auth_token", httponly=True, samesite="lax", path="/")
    return response


@router.get("/api/public/countries")
@router.get("/api/public/countries/")
async def match_centre_public_countries():
    countries = await _geo_documents("country")
    return JSONResponse(countries)


@router.get("/api/public/states")
async def match_centre_public_states(country_code: str = ""):
    """Compatibility endpoint for frontend state/region selectors."""
    items = await _geo_documents("region", country_code=country_code)
    return JSONResponse({"states": items, "regions": items, "data": items})


@router.get("/api/public/lgas")
async def match_centre_public_lgas(state: str = "", country_code: str = ""):
    """Compatibility endpoint for frontend LGA/subregion selectors."""
    items = await _geo_documents("subregion", country_code=country_code, region=state)
    return JSONResponse({"lgas": items, "subregions": items, "data": items})


@router.get("/api/public/countries/{country_code}/regions")
async def match_centre_public_regions(country_code: str):
    items = await _geo_documents("region", country_code=country_code)
    return JSONResponse({"regions": items, "region_label": "State / Region"})


@router.get("/api/public/countries/{country_code}/regions/{region}/subregions")
async def match_centre_public_subregions(country_code: str, region: str):
    items = await _geo_documents("subregion", country_code=country_code, region=region)
    return JSONResponse({"subregions": items, "subregion_label": "LGA / Local Area"})


@router.get("/api/admin/match-centre/public-venues")
async def match_centre_public_venues(limit: int = 100, q: str = ""):
    """Public venue catalogue consumed by the Match Centre searchable venue field."""
    limit = min(500, max(1, limit))
    docs = []
    for col in _db_collection_candidates("venues", "stadiums", "grounds"):
        try:
            query = {}
            if q:
                query = {"$or": [
                    {"name": {"$regex": q, "$options": "i"}},
                    {"venue_name": {"$regex": q, "$options": "i"}},
                    {"address": {"$regex": q, "$options": "i"}},
                ]}
            docs = await col.find(query).limit(limit).to_list(limit)
            if docs: break
        except Exception:
            continue
    result=[]; seen=set()
    for d in docs:
        x = _s(d)
        name = _doc_value(x, "name", "venue_name", "stadium", "ground")
        if not name or name.casefold() in seen: continue
        seen.add(name.casefold())
        lat = _doc_value(x, "gps_lat", "venue_gps_lat", "latitude", "lat")
        lng = _doc_value(x, "gps_lng", "venue_gps_lng", "longitude", "lng")
        gps = _doc_value(x, "gps", "venue_gps")
        if gps is None and lat is not None and lng is not None:
            gps = {"lat": lat, "lng": lng}
        result.append({
            **x, "name": name,
            "address": _doc_value(x, "address", "venue_address", "detailed_address", "full_address"),
            "full_address": _doc_value(x, "full_address", "venue_full_address", "address", "venue_address", "detailed_address"),
            "country": _doc_value(x, "country", "venue_country"),
            "country_code": str(_doc_value(x, "country_code", "venue_country_code", default="")).upper(),
            "state": _doc_value(x, "state", "venue_state", "region"),
            "lga": _doc_value(x, "lga", "venue_lga", "subregion"),
            "city": _doc_value(x, "city", "venue_city"),
            "gps_lat": lat, "gps_lng": lng, "gps": gps,
        })
    return JSONResponse({"venues": result})


@router.post("/api/admin/matches/{match_id}/supervisors")
async def admin_match_supervisors_post_alias(match_id: str, body: MatchSupervisorsBody, request: Request):
    """Exact POST variant emitted by match-centre.html; canonical operation remains PATCH."""
    return await update_match_supervisors(match_id=match_id, body=body, request=request)


@router.post("/api/admin/matches/")
async def admin_matches_create_trailing_slash(body: MatchCreateBody, request: Request):
    """Exact trailing-slash variant emitted by the Match Centre."""
    return await create_match_centre_match(body=body, request=request)


@router.get("/api/admin/match-centre/dco/assignments")
async def match_centre_dco_assignments(request: Request, limit: int = 200):
    """Admin-only read bridge, kept off the DCO-authenticated API namespace."""
    await _require_admin(request)
    col = _require_collection(dco_assignments_collection, "dco_assignments_collection")
    docs = await col.find({}).sort("created_at", -1).limit(min(500, max(1, limit))).to_list(min(500, max(1, limit)))
    return JSONResponse({"assignments": _ss(docs), "results": _ss(docs), "data": _ss(docs), "total": len(docs)})


@router.get("/api/admin/dco/submissions")
async def admin_match_centre_dco_submissions(request: Request, limit: int = 200):
    """Admin-scoped submissions bridge; avoids collisions with the DCO-only route."""
    await _require_admin(request)
    docs=[]
    for col in _db_collection_candidates("dco_submissions", "stats_submissions", "submissions", "match_submissions"):
        try:
            docs = await col.find({}).sort("created_at", -1).limit(min(500, max(1, limit))).to_list(min(500, max(1, limit)))
            if docs: break
        except Exception:
            continue
    data=_ss(docs)
    return JSONResponse({"submissions": data, "results": data, "data": data, "total": len(data)})


@router.get("/api/admin/match-centre/dco/submissions")
async def match_centre_dco_submissions(request: Request, limit: int = 200):
    """Admin-only read bridge, kept off the DCO-authenticated API namespace."""
    await _require_admin(request)
    docs=[]
    for col in _db_collection_candidates("dco_submissions", "stats_submissions", "submissions", "match_submissions"):
        try:
            docs = await col.find({}).sort("created_at", -1).limit(min(500, max(1, limit))).to_list(min(500, max(1, limit)))
            if docs: break
        except Exception:
            continue
    data=_ss(docs)
    return JSONResponse({"submissions": data, "results": data, "data": data, "total": len(data)})


@router.get("/api/admin/match-centre/supervisor/matches")
async def match_centre_supervisor_matches(request: Request, limit: int = 200):
    """Read bridge for supervisor-visible matches used by ecosystem synchronisation."""
    await _require_admin(request)
    col = _require_collection(matches_collection, "matches_collection")
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))
    sup = await _find_user(admin_id)
    sup_id = admin_id
    if sup:
        doc, role, id_field = sup
        if role == "supervisor":
            sup_id = doc.get("supervisor_id") or doc.get("user_id") or admin_id
    query = {"$or": [
        {"supervisor_ids": sup_id}, {"assigned_supervisor_id": sup_id},
        {"supervisor_id": sup_id},
    ]}
    docs = await col.find(query).sort("match_date", 1).limit(min(500, max(1, limit))).to_list(min(500, max(1, limit)))
    return JSONResponse({"matches": _ss(docs), "results": _ss(docs), "data": _ss(docs), "total": len(docs)})


@router.get("/api/admin/match-centre/supervisor/available-dcos")
async def match_centre_supervisor_available_dcos(request: Request, limit: int = 200, country: str = "Nigeria", state: str = "", lga: str = "", city: str = ""):
    """Admin-compatible availability bridge for the Match Centre synchroniser."""
    await _require_admin(request)
    col = _require_collection(dco_collection, "dco_collection")
    filt = build_venue_location_filter(country=get_country_name(country) or country, state=state, lga=lga, city=city)
    docs = await col.find(filt or {}).sort("created_at", -1).limit(min(500, max(1, limit))).to_list(min(500, max(1, limit)))
    data=_ss(docs)
    return JSONResponse({"dcos": data, "users": data, "results": data, "data": data, "total": len(data)})
