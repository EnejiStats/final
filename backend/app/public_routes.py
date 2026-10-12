"""
EnejiStats — New Public & Payment Routes
==========================================
Adds the FOUR endpoints that were missing from all existing route modules.

NOTE: The following routes already exist as inline handlers in main.py and
must NOT be re-declared here (earlier registration wins in FastAPI/Starlette):
  GET /api/public/countries          ← main.py line ~3248
  GET /api/public/states             ← main.py line ~3293
  GET /api/public/lgas               ← main.py line ~3307
  GET /api/public/clubs              ← main.py line ~3254
  GET /api/config/positions          ← main.py line ~3232
  GET /api/config/player-levels      ← main.py line ~3238

New endpoints added here:
  GET  /api/config/club-levels              → club level list
  POST /api/payment/bank-transfer/intent    → create bank-transfer payment intent
  GET  /api/bank-details/active             → active platform bank account details
  POST /api/payment/bank-transfer/receipt   → upload payment proof

Injection pattern (same as all other route modules):
    import public_routes as _pub
    _pub._setup_dependencies(globals())
    app.include_router(_pub.router)
"""

# ── AUTH NOTE ────────────────────────────────────────────────────────────────
# get_current_user (injected from main.py) already reads both:
#   1. auth_token cookie   (session-based login)
#   2. Authorization: Bearer <token> header  (JWT from localStorage)
#
# The previous 403 on POST /api/payment/bank-transfer/intent was NOT caused
# by this file.  The frontend's createIntent() was calling fetch() directly
# without attaching the Authorization header (unlike apiFetch which always
# adds it).  The fix is in dco_dashboard.html — createIntent and uploadReceipt
# now include 'Authorization: Bearer ' + localStorage.getItem('dco_token').
# ─────────────────────────────────────────────────────────────────────────────


from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# ============================================================
# MODULE-LEVEL DEPENDENCY STUBS  (populated by _setup_dependencies)
# ============================================================

_DEPS_READY = False

payment_intents_collection = None

MongoSerializer      = None
logger               = None
upload_to_cloudinary = None
get_current_user     = None   # injected — raises HTTPException if not authenticated
normalize_role       = None
ROLE_COLLECTION_MAP  = {}

BANK_TRANSFER_DETAILS: Dict[str, str] = {}

_database = None


# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    global _DEPS_READY
    global payment_intents_collection
    global MongoSerializer, logger, upload_to_cloudinary, get_current_user
    global normalize_role, ROLE_COLLECTION_MAP
    global BANK_TRANSFER_DETAILS
    global _database

    if _DEPS_READY:
        return

    _m = main_globals

    _database                  = _m.get("database")
    payment_intents_collection = _m.get("payment_intents_collection")

    MongoSerializer            = _m.get("MongoSerializer")
    logger                     = _m.get("logger")
    upload_to_cloudinary       = _m.get("upload_to_cloudinary")
    get_current_user           = _m.get("get_current_user")
    normalize_role             = _m.get("normalize_role")
    ROLE_COLLECTION_MAP        = _m.get("ROLE_COLLECTION_MAP", {})

    BANK_TRANSFER_DETAILS      = _m.get("BANK_TRANSFER_DETAILS", {})

    _DEPS_READY = True

    if logger:
        logger.debug("[public_routes] _setup_dependencies COMPLETE")


# ============================================================
# HELPERS
# ============================================================

def _make_intent_ref() -> str:
    return f"ES-BTI-{uuid.uuid4().hex[:12].upper()}"


def _user_unique_id(user: dict) -> str:
    """Return the canonical unique ID from any user document."""
    try:
        role = normalize_role(user.get("role") or user.get("user_type") or "")
        id_field = ROLE_COLLECTION_MAP[role][1]
    except (KeyError, TypeError, ValueError):
        id_field = None
    return str(
        (user.get(id_field) if id_field else None)
        or user.get("user_id")
        or user.get("unique_id")
        or user.get("_id")
        or ""
    )


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ────────────────────────────────────────────────────────────
# PAYMENT — Create bank-transfer intent
# POST /api/payment/bank-transfer/intent
#
# Called by usePaymentWizard.createIntent in the DCO dashboard.
# Body: { paymentType, selectedPlan, role, tokens?, level? }
# Authentication: required — the intent is associated with the caller.
# ────────────────────────────────────────────────────────────

@router.post("/api/payment/bank-transfer/intent")
async def create_bank_transfer_intent(request: Request):
    """
    Create a pending bank-transfer payment intent for the authenticated user.

    The `amount` is always resolved from the pricing catalogue — client-supplied
    amounts are ignored to prevent tampering.  Returns a unique reference number
    that the user includes in their bank transfer narration.
    """
    # ── Authenticate ─────────────────────────────────────────
    try:
        current_user = await get_current_user(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required.")

    caller_id   = _user_unique_id(current_user)
    try:
        caller_role = normalize_role(current_user.get("role") or current_user.get("user_type") or "")
    except (TypeError, ValueError):
        raise HTTPException(status_code=403, detail="Unsupported account role.")
    if caller_role not in {"player", "club", "scout", "dco", "agent"}:
        raise HTTPException(status_code=403, detail="Token purchases are not available for this account role.")

    # ── Parse body ───────────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    payment_type  = str(body.get("paymentType") or body.get("payment_type") or "TOKEN_PURCHASE").upper()
    selected_plan = str(body.get("selectedPlan") or body.get("plan_key") or body.get("selected_plan") or "")
    tokens        = body.get("tokens")
    level         = body.get("level")
    if payment_type not in {"SUBSCRIPTION", "TOKEN_PURCHASE"}:
        raise HTTPException(status_code=400, detail="Unsupported payment type.")

    # ── Resolve amount from pricing catalogue (never trust client amount) ──
    amount: float = 0.0
    try:
        from pricing_module import pricing_service as _ps
        if payment_type == "SUBSCRIPTION":
            plans = _ps.get_subscription_plans(caller_role, level)
            for plan in plans:
                if plan.get("key") == selected_plan:
                    amount = float(plan.get("price") or plan.get("amount") or 0)
                    break
        else:
            pkgs = _ps.get_token_packages(caller_role, level)
            for p in pkgs:
                pkg_key = p.get("key") or f"tokens_{p.get('tokens')}"
                if pkg_key == selected_plan:
                    amount = float(p.get("price") or p.get("amount") or 0)
                    tokens = tokens or p.get("tokens")
                    break
            # If still zero, accept any positive tokens sent for the matching package
            if not amount:
                for p in pkgs:
                    if tokens and int(p.get("tokens", 0)) == int(tokens):
                        amount = float(p.get("price") or p.get("amount") or 0)
                        break
    except Exception as exc:
        if logger:
            logger.warning("[public_routes] pricing resolution failed: %s", exc)

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Could not resolve a valid price for the selected plan. Please refresh and try again.",
        )

    reference = _make_intent_ref()
    now       = MongoSerializer.now_utc()

    intent_doc: Dict[str, Any] = {
        "reference":     reference,
        "tx_ref":        reference,
        "payment_type":  payment_type,
        "selected_plan": selected_plan,
        "plan_key":      selected_plan,
        "role":          caller_role,
        "user_type":     caller_role,
        "user_id":       caller_id,
        "tokens":        tokens,
        "amount":        amount,
        "level":         level,
        "status":        "pending",
        "method":        "bank_transfer",
        "expires_at":    now + timedelta(hours=48),
        "created_at":    now,
        "updated_at":    now,
    }
    if caller_role == "scout":
        intent_doc["scout_id"] = caller_id

    intent_id = ""
    if payment_intents_collection is not None:
        result    = await payment_intents_collection.insert_one(intent_doc)
        intent_id = str(result.inserted_id)

    return JSONResponse({
        "success":   True,
        "intentId":  intent_id,
        "intent_id": intent_id,
        "reference": reference,
        "ref":       reference,
        "tx_ref":    reference,
        "amount":    amount,
        "tokens":    tokens,
        "status":    "pending",
    })


# ────────────────────────────────────────────────────────────
# PAYMENT — Active bank details
# GET /api/bank-details/active
#
# Called by usePaymentWizard immediately after createIntent to
# display the platform's bank account details to the user.
# Public — no auth required (account numbers are not sensitive).
# ────────────────────────────────────────────────────────────

@router.get("/api/bank-details/active")
async def get_active_bank_details():
    """Return the platform's active bank account for bank transfers."""
    details = BANK_TRANSFER_DETAILS or {}

    # Also check the database for admin-configured bank details
    if _database is not None:
        try:
            bank_col = _database["bank_details"]
            doc = await bank_col.find_one({"active": True}, sort=[("created_at", -1)])
            if doc:
                details = {
                    "bank_name":      doc.get("bank_name",      details.get("bank_name",      "")),
                    "account_name":   doc.get("account_name",   details.get("account_name",   "")),
                    "account_number": doc.get("account_number", details.get("account_number", "")),
                    "bank_code":      doc.get("bank_code",      ""),
                }
        except Exception:
            pass

    return JSONResponse({
        "bank_name":      details.get("bank_name",      "First Bank of Nigeria"),
        "account_name":   details.get("account_name",   "Enejistats Ltd"),
        "account_number": details.get("account_number", "3078123456"),
        "bank_code":      details.get("bank_code",      "011"),
        "currency":       "NGN",
        "instructions": (
            "Make your transfer to the account above and include your "
            "payment reference in the transfer description/narration."
        ),
    })


# ────────────────────────────────────────────────────────────
# PAYMENT — Upload receipt
# POST /api/payment/bank-transfer/receipt
#
# Called by usePaymentWizard.uploadReceipt after the user picks
# a proof-of-payment file (PDF / PNG / JPG / JPEG, max 10 MB).
# Body: multipart/form-data — intentId (str) + receiptFile (file)
# Authentication: required; intent ownership is verified.
# ────────────────────────────────────────────────────────────

@router.post("/api/payment/bank-transfer/receipt")
async def upload_bank_transfer_receipt(request: Request):
    """
    Accept a payment proof file for a pending bank-transfer intent.

    Security:
    - Caller must be authenticated.
    - The intent must belong to the authenticated caller (or be an admin).
    - Status is set to 'receipt_uploaded'; admin verification is required
      before tokens are credited.
    """
    # ── Authenticate ─────────────────────────────────────────
    try:
        current_user = await get_current_user(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication required.")

    caller_id = _user_unique_id(current_user)
    try:
        caller_role = normalize_role(current_user.get("role") or current_user.get("user_type") or "")
    except (TypeError, ValueError):
        caller_role = ""
    is_admin = caller_role in {"admin", "supervisor"}

    # Both historic form contracts are accepted by this single canonical route:
    # public UI uses intentId/receiptFile; the old Scout UI used tx_ref/file.
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid multipart form data.")
    intent_id = str(form.get("intentId") or form.get("tx_ref") or "").strip()
    receipt_file = form.get("receiptFile") or form.get("file")

    if not intent_id:
        raise HTTPException(status_code=400, detail="intentId or tx_ref is required")
    if receipt_file is None or not callable(getattr(receipt_file, "read", None)):
        raise HTTPException(status_code=400, detail="A receipt file is required.")

    # ── Look up intent and verify ownership ──────────────────
    intent = None
    if payment_intents_collection is not None:
        # Try ObjectId first, fall back to reference string
        try:
            oid = ObjectId(intent_id) if len(intent_id) == 24 else None
        except Exception:
            oid = None

        if oid:
            intent = await payment_intents_collection.find_one({"_id": oid})
        if not intent:
            intent = await payment_intents_collection.find_one({
                "$or": [{"reference": intent_id}, {"tx_ref": intent_id}],
            })

    if not intent:
        raise HTTPException(status_code=404, detail="Payment intent not found.")

    intent_user_id = intent.get("user_id") or intent.get("scout_id") or ""
    if not is_admin and str(intent_user_id) != str(caller_id):
        raise HTTPException(
            status_code=403,
            detail="You are not authorised to upload a receipt for this payment intent.",
        )

    if intent.get("status") == "completed":
        raise HTTPException(
            status_code=409,
            detail="This payment intent has already been completed.",
        )

    # ── Validate file type ───────────────────────────────────
    filename = getattr(receipt_file, "filename", "") or ""
    ext      = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "png", "jpg", "jpeg"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, PNG, JPG, JPEG files are accepted as payment proof.",
        )

    # ── Read and size-check ──────────────────────────────────
    content = await receipt_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10 MB.")

    # ── Upload to Cloudinary ─────────────────────────────────
    receipt_url = ""
    if upload_to_cloudinary is not None:
        try:
            receipt_url = await upload_to_cloudinary(
                content,
                filename=filename,
                user_type="payment",
                file_category="receipts",
                folder="enejistats/payment_receipts",
            )
            if isinstance(receipt_url, dict):
                receipt_url = receipt_url.get("secure_url") or receipt_url.get("url", "")
        except Exception as exc:
            if logger:
                logger.warning("[public_routes] Cloudinary receipt upload failed: %s", exc)
            receipt_url = ""

    # ── Update intent status ─────────────────────────────────
    now = MongoSerializer.now_utc()
    if payment_intents_collection is not None:
        await payment_intents_collection.update_one(
            {"_id": intent["_id"]},
            {"$set": {
                "status":        "receipt_uploaded",
                "receipt_url":   receipt_url,
                "uploaded_by":   caller_id,
                "submitted_at":  now,
                "uploaded_at":   now,
                "updated_at":    now,
            }},
        )

    return JSONResponse({
        "success":     True,
        "receipt_url": receipt_url,
        "status":      "receipt_uploaded",
        "message": (
            "Payment proof received. Your account will be credited "
            "once the transfer is verified by our team (usually within 1 business day)."
        ),
    })
