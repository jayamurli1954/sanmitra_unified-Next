from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.mongo import get_collection

AUDIT_COLLECTION = "core_audit_logs"


async def ensure_audit_indexes() -> None:
    audit = get_collection(AUDIT_COLLECTION)
    await audit.create_index([("tenant_id", 1), ("timestamp", -1)])
    await audit.create_index([("tenant_id", 1), ("entity_type", 1), ("entity_id", 1), ("timestamp", -1)])


async def log_audit_event(
    *,
    tenant_id: str,
    user_id: str,
    product: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> str:
    audit = get_collection(AUDIT_COLLECTION)
    event_id = str(uuid4())

    doc = {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "product": product,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_value": old_value,
        "new_value": new_value,
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc),
    }
    await audit.insert_one(doc)
    return event_id


def _json_safe_event(doc: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in doc.items() if key != "_id"}


async def list_audit_events(
    *,
    tenant_id: str,
    product: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    filters: dict[str, Any] = {"tenant_id": tenant_id}
    if product:
        filters["product"] = product
    if entity_type:
        filters["entity_type"] = entity_type
    if entity_id:
        filters["entity_id"] = entity_id
    if action:
        filters["action"] = action

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(AUDIT_COLLECTION)
        .find(filters)
        .sort("timestamp", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_json_safe_event(row) for row in rows], "total": len(rows)}
