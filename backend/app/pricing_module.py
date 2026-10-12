# ============================================================
# pricing_module.py
# EnejiStats — Unified Pricing Module
# Extracted from main.py and extended with:
#   - Country/region-aware price multipliers
#   - Bulk price review helpers
#   - Regional pricing overrides stored in MongoDB
# ============================================================

from __future__ import annotations

import copy
import os
import math
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

# ── Location data — single source of truth ────────────────────────────────────
from location_module import COUNTRY_NAMES, validate_country_code

# ─────────────────────────────────────────────────────────────────────────────
# 1.  LEVEL NORMALISATION
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_LEVELS: List[str] = [
    "professional",
    "semi_professional",
    "academy",
    "university",
    "local",
    "other",
]

#: Every accepted alias → canonical key (case-insensitive after .lower())
LEVEL_ALIAS_MAP: Dict[str, str] = {
    # professional
    "professional":      "professional",
    # semi_professional
    "semi professional": "semi_professional",
    "semi-professional": "semi_professional",
    "semi_professional": "semi_professional",
    "semi-pro":          "semi_professional",
    "semi_pro":          "semi_professional",
    "semiprofessional":  "semi_professional",
    # academy
    "academy":           "academy",
    # university
    "university":        "university",
    # local  (amateur is treated as local)
    "local":             "local",
    "amateur":           "local",
    # other
    "other":             "other",
    "others":            "other",
}


def normalize_level(raw: str) -> str:
    """
    Normalise any accepted level alias to its canonical key.

    Args:
        raw: Raw level string from user input or database.

    Returns:
        Canonical level key (e.g. ``"semi_professional"``).

    Raises:
        ValueError: If the value cannot be mapped.
    """
    if not raw:
        raise ValueError("Level must not be empty.")
    key = raw.strip().lower()
    result = LEVEL_ALIAS_MAP.get(key)
    if result is None:
        raise ValueError(
            f"Unknown level '{raw}'. "
            f"Accepted values: {sorted(LEVEL_ALIAS_MAP.keys())}"
        )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2.  PLAN KEY NORMALISATION  (monthly | quarterly | annual — never six_month)
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_PLAN_KEYS: List[str] = ["monthly", "quarterly", "annual"]

#: Monthly count per canonical plan key
PLAN_MONTHS: Dict[str, int] = {
    "monthly":   1,
    "quarterly": 3,
    "annual":   12,
}

#: Legacy / misspelled keys → canonical (migration only — never store these)
LEGACY_PLAN_ALIAS_MAP: Dict[str, str] = {
    "six_month": "quarterly",
    "6month":    "quarterly",
    "6-month":   "quarterly",
    "6 month":   "quarterly",
    "yearly":    "annual",
    "year":      "annual",
    "month":     "monthly",
}


def normalize_plan_key(raw: str) -> str:
    """
    Normalise any plan-key alias (including legacy) to canonical.

    Args:
        raw: Raw plan key (e.g. ``"six_month"``, ``"quarterly"``).

    Returns:
        Canonical plan key: ``"monthly"``, ``"quarterly"``, or ``"annual"``.

    Raises:
        ValueError: If the value cannot be mapped.
    """
    if not raw:
        raise ValueError("Plan key must not be empty.")
    key = raw.strip().lower()
    key = LEGACY_PLAN_ALIAS_MAP.get(key, key)
    if key not in PLAN_MONTHS:
        raise ValueError(
            f"Unknown plan key '{raw}'. "
            f"Accepted values: {CANONICAL_PLAN_KEYS}"
        )
    return key


# ─────────────────────────────────────────────────────────────────────────────
# 3.  ENVIRONMENT / PLATFORM CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

BANK_TRANSFER_DETAILS: Dict[str, str] = {
    "bank_name":      os.getenv("PLATFORM_BANK_NAME",      "First Bank of Nigeria"),
    "account_name":   os.getenv("PLATFORM_ACCOUNT_NAME",   "Enejistats Ltd"),
    "account_number": os.getenv("PLATFORM_ACCOUNT_NUMBER", "3078123456"),
}

POSITIONS_CONFIG: Dict[str, List[str]] = {
    "Goalkeeper": ["GK"],
    "Defender":   ["CB", "RB", "LB", "RWB", "LWB"],
    "Midfielder": ["CDM", "CM", "CAM", "RM", "LM"],
    "Attacker":   ["ST", "CF", "LW", "RW"],
}

#: Display labels used by the frontend level picker
PLAYER_LEVELS_CONFIG: List[str] = [
    "Professional",
    "Semi-Professional",
    "Academy",
    "University",
    "Local",
    "Other",
]


# ─────────────────────────────────────────────────────────────────────────────
# 4.  TOKEN COSTS PER STATS-REQUEST ACTION
#     Keys must always be canonical level keys.
# ─────────────────────────────────────────────────────────────────────────────

#: Tokens consumed when requesting a *player's* stats (keyed by player level)
PLAYER_STATS_REQUEST_TOKENS: Dict[str, float] = {
    "professional":      3.5,
    "semi_professional": 2.5,
    "academy":           1.5,
    "university":        1.5,
    "local":             1.7,
    "other":             2.0,
}

#: Tokens consumed when requesting a *club's* stats (keyed by club level)
CLUB_STATS_REQUEST_TOKENS: Dict[str, float] = {
    "professional":      20.0,
    "semi_professional": 12.0,
    "academy":            8.0,
    "university":         6.0,
    "local":              5.0,
    "other":              5.0,
}

#: Flat per-action costs that do NOT depend on level
FLAT_TOKEN_COSTS: Dict[str, float] = {
    "club_match":    8.0,
    "heatmap_addon": 1.0,
    "match_request": 1.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# 5.  ROLE / LEVEL TOKEN COST TABLES
#     Integer token costs per canonical level key.
# ─────────────────────────────────────────────────────────────────────────────

#: Integer token cost per player level for a stats request
PLAYER_TOKEN_COSTS: Dict[str, int] = {
    "professional":      4,
    "semi_professional": 3,
    "academy":           2,
    "university":        2,
    "local":             2,
    "other":             2,
}

#: Integer token cost per club level for a stats request
CLUB_TOKEN_COSTS: Dict[str, int] = {
    "professional":      20,
    "semi_professional": 12,
    "academy":            8,
    "university":         6,
    "local":              5,
    "other":              5,
}

#: Flat token cost per scout action (level-independent)
SCOUT_TOKEN_COSTS: Dict[str, int] = {
    "default": 1,
    "other":   1,
}

#: Flat token cost per DCO action (level-independent)
DCO_TOKEN_COSTS: Dict[str, int] = {
    "default": 1,
    "other":   1,
}

#: Flat token cost per agent action (level-independent)
AGENT_TOKEN_COSTS: Dict[str, int] = {
    "default": 1,
    "other":   1,
}

#: Unified role → cost-table mapping (used by get_token_cost())
_ROLE_TOKEN_COSTS: Dict[str, Dict[str, int]] = {
    "player": PLAYER_TOKEN_COSTS,
    "club":   CLUB_TOKEN_COSTS,
    "scout":  SCOUT_TOKEN_COSTS,
    "dco":    DCO_TOKEN_COSTS,
    "agent":  AGENT_TOKEN_COSTS,
}


def get_token_cost(user_type: str, category: str) -> int:
    """
    Return the integer token cost for a given user type and level/category.

    For flat-rate roles (scout, dco, agent) the category is ignored and
    the default cost of 1 is returned.

    Level aliases are automatically normalised (e.g. ``"semi-pro"`` →
    ``"semi_professional"``).
    """
    user_type = user_type.lower().strip()
    category  = (category or "other").lower().strip()

    costs = _ROLE_TOKEN_COSTS.get(user_type)
    if costs is None:
        raise ValueError(
            f"Unsupported user type: '{user_type}'. "
            f"Valid types: {list(_ROLE_TOKEN_COSTS.keys())}"
        )

    result = costs.get(category)
    if result is not None:
        return result

    try:
        canonical = normalize_level(category)
        result = costs.get(canonical)
        if result is not None:
            return result
    except ValueError:
        pass

    return costs.get("other", costs.get("default", 1))


# ─────────────────────────────────────────────────────────────────────────────
# 6.  TOKEN PACKAGES  (role-aware, level-aware)
# ─────────────────────────────────────────────────────────────────────────────

#: Shared package tiers for roles without per-level differentiation.
_FLAT_ROLE_PACKAGES: List[Dict[str, Any]] = [
    {"tokens":  1, "price":  1_000, "bonus": None, "label": "Starter"},
    {"tokens":  3, "price":  3_000, "bonus": None, "label": "Basic"},
    {"tokens":  5, "price":  4_500, "bonus": None, "label": "Standard"},
    {"tokens": 10, "price":  9_000, "bonus": None, "label": "Pro"},
    {"tokens": 20, "price": 17_500, "bonus": None, "label": "Elite"},
    {"tokens": 50, "price": 45_000, "bonus": None, "label": "Champion"},
]

#: Shared package tiers for player/club roles (identical across all levels).
_LEVELLED_PACKAGES: List[Dict[str, Any]] = [
    {"tokens":  5, "price":  5_000, "bonus": None, "label": "Starter"},
    {"tokens": 10, "price":  9_500, "bonus": None, "label": "Basic"},
    {"tokens": 20, "price": 18_000, "bonus": None, "label": "Standard"},
    {"tokens": 50, "price": 45_000, "bonus": None, "label": "Pro"},
]

TOKEN_PACKAGES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "player": {level: _LEVELLED_PACKAGES for level in CANONICAL_LEVELS},
    "club":   {level: _LEVELLED_PACKAGES for level in CANONICAL_LEVELS},
    "scout":  {"default": _FLAT_ROLE_PACKAGES},
    "agent":  {"default": _FLAT_ROLE_PACKAGES},
    "dco":    {"default": _FLAT_ROLE_PACKAGES},
}

# ─────────────────────────────────────────────────────────────────────────────
# 7.  SUBSCRIPTION PRICES  (source of truth per role / level / duration)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SUBSCRIPTION_PRICES: Dict[str, Any] = {
    "player": {
        "professional":      {"monthly": 1_500, "quarterly":  3_800, "annual": 12_000},
        "semi_professional": {"monthly": 1_500, "quarterly":  3_800, "annual": 12_000},
        "academy":           {"monthly":   500, "quarterly":  1_200, "annual":  4_000},
        "university":        {"monthly":   500, "quarterly":  1_200, "annual":  4_000},
        "local":             {"monthly":   800, "quarterly":  2_000, "annual":  6_500},
        "other":             {"monthly":   800, "quarterly":  2_000, "annual":  6_500},
    },
    "club": {
        "professional":      {"monthly": 10_000, "quarterly": 27_000, "annual": 100_000},
        "semi_professional": {"monthly":  5_000, "quarterly": 13_500, "annual":  48_000},
        "academy":           {"monthly":  3_000, "quarterly":  8_000, "annual":  30_000},
        "university":        {"monthly":  2_500, "quarterly":  6_750, "annual":  25_000},
        "local":             {"monthly":  2_000, "quarterly":  5_400, "annual":  20_000},
        "other":             {"monthly":  2_000, "quarterly":  5_400, "annual":  20_000},
    },
    "scout": {"monthly": 20_000, "quarterly":  58_500, "annual": 230_000},
    "agent": {"monthly":  5_000, "quarterly":  13_000, "annual":  55_000},
    "dco":   {"monthly":  3_000, "quarterly":   8_500, "annual":  34_000},
}


def _assert_price_invariants(prices: Dict[str, Any]) -> None:
    """Raise AssertionError if any quarterly >= 3×monthly or annual >= 12×monthly."""
    for role, role_data in prices.items():
        if role in ("player", "club"):
            for level, tiers in role_data.items():
                m, q, a = tiers["monthly"], tiers["quarterly"], tiers["annual"]
                assert q < 3 * m, (
                    f"{role}/{level}: quarterly {q:,} must be < 3×monthly ({3*m:,})"
                )
                assert a < 12 * m, (
                    f"{role}/{level}: annual {a:,} must be < 12×monthly ({12*m:,})"
                )
        else:
            m, q, a = role_data["monthly"], role_data["quarterly"], role_data["annual"]
            assert q < 3 * m, (
                f"{role}: quarterly {q:,} must be < 3×monthly ({3*m:,})"
            )
            assert a < 12 * m, (
                f"{role}: annual {a:,} must be < 12×monthly ({12*m:,})"
            )


_assert_price_invariants(DEFAULT_SUBSCRIPTION_PRICES)

# ─────────────────────────────────────────────────────────────────────────────
# 8.  SUBSCRIPTION PLANS  (served to frontend by /api/subscriptions/plans)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SUBSCRIPTION_PLANS: Dict[str, List[Dict[str, Any]]] = {
    "player": [
        {"key": "monthly",   "name": "Monthly",   "amount":  1_500, "months":  1, "discount": ""},
        {"key": "quarterly", "name": "Quarterly", "amount":  3_800, "months":  3, "discount": "Save ~16%", "popular": True},
        {"key": "annual",    "name": "Annual",    "amount": 12_000, "months": 12, "discount": "Save ~33%"},
    ],
    "club": [
        {"key": "monthly",   "name": "Monthly",   "amount":  10_000, "months":  1, "discount": ""},
        {"key": "quarterly", "name": "Quarterly", "amount":  27_000, "months":  3, "discount": "Save 10%", "popular": True},
        {"key": "annual",    "name": "Annual",    "amount": 100_000, "months": 12, "discount": "Save ~17%"},
    ],
    "agent": [
        {"key": "monthly",   "name": "Monthly",   "amount":  5_000, "months":  1, "discount": ""},
        {"key": "quarterly", "name": "Quarterly", "amount": 13_000, "months":  3, "discount": "Save ~13%", "popular": True},
        {"key": "annual",    "name": "Annual",    "amount": 55_000, "months": 12, "discount": "Save ~8%"},
    ],
    "scout": [
        {"key": "monthly",   "name": "Monthly",   "amount":  20_000, "months":  1, "discount": ""},
        {"key": "quarterly", "name": "Quarterly", "amount":  58_500, "months":  3, "discount": "Save ~2.5%", "popular": True},
        {"key": "annual",    "name": "Annual",    "amount": 230_000, "months": 12, "discount": "Save ~4%"},
    ],
    "dco": [
        {"key": "monthly",   "name": "Monthly",   "amount":  3_000, "months":  1, "discount": ""},
        {"key": "quarterly", "name": "Quarterly", "amount":  8_500, "months":  3, "discount": "Save ~6%", "popular": True},
        {"key": "annual",    "name": "Annual",    "amount": 34_000, "months": 12, "discount": "Save ~6%"},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 9.  DCO / SUPERVISOR RATES  (all canonical level keys + club)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DCO_RATES: Dict[str, Dict[str, int]] = {
    "tier1": {
        "professional":      700,
        "semi_professional": 500,
        "academy":           400,
        "university":        400,
        "local":             400,
        "other":             500,
        "club":            1_400,
    },
    "tier2": {
        "professional":    1_000,
        "semi_professional": 700,
        "academy":           600,
        "university":        600,
        "local":             600,
        "other":             700,
        "club":            2_000,
    },
    "tier3": {
        "professional":    1_400,
        "semi_professional": 1_000,
        "academy":           900,
        "university":        900,
        "local":             900,
        "other":           1_000,
        "club":            2_800,
    },
}

DEFAULT_SUPERVISOR_RATES: Dict[str, Dict[str, int]] = {
    "tier1": {
        "professional":      250,
        "semi_professional": 150,
        "academy":           120,
        "university":        120,
        "local":             120,
        "other":             120,
        "club":              600,
    },
    "tier2": {
        "professional":      400,
        "semi_professional": 250,
        "academy":           200,
        "university":        200,
        "local":             200,
        "other":             200,
        "club":            1_000,
    },
    "tier3": {
        "professional":      600,
        "semi_professional": 400,
        "academy":           300,
        "university":        300,
        "local":             300,
        "other":             300,
        "club":            1_500,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 10.  ADMIN SETTINGS DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_ADMIN_SETTINGS: Dict[str, Any] = {
    "token_packages":       TOKEN_PACKAGES,
    "token_costs": {
        "player_stats": PLAYER_STATS_REQUEST_TOKENS,
        "club_stats":   CLUB_STATS_REQUEST_TOKENS,
        "flat":         FLAT_TOKEN_COSTS,
    },
    "subscription_pricing": DEFAULT_SUBSCRIPTION_PRICES,
    "dco_rates":            DEFAULT_DCO_RATES,
    "supervisor_rates":     DEFAULT_SUPERVISOR_RATES,
    "bank_transfer": {
        "bank_name":      "",
        "account_number": "",
        "account_name":   "",
    },
    "flutterwave": {
        "public_key":   "",
        "secret_key":   "",
        "webhook_hash": "",
    },
    "platform_fee_percent": 0.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# 11.  COUNTRY / REGION PRICING
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_COUNTRY_MULTIPLIERS: Dict[str, float] = {
    # ── West Africa (baseline = Nigeria) ─────────────────────────────────────
    "NG": 1.00,   # Nigeria — baseline
    "GH": 1.10,   # Ghana
    "SN": 1.05,   # Senegal
    "CI": 1.05,   # Côte d'Ivoire
    "BJ": 0.90,   # Benin
    "TG": 0.90,   # Togo
    "ML": 0.85,   # Mali
    "BF": 0.85,   # Burkina Faso
    "GN": 0.85,   # Guinea
    "GW": 0.80,   # Guinea-Bissau
    "SL": 0.80,   # Sierra Leone
    "LR": 0.80,   # Liberia
    "GM": 0.80,   # Gambia
    "MR": 0.80,   # Mauritania
    "NE": 0.80,   # Niger
    "CV": 0.90,   # Cabo Verde
    # ── East Africa ──────────────────────────────────────────────────────────
    "KE": 1.10,   # Kenya
    "TZ": 0.95,   # Tanzania
    "UG": 0.90,   # Uganda
    "RW": 0.90,   # Rwanda
    "ET": 0.80,   # Ethiopia
    "SS": 0.80,   # South Sudan
    "SD": 0.80,   # Sudan
    "DJ": 0.85,   # Djibouti
    "ER": 0.80,   # Eritrea
    "SO": 0.80,   # Somalia
    # ── Central Africa ───────────────────────────────────────────────────────
    "CM": 1.00,   # Cameroon
    "CD": 0.85,   # DR Congo
    "CG": 0.90,   # Congo
    "GA": 1.20,   # Gabon
    "GQ": 1.10,   # Equatorial Guinea
    "CF": 0.75,   # Central African Republic
    "TD": 0.80,   # Chad
    "BI": 0.75,   # Burundi
    # ── Southern Africa ──────────────────────────────────────────────────────
    "ZA": 1.40,   # South Africa
    "BW": 1.20,   # Botswana
    "NA": 1.15,   # Namibia
    "ZM": 0.95,   # Zambia
    "ZW": 0.90,   # Zimbabwe
    "MZ": 0.85,   # Mozambique
    "MW": 0.80,   # Malawi
    "MG": 0.80,   # Madagascar
    "MU": 1.30,   # Mauritius
    "SZ": 0.90,   # Eswatini
    # ── North Africa ─────────────────────────────────────────────────────────
    "EG": 1.00,   # Egypt
    "MA": 1.10,   # Morocco
    "TN": 1.10,   # Tunisia
    "DZ": 1.05,   # Algeria
    "LY": 1.00,   # Libya
    # ── Middle East ──────────────────────────────────────────────────────────
    "SA": 2.50,   # Saudi Arabia
    "AE": 2.50,   # UAE
    "QA": 2.50,   # Qatar
    "KW": 2.30,   # Kuwait
    "BH": 2.20,   # Bahrain
    "JO": 1.50,   # Jordan
    "LB": 1.30,   # Lebanon
    "IQ": 1.10,   # Iraq
    "YE": 0.90,   # Yemen
    # ── Europe ───────────────────────────────────────────────────────────────
    "GB": 3.00,   # United Kingdom
    "DE": 3.00,   # Germany
    "FR": 3.00,   # France
    "IT": 2.80,   # Italy
    "ES": 2.80,   # Spain
    "NL": 3.00,   # Netherlands
    "PT": 2.50,   # Portugal
    "BE": 3.00,   # Belgium
    "CH": 3.50,   # Switzerland
    "AT": 3.00,   # Austria
    "SE": 3.20,   # Sweden
    "NO": 3.50,   # Norway
    "DK": 3.20,   # Denmark
    "FI": 3.00,   # Finland
    "IE": 3.00,   # Ireland
    "GR": 2.30,   # Greece
    "PL": 2.00,   # Poland
    "CZ": 2.00,   # Czechia
    "HU": 1.80,   # Hungary
    "UA": 1.20,   # Ukraine
    "RS": 1.50,   # Serbia
    "HR": 1.80,   # Croatia
    "BA": 1.50,   # Bosnia
    # ── Americas ─────────────────────────────────────────────────────────────
    "US": 3.00,   # United States
    "CA": 2.80,   # Canada
    "BR": 1.80,   # Brazil
    "MX": 1.60,   # Mexico
    "AR": 1.40,   # Argentina
    "CO": 1.30,   # Colombia
    "CL": 1.50,   # Chile
    "VE": 0.90,   # Venezuela
    "UY": 1.50,   # Uruguay
    "JM": 1.30,   # Jamaica
    # ── Asia-Pacific ─────────────────────────────────────────────────────────
    "AU": 2.80,   # Australia
    "NZ": 2.80,   # New Zealand
    "JP": 2.80,   # Japan
    "KR": 2.50,   # South Korea
    "CN": 2.20,   # China
    "IN": 1.20,   # India
    "SG": 2.80,   # Singapore
    "MY": 1.60,   # Malaysia
    "TH": 1.40,   # Thailand
    "ID": 1.20,   # Indonesia
    "PK": 0.90,   # Pakistan
    "BD": 0.85,   # Bangladesh
    "VN": 1.10,   # Vietnam
    # ── Default for unlisted countries ────────────────────────────────────────
    "OTHER": 1.00,
}

#: Named region groups — admin can set one multiplier for an entire group.
REGION_GROUPS: Dict[str, List[str]] = {
    "West Africa":     ["NG", "GH", "SN", "CI", "BJ", "TG", "ML", "BF", "GN", "GW", "SL", "LR", "GM", "MR", "NE", "CV"],
    "East Africa":     ["KE", "TZ", "UG", "RW", "ET", "SS", "SD", "DJ", "ER", "SO"],
    "Central Africa":  ["CM", "CD", "CG", "GA", "GQ", "CF", "TD", "BI"],
    "Southern Africa": ["ZA", "BW", "NA", "ZM", "ZW", "MZ", "MW", "MG", "MU", "SZ"],
    "North Africa":    ["EG", "MA", "TN", "DZ", "LY"],
    "Middle East":     ["SA", "AE", "QA", "KW", "BH", "JO", "LB", "IQ", "YE"],
    "Europe":          ["GB", "DE", "FR", "IT", "ES", "NL", "PT", "BE", "CH", "AT", "SE", "NO", "DK", "FI", "IE", "GR", "PL", "CZ", "HU", "UA", "RS", "HR", "BA"],
    "North America":   ["US", "CA", "MX"],
    "South America":   ["BR", "AR", "CO", "CL", "VE", "UY", "JM"],
    "Asia-Pacific":    ["AU", "NZ", "JP", "KR", "CN", "IN", "SG", "MY", "TH", "ID", "PK", "BD", "VN"],
}

# COUNTRY_CODE_TO_NAME is sourced from location_module (single source of truth)
COUNTRY_CODE_TO_NAME: Dict[str, str] = COUNTRY_NAMES


def get_country_multiplier(
    country_code: str,
    overrides: Optional[Dict[str, float]] = None,
) -> float:
    """
    Return the price multiplier for a given ISO country code.

    Args:
        country_code: ISO-3166-1 alpha-2 code (e.g. ``"NG"``, ``"ZA"``).
        overrides:    Runtime overrides loaded from MongoDB (takes precedence).

    Returns:
        Float multiplier (1.0 = Nigeria baseline).
    """
    code = (country_code or "OTHER").upper().strip()
    if overrides and code in overrides:
        return float(overrides[code])
    return DEFAULT_COUNTRY_MULTIPLIERS.get(code, DEFAULT_COUNTRY_MULTIPLIERS.get("OTHER", 1.0))


def apply_country_multiplier(base_price: int, multiplier: float) -> int:
    """Apply localization multiplier and round to the nearest NGN 50 (legacy policy)."""
    raw = float(base_price) * float(multiplier)
    if not math.isfinite(raw) or raw < 0:
        raise ValueError("Price and multiplier must produce a finite non-negative amount")
    return int(round(raw / 50) * 50)


def calculate_bulk_adjusted_price(base_price: int, multiplier: float) -> int:
    """Adjust an administrator-selected base price without country rounding."""
    raw = float(base_price) * float(multiplier)
    if not math.isfinite(raw) or raw < 0:
        raise ValueError("Price and multiplier must produce a finite non-negative amount")
    return int(round(raw))


def get_country_adjusted_price(
    base_price: int,
    country_code: str,
    overrides: Optional[Dict[str, float]] = None,
) -> int:
    """Apply country multiplier to a base price and return rounded integer."""
    m = get_country_multiplier(country_code, overrides)
    return apply_country_multiplier(base_price, m)


# ─────────────────────────────────────────────────────────────────────────────
# 12.  PRICING SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class PricingService:
    """
    Central pricing service — the ONLY place that resolves prices.

    Lifecycle
    ---------
    A module-level singleton ``pricing_service`` is created at import time
    using Python defaults.  On application startup, reload it from MongoDB:

        doc = await db["admin_settings"].find_one({"key": "platform"})
        pricing_service = PricingService.from_db_settings(doc or {})

    When an admin updates settings, call ``PricingService.from_db_settings``
    again and replace the singleton.
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        s = copy.deepcopy(settings or {})
        self._token_costs: Dict[str, Any] = copy.deepcopy(s.get("token_costs") or DEFAULT_ADMIN_SETTINGS["token_costs"])
        self._subscription_pricing: Dict[str, Any] = (
            copy.deepcopy(s.get("subscription_pricing") or DEFAULT_SUBSCRIPTION_PRICES)
        )
        self._token_packages: Dict[str, Dict[str, List[Dict[str, Any]]]] = (
            copy.deepcopy(s.get("token_packages") or TOKEN_PACKAGES)
        )
        self._dco_rates: Dict[str, Any] = (
            copy.deepcopy(s.get("dco_rates") or DEFAULT_DCO_RATES)
        )
        self._supervisor_rates: Dict[str, Any] = (
            copy.deepcopy(s.get("supervisor_rates") or DEFAULT_SUPERVISOR_RATES)
        )
        self._country_multipliers: Dict[str, float] = (
            copy.deepcopy(s.get("country_multipliers") or {})
        )
        self._subscription_plans: Dict[str, List[Dict[str, Any]]] = (
            DEFAULT_SUBSCRIPTION_PLANS
        )

    # -- Normalisation helpers -------------------------------------------------

    @staticmethod
    def normalize_level(raw: str) -> str:
        return normalize_level(raw)

    @staticmethod
    def normalize_plan_key(raw: str) -> str:
        return normalize_plan_key(raw)

    # -- Subscription ---------------------------------------------------------

    def get_subscription_price(
        self,
        role: str,
        level: Optional[str],
        plan_key: str,
        country_code: Optional[str] = None,
    ) -> int:
        """
        Return the subscription price (₦, integer) for a role, level, plan
        duration, and optional country.
        """
        role     = role.lower().strip()
        plan_key = self.normalize_plan_key(plan_key)

        pricing = self._subscription_pricing.get(role)
        if pricing is None:
            raise ValueError(
                f"No subscription pricing for role '{role}'. "
                f"Valid roles: {list(self._subscription_pricing.keys())}"
            )

        if role in ("player", "club"):
            if not level:
                raise ValueError(
                    f"'level' is required for subscription pricing of role '{role}'."
                )
            lvl = self.normalize_level(level)
            level_pricing = pricing.get(lvl)
            if level_pricing is None:
                raise ValueError(f"No subscription pricing for {role}/{lvl}.")
            base = int(level_pricing[plan_key])
        else:
            base = int(pricing[plan_key])

        if country_code:
            return get_country_adjusted_price(base, country_code, self._country_multipliers)
        return base

    def get_subscription_plans(
        self,
        role: str,
        level: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return the ordered plan list for a role, optionally with country pricing."""
        role = role.lower().strip()
        base_plans = self._subscription_plans.get(role)
        if base_plans is None:
            raise ValueError(f"Unsupported subscription role: {role}")
        pricing = self._subscription_pricing.get(role)
        if role in ("player", "club"):
            if not level:
                raise ValueError(f"level is required for {role} pricing")
            lvl = self.normalize_level(level)
            if not isinstance(pricing, dict) or lvl not in pricing:
                raise ValueError(f"No subscription pricing for {role}/{lvl}")

        plans   = copy.deepcopy(base_plans)
        if role in ("player", "club"):
            if level and pricing:
                try:
                    lvl           = self.normalize_level(level)
                    level_pricing = pricing.get(lvl, {})
                    for plan in plans:
                        key = plan["key"]
                        if key in level_pricing:
                            base = int(level_pricing[key])
                            if country_code:
                                base = get_country_adjusted_price(base, country_code, self._country_multipliers)
                            plan["amount"] = base
                            plan["price"]  = base
                except ValueError as exc:
                    raise ValueError(str(exc)) from exc
        else:
            if pricing and isinstance(pricing, dict):
                for plan in plans:
                    key = plan["key"]
                    if key in pricing:
                        base = int(pricing[key])
                        if country_code:
                            base = get_country_adjusted_price(base, country_code, self._country_multipliers)
                        plan["amount"] = base
                        plan["price"]  = base

        return plans

    # -- Token packages -------------------------------------------------------

    def get_token_packages(
        self,
        role: str,
        level: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return the token package list for a role, optionally with country pricing."""
        role = role.lower().strip()
        role_packages = self._token_packages.get(role)
        if role_packages is None:
            raise ValueError(f"No token packages for role '{role}'.")

        if role in ("player", "club"):
            if not level:
                raise ValueError(f"'level' is required for token packages for role '{role}'.")
            lvl  = self.normalize_level(level)
            tier = role_packages.get(lvl)
            if tier is None:
                raise ValueError(f"No token packages for {role}/{lvl}.")
            pkgs = copy.deepcopy(tier)
        else:
            pkgs = copy.deepcopy(role_packages.get("default", []))

        if country_code:
            mult = get_country_multiplier(country_code, self._country_multipliers)
            pkgs = copy.deepcopy(pkgs)
            for pkg in pkgs:
                pkg["price"] = apply_country_multiplier(pkg["price"], mult)
        return pkgs

    # -- Per-action token costs -----------------------------------------------

    def get_stats_request_cost(self, role: str, level: str) -> float:
        role = role.lower().strip()
        lvl  = self.normalize_level(level)

        if role == "player":
            table: Dict[str, float] = self._token_costs.get("player_stats", {})
        elif role == "club":
            table = self._token_costs.get("club_stats", {})
        else:
            raise ValueError(f"Stats-request cost is only defined for 'player' and 'club', not '{role}'.")

        cost = table.get(lvl)
        if cost is None:
            raise ValueError(f"No stats-request cost defined for {role}/{lvl}.")
        return float(cost)

    def get_token_cost(self, user_type: str, category: str) -> int:
        """Resolve billable cost from persisted config where a configured table exists.

        Integer legacy costs remain the fallback for roles/actions not represented
        in the fractional stats-cost configuration; the debit implementation must
        use the same method to guarantee quote/debit parity.
        """
        role = (user_type or "").strip().lower()
        cat = (category or "other").strip().lower()
        if role in ("player", "club"):
            return int(math.ceil(self.get_stats_request_cost(role, cat)))
        return get_token_cost(role, cat)


    def get_flat_cost(self, action: str) -> float:
        flat = self._token_costs.get("flat", FLAT_TOKEN_COSTS)
        cost = flat.get(action)
        if cost is None:
            raise ValueError(
                f"No flat token cost for action '{action}'. "
                f"Valid actions: {list(FLAT_TOKEN_COSTS.keys())}"
            )
        return float(cost)

    def get_match_request_cost(self) -> float:
        return self.get_flat_cost("match_request")

    def get_heatmap_cost(self) -> float:
        return self.get_flat_cost("heatmap_addon")

    def get_club_match_cost(self) -> float:
        return self.get_flat_cost("club_match")

    # -- DCO / Supervisor rates -----------------------------------------------

    def get_dco_rate(self, tier: str, level: str) -> int:
        tier = tier.lower().strip()
        tier_data = self._dco_rates.get(tier)
        if tier_data is None:
            raise ValueError(f"Unknown DCO tier '{tier}'.")
        key = "club" if level.lower().strip() == "club" else self.normalize_level(level)
        rate = tier_data.get(key)
        if rate is None:
            raise ValueError(f"No DCO rate for {tier}/{key}.")
        return int(rate)

    def get_supervisor_rate(self, tier: str, level: str) -> int:
        tier = tier.lower().strip()
        tier_data = self._supervisor_rates.get(tier)
        if tier_data is None:
            raise ValueError(f"Unknown supervisor tier '{tier}'.")
        key = "club" if level.lower().strip() == "club" else self.normalize_level(level)
        rate = tier_data.get(key)
        if rate is None:
            raise ValueError(f"No supervisor rate for {tier}/{key}.")
        return int(rate)

    # -- Country pricing helpers -----------------------------------------------

    def get_country_multiplier(self, country_code: str) -> float:
        """Return the effective multiplier for a country code."""
        return get_country_multiplier(country_code, self._country_multipliers)

    def get_all_country_multipliers(self) -> Dict[str, float]:
        """
        Return merged dict: defaults overridden by runtime DB overrides.
        Each entry includes the country name for display.
        """
        merged = dict(DEFAULT_COUNTRY_MULTIPLIERS)
        merged.update(self._country_multipliers)
        return merged

    def set_country_multiplier(self, country_code: str, multiplier: float) -> None:
        """Update a canonical ISO alpha-2 country multiplier."""
        code = str(country_code or "").strip().upper()
        if not validate_country_code(code):
            raise ValueError(f"Unsupported country code: {country_code}")
        self._country_multipliers[code] = float(multiplier)

    def set_region_multiplier(self, region_name: str, multiplier: float) -> None:
        """
        Apply a single multiplier to all countries in a named region group.
        Individual country overrides already in ``_country_multipliers`` are
        NOT overwritten — only countries without a specific override are updated.
        """
        codes = REGION_GROUPS.get(region_name, [])
        for code in codes:
            if code not in self._country_multipliers:
                self._country_multipliers[code] = float(multiplier)

    def bulk_apply_region_multiplier(self, region_name: str, multiplier: float) -> Dict[str, float]:
        """
        Force-apply a multiplier to ALL countries in a region (overwriting individual overrides).
        Returns the dict of affected country codes → new multipliers.
        """
        codes = REGION_GROUPS.get(region_name, [])
        result: Dict[str, float] = {}
        for code in codes:
            self._country_multipliers[code] = float(multiplier)
            result[code] = float(multiplier)
        return result

    def preview_bulk_price_change(
        self,
        role: str,
        multiplier: float,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a preview of what all prices for a role/level would become
        if every base price is multiplied by ``multiplier``.

        Does NOT modify any state — purely informational.
        """
        role = role.lower().strip()
        multiplier = float(multiplier)
        if not math.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("multiplier must be finite and greater than zero")
        preview: Dict[str, Any] = {"role": role, "multiplier": multiplier, "changes": {}}

        pricing = self._subscription_pricing.get(role)
        if pricing is None:
            raise ValueError(f"Unsupported pricing role: {role}")

        if role in ("player", "club"):
            if level is None:
                levels = pricing.items()
            else:
                lvl = self.normalize_level(level)
                levels = [(lvl, pricing.get(lvl, {}))]
            for lvl, level_pricing in levels:
                for plan_key, base in level_pricing.items():
                    preview["changes"][f"{lvl}:{plan_key}"] = {
                        "level": lvl, "plan_key": plan_key, "before": base,
                        "after": calculate_bulk_adjusted_price(base, multiplier),
                    }
        else:
            for plan_key, base in pricing.items():
                preview["changes"][plan_key] = {
                    "before": base,
                    "after":  calculate_bulk_adjusted_price(base, multiplier),
                }
        return preview

    def bulk_apply_price_change(
        self,
        role: str,
        multiplier: float,
        level: Optional[str] = None,
        plan_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply a price multiplier to one or all plan durations for a role/level.

        - If ``plan_key`` is supplied, only that duration is updated.
        - If ``level`` is omitted for player/club, all levels are updated.

        Returns a summary of all changes made.
        """
        role = role.lower().strip()
        multiplier = float(multiplier)
        if not math.isfinite(multiplier) or multiplier <= 0:
            raise ValueError("multiplier must be finite and greater than zero")
        summary: Dict[str, Any] = {"role": role, "multiplier": multiplier, "updated": {}}

        pricing = self._subscription_pricing.get(role)
        if pricing is None:
            raise ValueError(f"Unsupported pricing role: {role}")

        if role in ("player", "club"):
            levels_to_update = [self.normalize_level(level)] if level else list(pricing.keys())
            for lvl in levels_to_update:
                level_pricing = pricing.get(lvl, {})
                keys_to_update = [normalize_plan_key(plan_key)] if plan_key else list(level_pricing.keys())
                for pk in keys_to_update:
                    if pk in level_pricing:
                        old = level_pricing[pk]
                        new = calculate_bulk_adjusted_price(old, multiplier)
                        level_pricing[pk] = new
                        summary["updated"].setdefault(lvl, {})[pk] = {"before": old, "after": new}
        else:
            keys_to_update = [normalize_plan_key(plan_key)] if plan_key else list(pricing.keys())
            for pk in keys_to_update:
                if pk in pricing:
                    old = pricing[pk]
                    new = calculate_bulk_adjusted_price(old, multiplier)
                    pricing[pk] = new
                    summary["updated"][pk] = {"before": old, "after": new}

        return summary

    def to_db_dict(self) -> Dict[str, Any]:
        """Return a dict suitable for $set in MongoDB admin_settings."""
        return {
            "subscription_pricing": self._subscription_pricing,
            "token_packages":       self._token_packages,
            "token_costs":          self._token_costs,
            "dco_rates":            self._dco_rates,
            "supervisor_rates":     self._supervisor_rates,
            "country_multipliers":  self._country_multipliers,
        }

    # -- Factory --------------------------------------------------------------

    @classmethod
    def from_db_settings(cls, doc: Dict[str, Any]) -> "PricingService":
        """Instantiate from a MongoDB admin-settings document."""
        return cls(settings=doc)

    # -- Repr -----------------------------------------------------------------

    def __repr__(self) -> str:
        roles = list(self._subscription_pricing.keys())
        return f"<PricingService roles={roles}>"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — import everywhere:
#   from pricing_module import pricing_service
#
# Re-seed it from MongoDB on startup:
#   doc = await db["admin_settings"].find_one({"key": "platform"})
#   pricing_service = PricingService.from_db_settings(doc or {})
# ─────────────────────────────────────────────────────────────────────────────

pricing_service: PricingService = PricingService()


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================
#
# `register_pricing_routes` is the ONLY public entry point this module
# expects you to call from main.py. It attaches public pricing routes to
# your existing app without touching any existing routes, middleware, or auth.
#
# Usage in main.py (after ``app = FastAPI(...)``):
#
#     from pricing_module import register_pricing_routes, pricing_service
#     register_pricing_routes(app)
#
# The separate pricing route file (if present) continues to use the
# _setup_dependencies() + app.include_router() pattern for its authenticated
# routes and does NOT need to be changed — these two mechanisms are
# independent and complementary.


def register_pricing_routes(app: FastAPI) -> None:
    """
    Register public (unauthenticated) pricing API routes on an existing
    FastAPI application.

    Does not create a new FastAPI() instance, does not conflict with any
    existing routes, and does not touch middleware or auth.
    """

    @app.get(
        "/api/public/pricing/plans",
        tags=["Pricing"],
        summary="Get subscription plans for a role",
    )
    async def get_public_subscription_plans(
        role: str = Query(..., description="User role: player, club, scout, agent, dco"),
        level: Optional[str] = Query(None, description="Player/club level (required for player and club roles)"),
        country: Optional[str] = Query(None, description="ISO-3166-1 alpha-2 country code for localised pricing"),
    ) -> JSONResponse:
        """
        Returns the ordered subscription plan list for a role, with amounts
        adjusted for the optional country multiplier.

        Always returns HTTP 200. Returns an empty ``plans`` list for unknown roles.
        """
        try:
            plans = pricing_service.get_subscription_plans(
                role=role,
                level=level,
                country_code=country,
            )
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "message": str(exc)},
            )
        return JSONResponse(
            content={
                "role":    role.lower().strip(),
                "level":   level,
                "country": country,
                "plans":   plans,
            },
            status_code=200,
        )

    @app.get(
        "/api/public/pricing/packages",
        tags=["Pricing"],
        summary="Get token packages for a role",
    )
    async def get_public_token_packages(
        role: str = Query(..., description="User role: player, club, scout, agent, dco"),
        level: Optional[str] = Query(None, description="Player/club level (required for player and club roles)"),
        country: Optional[str] = Query(None, description="ISO-3166-1 alpha-2 country code for localised pricing"),
    ) -> JSONResponse:
        """
        Returns the token package list for a role, with prices adjusted for
        the optional country multiplier.

        Returns HTTP 400 if required parameters are missing or invalid.
        """
        try:
            packages = pricing_service.get_token_packages(
                role=role,
                level=level,
                country_code=country,
            )
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "message": str(exc)},
            )
        return JSONResponse(
            content={
                "role":     role.lower().strip(),
                "level":    level,
                "country":  country,
                "packages": packages,
            },
            status_code=200,
        )

    @app.get(
        "/api/public/pricing/token-cost",
        tags=["Pricing"],
        summary="Get token cost for a user type and level",
    )
    async def get_public_token_cost(
        user_type: str = Query(..., description="User type: player, club, scout, agent, dco"),
        category: str = Query("other", description="Player/club level or 'other' for flat-rate roles"),
    ) -> JSONResponse:
        """
        Returns the integer token cost for a given user type and level/category.

        For flat-rate roles (scout, dco, agent) the category is ignored.
        """
        try:
            cost = pricing_service.get_token_cost(user_type=user_type, category=category)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "message": str(exc)},
            )
        return JSONResponse(
            content={
                "user_type": user_type.lower().strip(),
                "category":  category,
                "cost":      cost,
            },
            status_code=200,
        )

    @app.get(
        "/api/public/pricing/config",
        tags=["Pricing"],
        summary="Get full public pricing configuration",
    )
    async def get_public_pricing_config(
        country: Optional[str] = Query(None, description="ISO-3166-1 alpha-2 country code"),
    ) -> JSONResponse:
        """
        Returns the complete public-facing pricing configuration: all
        subscription plans for all roles, all token packages, and the
        resolved country multiplier.

        Suitable for a pricing page that must display all tiers at once.
        """
        multiplier = pricing_service.get_country_multiplier(country or "NG")

        all_plans: Dict[str, Any] = {}
        for role in DEFAULT_SUBSCRIPTION_PLANS:
            if role in ("player", "club"):
                all_plans[role] = {}
                for lvl in CANONICAL_LEVELS:
                    all_plans[role][lvl] = pricing_service.get_subscription_plans(
                        role=role, level=lvl, country_code=country
                    )
            else:
                all_plans[role] = pricing_service.get_subscription_plans(
                    role=role, country_code=country
                )

        all_packages: Dict[str, Any] = {}
        for role in TOKEN_PACKAGES:
            if role in ("player", "club"):
                all_packages[role] = {}
                for lvl in CANONICAL_LEVELS:
                    all_packages[role][lvl] = pricing_service.get_token_packages(
                        role=role, level=lvl, country_code=country
                    )
            else:
                all_packages[role] = pricing_service.get_token_packages(
                    role=role, country_code=country
                )

        return JSONResponse(
            content={
                "country":             country,
                "country_multiplier":  multiplier,
                "subscription_plans":  all_plans,
                "token_packages":      all_packages,
                "levels":              PLAYER_LEVELS_CONFIG,
                "plan_keys":           CANONICAL_PLAN_KEYS,
            },
            status_code=200,
        )


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    # Data constants
    "CANONICAL_LEVELS",
    "CANONICAL_PLAN_KEYS",
    "PLAN_MONTHS",
    "LEVEL_ALIAS_MAP",
    "LEGACY_PLAN_ALIAS_MAP",
    "PLAYER_LEVELS_CONFIG",
    "POSITIONS_CONFIG",
    "COUNTRY_CODE_TO_NAME",
    "BANK_TRANSFER_DETAILS",
    # Token cost tables
    "PLAYER_STATS_REQUEST_TOKENS",
    "CLUB_STATS_REQUEST_TOKENS",
    "FLAT_TOKEN_COSTS",
    "PLAYER_TOKEN_COSTS",
    "CLUB_TOKEN_COSTS",
    "SCOUT_TOKEN_COSTS",
    "DCO_TOKEN_COSTS",
    "AGENT_TOKEN_COSTS",
    "TOKEN_PACKAGES",
    # Subscription data
    "DEFAULT_SUBSCRIPTION_PRICES",
    "DEFAULT_SUBSCRIPTION_PLANS",
    # DCO / supervisor rates
    "DEFAULT_DCO_RATES",
    "DEFAULT_SUPERVISOR_RATES",
    # Admin settings
    "DEFAULT_ADMIN_SETTINGS",
    # Country pricing
    "DEFAULT_COUNTRY_MULTIPLIERS",
    "REGION_GROUPS",
    # Pure functions
    "normalize_level",
    "normalize_plan_key",
    "get_token_cost",
    "get_country_multiplier",
    "apply_country_multiplier",
    "get_country_adjusted_price",
    # Service class + singleton
    "PricingService",
    "pricing_service",
    # Route registration (mirrors location_module pattern)
    "register_pricing_routes",
]