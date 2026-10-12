"""
EnejiStats DCO dashboard routes.

This module is intentionally limited to requests made by the supplied
``dco-dashboard.html`` file.  Match tracking, widget persistence, assignment
accept/decline, and liveness routes live in ``stats_tracker_routes.py``.

Registration from the application's main.py:

    import dco_dashboard_routes as _dco_dashboard
    _dco_dashboard._setup_dependencies(globals())
    app.include_router(_dco_dashboard.router)

The module uses the same dependency-injection convention as the supplied
backend.  It does not import main.py, which prevents circular imports.
"""

# Integration contract: this router owns the main DCO dashboard endpoints.
# Register exactly once alongside stats_tracker_routes_aligned.router.
# This module owns the shared GET /api/dco/user-info endpoint; do not register
# another handler for that path in the Stats Tracker router.


from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import ReturnDocument


router = APIRouter(tags=["DCO dashboard"])

_READY = False
_database = None
dco_collection = None
dco_tokens_collection = None
players_collection = None
clubs_collection = None
player_stats_collection = None
activity_history_collection = None
support_tickets_collection = None
support_messages_collection = None
payment_intents_collection = None
dco_assignments_collection = None

get_current_user = None
get_dco_user = None
normalize_role = None
MongoSerializer = None
logger = None
upload_to_cloudinary = None
deduct_tokens = None
pricing_service = None
DEFAULT_DCO_RATES: Dict[str, Any] = {}
BANK_TRANSFER_DETAILS: Any = None


def _setup_dependencies(main_globals: dict) -> None:
    """Inject shared application state from main.py exactly once."""
    global _READY, _database, dco_collection, dco_tokens_collection
    global players_collection, clubs_collection, player_stats_collection, activity_history_collection
    global support_tickets_collection, support_messages_collection
    global payment_intents_collection, dco_assignments_collection
    global get_current_user, get_dco_user, normalize_role
    global MongoSerializer, logger, upload_to_cloudinary, deduct_tokens
    global pricing_service, DEFAULT_DCO_RATES, BANK_TRANSFER_DETAILS

    if _READY:
        return

    _database = main_globals["database"]

    def collection(name: str, global_name: str) -> Any:
        value = main_globals.get(global_name)
        return value if value is not None else _database[name]

    dco_collection = collection("dco", "dco_collection")
    dco_tokens_collection = collection("dco_tokens", "dco_tokens_collection")
    players_collection = collection("players", "players_collection")
    clubs_collection = collection("clubs", "clubs_collection")
    player_stats_collection = collection("player_stats", "player_stats_collection")
    activity_history_collection = collection("activity_history", "activity_history_collection")
    support_tickets_collection = collection("support_tickets", "support_tickets_collection")
    support_messages_collection = collection("support_messages", "support_messages_collection")
    payment_intents_collection = collection("payment_intents", "payment_intents_collection")
    dco_assignments_collection = collection("dco_assignments", "dco_assignments_collection")

    get_current_user = main_globals["get_current_user"]
    get_dco_user = main_globals.get("get_dco_user", get_current_user)
    normalize_role = main_globals["normalize_role"]
    MongoSerializer = main_globals.get("MongoSerializer")
    logger = main_globals.get("logger")
    upload_to_cloudinary = main_globals.get("upload_to_cloudinary")
    deduct_tokens = main_globals.get("deduct_tokens")
    pricing_service = main_globals.get("pricing_service")
    DEFAULT_DCO_RATES = main_globals.get("DEFAULT_DCO_RATES", {}) or {}
    BANK_TRANSFER_DETAILS = main_globals.get("BANK_TRANSFER_DETAILS")
    _READY = True


def _now() -> Any:
    if MongoSerializer is not None and hasattr(MongoSerializer, "now_utc"):
        return MongoSerializer.now_utc()
    return MongoSerializer.now_utc()


def _serialize(value: Any) -> Any:
    return MongoSerializer.serialize_value(value)


def _dco_id(document: dict) -> str:
    return str(
        document.get("dco_id")
        or document.get("data_scout_id")
        or document.get("user_id")
        or document.get("_id")
        or ""
    )


def _id_filter(identifier: str) -> Dict[str, Any]:
    clauses: List[Dict[str, Any]] = [
        {"dco_id": identifier},
        {"data_scout_id": identifier},
        {"user_id": identifier},
    ]
    if ObjectId.is_valid(str(identifier)):
        clauses.append({"_id": ObjectId(str(identifier))})
    return {"$or": clauses}


async def _get_dco(identifier: str) -> dict:
    document = await dco_collection.find_one(_id_filter(identifier))
    if not document:
        raise HTTPException(status_code=404, detail="DCO not found")
    return document


def _authorize(current_user: dict, identifier: str) -> None:
    try:
        role = normalize_role(current_user.get("role") or current_user.get("user_type") or "")
    except (ValueError, TypeError):
        role = ""
    if role in {"admin", "supervisor"}:
        return
    if role != "dco":
        raise HTTPException(status_code=403, detail="DCO access required")
    owner_ids = {
        str(current_user.get("dco_id") or ""),
        str(current_user.get("data_scout_id") or ""),
        str(current_user.get("user_id") or ""),
        str(current_user.get("_id") or ""),
    }
    if str(identifier) not in owner_ids:
        raise HTTPException(status_code=403, detail="Access denied")


async def _token_balance(identifier: str) -> int:
    wallet = await dco_tokens_collection.find_one(
        {"$or": [{"dco_id": identifier}, {"user_id": identifier}]}
    )
    return int((wallet or {}).get("balance", 0))


async def _upload(file: UploadFile, user_type: str, category: str) -> str:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if upload_to_cloudinary is None:
        raise HTTPException(status_code=503, detail="File storage is not configured")
    return await upload_to_cloudinary(
        content,
        filename=file.filename or "upload.bin",
        user_type=user_type,
        file_category=category,
    )


def _log_warning(message: str, *args: Any) -> None:
    if logger is not None and hasattr(logger, "warning"):
        logger.warning(message, *args)


class SupportTicketRequest(BaseModel):
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    role: Optional[str] = "dco"

    class Config:
        extra = "allow"


class SupportMessageRequest(BaseModel):
    sender: Optional[str] = "user"
    message: Optional[str] = None
    text: Optional[str] = None

    class Config:
        extra = "allow"


class PayoutRequest(BaseModel):
    amount: float
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.get("/api/dco/user-info")
async def dco_user_info(request: Request):
    """Shared identity endpoint used by both supplied dashboard pages."""
    user = await get_dco_user(request)
    return JSONResponse(_serialize(user))


@router.get("/api/dco/registration-stats")
async def dco_registration_stats(request: Request):
    identifier = _dco_id(await get_dco_user(request))
    levels = ["Professional", "Semi-professional", "Academy", "Local", "University"]

    async def count(collection: Any, level: str, level_keys: List[str]) -> int:
        # Exact matching prevents "Professional" from also matching
        # "Semi-professional" in the Dashboard registration snapshot.
        exact_level = {"$regex": f"^{re.escape(level)}$", "$options": "i"}
        return await collection.count_documents(
            {
                "$and": [
                    {"$or": [{"registered_by": identifier}, {"registered_by_dco_id": identifier}]},
                    {"$or": [{key: exact_level} for key in level_keys]},
                ]
            }
        )

    player_counts = [await count(players_collection, level, ["category", "player_level"]) for level in levels]
    club_counts = [await count(clubs_collection, level, ["category", "club_level"]) for level in levels]
    return JSONResponse(
        {
            "players": dict(zip(levels, player_counts)),
            "clubs": dict(zip(levels, club_counts)),
            "totalClubs": sum(club_counts),
        }
    )


@router.get("/api/dco/dashboard/venues")
async def dco_venues(request: Request, count_only: bool = False):
    identifier = _dco_id(await get_dco_user(request))
    venues = _database["venues"]
    query = {"$or": [{"registered_by": identifier}, {"registered_by_dco_id": identifier}, {"dco_id": identifier}]}
    total = await venues.count_documents(query)
    if count_only:
        return JSONResponse({"count": total, "total": total})
    rows = await venues.find(query).sort("created_at", -1).limit(100).to_list(length=100)
    return JSONResponse({"venues": _serialize(rows), "count": total, "total": total})


@router.post("/api/dco/update-bio")
async def dco_update_bio(
    request: Request,
    playerId: Optional[str] = Form(None),
    target_id: Optional[str] = Form(None),
    bio: str = Form(""),
    achievements: str = Form(""),
):
    identifier = _dco_id(await get_dco_user(request))
    target = playerId or target_id
    if not target:
        raise HTTPException(status_code=422, detail="playerId is required")
    player_clauses: List[Dict[str, Any]] = [{"player_id": target}, {"user_id": target}]
    if ObjectId.is_valid(target):
        player_clauses.append({"_id": ObjectId(target)})
    player = await players_collection.find_one({"$or": player_clauses})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # The external registration iframe sends achievements as a JSON array.
    # Accept that canonical shape, while retaining compatibility with legacy
    # comma-separated submissions.
    achievement_values: List[Any] = []
    raw_achievements = str(achievements or "").strip()
    if raw_achievements:
        try:
            parsed = json.loads(raw_achievements)
            if isinstance(parsed, list):
                achievement_values = [item for item in parsed if item not in (None, "", {})]
            else:
                achievement_values = [str(parsed).strip()] if str(parsed).strip() else []
        except (TypeError, ValueError, json.JSONDecodeError):
            achievement_values = [item.strip() for item in raw_achievements.split(",") if item.strip()]
    update: Dict[str, Any] = {"bio": bio, "updated_at": _now()}
    if raw_achievements:
        update["achievements"] = achievement_values
    await players_collection.update_one({"_id": player["_id"]}, {"$set": update})
    if deduct_tokens is not None:
        try:
            await deduct_tokens(
                user_id=identifier,
                user_type="dco",
                amount=1,
                admin_id="system",
                reason=f"Bio update for {target}",
            )
        except Exception as exc:
            _log_warning("DCO bio token deduction failed: %s", exc)
    await activity_history_collection.insert_one(
        {"actor_id": identifier, "actor_role": "dco", "type": "bio_updated", "target_id": target, "created_at": _now()}
    )
    return JSONResponse({"success": True, "player_id": target})


@router.post("/api/dco/update-availability")
async def dco_update_availability(
    request: Request,
    available: Optional[str] = Form(None),
    is_available: Optional[str] = Form(None),
):
    identifier = _dco_id(await get_dco_user(request))
    raw = str(available if available is not None else is_available if is_available is not None else "true").lower()
    flag = raw in {"true", "1", "yes", "on"}
    await dco_collection.update_one(_id_filter(identifier), {"$set": {"is_available": flag, "updated_at": _now()}})
    return JSONResponse({"success": True, "is_available": flag})


@router.get("/api/dco/search-players")
async def dco_search_players(request: Request, q: str = "", type: str = "player"):
    await get_dco_user(request)
    query = q.strip()
    entity_type = type.strip().lower()
    if not query:
        return JSONResponse({"results": []})
    collection = players_collection
    id_field = "player_id"
    name_fields = ["firstName", "middleName", "lastName"]
    search_fields = ["firstName", "lastName", "middleName", "email", "club", "full_name"]
    if entity_type == "club":
        collection = _database["clubs"]
        id_field = "club_id"
        name_fields = ["club_name"]
        search_fields = ["club_name", "club_nickname", "email", "address", "city"]
    clauses = [{field: {"$regex": re.escape(query), "$options": "i"}} for field in search_fields]
    clauses.append({id_field: query})
    rows = await collection.find({"$or": clauses}).limit(20).to_list(length=20)
    results = []
    for row in rows:
        item = _serialize(row)
        name = " ".join(str(item.get(key, "")) for key in name_fields).strip() or item.get("club_name", "")
        results.append(
            {
                "_id": item.get("_id", ""),
                "id": item.get(id_field, ""),
                id_field: item.get(id_field, ""),
                "name": name,
                "email": item.get("email", ""),
                "category": item.get("category") or item.get("club_level") or item.get("player_level", ""),
                "photo": item.get("photo") or item.get("profileImage") or item.get("logo") or "",
                "type": entity_type,
                "data": item,
            }
        )
    return JSONResponse({"results": results})


@router.post("/api/dco/update-profile")
async def dco_update_profile(
    request: Request,
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    lga: Optional[str] = Form(None),
    languages: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    identifier = _dco_id(await get_dco_user(request))
    update: Dict[str, Any] = {}
    for key, value in {"full_name": full_name, "phone": phone, "state": state, "lga": lga, "bio": bio}.items():
        if value is not None:
            update[key] = value.strip()
    if languages is not None:
        update["languages"] = [part.strip() for part in languages.split(",") if part.strip()]
    if photo is not None and photo.filename:
        # Enforce the same contract as the unified Dashboard editor on the API
        # itself; client-side validation must never be the security boundary.
        filename = (photo.filename or "").lower()
        content_type = str(photo.content_type or "").lower()
        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if content_type not in allowed_types and not filename.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            raise HTTPException(status_code=400, detail="Profile photo must be JPG, PNG, WEBP or GIF")
        content = await photo.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty profile photo")
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Profile photo must not exceed 5 MB")
        if upload_to_cloudinary is None:
            raise HTTPException(status_code=503, detail="File storage is not configured")
        url = await upload_to_cloudinary(
            content,
            filename=photo.filename or "profile-photo",
            user_type="dco",
            file_category="profiles",
        )
        update.update({"photo": url, "profileImage": url, "avatar": url})
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    update["updated_at"] = _now()
    await dco_collection.update_one(_id_filter(identifier), {"$set": update})
    return JSONResponse({"success": True, "updated": list(update.keys())})



async def _token_packages() -> List[Dict[str, Any]]:
    """Return the authoritative DCO token package catalog from pricing_service."""
    if pricing_service is None or not hasattr(pricing_service, "get_token_packages"):
        return []
    raw = pricing_service.get_token_packages("dco")
    if hasattr(raw, "__await__"):
        raw = await raw
    packages: List[Dict[str, Any]] = []
    for index, item in enumerate(raw or []):
        if not isinstance(item, dict):
            continue
        package = dict(item)
        key = str(package.get("key") or package.get("id") or package.get("plan_id") or package.get("_id") or package.get("name") or f"package_{index}")
        base_tokens = int(package.get("tokens") or package.get("token_quantity") or package.get("quantity") or 0)
        bonus_tokens = int(package.get("bonus_tokens") or package.get("bonus") or 0)
        price = package.get("price")
        if price is None:
            price = package.get("amount", 0)
        try:
            price = float(price or 0)
        except (TypeError, ValueError):
            price = 0.0
        package.update({
            "key": key,
            "id": package.get("id") or key,
            "plan_id": package.get("plan_id") or key,
            "price": price,
            "amount": price,
            "tokens": base_tokens,
            "bonus_tokens": bonus_tokens,
            "total_tokens": base_tokens + bonus_tokens,
            "label": package.get("label") or package.get("name") or f"{base_tokens} Tokens",
        })
        packages.append(package)
    return packages


async def _find_token_package(plan_id: str) -> Optional[Dict[str, Any]]:
    wanted = str(plan_id or "").strip()
    if not wanted:
        return None
    for package in await _token_packages():
        keys = {
            str(package.get("key") or ""),
            str(package.get("id") or ""),
            str(package.get("plan_id") or ""),
            str(package.get("_id") or ""),
            str(package.get("name") or ""),
        }
        if wanted in keys:
            return package
    return None


async def _token_wallet_document(identifier: str) -> Dict[str, Any]:
    wallet = await dco_tokens_collection.find_one(
        {"$or": [{"dco_id": identifier}, {"user_id": identifier}]}
    )
    return wallet or {}


async def _earnings_snapshot(identifier: str) -> Dict[str, Any]:
    rows = await player_stats_collection.find({
        "dco_id": identifier,
        "status": {"$in": ["submitted", "approved", "verified", "completed", "paid"]},
    }).sort("submitted_at", -1).limit(1000).to_list(length=1000)
    doc = await _get_dco(identifier)
    tier = str(doc.get("tier", "1"))
    rates = DEFAULT_DCO_RATES.get(f"tier{tier}", DEFAULT_DCO_RATES.get(tier, {})) or {}
    activities: List[Dict[str, Any]] = []
    pending = 0.0
    total = 0.0
    paid = 0.0
    for row in rows:
        item = _serialize(row)
        category = str(
            item.get("match_category") or item.get("player_level") or "other"
        ).lower().replace(" ", "_")
        amount = float(rates.get(category, rates.get("other", 500)))
        status = str(item.get("status") or "submitted").lower()
        total += amount
        if status == "paid":
            paid += amount
        else:
            pending += amount
        match = item.get("match") or {}
        activities.append({
            "match": f"{match.get('homeTeam', '')} vs {match.get('awayTeam', '')}".strip(),
            "entity": item.get("player_name") or item.get("club_name") or "—",
            "category": category,
            "amount": amount,
            "status": item.get("status", "submitted"),
            "date": item.get("submitted_at") or item.get("created_at") or "",
        })
    return {
        "total_earnings": total,
        "total_earned": total,
        "paid_amount": paid,
        "pending_amount": pending,
        "available_amount": pending,
        "activities": activities,
        "rates": rates,
        "tier": tier,
    }


class TokenPurchaseIntentRequest(BaseModel):
    plan_id: str
    role: Optional[str] = "DCO"


@router.get("/api/dco/token-info")
async def dco_token_info(request: Request):
    identifier = _dco_id(await get_dco_user(request))
    wallet = await dco_tokens_collection.find_one({"$or": [{"dco_id": identifier}, {"user_id": identifier}]})
    packages = await _token_packages()
    return JSONResponse(
        {
            "balance": int((wallet or {}).get("balance", 0)),
            "expiry": _serialize((wallet or {}).get("expiry_date")) or "",
            "packages": packages,
            "bank_details": BANK_TRANSFER_DETAILS,
        }
    )



@router.post("/api/dco/token-purchase/intent")
async def dco_token_purchase_intent(request: Request, payload: TokenPurchaseIntentRequest):
    identifier = _dco_id(await get_dco_user(request))
    package = await _find_token_package(payload.plan_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid or unavailable token package")
    reference = f"TKN-{MongoSerializer.now_utc().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    now = _now()
    record = {
        "dco_id": identifier,
        "user_type": str(payload.role or "DCO").lower(),
        "plan_id": package["key"],
        "plan": package,
        "amount": float(package.get("price") or 0),
        "tokens": int(package.get("tokens") or 0) + int(package.get("bonus_tokens") or 0),
        "reference": reference,
        "status": "intent_created",
        "created_at": now,
        "updated_at": now,
    }
    result = await payment_intents_collection.insert_one(record)
    return JSONResponse(_serialize({
        "success": True,
        "intent_id": str(result.inserted_id),
        "intentId": str(result.inserted_id),
        "reference": reference,
        "status": "intent_created",
        "plan": package,
        "bank_details": BANK_TRANSFER_DETAILS,
    }))


@router.post("/api/dco/token-purchase")
async def dco_token_purchase(
    request: Request,
    proof: UploadFile = File(...),
    plan_id: str = Form(...),
    tx_ref: str = Form(...),
    role: str = Form("DCO"),
    intent_id: Optional[str] = Form(None),
):
    identifier = _dco_id(await get_dco_user(request))
    tx_ref = str(tx_ref or "").strip()
    plan_id = str(plan_id or "").strip()
    if not tx_ref:
        raise HTTPException(status_code=400, detail="Transfer reference is required")
    package = await _find_token_package(plan_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid or unavailable token package")

    filename = (proof.filename or "").lower()
    content_type = str(proof.content_type or "").lower()
    allowed_types = {"image/jpeg", "image/png", "application/pdf"}
    if content_type not in allowed_types and not filename.endswith((".jpg", ".jpeg", ".png", ".pdf")):
        raise HTTPException(status_code=400, detail="Only JPG, PNG and PDF payment proofs are allowed")

    content = await proof.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty payment proof")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Payment proof must not exceed 10 MB")

    if upload_to_cloudinary is None:
        raise HTTPException(status_code=503, detail="File storage is not configured")
    proof_url = await upload_to_cloudinary(
        content,
        filename=proof.filename or "payment-proof",
        user_type="dco",
        file_category="payment-proofs",
    )

    now = _now()
    existing = None
    if intent_id and ObjectId.is_valid(intent_id):
        existing = await payment_intents_collection.find_one(
            {"_id": ObjectId(intent_id), "dco_id": identifier}
        )

    if existing:
        if str(existing.get("plan_id") or "") != str(package.get("key") or ""):
            raise HTTPException(status_code=400, detail="The payment intent does not match the selected token package")
        if str(existing.get("status") or "").lower() in {"approved", "paid", "completed", "success"}:
            raise HTTPException(status_code=409, detail="This payment intent has already been processed")
        # The intent belongs to the authenticated DCO. Preserve its generated
        # reference when the wizard supplies the same reference, but store the
        # actual transfer reference for reconciliation.
        await payment_intents_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "plan_id": package["key"],
                "plan": package,
                "amount": float(package.get("price") or 0),
                "tokens": int(package.get("tokens") or 0) + int(package.get("bonus_tokens") or 0),
                "reference": tx_ref.strip(),
                "intent_reference": existing.get("reference"),
                "proof_url": proof_url,
                "status": "pending",
                "updated_at": now,
            }},
        )
        intent_identifier = str(existing["_id"])
    else:
        # Backwards-compatible direct submission path.
        record = {
            "dco_id": identifier,
            "user_type": str(role or "DCO").lower(),
            "plan_id": package["key"],
            "plan": package,
            "amount": float(package.get("price") or 0),
            "tokens": int(package.get("tokens") or 0) + int(package.get("bonus_tokens") or 0),
            "reference": tx_ref.strip(),
            "proof_url": proof_url,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        result = await payment_intents_collection.insert_one(record)
        intent_identifier = str(result.inserted_id)

    return JSONResponse({
        "success": True,
        "intent_id": intent_identifier,
        "intentId": intent_identifier,
        "status": "pending",
        "tx_ref": tx_ref.strip(),
        "reference": tx_ref.strip(),
    })



@router.get("/api/dco/token-packages")
async def dco_token_packages(request: Request):
    await get_dco_user(request)
    return JSONResponse({"packages": await _token_packages()})


@router.get("/api/dco/token-purchases/{purchase_id}")
async def dco_token_purchase_detail(purchase_id: str, request: Request):
    identifier = _dco_id(await get_dco_user(request))
    query: Dict[str, Any] = {"dco_id": identifier}
    if ObjectId.is_valid(purchase_id):
        query["_id"] = ObjectId(purchase_id)
    else:
        query["reference"] = purchase_id
    row = await payment_intents_collection.find_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Token purchase not found")
    return JSONResponse({"purchase": _serialize(row)})


@router.get("/api/dco/{id}/token-wallet")
async def dco_token_wallet(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    wallet = await _token_wallet_document(id)
    safe_wallet = {
        "balance": int(wallet.get("balance", 0)),
        "available_tokens": int(wallet.get("balance", 0)),
        "expiry_date": _serialize(wallet.get("expiry_date")) or "",
        "used_this_month": int(wallet.get("used_this_month") or wallet.get("used_tokens_this_month") or wallet.get("used") or 0),
        "pending_tokens": int(wallet.get("pending_tokens") or wallet.get("pending_credit") or wallet.get("pending") or 0),
        "purchased_tokens": int(wallet.get("purchased_tokens") or wallet.get("tokens_purchased") or wallet.get("purchased") or 0),
        "transactions": wallet.get("transactions") if isinstance(wallet.get("transactions"), list) else [],
        "status": wallet.get("status") or "active",
        "last_transaction_at": wallet.get("last_transaction_at") or wallet.get("lastTransactionAt"),
    }
    return JSONResponse({"wallet": _serialize(safe_wallet), **_serialize(safe_wallet)})


@router.get("/api/dco/{id}/token-transactions")
async def dco_token_transactions(
    id: str,
    request: Request,
    page: int = 1,
    limit: int = 10,
    search: str = "",
    type: str = "",
):
    user = await get_current_user(request)
    _authorize(user, id)
    page = max(1, page)
    limit = min(100, max(1, limit))
    rows = await payment_intents_collection.find({"dco_id": id}).sort("created_at", -1).limit(2000).to_list(length=2000)
    wallet = await _token_wallet_document(id)
    txs: List[Dict[str, Any]] = []
    for row in rows:
        item = _serialize(row)
        status = str(item.get("status") or "pending").lower()
        requested = int(item.get("tokens") or 0)
        txs.append({
            "id": item.get("_id"),
            "reference": item.get("reference") or item.get("tx_ref"),
            "date": item.get("created_at"),
            "activity": "Token Purchase",
            "type": "purchase",
            "tokens": requested if status in {"approved", "completed", "paid", "success"} else 0,
            "requested_tokens": requested,
            "status": status,
            "amount": item.get("amount", 0),
            "plan_id": item.get("plan_id"),
        })
    native = wallet.get("transactions")
    if isinstance(native, list):
        for item in native:
            if isinstance(item, dict):
                txs.append(_serialize(item))
    q = search.strip().lower()
    if q:
        txs = [x for x in txs if q in str(x).lower()]
    if type:
        type_l = type.lower()
        txs = [x for x in txs if str(x.get("type") or "").lower() == type_l]
    total = len(txs)
    start = (page - 1) * limit
    return JSONResponse({
        "items": txs[start:start + limit],
        "transactions": txs[start:start + limit],
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": max(1, (total + limit - 1) // limit),
    })


@router.get("/api/dco/{id}/earnings/summary")
async def dco_earnings_summary(id: str, request: Request, range: str = "month"):
    user = await get_current_user(request)
    _authorize(user, id)
    snap = await _earnings_snapshot(id)
    return JSONResponse({
        "range": range,
        "total_earnings": snap["total_earnings"],
        "total_earned": snap["total_earned"],
        "paid_amount": snap["paid_amount"],
        "pending_amount": snap["pending_amount"],
        "available_amount": snap["available_amount"],
        "activity_count": len(snap["activities"]),
    })


@router.get("/api/dco/{id}/earnings/activities")
async def dco_earnings_activities(id: str, request: Request, range: str = "month"):
    user = await get_current_user(request)
    _authorize(user, id)
    snap = await _earnings_snapshot(id)
    return JSONResponse({"range": range, "activities": snap["activities"]})


@router.get("/api/dco/{id}/earnings/rates")
async def dco_earnings_rates(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    snap = await _earnings_snapshot(id)
    return JSONResponse({"tier": snap["tier"], "rates": snap["rates"]})


@router.get("/api/dco/{id}/payout-requests/{payout_id}")
async def dco_payout_detail(id: str, payout_id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    query: Dict[str, Any] = {"dco_id": id}
    if ObjectId.is_valid(payout_id):
        query["_id"] = ObjectId(payout_id)
    else:
        query["reference"] = payout_id
    row = await _database["dco_payout_requests"].find_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Payout request not found")
    return JSONResponse({"request": _serialize(row), "payout": _serialize(row)})


@router.get("/api/dco/{id}/submissions")
async def dco_submissions(
    id: str,
    request: Request,
    page: int = 1,
    limit: int = 20,
    status: str = "",
    entity: str = "",
    search: str = "",
):
    user = await get_current_user(request)
    _authorize(user, id)
    page = max(1, page)
    limit = min(100, max(1, limit))
    query: Dict[str, Any] = {"dco_id": id}
    if status:
        query["status"] = status
    if entity:
        if entity.lower() == "player":
            query["player_name"] = {"$exists": True}
        elif entity.lower() == "club":
            query["club_name"] = {"$exists": True}
    rows = await player_stats_collection.find(query).sort("submitted_at", -1).to_list(length=2000)
    serialized = [_serialize(row) for row in rows]
    q = search.strip().lower()
    if q:
        serialized = [row for row in serialized if q in str(row).lower()]
    total = len(serialized)
    start = (page - 1) * limit
    items = serialized[start:start + limit]
    return JSONResponse({
        "submissions": items,
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "totalPages": max(1, (total + limit - 1) // limit),
    })


@router.get("/api/dco/{id}/submissions/summary")
async def dco_submission_summary(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    rows = await player_stats_collection.find({"dco_id": id}).to_list(length=5000)
    total = len(rows)
    approved = sum(1 for r in rows if str(r.get("status") or "").lower() in {"approved", "verified", "completed", "paid"})
    rejected = sum(1 for r in rows if str(r.get("status") or "").lower() in {"rejected", "declined"})
    action = sum(1 for r in rows if str(r.get("status") or "").lower() in {"resubmit_required", "needs_action", "rejected", "revision_required"})
    pending = sum(1 for r in rows if str(r.get("status") or "").lower() in {"submitted", "pending", "under_review"})
    saved = sum(1 for r in rows if r.get("saved_directly") is True or str(r.get("status") or "").lower() == "saved")
    return JSONResponse({
        "total": total,
        "approved": approved,
        "rejected": rejected,
        "needs_action": action,
        "resubmit_required": action,
        "pending": pending,
        "saved_directly": saved,
        "approval_rate": round((approved / total) * 100, 1) if total else 0,
    })


@router.get("/api/dco/{id}/submissions/{submission_id}")
async def dco_submission_detail(id: str, submission_id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    clauses: List[Dict[str, Any]] = [{"submission_id": submission_id}, {"id": submission_id}]
    if ObjectId.is_valid(submission_id):
        clauses.append({"_id": ObjectId(submission_id)})
    row = await player_stats_collection.find_one({"$and": [{"dco_id": id}, {"$or": clauses}]})
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    return JSONResponse({"submission": _serialize(row)})


@router.get("/api/dco/{id}/earnings")
async def dco_earnings(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)

    rows = await player_stats_collection.find(
        {
            "dco_id": id,
            "status": {
                "$in": [
                    "submitted",
                    "approved",
                    "verified",
                    "completed",
                ]
            },
        }
    ).sort(
        "submitted_at", -1
    ).limit(500).to_list(length=500)

    doc = await _get_dco(id)

    tier = str(doc.get("tier", "1"))
    rates = DEFAULT_DCO_RATES.get(
        f"tier{tier}",
        DEFAULT_DCO_RATES.get(tier, {})
    )

    activities = []
    pending = 0.0

    for row in rows:
        item = _serialize(row)

        match = item.get("match") or {}

        category = str(
            item.get("match_category")
            or item.get("player_level")
            or "other"
        ).lower().replace(" ", "_")

        amount = float(
            rates.get(
                category,
                rates.get("other", 500)
            )
        )

        if item.get("status") != "paid":
            pending += amount

        activities.append(
            {
                "match": (
                    f"{match.get('homeTeam', '')} "
                    f"vs {match.get('awayTeam', '')}"
                ),
                "entity": (
                    item.get("player_name")
                    or item.get("club_name")
                    or "—"
                ),
                "category": category,
                "amount": amount,
                "status": item.get("status", "submitted"),
                "date": (
                    item.get("submitted_at")
                    or item.get("created_at")
                    or ""
                ),
            }
        )

    return JSONResponse(
        {
            "pending_amount": pending,
            "activities": activities,
        }
    )

@router.get("/api/dco/{id}/payout-requests")
async def dco_payout_requests(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    rows = await _database["dco_payout_requests"].find({"dco_id": id}).sort("created_at", -1).limit(100).to_list(length=100)
    return JSONResponse({"requests": _serialize(rows)})


@router.post("/api/dco/{id}/payout-requests")
async def create_dco_payout_request(id: str, request: Request, payload: PayoutRequest):
    user = await get_current_user(request)
    _authorize(user, id)
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="A positive amount is required")

    # Idempotency protects against double-clicks/retries from the finance UI.
    idem = (payload.idempotency_key or request.headers.get("Idempotency-Key") or "").strip()
    payout_col = _database["dco_payout_requests"]
    if idem:
        existing = await payout_col.find_one({"dco_id": id, "idempotency_key": idem})
        if existing:
            return JSONResponse({
                "success": True,
                "request_id": str(existing.get("_id")),
                "reference": existing.get("reference"),
                "status": existing.get("status", "pending"),
                "idempotent_replay": True,
            })

    # Recalculate the amount server-side from authoritative submission records.
    snap = await _earnings_snapshot(id)
    available = float(snap.get("available_amount") or 0)
    if payload.amount > available:
        raise HTTPException(
            status_code=400,
            detail=f"Payout amount exceeds the currently available balance ({available:.2f})",
        )

    dco = await _get_dco(id)
    bank_name = payload.bank_name or dco.get("bank_name", "")
    account_number = payload.account_number or dco.get("account_number", "")
    account_name = payload.account_name or dco.get("account_name", "")
    if not account_number:
        raise HTTPException(status_code=400, detail="Withdrawal account is not configured")

    now = _now()
    reference = f"DCO-PAY-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "dco_id": id,
        "dco_name": dco.get("full_name") or dco.get("name", ""),
        "amount": float(payload.amount),
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
        "reference": reference,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    if idem:
        record["idempotency_key"] = idem

    result = await payout_col.insert_one(record)
    return JSONResponse({
        "success": True,
        "request_id": str(result.inserted_id),
        "reference": reference,
        "status": "pending",
    })


@router.get("/api/dco/{id}/withdrawal-account")
async def dco_withdrawal_account(id: str, request: Request):
    user = await get_current_user(request)
    _authorize(user, id)
    dco = await _get_dco(id)
    return JSONResponse(
        {
            "bank_name": dco.get("bank_name", ""),
            "account_number": dco.get("account_number", ""),
            "account_name": dco.get("account_name", ""),
            "bank_code": dco.get("bank_code", ""),
        }
    )


@router.get("/api/dco/support/tickets")
async def support_tickets(request: Request, userId: Optional[str] = None):
    user = await get_current_user(request)
    identifier = userId or _dco_id(user)
    rows = await support_tickets_collection.find(
        {"$or": [{"user_id": identifier}, {"dco_id": identifier}, {"unique_id": identifier}]}
    ).sort("created_at", -1).limit(100).to_list(length=100)
    return JSONResponse({"tickets": _serialize(rows)})


@router.post("/api/dco/support/tickets")
async def create_support_ticket(request: Request, payload: SupportTicketRequest):
    user = await get_current_user(request)
    identifier = _dco_id(user)
    now = _now()
    record = {
        "ticket_id": f"TICK-{uuid.uuid4().hex[:8].upper()}",
        "user_id": payload.user_id or identifier,
        "user_name": payload.user_name or user.get("full_name") or user.get("name", ""),
        "role": payload.role or "dco",
        "reason": payload.reason or "",
        "message": payload.message or "",
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    result = await support_tickets_collection.insert_one(record)
    return JSONResponse({"success": True, "ticket_id": record["ticket_id"], "_id": str(result.inserted_id), "status": "open"})


@router.get("/api/dco/support/chat/{tid}")
async def support_chat(tid: str, request: Request):
    await get_current_user(request)
    query: Dict[str, Any] = {"ticket_id": tid}
    if ObjectId.is_valid(tid):
        query = {"$or": [{"ticket_id": tid}, {"_id": ObjectId(tid)}]}
    rows = await support_messages_collection.find(query).sort("created_at", 1).limit(500).to_list(length=500)
    return JSONResponse({"messages": _serialize(rows)})


@router.post("/api/dco/support/chat/{tid}")
async def create_support_message(tid: str, request: Request, payload: SupportMessageRequest):
    user = await get_current_user(request)
    message = (payload.message or payload.text or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    record = {
        "ticket_id": tid,
        "sender": payload.sender or "user",
        "sender_id": _dco_id(user),
        "message": message,
        "created_at": _now(),
    }
    result = await support_messages_collection.insert_one(record)
    return JSONResponse({"success": True, "_id": str(result.inserted_id), **_serialize(record)})
