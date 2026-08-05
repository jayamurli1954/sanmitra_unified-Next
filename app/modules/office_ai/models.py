from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection

TASKS_COLLECTION = "officemitra_tasks"
EMAILS_COLLECTION = "officemitra_emails"
BRIEFS_COLLECTION = "officemitra_briefs"
TELEMETRY_COLLECTION = "officemitra_ai_telemetry"

TASK_STATUSES = frozenset({"open", "done", "cancelled"})
TASK_SOURCES = frozenset({"manual", "ai"})

_indexes_ready = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_object_id() -> ObjectId:
    return ObjectId()


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = dict(doc)
    for key, value in list(out.items()):
        if isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, list):
            out[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    if "_id" in out:
        out["id"] = out.pop("_id")
    elif out.get("id") is not None:
        out["id"] = str(out["id"])
    return out


async def ensure_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        await get_collection(TASKS_COLLECTION).create_index([("tenant_id", 1), ("status", 1), ("updated_at", -1)])
        await get_collection(EMAILS_COLLECTION).create_index([("tenant_id", 1), ("created_at", -1)])
        await get_collection(BRIEFS_COLLECTION).create_index(
            [("tenant_id", 1), ("brief_date", 1), ("generated_at", -1)]
        )
        await get_collection(TELEMETRY_COLLECTION).create_index(
            [("tenant_id", 1), ("feature", 1), ("created_at", -1)]
        )
        _indexes_ready = True
    except Exception:
        # Indexes are best-effort; routes still work without them.
        pass
