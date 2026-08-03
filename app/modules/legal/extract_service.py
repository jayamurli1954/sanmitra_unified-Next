"""LegalMitra P2 — matter-paper extracts, chunks, retention, and custody write gates.

Intelligence comes from approved extracts/chunks (source_kind=matter_paper), not hot full PDFs.
Chamber Connector (P3) and deep LAN retrieve (P4) are out of scope here.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal import custody_service
from app.modules.legal.practice_schemas import DocCustodyMode

LEGAL_MATTER_EXTRACTS_COLLECTION = "legal_matter_extracts"
LEGAL_MATTER_CHUNKS_COLLECTION = "legal_matter_chunks"
LEGAL_MATTER_DOCUMENTS_COLLECTION = "legal_matter_documents"
LEGAL_MATTERS_COLLECTION = "legal_matters"

SOURCE_KIND_MATTER_PAPER = "matter_paper"
DEFAULT_APP_KEY = "legalmitra"
MAX_EXTRACT_CHARS = 80_000
CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 150


class ExtractValidationError(Exception):
    """Invalid extract ingest or custody gate failure."""


class ExtractNotFoundError(Exception):
    """Extract or linked document not found in tenant scope."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


def _serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out


def hash_text(text: str) -> str:
    normalized = (text or "").strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def chunk_text(text: str, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        chunks.append(clean[start:end].strip())
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def suggest_case_card_fields(extract_text: str) -> dict[str, Any]:
    """Heuristic, local suggestions only — never silent overwrite of advocate fields."""
    text = extract_text or ""
    suggestions: dict[str, Any] = {}
    case_match = re.search(
        r"(?:Case\s*(?:No\.?|Number)|W\.?P\.?|Crl\.?\s*A\.?|O\.?S\.?)\s*[:\-]?\s*([A-Za-z0-9/\-\.]+)",
        text,
        re.IGNORECASE,
    )
    if case_match:
        suggestions["case_number"] = case_match.group(1).strip()[:120]

    court_match = re.search(
        r"(Supreme Court of India|High Court of [A-Za-z .]+|[A-Za-z .]+ High Court)",
        text,
        re.IGNORECASE,
    )
    if court_match:
        suggestions["court"] = court_match.group(1).strip()[:160]

    issues: list[str] = []
    for label in ("limitation", "jurisdiction", "quash", "injunction", "GST", "Section"):
        if re.search(rf"\b{re.escape(label)}\b", text, re.IGNORECASE):
            issues.append(label)
    if issues:
        suggestions["issues"] = issues[:8]

    opposite = re.search(
        r"(?:v\.|vs\.?|versus)\s+([A-Z][A-Za-z0-9 .,&]{2,80})",
        text,
    )
    if opposite:
        suggestions["opposite_party"] = opposite.group(1).strip()[:160]

    return suggestions


async def ensure_extract_indexes() -> None:
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    chunks = get_collection(LEGAL_MATTER_CHUNKS_COLLECTION)
    await extracts.create_index([("tenant_id", 1), ("app_key", 1), ("extract_id", 1)], unique=True)
    await extracts.create_index([("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("created_at", -1)])
    await extracts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("content_hash", 1)],
        unique=True,
        partialFilterExpression={"content_hash": {"$type": "string"}},
    )
    await extracts.create_index([("tenant_id", 1), ("app_key", 1), ("expires_at", 1)])
    await chunks.create_index([("tenant_id", 1), ("app_key", 1), ("chunk_id", 1)], unique=True)
    await chunks.create_index([("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("extract_id", 1)])
    await chunks.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("source_kind", 1), ("approval_status", 1)]
    )


async def assert_text_extract_allowed(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    """P2.1: both modes may store extracts/metadata; binary originals are gated separately."""
    return await custody_service.get_custody_settings(tenant_id=tenant_id, app_key=app_key)


async def assert_cloud_original_allowed(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    """P2.8: Mode A + opt-in only. Mode B always rejected."""
    settings = await custody_service.get_custody_settings(tenant_id=tenant_id, app_key=app_key)
    mode = settings.get("doc_custody_mode")
    if mode == DocCustodyMode.CHAMBER_LAN.value:
        raise ExtractValidationError(
            "Chamber LAN rejects full PDF/binary upload to cloud. Keep originals on the chamber server; push extracts only (Connector is P3)."
        )
    if mode != DocCustodyMode.CLOUD_MINIMIZED.value:
        raise ExtractValidationError("Cloud originals require Personal Practice custody mode.")
    if not settings.get("doc_cloud_originals_opt_in"):
        raise ExtractValidationError(
            "Cloud originals are opt-in only. Enable doc_cloud_originals_opt_in in custody settings first."
        )
    return settings


async def assert_external_provider_allowed(
    *,
    tenant_id: str,
    app_key: str,
    authorize_external_provider: bool,
) -> None:
    """P2.7: fail closed unless explicit user authorization on this request."""
    if not authorize_external_provider:
        raise ExtractValidationError(
            "External AI for matter extracts is fail-closed. Pass authorize_external_provider=true after user consent, or use local heuristics."
        )
    # Tenant-wide policy hook (planned): when a dedicated flag exists, enforce it here.
    _ = await custody_service.get_custody_settings(tenant_id=tenant_id, app_key=app_key)


async def _get_document(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    document_id: str,
) -> dict[str, Any]:
    documents = get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION)
    doc = await documents.find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "document_id": document_id,
        }
    )
    if not doc:
        raise ExtractNotFoundError("Document not found for this matter")
    return doc


async def ingest_matter_extract(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    document_id: str,
    actor_id: str,
    extract_text: str,
    approve: bool = False,
    authorize_external_provider: bool = False,
) -> dict[str, Any]:
    """P2.1 + P2.3 + P2.5: paste/text ingest → extract + chunks; hash dedupe."""
    await assert_text_extract_allowed(tenant_id=tenant_id, app_key=app_key)
    if authorize_external_provider:
        # P2 MVP uses local heuristics only; still require explicit auth flag if caller asks for external path.
        await assert_external_provider_allowed(
            tenant_id=tenant_id,
            app_key=app_key,
            authorize_external_provider=True,
        )

    text = (extract_text or "").strip()
    if not text:
        raise ExtractValidationError("extract_text is required")
    if len(text) > MAX_EXTRACT_CHARS:
        raise ExtractValidationError(f"extract_text exceeds {MAX_EXTRACT_CHARS} characters")

    await _get_document(
        tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, document_id=document_id
    )
    await ensure_extract_indexes()

    content_hash = hash_text(text)
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    existing = await extracts.find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "content_hash": content_hash,
        }
    )
    if existing:
        await get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION).update_one(
            {
                **_scope(tenant_id=tenant_id, app_key=app_key),
                "document_id": document_id,
            },
            {"$set": {"extract_status": "done", "content_hash": content_hash}},
        )
        return {
            "deduped": True,
            "extract": _serialize(existing),
            "chunks": await list_matter_chunks(
                tenant_id=tenant_id,
                app_key=app_key,
                matter_id=matter_id,
                extract_id=existing["extract_id"],
                approved_only=False,
                limit=200,
            ),
            "suggestions": suggest_case_card_fields(text),
        }

    settings = await custody_service.get_custody_settings(tenant_id=tenant_id, app_key=app_key)
    retention_days = int(settings.get("extract_retention_days") or 365)
    now = _now()
    expires_at = now + timedelta(days=retention_days)
    approval_status = "approved" if approve else "draft"
    extract_id = str(uuid4())
    extract_doc = {
        "extract_id": extract_id,
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter_id,
        "document_id": document_id,
        "source_kind": SOURCE_KIND_MATTER_PAPER,
        "content_hash": content_hash,
        "extract_text": text,
        "approval_status": approval_status,
        "retention_tier": "warm",
        "expires_at": expires_at,
        "provider_used": "none",
        "created_by": actor_id,
        "created_at": now,
        "approved_by": actor_id if approve else None,
        "approved_at": now if approve else None,
        "human_review_required": not approve,
    }
    await extracts.insert_one(extract_doc)

    chunks_col = get_collection(LEGAL_MATTER_CHUNKS_COLLECTION)
    chunk_rows: list[dict[str, Any]] = []
    for idx, piece in enumerate(chunk_text(text)):
        row = {
            "chunk_id": str(uuid4()),
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "document_id": document_id,
            "extract_id": extract_id,
            "source_kind": SOURCE_KIND_MATTER_PAPER,
            "chunk_index": idx,
            "text": piece,
            "token_count": max(1, len(piece.split())),
            "approval_status": approval_status,
            "expires_at": expires_at,
            "created_at": now,
        }
        chunk_rows.append(row)
        await chunks_col.insert_one(row)

    await get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION).update_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "document_id": document_id,
        },
        {"$set": {"extract_status": "done", "content_hash": content_hash}},
    )

    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=actor_id,
            product=app_key or DEFAULT_APP_KEY,
            action="legal_matter_extract_ingested",
            entity_type="legal_matter_extract",
            entity_id=extract_id,
            new_value={
                "matter_id": matter_id,
                "document_id": document_id,
                "chunk_count": len(chunk_rows),
                "approval_status": approval_status,
                "deduped": False,
            },
        )
    except Exception:
        pass

    return {
        "deduped": False,
        "extract": _serialize(extract_doc),
        "chunks": [_serialize(c) for c in chunk_rows],
        "suggestions": suggest_case_card_fields(text),
    }


async def list_matter_extracts(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    await ensure_extract_indexes()
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    rows = await (
        extracts.find({**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id})
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    return [_serialize(doc) or {} for doc in rows]


async def list_matter_chunks(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    extract_id: str | None = None,
    approved_only: bool = True,
    limit: int = 100,
) -> list[dict[str, Any]]:
    await ensure_extract_indexes()
    flt: dict[str, Any] = {
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter_id,
        "source_kind": SOURCE_KIND_MATTER_PAPER,
    }
    if extract_id:
        flt["extract_id"] = extract_id
    if approved_only:
        flt["approval_status"] = "approved"
    chunks = get_collection(LEGAL_MATTER_CHUNKS_COLLECTION)
    rows = await chunks.find(flt).sort("chunk_index", 1).limit(limit).to_list(length=limit)
    return [_serialize(doc) or {} for doc in rows]


async def approve_extract(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    extract_id: str,
    actor_id: str,
) -> dict[str, Any]:
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    extract = await extracts.find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "extract_id": extract_id,
        }
    )
    if not extract:
        raise ExtractNotFoundError("Extract not found")
    now = _now()
    await extracts.update_one(
        {"extract_id": extract_id, **_scope(tenant_id=tenant_id, app_key=app_key)},
        {
            "$set": {
                "approval_status": "approved",
                "approved_by": actor_id,
                "approved_at": now,
                "human_review_required": False,
            }
        },
    )
    await get_collection(LEGAL_MATTER_CHUNKS_COLLECTION).update_many(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "extract_id": extract_id,
        },
        {"$set": {"approval_status": "approved"}},
    )
    refreshed = await extracts.find_one(
        {"extract_id": extract_id, **_scope(tenant_id=tenant_id, app_key=app_key)}
    )
    return _serialize(refreshed) or {}


async def suggest_case_card(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    extract_id: str,
) -> dict[str, Any]:
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    extract = await extracts.find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "extract_id": extract_id,
        }
    )
    if not extract:
        raise ExtractNotFoundError("Extract not found")
    suggestions = suggest_case_card_fields(str(extract.get("extract_text") or ""))
    return {
        "extract_id": extract_id,
        "matter_id": matter_id,
        "suggestions": suggestions,
        "human_review_required": True,
        "advisory_notice": "Suggestions are heuristic only. An advocate must review before apply.",
    }


async def apply_case_card_suggestions(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    extract_id: str,
    actor_id: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """P2.2: apply only explicitly requested fields — never silent overwrite."""
    from app.modules.legal import practice_service
    from app.modules.legal.practice_schemas import MatterUpdateRequest

    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    extract = await extracts.find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "matter_id": matter_id,
            "extract_id": extract_id,
        }
    )
    if not extract:
        raise ExtractNotFoundError("Extract not found")

    allowed = {"case_number", "issues", "court", "opposite_party", "jurisdiction"}
    payload_data = {k: v for k, v in (fields or {}).items() if k in allowed and v is not None}
    if not payload_data:
        raise ExtractValidationError("No applyable case-card fields provided")

    payload = MatterUpdateRequest(**payload_data)
    updated = await practice_service.update_matter(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        updated_by=actor_id,
        payload=payload,
    )
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=actor_id,
            product=app_key or DEFAULT_APP_KEY,
            action="legal_matter_case_card_applied_from_extract",
            entity_type="legal_matter",
            entity_id=matter_id,
            new_value={"extract_id": extract_id, "fields": list(payload_data.keys())},
        )
    except Exception:
        pass
    return updated


async def retention_dry_run(
    *,
    tenant_id: str,
    app_key: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """P2.6: preview extracts/chunks past expires_at (no delete)."""
    await ensure_extract_indexes()
    now = now or _now()
    extracts = get_collection(LEGAL_MATTER_EXTRACTS_COLLECTION)
    chunks = get_collection(LEGAL_MATTER_CHUNKS_COLLECTION)
    expired_extracts = await extracts.find(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "expires_at": {"$lte": now}}
    ).limit(200).to_list(length=200)
    extract_hits = [
        {
            "extract_id": doc.get("extract_id"),
            "matter_id": doc.get("matter_id"),
            "document_id": doc.get("document_id"),
            "expires_at": doc.get("expires_at"),
            "retention_tier": doc.get("retention_tier"),
        }
        for doc in expired_extracts
    ]
    expired_chunks = await chunks.find(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "expires_at": {"$lte": now}}
    ).limit(500).to_list(length=500)
    return {
        "dry_run": True,
        "as_of": now,
        "expired_extract_count": len(extract_hits),
        "expired_chunk_count": len(expired_chunks),
        "expired_extracts": extract_hits,
        "advisory_notice": "Dry-run only. Case cards are hot-tier and are not purged by this job.",
    }


async def reject_binary_original_upload(*, tenant_id: str, app_key: str) -> None:
    """Convenience gate for any binary/original route (P2.8 / Mode B fail-closed)."""
    await assert_cloud_original_allowed(tenant_id=tenant_id, app_key=app_key)
