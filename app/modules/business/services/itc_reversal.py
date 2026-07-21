"""Business Rule 37 ITC reversal / reclaim (purchase-side).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Imported via the service.py facade (which re-exports the public functions), so
the shared symbols below resolve from the fully-initialised service module.
"""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
)
from app.modules.business import service as business_service
from app.modules.business.schemas import (
    BillPaymentUpdateRequest,
    ItcReclaimActionRequest,
    ItcReversalActionRequest,
)
from app.modules.business.services.purchase_bills import _bill_response_doc
from app.modules.business.service import (
    GST_INTEREST_EXPENSE_CODE,
    GST_INTEREST_PAYABLE_CODE,
    INPUT_CGST_CODE,
    INPUT_IGST_CODE,
    INPUT_SGST_CODE,
    ITC_INTEREST_RATE,
    ITC_REVERSAL_DAYS,
    ITC_REVERSAL_RECOVERABLE_CODE,
    PURCHASE_BILLS_COLLECTION,
    _audit_business_event,
    _now,
    _period_key,
    _period_label,
)


def _parse_iso_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _itc_split_for_bill(bill: dict) -> tuple[dict, Decimal]:
    """Input GST (ITC) per head as recorded on a posted bill."""
    split = {
        "cgst": Decimal(str(bill.get("cgst_total") or "0")),
        "sgst": Decimal(str(bill.get("sgst_total") or "0")),
        "igst": Decimal(str(bill.get("igst_total") or "0")),
    }
    total = split["cgst"] + split["sgst"] + split["igst"]
    return split, total


def _compute_itc_interest(itc_total: Decimal, bill_date: date | None, as_of: date) -> Decimal:
    """18% p.a. interest (Section 50), accruing from the ITC-availed (bill) date to
    the reversal/as-of date. Simple interest on a 365-day year, ROUND_HALF_UP."""
    if bill_date is None:
        return Decimal("0")
    days = (as_of - bill_date).days
    if days <= 0 or itc_total <= 0:
        return Decimal("0")
    interest = itc_total * ITC_INTEREST_RATE * Decimal(days) / Decimal("365")
    return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def mark_bill_payment(
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: BillPaymentUpdateRequest,
) -> dict:
    """Record how much of a posted bill has been paid. Drives the Rule 37
    180-day non-payment test; the cash/bank movement itself is a separate voucher."""
    bills = business_service.get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can record payments")

    bill_total = Decimal(str(bill.get("bill_total") or "0"))
    # With TDS the vendor is only owed the net; the deducted tax is discharged
    # via the TDS challan, so full settlement is reached at net_payable.
    settle_total = Decimal(str(bill.get("net_payable") or bill_total))
    paid_amount = Decimal(payload.paid_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if paid_amount < 0:
        raise AccountingValidationError("Paid amount cannot be negative")
    if paid_amount > settle_total:
        raise AccountingValidationError("Paid amount cannot exceed the amount payable on the bill")

    if paid_amount <= 0:
        payment_status = "unpaid"
    elif paid_amount >= settle_total:
        payment_status = "paid"
    else:
        payment_status = "partial"

    if payment_status == "unpaid":
        paid_date = None
    elif payload.paid_date:
        paid_date = payload.paid_date.isoformat()
    else:
        paid_date = date.today().isoformat()

    old_bill = _bill_response_doc(bill)
    update = {
        "payment_status": payment_status,
        "paid_amount": str(paid_amount),
        "paid_date": paid_date,
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_bill_payment_updated",
        entity_type="business_purchase_bill",
        entity_id=bill_id,
        old_value=old_bill,
        new_value=result,
    )
    return result


async def preview_itc_reversals(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    as_of: date | None = None,
) -> dict:
    """Scan posted bills and flag those whose ITC must be reversed under Rule 37:
    unpaid (or partial) beyond 180 days from the bill date, not already reversed."""
    as_of = as_of or date.today()
    bills = business_service.get_collection(PURCHASE_BILLS_COLLECTION)
    rows = await (
        bills.find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "status": "posted",
            }
        ).to_list(length=2000)
    )

    candidates: list[dict] = []
    total_itc = Decimal("0")
    total_interest = Decimal("0")
    for bill in rows:
        if bill.get("itc_reversed"):
            continue
        if bill.get("is_reverse_charge"):
            # Rule 37 proviso: the 180-day payment test does not apply to
            # supplies taxed under reverse charge (the recipient paid the tax).
            continue
        if bill.get("payment_status") == "paid":
            continue
        bill_date = _parse_iso_date(bill.get("bill_date"))
        if bill_date is None:
            continue
        due_date = bill_date + timedelta(days=ITC_REVERSAL_DAYS)
        if due_date > as_of:
            continue  # still within the 180-day window
        split, itc_total = _itc_split_for_bill(bill)
        if itc_total <= 0:
            continue
        interest = _compute_itc_interest(itc_total, bill_date, as_of)
        total_itc += itc_total
        total_interest += interest
        candidates.append(
            {
                "bill_id": bill.get("bill_id"),
                "bill_number": bill.get("bill_number"),
                "vendor_party_id": bill.get("vendor_party_id"),
                "vendor_name": bill.get("vendor_name"),
                "bill_date": bill_date.isoformat(),
                "due_date": due_date.isoformat(),
                "days_overdue": (as_of - due_date).days,
                "payment_status": bill.get("payment_status", "unpaid"),
                "paid_amount": str(bill.get("paid_amount") or "0"),
                "bill_total": str(bill.get("bill_total") or "0"),
                # Full settlement target — net of TDS when the bill deducted any.
                "net_payable": str(bill.get("net_payable") or bill.get("bill_total") or "0"),
                "itc_amounts": {h: str(split[h]) for h in ("igst", "cgst", "sgst")},
                "itc_total": str(itc_total),
                "interest_amount": str(interest),
                "gstr3b_ref": "4(B)(2)",
            }
        )
    candidates.sort(key=lambda c: c["days_overdue"], reverse=True)
    return {
        "as_of": as_of.isoformat(),
        "accounting_entity_id": accounting_entity_id,
        "candidates": candidates,
        "total_itc": str(total_itc),
        "total_interest": str(total_interest),
        "count": len(candidates),
    }


async def reverse_itc_for_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: ItcReversalActionRequest,
    idempotency_key: str | None,
) -> dict:
    """Post the Rule 37 ITC reversal for a bill: park the credit as recoverable and
    add 18% interest. Crediting Input GST raises the reversal period's net payable."""
    bills = business_service.get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if bill.get("status") != "posted":
        raise AccountingValidationError("Only posted purchase bills can have ITC reversed")
    if bill.get("itc_reversed") and bill.get("itc_reversal_journal_entry_id"):
        return _bill_response_doc(bill, created=False)
    if bill.get("payment_status") == "paid":
        raise AccountingValidationError("This bill is marked paid; its ITC need not be reversed")

    split, itc_total = _itc_split_for_bill(bill)
    if itc_total <= 0:
        raise AccountingValidationError("This bill carries no input GST to reverse")

    bill_date = _parse_iso_date(bill.get("bill_date"))
    reversal_date = payload.reversal_date or date.today()
    if bill_date and reversal_date < bill_date:
        raise AccountingValidationError("Reversal date cannot precede the bill date")

    reversal_period = _period_key(reversal_date)
    if await business_service.is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        period=reversal_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(reversal_period)} GST period is finalised and locked. "
            f"Choose a reversal date in an open period."
        )

    if app_key == "mitrabooks":
        await business_service.initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    interest = _compute_itc_interest(itc_total, bill_date, reversal_date)

    # Dr ITC Reversed (Recoverable); Cr Input CGST/SGST/IGST (reduce ITC -> raises net payable).
    recoverable_id = await business_service._resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=ITC_REVERSAL_RECOVERABLE_CODE, side="ITC reversal",
    )
    journal_lines = [JournalLineIn(account_id=recoverable_id, debit=itc_total, credit=Decimal("0"))]
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if split[head] > 0:
            acc = await business_service._resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=Decimal("0"), credit=split[head]))
    # Interest (non-reclaimable): Dr Interest on GST (expense); Cr Interest Payable on GST.
    if interest > 0:
        interest_exp = await business_service._resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_INTEREST_EXPENSE_CODE, side="interest expense",
        )
        interest_pay = await business_service._resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_INTEREST_PAYABLE_CODE, side="interest payable",
        )
        journal_lines.append(JournalLineIn(account_id=interest_exp, debit=interest, credit=Decimal("0")))
        journal_lines.append(JournalLineIn(account_id=interest_pay, debit=Decimal("0"), credit=interest))

    bill_number = bill.get("bill_number")
    journal_entry, created = await business_service.post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=reversal_date,
            description=f"ITC reversal (Rule 37) - Bill {bill_number}",
            reference=f"ITC-REV-{bill_number}",
            source_module="business", source_document_type="itc_reversal", source_document_id=bill_id,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"itc-reversal:{bill_id}",
    )

    update = {
        "itc_reversed": True,
        "itc_reversal_journal_entry_id": journal_entry.id,
        "itc_reversal_date": reversal_date.isoformat(),
        "itc_reversal_period": reversal_period,
        "itc_reversed_amounts": {h: str(split[h]) for h in ("igst", "cgst", "sgst")},
        "itc_interest_amount": str(interest),
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_itc_reversed", entity_type="business_purchase_bill", entity_id=bill_id, new_value=result,
    )
    return result


async def reclaim_itc_for_bill(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill_id: str,
    created_by: str,
    payload: ItcReclaimActionRequest,
    idempotency_key: str | None,
) -> dict:
    """Re-avail ITC previously reversed under Rule 37, once the bill is paid.
    Interest already charged is not reclaimable. GSTR-3B reference: 4(D)(1)."""
    bills = business_service.get_collection(PURCHASE_BILLS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "bill_id": bill_id,
    }
    bill = await bills.find_one(filters)
    if bill is None:
        raise AccountingNotFoundError("Purchase bill not found")
    if not bill.get("itc_reversed"):
        raise AccountingValidationError("ITC was not reversed on this bill; nothing to reclaim")
    if bill.get("itc_reclaimed") and bill.get("itc_reclaim_journal_entry_id"):
        return _bill_response_doc(bill, created=False)
    if bill.get("payment_status") != "paid":
        raise AccountingValidationError("Mark the bill as paid before reclaiming the reversed ITC")

    reversed_amounts = bill.get("itc_reversed_amounts") or {}
    split = {h: Decimal(str(reversed_amounts.get(h) or "0")) for h in ("cgst", "sgst", "igst")}
    itc_total = split["cgst"] + split["sgst"] + split["igst"]
    if itc_total <= 0:
        raise AccountingValidationError("No reversed ITC recorded to reclaim")

    reclaim_date = payload.reclaim_date or date.today()
    reclaim_period = _period_key(reclaim_date)
    if await business_service.is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        period=reclaim_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(reclaim_period)} GST period is finalised and locked. "
            f"Choose a reclaim date in an open period."
        )

    if app_key == "mitrabooks":
        await business_service.initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            organization_type="BUSINESS",
        )

    # Dr Input CGST/SGST/IGST (restore ITC); Cr ITC Reversed (Recoverable).
    journal_lines = []
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if split[head] > 0:
            acc = await business_service._resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=split[head], credit=Decimal("0")))
    recoverable_id = await business_service._resolve_voucher_account_id(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        account_id=None, account_code=ITC_REVERSAL_RECOVERABLE_CODE, side="ITC reversal",
    )
    journal_lines.append(JournalLineIn(account_id=recoverable_id, debit=Decimal("0"), credit=itc_total))

    bill_number = bill.get("bill_number")
    journal_entry, created = await business_service.post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=reclaim_date,
            description=f"ITC reclaim (Rule 37) - Bill {bill_number}",
            reference=f"ITC-RCL-{bill_number}",
            source_module="business", source_document_type="itc_reclaim", source_document_id=bill_id,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"itc-reclaim:{bill_id}",
    )

    update = {
        "itc_reclaimed": True,
        "itc_reclaim_journal_entry_id": journal_entry.id,
        "itc_reclaim_date": reclaim_date.isoformat(),
        "updated_at": _now(),
    }
    await bills.update_one(filters, {"$set": update})
    bill.update(update)
    result = _bill_response_doc(bill, created=created)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_itc_reclaimed", entity_type="business_purchase_bill", entity_id=bill_id, new_value=result,
    )
    return result
