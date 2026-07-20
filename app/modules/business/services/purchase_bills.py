"""Business Purchase Bill documents (create / review / approve / cancel).

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
from app.modules.business.inventory import validate_item_refs
from app.modules.business.tds import compute_tds
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    PurchaseBillCancelRequest,
    PurchaseBillCreateRequest,
)
from app.modules.business.service import (
    INPUT_CGST_CODE,
    INPUT_IGST_CODE,
    INPUT_SGST_CODE,
    PURCHASE_BILLS_COLLECTION,
    PURCHASE_PAYABLE_CODE,
    RCM_PAYABLE_CODE,
    TDS_PAYABLE_CODE,
    _audit_business_event,
    _compute_invoice_lines,
    _now,
    _resolve_voucher_account_id,
    _reverse_after_domain_persistence_failure,
    _validate_reversal_period,
    get_gst_profile,
    get_party,
)


def _bill_response_doc(doc: dict, *, created: bool = False) -> dict:
    from app.modules.business import service as business_service

    result = business_service._json_safe_doc(doc)
    business_service._apply_approval_defaults(result)
    result.setdefault("created", created)
    # Defaults so bills created before payment / ITC-reversal tracking render cleanly.
    result.setdefault("payment_status", "unpaid")
    result.setdefault("paid_amount", "0")
    result.setdefault("paid_date", None)
    result.setdefault("itc_reversed", False)
    result.setdefault("itc_interest_amount", "0")
    result.setdefault("itc_reclaimed", False)
    return result


async def list_purchase_bills(
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
        await get_collection(PURCHASE_BILLS_COLLECTION)
        .find(filters)
        .sort("bill_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_bill_response_doc(row) for row in rows], "total": len(rows)}


async def get_purchase_bill(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    bill_id: str,
) -> dict | None:
    row = await get_collection(PURCHASE_BILLS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "bill_id": bill_id,
        }
    )
    return _bill_response_doc(row) if row else None


async def review_purchase_bill(
    *,
    session: AsyncSession | None,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    reviewed_by: str,
    payload: ApprovalReviewRequest,
) -> dict:
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    old_value = _bill_response_doc(bill)
    current_status = str(bill.get("status") or "").strip().lower()
    if current_status in {"draft", "pending_approval"}:
        if current_status == "draft":
            raise AccountingValidationError("Only submitted purchase bills can be approved or rejected")
        if payload.approve:
            return await _approve_purchase_bill_document(
                session=session,
                tenant_id=tenant_id,
                app_key=app_key,
                reviewed_by=reviewed_by,
                bill=bill,
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
        if bill.get("approval_submitted_at") is None:
            patch["approval_submitted_at"] = bill.get("created_at")
            patch["approval_submitted_by"] = bill.get("created_by")
        await bills.update_one(filters, {"$set": patch})
        bill.update(patch)
        result = _bill_response_doc(bill)
        await _audit_business_event(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=reviewed_by,
            action="business_purchase_bill_reviewed",
            entity_type="business_purchase_bill",
            entity_id=bill_id,
            old_value=old_value,
            new_value=result,
        )
        return result
    if current_status != "posted":
        raise AccountingValidationError("Only posted or pending-approval purchase bills can be reviewed")

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
    if bill.get("approval_submitted_at") is None:
        patch["approval_submitted_at"] = bill.get("created_at")
        patch["approval_submitted_by"] = bill.get("created_by")

    await bills.update_one(filters, {"$set": patch})
    bill.update(patch)
    result = _bill_response_doc(bill)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_purchase_bill_reviewed",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def _approve_purchase_bill_document(
    *,
    session: AsyncSession | None,
    tenant_id: str,
    app_key: str,
    reviewed_by: str,
    bill: dict,
    old_value: dict,
    approval_notes: str | None,
) -> dict:
    if session is None:
        raise AccountingValidationError("Approval posting requires an active accounting session")
    bill_id = str(bill.get("bill_id") or "")
    bill_number = str(bill.get("bill_number") or bill_id)
    accounting_entity_id = str(bill.get("accounting_entity_id") or "primary")
    taxable_total = Decimal(str(bill.get("taxable_total") or "0"))
    cgst_total = Decimal(str(bill.get("cgst_total") or "0"))
    sgst_total = Decimal(str(bill.get("sgst_total") or "0"))
    igst_total = Decimal(str(bill.get("igst_total") or "0"))
    gst_total = Decimal(str(bill.get("gst_total") or "0"))
    bill_total = Decimal(str(bill.get("bill_total") or "0"))
    tds_amount = Decimal(str(bill.get("tds_amount") or "0"))
    net_payable = Decimal(str(bill.get("net_payable") or bill_total))
    is_composition = not bool(bill.get("itc_claimed", True))
    is_rcm = bool(bill.get("is_reverse_charge"))
    expense_account_code = str(bill.get("expense_account_code") or "51001")
    vendor_party_id = str(bill.get("vendor_party_id") or "")

    payable_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=PURCHASE_PAYABLE_CODE, side="payable",
    )
    expense_id = await _resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        account_id=None, account_code=expense_account_code, side="expense",
    )
    if is_composition:
        journal_lines = [JournalLineIn(account_id=expense_id, debit=bill_total, credit=Decimal("0"))]
    else:
        journal_lines = [JournalLineIn(account_id=expense_id, debit=taxable_total, credit=Decimal("0"))]
        for gst_amount, code in ((cgst_total, INPUT_CGST_CODE), (sgst_total, INPUT_SGST_CODE), (igst_total, INPUT_IGST_CODE)):
            if gst_amount > Decimal("0"):
                input_gst_id = await _resolve_voucher_account_id(
                    session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
                    account_id=None, account_code=code, side="input GST",
                )
                journal_lines.append(JournalLineIn(account_id=input_gst_id, debit=gst_amount, credit=Decimal("0")))
    if is_rcm and gst_total > Decimal("0"):
        rcm_payable_id = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            account_id=None, account_code=RCM_PAYABLE_CODE, side="RCM payable",
        )
        journal_lines.append(JournalLineIn(account_id=rcm_payable_id, debit=Decimal("0"), credit=gst_total))
    if tds_amount > Decimal("0"):
        tds_payable_id = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            account_id=None, account_code=TDS_PAYABLE_CODE, side="TDS payable",
        )
        journal_lines.append(JournalLineIn(account_id=tds_payable_id, debit=Decimal("0"), credit=tds_amount))
    journal_lines.append(JournalLineIn(account_id=payable_id, debit=Decimal("0"), credit=net_payable, party_id=vendor_party_id))

    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    description = f"Purchase Bill {bill_number} - {bill.get('vendor_name') or vendor_party_id}"
    try:
        journal_entry, created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            payload=JournalPostRequest(
                entry_date=date.fromisoformat(str(bill.get("bill_date"))[:10]),
                description=description,
                reference=bill_number,
                source_module="business",
                source_document_type="purchase_bill",
                source_document_id=bill_id,
                lines=journal_lines,
            ),
            idempotency_key=f"purchase-bill:{bill_id}",
        )
    except Exception as exc:
        raise AccountingValidationError(f"Purchase bill approval posting failed: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_entry_id": journal_entry.id,
        "approval_required": True,
        "approval_status": "approved",
        "approval_submitted_at": bill.get("approval_submitted_at") or bill.get("created_at"),
        "approval_submitted_by": bill.get("approval_submitted_by") or bill.get("created_by"),
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": approval_notes or "Approved and posted",
        "rejection_reason": None,
        "updated_at": _now(),
    }
    try:
        await bills.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "bill_id": bill_id},
            {"$set": patch},
        )
    except Exception as exc:
        await _reverse_after_domain_persistence_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            journal_entry_id=int(journal_entry.id),
            document_label="Purchase bill",
            document_id=bill_id,
            reversal_reason=f"Compensation after purchase bill approval persistence failure for {bill_number}",
            reversal_idempotency_key=f"purchase-bill-approve-compensate:{bill_id}:{journal_entry.id}",
        )
        raise AccountingValidationError(
            "Purchase bill approval persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    bill.update(patch)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_purchase_bill_reviewed",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def create_purchase_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: PurchaseBillCreateRequest,
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
        existing = await get_collection(PURCHASE_BILLS_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            return _bill_response_doc(existing, created=False)

    vendor = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        party_id=payload.vendor_party_id,
    )
    if vendor is None:
        raise AccountingValidationError("Vendor party not found for this tenant")

    await validate_dimension_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id, project_id=payload.project_id,
    )
    for item in payload.line_items:
        await validate_dimension_refs(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            cost_centre_id=getattr(item, "cost_centre_id", None),
            project_id=getattr(item, "project_id", None),
        )
    await validate_item_refs(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        line_items=payload.line_items,
    )

    # GST line computation is identical to sales (reads line_items + is_inter_state).
    lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, bill_total = _compute_invoice_lines(payload)
    if bill_total <= Decimal("0"):
        raise AccountingValidationError("Bill total must be greater than zero")

    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
    )
    is_composition = profile["is_composition"]

    # TDS (Income-tax) — deducted at credit time on the GST-exclusive taxable
    # value (Circular 23/2017). For composition entities GST is part of cost,
    # so the books' taxable_total (pre-GST) is still the correct TDS base.
    tds_rate = tds_amount = None
    if payload.tds_section:
        try:
            tds_rate, tds_amount = compute_tds(payload.tds_section, taxable_total, payload.tds_rate)
        except ValueError as exc:
            raise AccountingValidationError(str(exc))
        if tds_amount >= bill_total:
            raise AccountingValidationError("TDS deduction cannot equal or exceed the bill total")
    # Under reverse charge the vendor is owed the taxable value only — the GST
    # is the recipient's own liability (Cr RCM Payable), settled in cash.
    is_rcm = bool(payload.is_reverse_charge)
    vendor_owed = taxable_total if is_rcm else bill_total
    net_payable = vendor_owed - (tds_amount or Decimal("0"))

    bill_id = str(uuid4())
    bill_number = payload.bill_number.strip()
    now = _now()
    doc = {
        "bill_id": bill_id,
        "bill_number": bill_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "vendor_party_id": payload.vendor_party_id,
        "vendor_name": vendor.get("party_name"),
        "vendor_gstin": vendor.get("gstin"),
        "bill_date": payload.bill_date.isoformat(),
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "is_inter_state": payload.is_inter_state,
        "is_reverse_charge": is_rcm,
        "rcm_payable": str(gst_total) if is_rcm else "0",
        "place_of_supply": payload.place_of_supply,
        "expense_account_code": payload.expense_account_code,
        "notes": payload.notes,
        "line_items": lines,
        "taxable_total": str(taxable_total),
        "cgst_total": str(cgst_total),
        "sgst_total": str(sgst_total),
        "igst_total": str(igst_total),
        "gst_total": str(gst_total),
        "bill_total": str(bill_total),
        "tds_section": payload.tds_section,
        "tds_rate": str(tds_rate) if tds_rate is not None else None,
        "tds_base_amount": str(taxable_total) if payload.tds_section else None,
        "tds_amount": str(tds_amount) if tds_amount is not None else "0",
        "net_payable": str(net_payable),
        "deductee_pan": vendor.get("pan"),
        "deductee_pan_missing": bool(payload.tds_section) and not vendor.get("pan"),
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
        "itc_claimed": not is_composition,
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
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    await bills.insert_one(doc)
    result = _bill_response_doc(doc, created=True)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_purchase_bill_created",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        new_value=result,
    )
    return result


async def cancel_purchase_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: PurchaseBillCancelRequest,
    idempotency_key: str | None,
) -> dict:
    bills = get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")

    if bill.get("status") == "cancelled" and bill.get("reversal_journal_entry_id"):
        return _bill_response_doc(bill, created=False)

    journal_entry_id = bill.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Purchase bill is not linked to a posted journal entry")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can be cancelled")

    reversal_date = payload.cancel_date or date.today()
    await _validate_reversal_period(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        original_date=bill.get("bill_date"),
        reversal_date=reversal_date,
        document_label="bill",
    )

    old_bill = _bill_response_doc(bill)
    reversal_key = idempotency_key or f"purchase-bill-cancel:{bill_id}"
    reversal, created = await reverse_journal_entry(
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
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_purchase_bill_cancelled",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_bill,
        new_value=result,
    )
    return result
