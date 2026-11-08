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
from app.modules.business.capture.classify import classify
from app.modules.business.capture.extract import extract_document
from app.modules.business.capture.routing import resolve_client_binding

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

    # Classify the document and derive its accounting treatment (ITC/RCM, registered
    # vs unregistered/no-GSTIN). Bind the client — channel-bound here; never guessed.
    classification = classify(document_type_hint=extraction.get("document_type"), fields=fields)
    binding = resolve_client_binding(provided_entity=accounting_entity_id)

    checks = validators.validate(fields)
    passed = validators.all_passed(checks) and bool(extraction.get("extracted"))
    score = scoring.blended_score(confidences, validation_passed=passed)
    # A document with no bound client can never draft or post — it waits for a human.
    if binding["method"] == "needs_client":
        status = models.STATUS_NEEDS_CLIENT
    else:
        status = scoring.routed_status(score, validation_passed=passed)

    updated = await store.update(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id,
        updates={
            "status": status,
            "doc_kind": classification["doc_type"],
            "treatment": classification["treatment"],
            "registration_status": classification["registration_status"],
            "itc_eligible": classification["itc_eligible"],
            "possible_rcm": classification["possible_rcm"],
            "client_binding_method": binding["method"],
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
            "doc_kind": classification["doc_type"],
            "treatment": classification["treatment"],
            "possible_rcm": classification["possible_rcm"],
            "client_binding_method": binding["method"],
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


_MATERIALIZABLE = {models.STATUS_DRAFTED, models.STATUS_NEEDS_REVIEW}
_PURCHASE_KINDS = {"purchase_bill", "expense_voucher"}


def _as_date(value):
    import datetime as _dt

    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _synth_line(fields: dict[str, Any]) -> dict[str, Any]:
    """One purchase-bill line from the captured fields. The reviewer verifies the
    DRAFT bill in MitraBooks afterwards, so a single synthesized line is fine."""
    from decimal import Decimal, InvalidOperation

    def _dec(v, default="0"):
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal(default)

    taxable = _dec(fields.get("taxable_value"), "0")
    total = _dec(fields.get("total_amount"), "0")
    tax = _dec(fields.get("tax_amount"), "0")
    base = taxable if taxable > 0 else total
    gst_rate = Decimal("0")
    if taxable > 0 and tax > 0:
        gst_rate = (tax / taxable * Decimal("100")).quantize(Decimal("0.01"))
        if gst_rate > Decimal("100"):
            gst_rate = Decimal("0")
    desc = "Imported from captured document"
    raw_lines = fields.get("line_items")
    if isinstance(raw_lines, list) and raw_lines and isinstance(raw_lines[0], dict):
        d = str(raw_lines[0].get("description") or "").strip()
        if d:
            desc = d[:300]
    return {"description": desc, "quantity": Decimal("1"), "rate": base, "gst_rate": gst_rate}


async def materialize_capture(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    capture_id: str,
    vendor_party_id: str,
    is_inter_state: bool = False,
    is_reverse_charge: bool | None = None,
    expense_account_code: str = "51001",
    bill_number: str | None = None,
    bill_date: str | None = None,
    actor: str,
) -> dict[str, Any]:
    """Turn an approved CaptureItem into a DRAFT purchase bill in the right client's
    books. It creates a draft only — the human posts it through the normal purchase-
    bill approval flow, so capture never writes to the ledger itself. Idempotent per
    capture_id. Purchase-type documents only in this slice."""
    import datetime as _dt

    from app.modules.business.schemas import PurchaseBillCreateRequest

    item = await store.get(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id
    )
    if item is None:
        raise CaptureError(f"Capture item not found: {capture_id}")
    if item.get("status") == models.STATUS_MATERIALIZED and item.get("linked_document_id"):
        return {"item": item, "document": None, "already_materialized": True}
    if item.get("status") not in _MATERIALIZABLE:
        raise CaptureError(f"Capture item is not ready to materialize (status: {item.get('status')})")
    if item.get("client_binding_method") == "needs_client":
        raise CaptureError("Assign a client to this document before materializing")
    if str(item.get("doc_kind") or "") not in _PURCHASE_KINDS:
        raise CaptureError("Only purchase bills can be materialized in this slice")

    fields = item.get("extracted_fields") or {}
    rcm = bool(item.get("possible_rcm")) if is_reverse_charge is None else bool(is_reverse_charge)
    payload = PurchaseBillCreateRequest(
        vendor_party_id=vendor_party_id,
        bill_number=(bill_number or str(fields.get("invoice_number") or "").strip() or f"CAP-{capture_id[:8]}")[:120],
        bill_date=_as_date(bill_date) or _as_date(fields.get("invoice_date")) or _dt.date.today(),
        is_inter_state=bool(is_inter_state),
        is_reverse_charge=rcm,
        expense_account_code=expense_account_code or "51001",
        line_items=[_synth_line(fields)],
        save_as_draft=True,  # land as a DRAFT; the human posts via the normal flow
        accounting_entity_id=accounting_entity_id,
    )

    from app.modules.business.services.purchase_bills import create_purchase_bill

    bill = await create_purchase_bill(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        created_by=actor,
        payload=payload,
        idempotency_key=f"capture:{capture_id}",
    )

    updated = await store.update(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, capture_id=capture_id,
        updates={
            "status": models.STATUS_MATERIALIZED,
            "linked_document_type": "purchase_bill",
            "linked_document_id": bill.get("bill_id"),
            "linked_document_number": bill.get("bill_number"),
        },
    )
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=actor,
        product=app_key,
        action="business.capture.materialize",
        entity_type="capture_item",
        entity_id=capture_id,
        new_value={
            "accounting_entity_id": accounting_entity_id,
            "linked_document_type": "purchase_bill",
            "linked_document_id": bill.get("bill_id"),
            "bill_number": bill.get("bill_number"),
            "status": bill.get("status"),
        },
    )
    return {"item": updated, "document": bill, "already_materialized": False}


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
