"""GST return assembly — GSTR-3B (monthly summary return).

Clean-room: built to the GSTN GSTR-3B return structure (tables 3.1, 4, 5, 6.1)
and the offline-utility JSON shape, not copied from any implementation. The
numbers come from our own immutable Postgres ledger (tax heads) and the posted
sales-invoice / credit-note documents (taxable value) — never invented.

Design mirrors the GST settlement engine:
- A **pure** assembler (`assemble_gstr3b`) takes already-computed figures and
  returns the structured report + the GSTN JSON. It needs no DB, so the return
  logic unit-tests in isolation.
- Async gatherers (`build_gstr3b`) collect the figures: tax heads from the
  ledger (reusing the settlement set-off), taxable value from invoice docs.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry, JournalLine
from app.db.mongo import get_collection
from app.modules.business.service import (
    INPUT_CGST_CODE,
    INPUT_IGST_CODE,
    INPUT_SGST_CODE,
    OUTPUT_CGST_CODE,
    OUTPUT_IGST_CODE,
    OUTPUT_SGST_CODE,
    SALES_INVOICES_COLLECTION,
    CREDIT_NOTES_COLLECTION,
    _compute_gst_setoff,
    _period_bounds,
)

HEADS = ("igst", "cgst", "sgst")

# Ledger account code -> (side, head) for the six GST accounts.
_GST_CODE_MAP = {
    OUTPUT_IGST_CODE: ("output", "igst"),
    OUTPUT_CGST_CODE: ("output", "cgst"),
    OUTPUT_SGST_CODE: ("output", "sgst"),
    INPUT_IGST_CODE: ("input", "igst"),
    INPUT_CGST_CODE: ("input", "cgst"),
    INPUT_SGST_CODE: ("input", "sgst"),
}


def _zero_heads() -> dict:
    return {h: Decimal("0") for h in HEADS}


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def _ret_period(period: str) -> str:
    """'YYYY-MM' -> GSTN 'MMYYYY'."""
    year, month = period.split("-")
    return f"{int(month):02d}{year}"


# --------------------------------------------------------------------------- #
# Pure assembler (no DB) — the return logic
# --------------------------------------------------------------------------- #
def assemble_gstr3b(
    *,
    gstin: str | None,
    period: str,
    output: dict,            # net output tax per head (liability)
    itc_available: dict,     # gross ITC per head
    itc_reversed: dict,      # ITC reversed per head (Rule 37 etc.)
    outward_taxable_value: Decimal,
) -> dict:
    """Build the GSTR-3B structured report and GSTN JSON from computed figures.

    Coverage note (v1): populates 3.1(a) outward taxable supplies, 4 eligible
    ITC (4A "all other ITC", 4B "others" reversal, 4C net), and 6.1 payment of
    tax. Zero-rated/nil/exempt (3.1 b/c/e) and inward-RCM (3.1 d) are reported
    as zero with a note until those supply types are flagged on documents.
    """
    output = {h: _q(output.get(h, 0)) for h in HEADS}
    itc_available = {h: _q(itc_available.get(h, 0)) for h in HEADS}
    itc_reversed = {h: _q(itc_reversed.get(h, 0)) for h in HEADS}
    itc_net = {h: _q(itc_available[h] - itc_reversed[h]) for h in HEADS}

    # Set-off: how much liability is met by ITC vs cash (statutory order).
    _utilized, cash_payable, _carry = _compute_gst_setoff(output, itc_net)
    cash_payable = {h: _q(cash_payable.get(h, 0)) for h in HEADS}
    itc_applied = {h: _q(output[h] - cash_payable[h]) for h in HEADS}

    report = {
        "return_type": "GSTR-3B",
        "gstin": gstin,
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # 3.1 Outward supplies and inward supplies liable to reverse charge.
        "outward_supplies": {
            "taxable": {
                "taxable_value": _q(outward_taxable_value),
                **output,
            },
            "zero_rated": {"taxable_value": Decimal("0.00"), **_zero_heads()},
            "nil_exempt": {"taxable_value": Decimal("0.00")},
            "inward_reverse_charge": {"taxable_value": Decimal("0.00"), **_zero_heads()},
            "non_gst": {"taxable_value": Decimal("0.00")},
        },
        # 4. Eligible ITC.
        "itc": {
            "available_all_other": itc_available,
            "reversed_others": itc_reversed,
            "net_available": itc_net,
        },
        # 6.1 Payment of tax.
        "tax_payment": {
            h: {
                "tax_payable": output[h],
                "paid_through_itc": itc_applied[h],
                "paid_in_cash": cash_payable[h],
            }
            for h in HEADS
        },
        "totals": {
            "total_output_tax": _q(sum(output.values())),
            "total_itc_net": _q(sum(itc_net.values())),
            "total_cash_payable": _q(sum(cash_payable.values())),
        },
        "notes": [
            "Zero-rated, nil/exempt, non-GST outward and inward-RCM supplies are "
            "reported as zero until those supply types are flagged on documents.",
        ],
    }
    report["gstn_json"] = _gstn_json(report)
    return report


def _amt(d: dict) -> dict:
    """Heads dict -> GSTN amount keys (iamt/camt/samt/csamt)."""
    return {
        "iamt": float(d["igst"]),
        "camt": float(d["cgst"]),
        "samt": float(d["sgst"]),
        "csamt": 0.0,
    }


def _gstn_json(report: dict) -> dict:
    """Approximate the GSTN GSTR-3B offline-utility JSON shape."""
    osup = report["outward_supplies"]
    itc = report["itc"]
    pay = report["tax_payment"]
    head_to_ty = {"igst": "IGST", "cgst": "CGST", "sgst": "SGST"}
    return {
        "gstin": report["gstin"],
        "ret_period": _ret_period(report["period"]),
        "sup_details": {
            "osup_det": {"txval": float(osup["taxable"]["taxable_value"]), **_amt(osup["taxable"])},
            "osup_zero": {"txval": 0.0, **_amt(osup["zero_rated"])},
            "osup_nil_exmp": {"txval": 0.0},
            "isup_rev": {"txval": 0.0, **_amt(osup["inward_reverse_charge"])},
            "osup_nongst": {"txval": 0.0},
        },
        "itc_elg": {
            "itc_avl": [{"ty": "OTH", **_amt(itc["available_all_other"])}],
            "itc_rev": [{"ty": "OTH", **_amt(itc["reversed_others"])}],
            "itc_net": _amt(itc["net_available"]),
        },
        "tx_pmt": {
            "tx_pd": [
                {
                    "ty": head_to_ty[h],
                    "tx_payable": float(pay[h]["tax_payable"]),
                    "tx_paid_itc": float(pay[h]["paid_through_itc"]),
                    "tx_paid_cash": float(pay[h]["paid_in_cash"]),
                }
                for h in HEADS
            ]
        },
    }


# --------------------------------------------------------------------------- #
# Async gatherers — pull the figures, then call the pure assembler
# --------------------------------------------------------------------------- #
async def _gst_gross_by_head(
    session: AsyncSession, *, tenant_id: str, app_key: str, accounting_entity_id: str,
    first: date, last: date,
) -> tuple[dict, dict, dict]:
    """Per-head ledger figures for the period:
    - output net (credit-debit on Output GST accounts) = liability raised,
    - itc available (debit on Input GST accounts) = fresh ITC claimed,
    - itc reversed (credit on Input GST accounts) = Rule-37 etc. reversals.
    """
    stmt = (
        select(
            Account.code,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.app_key == app_key,
            JournalEntry.accounting_entity_id == accounting_entity_id,
            JournalEntry.entry_date >= first,
            JournalEntry.entry_date <= last,
            Account.code.in_(list(_GST_CODE_MAP.keys())),
        ))
        .group_by(Account.code)
    )
    output = _zero_heads()
    itc_available = _zero_heads()
    itc_reversed = _zero_heads()
    for code, debit_total, credit_total in (await session.execute(stmt)).all():
        side, head = _GST_CODE_MAP[code]
        debit = Decimal(debit_total or 0)
        credit = Decimal(credit_total or 0)
        if side == "output":
            output[head] += (credit - debit)
        else:
            itc_available[head] += debit
            itc_reversed[head] += credit
    for d in (output, itc_available, itc_reversed):
        for h in d:
            if d[h] < 0:
                d[h] = Decimal("0")
    return output, itc_available, itc_reversed


async def _outward_taxable_value(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, first: date, last: date,
) -> Decimal:
    """Net outward taxable value = posted sales invoices' taxable_total in the
    period, less posted credit notes (which reduce outward supply)."""
    def _in_period(row: dict) -> bool:
        raw = str(row.get("invoice_date") or row.get("note_date") or row.get("date") or "")[:10]
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return False
        return first <= d <= last and str(row.get("status") or "posted").lower() != "cancelled"

    scope = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    total = Decimal("0")
    invoices = await get_collection(SALES_INVOICES_COLLECTION).find(scope).to_list(length=20000)
    for inv in invoices:
        if _in_period(inv):
            total += Decimal(str(inv.get("taxable_total") or 0))
    notes = await get_collection(CREDIT_NOTES_COLLECTION).find(scope).to_list(length=20000)
    for note in notes:
        if _in_period(note):
            total -= Decimal(str(note.get("taxable_total") or 0))
    return total if total > 0 else Decimal("0")


async def build_gstr3b(
    session: AsyncSession, *, tenant_id: str, app_key: str,
    accounting_entity_id: str, period: str, gstin: str | None = None,
) -> dict:
    """Assemble the GSTR-3B for a 'YYYY-MM' period from the ledger + invoices."""
    first, last = _period_bounds(period)
    output, itc_available, itc_reversed = await _gst_gross_by_head(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last,
    )
    taxable_value = await _outward_taxable_value(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last,
    )
    return assemble_gstr3b(
        gstin=gstin, period=period, output=output, itc_available=itc_available,
        itc_reversed=itc_reversed, outward_taxable_value=taxable_value,
    )
