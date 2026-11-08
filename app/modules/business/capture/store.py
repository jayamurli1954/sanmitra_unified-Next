"""Tenant/app/entity-scoped persistence for CaptureItems (MongoDB)."""
from __future__ import annotations

from typing import Any

from app.db.mongo import get_collection
from app.modules.business.capture import models


def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }


async def insert(doc: dict[str, Any]) -> dict[str, Any]:
    await get_collection(models.COLLECTION).insert_one(dict(doc))
    return models.serialize(doc)  # type: ignore[return-value]


async def find_by_fingerprint(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, fingerprint: str
) -> dict[str, Any] | None:
    row = await get_collection(models.COLLECTION).find_one(
        {**_scope(tenant_id, app_key, accounting_entity_id), "fingerprint": fingerprint}
    )
    return models.serialize(row)


async def get(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, capture_id: str
) -> dict[str, Any] | None:
    row = await get_collection(models.COLLECTION).find_one(
        {**_scope(tenant_id, app_key, accounting_entity_id), "capture_id": capture_id}
    )
    return models.serialize(row)


async def update(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, capture_id: str, updates: dict[str, Any]
) -> dict[str, Any] | None:
    await get_collection(models.COLLECTION).update_one(
        {**_scope(tenant_id, app_key, accounting_entity_id), "capture_id": capture_id},
        {"$set": {**updates, "updated_at": models.utcnow()}},
    )
    return await get(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id
    )


async def list_items(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = _scope(tenant_id, app_key, accounting_entity_id)
    if status:
        query["status"] = status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(models.COLLECTION)
        .find(query)
        .sort("created_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return [models.serialize(row) for row in rows]  # type: ignore[misc]
