"""Business Credit Notes (sales-side GST adjustment).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Imported via the service.py facade (which re-exports the public functions), so
the shared symbols below resolve from the fully-initialised service module.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    initialize_default_chart_of_accounts,
    post_journal_entry,
    reverse_journal_entry,
)
from app.db.mongo import get_collection
from app.modules.business.dimensions import validate_dimension_refs
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    CreditNoteCancelRequest,
    CreditNoteCreateRequest,
)
from app.modules.business.service import (
    CREDIT_NOTES_COLLECTION,
    OUTPUT_CGST_CODE,
    OUTPUT_IGST_CODE,
    OUTPUT_SGST_CODE,
    SALES_RECEIVABLE_CODE,
    _apply_approval_defaults,
    _audit_business_event,
    _compute_invoice_lines,
    _json_safe_doc,
    _now,
    _period_key,
    _period_label,
    _reserve_sequence_number,
    _resolve_voucher_account_id,
    _reverse_after_domain_persistence_failure,
    _validate_reversal_period,
    get_party,
    is_gst_period_locked,
)


def _credit_note_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    _apply_approval_defaults(result)
    result.setdefault("created", created)
    return result


async def list_credit_notes(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    approval_status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    if status:
        filters["status"] = status
    if approval_status:
        filters["approval_status"] = approval_status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(CREDIT_NOTES_COLLECTION)
        .find(filters)
        .sort("note_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_credit_note_response_doc(row) for row in rows], "total": len(rows)}


async def get_credit_note(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    credit_note_id: str,
) -> dict | None:
    row = await get_collection(CREDIT_NOTES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "credit_note_id": credit_note_id}
    )
    return _credit_note_response_doc(row) if row else None


async def review_credit_note(
    *,
    session: AsyncSession | None,
    tenant_id: str,
    app_key: str,
    credit_note_id: str,
    reviewed_by: str,
    payload: ApprovalReviewRequest,
) -> dict:
    notes = get_collection(CREDIT_NOTES_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "credit_note_id": credit_note_id,
    }
    note = await notes.find_one(filters)
    if note is None:
        raise AccountingNotFoundError("Credit note not found")
    old_value = _credit_note_response_doc(note)
    current_status = str(note.get("status") or "").strip().lower()
    if current_status in {"draft", "pending_approval"}:
        if current_status == "draft":
            raise AccountingValidationError("Only submitted credit notes can be approved or rejected")
        if payload.approve:
            return await _approve_credit_note_document(
                session=session,
                tenant_id=tenant_id,
                app_key=app_key,
                reviewed_by=reviewed_by,
                note=note,
                old_value=old_value,
                approval_notes=payload.notes,
            )
        approval_status = "rejected"
        patch = {
            "status": "rejected",
            "approval_required": True,
            "approval_status": approval_status,
            "approval_decided_at": _now(),
            "approval_decided_by": reviewed_by,
            "approval_notes": payload.notes,
            "rejection_reason": payload.rejection_reason or "Rejected during manual review",
            "updated_at": _now(),
        }
        if note.get("approval_submitted_at") is None:
            patch["approval_submitted_at"] = note.get("created_at")
            patch["approval_submitted_by"] = note.get("created_by")
        await notes.update_one(filters, {"$set": patch})
        note.update(patch)
        result = _credit_note_response_doc(note)
        await _audit_business_event(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=reviewed_by,
            action="business_credit_note_reviewed",
            entity_type="business_credit_note",
            entity_id=credit_note_id,
            old_value=old_value,
            new_value=result,
        )
        return result
    if current_status != "posted":
        raise AccountingValidationError("Only posted or pending-approval credit notes can be reviewed")

    approval_status = "approved" if payload.approve else "rejected"
    patch = {
        "approval_required": True,
        "approval_status": approval_status,
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": payload.notes,
        "rejection_reason": None if payload.approve else (payload.rejection_reason or "Rejected during manual review"),
        "updated_at": _now(),
    }
    if note.get("approval_submitted_at") is None:
        patch["approval_submitted_at"] = note.get("created_at")
        patch["approval_submitted_by"] = note.get("created_by")

    await notes.update_one(filters, {"$set": patch})
    note.update(patch)
    result = _credit_note_response_doc(note)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_credit_note_reviewed",
        entity_type="business_credit_note",
        entity_id=credit_note_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def _approve_credit_note_document(
    *,
    session: AsyncSession | None,
    tenant_id: str,
    app_key: str,
    reviewed_by: str,
    note: dict,
    old_value: dict,
    approval_notes: str | None,
) -> dict:
    if session is None:
        raise AccountingValidationError("Approval posting requires an active accounting session")
    credit_note_id = str(note.get("credit_note_id") or "")
    credit_note_number = str(note.get("credit_note_number") or credit_note_id)
    accounting_entity_id = str(note.get("accounting_entity_id") or "primary")
    customer_party_id = str(note.get("customer_party_id") or "")
    taxable_total = Decimal(str(note.get("taxable_total") or "0"))
    cgst_total = Decimal(str(note.get("cgst_total") or "0"))
    sgst_total = Decimal(str(note.get("sgst_total") or "0"))
    igst_total = Decimal(str(note.get("igst_total") or "0"))
    note_total = Decimal(str(note.get("note_total") or "0"))
    income_account_code = str(note.get("income_account_code") or "41001")

    receivable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=SALES_RECEIVABLE_CODE, side="receivable",
    )
    income_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=income_account_code, side="income",
    )
    journal_lines = [JournalLineIn(account_id=income_id, debit=taxable_total, credit=Decimal("0"))]
    for gst_amount, code in ((cgst_total, OUTPUT_CGST_CODE), (sgst_total, OUTPUT_SGST_CODE), (igst_total, OUTPUT_IGST_CODE)):
        if gst_amount > Decimal("0"):
            gst_account_id = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
                account_id=None, account_code=code, side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=gst_account_id, debit=gst_amount, credit=Decimal("0")))
    journal_lines.append(JournalLineIn(account_id=receivable_id, debit=Decimal("0"), credit=note_total, party_id=customer_party_id))

    ref_suffix = f" against {note.get('original_invoice_number')}" if note.get("original_invoice_number") else ""
    description = f"Credit Note {credit_note_number} - {note.get('customer_name') or customer_party_id}{ref_suffix}"
    notes = get_collection(CREDIT_NOTES_COLLECTION)
    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            payload=JournalPostRequest(
                entry_date=date.fromisoformat(str(note.get("note_date"))[:10]),
                description=description,
                reference=credit_note_number,
                source_module="business",
                source_document_type="credit_note",
                source_document_id=credit_note_id,
                lines=journal_lines,
            ),
            idempotency_key=f"credit-note:{credit_note_id}",
        )
    except Exception as exc:
        raise AccountingValidationError(f"Credit note approval posting failed: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_entry_id": journal_entry.id,
        "approval_required": True,
        "approval_status": "approved",
        "approval_submitted_at": note.get("approval_submitted_at") or note.get("created_at"),
        "approval_submitted_by": note.get("approval_submitted_by") or note.get("created_by"),
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": approval_notes or "Approved and posted",
        "rejection_reason": None,
        "updated_at": _now(),
    }
    try:
        await notes.update_one({"tenant_id": tenant_id, "app_key": app_key, "credit_note_id": credit_note_id}, {"$set": patch})
    except Exception as exc:
        await _reverse_after_domain_persistence_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            journal_entry_id=int(journal_entry.id),
            document_label="Credit note",
            document_id=credit_note_id,
            reversal_reason=f"Compensation after credit note approval persistence failure for {credit_note_number}",
            reversal_idempotency_key=f"credit-note-approve-compensate:{credit_note_id}:{journal_entry.id}",
        )
        raise AccountingValidationError(
            "Credit note approval persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    note.update(patch)
    result = _credit_note_response_doc(note, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=reviewed_by,
        action="business_credit_note_reviewed", entity_type="business_credit_note", entity_id=credit_note_id,
        old_value=old_value, new_value=result,
    )
    return result


async def create_credit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: CreditNoteCreateRequest,
    idempotency_key: str | None,
) -> dict:
    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    if idempotency_key:
        existing = await get_collection(CREDIT_NOTES_COLLECTION).find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "idempotency_key": idempotency_key}
        )
        if existing is not None:
            return _credit_note_response_doc(existing, created=False)

    customer = await get_party(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, party_id=payload.customer_party_id,
    )
    if customer is None:
        raise AccountingValidationError("Customer party not found for this tenant")

    # A credit note is posted in an open period; block if that month is finalised.
    if await is_gst_period_locked(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, period=_period_key(payload.note_date),
    ):
        raise AccountingValidationError(
            f"The {_period_label(_period_key(payload.note_date))} GST period is finalised and locked. Choose a date in an open period."
        )
    await validate_dimension_refs(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id,
        project_id=payload.project_id,
    )
    for item in payload.line_items:
        await validate_dimension_refs(
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            cost_centre_id=getattr(item, "cost_centre_id", None),
            project_id=getattr(item, "project_id", None),
        )

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, note_total = _compute_invoice_lines(payload)
    if note_total <= Decimal("0"):
        raise AccountingValidationError("Credit note total must be greater than zero")

    credit_note_id = str(uuid4())
    credit_note_number = await _reserve_sequence_number(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        doc_type="credit_note", prefix="CN", on_date=payload.note_date, fallback_collection=CREDIT_NOTES_COLLECTION,
    )
    now = _now()
    doc = {
        "credit_note_id": credit_note_id,
        "credit_note_number": credit_note_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "customer_party_id": payload.customer_party_id,
        "customer_name": customer.get("party_name"),
        "customer_gstin": customer.get("gstin"),
        "note_date": payload.note_date.isoformat(),
        "original_invoice_id": payload.original_invoice_id,
        "original_invoice_number": payload.original_invoice_number,
        "reason": payload.reason,
        "is_inter_state": payload.is_inter_state,
        "place_of_supply": payload.place_of_supply,
        "income_account_code": payload.income_account_code,
        "notes": payload.notes,
        "line_items": lines,
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "note_total": str(note_total),
        "status": "draft" if payload.save_as_draft else "pending_approval",
        "approval_required": True,
        "approval_status": "not_submitted" if payload.save_as_draft else "pending_approval",
        "approval_submitted_at": None if payload.save_as_draft else now,
        "approval_submitted_by": None if payload.save_as_draft else created_by,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    credit_notes = get_collection(CREDIT_NOTES_COLLECTION)
    await credit_notes.insert_one(doc)
    result = _credit_note_response_doc(doc, created=True)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_credit_note_created", entity_type="business_credit_note", entity_id=credit_note_id, new_value=result,
    )
    return result


async def cancel_credit_note(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    credit_note_id: str,
    created_by: str,
    payload: CreditNoteCancelRequest,
    idempotency_key: str | None,
) -> dict:
    credit_notes = get_collection(CREDIT_NOTES_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "credit_note_id": credit_note_id}
    note = await credit_notes.find_one(filters)
    if note is None:
        raise AccountingNotFoundError("Credit note not found")
    if note.get("status") == "cancelled" and note.get("reversal_journal_entry_id"):
        return _credit_note_response_doc(note, created=False)
    journal_entry_id = note.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Credit note is not linked to a posted journal entry")
    if note.get("status") != "posted":
        raise AccountingValidationError("Only posted credit notes can be reversed")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        original_date=note.get("note_date"), reversal_date=reversal_date, document_label="credit note",
    )

    old_note = _credit_note_response_doc(note)
    reversal, created = await reverse_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by, journal_id=int(journal_entry_id), reversal_date=reversal_date,
        reason=payload.reason, idempotency_key=idempotency_key or f"credit-note-cancel:{credit_note_id}",
    )
    update = {
        "status": "cancelled",
        "reversal_journal_entry_id": reversal.id,
        "cancel_reason": payload.reason,
        "cancelled_at": _now(),
        "updated_at": _now(),
    }
    await credit_notes.update_one(filters, {"$set": update})
    note.update(update)
    result = _credit_note_response_doc(note, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_credit_note_cancelled", entity_type="business_credit_note", entity_id=credit_note_id,
        old_value=old_note, new_value=result,
    )
    return result
