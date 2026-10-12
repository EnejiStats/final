"""
pricing_routes.py
=================
EnejiStats — Admin Pricing Management API Routes.

Architecture
------------
- Uses APIRouter (NOT app = FastAPI())
- Module-level placeholders set in _setup_dependencies(main_globals)
- Mount in main.py AFTER admin_dashboard_routes:
      import pricing_routes as _pricing_r
      _pricing_r._setup_dependencies(globals())
      app.include_router(_pricing_r.router)

Endpoints
---------
GET    /api/admin/pricing/config               Full pricing config (subscription, tokens, DCO/sup rates)
PATCH  /api/admin/pricing/config               Update any part of the pricing config (with invariant checks)
GET    /api/admin/pricing/countries            All country multipliers (defaults + overrides)
PATCH  /api/admin/pricing/country/{code}       Update a single country multiplier
DELETE /api/admin/pricing/country/{code}       Reset a country multiplier to the default
GET    /api/admin/pricing/regions              Region groups with current effective multipliers
PATCH  /api/admin/pricing/region/{region}      Apply a multiplier to all countries in a region
POST   /api/admin/pricing/bulk-preview         Preview what a bulk multiplier would produce
POST   /api/admin/pricing/bulk-apply           Commit a bulk price multiplier to the DB
"""

from __future__ import annotations

import asyncio
import copy
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ============================================================
# MODULE-LEVEL PLACEHOLDERS — set in _setup_dependencies()
# ============================================================

logger                       = None
MongoSerializer              = None
verify_token                 = None
get_admin_user               = None
platform_settings_collection = None
admins_collection            = None
activity_history_collection  = None

# pricing_service is replaced at startup with a DB-loaded instance
pricing_service              = None

# Import module-level pricing constants (always available)
# In the top-level import block (where the other pricing_module imports already are):
from pricing_module import (
    DEFAULT_COUNTRY_MULTIPLIERS,
    DEFAULT_SUBSCRIPTION_PRICES,
    DEFAULT_DCO_RATES,
    DEFAULT_SUPERVISOR_RATES,
    TOKEN_PACKAGES,
    FLAT_TOKEN_COSTS,
    PLAYER_STATS_REQUEST_TOKENS,
    CLUB_STATS_REQUEST_TOKENS,
    REGION_GROUPS,
    COUNTRY_CODE_TO_NAME,
    CANONICAL_LEVELS,
    CANONICAL_PLAN_KEYS,
    normalize_level,
    normalize_plan_key,
    apply_country_multiplier,
    get_country_multiplier,
    PricingService,
    _assert_price_invariants,   # ← ADD THIS LINE
)

_DEPS_READY = False

# ============================================================
# ROUTER
# ============================================================

router = APIRouter()

# ============================================================
# DEPENDENCY INJECTION
# ============================================================

def _setup_dependencies(main_globals: dict) -> None:
    global _DEPS_READY
    global logger, MongoSerializer, verify_token, get_admin_user
    global platform_settings_collection, admins_collection
    global activity_history_collection, pricing_service

    g = main_globals
    logger                       = g.get("logger")
    MongoSerializer              = g.get("MongoSerializer")
    verify_token                 = g.get("verify_token")
    get_admin_user               = g.get("get_admin_user")
    platform_settings_collection = g.get("platform_settings_collection")
    admins_collection            = g.get("admins_collection")
    activity_history_collection  = g.get("activity_history_collection")
    pricing_service              = g.get("pricing_service")
    _DEPS_READY = True
    if logger:
        logger.info("[pricing_routes] Dependencies injected — %d routes registered", len(router.routes))


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now() -> datetime:
    return MongoSerializer.now_utc()


def _s(doc: Optional[dict]) -> dict:
    if not doc:
        return {}
    return MongoSerializer.serialize_document(doc)


def _log(actor_id: str, atype: str, desc: str) -> None:
    async def _inner():
        try:
            await activity_history_collection.insert_one({
                "actor_id":    actor_id,
                "actor_role":  "admin",
                "type":        atype,
                "description": desc,
                "created_at":  _now(),
            })
        except Exception:
            pass
    if activity_history_collection is not None:
        asyncio.ensure_future(_inner())


async def _require_admin(request: Request) -> dict:
    """Require the canonical active Admin identity from main.py."""
    if not callable(get_admin_user):
        raise HTTPException(status_code=503, detail="Admin auth service not ready")
    return await get_admin_user(request)

async def _load_platform_doc() -> dict:
    """Load the platform settings document from MongoDB."""
    if platform_settings_collection is None:
        raise HTTPException(status_code=503, detail="Pricing settings database is unavailable")
    try:
        doc = await platform_settings_collection.find_one({"key": "platform"})
    except Exception as exc:
        if logger:
            logger.exception("Failed to read platform pricing settings")
        raise HTTPException(status_code=503, detail="Unable to load pricing settings") from exc
    return doc or {}


async def _save_platform_doc(updates: dict, admin_id: str) -> None:
    global pricing_service
    if platform_settings_collection is None:
        raise HTTPException(status_code=503, detail="Pricing settings database is unavailable")
    updates = copy.deepcopy(updates)
    updates["key"] = "platform"
    updates["updated_at"] = _now()
    updates["updated_by"] = admin_id
    try:
        await platform_settings_collection.update_one(
            {"key": "platform"}, {"$set": updates}, upsert=True
        )
    except Exception as exc:
        if logger:
            logger.exception("Failed to persist pricing settings")
        raise HTTPException(status_code=503, detail="Unable to save pricing settings") from exc
    # Reload the singleton from the updated doc
    doc = await platform_settings_collection.find_one({"key": "platform"})
    if doc:
        new_service = PricingService.from_db_settings(doc)
        pricing_service = new_service              # refresh local ref in pricing_routes

        # Also update the canonical singleton in pricing_module so that
        # all other route modules see live prices without a server restart.
        import pricing_module as _pm_ref           # cached sys.modules lookup — no re-execution
        _pm_ref.pricing_service = new_service
          
# ============================================================
# PYDANTIC MODELS
# ============================================================

class BulkPreviewBody(BaseModel):
    role:       str
    multiplier: float
    level:      Optional[str] = None
    plan_key:   Optional[str] = None  # if omitted, preview all durations


class BulkApplyBody(BaseModel):
    role:       str
    multiplier: float
    level:      Optional[str] = None  # if omitted, apply to all levels for player/club
    plan_key:   Optional[str] = None  # if omitted, apply to all durations


class CountryMultiplierBody(BaseModel):
    multiplier: float


class RegionMultiplierBody(BaseModel):
    multiplier:        float
    force_all:         bool = False  # True → overwrite individual overrides too


class PricingConfigPatch(BaseModel):
    subscription_pricing: Optional[Dict[str, Any]] = None
    token_packages:       Optional[Dict[str, Any]] = None
    token_costs:          Optional[Dict[str, Any]] = None
    dco_rates:            Optional[Dict[str, Any]] = None
    supervisor_rates:     Optional[Dict[str, Any]] = None


# ============================================================
# ENDPOINTS — FULL PRICING CONFIG
# ============================================================

@router.get("/api/admin/pricing/config")
async def get_pricing_config(request: Request):
    """
    Return the complete pricing configuration:
    - subscription_pricing (by role, by level, by duration)
    - token_packages (by role, by level)
    - token_costs (player_stats, club_stats, flat)
    - dco_rates (tier1/2/3, by level)
    - supervisor_rates (tier1/2/3, by level)
    - country_multipliers (ISO code → float)
    - metadata (canonical levels, plan keys, region groups)
    """
    await _require_admin(request)
    doc = await _load_platform_doc()

    sub_pricing  = doc.get("subscription_pricing")  or DEFAULT_SUBSCRIPTION_PRICES
    tok_packages = doc.get("token_packages")        or TOKEN_PACKAGES
    tok_costs    = doc.get("token_costs")           or {
        "player_stats": PLAYER_STATS_REQUEST_TOKENS,
        "club_stats":   CLUB_STATS_REQUEST_TOKENS,
        "flat":         FLAT_TOKEN_COSTS,
    }
    dco_rates    = doc.get("dco_rates")            or DEFAULT_DCO_RATES
    sup_rates    = doc.get("supervisor_rates")      or DEFAULT_SUPERVISOR_RATES
    country_mult = doc.get("country_multipliers")   or {}

    # Merge defaults with overrides for country display
    merged_countries: Dict[str, Any] = {}
    for code, default_mult in DEFAULT_COUNTRY_MULTIPLIERS.items():
        merged_countries[code] = {
            "code":       code,
            "name":       COUNTRY_CODE_TO_NAME.get(code, code),
            "multiplier": country_mult.get(code, default_mult),
            "is_default": code not in country_mult,
        }
    # Inject any extra overrides not in the default list
    for code, mult in country_mult.items():
        if code not in merged_countries:
            merged_countries[code] = {
                "code":       code,
                "name":       COUNTRY_CODE_TO_NAME.get(code, code),
                "multiplier": mult,
                "is_default": False,
            }

    return JSONResponse({
        "subscription_pricing": sub_pricing,
        "token_packages":       tok_packages,
        "token_costs":          tok_costs,
        "dco_rates":            dco_rates,
        "supervisor_rates":     sup_rates,
        "country_multipliers":  merged_countries,
        "canonical_levels":     CANONICAL_LEVELS,
        "canonical_plan_keys":  CANONICAL_PLAN_KEYS,
        "region_groups":        REGION_GROUPS,
    })


@router.patch("/api/admin/pricing/config")
async def update_pricing_config(request: Request):
    """
    Partial update of pricing configuration.

    Accepts any subset of:
      subscription_pricing, token_packages, token_costs,
      dco_rates, supervisor_rates

    Runs price invariant checks before persisting.
    """
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="JSON body must be an object")
    allowed = {"subscription_pricing", "token_packages", "token_costs", "dco_rates", "supervisor_rates"}
    unknown = set(body) - allowed
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported pricing fields: {sorted(unknown)}")
    current_doc = await _load_platform_doc()
    merged = {
        "subscription_pricing": copy.deepcopy(current_doc.get("subscription_pricing") or DEFAULT_SUBSCRIPTION_PRICES),
        "token_packages": copy.deepcopy(current_doc.get("token_packages") or TOKEN_PACKAGES),
        "token_costs": copy.deepcopy(current_doc.get("token_costs") or {"player_stats": PLAYER_STATS_REQUEST_TOKENS, "club_stats": CLUB_STATS_REQUEST_TOKENS, "flat": FLAT_TOKEN_COSTS}),
        "dco_rates": copy.deepcopy(current_doc.get("dco_rates") or DEFAULT_DCO_RATES),
        "supervisor_rates": copy.deepcopy(current_doc.get("supervisor_rates") or DEFAULT_SUPERVISOR_RATES),
    }
    updates: Dict[str, Any] = {}

    if "subscription_pricing" in body:
        new_pricing = body["subscription_pricing"]
        # Validate price invariants
        try:
            _assert_price_invariants(new_pricing)
        except (AssertionError, KeyError, TypeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=f"Invalid subscription pricing: {e}")
        merged["subscription_pricing"] = new_pricing
        updates["subscription_pricing"] = new_pricing

    if "token_packages" in body:
        if not isinstance(body["token_packages"], dict): raise HTTPException(status_code=422, detail="token_packages must be an object")
        merged["token_packages"] = body["token_packages"]
        updates["token_packages"] = body["token_packages"]

    if "token_costs" in body:
        if not isinstance(body["token_costs"], dict): raise HTTPException(status_code=422, detail="token_costs must be an object")
        merged["token_costs"] = body["token_costs"]
        updates["token_costs"] = body["token_costs"]

    if "dco_rates" in body:
        if not isinstance(body["dco_rates"], dict): raise HTTPException(status_code=422, detail="dco_rates must be an object")
        merged["dco_rates"] = body["dco_rates"]
        updates["dco_rates"] = body["dco_rates"]

    if "supervisor_rates" in body:
        if not isinstance(body["supervisor_rates"], dict): raise HTTPException(status_code=422, detail="supervisor_rates must be an object")
        merged["supervisor_rates"] = body["supervisor_rates"]
        updates["supervisor_rates"] = body["supervisor_rates"]

    if not updates:
        raise HTTPException(status_code=400, detail="No recognised fields provided")

    try:
        _assert_price_invariants(merged["subscription_pricing"])
        # Constructing the service checks that the merged structures are copyable and usable.
        PricingService.from_db_settings(merged)
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid pricing configuration: {exc}") from exc

    await _save_platform_doc(updates, admin_id)
    _log(admin_id, "pricing_config_updated", f"Pricing config updated: {list(updates.keys())}")
    return JSONResponse({"success": True, "updated_fields": list(updates.keys())})


# ============================================================
# ENDPOINTS — COUNTRY PRICING
# ============================================================

@router.get("/api/admin/pricing/countries")
async def get_country_pricing(request: Request):
    """
    Return all country pricing multipliers with names and region group.

    Returns a list sorted by region then country name.
    """
    await _require_admin(request)
    doc = await _load_platform_doc()
    overrides = doc.get("country_multipliers") or {}

    # Build a reverse lookup: code → regions it belongs to
    code_to_regions: Dict[str, List[str]] = {}
    for region_name, codes in REGION_GROUPS.items():
        for c in codes:
            code_to_regions.setdefault(c, []).append(region_name)

    result = []
    for code, default_mult in DEFAULT_COUNTRY_MULTIPLIERS.items():
        result.append({
            "code":         code,
            "name":         COUNTRY_CODE_TO_NAME.get(code, code),
            "multiplier":   overrides.get(code, default_mult),
            "default":      default_mult,
            "is_overridden": code in overrides,
            "regions":      code_to_regions.get(code, []),
        })

    # Sort by primary region name, then country name
    result.sort(key=lambda x: (x["regions"][0] if x["regions"] else "zzz", x["name"]))
    return JSONResponse({
        "countries":      result,
        "total":          len(result),
        "region_groups":  REGION_GROUPS,
    })


@router.patch("/api/admin/pricing/country/{country_code}")
async def update_country_multiplier(country_code: str, request: Request):
    """Update the price multiplier for a single country."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    multiplier = body.get("multiplier")
    if multiplier is None:
        raise HTTPException(status_code=400, detail="'multiplier' is required")
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'multiplier' must be a number")
    if not math.isfinite(multiplier) or not 0.01 <= multiplier <= 100:
        raise HTTPException(status_code=422, detail="multiplier must be finite and between 0.01 and 100")

    code = country_code.upper().strip()
    if len(code) != 2 or code not in COUNTRY_CODE_TO_NAME:
        raise HTTPException(status_code=422, detail="Unknown ISO country code")
    doc = await _load_platform_doc()
    country_multipliers = dict(doc.get("country_multipliers") or {})
    country_multipliers[code] = multiplier

    await _save_platform_doc({"country_multipliers": country_multipliers}, admin_id)
    _log(admin_id, "country_pricing_updated", f"Country {code} multiplier → {multiplier}")
    return JSONResponse({
        "success":    True,
        "code":       code,
        "name":       COUNTRY_CODE_TO_NAME.get(code, code),
        "multiplier": multiplier,
    })


@router.delete("/api/admin/pricing/country/{country_code}")
async def reset_country_multiplier(country_code: str, request: Request):
    """Reset a country's multiplier to the platform default."""
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    code = country_code.upper().strip()
    if len(code) != 2 or code not in COUNTRY_CODE_TO_NAME:
        raise HTTPException(status_code=422, detail="Unknown ISO country code")
    doc = await _load_platform_doc()
    country_multipliers = dict(doc.get("country_multipliers") or {})
    country_multipliers.pop(code, None)

    await _save_platform_doc({"country_multipliers": country_multipliers}, admin_id)
    default_mult = DEFAULT_COUNTRY_MULTIPLIERS.get(code, 1.0)
    _log(admin_id, "country_pricing_reset", f"Country {code} multiplier reset to default {default_mult}")
    return JSONResponse({
        "success":     True,
        "code":        code,
        "name":        COUNTRY_CODE_TO_NAME.get(code, code),
        "multiplier":  default_mult,
        "is_default":  True,
    })


# ============================================================
# ENDPOINTS — REGION PRICING
# ============================================================

@router.get("/api/admin/pricing/regions")
async def get_region_pricing(request: Request):
    """
    Return all region groups with the effective per-country multipliers.
    """
    await _require_admin(request)
    doc = await _load_platform_doc()
    overrides = doc.get("country_multipliers") or {}

    regions = []
    for region_name, codes in REGION_GROUPS.items():
        country_data = []
        for code in codes:
            default_mult = DEFAULT_COUNTRY_MULTIPLIERS.get(code, 1.0)
            country_data.append({
                "code":         code,
                "name":         COUNTRY_CODE_TO_NAME.get(code, code),
                "multiplier":   overrides.get(code, default_mult),
                "is_overridden": code in overrides,
            })
        # Region-level summary: average of effective multipliers
        effective_mults = [c["multiplier"] for c in country_data]
        avg_mult = round(sum(effective_mults) / len(effective_mults), 3) if effective_mults else 1.0
        regions.append({
            "region":           region_name,
            "avg_multiplier":   avg_mult,
            "country_count":    len(codes),
            "countries":        country_data,
        })

    return JSONResponse({"regions": regions, "total": len(regions)})


@router.patch("/api/admin/pricing/region/{region_name}")
async def update_region_multiplier(region_name: str, request: Request):
    """
    Apply a single multiplier to all countries in a named region.

    Body:
      { "multiplier": 1.2, "force_all": false }

    If ``force_all`` is false (default), only countries WITHOUT an existing
    individual override are updated.
    If ``force_all`` is true, all countries in the region are overwritten.
    """
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # URL-encode spaces: region names may contain spaces
    region_name_decoded = region_name.replace("-", " ")
    if region_name_decoded not in REGION_GROUPS:
        raise HTTPException(status_code=404, detail=f"Region '{region_name_decoded}' not found")

    multiplier = body.get("multiplier")
    if multiplier is None:
        raise HTTPException(status_code=400, detail="'multiplier' is required")
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'multiplier' must be a number")
    if not math.isfinite(multiplier) or not 0.01 <= multiplier <= 100:
        raise HTTPException(status_code=422, detail="multiplier must be finite and between 0.01 and 100")

    force_all_value = body.get("force_all", False)
    if not isinstance(force_all_value, bool):
        raise HTTPException(status_code=422, detail="force_all must be a boolean")
    force_all = force_all_value

    doc = await _load_platform_doc()
    country_multipliers = dict(doc.get("country_multipliers") or {})
    codes = REGION_GROUPS[region_name_decoded]
    updated: List[str] = []

    for code in codes:
        if force_all or code not in country_multipliers:
            country_multipliers[code] = multiplier
            updated.append(code)

    await _save_platform_doc({"country_multipliers": country_multipliers}, admin_id)
    _log(admin_id, "region_pricing_updated",
         f"Region '{region_name_decoded}' multiplier → {multiplier} (force_all={force_all}), "
         f"{len(updated)} countries updated")
    return JSONResponse({
        "success":           True,
        "region":            region_name_decoded,
        "multiplier":        multiplier,
        "countries_updated": updated,
        "total_in_region":   len(codes),
    })


# ============================================================
# ENDPOINTS — BULK PRICE PREVIEW & APPLY
# ============================================================

@router.post("/api/admin/pricing/bulk-preview")
async def bulk_price_preview(request: Request):
    """
    Preview what subscription prices would become for a role/level
    if all base prices were scaled by a multiplier.

    Body:
      {
        "role":       "player",           # required
        "multiplier": 1.1,                # required
        "level":      "professional",     # optional — only for player/club
        "plan_key":   "monthly"           # optional — preview single duration only
      }

    Returns: before/after price map (no DB writes).
    """
    await _require_admin(request)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    role       = (body.get("role") or "").lower().strip()
    level      = body.get("level")
    plan_key   = body.get("plan_key")
    multiplier = body.get("multiplier")

    if not role:
        raise HTTPException(status_code=400, detail="'role' is required")
    if multiplier is None:
        raise HTTPException(status_code=400, detail="'multiplier' is required")
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'multiplier' must be a number")
    if not math.isfinite(multiplier) or not 0.01 <= multiplier <= 100:
        raise HTTPException(status_code=422, detail="multiplier must be finite and between 0.01 and 100")

    doc = await _load_platform_doc()
    svc = PricingService.from_db_settings(doc)

    try:
        preview = svc.preview_bulk_price_change(role, multiplier, level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Filter to single plan_key if requested
    if plan_key and preview.get("changes"):
        try:
            pk = normalize_plan_key(plan_key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        preview["changes"] = {k: v for k, v in preview["changes"].items() if v.get("plan_key", k.split(":")[-1]) == pk}

    return JSONResponse(preview)


@router.post("/api/admin/pricing/bulk-apply")
async def bulk_price_apply(request: Request):
    """
    Commit a bulk price multiplier to the database.

    Body:
      {
        "role":       "player",           # required
        "multiplier": 1.1,                # required
        "level":      null,               # optional — null = apply to all levels
        "plan_key":   null                # optional — null = apply to all durations
      }

    This is a DESTRUCTIVE action — original prices are overwritten.
    The price invariants (quarterly < 3×monthly, annual < 12×monthly)
    are enforced for player and club roles before committing.
    """
    admin = await _require_admin(request)
    admin_id = admin.get("admin_id") or str(admin.get("_id", ""))

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    role       = (body.get("role") or "").lower().strip()
    level      = body.get("level")
    plan_key   = body.get("plan_key")
    multiplier = body.get("multiplier")

    if not role:
        raise HTTPException(status_code=400, detail="'role' is required")
    if multiplier is None:
        raise HTTPException(status_code=400, detail="'multiplier' is required")
    try:
        multiplier = float(multiplier)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'multiplier' must be a number")
    if not math.isfinite(multiplier) or not 0.01 <= multiplier <= 100:
        raise HTTPException(status_code=422, detail="multiplier must be finite and between 0.01 and 100")

    # Load current config, apply bulk change, validate, persist
    doc = await _load_platform_doc()
    svc = PricingService.from_db_settings(doc)

    try:
        summary = svc.bulk_apply_price_change(role, multiplier, level, plan_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate invariants after mutation
    if role in ("player", "club"):
        try:
            _assert_price_invariants(svc._subscription_pricing)
        except AssertionError as e:
            raise HTTPException(status_code=400, detail=f"Price invariant violated: {e}")

    # Persist the mutated pricing
    await _save_platform_doc(
        {"subscription_pricing": svc._subscription_pricing},
        admin_id,
    )
    _log(admin_id, "bulk_price_applied",
         f"Bulk price ×{multiplier} applied to {role}"
         + (f"/{level}" if level else "")
         + (f" [{plan_key}]" if plan_key else ""))

    return JSONResponse({
        "success":    True,
        "role":       role,
        "multiplier": multiplier,
        "summary":    summary,
    })