"""
Shared match identity, kickoff-window and duplicate-request rules for EnejiStats.
All stats-request submitters import this module so the rules cannot drift by role.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def canonical_match_id(match_date: Any, home_team: Any, away_team: Any) -> str:
    """Stable fallback ID shared by every role for the same dated, ordered fixture."""
    teams = sorted((_clean(home_team), _clean(away_team)))
    raw = "|".join((_clean(match_date), teams[0], teams[1]))
    if not all((_clean(match_date), _clean(home_team), _clean(away_team))):
        raise ValueError("Match date, home team and away team are required to identify a match")
    return "MAT-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()


def kickoff_datetime(match_date: Any, match_time: Any, match_timezone: Any = None) -> datetime:
    date_text = str(match_date or "").strip()
    time_text = str(match_time or "").strip()
    if not date_text or not time_text:
        raise ValueError("Match date and kickoff time are required")
    dt_text = date_text if "T" in date_text else f"{date_text}T{time_text}"
    if "T" in date_text and not time_text:
        dt_text = date_text
    try:
        dt = datetime.fromisoformat(dt_text.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = date.fromisoformat(date_text[:10])
            t = time.fromisoformat(time_text)
            dt = datetime.combine(d, t)
        except Exception:
            try:
                from datetime import datetime as _dt
                t = _dt.strptime(time_text, "%I:%M %p").time()
                dt = datetime.combine(date.fromisoformat(date_text[:10]), t)
            except Exception as exc:
                raise ValueError("Invalid match date or kickoff time") from exc
    if dt.tzinfo is None:
        tz_name = str(match_timezone or "Africa/Lagos").strip() or "Africa/Lagos"
        try:
            dt = dt.replace(tzinfo=ZoneInfo(tz_name))
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown match timezone: {tz_name}") from exc
    return dt.astimezone(timezone.utc)


def validate_stats_window(match_date: Any, match_time: Any, match_timezone: Any,
                          minimum_hours: int, maximum_hours: int,
                          now: Optional[datetime] = None) -> datetime:
    kickoff = kickoff_datetime(match_date, match_time, match_timezone)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    hours = (kickoff - current.astimezone(timezone.utc)).total_seconds() / 3600
    if hours < minimum_hours or hours > maximum_hours:
        raise ValueError(
            f"This stats request can only be submitted {minimum_hours} to {maximum_hours} hours before kickoff. "
            f"Time remaining: {max(0, hours):.2f} hours."
        )
    return kickoff


async def resolve_match_id(match_date: Any, home_team: Any, away_team: Any,
                           supplied_match_id: Any = None,
                           collections: Iterable[Any] = ()) -> str:
    """Prefer a verified registered fixture ID; otherwise return the shared stable ID."""
    supplied = str(supplied_match_id or "").strip()
    home, away = str(home_team or "").strip(), str(away_team or "").strip()
    date_text = str(match_date or "").strip()
    for col in collections:
        if col is None:
            continue
        try:
            if supplied:
                doc = await col.find_one({"match_id": supplied})
                if doc and doc.get("match_id"):
                    return str(doc["match_id"])
                if len(supplied) == 24:
                    try:
                        from bson import ObjectId
                        doc = await col.find_one({"_id": ObjectId(supplied)})
                        if doc:
                            return str(doc.get("match_id") or canonical_match_id(
                                doc.get("match_date") or doc.get("date"),
                                doc.get("home_team"), doc.get("away_team")))
                    except Exception:
                        pass
            for h, a in ((home, away), (away, home)):
                doc = await col.find_one({
                    "match_date": date_text,
                    "home_team": {"$regex": "^" + re.escape(h) + "$", "$options": "i"},
                    "away_team": {"$regex": "^" + re.escape(a) + "$", "$options": "i"},
                })
                if doc and doc.get("match_id"):
                    return str(doc["match_id"])
        except Exception:
            continue
    return canonical_match_id(date_text, home, away)


# A fixture/player pair is a one-time request identity. Even a cancelled,
# rejected or completed request remains in the audit trail and must not be
# silently duplicated by another dashboard.


async def find_duplicate_stats_request(collection: Any, match_id: str,
                                       player_id: Any = None,
                                       club_id: Any = None,
                                       match_date: Any = None,
                                       home_team: Any = None,
                                       away_team: Any = None) -> Optional[dict]:
    """Find an active request for this fixture/player or fixture/club, including legacy rows."""
    if collection is None or not match_id:
        return None
    fixture_clauses = [{"match_id": match_id}]
    if match_date and home_team and away_team:
        for home, away in ((home_team, away_team), (away_team, home_team)):
            fixture_clauses.append({
                "match_date": str(match_date),
                "home_team": {"$regex": "^" + re.escape(str(home).strip()) + "$", "$options": "i"},
                "away_team": {"$regex": "^" + re.escape(str(away).strip()) + "$", "$options": "i"},
            })
    clauses = [{"$or": fixture_clauses}]
    if player_id:
        pid = str(player_id)
        clauses.append({"$or": [
            {"player_id": pid}, {"user_id": pid}, {"player_ids": pid},
            {"player_request_states.player_id": pid},
        ]})
    elif club_id:
        cid = str(club_id)
        clauses.append({"$or": [{"club_id": cid}, {"user_id": cid}]})
        # Player-only requests submitted on behalf of a club must not block a
        # later club-level request for the same fixture.
        clauses.append({"$nor": [
            {"entity_type": "player"},
            {"requester_type": "player"},
            {"request_type": "player"},
        ]})
    query = {"$and": clauses}
    try:
        cursor = collection.find(query).sort("submitted_at", -1).limit(100)
        rows = await cursor.to_list(length=100)
    except Exception:
        row = await collection.find_one(query)
        rows = [row] if row else []
    for row in rows:
        return row
    return None



async def ensure_stats_request_indexes(collection: Any) -> None:
    """Best-effort unique indexes close the concurrent-submit race for new schemas."""
    if collection is None:
        return
    try:
        await collection.create_index(
            [("match_id", 1), ("player_id", 1)],
            unique=True,
            partialFilterExpression={
                "match_id": {"$type": "string"},
                "player_id": {"$type": "string"},
            },
            name="uniq_stats_request_match_player",
        )
    except Exception:
        # Existing legacy duplicates can prevent index creation. The role routes
        # still run the cross-schema duplicate lookup before accepting a request.
        pass


def is_duplicate_key_error(exc: Exception) -> bool:
    return getattr(exc, "code", None) == 11000 or "duplicate key" in str(exc).casefold()

async def resolve_registered_venue(collection: Any, venue_id: Any) -> Optional[dict]:
    """Resolve a selected venue against the auth registration collection."""
    value = str(venue_id or '').strip()
    if not collection or not value:
        return None
    clauses = [{'venue_id': value}, {'id': value}]
    try:
        from bson import ObjectId
        clauses.insert(0, {'_id': ObjectId(value)})
    except Exception:
        pass
    try:
        doc = await collection.find_one({'$or': clauses})
    except Exception:
        doc = None
    if not doc:
        return None
    name = str(doc.get('venue_name') or doc.get('name') or doc.get('stadium') or doc.get('ground_name') or doc.get('field_name') or '').strip()
    address = str(doc.get('full_address') or doc.get('address') or doc.get('venue_address') or doc.get('stadium_address') or doc.get('ground_address') or doc.get('field_address') or '').strip()
    if not name:
        return None
    return {
        'venue_id': str(doc.get('venue_id') or doc.get('id') or doc.get('_id') or value),
        'venue_name': name, 'venue_address': address, 'venue_detailed_address': address,
        'venue_country': doc.get('country') or '', 'venue_country_code': str(doc.get('country_code') or '').upper(),
        'venue_state': doc.get('state') or doc.get('region') or doc.get('province') or '',
        'venue_region': doc.get('region') or '', 'venue_province': doc.get('province') or doc.get('county') or '',
        'venue_lga': doc.get('lga') or doc.get('local_area') or doc.get('subregion') or '',
        'venue_city': doc.get('city') or doc.get('town') or '',
        'venue_type': doc.get('venue_type') or '', 'venue_capacity': doc.get('capacity'),
        'venue_gps_lat': doc.get('gps_lat'), 'venue_gps_lng': doc.get('gps_lng'),
        'venue_photo_url': doc.get('photo_url') or '',
    }


async def resolve_registered_club(collection: Any, club_id: Any = None, club_name: Any = None) -> Optional[dict]:
    """Resolve a club selected from the registration-backed public directory."""
    value = str(club_id or '').strip()
    name = str(club_name or '').strip()
    if collection is None:
        return None
    clauses = []
    if value:
        clauses.extend([{'club_id': value}, {'user_id': value}, {'id': value}])
        try:
            from bson import ObjectId
            clauses.insert(0, {'_id': ObjectId(value)})
        except Exception:
            pass
    elif name:
        import re
        safe = re.escape(name)
        clauses.extend([{'club_name': {'$regex': '^' + safe + '$', '$options': 'i'}}, {'name': {'$regex': '^' + safe + '$', '$options': 'i'}}])
    if not clauses:
        return None
    try:
        doc = await collection.find_one({'$or': clauses})
    except Exception:
        doc = None
    if not doc:
        return None
    return {
        'club_id': str(doc.get('club_id') or doc.get('user_id') or doc.get('_id') or ''),
        'club_name': str(doc.get('club_name') or doc.get('full_name') or doc.get('name') or ''),
        'country': doc.get('country') or '', 'state': doc.get('state') or doc.get('region') or '',
        'lga': doc.get('lga') or '', 'city': doc.get('city') or doc.get('town') or '',
        'primary_ground_id': doc.get('primary_ground_id') or '',
    }


async def upsert_canonical_match_record(matches_collection: Any, payload: dict, *, source: str = "Stats request", source_request_id: str = "") -> dict:
    """Create/update one canonical fixture with complete teams and venue metadata.

    A fixture is keyed by canonical match_id (date + unordered teams), while
    source_request_id is retained for audit and idempotent conversion.
    """
    if matches_collection is None:
        return {}
    home = str(payload.get("home_team") or payload.get("home") or "").strip()
    away = str(payload.get("away_team") or payload.get("away") or "").strip()
    date_value = payload.get("match_date") or payload.get("date") or payload.get("event_date")
    time_value = payload.get("match_time") or payload.get("time") or payload.get("kickoff_time") or "00:00"
    venue = str(payload.get("venue_name") or payload.get("venue") or payload.get("venue_address") or "").strip()
    if not (home and away and date_value and venue) or home.casefold() == away.casefold():
        return {}
    mid = str(payload.get("match_id") or canonical_match_id(date_value, home, away))
    now = datetime.now(timezone.utc)
    doc = {
        "match_id": mid, "home_team": home, "away_team": away, "home": home, "away": away,
        "home_team_id": str(payload.get("home_club_id") or payload.get("home_team_id") or ""),
        "away_team_id": str(payload.get("away_club_id") or payload.get("away_team_id") or ""),
        "match_date": str(date_value), "match_time": str(time_value), "date": str(date_value), "time": str(time_value),
        "venue_id": str(payload.get("venue_id") or ""), "venue": venue, "venue_name": venue,
        "venue_address": payload.get("venue_address") or payload.get("venue_detailed_address") or "",
        "venue_detailed_address": payload.get("venue_detailed_address") or payload.get("venue_address") or "",
        "country": payload.get("venue_country") or payload.get("country") or "",
        "country_name": payload.get("venue_country") or payload.get("country_name") or payload.get("country") or "",
        "country_code": str(payload.get("venue_country_code") or payload.get("country_code") or "").upper(),
        "state": payload.get("venue_state") or payload.get("state") or payload.get("region") or "",
        "region": payload.get("venue_region") or payload.get("region") or payload.get("venue_state") or "",
        "province": payload.get("venue_province") or payload.get("province") or "",
        "lga": payload.get("venue_lga") or payload.get("lga") or "",
        "city": payload.get("venue_city") or payload.get("city") or "",
        "venue_country": payload.get("venue_country") or payload.get("country") or "",
        "venue_country_code": str(payload.get("venue_country_code") or payload.get("country_code") or "").upper(),
        "venue_state": payload.get("venue_state") or payload.get("state") or "",
        "venue_lga": payload.get("venue_lga") or payload.get("lga") or "",
        "venue_city": payload.get("venue_city") or payload.get("city") or "",
        "venue_type": payload.get("venue_type") or "", "venue_capacity": payload.get("venue_capacity"),
        "gps": payload.get("gps") or (dict(lat=payload.get("venue_gps_lat"), lng=payload.get("venue_gps_lng")) if payload.get("venue_gps_lat") is not None and payload.get("venue_gps_lng") is not None else None),
        "category": payload.get("match_type") or payload.get("category") or "",
        "competition": payload.get("competition") or payload.get("competition_name") or "",
        "status": payload.get("match_status") or "scheduled", "source": source,
        "source_request_id": str(source_request_id or payload.get("request_id") or payload.get("reference_id") or ""),
        "notes": payload.get("notes") or "", "updated_at": now,
    }
    existing = await matches_collection.find_one({"match_id": mid})
    if existing:
        # Preserve admin-entered details/status; fill blanks and refresh request linkage.
        fill = {k: v for k, v in doc.items() if v not in (None, "", []) and existing.get(k) in (None, "", [])}
        fill["updated_at"] = now
        if source_request_id: fill["source_request_id"] = str(source_request_id)
        await matches_collection.update_one({"match_id": mid}, {"$set": fill})
        return (await matches_collection.find_one({"match_id": mid})) or existing
    doc["created_at"] = now
    await matches_collection.insert_one(doc)
    return doc
