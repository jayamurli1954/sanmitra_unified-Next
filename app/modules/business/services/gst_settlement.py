"""Business GST Settlement (period-end set-off).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Imported via the service.py facade (which re-exports the public functions), so
the shared symbols below resolve from the fully-initialised service module.
"""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    initialize_default_chart_of_accounts,
    post_journal_entry,
    reverse_journal_entry,
)
from app.db.mongo import get_collection
from app.modules.business.schemas import (
    GstPeriodLockUpdateRequest,
    GstSettlementCreateRequest,
    GstSettlementReverseRequest,
)
from app.modules.business.service import (
    GST_PAYABLE_CODE,
    GST_SETTLEMENTS_COLLECTION,
    INPUT_CGST_CODE,
    INPUT_IGST_CODE,
    INPUT_SGST_CODE,
    OUTPUT_CGST_CODE,
    OUTPUT_IGST_CODE,
    OUTPUT_SGST_CODE,
    _audit_business_event,
    _compensate_gst_settlement_failure,
    _compute_gst_setoff,
    _now,
    _period_bounds,
    _period_key,
    _period_label,
    _resolve_voucher_account_id,
    is_gst_period_locked,
    set_gst_period_lock,
)


async def _gst_period_balances(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    """Net GST accrued in the period per head: output (credit-debit on Output
    accounts) and input/ITC (debit-credit on Input accounts)."""
    first, last = _period_bounds(period)
    codes = {
        OUTPUT_IGST_CODE: ("output", "igst"), OUTPUT_CGST_CODE: ("output", "cgst"), OUTPUT_SGST_CODE: ("output", "sgst"),
        INPUT_IGST_CODE: ("input", "igst"), INPUT_CGST_CODE: ("input", "cgst"), INPUT_SGST_CODE: ("input", "sgst"),
    }
    stmt = (
        select(
            Account.code,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.app_key == app_key,
            JournalEntry.accounting_entity_id == accounting_entity_id,
            JournalEntry.entry_date >= first,
            JournalEntry.entry_date <= last,
            Account.code.in_(list(codes.keys())),
        )
        .group_by(Account.code)
    )
    output = {"igst": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
    credit = {"igst": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
    for code, debit_total, credit_total in (await session.execute(stmt)).all():
        kind, head = codes[code]
        debit = Decimal(debit_total or 0)
        cr = Decimal(credit_total or 0)
        if kind == "output":
            output[head] += (cr - debit)  # liability is a credit balance
        else:
            credit[head] += (debit - cr)  # ITC is a debit balance
    # Guard against tiny negatives from rounding.
    for d in (output, credit):
        for h in d:
            if d[h] < 0:
                d[h] = Decimal("0")
    return {"output": output, "credit": credit}


def _settlement_doc_to_response(doc: dict) -> dict:
    heads = ("igst", "cgst", "sgst")
    def amt(section):
        section = section or {}
        return {h: str(section.get(h, "0")) for h in heads}
    return {
        "period": doc.get("period"),
        "accounting_entity_id": doc.get("accounting_entity_id"),
        "output": amt(doc.get("output")),
        "input_credit": amt(doc.get("input_credit")),
        "utilized": amt(doc.get("utilized")),
        "cash_payable": amt(doc.get("cash_payable")),
        "itc_carry_forward": amt(doc.get("itc_carry_forward")),
        "net_cash_payable": str(doc.get("net_cash_payable", "0")),
        "total_output": str(doc.get("total_output", "0")),
        "total_input": str(doc.get("total_input", "0")),
        "status": doc.get("status", "preview"),
        "posted": bool(doc.get("posted")),
        "period_locked": bool(doc.get("period_locked")),
        "journal_entry_id": doc.get("journal_entry_id"),
        "reversal_journal_entry_id": doc.get("reversal_journal_entry_id"),
        "note": doc.get("note"),
        "settled_by": doc.get("settled_by"),
        "settled_at": doc.get("settled_at"),
        "reversed_by": doc.get("reversed_by"),
        "reversed_at": doc.get("reversed_at"),
    }


async def _build_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    balances = await _gst_period_balances(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    output, credit = balances["output"], balances["credit"]
    utilized, cash_payable, itc_carry = _compute_gst_setoff(output, credit)
    net_cash = sum(cash_payable.values())
    total_output = sum(output.values())
    total_input = sum(credit.values())
    note = None
    if total_output == 0 and total_input > 0:
        note = "No output GST this period; input credit carries forward."
    return {
        "period": period,
        "accounting_entity_id": accounting_entity_id,
        "output": {h: str(output[h]) for h in output},
        "input_credit": {h: str(credit[h]) for h in credit},
        "utilized": {h: str(utilized[h]) for h in utilized},
        "cash_payable": {h: str(cash_payable[h]) for h in cash_payable},
        "itc_carry_forward": {h: str(itc_carry[h]) for h in itc_carry},
        "net_cash_payable": str(net_cash),
        "total_output": str(total_output),
        "total_input": str(total_input),
        "note": note,
        "_raw": {"output": output, "credit": credit, "utilized": utilized, "cash_payable": cash_payable, "net_cash": net_cash},
    }


async def preview_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> dict:
    existing = await get_collection(GST_SETTLEMENTS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id, "period": period}
    )
    if existing is not None and existing.get("status") == "posted":
        return _settlement_doc_to_response(existing)
    built = await _build_gst_settlement(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    built.pop("_raw", None)
    built["status"] = "preview"
    built["posted"] = False
    built["period_locked"] = await is_gst_period_locked(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, period=period,
    )
    return _settlement_doc_to_response(built)


async def create_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: GstSettlementCreateRequest,
    idempotency_key: str | None,
) -> dict:
    period = payload.period
    settlements = get_collection(GST_SETTLEMENTS_COLLECTION)
    existing = await settlements.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "period": period}
    )
    if existing is not None and existing.get("status") == "posted":
        return _settlement_doc_to_response(existing)

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id, organization_type="BUSINESS",
        )

    built = await _build_gst_settlement(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id, period=period,
    )
    raw = built.pop("_raw")
    output, utilized, net_cash = raw["output"], raw["utilized"], raw["net_cash"]
    if sum(output.values()) <= 0:
        raise AccountingValidationError("No output GST to settle for this period; input credit simply carries forward.")

    # Build the set-off journal entry: Dr Output GST; Cr Input GST (utilized) + Cr GST Payable (net cash).
    journal_lines = []
    for head, code in (("cgst", OUTPUT_CGST_CODE), ("sgst", OUTPUT_SGST_CODE), ("igst", OUTPUT_IGST_CODE)):
        if output[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="output GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=output[head], credit=Decimal("0")))
    for head, code in (("cgst", INPUT_CGST_CODE), ("sgst", INPUT_SGST_CODE), ("igst", INPUT_IGST_CODE)):
        if utilized[head] > 0:
            acc = await _resolve_voucher_account_id(
                session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
                account_id=None, account_code=code, side="input GST",
            )
            journal_lines.append(JournalLineIn(account_id=acc, debit=Decimal("0"), credit=utilized[head]))
    if net_cash > 0:
        payable_acc = await _resolve_voucher_account_id(
            session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
            account_id=None, account_code=GST_PAYABLE_CODE, side="GST payable",
        )
        journal_lines.append(JournalLineIn(account_id=payable_acc, debit=Decimal("0"), credit=net_cash))

    _, last = _period_bounds(period)
    journal_entry, _created = await post_journal_entry(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=last,
            description=f"GST settlement for {_period_label(period)}",
            reference=f"GST-{period}",
            source_module="business", source_document_type="gst_settlement", source_document_id=period,
            lines=journal_lines,
        ),
        idempotency_key=idempotency_key or f"gst-settlement:{tenant_id}:{payload.accounting_entity_id}:{period}",
    )

    period_locked = False
    if payload.lock_period:
        try:
            await set_gst_period_lock(
                tenant_id=tenant_id, app_key=app_key, updated_by=created_by,
                payload=GstPeriodLockUpdateRequest(period=period, locked=True, note=f"Auto-locked on GST settlement", accounting_entity_id=payload.accounting_entity_id),
            )
            period_locked = True
        except Exception as exc:
            await _compensate_gst_settlement_failure(
                session,
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=payload.accounting_entity_id,
                created_by=created_by,
                period=period,
                journal_entry_id=int(journal_entry.id),
                unlock_period=False,
                failure_label="GST period locking failed",
            )
            raise AccountingValidationError(
                "GST period locking failed after settlement journal posting; the accounting entry was automatically reversed"
            ) from exc

    doc = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        **built,
        "status": "posted",
        "posted": True,
        "period_locked": period_locked,
        "journal_entry_id": journal_entry.id,
        "settled_by": created_by,
        "settled_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
    }
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id, "period": period}
    try:
        await settlements.update_one(filters, {"$set": doc}, upsert=True)
    except Exception as exc:
        await _compensate_gst_settlement_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=payload.accounting_entity_id,
            created_by=created_by,
            period=period,
            journal_entry_id=int(journal_entry.id),
            unlock_period=period_locked,
            failure_label="GST settlement persistence failed",
        )
        if period_locked:
            raise AccountingValidationError(
                "GST settlement persistence failed after journal posting; the accounting entry was automatically reversed and the GST period was unlocked"
            ) from exc
        raise AccountingValidationError(
            "GST settlement persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    result = _settlement_doc_to_response(doc)
    await _audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="business_gst_settlement_posted", entity_type="business_gst_settlement", entity_id=period, new_value=result,
    )
    return result


async def reverse_gst_settlement(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    period: str,
    payload: GstSettlementReverseRequest,
    idempotency_key: str | None,
) -> dict:
    settlements = get_collection(GST_SETTLEMENTS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "period": period,
    }
    settlement = await settlements.find_one(filters)
    if settlement is None:
        raise AccountingNotFoundError("GST settlement not found")
    if settlement.get("status") == "reversed" and settlement.get("reversal_journal_entry_id"):
        return _settlement_doc_to_response(settlement)
    if settlement.get("status") != "posted":
        raise AccountingValidationError("Only posted GST settlements can be reversed")
    journal_entry_id = settlement.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("GST settlement is not linked to a posted journal entry")

    _, period_end = _period_bounds(period)
    reversal_date = payload.reversal_date or period_end
    reversal_period = _period_key(reversal_date)
    if reversal_period != period:
        raise AccountingValidationError(
            f"GST settlement reversal must be dated within {_period_label(period)}"
        )

    period_was_locked = await is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        period=period,
    )
    if period_was_locked and not payload.unlock_period:
        raise AccountingValidationError(
            f"The {_period_label(period)} GST period is locked. Set unlock_period=true to reverse the settlement."
        )
    if period_was_locked:
        await set_gst_period_lock(
            tenant_id=tenant_id,
            app_key=app_key,
            updated_by=created_by,
            payload=GstPeriodLockUpdateRequest(
                period=period,
                locked=False,
                note="Unlocked for GST settlement reversal",
                accounting_entity_id=payload.accounting_entity_id,
            ),
        )

    reversal, created = await reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=reversal_date,
        reason=payload.reason,
        idempotency_key=idempotency_key or f"gst-settlement-reversal:{tenant_id}:{payload.accounting_entity_id}:{period}",
    )
    update = {
        "status": "reversed",
        "posted": False,
        "period_locked": False,
        "reversal_journal_entry_id": reversal.id,
        "reversed_by": created_by,
        "reversed_at": _now(),
        "reverse_reason": payload.reason,
        "updated_at": _now(),
    }
    await settlements.update_one(filters, {"$set": update})
    settlement.update(update)
    result = _settlement_doc_to_response(settlement)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_gst_settlement_reversed",
        entity_type="business_gst_settlement",
        entity_id=period,
        new_value={**result, "created_reversal": created},
    )
    return result
