"""
ENEJISTATS -- Agent Dashboard Routes
=====================================
Standalone FastAPI router module covering every API endpoint consumed by
the Agent Dashboard HTML interface.

ROUTES COVERED
--------------
  GET    /api/agent/available-players                 -- free/expiring players for scouting
  GET    /api/agent/search-players                    -- owned by agent_discovery_routes.py (single registration)
  GET    /api/subscription/pricing                    -- subscription plans (role-aware: agent/player)
  GET    /api/token/pricing                           -- token packages (role-aware: agent/player)
  POST   /api/payment/bank-transfer/intent            -- create bank-transfer payment intent (agent or player)
  GET    /api/bank-details/active                     -- platform active bank details
  POST   /api/payment/bank-transfer/receipt           -- upload payment receipt (agent or player)
  GET    /api/agent/{agent_id}/players                -- agent roster + summary stats
  POST   /api/agent/{agent_id}/players                -- add player to roster
  GET    /api/agent/{agent_id}/notifications          -- notification list + unread count
  PATCH  /api/agent/{agent_id}/notifications/read-all -- mark all notifications read
  GET    /api/agent/{agent_id}/profile                -- full agent profile object
  GET    /api/agent/{agent_id}/reports                -- agent report list
  POST   /api/agent/{agent_id}/reports                -- generate a new report
  GET    /api/agent/{agent_id}/contracts              -- player contract history
  POST   /api/agent/{agent_id}/proposals              -- send proposal to a player
  GET    /api/agent/{agent_id}/proposals              -- list of sent proposals
  DELETE /api/agent/{agent_id}/proposals/{request_id} -- cancel a pending proposal
  GET    /api/agent/{agent_id}/subscription           -- current subscription status
  GET    /api/agent/{agent_id}/subscription/history   -- payment / subscription history
  PATCH  /api/agent/{agent_id}/settings               -- update editable profile fields
  GET    /api/agent/{agent_id}/tokens                 -- agent token balance
  POST   /api/agent/{agent_id}/tokens/credit          -- credit tokens from agent to contracted player

HOW TO INTEGRATE IN main.py
----------------------------
    import agent_dashboard_routes as _agent_dash
    _agent_dash._setup_dependencies(globals())
    app.include_router(_agent_dash.router)

WHY THIS PATTERN -- CIRCULAR IMPORT EXPLAINED
---------------------------------------------
No import from main at module-level -- avoids circular imports.
All shared state (collections, helpers, pricing constants) is injected
by _setup_dependencies() which is called by main.py AFTER main.py has
fully executed and all symbols are bound in its namespace.

ROUTE ORDER MATTERS
--------------------
Static path segments (e.g. /api/agent/available-players) are always
declared BEFORE parameterised routes (/api/agent/{agent_id}/...) so
FastAPI does not mistakenly capture the literal string "available-players"
as an agent_id value.

AGENT-ID SEMANTICS
-------------------
The {agent_id} path parameter is the human-readable business ID stored
in agents_collection["agent_id"] (e.g. "AG-202506-A3F9C1").  It is NOT
the MongoDB ObjectId.  The JWT "sub" field holds the ObjectId string,
which _resolve_agent() uses to fetch the document; the business agent_id
is then compared to guard cross-agent access.
"""

# ============================================================
# STANDARD-LIBRARY & THIRD-PARTY IMPORTS ONLY
# (No import from main -- circular import avoided)
# ============================================================

import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ============================================================
# END: IMPORTS
# ============================================================

# ============================================================
# START: MODULE CONFIGURATION / CANONICAL DEPENDENCY CONTRACT
# ============================================================
# MODULE-LEVEL PLACEHOLDERS  (all filled by _setup_dependencies)
# ============================================================

# -- Database handle ------------------------------------------
database = None

# -- Collections -----------------------------------------------
agents_collection            = None
players_collection           = None
notifications_collection     = None
reports_collection           = None
proposals_collection         = None
agent_contracts_collection   = None  # written-to when a proposal is sent; read by player contracts endpoint
subscriptions_collection     = None
transactions_collection      = None
payment_intents_collection   = None
platform_settings_collection = None

# -- Token collections (agent token ledger + player token ledger) -------
# Used by GET /api/agent/{id}/tokens and POST /api/agent/{id}/tokens/credit
agent_tokens_collection       = None
player_tokens_collection      = None   # player-side token balances (same coll as player_dashboard)
token_transactions_collection = None   # unified token transaction log

# -- Canonical authentication / authorization services ----------
get_current_user = None
get_agent_user = None
generate_user_id = None
normalize_role = None
role_collection = None
ROLE_COLLECTION_MAP = None
CANONICAL_ROLES = None
TOKEN_ELIGIBLE_ROLES = None
SUBSCRIPTION_ELIGIBLE_ROLES = None

# -- Business-logic helpers ------------------------------------
MongoSerializer      = None
logger               = None
upload_to_cloudinary = None

# -- Pricing data ----------------------------------------------
DEFAULT_SUBSCRIPTION_PLANS = None   # Dict[role, List[plan_dict]]
TOKEN_PACKAGES             = None   # Dict[role, Dict[level, List[pkg_dict]]]
BANK_TRANSFER_DETAILS      = None   # Dict with bank_name / account_name / account_number
PLAN_MONTHS                = None   # Dict[plan_key, int]

_DEPS_READY = False


# ============================================================
# START: CANONICAL DEPENDENCY INJECTION
# ============================================================
# DEPENDENCY INJECTION -- called once by main.py
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    """
    Inject canonical services and module-specific collections from main.py.

    main.py remains the single source of truth for authentication, role
    metadata, public IDs, permissions, serialization, timestamps, and
    database initialization.  This module only owns agent-dashboard domain
    behavior.
    """
    global _DEPS_READY
    global database
    global agents_collection, players_collection
    global notifications_collection, reports_collection, proposals_collection, agent_contracts_collection
    global subscriptions_collection, transactions_collection
    global payment_intents_collection, platform_settings_collection
    global agent_tokens_collection, player_tokens_collection, token_transactions_collection
    global get_current_user, get_agent_user, normalize_role, role_collection, generate_user_id
    global ROLE_COLLECTION_MAP, CANONICAL_ROLES, TOKEN_ELIGIBLE_ROLES
    global SUBSCRIPTION_ELIGIBLE_ROLES
    global MongoSerializer, logger, upload_to_cloudinary
    global DEFAULT_SUBSCRIPTION_PLANS, TOKEN_PACKAGES
    global BANK_TRANSFER_DETAILS, PLAN_MONTHS

    if _DEPS_READY:
        return

    _m = main_globals

    def _require(key: str):
        if key not in _m:
            raise RuntimeError(
                f"[agent_dashboard] _setup_dependencies: required symbol "
                f"'{key}' is missing from main.py globals."
            )
        return _m[key]

    # Canonical platform dependencies.
    database = _require("database")
    agents_collection = _require("agents_collection")
    players_collection = _require("players_collection")
    notifications_collection = _require("notifications_collection")
    transactions_collection = _require("transactions_collection")
    payment_intents_collection = _require("payment_intents_collection")

    get_current_user = _require("get_current_user")
    get_agent_user = _require("get_agent_user")
    generate_user_id = _require("generate_user_id")
    normalize_role = _require("normalize_role")
    role_collection = _require("role_collection")
    ROLE_COLLECTION_MAP = _require("ROLE_COLLECTION_MAP")
    CANONICAL_ROLES = _require("CANONICAL_ROLES")
    TOKEN_ELIGIBLE_ROLES = _require("TOKEN_ELIGIBLE_ROLES")
    SUBSCRIPTION_ELIGIBLE_ROLES = _require("SUBSCRIPTION_ELIGIBLE_ROLES")

    MongoSerializer = _require("MongoSerializer")
    logger = _require("logger")
    upload_to_cloudinary = _require("upload_to_cloudinary")

    # Module/domain collections: consume canonical main.py objects when
    # available; otherwise resolve only the module-specific collection names.
    subscriptions_collection = _m.get("subscriptions_collection")
    if subscriptions_collection is None:
        subscriptions_collection = database["subscriptions"]

    reports_collection = _m.get("reports_collection")
    if reports_collection is None:
        reports_collection = database["agent_reports"]

    proposals_collection = _m.get("proposals_collection")
    if proposals_collection is None:
        proposals_collection = database["agent_proposals"]

    agent_contracts_collection = _m.get("agent_contracts_collection")
    if agent_contracts_collection is None:
        agent_contracts_collection = database["agent_contracts"]

    platform_settings_collection = _m.get("platform_settings_collection")
    if platform_settings_collection is None:
        platform_settings_collection = database["platform_settings"]

    agent_tokens_collection = _m.get("agent_tokens_collection")
    if agent_tokens_collection is None:
        agent_tokens_collection = database["agent_tokens"]

    player_tokens_collection = _m.get("player_tokens_collection")
    if player_tokens_collection is None:
        player_tokens_collection = database["player_tokens"]

    token_transactions_collection = _m.get("token_transactions_collection")
    if token_transactions_collection is None:
        token_transactions_collection = database["token_transactions"]

    DEFAULT_SUBSCRIPTION_PLANS = _m.get("DEFAULT_SUBSCRIPTION_PLANS") or {}
    TOKEN_PACKAGES = _m.get("TOKEN_PACKAGES") or {}
    BANK_TRANSFER_DETAILS = _m.get("BANK_TRANSFER_DETAILS") or {}
    PLAN_MONTHS = _m.get("PLAN_MONTHS") or {}

    _DEPS_READY = True
    logger.debug("[agent_dashboard] canonical dependency injection complete")


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# END: CANONICAL DEPENDENCY INJECTION
# ============================================================

# ============================================================
# START: PYDANTIC MODELS
# ============================================================

class AddPlayerRequest(BaseModel):
    name:              str
    position:          str
    club:              Optional[str] = None
    nationality:       Optional[str] = None
    dob:               Optional[str] = None
    marketValue:       Optional[int] = None
    contractStartDate: Optional[str] = None
    contractEndDate:   Optional[str] = None


class GenerateReportRequest(BaseModel):
    type:     str
    playerId: Optional[str] = None
    notes:    Optional[str] = None


class ProposalRequest(BaseModel):
    playerId:          str
    proposedStartDate: str
    proposedEndDate:   str
    message:           Optional[str] = None


class SettingsRequest(BaseModel):
    phone:     Optional[str] = None
    whatsapp:  Optional[str] = None
    website:   Optional[str] = None
    instagram: Optional[str] = None
    linkedin:  Optional[str] = None
    bio:       Optional[str] = None


class PaymentIntentRequest(BaseModel):
    paymentType:  str            # "SUBSCRIPTION" | "TOKEN_PURCHASE"
    selectedPlan: str            # e.g. "monthly", "quarterly", "annual", "tokens_5"
    role:         str            # "agent", "player", etc.  (used for display only; pricing always uses authenticated role)
    level:        Optional[str] = None  # for levelled roles (player/club)
    tokens:       Optional[int] = None  # for TOKEN_PURCHASE


class CreditTokensRequest(BaseModel):
    """Request body for POST /api/agent/{agent_id}/tokens/credit."""
    playerId:    str
    amount:      int             # number of tokens to credit
    description: Optional[str] = None


# ============================================================
# END: PYDANTIC MODELS
# ============================================================

# ============================================================
# START: MODULE-SPECIFIC HELPERS / AUTHORIZATION INTEGRATION
# ============================================================

async def _resolve_agent(request: Request) -> Dict[str, Any]:
    """Resolve the authenticated agent through main.py's canonical guard."""
    agent = await get_agent_user(request)
    return MongoSerializer.serialize_document(agent)


def _guard_agent_id(authenticated_agent: Dict[str, Any], agent_id: str) -> None:
    """Prevent cross-agent access using the canonical public agent_id."""
    own_id = (
        authenticated_agent.get("agent_id")
        or authenticated_agent.get("user_id")
        or authenticated_agent.get("unique_id")
    )
    if own_id != agent_id:
        raise HTTPException(status_code=403, detail="Access denied")


def _compute_contract_status(contract: Optional[Dict[str, Any]]) -> str:
    """Derive contract status from a contract object's end date."""
    if not contract:
        return "none"

    end_raw = contract.get("end_date") or contract.get("endDate")
    if not end_raw:
        return "none"

    try:
        if isinstance(end_raw, datetime):
            end = MongoSerializer.ensure_timezone_aware(end_raw)
        else:
            end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
            end = MongoSerializer.ensure_timezone_aware(end)

        now = MongoSerializer.now_utc()
        if end < now:
            return "expired"
        if (end - now).days <= 60:
            return "expiring_soon"
        return "active"
    except (TypeError, ValueError, OverflowError):
        return "none"


def _resolve_player_name(p: Dict[str, Any]) -> str:
    """Build a display name while reading canonical fields before legacy aliases."""
    first = (p.get("first_name") or p.get("firstName") or "").strip()
    middle = (p.get("middle_name") or p.get("middleName") or "").strip()
    last = (p.get("last_name") or p.get("lastName") or "").strip()

    if first or last:
        return " ".join(x for x in (first, middle, last) if x)

    return (
        p.get("name")
        or p.get("full_name")
        or p.get("fullName")
        or ""
    )


def _serialize_player(p: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize a player into the stable Agent Dashboard response shape."""
    contract = p.get("contract") or {}
    contract_status = _compute_contract_status(contract)

    player_id = (
        p.get("player_id")
        or p.get("user_id")
        or str(p.get("_id", ""))
    )

    position = (
        p.get("position")
        or p.get("preferred_position")
        or p.get("preferredPosition")
        or ""
    )
    club = (
        p.get("current_club")
        or p.get("club")
        or p.get("currentClub")
        or None
    )
    dob = (
        p.get("date_of_birth")
        or p.get("dob")
        or p.get("dateOfBirth")
        or None
    )
    photo_url = p.get("photo_url") or p.get("photoUrl") or None
    category = (
        p.get("playing_category")
        or p.get("playingCategory")
        or p.get("category")
        or p.get("level")
        or None
    )

    return {
        "id": player_id,
        "name": _resolve_player_name(p),
        "position": position,
        "club": club,
        "nationality": p.get("nationality") or None,
        "dob": dob,
        "marketValue": p.get("market_value") if p.get("market_value") is not None else p.get("marketValue"),
        "photoUrl": photo_url,
        "category": category,
        "contractStatus": contract_status,
        "contract": {
            "startDate": contract.get("start_date") or contract.get("startDate"),
            "endDate": contract.get("end_date") or contract.get("endDate"),
        } if contract else None,
    }


def _make_payment_ref(prefix: str = "ENST") -> str:
    """Generate a module-specific payment reference; not a user ID."""
    now = MongoSerializer.now_utc()
    rand = secrets.token_hex(4).upper()
    return f"{prefix}-{now.strftime('%Y%m%d')}-{rand}"


def _plan_amount_for_role(role: str, plan_key: str) -> int:
    """Look up pricing from canonical main.py configuration."""
    canonical_role = normalize_role(role)
    plans_for_role = (DEFAULT_SUBSCRIPTION_PLANS or {}).get(canonical_role, [])
    for plan in plans_for_role:
        if plan.get("key") == plan_key:
            return int(plan.get("amount") or 0)
    return 0


def _token_amount_for_role(role: str, tokens: int) -> int:
    """Look up token pricing from canonical main.py configuration."""
    canonical_role = normalize_role(role)
    role_pkgs = (TOKEN_PACKAGES or {}).get(canonical_role, {})
    packages = role_pkgs.get("default") or []
    for package in packages:
        if int(package.get("tokens") or 0) == int(tokens):
            return int(package.get("price") or 0)
    return 0


async def _resolve_any_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Resolve the current identity exclusively through main.py's canonical
    get_current_user() resolver.
    """
    user_doc = await get_current_user(request)
    role = normalize_role(user_doc.get("role") or user_doc.get("user_type"))
    _, id_field = ROLE_COLLECTION_MAP[role]
    typed_id = (
        user_doc.get(id_field)
        or user_doc.get("user_id")
        or user_doc.get("unique_id")
    )
    if not typed_id:
        raise HTTPException(status_code=401, detail="Authenticated user has no canonical public ID")

    return {
        "user_id": str(user_doc.get("user_id") or typed_id),
        "user_role": role,
        "user_doc": user_doc,
        "typed_id": str(typed_id),
        "id_field": id_field,
    }


def _require_subscription_eligible(role: str) -> str:
    canonical_role = normalize_role(role)
    if canonical_role not in SUBSCRIPTION_ELIGIBLE_ROLES:
        raise HTTPException(status_code=403, detail="This role is not eligible for subscriptions")
    return canonical_role


def _require_token_eligible(role: str) -> str:
    canonical_role = normalize_role(role)
    if canonical_role not in TOKEN_ELIGIBLE_ROLES:
        raise HTTPException(status_code=403, detail="This role is not eligible for tokens")
    return canonical_role


# ============================================================
# END: MODULE-SPECIFIC HELPERS / AUTHORIZATION INTEGRATION
# ============================================================

# ============================================================
# START: API ROUTES
# ============================================================
# IMPORTANT: static paths must be declared before parameterised
# ones so FastAPI routes them correctly.
# ============================================================


# -------------------------------------------------------------
# GET /api/agent/available-players
# Free / expiring players available for the agent to scout.
# MUST be declared before /api/agent/{agent_id}/... routes.
# -------------------------------------------------------------

@router.get("/api/agent/available-players")
async def get_available_players(request: Request):
    """
    Return players who are free agents or have expiring/expired contracts
    and are not already rostered by the calling agent.
    """
    agent     = await _resolve_agent(request)
    agent_id  = (
        agent.get("agent_id")
        or agent.get("id")
        or str(agent.get("_id", ""))
    )

    # Fetch all players NOT currently on this agent's books
    cursor = players_collection.find(
        {"$or": [{"agent_id": {"$exists": False}}, {"agent_id": {"$ne": agent_id}}]}
    )
    all_players = await cursor.to_list(length=500)

    # BF1: Batch-fetch all pending proposals from this agent in ONE query — eliminates N+1.
    # Build the set of player IDs from the fetched list so we scope the proposal query tightly.
    available_pids: List[str] = [
        p.get("player_id") or p.get("user_id") or str(p.get("_id", ""))
        for p in all_players
    ]
    pending_map: Dict[str, str] = {}
    if available_pids and proposals_collection is not None:
        pending_cursor = proposals_collection.find(
            {
                "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
                "status": "pending",
                "player_id": {"$in": available_pids},
            },
            {"player_id": 1, "request_id": 1, "_id": 1},
        )
        pending_docs = await pending_cursor.to_list(length=1000)
        for prop in pending_docs:
            pid = prop.get("player_id", "")
            rid = prop.get("request_id") or str(prop.get("_id", ""))
            if pid:
                pending_map[pid] = rid

    available: List[Dict[str, Any]] = []
    for p in all_players:
        contract = p.get("contract") or {}
        status   = _compute_contract_status(contract)
        if status in ("none", "expired", "expiring_soon"):
            serialized = _serialize_player(p)
            pid_key = serialized["id"]
            # BF1: attach pendingProposalId so the frontend can show the right UI state
            serialized["pendingProposalId"] = pending_map.get(pid_key) or None
            available.append(serialized)

    return JSONResponse({"players": available})


# -------------------------------------------------------------
# GET /api/subscription/pricing
# Role-aware: returns plans for the authenticated user's role.
# Agents see agent plans; players see player plans.
# -------------------------------------------------------------

@router.get("/api/subscription/pricing")
async def get_subscription_pricing(request: Request):
    """Return canonical subscription plans for the authenticated eligible role."""
    user_info = await _resolve_any_authenticated_user(request)
    role = _require_subscription_eligible(user_info["user_role"])
    plans = (DEFAULT_SUBSCRIPTION_PLANS or {}).get(role, [])
    return JSONResponse({"plans": plans})


# -------------------------------------------------------------
# GET /api/token/pricing
# Role-aware: returns token packages for the authenticated user's role.
# Both agent and player dashboards call this endpoint.
# The player_dashboard_routes.py version is intentionally removed to avoid
# duplicate route conflicts; this single endpoint handles both roles.
# -------------------------------------------------------------

@router.get("/api/token/pricing")
async def get_token_pricing(request: Request):
    """Return canonical token packages for the authenticated eligible role."""
    user_info = await _resolve_any_authenticated_user(request)
    role = _require_token_eligible(user_info["user_role"])

    role_pkgs = (TOKEN_PACKAGES or {}).get(role, {})
    raw_pkgs: List[Dict[str, Any]] = role_pkgs.get("default") or []

    packages = []
    for pkg in raw_pkgs:
        tok = int(pkg.get("tokens") or 0)
        packages.append({
            "key": f"tokens_{tok}",
            "label": pkg.get("label") or f"{tok} Token{'s' if tok != 1 else ''}",
            "tokens": tok,
            "price": pkg.get("price", 0),
            "amount": pkg.get("price", 0),
            "bonus": pkg.get("bonus"),
        })

    return JSONResponse({"packages": packages})


# -------------------------------------------------------------
# GET /api/bank-details/active
# -------------------------------------------------------------

@router.get("/api/bank-details/active")
async def get_active_bank_details(request: Request):
    """
    Return the platform's active bank transfer details.
    Tries the DB (admin-configurable) first; falls back to the
    environment-sourced BANK_TRANSFER_DETAILS constant.

    Response shape:
        { "bankName", "accountName", "accountNumber" }
    """
    try:
        db_settings = await platform_settings_collection.find_one(
            {"type": "bank_details", "active": True}
        )
        if db_settings is not None:
            return JSONResponse({
                "bankName":      db_settings.get("bank_name") or db_settings.get("bankName", ""),
                "accountName":   db_settings.get("account_name") or db_settings.get("accountName", ""),
                "accountNumber": db_settings.get("account_number") or db_settings.get("accountNumber", ""),
            })
    except Exception as exc:
        logger.warning("[agent_dashboard] bank_details DB lookup failed: %s", exc)

    bd = BANK_TRANSFER_DETAILS or {}
    return JSONResponse({
        "bankName":      bd.get("bank_name", ""),
        "accountName":   bd.get("account_name", ""),
        "accountNumber": bd.get("account_number", ""),
    })


# -------------------------------------------------------------
# POST /api/payment/bank-transfer/intent
# -------------------------------------------------------------

@router.post("/api/payment/bank-transfer/intent")
async def create_bank_transfer_intent(
    request: Request,
    body: PaymentIntentRequest,
):
    """
    Create a pending bank-transfer payment intent for an authenticated
    subscription/token-eligible user. The authenticated canonical role controls
    pricing and identity; body.role is never used for authorization.
    """
    user_info = await _resolve_any_authenticated_user(request)
    role = user_info["user_role"]
    typed_id = user_info["typed_id"]
    user_doc = user_info["user_doc"]

    payment_type = (body.paymentType or "").strip().upper()
    plan_key = (body.selectedPlan or "").strip()

    if payment_type == "SUBSCRIPTION":
        role = _require_subscription_eligible(role)
        amount = _plan_amount_for_role(role, plan_key)
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown or invalid subscription plan '{plan_key}' for role '{role}'.",
            )
    elif payment_type == "TOKEN_PURCHASE":
        role = _require_token_eligible(role)
        tokens = body.tokens or 0
        if tokens <= 0:
            raise HTTPException(
                status_code=400,
                detail="tokens must be a positive integer for TOKEN_PURCHASE.",
            )
        amount = _token_amount_for_role(role, tokens)
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown token package for {tokens} token(s). Check /api/token/pricing for valid options.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown paymentType '{body.paymentType}'. Expected 'SUBSCRIPTION' or 'TOKEN_PURCHASE'.",
        )

    reference = _make_payment_ref("ENST")
    intent_id = secrets.token_hex(12)
    now = MongoSerializer.now_utc()

    _, id_field = ROLE_COLLECTION_MAP[role]
    intent_doc: Dict[str, Any] = {
        "intent_id": intent_id,
        "reference": reference,
        "payment_type": payment_type,
        "selected_plan": plan_key,
        "role": role,
        "user_type": role,
        "level": body.level,
        "tokens": body.tokens,
        "amount": amount,
        "user_id": typed_id,
        "unique_id": typed_id,
        "public_id_field": id_field,
        "status": "pending",
        "created_at": now,
    }

    await payment_intents_collection.insert_one(intent_doc)
    logger.info(
        "[agent_dashboard] payment intent created: %s role=%s ref=%s amount=%s",
        intent_id, role, reference, amount,
    )

    return JSONResponse({
        "intentId": intent_id,
        "reference": reference,
        "amount": amount,
    })


# -------------------------------------------------------------
# POST /api/payment/bank-transfer/receipt
# Multipart upload of the payment proof receipt.
# -------------------------------------------------------------

@router.post("/api/payment/bank-transfer/receipt")
async def upload_bank_transfer_receipt(
    request: Request,
    intentId: str = Form(...),
    receiptFile: UploadFile = File(...),
):
    """
    Upload a bank-transfer receipt for the authenticated user's own pending
    payment intent and create a canonical pending transaction record.
    """
    user_info = await _resolve_any_authenticated_user(request)
    role = user_info["user_role"]
    typed_id = user_info["typed_id"]

    # Canonical lookup first; legacy field aliases are read-only compatibility.
    intent = await payment_intents_collection.find_one({
        "intent_id": intentId,
        "user_id": typed_id,
    })
    if intent is None:
        intent = await payment_intents_collection.find_one({
            "$and": [
                {"$or": [
                    {"intentId": intentId},
                    {"intent_id": intentId},
                ]},
                {"$or": [
                    {"userId": typed_id},
                    {"user_id": typed_id},
                    {"agentId": typed_id},
                    {"playerId": typed_id},
                    {"player_id": typed_id},
                ]},
            ],
        })
    if intent is None:
        raise HTTPException(status_code=404, detail="Payment intent not found")

    stored_role = normalize_role(intent.get("role") or intent.get("user_type") or role)
    if stored_role != role:
        raise HTTPException(status_code=403, detail="Payment intent does not belong to this role")

    intent_owner = (
        intent.get("user_id")
        or intent.get("userId")
        or intent.get("agentId")
        or intent.get("playerId")
        or intent.get("player_id")
    )
    if str(intent_owner) != str(typed_id):
        raise HTTPException(status_code=403, detail="Access denied")

    status = intent.get("status")
    if status != "pending":
        raise HTTPException(
            status_code=400,
            detail="This intent has already been submitted or is not in a valid state",
        )

    filename = receiptFile.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "png", "jpg", "jpeg"):
        raise HTTPException(status_code=400, detail="Only PDF, PNG, JPG, JPEG files are accepted")

    file_bytes = await receiptFile.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10 MB")

    receipt_url: Optional[str] = None
    cloudinary_folder = f"{role}_receipts"
    try:
        upload_result = await upload_to_cloudinary(
            file_bytes,
            folder=cloudinary_folder,
            resource_type="auto",
        )
        receipt_url = upload_result.get("secure_url") or upload_result.get("url")
    except Exception as exc:
        logger.error("[agent_dashboard] Cloudinary receipt upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Receipt upload failed -- please try again")

    now = MongoSerializer.now_utc()
    ref = intent.get("reference") or _make_payment_ref()

    intent_filter = {"_id": intent["_id"]} if intent.get("_id") is not None else {
        "intent_id": intentId
    }
    await payment_intents_collection.update_one(
        intent_filter,
        {"$set": {
            "status": "receipt_uploaded",
            "receipt_url": receipt_url,
            "uploaded_at": now,
        }},
    )

    payment_type = intent.get("payment_type") or intent.get("paymentType")
    selected_plan = intent.get("selected_plan") or intent.get("selectedPlan")
    tx_doc: Dict[str, Any] = {
        "user_id": typed_id,
        "unique_id": typed_id,
        "user_type": role,
        "type": "subscription" if payment_type == "SUBSCRIPTION" else "token_purchase",
        "plan": selected_plan,
        "tokens": intent.get("tokens"),
        "amount": intent.get("amount", 0),
        "reference": ref,
        "intent_id": intentId,
        "receipt_url": receipt_url,
        "status": "pending",
        "created_at": now,
    }
    await transactions_collection.insert_one(tx_doc)

    try:
        await notifications_collection.insert_one({
            "user_id": typed_id,
            "unique_id": typed_id,
            "user_type": role,
            "type": "payment_submitted",
            "message": (
                f"Your payment receipt (ref: {ref}) has been received "
                "and is under review. You will be notified once confirmed."
            ),
            "read": False,
            "created_at": now,
        })
    except Exception as notif_exc:
        logger.warning("[agent_dashboard] notification insert failed: %s", notif_exc)

    logger.info(
        "[agent_dashboard] receipt uploaded intent=%s role=%s user=%s",
        intentId, role, typed_id,
    )
    return JSONResponse({"success": True, "reference": ref})


# -------------------------------------------------------------
# GET  /api/agent/{agent_id}/players -- roster list + summary
# POST /api/agent/{agent_id}/players -- add player
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/players")
async def get_agent_players(agent_id: str, request: Request):
    """
    Return the agent's full player roster with a summary block.

    Response:
        {
          "players": [ { id, name, position, club, nationality, dob,
                         marketValue, photoUrl, category,
                         contractStatus,
                         contract: { startDate, endDate } }, ... ],
          "summary": { total, active, expiringSoon, freeAgents }
        }
    """
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    cursor      = players_collection.find({"agent_id": agent_id})
    raw_players = await cursor.to_list(length=500)
    players     = [_serialize_player(p) for p in raw_players]

    total       = len(players)
    active      = sum(1 for p in players if p["contractStatus"] == "active")
    expiring    = sum(1 for p in players if p["contractStatus"] == "expiring_soon")
    free_agents = sum(1 for p in players if p["contractStatus"] in ("none", "expired"))

    return JSONResponse({
        "players": players,
        "summary": {
            "total":        total,
            "active":       active,
            "expiringSoon": expiring,
            "freeAgents":   free_agents,
        },
    })


@router.post("/api/agent/{agent_id}/players")
async def add_agent_player(
    agent_id: str,
    request: Request,
    body: AddPlayerRequest,
):
    """Add a domain player profile to the authenticated agent's roster."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Player name is required")

    contract: Optional[Dict[str, Any]] = None
    if body.contractStartDate or body.contractEndDate:
        contract = {
            "start_date": body.contractStartDate,
            "end_date": body.contractEndDate,
        }

    # This is a player profile without credentials; therefore use the
    # canonical platform ID generator directly rather than creating a fake
    # account through create_platform_user().
    player_id = await generate_user_id("player", "")
    now = MongoSerializer.now_utc()
    player_doc: Dict[str, Any] = {
        "player_id": player_id,
        "agent_id": agent_id,
        "name": body.name.strip(),
        "position": body.position or "",
        "club": body.club,
        "nationality": body.nationality,
        "dob": body.dob,
        "market_value": body.marketValue,
        "contract": contract,
        "photo_url": None,
        "added_by": "agent",
        "created_at": now,
        "updated_at": now,
    }

    result = await players_collection.insert_one(player_doc)
    player_doc["_id"] = result.inserted_id
    serialized = _serialize_player(player_doc)

    logger.info(
        "[agent_dashboard] player '%s' (%s) added by agent %s",
        body.name, player_id, agent_id,
    )
    return JSONResponse({"success": True, "player": serialized}, status_code=201)


# -------------------------------------------------------------
# GET   /api/agent/{agent_id}/notifications
# PATCH /api/agent/{agent_id}/notifications/read-all
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/notifications")
async def get_agent_notifications(agent_id: str, request: Request):
    """Return the authenticated agent's notifications and unread count."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    cursor = (
        notifications_collection
        .find({"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]})
        .sort([("created_at", -1), ("createdAt", -1)])
        .limit(100)
    )
    raw = await cursor.to_list(length=100)

    notifications: List[Dict[str, Any]] = []
    unread_count = 0
    for n in raw:
        is_read = bool(n.get("read") if n.get("read") is not None else n.get("isRead") or False)
        if not is_read:
            unread_count += 1
        notifications.append({
            "id": str(n.get("_id", "")),
            "type": n.get("type", "info"),
            "message": n.get("message", ""),
            "isRead": is_read,
            "createdAt": MongoSerializer.serialize_value(
                n.get("created_at") or n.get("createdAt")
            ),
        })

    return JSONResponse({
        "notifications": notifications,
        "unreadCount": unread_count,
    })
@router.patch("/api/agent/{agent_id}/notifications/read-all")
async def mark_all_notifications_read(agent_id: str, request: Request):
    """Mark every unread notification for the authenticated agent as read."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    now = MongoSerializer.now_utc()
    await notifications_collection.update_many(
        {
            "$and": [
                {"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]},
                {"$or": [
                    {"read": False},
                    {"isRead": False},
                    {"read": {"$exists": False}, "isRead": {"$exists": False}},
                ]},
            ],
        },
        {"$set": {"read": True, "read_at": now}},
    )
    return JSONResponse({"success": True})


@router.get("/api/agent/{agent_id}/profile")
async def get_agent_profile(agent_id: str, request: Request):
    """Return the authenticated agent's profile using canonical identity fields."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    profile = {
        "id": agent.get("agent_id") or agent.get("user_id") or str(agent.get("_id", "")),
        "agentUid": agent.get("agent_id") or agent.get("user_id") or agent.get("unique_id"),
        "name": (
            agent.get("name")
            or agent.get("full_name")
            or " ".join(
                x for x in (
                    agent.get("first_name") or agent.get("firstName") or "",
                    agent.get("middle_name") or agent.get("middleName") or "",
                    agent.get("last_name") or agent.get("lastName") or "",
                ) if x
            )
            or ""
        ),
        "email": agent.get("email", ""),
        "phone": agent.get("phone"),
        "whatsapp": agent.get("whatsapp"),
        "website": agent.get("website"),
        "nationality": agent.get("nationality"),
        "gender": agent.get("gender"),
        "yearsExperience": agent.get("years_experience") if agent.get("years_experience") is not None else agent.get("yearsExperience"),
        "licenseNumber": (
            agent.get("license_number")
            or agent.get("fifa_license")
            or agent.get("licenseNumber")
        ),
        "instagram": agent.get("instagram"),
        "linkedin": agent.get("linkedin"),
        "languages": agent.get("languages") or [],
        "operatingCountries": agent.get("operating_countries") or agent.get("operatingCountries") or [],
        "bio": agent.get("bio"),
        "photoUrl": agent.get("photo_url") or agent.get("photoUrl") or agent.get("avatar"),
        "isVerified": bool(agent.get("is_verified") if agent.get("is_verified") is not None else agent.get("isVerified") or False),
        "accountType": agent.get("account_type") or agent.get("accountType") or "individual",
        "subscriptionStatus": agent.get("subscription_status") or agent.get("subscriptionStatus") or "trial",
        "trialEndDate": MongoSerializer.serialize_value(
            agent.get("trial_end_date") or agent.get("trialEndDate")
        ),
        "professionalQualifications": (
            agent.get("professional_qualifications")
            or agent.get("professionalQualifications")
        ),
        "totalPlayersRepresented": (
            agent.get("total_players_represented")
            if agent.get("total_players_represented") is not None
            else agent.get("totalPlayersRepresented")
        ),
    }
    return JSONResponse({"agent": profile})


# -------------------------------------------------------------
# GET  /api/agent/{agent_id}/reports -- list reports
# POST /api/agent/{agent_id}/reports -- generate report
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/reports")
async def get_agent_reports(agent_id: str, request: Request):
    """
    Return the list of reports generated by the agent (newest first).

    Response:
        { "reports": [ { id, type, playerName, notes, status, createdAt } ] }
    """
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    cursor = (
        reports_collection
        .find({"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]})
        .sort([("created_at", -1), ("createdAt", -1)])
        .limit(200)
    )
    raw = await cursor.to_list(length=200)

    reports = []
    for r in raw:
        reports.append({
            "id":         str(r.get("_id", "")),
            "type":       r.get("type", ""),
            "playerName": (
                r.get("player_name")
                or r.get("playerName")
                or "All Players"
            ),
            "notes":      r.get("notes"),
            "status":     r.get("status", "generated"),
            "createdAt":  MongoSerializer.serialize_value(r.get("created_at") or r.get("createdAt")),
        })

    return JSONResponse({"reports": reports})


@router.post("/api/agent/{agent_id}/reports")
async def generate_agent_report(
    agent_id: str,
    request: Request,
    body: GenerateReportRequest,
):
    """Generate a new agent report while preserving canonical identity fields."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    if not (body.type or "").strip():
        raise HTTPException(status_code=400, detail="Report type is required")

    player_name: Optional[str] = None
    player_id = body.playerId
    if player_id:
        player = None
        try:
            player = await players_collection.find_one({
                "_id": ObjectId(player_id),
                "agent_id": agent_id,
            })
        except InvalidId:
            pass
        if player is None:
            player = await players_collection.find_one({
                "$or": [{"player_id": player_id}, {"user_id": player_id}],
                "agent_id": agent_id,
            })
        if player is not None:
            player_id = player.get("player_id") or player.get("user_id") or str(player.get("_id", ""))
            player_name = _resolve_player_name(player) or None

    now = MongoSerializer.now_utc()
    report_doc: Dict[str, Any] = {
        "agent_id": agent_id,
        "type": body.type.strip(),
        "player_id": player_id,
        "player_name": player_name,
        "notes": body.notes,
        "status": "generated",
        "created_at": now,
    }

    result = await reports_collection.insert_one(report_doc)

    logger.info(
        "[agent_dashboard] report type='%s' generated by agent %s",
        body.type, agent_id,
    )
    return JSONResponse({
        "success": True,
        "report": {
            "id": str(result.inserted_id),
            "type": body.type.strip(),
            "playerName": player_name or "All Players",
            "status": "generated",
            "createdAt": MongoSerializer.serialize_value(now),
        },
    }, status_code=201)


# -------------------------------------------------------------
# GET /api/agent/{agent_id}/contracts
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/contracts")
async def get_agent_contracts(agent_id: str, request: Request):
    """
    Return contract details for all players on the agent's roster,
    sorted by end date (soonest first).

    Response:
        { "contracts": [ { id, playerName, club, startDate, endDate, status } ] }
    """
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    cursor      = players_collection.find({"agent_id": agent_id})
    raw_players = await cursor.to_list(length=500)

    contracts: List[Dict[str, Any]] = []
    for p in raw_players:
        contract = p.get("contract") or {}
        # Include even players with no contract so agent sees full roster
        status    = _compute_contract_status(contract)
        contracts.append({
            "id":         (
                p.get("player_id")
                or p.get("user_id")
                or str(p.get("_id", ""))
            ),
            "playerName": _resolve_player_name(p),
            "club":       (
                p.get("club")
                or p.get("current_club")
                or p.get("currentClub")
                or None
            ),
            "startDate":  contract.get("startDate") or contract.get("start_date"),
            "endDate":    contract.get("endDate")   or contract.get("end_date"),
            "status":     status,
        })

    # Sort: soonest-expiring contracts first; entries without endDate go last
    contracts.sort(key=lambda c: c.get("endDate") or "9999-99-99")

    return JSONResponse({"contracts": contracts})


# -------------------------------------------------------------
# POST /api/agent/{agent_id}/proposals
# -------------------------------------------------------------

@router.post("/api/agent/{agent_id}/proposals")
async def send_player_proposal(
    agent_id: str,
    request: Request,
    body: ProposalRequest,
):
    """Send a contract proposal from the authenticated agent to a player."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    if not body.playerId:
        raise HTTPException(status_code=400, detail="playerId is required")
    if not body.proposedStartDate or not body.proposedEndDate:
        raise HTTPException(status_code=400, detail="Proposed contract dates are required")

    try:
        start_dt = datetime.fromisoformat(body.proposedStartDate.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(body.proposedEndDate.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format — use YYYY-MM-DD or ISO 8601")
    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="Contract end date must be after start date")
    try:
        max_end = start_dt.replace(year=start_dt.year + 1)
    except ValueError:
        max_end = start_dt.replace(year=start_dt.year + 1, day=28)
    if end_dt > max_end:
        raise HTTPException(
            status_code=400,
            detail="Contract duration cannot exceed 1 year. Adjust the proposed end date.",
        )

    player: Optional[Dict[str, Any]] = None
    try:
        player = await players_collection.find_one({"_id": ObjectId(body.playerId)})
    except InvalidId:
        pass
    if player is None:
        player = await players_collection.find_one({
            "$or": [{"player_id": body.playerId}, {"user_id": body.playerId}]
        })
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    player_id_for_check = player.get("player_id") or player.get("user_id") or str(player.get("_id", ""))
    existing_proposal = await proposals_collection.find_one({
        "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
        "player_id": player_id_for_check,
        "status": "pending",
    })
    if existing_proposal is not None:
        raise HTTPException(
            status_code=409,
            detail="A pending proposal already exists for this player. Cancel it before sending a new one.",
        )

    verification_code = secrets.token_hex(6).upper()
    contract_oid = ObjectId()
    now = MongoSerializer.now_utc()

    agent_name = agent.get("name") or agent.get("full_name") or _resolve_player_name(agent)
    agency_name = agent.get("agency") or agent.get("agency_name") or agent.get("agencyName") or ""
    player_name = _resolve_player_name(player)

    shared_fields: Dict[str, Any] = {
        "request_id": str(contract_oid),
        "agent_id": agent_id,
        "agent_name": agent_name,
        "agency": agency_name,
        "player_id": player_id_for_check,
        "player_name": player_name,
        "start_date": body.proposedStartDate,
        "end_date": body.proposedEndDate,
        "contract_duration": "1 year",
        "message": body.message,
        "verification_code": verification_code,
        "status": "pending",
        "created_at": now,
    }

    await proposals_collection.insert_one({**shared_fields})

    if agent_contracts_collection is not None:
        try:
            await agent_contracts_collection.insert_one({
                "_id": contract_oid,
                **shared_fields,
            })
        except Exception as exc:
            logger.warning("[agent_dashboard] agent_contracts insert failed: %s", exc)

    try:
        await notifications_collection.insert_one({
            "player_id": player_id_for_check,
            "user_type": "player",
            "type": "proposal_received",
            "message": (
                f"Agent {agent_name or 'An agent'} has sent you a contract proposal "
                f"({body.proposedStartDate} → {body.proposedEndDate}). "
                f"Your verification code is: {verification_code}"
            ),
            "extra_data": {
                "verification_code": verification_code,
                "request_id": str(contract_oid),
                "agent_name": agent_name,
                "start_date": body.proposedStartDate,
                "end_date": body.proposedEndDate,
            },
            "read": False,
            "created_at": now,
        })
    except Exception as notif_exc:
        logger.warning("[agent_dashboard] player notification failed for proposal: %s", notif_exc)

    logger.info(
        "[agent_dashboard] proposal sent by agent %s to player %s",
        agent_id, player_id_for_check,
    )
    return JSONResponse({"success": True}, status_code=201)

# -------------------------------------------------------------
# GET /api/agent/{agent_id}/proposals  (sent proposals history)
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/proposals")
async def get_agent_proposals(agent_id: str, request: Request):
    """Return proposals sent by the authenticated agent."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    proposals: List[Dict[str, Any]] = []

    if agent_contracts_collection is not None:
        cursor = (
            agent_contracts_collection
            .find({"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]})
            .sort([("created_at", -1), ("createdAt", -1)])
            .limit(300)
        )
        raw = await cursor.to_list(length=300)
        for doc in raw:
            proposals.append({
                "id": doc.get("request_id") or str(doc.get("_id", "")),
                "playerName": doc.get("player_name") or doc.get("playerName") or "—",
                "playerId": doc.get("player_id") or doc.get("playerId") or "",
                "startDate": doc.get("start_date") or doc.get("proposedStartDate") or doc.get("proposed_start_date"),
                "endDate": doc.get("end_date") or doc.get("proposedEndDate") or doc.get("proposed_end_date"),
                "message": doc.get("message"),
                "status": doc.get("status", "pending"),
                "createdAt": MongoSerializer.serialize_value(
                    doc.get("created_at") or doc.get("createdAt")
                ),
                "signedDate": MongoSerializer.serialize_value(
                    doc.get("signed_date") or doc.get("signedDate")
                ),
                "verificationCode": doc.get("verification_code"),
            })

    if not proposals and proposals_collection is not None:
        cursor = (
            proposals_collection
            .find({"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]})
            .sort([("created_at", -1), ("createdAt", -1)])
            .limit(300)
        )
        raw = await cursor.to_list(length=300)
        for doc in raw:
            proposals.append({
                "id": doc.get("request_id") or str(doc.get("_id", "")),
                "playerName": doc.get("player_name") or doc.get("playerName") or "—",
                "playerId": doc.get("player_id") or doc.get("playerId") or "",
                "startDate": doc.get("start_date") or doc.get("proposedStartDate"),
                "endDate": doc.get("end_date") or doc.get("proposedEndDate"),
                "message": doc.get("message"),
                "status": doc.get("status", "pending"),
                "createdAt": MongoSerializer.serialize_value(
                    doc.get("created_at") or doc.get("createdAt")
                ),
                "signedDate": None,
                "verificationCode": doc.get("verification_code"),
            })

    logger.info(
        "[agent_dashboard] proposals fetched for agent %s: %d records",
        agent_id, len(proposals),
    )
    return JSONResponse({"proposals": proposals})


# -------------------------------------------------------------
# DELETE /api/agent/{agent_id}/proposals/{request_id}  (BF3)
# Cancel a pending proposal sent by this agent.
# -------------------------------------------------------------

@router.delete("/api/agent/{agent_id}/proposals/{request_id}")
async def cancel_agent_proposal(
    agent_id: str,
    request_id: str,
    request: Request,
):
    """Cancel a pending proposal belonging to the authenticated agent."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    proposal: Optional[Dict[str, Any]] = None
    if proposals_collection is not None:
        proposal = await proposals_collection.find_one({
            "request_id": request_id,
            "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
        })

    if proposal is None and agent_contracts_collection is not None:
        try:
            proposal = await agent_contracts_collection.find_one({
                "$and": [
                    {"$or": [
                        {"request_id": request_id},
                        {"_id": ObjectId(request_id)},
                    ]},
                    {"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]},
                ],
            })
        except InvalidId:
            proposal = await agent_contracts_collection.find_one({
                "request_id": request_id,
                "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
            })

    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    current_status = proposal.get("status", "pending")
    if current_status not in ("pending", "Pending"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a proposal with status '{current_status}'",
        )

    now = MongoSerializer.now_utc()
    cancel_patch = {
        "status": "cancelled",
        "cancelled_at": now,
    }

    if proposals_collection is not None:
        await proposals_collection.update_many(
            {
                "request_id": request_id,
                "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
            },
            {"$set": cancel_patch},
        )

    if agent_contracts_collection is not None:
        query = {"request_id": request_id}
        try:
            await agent_contracts_collection.update_many(
                {"$and": [
                    {"$or": [query, {"_id": ObjectId(request_id)}]},
                    {"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]},
                ]},
                {"$set": cancel_patch},
            )
        except InvalidId:
            await agent_contracts_collection.update_many(
                {
                    "request_id": request_id,
                    "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
                },
                {"$set": cancel_patch},
            )

    player_id_str = proposal.get("player_id") or proposal.get("playerId") or ""
    agent_name = agent.get("name") or agent.get("full_name") or ""
    if player_id_str:
        try:
            await notifications_collection.insert_one({
                "player_id": player_id_str,
                "user_type": "player",
                "type": "proposal_cancelled",
                "message": f"Agent {agent_name or 'An agent'} has cancelled their contract proposal.",
                "extra_data": {
                    "request_id": request_id,
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                },
                "read": False,
                "created_at": now,
            })
        except Exception as notif_exc:
            logger.warning(
                "[agent_dashboard] cancel-proposal player notification failed: %s",
                notif_exc,
            )

    logger.info(
        "[agent_dashboard] proposal %s cancelled by agent %s",
        request_id, agent_id,
    )
    return JSONResponse({"success": True})


# -------------------------------------------------------------
# GET /api/agent/{agent_id}/subscription
# GET /api/agent/{agent_id}/subscription/history
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/subscription")
async def get_agent_subscription(agent_id: str, request: Request):
    """Return the authenticated agent's current subscription status."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    sub = await subscriptions_collection.find_one(
        {"$or": [{"agent_id": agent_id}, {"agentId": agent_id}]},
        sort=[("created_at", -1), ("createdAt", -1)],
    )

    if sub is not None:
        subscription = {
            "status": sub.get("status", "trial"),
            "plan": sub.get("plan") or sub.get("plan_key"),
            "startDate": MongoSerializer.serialize_value(
                sub.get("start_date") or sub.get("startDate")
            ),
            "endDate": MongoSerializer.serialize_value(
                sub.get("end_date") or sub.get("endDate")
            ),
        }
    else:
        subscription = {
            "status": agent.get("subscription_status") or agent.get("subscriptionStatus") or "trial",
            "plan": agent.get("subscription_plan") or agent.get("subscriptionPlan"),
            "startDate": MongoSerializer.serialize_value(
                agent.get("subscription_start_date") or agent.get("subscriptionStartDate")
            ),
            "endDate": MongoSerializer.serialize_value(
                agent.get("subscription_end_date")
                or agent.get("subscriptionEndDate")
                or agent.get("trial_end_date")
                or agent.get("trialEndDate")
            ),
        }

    return JSONResponse({"subscription": subscription})





# -------------------------------------------------------------
# PATCH /api/agent/{agent_id}/settings
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/subscription/history")
async def get_agent_subscription_history(agent_id: str, request: Request):
    """Return the authenticated agent's payment/subscription history."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    canonical_id = agent.get("agent_id") or agent.get("user_id") or agent.get("unique_id")
    mongo_id = str(agent.get("_id", ""))
    cursor = (
        transactions_collection
        .find({
            "$or": [
                {"agent_id": canonical_id},
                {"user_id": canonical_id},
                {"agentId": canonical_id},
                {"user_id": mongo_id},
            ]
        })
        .sort([("created_at", -1), ("createdAt", -1)])
        .limit(100)
    )
    raw = await cursor.to_list(length=100)

    payments = []
    for t in raw:
        created = t.get("created_at") or t.get("createdAt")
        payments.append({
            "plan": t.get("plan") or t.get("selected_plan") or t.get("selectedPlan") or t.get("type"),
            "amount": t.get("amount", 0),
            "reference": t.get("reference", ""),
            "status": t.get("status", ""),
            "createdAt": MongoSerializer.serialize_value(created),
            "date": MongoSerializer.serialize_value(created),
        })

    return JSONResponse({"payments": payments})


@router.patch("/api/agent/{agent_id}/settings")
async def update_agent_settings(
    agent_id: str,
    request:  Request,
    body:     SettingsRequest,
):
    """
    Update the agent's editable profile fields.

    Request body (JSON -- all fields optional):
        phone, whatsapp, website, instagram, linkedin, bio

    Response:
        { "success": true }
    """
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)

    update_fields: Dict[str, Any] = {}
    for field in ("phone", "whatsapp", "website", "instagram", "linkedin", "bio"):
        val = getattr(body, field, None)
        if val is not None:
            update_fields[field] = val.strip() if isinstance(val, str) else val

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    update_fields["updated_at"] = MongoSerializer.now_utc()

    # Use the human-readable business key to ensure we update the right document
    await agents_collection.update_one(
        {"agent_id": agent_id},
        {"$set": update_fields},
    )

    logger.info("[agent_dashboard] settings updated for agent %s", agent_id)
    return JSONResponse({"success": True})


# -------------------------------------------------------------
# GET /api/agent/{agent_id}/tokens
# Return the agent's current token balance and locked amount.
# -------------------------------------------------------------

@router.get("/api/agent/{agent_id}/tokens")
async def get_agent_tokens(agent_id: str, request: Request):
    """Return the authenticated agent's canonical token-wallet balance."""
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)
    _require_token_eligible("agent")

    ledger_doc = await agent_tokens_collection.find_one({"agent_id": agent_id})
    balance = int((ledger_doc or {}).get("balance") or 0)
    locked = int((ledger_doc or {}).get("locked") or (ledger_doc or {}).get("locked_tokens") or 0)

    return JSONResponse({
        "balance": balance,
        "locked": locked,
        "tokens": balance,
    })


# -------------------------------------------------------------
# POST /api/agent/{agent_id}/tokens/credit
# Debit tokens from agent and credit them to a contracted player.
# -------------------------------------------------------------

@router.post("/api/agent/{agent_id}/tokens/credit")
async def credit_tokens_to_player(
    agent_id: str,
    request: Request,
    body: CreditTokensRequest,
):
    """
    Transfer tokens from the authenticated agent wallet to an actively
    contracted player wallet using the canonical token collections.
    """
    agent = await _resolve_agent(request)
    _guard_agent_id(agent, agent_id)
    _require_token_eligible("agent")

    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be a positive integer")

    player: Optional[Dict[str, Any]] = None
    try:
        player = await players_collection.find_one({"_id": ObjectId(body.playerId)})
    except InvalidId:
        pass
    if player is None:
        player = await players_collection.find_one({
            "$or": [{"player_id": body.playerId}, {"user_id": body.playerId}]
        })
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    player_id_str = player.get("player_id") or player.get("user_id") or str(player.get("_id", ""))

    if agent_contracts_collection is None:
        raise HTTPException(status_code=503, detail="Contract service is unavailable")

    active_contract = await agent_contracts_collection.find_one({
        "$or": [{"agent_id": agent_id}, {"agentId": agent_id}],
        "$and": [
            {"$or": [{"player_id": player_id_str}, {"playerId": body.playerId}]},
            {"status": {"$in": ["Active", "active"]}},
        ],
    })
    if active_contract is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "This player does not have an active contract with you. "
                "Tokens can only be credited to actively contracted players."
            ),
        )

    agent_wallet = await agent_tokens_collection.find_one({"agent_id": agent_id})
    agent_balance = int((agent_wallet or {}).get("balance") or 0)
    if agent_balance < body.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient token balance. You have {agent_balance} token(s) but tried to credit {body.amount}.",
        )

    player_wallet = await player_tokens_collection.find_one({"player_id": player_id_str})
    player_balance = int((player_wallet or {}).get("balance") or 0)

    now = MongoSerializer.now_utc()
    new_agent_balance = agent_balance - body.amount
    new_player_balance = player_balance + body.amount

    # Canonical wallet fields and UTC timestamps.
    try:
        if agent_wallet is None:
            raise HTTPException(status_code=409, detail="Agent token wallet not found")
        await agent_tokens_collection.update_one(
            {"_id": agent_wallet["_id"]},
            {"$set": {"balance": new_agent_balance, "updated_at": now}},
        )

        if player_wallet is not None:
            await player_tokens_collection.update_one(
                {"_id": player_wallet["_id"]},
                {"$set": {"balance": new_player_balance, "updated_at": now}},
            )
        else:
            await player_tokens_collection.insert_one({
                "player_id": player_id_str,
                "balance": body.amount,
                "expiry_date": None,
                "created_at": now,
                "updated_at": now,
            })
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[agent_dashboard] token wallet transfer failed: %s", exc)
        try:
            await agent_tokens_collection.update_one(
                {"_id": agent_wallet["_id"]},
                {"$set": {"balance": agent_balance, "updated_at": now}},
            )
        except Exception:
            logger.exception("[agent_dashboard] agent token rollback failed")
        raise HTTPException(status_code=500, detail="Token credit failed — transaction rolled back")

    tx_doc = {
        "type": "agent_credit",
        "agent_id": agent_id,
        "player_id": player_id_str,
        "agent_name": agent.get("name") or agent.get("full_name") or "",
        "player_name": _resolve_player_name(player),
        "amount": body.amount,
        "description": body.description or f"Token credit from agent {agent_id}",
        "balance_before": agent_balance,
        "balance_after": new_agent_balance,
        "player_balance_before": player_balance,
        "player_balance_after": new_player_balance,
        "status": "completed",
        "created_at": now,
    }
    try:
        await token_transactions_collection.insert_one(tx_doc)
    except Exception as tx_exc:
        logger.warning("[agent_dashboard] token transaction record failed: %s", tx_exc)

    try:
        await notifications_collection.insert_one({
            "player_id": player_id_str,
            "user_type": "player",
            "type": "tokens_credited",
            "message": (
                f"{tx_doc['agent_name'] or 'Your agent'} has credited {body.amount} token(s) "
                f"to your account. "
                + (f'Note: "{body.description}"' if body.description else "")
            ).strip(),
            "extra_data": {
                "agent_id": agent_id,
                "agent_name": tx_doc["agent_name"],
                "tokens_credited": body.amount,
                "new_balance": new_player_balance,
            },
            "read": False,
            "created_at": now,
        })
    except Exception as notif_exc:
        logger.warning("[agent_dashboard] credit-tokens player notification failed: %s", notif_exc)

    return JSONResponse({
        "success": True,
        "agentBalance": new_agent_balance,
        "playerBalance": new_player_balance,
    })


# ============================================================
# END: API ROUTES / ROUTER EXPORT
# ============================================================
# main.py owns FastAPI application assembly and router mounting.
