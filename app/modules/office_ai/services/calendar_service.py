from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection
from app.modules.office_ai.models import (
    CALENDAR_EVENTS_COLLECTION,
    CALENDAR_SOURCES,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)
from app.modules.office_ai.services import notification_service


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


def _parse_ics_datetime(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if ":" in raw and raw.upper().startswith("TZID"):
        raw = raw.split(":", 1)[-1]
    raw = raw.replace("Z", "")
    for fmt, length in (("%Y%m%dT%H%M%S", 15), ("%Y%m%dT%H%M", 13), ("%Y%m%d", 8)):
        try:
            dt = datetime.strptime(raw[:length], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def parse_calendar_text(raw_text: str) -> list[dict[str, Any]]:
    """Deterministic paste parser for ICS VEVENT blocks and simple agenda lines."""
    text = (raw_text or "").strip()
    if not text:
        return []
    events: list[dict[str, Any]] = []

    if "BEGIN:VEVENT" in text.upper():
        blocks = re.split(r"(?i)BEGIN:VEVENT", text)
        for block in blocks[1:]:
            end = re.split(r"(?i)END:VEVENT", block, maxsplit=1)[0]
            fields: dict[str, str] = {}
            for line in end.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.split(";")[0].strip().upper()
                fields[key] = value.strip()
            title = fields.get("SUMMARY") or "Calendar event"
            starts = _parse_ics_datetime(fields.get("DTSTART", ""))
            ends = _parse_ics_datetime(fields.get("DTEND", ""))
            if starts is None:
                continue
            events.append(
                {
                    "title": title[:500],
                    "starts_at": starts.isoformat(),
                    "ends_at": ends.isoformat() if ends else None,
                    "location": (fields.get("LOCATION") or "")[:300] or None,
                }
            )
        if events:
            return events

    today = date.today()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # e.g. "2026-08-05 10:00 Client GST review" or "10:00 Client GST review"
        m = re.match(
            r"^(?:(\d{4}-\d{2}-\d{2})\s+)?(\d{1,2}:\d{2})\s+(.+)$",
            line,
        )
        if m:
            day_s, time_s, title = m.group(1), m.group(2), m.group(3).strip()
            day = date.fromisoformat(day_s) if day_s else today
            hour, minute = [int(x) for x in time_s.split(":")]
            starts = datetime.combine(day, time(hour=hour, minute=minute), tzinfo=timezone.utc)
            events.append(
                {
                    "title": title[:500],
                    "starts_at": starts.isoformat(),
                    "ends_at": None,
                    "location": None,
                }
            )
            continue
        # Fallback: treat non-empty line as all-day event today
        if len(line) >= 3:
            starts = datetime.combine(today, time(9, 0), tzinfo=timezone.utc)
            events.append(
                {
                    "title": line[:500],
                    "starts_at": starts.isoformat(),
                    "ends_at": None,
                    "location": None,
                }
            )
    return events


def _to_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _utc_today() -> date:
    """Calendar day boundaries use UTC to match stored starts_at (UTC)."""
    return datetime.now(timezone.utc).date()


async def list_events(
    *,
    tenant_id: str,
    day: str | None = None,
    limit: int = 100,
) -> list[dict]:
    await ensure_indexes()
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if day:
        try:
            d = date.fromisoformat(day)
        except ValueError:
            d = _utc_today()
        start = datetime.combine(d, time.min, tzinfo=timezone.utc)
        end = datetime.combine(d, time.max, tzinfo=timezone.utc)
        query["starts_at"] = {"$gte": start, "$lte": end}
    cursor = (
        get_collection(CALENDAR_EVENTS_COLLECTION)
        .find(query)
        .sort("starts_at", 1)
        .limit(min(limit, 200))
    )
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 200))]


async def list_today_events(*, tenant_id: str, limit: int = 50) -> list[dict]:
    return await list_events(tenant_id=tenant_id, day=_utc_today().isoformat(), limit=limit)


async def create_event(
    *,
    tenant_id: str,
    user: dict,
    title: str,
    starts_at: str | datetime,
    ends_at: str | datetime | None = None,
    location: str | None = None,
    raw_text: str | None = None,
    source: str = "manual",
    linked_note_id: str | None = None,
    notify: bool = True,
) -> dict:
    await ensure_indexes()
    starts = _to_datetime(starts_at)
    if starts is None:
        raise ValueError("starts_at is required and must be ISO datetime")
    ends = _to_datetime(ends_at)
    now = utcnow()
    uid = _user_id(user)
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "title": str(title or "").strip()[:500] or "Calendar event",
        "starts_at": starts,
        "ends_at": ends,
        "location": (str(location).strip()[:300] if location else None) or None,
        "raw_text": (str(raw_text).strip()[:20000] if raw_text else None) or None,
        "source": source if source in CALENDAR_SOURCES else "manual",
        "linked_note_id": ObjectId(linked_note_id)
        if linked_note_id and ObjectId.is_valid(linked_note_id)
        else None,
        "created_at": now,
        "updated_at": now,
        "created_by": uid,
        "updated_by": uid,
    }
    await get_collection(CALENDAR_EVENTS_COLLECTION).insert_one(doc)
    item = serialize_doc(doc)
    if notify and starts.astimezone(timezone.utc).date() == _utc_today():
        await notification_service.create_notification(
            tenant_id=tenant_id,
            user=user,
            title=f"Today: {doc['title']}",
            body=f"Starts at {starts.isoformat()}",
            kind="calendar_due",
            href="/business/office-ai",
            dedupe_key=f"calendar_due:{item['id']}",
        )
    return item


async def update_event(
    *,
    tenant_id: str,
    user: dict,
    event_id: str,
    updates: dict[str, Any],
) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(event_id):
        return None
    allowed: dict[str, Any] = {}
    if "title" in updates and updates["title"] is not None:
        allowed["title"] = str(updates["title"]).strip()[:500]
    if "starts_at" in updates:
        starts = _to_datetime(updates["starts_at"])
        if starts is None:
            return None
        allowed["starts_at"] = starts
    if "ends_at" in updates:
        allowed["ends_at"] = _to_datetime(updates["ends_at"])
    if "location" in updates:
        loc = updates["location"]
        allowed["location"] = (str(loc).strip()[:300] if loc is not None else None)
    if not allowed:
        existing = await get_collection(CALENDAR_EVENTS_COLLECTION).find_one(
            {"_id": ObjectId(event_id), "tenant_id": tenant_id}
        )
        return serialize_doc(existing)
    allowed["updated_at"] = utcnow()
    allowed["updated_by"] = _user_id(user)
    result = await get_collection(CALENDAR_EVENTS_COLLECTION).find_one_and_update(
        {"_id": ObjectId(event_id), "tenant_id": tenant_id},
        {"$set": allowed},
    )
    if result is None:
        return None
    updated = await get_collection(CALENDAR_EVENTS_COLLECTION).find_one(
        {"_id": ObjectId(event_id), "tenant_id": tenant_id}
    )
    return serialize_doc(updated)


async def parse_and_optionally_persist(
    *,
    tenant_id: str,
    user: dict,
    raw_text: str,
    persist: bool = True,
) -> dict[str, Any]:
    suggested = parse_calendar_text(raw_text)
    saved: list[dict] = []
    if persist:
        for item in suggested:
            saved.append(
                await create_event(
                    tenant_id=tenant_id,
                    user=user,
                    title=item["title"],
                    starts_at=item["starts_at"],
                    ends_at=item.get("ends_at"),
                    location=item.get("location"),
                    raw_text=raw_text[:2000],
                    source="paste",
                    notify=True,
                )
            )
        if saved:
            await notification_service.create_notification(
                tenant_id=tenant_id,
                user=user,
                title=f"Calendar: {len(saved)} event(s) saved",
                body="Parsed from pasted calendar text.",
                kind="calendar_parsed",
                href="/business/office-ai",
                dedupe_key=f"calendar_parsed:{_utc_today().isoformat()}:{len(saved)}:{_user_id(user)}",
            )
    return {
        "suggested_events": suggested,
        "saved_events": saved,
        "count": len(saved) if persist else len(suggested),
        "ai_available": False,
        "parser": "deterministic_v1",
    }
