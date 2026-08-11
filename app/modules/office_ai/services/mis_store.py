from __future__ import annotations

import uuid
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection
from app.modules.office_ai.models import (
    MIS_EDITABLE_PACK_STATUSES,
    MIS_ENTITY_TYPES,
    MIS_EXPORTS_COLLECTION,
    MIS_FACTS_COLLECTION,
    MIS_INGESTION_PATHS,
    MIS_PACKS_COLLECTION,
    MIS_PACK_STATUSES,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)


class MISStoreError(ValueError):
    """Base error for MIS persistence layer."""


class MISPackNotFoundError(MISStoreError):
    pass


class MISImmutableError(MISStoreError):
    pass


def _actor_id(user: dict[str, Any] | None) -> str:
    if not user:
        return "system"
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "unknown").strip() or "unknown"


def _pack_oid(pack_id: str) -> ObjectId:
    try:
        return ObjectId(str(pack_id).strip())
    except Exception as exc:
        raise MISPackNotFoundError(f"Invalid pack_id: {pack_id}") from exc


def pack_is_editable(pack: dict[str, Any]) -> bool:
    if pack.get("immutable"):
        return False
    return str(pack.get("status") or "").strip().lower() in MIS_EDITABLE_PACK_STATUSES


def _catalog_entry(pack_key: str) -> dict[str, Any]:
    from app.modules.office_ai.services.mis_service import get_pack_catalog_entry

    entry = get_pack_catalog_entry(pack_key)
    if entry is None:
        raise MISStoreError(f"Unknown pack_key: {pack_key}")
    return entry


async def create_pack_draft(
    *,
    tenant_id: str,
    user: dict[str, Any],
    pack_key: str,
    period: str,
    ingestion_path: str = "manual",
    revision: int = 1,
    supersedes_pack_id: str | None = None,
) -> dict[str, Any]:
    await ensure_indexes()
    catalog = _catalog_entry(pack_key)
    path = str(ingestion_path or "manual").strip().lower()
    if path not in MIS_INGESTION_PATHS:
        raise MISStoreError(f"Invalid ingestion_path: {ingestion_path}")

    now = utcnow()
    actor = _actor_id(user)
    doc: dict[str, Any] = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "pack_key": catalog["pack_key"],
        "pack_version": catalog["pack_version"],
        "materiality_rule_version": catalog["materiality_rule_version"],
        "display_name": catalog.get("display_name"),
        "period": str(period or "").strip(),
        "status": "draft",
        "revision": max(1, int(revision or 1)),
        "supersedes_pack_id": str(supersedes_pack_id).strip() if supersedes_pack_id else None,
        "ingestion_path": path,
        "immutable": False,
        "data_quality_score": None,
        "data_quality_breakdown": None,
        "reconciled_at": None,
        "reconciled_by": None,
        "exported_at": None,
        "created_at": now,
        "updated_at": now,
        "created_by": actor,
        "updated_by": actor,
    }
    if not doc["period"]:
        raise MISStoreError("period is required")

    await get_collection(MIS_PACKS_COLLECTION).insert_one(doc)
    return serialize_doc(doc) or {}


async def list_packs(
    *,
    tenant_id: str,
    period: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await ensure_indexes()
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if period:
        query["period"] = str(period).strip()
    if status:
        normalized = str(status).strip().lower()
        if normalized not in MIS_PACK_STATUSES:
            raise MISStoreError(f"Invalid status: {status}")
        query["status"] = normalized

    cursor = (
        get_collection(MIS_PACKS_COLLECTION)
        .find(query)
        .sort("updated_at", -1)
        .limit(min(max(limit, 1), 200))
    )
    items = [serialize_doc(doc) async for doc in cursor]
    return [item for item in items if item]


async def get_pack(*, tenant_id: str, pack_id: str) -> dict[str, Any] | None:
    await ensure_indexes()
    doc = await get_collection(MIS_PACKS_COLLECTION).find_one(
        {"_id": _pack_oid(pack_id), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def _require_editable_pack(*, tenant_id: str, pack_id: str) -> dict[str, Any]:
    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    if not pack_is_editable(pack):
        raise MISImmutableError(
            f"Pack {pack_id} is immutable (status={pack.get('status')}); create a new revision instead"
        )
    return pack


def _normalize_fact_input(raw: dict[str, Any], *, pack_id: str, tenant_id: str) -> dict[str, Any]:
    entity_type = str(raw.get("entity_type") or "").strip().lower()
    if entity_type not in MIS_ENTITY_TYPES:
        raise MISStoreError(f"Invalid entity_type: {raw.get('entity_type')}")

    fact_id = str(raw.get("fact_id") or uuid.uuid4().hex).strip()
    amount_decimal = raw.get("amount_decimal")
    if amount_decimal is not None:
        amount_decimal = str(amount_decimal)
    amount_minor = raw.get("amount_minor")
    if amount_minor is not None:
        amount_minor = int(amount_minor)

    return {
        "tenant_id": tenant_id,
        "pack_id": pack_id,
        "fact_id": fact_id,
        "entity_type": entity_type,
        "period": str(raw.get("period") or "").strip() or None,
        "as_of": str(raw.get("as_of") or "").strip() or None,
        "source_system": str(raw.get("source_system") or "manual").strip().lower(),
        "source_id": raw.get("source_id"),
        "source_ref": raw.get("source_ref"),
        "amount_decimal": amount_decimal,
        "amount_minor": amount_minor,
        "currency": str(raw.get("currency") or "INR").strip().upper(),
        "value": raw.get("value"),
        "dimensions": dict(raw.get("dimensions") or {}),
        "reconciled": False,
        "immutable": False,
    }


async def insert_facts(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    await _require_editable_pack(tenant_id=tenant_id, pack_id=pack_id)
    if not facts:
        return {"inserted": 0, "fact_ids": []}

    now = utcnow()
    actor = _actor_id(user)
    docs: list[dict[str, Any]] = []
    for raw in facts:
        normalized = _normalize_fact_input(raw, pack_id=pack_id, tenant_id=tenant_id)
        normalized["created_at"] = now
        normalized["updated_at"] = now
        normalized["created_by"] = actor
        normalized["updated_by"] = actor
        docs.append(normalized)

    col = get_collection(MIS_FACTS_COLLECTION)
    await col.insert_many(docs)
    await get_collection(MIS_PACKS_COLLECTION).update_one(
        {"_id": _pack_oid(pack_id), "tenant_id": tenant_id},
        {"$set": {"updated_at": now, "updated_by": actor}},
    )
    return {"inserted": len(docs), "fact_ids": [doc["fact_id"] for doc in docs]}


async def list_facts(
    *,
    tenant_id: str,
    pack_id: str,
    entity_type: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    await ensure_indexes()
    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")

    query: dict[str, Any] = {"tenant_id": tenant_id, "pack_id": pack_id}
    if entity_type:
        et = str(entity_type).strip().lower()
        if et not in MIS_ENTITY_TYPES:
            raise MISStoreError(f"Invalid entity_type: {entity_type}")
        query["entity_type"] = et

    cursor = (
        get_collection(MIS_FACTS_COLLECTION)
        .find(query)
        .sort("entity_type", 1)
        .limit(min(max(limit, 1), 2000))
    )
    items = [serialize_doc(doc) async for doc in cursor]
    return [item for item in items if item]


async def update_pack_status(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    normalized = str(status or "").strip().lower()
    if normalized not in MIS_PACK_STATUSES:
        raise MISStoreError(f"Invalid status: {status}")

    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    if pack.get("immutable") and normalized in MIS_EDITABLE_PACK_STATUSES:
        raise MISImmutableError(f"Pack {pack_id} is immutable")

    now = utcnow()
    actor = _actor_id(user)
    await get_collection(MIS_PACKS_COLLECTION).update_one(
        {"_id": _pack_oid(pack_id), "tenant_id": tenant_id},
        {"$set": {"status": normalized, "updated_at": now, "updated_by": actor}},
    )
    updated = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    return updated or {}


async def reconcile_pack(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
    data_quality_score: int | None = None,
    data_quality_breakdown: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    if pack.get("immutable"):
        raise MISImmutableError(f"Pack {pack_id} is already immutable")

    now = utcnow()
    actor = _actor_id(user)
    pack_update: dict[str, Any] = {
        "status": "reconciled",
        "immutable": True,
        "reconciled_at": now,
        "reconciled_by": actor,
        "updated_at": now,
        "updated_by": actor,
    }
    if data_quality_score is not None:
        pack_update["data_quality_score"] = max(0, min(100, int(data_quality_score)))
    if data_quality_breakdown is not None:
        pack_update["data_quality_breakdown"] = dict(data_quality_breakdown)

    await get_collection(MIS_PACKS_COLLECTION).update_one(
        {"_id": _pack_oid(pack_id), "tenant_id": tenant_id},
        {"$set": pack_update},
    )
    await get_collection(MIS_FACTS_COLLECTION).update_many(
        {"tenant_id": tenant_id, "pack_id": pack_id, "immutable": False},
        {
            "$set": {
                "immutable": True,
                "reconciled": True,
                "updated_at": now,
                "updated_by": actor,
            }
        },
    )
    updated = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    return updated or {}


async def mark_pack_exported(*, tenant_id: str, pack_id: str, user: dict[str, Any]) -> dict[str, Any]:
    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    if str(pack.get("status") or "") not in {"reconciled", "pending_export", "exported"}:
        raise MISStoreError("Pack must be reconciled before export")

    now = utcnow()
    actor = _actor_id(user)
    await get_collection(MIS_PACKS_COLLECTION).update_one(
        {"_id": _pack_oid(pack_id), "tenant_id": tenant_id},
        {
            "$set": {
                "status": "exported",
                "immutable": True,
                "exported_at": now,
                "updated_at": now,
                "updated_by": actor,
            }
        },
    )
    updated = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    return updated or {}


async def save_export_artifact(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
    export_format: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> dict[str, Any]:
    """Persist generated export bytes (tenant-scoped). Content excluded from serialized meta."""
    from bson.binary import Binary

    await ensure_indexes()
    pack = await get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise MISPackNotFoundError(f"MIS pack not found: {pack_id}")

    now = utcnow()
    actor = _actor_id(user)
    payload = content if isinstance(content, (bytes, bytearray)) else bytes(content or b"")
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "pack_id": pack_id,
        "format": str(export_format or "").strip().lower(),
        "filename": str(filename or "mis-export.bin"),
        "content_type": str(content_type or "application/octet-stream"),
        "byte_size": len(payload),
        "content": Binary(payload),
        "created_at": now,
        "created_by": actor,
        "status": "generated",
    }
    await get_collection(MIS_EXPORTS_COLLECTION).insert_one(doc)
    meta = serialize_doc({k: v for k, v in doc.items() if k != "content"}) or {}
    meta["download_path"] = f"/api/v1/officemitra/mis/exports/{meta['id']}/download"
    return meta


async def get_export_artifact(
    *,
    tenant_id: str,
    artifact_id: str,
    include_content: bool = False,
) -> dict[str, Any] | None:
    await ensure_indexes()
    if not ObjectId.is_valid(artifact_id):
        return None
    doc = await get_collection(MIS_EXPORTS_COLLECTION).find_one(
        {"_id": ObjectId(artifact_id), "tenant_id": tenant_id}
    )
    if not doc:
        return None
    if include_content:
        out = dict(doc)
        content = out.pop("content", b"")
        meta = serialize_doc(out) or {}
        meta["content"] = bytes(content) if content is not None else b""
        return meta
    meta = serialize_doc({k: v for k, v in doc.items() if k != "content"}) or {}
    meta["download_path"] = f"/api/v1/officemitra/mis/exports/{meta['id']}/download"
    return meta
