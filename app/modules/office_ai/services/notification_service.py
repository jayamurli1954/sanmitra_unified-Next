from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection
from app.modules.office_ai.models import (
    NOTIFICATION_KINDS,
    NOTIFICATIONS_COLLECTION,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


async def create_notification(
    *,
    tenant_id: str,
    user: dict,
    title: str,
    body: str | None = None,
    kind: str = "note_processed",
    href: str | None = None,
    dedupe_key: str | None = None,
) -> dict | None:
    await ensure_indexes()
    uid = _user_id(user)
    key = (dedupe_key or "").strip()[:200] or None
    if key:
        existing = await get_collection(NOTIFICATIONS_COLLECTION).find_one(
            {"tenant_id": tenant_id, "user_id": uid, "dedupe_key": key}
        )
        if existing:
            return serialize_doc(existing)

    now = utcnow()
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "user_id": uid,
        "title": str(title or "").strip()[:300] or "OfficeMitra notice",
        "body": (str(body).strip()[:2000] if body else None) or None,
        "kind": kind if kind in NOTIFICATION_KINDS else "note_processed",
        "href": (str(href).strip()[:500] if href else None) or None,
        "dedupe_key": key,
        "read_at": None,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(NOTIFICATIONS_COLLECTION).insert_one(doc)
    return serialize_doc(doc)


async def list_notifications(
    *,
    tenant_id: str,
    user: dict,
    unread_only: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    await ensure_indexes()
    uid = _user_id(user)
    query: dict[str, Any] = {"tenant_id": tenant_id, "user_id": uid}
    if unread_only:
        query["read_at"] = None
    cursor = (
        get_collection(NOTIFICATIONS_COLLECTION)
        .find(query)
        .sort("created_at", -1)
        .limit(min(limit, 100))
    )
    items = [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 100))]
    unread_count = await get_collection(NOTIFICATIONS_COLLECTION).count_documents(
        {"tenant_id": tenant_id, "user_id": uid, "read_at": None}
    )
    return {"items": items, "count": len(items), "unread_count": int(unread_count)}


async def mark_read(*, tenant_id: str, user: dict, notification_id: str) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(notification_id):
        return None
    uid = _user_id(user)
    now = utcnow()
    result = await get_collection(NOTIFICATIONS_COLLECTION).find_one_and_update(
        {"_id": ObjectId(notification_id), "tenant_id": tenant_id, "user_id": uid},
        {"$set": {"read_at": now, "updated_at": now}},
    )
    if result is None:
        return None
    updated = await get_collection(NOTIFICATIONS_COLLECTION).find_one(
        {"_id": ObjectId(notification_id), "tenant_id": tenant_id, "user_id": uid}
    )
    return serialize_doc(updated)
