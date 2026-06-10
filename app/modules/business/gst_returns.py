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
    _compute_gst_setoff,
    _period_bounds,
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

    Sections: B2B (4A), B2CL (5), B2CS (7), CDNR (9B), HSN (12), DOCS (13).
    Export/SEZ (zero-rated) sections are out of scope for v1 (domestic supply);
    a note flags it. Each figure comes from the stored documents.
    """
    b2b: dict[str, list] = {}            # ctin -> [inv...]
    b2cl: dict[str, list] = {}           # pos  -> [inv...]
    b2cs: dict[tuple, dict] = {}         # (pos, sply_ty, rate) -> aggregate
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
        if gst:
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

    report = _gstr1_report(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers)
    report["gstn_json"] = _gstr1_gstn_json(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers)
    return report


def _gstr1_report(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers) -> dict:
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
            "Export / SEZ (zero-rated) supplies are out of scope in this v1 and are "
            "not split into a separate section.",
        ],
    }


def _gstr1_gstn_json(gstin, period, b2b, b2cl, b2cs, cdnr, hsn, inv_numbers) -> dict:
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
