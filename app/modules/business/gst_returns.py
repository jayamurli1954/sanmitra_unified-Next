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

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry, JournalLine
from app.db.mongo import get_collection
from app.modules.business.gst_states import resolve_state_code, state_label
from app.modules.business.service import (
    INPUT_CGST_CODE,
    INPUT_IGST_CODE,
    INPUT_SGST_CODE,
    OUTPUT_CGST_CODE,
    OUTPUT_IGST_CODE,
    OUTPUT_SGST_CODE,
    SALES_INVOICES_COLLECTION,
    CREDIT_NOTES_COLLECTION,
    PURCHASE_BILLS_COLLECTION,
    _compute_gst_setoff,
    _period_bounds,
    get_gst_profile,
)

HEADS = ("igst", "cgst", "sgst")

# GSTR-1 B2C Large threshold: inter-state B2C invoices above this go to B2CL (5),
# the rest are summarised in B2CS (7). (Rationalised to Rs 1,00,000 from 2024;
# kept configurable here.)
B2CL_THRESHOLD = Decimal("100000")

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
    itc_available: dict,     # gross ITC per head (incl. any RCM ITC in the ledger)
    itc_reversed: dict,      # ITC reversed per head (Rule 37 etc.)
    outward_taxable_value: Decimal,
    rcm_inward: dict | None = None,   # {"taxable_value", igst, cgst, sgst} from RCM bills
    itc_rcm: dict | None = None,      # heads — the 4(A)(3) split of the ITC above
    zero_rated_taxable_value: Decimal | None = None,  # 3.1(b) export/SEZ under LUT
) -> dict:
    """Build the GSTR-3B structured report and GSTN JSON from computed figures.

    Coverage: 3.1(a) outward taxable supplies, 3.1(d) inward supplies liable
    to reverse charge (from RCM-flagged purchase bills), 4 eligible ITC
    (4A(3) RCM ITC split out of 4A(5) all-other), 4B reversal, 4C net, and
    6.1 payment of tax. Zero-rated/nil/exempt (3.1 b/c/e) stay zero with a
    note until those supply types are flagged on documents.
    """
    output = {h: _q(output.get(h, 0)) for h in HEADS}
    itc_available = {h: _q(itc_available.get(h, 0)) for h in HEADS}
    itc_reversed = {h: _q(itc_reversed.get(h, 0)) for h in HEADS}
    itc_net = {h: _q(itc_available[h] - itc_reversed[h]) for h in HEADS}
    itc_rcm = {h: _q((itc_rcm or {}).get(h, 0)) for h in HEADS}
    # 4A(5) "all other ITC" = ledger ITC minus the RCM portion (never negative).
    itc_all_other = {h: max(_q(itc_available[h] - itc_rcm[h]), Decimal("0")) for h in HEADS}
    rcm = rcm_inward or {}
    rcm_block = {
        "taxable_value": _q(rcm.get("taxable_value", 0)),
        **{h: _q(rcm.get(h, 0)) for h in HEADS},
    }
    rcm_tax_total = _q(sum(rcm_block[h] for h in HEADS))

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
            "zero_rated": {"taxable_value": _q(zero_rated_taxable_value or 0), **_zero_heads()},
            "nil_exempt": {"taxable_value": Decimal("0.00")},
            "inward_reverse_charge": rcm_block,
            "non_gst": {"taxable_value": Decimal("0.00")},
        },
        # 4. Eligible ITC.
        "itc": {
            "available_rcm": itc_rcm,                # 4(A)(3)
            "available_all_other": itc_all_other,    # 4(A)(5)
            "reversed_others": itc_reversed,
            "net_available": itc_net,
        },
        # 3.1(d) liability is discharged in CASH only (no ITC set-off).
        "rcm_cash_payable": rcm_tax_total,
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
            "3.1(b) zero-rated comes from invoice lines flagged 'zero_rated' "
            "(export/SEZ under LUT — no tax). Nil/exempt and non-GST outward "
            "supplies stay zero until those supply types are flagged on documents.",
            "3.1(d) and 4(A)(3) come from purchase bills flagged 'reverse charge'. "
            "The RCM liability must be paid in cash (account 22005) — it cannot be "
            "set off against ITC.",
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
            "osup_zero": {"txval": float(osup["zero_rated"]["taxable_value"]), **_amt(osup["zero_rated"])},
            "osup_nil_exmp": {"txval": 0.0},
            "isup_rev": {"txval": float(osup["inward_reverse_charge"]["taxable_value"]), **_amt(osup["inward_reverse_charge"])},
            "osup_nongst": {"txval": 0.0},
        },
        "itc_elg": {
            "itc_avl": [
                {"ty": "ISRC", **_amt(itc["available_rcm"])},
                {"ty": "OTH", **_amt(itc["available_all_other"])},
            ],
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


async def _rcm_inward_for_period(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, first: date, last: date,
) -> dict:
    """3.1(d) figures: taxable value + tax heads from posted reverse-charge
    purchase bills in the period."""
    scope = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    totals = {"taxable_value": Decimal("0"), "igst": Decimal("0"), "cgst": Decimal("0"), "sgst": Decimal("0")}
    bills = await get_collection(PURCHASE_BILLS_COLLECTION).find(
        {**scope, "status": "posted", "is_reverse_charge": True,
         "bill_date": {"$gte": first.isoformat(), "$lte": last.isoformat()}}
    ).to_list(length=20000)
    for bill in bills:
        totals["taxable_value"] += Decimal(str(bill.get("taxable_total") or 0))
        totals["igst"] += Decimal(str(bill.get("igst_total") or 0))
        totals["cgst"] += Decimal(str(bill.get("cgst_total") or 0))
        totals["sgst"] += Decimal(str(bill.get("sgst_total") or 0))
    return totals


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
    rcm_inward = await _rcm_inward_for_period(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last,
    )
    # 4(A)(3): the ITC arising from those RCM bills (booked on the Input GST
    # accounts at posting, so it is already inside the ledger itc_available).
    itc_rcm = {h: rcm_inward[h] for h in ("igst", "cgst", "sgst")}
    # 3.1(b): zero-rated (export/SEZ) lines on posted invoices in the period.
    invoices = await _posted_in_period(
        SALES_INVOICES_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="invoice_date",
    )
    zero_rated_value = Decimal("0")
    for inv in invoices:
        for ln in inv.get("line_items") or []:
            if str(ln.get("supply_type") or "") == "zero_rated":
                zero_rated_value += _D(ln.get("taxable_amount"))
    # 3.1(a) is "outward taxable supplies OTHER THAN zero-rated/nil/exempt".
    taxable_value = max(taxable_value - zero_rated_value, Decimal("0"))
    return assemble_gstr3b(
        gstin=gstin, period=period, output=output, itc_available=itc_available,
        itc_reversed=itc_reversed, outward_taxable_value=taxable_value,
        rcm_inward=rcm_inward, itc_rcm=itc_rcm, zero_rated_taxable_value=zero_rated_value,
    )


# =========================================================================== #
# GSTR-1 — outward supplies detail (B2B / B2CL / B2CS / CDNR / HSN / DOCS)
# =========================================================================== #
def _D(value) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else 0))
    except Exception:
        return Decimal("0")


def _rate_buckets(line_items: list[dict]) -> dict:
    """Group a document's lines by GST rate -> summed taxable + tax per head."""
    buckets: dict[Decimal, dict] = {}
    for ln in line_items or []:
        rt = _D(ln.get("gst_rate"))
        b = buckets.setdefault(rt, {"txval": Decimal("0"), "iamt": Decimal("0"),
                                    "camt": Decimal("0"), "samt": Decimal("0")})
        b["txval"] += _D(ln.get("taxable_amount"))
        b["iamt"] += _D(ln.get("igst"))
        b["camt"] += _D(ln.get("cgst"))
        b["samt"] += _D(ln.get("sgst"))
    return buckets


def _itms(line_items: list[dict]) -> list[dict]:
    """GSTN rate-wise itms array for an invoice/note."""
    out = []
    for i, (rt, b) in enumerate(sorted(_rate_buckets(line_items).items()), start=1):
        out.append({"num": i, "itm_det": {
            "rt": float(rt), "txval": float(_q(b["txval"])),
            "iamt": float(_q(b["iamt"])), "camt": float(_q(b["camt"])),
            "samt": float(_q(b["samt"])), "csamt": 0.0,
        }})
    return out


def _doc_tax_totals(line_items: list[dict]) -> dict:
    t = {"txval": Decimal("0"), "iamt": Decimal("0"), "camt": Decimal("0"), "samt": Decimal("0")}
    for b in _rate_buckets(line_items).values():
        for k in t:
            t[k] += b[k]
    return {k: _q(v) for k, v in t.items()}


def assemble_gstr1(*, gstin: str | None, period: str, invoices: list[dict], credit_notes: list[dict]) -> dict:
    """Build the GSTR-1 sections + GSTN JSON from posted invoice/credit-note docs.

    Sections: B2B (4A), B2CL (5), B2CS (7), EXP (6A, zero-rated under LUT),
    CDNR (9B), HSN (12), DOCS (13). An invoice with any zero-rated line is
    treated as an export/SEZ invoice (don't mix zero-rated and domestic lines
    on one document). Each figure comes from the stored documents.
    """
    b2b: dict[str, list] = {}            # ctin -> [inv...]
    b2cl: dict[str, list] = {}           # pos  -> [inv...]
    b2cs: dict[tuple, dict] = {}         # (pos, sply_ty, rate) -> aggregate
    exp: list[dict] = []                 # zero-rated (export/SEZ) invoices
    hsn: dict[tuple, dict] = {}          # (hsn, uqc, rate) -> aggregate
    inv_numbers: list[str] = []

    def _accumulate_hsn(line_items, sign=Decimal("1")):
        for ln in line_items or []:
            key = (str(ln.get("hsn_sac") or "").strip(), str(ln.get("uqc") or "OTH").strip().upper() or "OTH", _D(ln.get("gst_rate")))
            h = hsn.setdefault(key, {"qty": Decimal("0"), "txval": Decimal("0"),
                                     "iamt": Decimal("0"), "camt": Decimal("0"), "samt": Decimal("0")})
            h["qty"] += sign * _D(ln.get("quantity"))
            h["txval"] += sign * _D(ln.get("taxable_amount"))
            h["iamt"] += sign * _D(ln.get("igst"))
            h["camt"] += sign * _D(ln.get("cgst"))
            h["samt"] += sign * _D(ln.get("sgst"))

    for inv in invoices:
        gst = str(inv.get("customer_gstin") or "").strip()
        pos = resolve_state_code(inv.get("place_of_supply"), gst)
        val = _q(_D(inv.get("invoice_total")))
        line_items = inv.get("line_items") or []
        inv_numbers.append(str(inv.get("invoice_number") or ""))
        _accumulate_hsn(line_items)
        record = {
            "number": inv.get("invoice_number"), "date": str(inv.get("invoice_date") or "")[:10],
            "value": val, "pos": pos, "line_items": line_items,
        }
        if any(str(ln.get("supply_type") or "") == "zero_rated" for ln in line_items):
            exp.append(record)
        elif gst:
            b2b.setdefault(gst, []).append(record)
        elif bool(inv.get("is_inter_state")) and val > B2CL_THRESHOLD:
            b2cl.setdefault(pos, []).append(record)
        else:
            sply_ty = "INTER" if inv.get("is_inter_state") else "INTRA"
            for rt, b in _rate_buckets(line_items).items():
                key = (pos, sply_ty, rt)
                agg = b2cs.setdefault(key, {"txval": Decimal("0"), "iamt": Decimal("0"),
                                            "camt": Decimal("0"), "samt": Decimal("0")})
                for k in ("txval", "iamt", "camt", "samt"):
                    agg[k] += b[k]

    cdnr: dict[str, list] = {}
    for note in credit_notes:
        gst = str(note.get("customer_gstin") or "").strip()
        pos = resolve_state_code(note.get("place_of_supply"), gst)
        line_items = note.get("line_items") or []
        _accumulate_hsn(line_items, sign=Decimal("-1"))  # credit notes reduce HSN totals
        if gst:
            cdnr.setdefault(gst, []).append({
                "number": note.get("credit_note_number"), "date": str(note.get("note_date") or "")[:10],
                "value": _q(_D(note.get("note_total"))), "pos": pos, "line_items": line_items,
            })

    report = _gstr1_report(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers, exp)
    report["gstn_json"] = _gstr1_gstn_json(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers, exp)
    return report


def _gstr1_report(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers, exp) -> dict:
    def _section_total(line_item_groups):
        tot = {"txval": Decimal("0"), "tax": Decimal("0")}
        for recs in line_item_groups:
            for rec in recs:
                t = _doc_tax_totals(rec["line_items"])
                tot["txval"] += t["txval"]
                tot["tax"] += t["iamt"] + t["camt"] + t["samt"]
        return {"taxable_value": _q(tot["txval"]), "tax": _q(tot["tax"])}

    b2cs_txval = sum((v["txval"] for v in b2cs.values()), Decimal("0"))
    b2cs_tax = sum((v["iamt"] + v["camt"] + v["samt"] for v in b2cs.values()), Decimal("0"))
    issued = [n for n in inv_numbers if n]

    return {
        "return_type": "GSTR-1",
        "gstin": gstin,
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "b2b": {"recipients": len(b2b), "invoices": sum(len(v) for v in b2b.values()),
                    **_section_total(b2b.values())},
            "b2cl": {"places": len(b2cl), "invoices": sum(len(v) for v in b2cl.values()),
                     **_section_total(b2cl.values())},
            "b2cs": {"rows": len(b2cs), "taxable_value": _q(b2cs_txval), "tax": _q(b2cs_tax)},
            "exp": {"invoices": len(exp), **_section_total([exp])},
            "cdnr": {"recipients": len(cdnr), "notes": sum(len(v) for v in cdnr.values()),
                     **_section_total(cdnr.values())},
            "hsn": {"rows": len(hsn),
                    "taxable_value": _q(sum((h["txval"] for h in hsn.values()), Decimal("0"))),
                    "tax": _q(sum((h["iamt"] + h["camt"] + h["samt"] for h in hsn.values()), Decimal("0")))},
            "docs": {"total": len(issued), "from": min(issued) if issued else None,
                     "to": max(issued) if issued else None},
        },
        "b2cs_rows": [
            {"pos": state_label(pos), "supply_type": sply_ty, "rate": rt,
             "taxable_value": _q(v["txval"]), "igst": _q(v["iamt"]),
             "cgst": _q(v["camt"]), "sgst": _q(v["samt"])}
            for (pos, sply_ty, rt), v in sorted(b2cs.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))
        ],
        "hsn_rows": [
            {"hsn_sac": k[0], "uqc": k[1], "rate": k[2], "quantity": _q(v["qty"]),
             "taxable_value": _q(v["txval"]), "igst": _q(v["iamt"]),
             "cgst": _q(v["camt"]), "sgst": _q(v["samt"])}
            for k, v in sorted(hsn.items(), key=lambda kv: (str(kv[0][0]), kv[0][2]))
        ],
        "notes": [
            "EXP (6A) covers invoices with zero-rated lines, reported WOPAY (supply "
            "under LUT, no tax). Shipping-bill/port details are not captured yet — "
            "fill them in the offline utility before filing. Exports with payment "
            "of IGST are out of scope.",
        ],
    }


def _gstr1_gstn_json(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers, exp) -> dict:
    b2b_json = [
        {"ctin": ctin, "inv": [
            {"inum": r["number"], "idt": r["date"], "val": float(r["value"]), "pos": r["pos"],
             "rchrg": "N", "inv_typ": "R", "itms": _itms(r["line_items"])}
            for r in recs
        ]}
        for ctin, recs in b2b.items()
    ]
    b2cl_json = [
        {"pos": pos, "inv": [
            {"inum": r["number"], "idt": r["date"], "val": float(r["value"]), "itms": _itms(r["line_items"])}
            for r in recs
        ]}
        for pos, recs in b2cl.items()
    ]
    b2cs_json = [
        {"sply_ty": sply_ty, "pos": pos, "typ": "OE", "rt": float(rt),
         "txval": float(_q(v["txval"])), "iamt": float(_q(v["iamt"])),
         "camt": float(_q(v["camt"])), "samt": float(_q(v["samt"])), "csamt": 0.0}
        for (pos, sply_ty, rt), v in b2cs.items()
    ]
    cdnr_json = [
        {"ctin": ctin, "nt": [
            {"ntty": "C", "nt_num": r["number"], "nt_dt": r["date"], "val": float(r["value"]),
             "pos": r["pos"], "rchrg": "N", "inv_typ": "R", "itms": _itms(r["line_items"])}
            for r in recs
        ]}
        for ctin, recs in cdnr.items()
    ]
    hsn_json = [
        {"num": i, "hsn_sc": k[0], "uqc": k[1], "qty": float(_q(v["qty"])),
         "txval": float(_q(v["txval"])), "iamt": float(_q(v["iamt"])),
         "camt": float(_q(v["camt"])), "samt": float(_q(v["samt"])), "csamt": 0.0, "rt": float(k[2])}
        for i, (k, v) in enumerate(sorted(hsn.items(), key=lambda kv: (str(kv[0][0]), kv[0][2])), start=1)
    ]
    # 6A exports/SEZ, reported WOPAY (supply under LUT — no tax). Shipping-bill
    # details are not captured; the offline utility accepts them blank.
    exp_json = [{"exp_typ": "WOPAY", "inv": [
        {"inum": r["number"], "idt": r["date"], "val": float(r["value"]), "itms": _itms(r["line_items"])}
        for r in exp
    ]}] if exp else []
    issued = sorted(n for n in inv_numbers if n)
    doc_issue = {"doc_det": [{"doc_num": 1, "docs": [
        {"num": 1, "from": issued[0] if issued else "", "to": issued[-1] if issued else "",
         "totnum": len(issued), "cancel": 0, "net_issue": len(issued)}
    ]}]} if issued else {"doc_det": []}

    return {
        "gstin": gstin,
        "fp": _ret_period(period),
        "b2b": b2b_json,
        "b2cl": b2cl_json,
        "b2cs": b2cs_json,
        "exp": exp_json,
        "cdnr": cdnr_json,
        "hsn": {"data": hsn_json},
        "doc_issue": doc_issue,
    }


async def _posted_in_period(collection: str, *, tenant_id, app_key, accounting_entity_id, first, last, date_field):
    scope = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    rows = await get_collection(collection).find(scope).to_list(length=20000)
    out = []
    for row in rows:
        if str(row.get("status") or "posted").lower() == "cancelled":
            continue
        raw = str(row.get(date_field) or "")[:10]
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            continue
        if first <= d <= last:
            out.append(row)
    return out


async def build_gstr1(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, period: str, gstin: str | None = None,
) -> dict:
    """Assemble GSTR-1 for a 'YYYY-MM' period from posted invoices + credit notes."""
    first, last = _period_bounds(period)
    invoices = await _posted_in_period(
        SALES_INVOICES_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="invoice_date",
    )
    credit_notes = await _posted_in_period(
        CREDIT_NOTES_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="note_date",
    )
    return assemble_gstr1(gstin=gstin, period=period, invoices=invoices, credit_notes=credit_notes)


# =========================================================================== #
# CMP-08 — quarterly statement-cum-challan for composition dealers (Section 10)
# =========================================================================== #
def _quarter_bounds(quarter: str) -> tuple[date, date]:
    """'YYYY-Q[1-4]' (FY quarters, Q1 = Apr-Jun) -> (first_day, last_day)."""
    year_s, q_s = quarter.upper().split("-Q")
    year, q = int(year_s), int(q_s)
    start_month = {1: 4, 2: 7, 3: 10, 4: 1}[q]
    start_year = year if q < 4 else year + 1
    first = date(start_year, start_month, 1)
    end_month = start_month + 2
    if end_month >= 12:
        last = date(start_year, 12, 31) if end_month == 12 else date(start_year, end_month + 1, 1) - timedelta(days=1)
    else:
        last = date(start_year, end_month + 1, 1) - timedelta(days=1)
    return first, last


def assemble_cmp08(
    *, gstin: str | None, quarter: str, category: str | None, rate, outward_turnover, is_composition: bool,
    rcm_inward: dict | None = None,
) -> dict:
    """Form GST CMP-08 (self-assessed quarterly liability) for a composition
    dealer. Tax = turnover x composition rate, split equally CGST/SGST (a
    composition dealer's outward supply is always intra-state). Inward
    reverse-charge tax comes from RCM-flagged purchase bills in the quarter."""
    rate_d = Decimal(str(rate or 0))
    turnover = _q(_D(outward_turnover))
    out_tax = _q(turnover * rate_d / Decimal("100"))
    cgst = _q(out_tax / Decimal("2"))
    sgst = _q(out_tax - cgst)
    rcm_src = rcm_inward or {}
    rcm = {h: _q(rcm_src.get(h, 0)) for h in ("igst", "cgst", "sgst")}
    total_tax = _q(out_tax + sum(rcm.values()))

    notes = []
    if not is_composition:
        notes.append("This entity is not registered under the composition scheme; "
                      "CMP-08 applies only to composition dealers.")
    notes.append("Inward reverse-charge tax comes from purchase bills flagged RCM; "
                 "it is already booked to GST Payable under RCM (22005) at bill time.")

    report = {
        "return_type": "CMP-08",
        "gstin": gstin,
        "quarter": quarter,
        "composition_category": category,
        "composition_rate": rate_d,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # Table 3 — summary of self-assessed liability.
        "outward_supplies": {
            "turnover": turnover,
            "igst": Decimal("0.00"), "cgst": cgst, "sgst": sgst, "total_tax": out_tax,
        },
        "inward_reverse_charge": rcm,
        "tax_payable": {
            "igst": rcm["igst"], "cgst": _q(cgst + rcm["cgst"]), "sgst": _q(sgst + rcm["sgst"]),
            "interest": Decimal("0.00"), "total": total_tax,
        },
        "notes": notes,
    }
    report["gstn_json"] = {
        "gstin": gstin,
        "ret_period": quarter,
        "summ": {
            "typ_summ": [
                {"typ": "OS", "txval": float(turnover), "iamt": 0.0,
                 "camt": float(cgst), "samt": float(sgst), "csamt": 0.0},
                {"typ": "RC", "txval": float(_q(rcm_src.get("taxable_value", 0))),
                 "iamt": float(rcm["igst"]), "camt": float(rcm["cgst"]),
                 "samt": float(rcm["sgst"]), "csamt": 0.0},
            ],
            "intr_ltfee": {"iamt": 0.0, "camt": 0.0, "samt": 0.0, "csamt": 0.0},
        },
    }
    return report


async def build_cmp08(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, quarter: str, gstin: str | None = None,
) -> dict:
    """Assemble CMP-08 for an FY quarter from the composition turnover (posted
    sales / bills of supply) and the entity's composition rate."""
    first, last = _quarter_bounds(quarter)
    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    sales = await _posted_in_period(
        SALES_INVOICES_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="invoice_date",
    )
    turnover = sum((_D(s.get("taxable_total")) for s in sales), Decimal("0"))
    rcm_inward = await _rcm_inward_for_period(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last,
    )
    return assemble_cmp08(
        gstin=gstin, quarter=quarter, category=profile.get("composition_category"),
        rate=profile.get("composition_rate") or 0, outward_turnover=turnover,
        is_composition=profile.get("is_composition", False), rcm_inward=rcm_inward,
    )


# --------------------------------------------------------------------------- #
# Composition liability posting — book the CMP-08 outward tax in the ledger.
# --------------------------------------------------------------------------- #
COMPOSITION_GST_EXPENSE_CODE = "54007"
GST_NET_PAYABLE_CODE = "22004"


async def find_cmp08_posting(
    session: AsyncSession, *, tenant_id: str, app_key: str, accounting_entity_id: str, quarter: str,
) -> list[dict]:
    rows = (await session.execute(
        select(JournalEntry.id, JournalEntry.entry_date).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.app_key == app_key,
            JournalEntry.accounting_entity_id == accounting_entity_id,
            JournalEntry.source_document_type == "cmp08_liability",
            JournalEntry.source_document_id == f"cmp08:{quarter}",
        ).order_by(JournalEntry.id.asc())
    )).all()
    return [{"journal_entry_id": r.id,
             "entry_date": r.entry_date.isoformat() if hasattr(r.entry_date, "isoformat") else str(r.entry_date)}
            for r in rows]


async def post_cmp08_liability(
    session: AsyncSession, *, tenant_id: str, app_key: str, accounting_entity_id: str,
    quarter: str, created_by: str, idempotency_key: str | None = None,
) -> dict:
    """Book the quarter's composition levy: Dr GST Expense (Composition) 54007,
    Cr GST Payable (Net) 22004 on the quarter-end date. The levy is the
    dealer's own cost (never collected from buyers). Only the OUTWARD tax is
    posted — RCM tax was already credited to 22005 when each bill posted.
    Idempotent per quarter; reverse the journal to redo."""
    from app.accounting.schemas import JournalLineIn, JournalPostRequest
    from app.accounting.service import (
        AccountingValidationError,
        initialize_default_chart_of_accounts,
        post_journal_entry,
    )
    from app.modules.business.opening_close import _account_lookups

    report = await build_cmp08(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, quarter=quarter,
    )
    out_tax = Decimal(str(report["outward_supplies"]["total_tax"]))
    if out_tax <= 0:
        raise AccountingValidationError(f"No composition liability to post for {quarter}")
    existing = await find_cmp08_posting(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, quarter=quarter,
    )
    if existing:
        first_e = existing[0]
        raise AccountingValidationError(
            f"CMP-08 liability for {quarter} is already posted "
            f"(entry #{first_e['journal_entry_id']}). Reverse it to redo."
        )

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
        )
    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    expense = accounts_by_code.get(COMPOSITION_GST_EXPENSE_CODE)
    payable = accounts_by_code.get(GST_NET_PAYABLE_CODE)
    if expense is None or payable is None:
        raise AccountingValidationError(
            f"Composition posting accounts missing ({COMPOSITION_GST_EXPENSE_CODE} / {GST_NET_PAYABLE_CODE})"
        )

    quarter_end = _quarter_bounds(quarter)[1]
    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=quarter_end,
            description=f"Composition GST liability {quarter} (CMP-08)",
            reference=f"CMP08-{quarter}",
            source_module="business",
            source_document_type="cmp08_liability",
            source_document_id=f"cmp08:{quarter}",
            lines=[
                JournalLineIn(account_id=expense["account_id"], debit=out_tax, credit=Decimal("0")),
                JournalLineIn(account_id=payable["account_id"], debit=Decimal("0"), credit=out_tax),
            ],
        ),
        idempotency_key=idempotency_key or f"cmp08-liability:{accounting_entity_id}:{quarter}",
    )
    return {
        "journal_entry_id": journal_entry.id,
        "created": created,
        "quarter": quarter,
        "entry_date": quarter_end.isoformat(),
        "amount": str(out_tax),
    }


# =========================================================================== #
# GSTR-4 — annual return for composition dealers (Section 10), due 30 June
# =========================================================================== #
def _fy_bounds(financial_year: str) -> tuple[int, date, date]:
    """'YYYY-YY' (e.g. '2026-27') -> (start_year, Apr 1, next Mar 31)."""
    start_year = int(str(financial_year)[:4])
    return start_year, date(start_year, 4, 1), date(start_year + 1, 3, 31)


def _inward_rate_rows(buckets: dict) -> list[dict]:
    return [
        {"rate": rt, "taxable_value": _q(b["txval"]), "igst": _q(b["iamt"]),
         "cgst": _q(b["camt"]), "sgst": _q(b["samt"])}
        for rt, b in sorted(buckets.items())
    ]


def assemble_gstr4(
    *, gstin: str | None, financial_year: str, category: str | None, rate,
    quarter_turnovers: dict, inward_registered: dict, inward_unregistered: dict, is_composition: bool,
) -> dict:
    """Annual composition return. Table 5 = the four CMP-08 self-assessed
    liabilities; Table 6 = annual outward turnover x composition rate; Table 4 =
    inward supplies split registered (4A) / unregistered (4C), rate-wise.
    Reverse-charge / imports (4B/4D) are zero until tracked."""
    rate_d = Decimal(str(rate or 0))

    # Table 5 — per-quarter self-assessed liability (from CMP-08).
    table5 = []
    annual_turnover = Decimal("0")
    t5_cgst = t5_sgst = Decimal("0")
    for q in ("Q1", "Q2", "Q3", "Q4"):
        turnover = _q(_D(quarter_turnovers.get(q)))
        tax = _q(turnover * rate_d / Decimal("100"))
        cgst = _q(tax / Decimal("2"))
        sgst = _q(tax - cgst)
        annual_turnover += turnover
        t5_cgst += cgst
        t5_sgst += sgst
        table5.append({"quarter": q, "turnover": turnover, "cgst": cgst, "sgst": sgst, "total_tax": tax})

    # Table 6 — annual outward liability at the composition rate.
    annual_turnover = _q(annual_turnover)
    out_tax = _q(annual_turnover * rate_d / Decimal("100"))
    out_cgst = _q(out_tax / Decimal("2"))
    out_sgst = _q(out_tax - out_cgst)

    def _sum_tax(rows):
        return _q(sum((r["igst"] + r["cgst"] + r["sgst"] for r in rows), Decimal("0")))

    reg_rows = _inward_rate_rows(inward_registered)
    unreg_rows = _inward_rate_rows(inward_unregistered)

    report = {
        "return_type": "GSTR-4",
        "gstin": gstin,
        "financial_year": financial_year,
        "composition_category": category,
        "composition_rate": rate_d,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # Table 5 — summary of self-assessed liability (CMP-08).
        "cmp08_summary": {
            "quarters": table5,
            "total_turnover": annual_turnover,
            "cgst": _q(t5_cgst), "sgst": _q(t5_sgst), "total_tax": _q(t5_cgst + t5_sgst),
        },
        # Table 6 — outward supplies (composition liability).
        "outward_supplies": {
            "turnover": annual_turnover, "rate": rate_d,
            "cgst": out_cgst, "sgst": out_sgst, "total_tax": out_tax,
        },
        # Table 4 — inward supplies.
        "inward_supplies": {
            "registered": {"rows": reg_rows,
                           "taxable_value": _q(sum((r["taxable_value"] for r in reg_rows), Decimal("0"))),
                           "tax": _sum_tax(reg_rows)},
            "unregistered": {"rows": unreg_rows,
                             "taxable_value": _q(sum((r["taxable_value"] for r in unreg_rows), Decimal("0"))),
                             "tax": _sum_tax(unreg_rows)},
        },
        "notes": [],
    }
    if not is_composition:
        report["notes"].append("This entity is not registered under the composition scheme; "
                                "GSTR-4 applies only to composition dealers.")
    report["notes"].append("Reverse-charge (4B) and import-of-services (4D) inward supplies are "
                            "reported as zero until those flows are tracked.")

    def _amt(c, s, i=Decimal("0")):
        return {"iamt": float(i), "camt": float(c), "samt": float(s), "csamt": 0.0}

    report["gstn_json"] = {
        "gstin": gstin,
        "fy": financial_year,
        "txos": [{"rt": float(rate_d), "txval": float(annual_turnover), **_amt(out_cgst, out_sgst)}],
        "inward_sup": (
            [{"sup_typ": "REG", "rt": float(r["rate"]), "txval": float(r["taxable_value"]),
              **_amt(r["cgst"], r["sgst"], r["igst"])} for r in reg_rows]
            + [{"sup_typ": "UNREG", "rt": float(r["rate"]), "txval": float(r["taxable_value"]),
                **_amt(r["cgst"], r["sgst"], r["igst"])} for r in unreg_rows]
        ),
        "cmp08_summ": [
            {"quarter": t["quarter"], "txval": float(t["turnover"]), **_amt(t["cgst"], t["sgst"])}
            for t in table5
        ],
    }
    return report


async def build_gstr4(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, financial_year: str, gstin: str | None = None,
) -> dict:
    """Assemble GSTR-4 for a financial year ('YYYY-YY') from the four quarters'
    composition turnover and the year's inward purchases."""
    start_year, fy_first, fy_last = _fy_bounds(financial_year)
    profile = await get_gst_profile(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )

    quarter_turnovers: dict[str, Decimal] = {}
    for q in (1, 2, 3, 4):
        first, last = _quarter_bounds(f"{start_year}-Q{q}")
        sales = await _posted_in_period(
            SALES_INVOICES_COLLECTION, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="invoice_date",
        )
        quarter_turnovers[f"Q{q}"] = sum((_D(s.get("taxable_total")) for s in sales), Decimal("0"))

    bills = await _posted_in_period(
        PURCHASE_BILLS_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=fy_first, last=fy_last, date_field="bill_date",
    )
    inward_registered: dict = {}
    inward_unregistered: dict = {}
    for bill in bills:
        target = inward_registered if str(bill.get("vendor_gstin") or "").strip() else inward_unregistered
        for rt, b in _rate_buckets(bill.get("line_items") or []).items():
            agg = target.setdefault(rt, {"txval": Decimal("0"), "iamt": Decimal("0"),
                                         "camt": Decimal("0"), "samt": Decimal("0")})
            for k in ("txval", "iamt", "camt", "samt"):
                agg[k] += b[k]

    return assemble_gstr4(
        gstin=gstin, financial_year=financial_year, category=profile.get("composition_category"),
        rate=profile.get("composition_rate") or 0, quarter_turnovers=quarter_turnovers,
        inward_registered=inward_registered, inward_unregistered=inward_unregistered,
        is_composition=profile.get("is_composition", False),
    )


# =========================================================================== #
# GSTR-2B / ITC reconciliation — match the portal's auto-drafted ITC statement
# against the input GST we actually booked (Section 16(2)(aa) / Rule 36(4))
# =========================================================================== #
def _norm_inv(num) -> str:
    return "".join(str(num or "").split()).upper()


def parse_gstr2b(payload: dict) -> list[dict]:
    """Normalise an uploaded GSTR-2B JSON into supplier B2B invoices with ITC.

    Tolerant of the portal's nesting (`data.docdata.b2b`) and of the per-item tax
    keys being either igst/cgst/sgst or iamt/camt/samt.
    """
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    docdata = data.get("docdata") if isinstance(data.get("docdata"), dict) else data
    rows: list[dict] = []
    for sup in docdata.get("b2b") or []:
        ctin = str(sup.get("ctin") or "").strip()
        for inv in sup.get("inv") or []:
            igst = cgst = sgst = Decimal("0")
            for itm in inv.get("itms") or []:
                d = itm.get("itm_det") if isinstance(itm.get("itm_det"), dict) else itm
                igst += _D(d.get("igst") if d.get("igst") is not None else d.get("iamt"))
                cgst += _D(d.get("cgst") if d.get("cgst") is not None else d.get("camt"))
                sgst += _D(d.get("sgst") if d.get("sgst") is not None else d.get("samt"))
            rows.append({
                "gstin": ctin,
                "invoice_number": str(inv.get("inum") or "").strip(),
                "date": str(inv.get("dt") or inv.get("idt") or "")[:10],
                "value": _q(_D(inv.get("val"))),
                "igst": _q(igst), "cgst": _q(cgst), "sgst": _q(sgst),
                "tax_total": _q(igst + cgst + sgst),
            })
    return rows


def reconcile_gstr2b(
    *, period: str, gstr2b_invoices: list[dict], book_invoices: list[dict], tolerance=Decimal("1.00"),
) -> dict:
    """Match GSTR-2B supplier invoices against booked purchases by (GSTIN, invoice
    no.) and classify: matched, mismatch (amounts differ), in 2B only (available,
    not booked), in books only (ITC claimed but not reflected — at risk)."""
    by_2b = {(g["gstin"], _norm_inv(g["invoice_number"])): g for g in gstr2b_invoices}
    by_book = {(b["gstin"], _norm_inv(b["invoice_number"])): b for b in book_invoices}

    matched, mismatch, only_2b, only_books = [], [], [], []
    for key, g in by_2b.items():
        b = by_book.get(key)
        if b is None:
            only_2b.append(g)
        elif abs(g["tax_total"] - b["tax_total"]) <= tolerance:
            matched.append({"gstin": g["gstin"], "invoice_number": g["invoice_number"],
                            "itc": g["tax_total"], "book_bill_id": b.get("bill_id")})
        else:
            mismatch.append({"gstin": g["gstin"], "invoice_number": g["invoice_number"],
                             "itc_2b": g["tax_total"], "itc_books": b["tax_total"],
                             "difference": _q(g["tax_total"] - b["tax_total"]),
                             "book_bill_id": b.get("bill_id")})
    for key, b in by_book.items():
        if key not in by_2b:
            only_books.append(b)

    def _sum(rows, field):
        return _q(sum((r[field] for r in rows), Decimal("0")))

    itc_2b = _q(sum((g["tax_total"] for g in gstr2b_invoices), Decimal("0")))
    itc_books = _q(sum((b["tax_total"] for b in book_invoices), Decimal("0")))
    matched_itc = _sum(matched, "itc")
    return {
        "report_type": "GSTR-2B-reconciliation",
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "itc_as_per_2b": itc_2b,
            "itc_as_per_books": itc_books,
            "matched_itc": matched_itc,
            "matched_count": len(matched),
            "mismatch_count": len(mismatch),
            "mismatch_itc_difference": _sum(mismatch, "difference"),
            # In 2B but not booked: ITC available you may have missed recording.
            "available_not_booked": _sum(only_2b, "tax_total"),
            "available_not_booked_count": len(only_2b),
            # Booked but absent from 2B: ITC at risk / not yet eligible.
            "at_risk_not_in_2b": _sum(only_books, "tax_total"),
            "at_risk_count": len(only_books),
        },
        "matched": matched,
        "mismatch": mismatch,
        "in_2b_not_in_books": only_2b,
        "in_books_not_in_2b": only_books,
        "notes": [
            "ITC under 'in books, not in 2B' is at risk under Section 16(2)(aa) — "
            "claim only what is reflected in GSTR-2B.",
            "Matching is by supplier GSTIN + invoice number; amounts within "
            f"Rs {tolerance} are treated as agreeing.",
        ],
    }


async def build_gstr2b_reconciliation(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, period: str, gstr2b_payload: dict,
) -> dict:
    """Reconcile an uploaded GSTR-2B for a 'YYYY-MM' period against the input GST
    booked on posted purchase bills (ITC-claimed, registered suppliers) that month."""
    first, last = _period_bounds(period)
    bills = await _posted_in_period(
        PURCHASE_BILLS_COLLECTION, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, first=first, last=last, date_field="bill_date",
    )
    book_invoices = []
    for bill in bills:
        if bill.get("itc_claimed") is False:           # composition bills claim no ITC
            continue
        gstin = str(bill.get("vendor_gstin") or "").strip()
        if not gstin:                                  # 2B only carries registered suppliers
            continue
        igst, cgst, sgst = _D(bill.get("igst_total")), _D(bill.get("cgst_total")), _D(bill.get("sgst_total"))
        book_invoices.append({
            "gstin": gstin, "invoice_number": str(bill.get("bill_number") or "").strip(),
            "date": str(bill.get("bill_date") or "")[:10], "bill_id": bill.get("bill_id"),
            "igst": _q(igst), "cgst": _q(cgst), "sgst": _q(sgst), "tax_total": _q(igst + cgst + sgst),
        })
    return reconcile_gstr2b(
        period=period, gstr2b_invoices=parse_gstr2b(gstr2b_payload or {}), book_invoices=book_invoices,
    )
