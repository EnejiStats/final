"""
EnejiStats public SEO routes
============================

Drop-in FastAPI router for public player discovery.

This module deliberately lives outside the authenticated player dashboard
router.  Player dashboards are private application screens; player profile
pages, robots.txt, and sitemaps must be public and crawlable.

Integration in main.py:

    import seo_routes as _seo

    _seo.setup_dependencies(
        globals(),
        profile_page_path=_TEMPLATES_DIR / "player-profile.html",
    )
    # The existing main.py route owns /player-profile.html.  Update that
    # handler to call _seo.legacy_player_profile(request) when id is present.
    app.include_router(_seo.router)

The router expects a Motor/Mongo players collection to be available under
the name ``players_collection`` in main.py globals().  It supports the
existing EnejiStats identifiers: user_id, player_id, and Mongo _id.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)


router = APIRouter(tags=["public-seo"])

players_collection = None
player_stats_collection = None
match_stats_collection = None
match_data_collection = None
logger = None
MongoSerializer = None
profile_page_path: Optional[Path] = None

PUBLIC_SITE_URL = os.getenv(
    "PUBLIC_SITE_URL",
    "https://enejistats.onrender.com",
).rstrip("/")


def setup_dependencies(
    main_globals: dict[str, Any],
    *,
    profile_page_path: str | Path,
    public_site_url: Optional[str] = None,
) -> None:
    """Inject the existing application dependencies into this standalone router."""

    global players_collection
    global player_stats_collection, match_stats_collection, match_data_collection
    global logger, MongoSerializer
    globals()["profile_page_path"] = Path(profile_page_path)

    players_collection = main_globals.get("players_collection")
    player_stats_collection = main_globals.get("player_stats_collection")
    match_stats_collection = main_globals.get("match_stats_collection")
    match_data_collection = main_globals.get("match_data_collection")
    logger = main_globals.get("logger")
    MongoSerializer = main_globals.get("MongoSerializer")

    if players_collection is None:
        raise RuntimeError(
            "players_collection must be injected into seo_routes before startup"
        )

    if public_site_url:
        globals()["PUBLIC_SITE_URL"] = public_site_url.rstrip("/")


def _slugify(value: Any) -> str:
    """Create a stable, readable URL segment from a player name."""

    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")
    return slug or "player"


def _value(doc: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = doc.get(key)
        if value not in (None, ""):
            return value
    return default


def _player_name(doc: dict[str, Any]) -> str:
    explicit_name = _value(doc, "name", "full_name", "fullName")
    if explicit_name:
        return str(explicit_name).strip()

    parts = [
        _value(doc, "first_name", "firstName"),
        _value(doc, "middle_name", "middleName"),
        _value(doc, "last_name", "lastName"),
    ]
    return " ".join(str(part).strip() for part in parts if str(part).strip()) or "Football Player"


def _string_list(value: Any) -> list[str]:
    """Normalize a scalar or list-like name field into clean display strings."""

    if value in (None, ""):
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _name_forms(doc: dict[str, Any]) -> list[str]:
    """Return useful, human-readable search forms for a player's name.

    These forms are rendered as real page text and Schema.org alternateName
    values. They are not hidden keyword stuffing: each form is a legitimate
    representation from the record or a natural first/last-name ordering.
    """

    full_name = _player_name(doc)
    first = str(_value(doc, "first_name", "firstName")).strip()
    middle = str(_value(doc, "middle_name", "middleName")).strip()
    last = str(_value(doc, "last_name", "lastName")).strip()
    forms: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if text and text.lower() != "football player" and text not in forms:
            forms.append(text)

    add(full_name)
    add(" ".join(part for part in (first, middle, last) if part))
    add(" ".join(part for part in (first, last) if part))
    add(" ".join(part for part in (last, first) if part))
    add(" ".join(part for part in (last, middle, first) if part))

    for key in (
        "alias",
        "aliases",
        "alternate_name",
        "alternate_names",
        "alternateName",
        "known_as",
        "knownAs",
        "nickname",
        "nicknames",
        "search_names",
        "searchNames",
        "display_name",
        "displayName",
    ):
        for value in _string_list(doc.get(key)):
            add(value)

    return forms


def _player_id(doc: dict[str, Any]) -> str:
    return str(_value(doc, "player_id", "user_id", default=doc.get("_id", "")))


def _profile_path(doc: dict[str, Any]) -> str:
    player_id = _player_id(doc)
    return f"/players/{quote(player_id, safe='')}/{quote(_slugify(_player_name(doc)), safe='')}"


def _is_public(doc: dict[str, Any]) -> bool:
    """Only publish profiles that have not explicitly opted out or been removed."""

    if doc.get("profile_visible") is False:
        return False
    if doc.get("is_public") is False or doc.get("public") is False:
        return False
    if doc.get("deleted") is True or doc.get("deactivated") is True:
        return False
    if str(doc.get("status", "")).lower() in {"deleted", "removed", "deactivated", "private"}:
        return False
    return True


def _number(value: Any) -> int | float:
    if isinstance(value, dict):
        value = value.get("value", value.get("total", 0))
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return 0
    return int(parsed) if parsed.is_integer() else parsed


def _json_safe(value: Any) -> Any:
    """Delegate BSON/time conversion to main.py, preserving date-only values."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    return MongoSerializer.serialize_value(value)

def _public_player(doc: dict[str, Any]) -> dict[str, Any]:
    """Return an allow-listed public projection; never expose the raw document."""

    name = _player_name(doc)
    season = _value(doc, "season", "current_season", default={})
    career = _value(doc, "career", "career_stats", default={})
    season = season if isinstance(season, dict) else {}
    career = career if isinstance(career, dict) else {}
    player_id = _player_id(doc)
    name_forms = _name_forms(doc)

    payload: dict[str, Any] = {
        "id": player_id,
        "player_id": player_id,
        "name": name,
        "alternate_names": [form for form in name_forms if form != name],
        "first_name": _value(doc, "first_name", "firstName"),
        "last_name": _value(doc, "last_name", "lastName"),
        "position": _value(doc, "position", "preferred_position", "preferredPosition"),
        "preferred_position": _value(doc, "preferred_position", "preferredPosition", "position"),
        "club": _value(doc, "current_club", "club", "club_name", "clubName", default="Free Agent"),
        "current_club": _value(doc, "current_club", "club", "club_name", "clubName", default="Free Agent"),
        "nationality": _value(doc, "nationality", "country", default="Nigerian"),
        "state": _value(doc, "state", "home_state"),
        "home_state": _value(doc, "home_state", "state"),
        "height": _value(doc, "height", "height_cm", "heightCm"),
        "weight": _value(doc, "weight", "weight_kg", "weightKg"),
        "preferred_foot": _value(doc, "preferred_foot", "preferredFoot"),
        "jersey_number": _value(doc, "jersey_number", "jerseyNumber"),
        "playing_category": _value(doc, "playing_category", "playingCategory", "player_category", "playerCategory", "category"),
        "player_category": _value(doc, "player_category", "playerCategory", "playing_category", "playingCategory", "category"),
        "player_level": _value(doc, "player_level", "playerLevel", "playing_level", "playingLevel", "level"),
        "playing_level": _value(doc, "playing_level", "playingLevel", "player_level", "playerLevel", "level"),
        "secondary_positions": _string_list(_value(doc, "secondary_positions", "secondaryPositions")),
        "verified": bool(_value(doc, "verified", "is_verified", "isVerified", default=False)),
        "rating": _number(_value(doc, "rating", "performance_rating", default=0)),
        "bio": _value(doc, "bio", "description"),
        "achievements": _json_safe(_value(doc, "achievements", "awards", "badges", default=[])),
        "season": _json_safe(season),
        "career": _json_safe(career),
        "url": f"{PUBLIC_SITE_URL}{_profile_path(doc)}",
    }

    # Keep only non-sensitive, explicitly public fields in the embed payload.
    # DOB is included only when the player has opted into DOB visibility.
    if doc.get("dob_visible") is True:
        payload["dob"] = _json_safe(
            _value(doc, "dob", "date_of_birth", "dateOfBirth")
        )

    return payload


async def _resolve_player(uid: str) -> Optional[dict[str, Any]]:
    if players_collection is None:
        raise RuntimeError("seo_routes.setup_dependencies() has not been called")

    doc = await players_collection.find_one(
        {"$or": [{"user_id": uid}, {"player_id": uid}, {"unique_id": uid}]}
    )
    if not doc and len(uid) == 24:
        try:
            doc = await players_collection.find_one({"_id": ObjectId(uid)})
        except Exception:
            doc = None
    return doc


def _date_value(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value:
        match = re.match(r"^\d{4}-\d{2}-\d{2}", str(value))
        return match.group(0) if match else None
    return None


def _meta_description(player: dict[str, Any]) -> str:
    name = player["name"]
    alternate_names = player.get("alternate_names") or []
    position = player.get("position") or "football player"
    club = player.get("club") or "Nigeria"
    rating = player.get("rating")
    rating_text = f" Rated {rating}/10." if rating else ""
    name_text = (
        f" Also listed as {', '.join(str(item) for item in alternate_names[:2])}."
        if alternate_names
        else ""
    )
    description = (
        f"{name} is a {position} at {club}. View verified football statistics, "
        f"match history and performance data on EnejiStats.{name_text}{rating_text}"
    )
    return description[:160].rstrip()


def _json_for_script(value: Any) -> str:
    """Serialize JSON safely inside a script tag."""

    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _structured_data(player: dict[str, Any]) -> dict[str, Any]:
    person: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": player["name"],
        "url": player["url"],
        "description": _meta_description(player),
        "jobTitle": player.get("position") or "Football player",
        "nationality": player.get("nationality") or "Nigerian",
    }
    if player.get("alternate_names"):
        person["alternateName"] = player["alternate_names"]
    if player.get("photo_url"):
        person["image"] = player["photo_url"]
    if player.get("club") and player["club"] != "Free Agent":
        person["memberOf"] = {
            "@type": "SportsTeam",
            "name": player["club"],
        }
    if player.get("dob"):
        person["birthDate"] = player["dob"]
    return person


def _server_profile_markup(player: dict[str, Any]) -> str:
    """Visible HTML fallback; this is present in the first response before Preact runs."""

    name = html.escape(str(player["name"]))
    position = html.escape(str(player.get("position") or "Football player"))
    club = html.escape(str(player.get("club") or "Free Agent"))
    nationality = html.escape(str(player.get("nationality") or "Nigerian"))
    bio = html.escape(str(player.get("bio") or _meta_description(player)))
    alternate_names = [
        html.escape(str(item))
        for item in (player.get("alternate_names") or [])
        if str(item).strip()
    ]
    photo = str(player.get("photo_url") or "")
    photo_markup = (
        f'<img src="{html.escape(photo, quote=True)}" alt="{name}" width="128" height="128">'
        if photo
        else f'<div aria-hidden="true">{html.escape(name[:1].upper())}</div>'
    )
    season = player.get("season") if isinstance(player.get("season"), dict) else {}
    stats = [
        ("Goals", _number(season.get("goals", player.get("career", {}).get("goals", 0)))),
        ("Assists", _number(season.get("assists", player.get("career", {}).get("assists", 0)))),
        ("Matches", _number(season.get("matches", player.get("career", {}).get("matches", 0)))),
    ]
    stats_markup = "".join(
        f"<li><strong>{html.escape(str(value))}</strong> {label}</li>"
        for label, value in stats
    )
    name_search_markup = (
        "<p class=\"seo-player-name-forms\"><strong>Name:</strong> "
        f"{name}"
        + (
            " · <strong>Also listed as:</strong> "
            + ", ".join(alternate_names)
            if alternate_names
            else ""
        )
        + "</p>"
    )
    return f"""
<main id="seo-player-profile" class="seo-player-profile" data-seo-fallback="true">
  <article itemscope itemtype="https://schema.org/Person">
    <div class="seo-player-photo" itemprop="image">{photo_markup}</div>
    <p class="seo-kicker">EnejiStats player profile</p>
    <h1 itemprop="name">{name}</h1>
    {name_search_markup}
    <p><span itemprop="jobTitle">{position}</span> ·
       <span itemprop="memberOf">{club}</span> ·
       <span itemprop="nationality">{nationality}</span></p>
    <p itemprop="description">{bio}</p>
    <ul aria-label="Player statistics">{stats_markup}</ul>
    <p><a href="/browse.html">Browse all EnejiStats players</a></p>
  </article>
</main>
""".strip()


def _profile_document(template: str, player: dict[str, Any]) -> str:
    title = f"{player['name']} | {player.get('position') or 'Football Player'} | EnejiStats"
    description = _meta_description(player)
    canonical = player["url"]
    image = player.get("photo_url") or f"{PUBLIC_SITE_URL}/static/images/eneji-stats-branding.png"
    json_player = _json_for_script(player)
    json_ld = _json_for_script(_structured_data(player))

    head_insert = f"""
  <meta name="robots" content="index,follow,max-image-preview:large"/>
  <link rel="canonical" href="{html.escape(canonical, quote=True)}"/>
  <meta property="og:type" content="profile"/>
  <meta property="og:site_name" content="EnejiStats"/>
  <meta property="og:title" content="{html.escape(title, quote=True)}"/>
  <meta property="og:description" content="{html.escape(description, quote=True)}"/>
  <meta property="og:url" content="{html.escape(canonical, quote=True)}"/>
  <meta property="og:image" content="{html.escape(str(image), quote=True)}"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{html.escape(title, quote=True)}"/>
  <meta name="twitter:description" content="{html.escape(description, quote=True)}"/>
  <script type="application/ld+json">{json_ld}</script>
"""
    document = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)}</title>", template, count=1, flags=re.I | re.S)
    document = re.sub(
        r'<meta\s+name=["\']description["\'][^>]*>',
        f'<meta name="description" content="{html.escape(description, quote=True)}"/>',
        document,
        count=1,
        flags=re.I,
    )
    document = document.replace("</head>", f"{head_insert}</head>", 1)
    fallback = _server_profile_markup(player)
    document = document.replace(
        '<div id="app"></div>',
        f'<div id="app">{fallback}</div><script>window.__PLAYER__={json_player};</script>',
        1,
    )
    return document


def _player_match_filter(uid: str) -> dict[str, Any]:
    return {
        "$or": [
            {"player_id": uid},
            {"user_id": uid},
            {"unique_id": uid},
        ]
    }


def _match_collections() -> list[Any]:
    """Return configured match collections without introducing new main.py dependencies."""

    return [
        collection
        for collection in (
            match_stats_collection,
            player_stats_collection,
            match_data_collection,
        )
        if collection is not None
    ]


def _public_match(doc: dict[str, Any]) -> dict[str, Any]:
    """Allow-list the match fields consumed by the public Preact profile."""

    score = _value(doc, "score", default="")
    if isinstance(score, dict):
        score = _json_safe(score)
    return {
        "id": str(_value(doc, "id", "match_id", "submission_id", default=doc.get("_id", ""))),
        "date": _json_safe(_value(doc, "date", "match_date", "played_at", "created_at")),
        "match_date": _json_safe(_value(doc, "match_date", "date", "played_at")),
        "opponent": _value(doc, "opponent", "opponent_club", "opponent_club_name"),
        "opponent_club": _value(doc, "opponent_club", "opponent", "opponent_club_name"),
        "competition": _value(doc, "competition", "competition_name", "league"),
        "result": _value(doc, "result", "outcome"),
        "score": score,
        "goals": _number(_value(doc, "goals", "player_goals", default=0)),
        "assists": _number(_value(doc, "assists", "player_assists", default=0)),
        "rating": _number(_value(doc, "rating", "performance_rating", default=0)),
        "minutes": _number(_value(doc, "minutes", "minutes_played", default=0)),
    }


async def _find_public_matches(uid: str, page: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    """Read public match rows from the first configured match collection with data."""

    query = _player_match_filter(uid)
    skip = (page - 1) * limit

    for collection in _match_collections():
        try:
            total = await collection.count_documents(query)
            if not total:
                continue
            cursor = (
                collection.find(query)
                .sort([("match_date", -1), ("date", -1), ("created_at", -1)])
                .skip(skip)
                .limit(limit)
            )
            docs = await cursor.to_list(length=limit)
            return [_public_match(doc) for doc in docs], total
        except Exception:
            if logger:
                logger.exception("SEO public match lookup failed")

    return [], 0


@router.get("/api/seo/public/players/{uid}")
async def public_player_api(uid: str) -> JSONResponse:
    """Public, allow-listed player data used by the existing profile page."""

    doc = await _resolve_player(uid)
    if not doc or not _is_public(doc):
        raise HTTPException(status_code=404, detail="Player profile not found")
    return JSONResponse(_public_player(doc))


@router.get("/api/seo/public/players/{uid}/matches")
async def public_player_matches_api(
    uid: str,
    page: int = 1,
    limit: int = 6,
) -> JSONResponse:
    """Public paginated match history used by the existing profile page."""

    doc = await _resolve_player(uid)
    if not doc or not _is_public(doc):
        raise HTTPException(status_code=404, detail="Player profile not found")

    page = max(1, int(page))
    limit = min(max(1, int(limit)), 50)
    rows, total = await _find_public_matches(uid, page, limit)
    pages = max(1, math.ceil(total / limit)) if total else 1
    return JSONResponse(
        {
            "data": rows,
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
        }
    )


@router.get("/players/{uid}/{slug}", response_class=HTMLResponse)
async def public_player_profile(uid: str, slug: str) -> Response:
    """Serve a unique, indexable URL for a visible player profile."""

    doc = await _resolve_player(uid)
    if not doc or not _is_public(doc):
        raise HTTPException(status_code=404, detail="Player profile not found")

    expected_slug = _slugify(_player_name(doc))
    if slug != expected_slug:
        canonical_path = _profile_path(doc)
        return RedirectResponse(
            url=f"{PUBLIC_SITE_URL}{canonical_path}",
            status_code=308,
        )

    if profile_page_path is None or not profile_page_path.is_file():
        raise HTTPException(
            status_code=500,
            detail="The player profile HTML template is not configured",
        )

    player = _public_player(doc)
    template = profile_page_path.read_text(encoding="utf-8")
    document = _profile_document(template, player)
    return HTMLResponse(
        document,
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=600"},
    )


@router.get("/seo/player-profile.html")
async def legacy_player_profile(request: Request) -> RedirectResponse:
    """Move existing query-string links to the stable player URL."""

    uid = request.query_params.get("id", "").strip()
    if not uid:
        return RedirectResponse(url="/browse.html", status_code=302)
    doc = await _resolve_player(uid)
    if not doc or not _is_public(doc):
        raise HTTPException(status_code=404, detail="Player profile not found")
    return RedirectResponse(
        url=f"{PUBLIC_SITE_URL}{_profile_path(doc)}",
        status_code=308,
    )


def _sitemap_entry(url: str, lastmod: Optional[str] = None) -> str:
    lastmod_xml = f"<lastmod>{html.escape(lastmod)}</lastmod>" if lastmod else ""
    return f"<url><loc>{html.escape(url)}</loc>{lastmod_xml}</url>"


@router.get("/sitemap.xml")
async def sitemap() -> Response:
    """Publish the home, browse, and every visible player profile URL."""

    if players_collection is None:
        raise HTTPException(status_code=500, detail="Player collection is not configured")

    docs = await players_collection.find({}).to_list(length=50000)
    entries = [
        _sitemap_entry(f"{PUBLIC_SITE_URL}/"),
        _sitemap_entry(f"{PUBLIC_SITE_URL}/browse.html"),
    ]
    for doc in docs:
        if not _is_public(doc):
            continue
        player = _public_player(doc)
        lastmod = _date_value(
            _value(doc, "updated_at", "updatedAt", "modified_at", "created_at", "createdAt")
        )
        entries.append(_sitemap_entry(player["url"], lastmod))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(entries)
        + "</urlset>"
    )
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=300, stale-while-revalidate=600"},
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots() -> PlainTextResponse:
    return PlainTextResponse(
        "\n".join(
            [
                "User-agent: *",
                "Allow: /",
                "Allow: /players/",
                "Disallow: /api/",
                "Disallow: /dashboard",
                "Disallow: /player-dashboard",
                "Disallow: /admin",
                "Disallow: /login",
                "Disallow: /register",
                f"Sitemap: {PUBLIC_SITE_URL}/sitemap.xml",
                "",
            ]
        ),
        headers={"Cache-Control": "public, max-age=3600"},
    )
