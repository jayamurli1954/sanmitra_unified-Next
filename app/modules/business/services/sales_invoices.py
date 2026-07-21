"""Business Sales Invoice documents (create / review / approve / cancel).

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
)
from app.modules.business.inventory import validate_item_refs
from app.modules.business.tds import compute_tcs
from app.modules.business import service as business_service
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    InvoiceSettings,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
)
from app.modules.business.service import (
    OUTPUT_CGST_CODE,
    OUTPUT_IGST_CODE,
    OUTPUT_SGST_CODE,
    SALES_INVOICES_COLLECTION,
    SALES_RECEIVABLE_CODE,
    TCS_PAYABLE_CODE,
    _audit_business_event,
    _compute_invoice_lines,
    _invoice_response_doc,
    _now,
    _validate_required_invoice_fields,
    _validate_reversal_period,
    get_gst_profile,
    get_invoice_settings,
    get_party,
)


async def list_sales_invoices(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    approval_status: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if status:
        filters["status"] = status
    if approval_status:
        filters["approval_status"] = approval_status
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await business_service.get_collection(SALES_INVOICES_COLLECTION)
        .find(filters)
        .sort("invoice_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_invoice_response_doc(row) for row in rows], "total": len(rows)}


async def get_sales_invoice(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    invoice_id: str,
) -> dict | None:
    row = await business_service.get_collection(SALES_INVOICES_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "invoice_id": invoice_id,
        }
    )
    return _invoice_response_doc(row) if row else None


async def review_sales_invoice(
    *,
    session: AsyncSession | None,
    tenant_id: str,
    app_key: str,
    invoice_id: str,
    reviewed_by: str,
    payload: ApprovalReviewRequest,
) -> dict:
    invoices = business_service.get_collection(SALES_INVOICES_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "invoice_id": invoice_id,
    }
    invoice = await invoices.find_one(filters)
    if invoice is None:
        raise AccountingNotFoundError("Sales invoice not found")
    old_value = _invoice_response_doc(invoice)
    current_status = str(invoice.get("status") or "").strip().lower()
    if current_status in {"draft", "pending_approval"}:
        if current_status == "draft":
            raise AccountingValidationError("Only submitted sales invoices can be approved or rejected")
        if payload.approve:
            return await _approve_sales_invoice_document(
                session=session,
                tenant_id=tenant_id,
                app_key=app_key,
                reviewed_by=reviewed_by,
                invoice=invoice,
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
        if invoice.get("approval_submitted_at") is None:
            patch["approval_submitted_at"] = invoice.get("created_at")
            patch["approval_submitted_by"] = invoice.get("created_by")
        await invoices.update_one(filters, {"$set": patch})
        invoice.update(patch)
        result = _invoice_response_doc(invoice)
        await _audit_business_event(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=reviewed_by,
            action="business_sales_invoice_reviewed",
            entity_type="business_sales_invoice",
            entity_id=invoice_id,
            old_value=old_value,
            new_value=result,
        )
        return result
    if current_status != "posted":
        raise AccountingValidationError("Only posted or pending-approval sales invoices can be reviewed")

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
    if invoice.get("approval_submitted_at") is None:
        patch["approval_submitted_at"] = invoice.get("created_at")
        patch["approval_submitted_by"] = invoice.get("created_by")

    await invoices.update_one(filters, {"$set": patch})
    invoice.update(patch)
    result = _invoice_response_doc(invoice)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_sales_invoice_reviewed",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def _approve_sales_invoice_document(
    *,
    session,
    tenant_id: str,
    app_key: str,
    reviewed_by: str,
    invoice: dict,
    old_value: dict,
    approval_notes: str | None,
) -> dict:
    if session is None:
        raise AccountingValidationError("Approval posting requires an active accounting session")
    invoice_id = str(invoice.get("invoice_id") or "")
    invoice_number = str(invoice.get("invoice_number") or invoice_id)
    accounting_entity_id = str(invoice.get("accounting_entity_id") or "primary")
    customer_party_id = str(invoice.get("customer_party_id") or "")
    taxable_total = Decimal(str(invoice.get("taxable_total") or "0"))
    cgst_total = Decimal(str(invoice.get("cgst_total") or "0"))
    sgst_total = Decimal(str(invoice.get("sgst_total") or "0"))
    igst_total = Decimal(str(invoice.get("igst_total") or "0"))
    grand_total = Decimal(str(invoice.get("grand_total") or invoice.get("invoice_total") or "0"))
    tcs_amount = Decimal(str(invoice.get("tcs_amount") or "0"))
    income_account_code = str(invoice.get("income_account_code") or "41001")

    receivable_id = await business_service._resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=SALES_RECEIVABLE_CODE, side="receivable",
    )
    income_id = await business_service._resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=income_account_code, side="income",
    )
    journal_lines = [
        JournalLineIn(account_id=receivable_id, debit=grand_total, credit=Decimal("0"), party_id=customer_party_id),
        JournalLineIn(account_id=income_id, debit=Decimal("0"), credit=taxable_total),
    ]
    if tcs_amount > Decimal("0"):
        tcs_payable_id = await business_service._resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            account_id=None, account_code=TCS_PAYABLE_CODE, side="TCS payable",
        )
        journal_lines.append(JournalLineIn(account_id=tcs_payable_id, debit=Decimal("0"), credit=tcs_amount))
    for gst_amount, code in ((cgst_total, OUTPUT_CGST_CODE), (sgst_total, OUTPUT_SGST_CODE), (igst_total, OUTPUT_IGST_CODE)):
        if gst_amount > Decimal("0"):
            gst_account_id = await business_service._resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
                account_id=None, account_code=code, side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=gst_account_id, debit=Decimal("0"), credit=gst_amount))

    description = f"Sales Invoice {invoice_number} - {invoice.get('customer_name') or customer_party_id}"
    invoices = business_service.get_collection(SALES_INVOICES_COLLECTION)
    try:
        journal_entry, created = await business_service.post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            payload=JournalPostRequest(
                entry_date=date.fromisoformat(str(invoice.get("invoice_date"))[:10]),
                description=description,
                reference=invoice_number,
                source_module="business",
                source_document_type="sales_invoice",
                source_document_id=invoice_id,
                lines=journal_lines,
            ),
            idempotency_key=f"sales-invoice:{invoice_id}",
        )
    except Exception as exc:
        raise AccountingValidationError(f"Sales invoice approval posting failed: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_entry_id": journal_entry.id,
        "approval_required": True,
        "approval_status": "approved",
        "approval_submitted_at": invoice.get("approval_submitted_at") or invoice.get("created_at"),
        "approval_submitted_by": invoice.get("approval_submitted_by") or invoice.get("created_by"),
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": approval_notes or "Approved and posted",
        "rejection_reason": None,
        "updated_at": _now(),
    }
    try:
        await invoices.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "invoice_id": invoice_id},
            {"$set": patch},
        )
    except Exception as exc:
        await business_service._reverse_after_domain_persistence_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            journal_entry_id=int(journal_entry.id),
            document_label="Sales invoice",
            document_id=invoice_id,
            reversal_reason=f"Compensation after sales invoice approval persistence failure for {invoice_number}",
            reversal_idempotency_key=f"sales-invoice-approve-compensate:{invoice_id}:{journal_entry.id}",
        )
        raise AccountingValidationError(
            "Sales invoice approval persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    invoice.update(patch)
    result = _invoice_response_doc(invoice, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_sales_invoice_reviewed",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def create_sales_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: SalesInvoiceCreateRequest,
    idempotency_key: str | None,
) -> dict:
    if app_key == "mitrabooks":
        await business_service.initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    if idempotency_key:
        existing = await business_service.get_collection(SALES_INVOICES_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            return _invoice_response_doc(existing, created=False)

    customer = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        party_id=payload.customer_party_id,
    )
    if customer is None:
        raise AccountingValidationError("Customer party not found for this tenant")

    settings = await get_invoice_settings(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
    )
    _validate_required_invoice_fields(payload, settings)

    await business_service.validate_dimension_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id, project_id=payload.project_id,
    )
    for item in payload.line_items:
        await business_service.validate_dimension_refs(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            cost_centre_id=getattr(item, "cost_centre_id", None),
            project_id=getattr(item, "project_id", None),
        )
    await validate_item_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        line_items=payload.line_items,
    )

    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
    )
    is_composition = profile["is_composition"]
    if is_composition and payload.is_inter_state:
        raise AccountingValidationError(
            "Composition dealers cannot make inter-state outward supplies. "
            "Issue an intra-state Bill of Supply only."
        )

    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, invoice_total = _compute_invoice_lines(
        payload, composition=is_composition,
    )
    if invoice_total <= Decimal("0"):
        raise AccountingValidationError("Invoice total must be greater than zero")

    # TCS (206C) is collected on the GST-inclusive consideration (Circular
    # 17/2020), so its base is the invoice total; the customer owes grand_total.
    tcs_rate = tcs_amount = None
    if payload.tcs_section:
        try:
            tcs_rate, tcs_amount = compute_tcs(payload.tcs_section, invoice_total, payload.tcs_rate)
        except ValueError as exc:
            raise AccountingValidationError(str(exc))
    grand_total = invoice_total + (tcs_amount or Decimal("0"))

    invoice_id = str(uuid4())
    numbering = InvoiceSettings(**{k: settings[k] for k in ("field_config", "numbering", "custom_fields", "branding") if k in settings}).numbering
    invoice_number = await business_service._reserve_invoice_number(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        invoice_date=payload.invoice_date,
        numbering=numbering,
    )
    now = _now()
    doc = {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "customer_party_id": payload.customer_party_id,
        "customer_name": customer.get("party_name"),
        "customer_gstin": customer.get("gstin"),
        "invoice_date": payload.invoice_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "is_inter_state": payload.is_inter_state,
        "place_of_supply": payload.place_of_supply,
        "income_account_code": payload.income_account_code,
        "document_type": "bill_of_supply" if is_composition else "tax_invoice",
        "is_composition": is_composition,
        "reference": payload.reference,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "invoice_total": str(invoice_total),
        "tcs_section": payload.tcs_section,
        "tcs_rate": str(tcs_rate) if tcs_rate is not None else None,
        "tcs_base_amount": str(invoice_total) if payload.tcs_section else None,
        "tcs_amount": str(tcs_amount) if tcs_amount is not None else "0",
        "grand_total": str(grand_total),
        "collectee_pan": customer.get("pan"),
        "collectee_pan_missing": bool(payload.tcs_section) and not customer.get("pan"),
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
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
    invoices = business_service.get_collection(SALES_INVOICES_COLLECTION)
    await invoices.insert_one(doc)
    result = _invoice_response_doc(doc, created=True)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_sales_invoice_created",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        new_value=result,
    )
    return result


async def cancel_sales_invoice(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    invoice_id: str,
    created_by: str,
    payload: SalesInvoiceCancelRequest,
    idempotency_key: str | None,
) -> dict:
    invoices = business_service.get_collection(SALES_INVOICES_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "invoice_id": invoice_id,
    }
    invoice = await invoices.find_one(filters)
    if invoice is None:
        raise AccountingNotFoundError("Sales invoice not found")

    if invoice.get("status") == "cancelled" and invoice.get("reversal_journal_entry_id"):
        return _invoice_response_doc(invoice, created=False)

    journal_entry_id = invoice.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Sales invoice is not linked to a posted journal entry")
    if invoice.get("status") != "posted":
        raise AccountingValidationError("Only posted sales invoices can be cancelled")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        original_date=invoice.get("invoice_date"),
        reversal_date=reversal_date,
        document_label="invoice",
    )

    old_invoice = _invoice_response_doc(invoice)
    reversal_key = idempotency_key or f"sales-invoice-cancel:{invoice_id}"
    reversal, created = await business_service.reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=reversal_date,
        reason=payload.reason,
        idempotency_key=reversal_key,
    )
    update = {
        "status": "cancelled",
        "reversal_journal_entry_id": reversal.id,
        "cancel_reason": payload.reason,
        "cancelled_at": _now(),
        "updated_at": _now(),
    }
    await invoices.update_one(filters, {"$set": update})
    invoice.update(update)
    result = _invoice_response_doc(invoice, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_sales_invoice_cancelled",
        entity_type="business_sales_invoice",
        entity_id=invoice_id,
        old_value=old_invoice,
        new_value=result,
    )
    return result
