"""Capture pipeline orchestration: capture -> extract -> validate -> score -> route.

Phase 1: produces draft CaptureItems only (status drafted | needs_review). It does
NOT post to the ledger — materializing an approved capture into a typed purchase
bill is a later slice. Every item is tenant/app/entity scoped and audited.

Extraction runs through a pluggable backend (default: open-source Tesseract OCR +
rules, no API key). The service only rasterizes the upload into page images; it is
engine-agnostic.
"""
from __future__ import annotations

from typing import Any

from app.core.audit.service import log_audit_event
from app.modules.business.capture import models, scoring, store, validators
from app.modules.business.capture.backends.base import PageImage
from app.modules.business.capture.extract import extract_document

MAX_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 3
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


class CaptureError(ValueError):
    pass


def _to_page_images(raw: bytes, media_type: str) -> list[PageImage]:
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt in _IMAGE_TYPES:
        normalized = "image/jpeg" if mt == "image/jpg" else mt
        return [PageImage(media_type=normalized, data=raw)]
    if mt == "application/pdf":
        return _rasterize_pdf(raw)
    raise CaptureError(f"Unsupported document type: {mt or 'unknown'} (use PNG, JPEG, WEBP or PDF)")


def _rasterize_pdf(raw: bytes) -> list[PageImage]:
    try:
        import pypdfium2 as pdfium  # lazy: optional dependency
    except Exception as exc:  # pragma: no cover - environment dependent
        raise CaptureError("PDF support requires pypdfium2 on the server") from exc
    import io

    pages: list[PageImage] = []
    pdf = pdfium.PdfDocument(raw)
    try:
        for i in range(min(len(pdf), MAX_PDF_PAGES)):
            pil = pdf[i].render(scale=2.0).to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            pages.append(PageImage(media_type="image/png", data=buf.getvalue()))
    finally:
        pdf.close()
    if not pages:
        raise CaptureError("PDF had no renderable pages")
    return pages


async def ingest_upload(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    raw: bytes,
    media_type: str,
    filename: str,
    created_by: str,
) -> dict[str, Any]:
    if not raw:
        raise CaptureError("Uploaded file is empty")
    if len(raw) > MAX_BYTES:
        raise CaptureError("File exceeds the 10 MB limit")

    fingerprint = models.content_fingerprint(raw, source_ref=filename)
    existing = await store.find_by_fingerprint(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, fingerprint=fingerprint
    )
    if existing:
        return {"item": existing, "duplicate": True}

    pages = _to_page_images(raw, media_type)
    now = models.utcnow()
    capture_id = models.new_id()
    base_doc: dict[str, Any] = {
        "capture_id": capture_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "fingerprint": fingerprint,
        "source": "upload",
        "source_ref": filename,
        "status": models.STATUS_CAPTURED,
        "doc_kind": None,
        "extracted_fields": {},
        "field_confidences": {},
        "validation": [],
        "final_confidence": 0.0,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await store.insert(base_doc)

    extraction = await extract_document(tenant_id=tenant_id, pages=pages, user_id=created_by)

    fields = extraction.get("fields") or {}
    confidences = extraction.get("field_confidences") or {}
    checks = validators.validate(fields)
    passed = validators.all_passed(checks) and bool(extraction.get("extracted"))
    score = scoring.blended_score(confidences, validation_passed=passed)
    status = scoring.routed_status(score, validation_passed=passed)

    updated = await store.update(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id,
        updates={
            "status": status,
            "doc_kind": extraction.get("document_type"),
            "extracted_fields": fields,
            "field_confidences": confidences,
            "validation": checks,
            "final_confidence": score,
            "extracted": bool(extraction.get("extracted")),
            "engine": extraction.get("engine"),
            "extract_error_code": extraction.get("error_code"),
            "telemetry_id": extraction.get("telemetry_id"),
            "provider": extraction.get("provider"),
            "model": extraction.get("model"),
        },
    )

    await log_audit_event(
        tenant_id=tenant_id,
        user_id=created_by,
        product=app_key,
        action="business.capture.ingest",
        entity_type="capture_item",
        entity_id=capture_id,
        new_value={
            "accounting_entity_id": accounting_entity_id,
            "status": status,
            "final_confidence": score,
            "pages": len(pages),
            "engine": extraction.get("engine"),
            "extracted": bool(extraction.get("extracted")),
        },
    )
    return {"item": updated, "duplicate": False}


async def list_items(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, status: str | None = None, limit: int = 100
) -> dict[str, Any]:
    items = await store.list_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, status=status, limit=limit
    )
    return {"items": items, "total": len(items)}


async def get_item(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, capture_id: str
) -> dict[str, Any]:
    item = await store.get(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id
    )
    if item is None:
        raise CaptureError(f"Capture item not found: {capture_id}")
    return {"item": item}


async def reject_item(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, capture_id: str, reason: str, actor: str
) -> dict[str, Any]:
    item = await store.get(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id
    )
    if item is None:
        raise CaptureError(f"Capture item not found: {capture_id}")
    updated = await store.update(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id,
        updates={"status": models.STATUS_REJECTED, "reject_reason": reason[:500]},
    )
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=actor,
        product=app_key,
        action="business.capture.reject",
        entity_type="capture_item",
        entity_id=capture_id,
        new_value={"accounting_entity_id": accounting_entity_id, "reason": reason[:200]},
    )
    return {"item": updated}
