"""OfficeMitra Review persistence (ADR-015). Tenant-scoped Mongo only — no ledger writes."""
from __future__ import annotations

import hashlib
from typing import Any

from bson import ObjectId
from bson.binary import Binary

from app.db.mongo import get_collection
from app.modules.office_ai.models import (
    REVIEW_ENGAGEMENT_STATUSES,
    REVIEW_ENGAGEMENTS_COLLECTION,
    REVIEW_ISSUE_STATUSES,
    REVIEW_ISSUES_COLLECTION,
    REVIEW_NOTE_STATUSES,
    REVIEW_NOTES_COLLECTION,
    REVIEW_PAPER_GENERATOR_VERSION,
    REVIEW_PAPER_STATUSES,
    REVIEW_PAPER_TYPES,
    REVIEW_PAPERS_COLLECTION,
    REVIEW_RULE_VERSION,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)


class ReviewStoreError(ValueError):
    """Base error for Review persistence."""


class ReviewNotFoundError(ReviewStoreError):
    pass


class ReviewImmutableError(ReviewStoreError):
    pass


def _actor_id(user: dict[str, Any] | None) -> str:
    if not user:
        return "system"
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "unknown").strip() or "unknown"


def _oid(value: str, *, label: str) -> ObjectId:
    try:
        return ObjectId(str(value).strip())
    except Exception as exc:
        raise ReviewNotFoundError(f"Invalid {label}: {value}") from exc


def _strip_content(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = dict(doc)
    out.pop("content", None)
    return serialize_doc(out)


async def create_engagement(
    *,
    tenant_id: str,
    user: dict[str, Any],
    period: str,
    pack_id: str | None = None,
    accounting_entity_id: str | None = None,
    jurisdiction: str = "IN",
) -> dict[str, Any]:
    await ensure_indexes()
    period_value = str(period or "").strip()
    if not period_value:
        raise ReviewStoreError("period is required")
    now = utcnow()
    actor = _actor_id(user)
    doc: dict[str, Any] = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "period": period_value,
        "jurisdiction": str(jurisdiction or "IN").strip().upper()[:8] or "IN",
        "pack_id": str(pack_id).strip() if pack_id else None,
        "accounting_entity_id": str(accounting_entity_id).strip() if accounting_entity_id else None,
        "status": "open",
        "engagement_risk_score": None,
        "rule_version": REVIEW_RULE_VERSION,
        "last_scanned_at": None,
        "created_at": now,
        "updated_at": now,
        "created_by": actor,
        "updated_by": actor,
    }
    await get_collection(REVIEW_ENGAGEMENTS_COLLECTION).insert_one(doc)
    return serialize_doc(doc) or {}


async def list_engagements(*, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    await ensure_indexes()
    cursor = (
        get_collection(REVIEW_ENGAGEMENTS_COLLECTION)
        .find({"tenant_id": tenant_id})
        .sort("updated_at", -1)
        .limit(min(max(limit, 1), 200))
    )
    items = [serialize_doc(doc) async for doc in cursor]
    return [item for item in items if item]


async def get_engagement(*, tenant_id: str, engagement_id: str) -> dict[str, Any] | None:
    await ensure_indexes()
    doc = await get_collection(REVIEW_ENGAGEMENTS_COLLECTION).find_one(
        {"_id": _oid(engagement_id, label="engagement_id"), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def update_engagement(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    existing = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if existing is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    allowed = {
        "pack_id",
        "accounting_entity_id",
        "status",
        "engagement_risk_score",
        "last_scanned_at",
        "rule_version",
    }
    payload = {key: value for key, value in updates.items() if key in allowed}
    if "status" in payload:
        status = str(payload["status"] or "").strip().lower()
        if status not in REVIEW_ENGAGEMENT_STATUSES:
            raise ReviewStoreError(f"Invalid engagement status: {status}")
        payload["status"] = status
    if not payload:
        return existing
    now = utcnow()
    payload["updated_at"] = now
    payload["updated_by"] = _actor_id(user)
    await get_collection(REVIEW_ENGAGEMENTS_COLLECTION).update_one(
        {"_id": _oid(engagement_id, label="engagement_id"), "tenant_id": tenant_id},
        {"$set": payload},
    )
    updated = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    return updated or {}


async def replace_issues(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    col = get_collection(REVIEW_ISSUES_COLLECTION)
    await col.delete_many({"tenant_id": tenant_id, "engagement_id": engagement_id})
    if not issues:
        return []
    now = utcnow()
    actor = _actor_id(user)
    docs: list[dict[str, Any]] = []
    for raw in issues:
        code = str(raw.get("finding_code") or "").strip().upper()
        if not code:
            continue
        docs.append(
            {
                "_id": new_object_id(),
                "tenant_id": tenant_id,
                "engagement_id": engagement_id,
                "finding_code": code,
                "rule_version": str(raw.get("rule_version") or REVIEW_RULE_VERSION),
                "severity": str(raw.get("severity") or "medium").strip().lower(),
                "description": str(raw.get("description") or "")[:2000],
                "fact_ids": list(raw.get("fact_ids") or []),
                "ai_generated": False,
                "status": "open",
                "created_at": now,
                "updated_at": now,
                "created_by": actor,
                "updated_by": actor,
            }
        )
    if docs:
        await col.insert_many(docs)
    return [item for item in (serialize_doc(doc) for doc in docs) if item]


async def list_issues(*, tenant_id: str, engagement_id: str) -> list[dict[str, Any]]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    cursor = (
        get_collection(REVIEW_ISSUES_COLLECTION)
        .find({"tenant_id": tenant_id, "engagement_id": engagement_id})
        .sort("finding_code", 1)
        .limit(500)
    )
    items = [serialize_doc(doc) async for doc in cursor]
    return [item for item in items if item]


async def get_issue(*, tenant_id: str, issue_id: str) -> dict[str, Any] | None:
    await ensure_indexes()
    doc = await get_collection(REVIEW_ISSUES_COLLECTION).find_one(
        {"_id": _oid(issue_id, label="issue_id"), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def save_paper(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    paper_type: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> dict[str, Any]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    kind = str(paper_type or "").strip().lower()
    if kind not in REVIEW_PAPER_TYPES:
        raise ReviewStoreError(f"Invalid working paper type: {paper_type}")
    payload = content if isinstance(content, (bytes, bytearray)) else bytes(content or b"")
    digest = hashlib.sha256(payload).hexdigest()
    now = utcnow()
    actor = _actor_id(user)
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "engagement_id": engagement_id,
        "type": kind,
        "status": "draft",
        "immutable": False,
        "filename": str(filename or f"{kind}.xlsx")[:200],
        "content_type": str(content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "byte_size": len(payload),
        "content_hash": digest,
        "generator_version": REVIEW_PAPER_GENERATOR_VERSION,
        "content": Binary(payload),
        "generated_at": now,
        "generated_by": actor,
        "closed_at": None,
        "closed_by": None,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(REVIEW_PAPERS_COLLECTION).insert_one(doc)
    meta = _strip_content(doc) or {}
    meta["download_path"] = f"/api/v1/officemitra/review/working-papers/{meta['id']}/download"
    return meta


async def list_papers(*, tenant_id: str, engagement_id: str) -> list[dict[str, Any]]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    cursor = (
        get_collection(REVIEW_PAPERS_COLLECTION)
        .find({"tenant_id": tenant_id, "engagement_id": engagement_id})
        .sort("generated_at", -1)
        .limit(100)
    )
    items = []
    async for doc in cursor:
        meta = _strip_content(doc)
        if meta:
            meta["download_path"] = f"/api/v1/officemitra/review/working-papers/{meta['id']}/download"
            items.append(meta)
    return items


async def get_paper(
    *,
    tenant_id: str,
    paper_id: str,
    include_content: bool = False,
) -> dict[str, Any] | None:
    await ensure_indexes()
    doc = await get_collection(REVIEW_PAPERS_COLLECTION).find_one(
        {"_id": _oid(paper_id, label="paper_id"), "tenant_id": tenant_id}
    )
    if not doc:
        return None
    if include_content:
        out = serialize_doc({k: v for k, v in doc.items() if k != "content"}) or {}
        raw = doc.get("content")
        out["content"] = bytes(raw) if raw is not None else b""
        return out
    meta = _strip_content(doc) or {}
    meta["download_path"] = f"/api/v1/officemitra/review/working-papers/{meta['id']}/download"
    return meta


async def close_paper(*, tenant_id: str, paper_id: str, user: dict[str, Any]) -> dict[str, Any]:
    paper = await get_paper(tenant_id=tenant_id, paper_id=paper_id, include_content=False)
    if paper is None:
        raise ReviewNotFoundError(f"Working paper not found: {paper_id}")
    if paper.get("immutable") or str(paper.get("status") or "") == "final":
        raise ReviewImmutableError("Working paper is already closed")
    now = utcnow()
    actor = _actor_id(user)
    await get_collection(REVIEW_PAPERS_COLLECTION).update_one(
        {"_id": _oid(paper_id, label="paper_id"), "tenant_id": tenant_id},
        {
            "$set": {
                "status": "final",
                "immutable": True,
                "closed_at": now,
                "closed_by": actor,
                "updated_at": now,
            }
        },
    )
    updated = await get_paper(tenant_id=tenant_id, paper_id=paper_id, include_content=False)
    return updated or {}


async def create_note(
    *,
    tenant_id: str,
    engagement_id: str,
    user: dict[str, Any],
    description: str,
    issue_id: str | None = None,
    assigned_to: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    text = str(description or "").strip()
    if not text:
        raise ReviewStoreError("description is required")
    assignee = str(assigned_to or "").strip() or None
    now = utcnow()
    actor = _actor_id(user)
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "engagement_id": engagement_id,
        "issue_id": str(issue_id).strip() if issue_id else None,
        "task_id": str(task_id).strip() if task_id else None,
        "description": text[:4000],
        "assigned_to": assignee,
        "status": "assigned" if assignee else "open",
        "ca_document_id": None,
        "created_at": now,
        "updated_at": now,
        "created_by": actor,
        "updated_by": actor,
    }
    await get_collection(REVIEW_NOTES_COLLECTION).insert_one(doc)
    return serialize_doc(doc) or {}


async def list_notes(*, tenant_id: str, engagement_id: str) -> list[dict[str, Any]]:
    await ensure_indexes()
    engagement = await get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
    if engagement is None:
        raise ReviewNotFoundError(f"Engagement not found: {engagement_id}")
    cursor = (
        get_collection(REVIEW_NOTES_COLLECTION)
        .find({"tenant_id": tenant_id, "engagement_id": engagement_id})
        .sort("updated_at", -1)
        .limit(200)
    )
    items = [serialize_doc(doc) async for doc in cursor]
    return [item for item in items if item]


async def get_note(*, tenant_id: str, note_id: str) -> dict[str, Any] | None:
    await ensure_indexes()
    doc = await get_collection(REVIEW_NOTES_COLLECTION).find_one(
        {"_id": _oid(note_id, label="note_id"), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def update_note(
    *,
    tenant_id: str,
    note_id: str,
    user: dict[str, Any],
    updates: dict[str, Any],
) -> dict[str, Any]:
    existing = await get_note(tenant_id=tenant_id, note_id=note_id)
    if existing is None:
        raise ReviewNotFoundError(f"Review note not found: {note_id}")
    payload: dict[str, Any] = {}
    if "status" in updates and updates["status"] is not None:
        status = str(updates["status"] or "").strip().lower()
        if status not in REVIEW_NOTE_STATUSES:
            raise ReviewStoreError(f"Invalid note status: {status}")
        payload["status"] = status
    if "assigned_to" in updates:
        payload["assigned_to"] = str(updates["assigned_to"] or "").strip() or None
        if payload["assigned_to"] and existing.get("status") == "open":
            payload.setdefault("status", "assigned")
    if "task_id" in updates and updates["task_id"]:
        payload["task_id"] = str(updates["task_id"]).strip()
    if "ca_document_id" in updates:
        linked = str(updates["ca_document_id"] or "").strip()
        payload["ca_document_id"] = linked or None
    if not payload:
        return existing
    payload["updated_at"] = utcnow()
    payload["updated_by"] = _actor_id(user)
    await get_collection(REVIEW_NOTES_COLLECTION).update_one(
        {"_id": _oid(note_id, label="note_id"), "tenant_id": tenant_id},
        {"$set": payload},
    )
    updated = await get_note(tenant_id=tenant_id, note_id=note_id)
    return updated or {}
