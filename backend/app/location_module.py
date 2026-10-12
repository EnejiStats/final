from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, Path
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Canonical data source
# ---------------------------------------------------------------------------
# All geographic constants live in the pure-data module.  This module owns
# the API/lookup/filter behavior and never imports another route module.
import world_locations_complete as _world_locations

# Re-export the data symbols for backwards compatibility with existing
# EnejiStats modules that historically imported locations from location_module.
for _name, _value in vars(_world_locations).items():
    if not _name.startswith("__"):
        globals().setdefault(_name, _value)


@dataclass(frozen=True)
class SubregionLookupResult:
    found: bool
    payload: Optional[Dict[str, Any]] = None


DEFAULT_LOCATION_CONFIG = CountryLocationConfig(
    region_label="Region",
    subregion_label="District",
    regions=[],
    subregions={},
)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = value.replace("-", " ").replace("_", " ")
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value


def _build_region_index() -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    for country_code, config in LOCATION_CONFIG.items():
        index[country_code] = {
            _normalize(region): region for region in config.regions
        }
    return index


_REGION_LOOKUP_INDEX = _build_region_index()


def get_location_config(country_code: str) -> CountryLocationConfig:
    code = str(country_code or "").strip().upper()
    return LOCATION_CONFIG.get(code, DEFAULT_LOCATION_CONFIG)


def resolve_region(country_code: str, region: str) -> Optional[str]:
    code = str(country_code or "").strip().upper()
    return _REGION_LOOKUP_INDEX.get(code, {}).get(_normalize(region))


def get_regions_payload(country_code: str) -> Dict[str, Any]:
    code = str(country_code or "").strip().upper()
    config = LOCATION_CONFIG.get(code)

    if config is None:
        return {
            "country": code,
            "region_label": DEFAULT_LOCATION_CONFIG.region_label,
            "regions": [],
        }

    return {
        "country": code,
        "region_label": config.region_label,
        "regions": list(config.regions),
    }


def get_subregions_payload(
    country_code: str,
    region: str,
) -> SubregionLookupResult:
    code = str(country_code or "").strip().upper()
    config = LOCATION_CONFIG.get(code)

    if config is None:
        return SubregionLookupResult(found=False)

    canonical_region = resolve_region(code, region)
    if canonical_region is None:
        return SubregionLookupResult(found=False)

    return SubregionLookupResult(
        found=True,
        payload={
            "country": code,
            "region": canonical_region,
            "subregion_label": config.subregion_label,
            "subregions": list(config.subregions.get(canonical_region, [])),
        },
    )


def get_country_name(country_code: str) -> Optional[str]:
    if not country_code:
        return None
    return COUNTRY_NAMES.get(str(country_code).strip().upper())


def get_all_supported_country_codes() -> List[str]:
    return sorted(LOCATION_CONFIG.keys())


def get_nigerian_states() -> List[str]:
    return list(NIGERIAN_STATES)


def get_nigerian_lgas(state: str) -> List[str]:
    if not state:
        return []
    canonical = resolve_region("NG", state)
    return list(NIGERIAN_LGAS.get(canonical, [])) if canonical else []


def validate_country_code(country_code: str) -> bool:
    return bool(country_code) and str(country_code).strip().upper() in LOCATION_CONFIG


def validate_region(country_code: str, region: str) -> bool:
    return bool(country_code and region) and resolve_region(country_code, region) is not None


def validate_subregion(country_code: str, region: str, subregion: str) -> bool:
    if not (country_code and region and subregion):
        return False

    result = get_subregions_payload(country_code, region)
    if not result.found or not result.payload:
        return False

    wanted = _normalize(subregion)
    return wanted in {
        _normalize(item) for item in result.payload.get("subregions", [])
    }


def _regex_clause(field: str, value: Optional[str]) -> Optional[Dict[str, Any]]:
    value = str(value or "").strip()
    if not value:
        return None
    return {
        field: {
            "$regex": re.escape(value),
            "$options": "i",
        }
    }

def _country_clause(value: Optional[str]) -> Optional[Dict[str, Any]]:
    """Match a canonical country name or ISO alpha-2 code."""
    value = str(value or "").strip()
    if not value:
        return None
    code = value.upper()
    name = COUNTRY_NAMES.get(code)
    if name:
        return {"$or": [
            {"country": {"$regex": re.escape(name), "$options": "i"}},
            {"country_code": code},
        ]}
    return _regex_clause("country", value)


def build_player_location_filter(
    country: Optional[str] = None,
    state: Optional[str] = None,
    lga: Optional[str] = None,
    city: Optional[str] = None,
    nationality: Optional[str] = None,
) -> List[Dict[str, Any]]:
    clauses: List[Dict[str, Any]] = []
    country_clause = _country_clause(country)
    if country_clause:
        clauses.append(country_clause)
    for field, value in (
        ("state", state),
        ("lga", lga),
        ("city", city),
        ("nationality", nationality),
    ):
        clause = _regex_clause(field, value)
        if clause:
            clauses.append(clause)
    return clauses


def build_club_location_filter(
    country: Optional[str] = None,
    state: Optional[str] = None,
    lga: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    clauses: List[Dict[str, Any]] = []
    country_clause = _country_clause(country)
    if country_clause:
        clauses.append(country_clause)
    for field, value in (
        ("state", state),
        ("lga", lga),
        ("city", city),
    ):
        clause = _regex_clause(field, value)
        if clause:
            clauses.append(clause)
    return clauses


def build_venue_location_filter(
    country: Optional[str] = None,
    state: Optional[str] = None,
    lga: Optional[str] = None,
    city: Optional[str] = None,
) -> Dict[str, Any]:
    clauses = build_club_location_filter(
        country=country,
        state=state,
        lga=lga,
        city=city,
    )
    return {"$and": clauses} if clauses else {}


def build_stadium_location_clauses(
    country: Optional[str] = None,
    state: Optional[str] = None,
    lga: Optional[str] = None,
    city: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return build_club_location_filter(
        country=country,
        state=state,
        lga=lga,
        city=city,
    )


def _route_exists(app: FastAPI, path: str, method: str) -> bool:
    method = method.upper()
    for route in getattr(app, "routes", []):
        if getattr(route, "path", None) == path and method in {
            m.upper() for m in getattr(route, "methods", set())
        }:
            return True
    return False


def register_location_routes(app: FastAPI) -> None:
    """Register the canonical country -> region -> subregion API exactly once."""

    regions_path = "/api/public/countries/{country_code}/regions"
    subregions_path = "/api/public/countries/{country_code}/regions/{region}/subregions"
    countries_path = "/api/public/countries"

    if not _route_exists(app, regions_path, "GET"):
        @app.get(regions_path, tags=["Locations"])
        async def get_country_regions(
            country_code: str = Path(..., min_length=2, max_length=8),
        ) -> JSONResponse:
            code = country_code.strip().upper()
            if code not in LOCATION_CONFIG:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "country_not_found",
                        "message": f"Country code '{code}' is not supported.",
                        "country": code,
                    },
                )
            return JSONResponse(
                content=get_regions_payload(code),
                status_code=200,
            )

    if not _route_exists(app, subregions_path, "GET"):
        @app.get(subregions_path, tags=["Locations"])
        async def get_region_subregions(
            country_code: str = Path(..., min_length=2, max_length=8),
            region: str = Path(..., min_length=1),
        ) -> JSONResponse:
            code = country_code.strip().upper()
            if code not in LOCATION_CONFIG:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "country_not_found",
                        "message": f"Country code '{code}' is not supported.",
                        "country": code,
                    },
                )

            result = get_subregions_payload(code, region)
            if not result.found:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": "region_not_found",
                        "message": f"Region '{region}' was not found for country '{code}'.",
                        "country": code,
                        "region": region,
                    },
                )

            return JSONResponse(
                content=result.payload,
                status_code=200,
            )

    if not _route_exists(app, countries_path, "GET"):
        @app.get(countries_path, tags=["Locations"])
        async def get_all_countries() -> JSONResponse:
            payload = [
                {
                    "code": code,
                    "name": COUNTRY_NAMES.get(code, code),
                    "region_label": config.region_label,
                    "subregion_label": config.subregion_label,
                }
                for code, config in sorted(LOCATION_CONFIG.items())
            ]
            return JSONResponse(
                content={
                    "countries": payload,
                    "count": len(payload),
                },
                status_code=200,
            )


__all__ = [
    "CountryLocationConfig",
    "SubregionLookupResult",
    "DEFAULT_LOCATION_CONFIG",
    "LOCATION_CONFIG",
    "COUNTRY_NAMES",
    "AFRICA_LOCATION_SEED",
    "CONTINENT_CODES",
    "AFRICA_SUB_REGIONS",
    "get_location_config",
    "resolve_region",
    "get_regions_payload",
    "get_subregions_payload",
    "get_country_name",
    "get_all_supported_country_codes",
    "get_nigerian_states",
    "get_nigerian_lgas",
    "validate_country_code",
    "validate_region",
    "validate_subregion",
    "build_player_location_filter",
    "build_club_location_filter",
    "build_venue_location_filter",
    "build_stadium_location_clauses",
    "register_location_routes",
]
