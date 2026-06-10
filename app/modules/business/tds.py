"""TDS / TCS (Income-tax Act, 1961) — deduction at source on purchases and
collection at source on sales, plus the quarterly register that feeds Form
26Q / 27EQ preparation.

Clean-room implementation from the published Income-tax Act rate tables
(FY 2025-26). Design rules, mirroring the GST modules:

  * Section masters are data, not logic — rates are defaults the user can
    override per document (rates change by Finance Act; an override never
    blocks a filing).
  * TDS is computed on the taxable value EXCLUDING GST when GST is shown
    separately on the invoice (CBDT Circular 23/2017).
  * TCS under 206C(1H) is collected on the consideration INCLUDING GST
    (CBDT Circular 17/2020), so its base is the invoice total.
  * Deduction happens at bill (credit) time — "credit or payment, whichever
    is earlier" — the standard case for books-of-account driven deduction.
  * Pure assemblers take already-fetched documents; async builders gather.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# Section 206AA: deduction at a higher rate when the deductee has no PAN.
# We surface a `pan_missing` flag rather than silently re-rating, so the
# accountant decides (maker-checker; the override field applies 20% if chosen).
NO_PAN_TDS_RATE = Decimal("20")

# TDS sections relevant to a books-driven SME purchase/expense flow.
# rate = default % for the FY 2025-26 published table; threshold = annual or
# per-transaction trigger (informational — books may legitimately deduct below it).
TDS_SECTIONS: dict[str, dict] = {
    "194A": {"label": "Interest other than securities", "rate": Decimal("10"), "threshold": "₹5,000–₹50,000/yr by payer type"},
    "194C-IND": {"label": "Contractor payment (individual/HUF)", "rate": Decimal("1"), "threshold": "₹30,000/contract or ₹1,00,000/yr"},
    "194C": {"label": "Contractor payment (others)", "rate": Decimal("2"), "threshold": "₹30,000/contract or ₹1,00,000/yr"},
    "194H": {"label": "Commission or brokerage", "rate": Decimal("2"), "threshold": "₹20,000/yr"},
    "194I-PM": {"label": "Rent — plant & machinery", "rate": Decimal("2"), "threshold": "₹50,000/month"},
    "194I-LB": {"label": "Rent — land or building", "rate": Decimal("10"), "threshold": "₹50,000/month"},
    "194J-TECH": {"label": "Technical services / call centre", "rate": Decimal("2"), "threshold": "₹50,000/yr"},
    "194J": {"label": "Professional fees", "rate": Decimal("10"), "threshold": "₹50,000/yr"},
    "194Q": {"label": "Purchase of goods", "rate": Decimal("0.1"), "threshold": "above ₹50 lakh/yr per seller"},
}

# TCS sections for the sales side. 206C(1H) is the common SME case.
TCS_SECTIONS: dict[str, dict] = {
    "206C-1H": {"label": "Sale of goods", "rate": Decimal("0.1"), "threshold": "above ₹50 lakh/yr per buyer"},
    "206C-SCRAP": {"label": "Sale of scrap", "rate": Decimal("1"), "threshold": "per transaction"},
    "206C-TIMBER": {"label": "Timber / forest produce", "rate": Decimal("2.5"), "threshold": "per transaction"},
}


def list_sections() -> dict:
    """Section masters for the frontend dropdowns (JSON-safe)."""
    def rows(table: dict) -> list[dict]:
        return [
            {"section": code, "label": meta["label"], "rate": str(meta["rate"]), "threshold": meta["threshold"]}
            for code, meta in table.items()
        ]
    return {"tds": rows(TDS_SECTIONS), "tcs": rows(TCS_SECTIONS), "no_pan_rate": str(NO_PAN_TDS_RATE)}


def compute_tds(section: str, base_amount, rate_override=None) -> tuple[Decimal, Decimal]:
    """(rate, amount) for a TDS deduction on `base_amount` (GST-exclusive)."""
    if section not in TDS_SECTIONS:
        raise ValueError(f"Unknown TDS section: {section}")
    rate = Decimal(str(rate_override)) if rate_override is not None else TDS_SECTIONS[section]["rate"]
    if rate < Decimal("0") or rate > Decimal("100"):
        raise ValueError("TDS rate must be between 0 and 100")
    return rate, _q2(Decimal(str(base_amount)) * rate / Decimal("100"))


def compute_tcs(section: str, base_amount, rate_override=None) -> tuple[Decimal, Decimal]:
    """(rate, amount) for a TCS collection on `base_amount` (GST-inclusive)."""
    if section not in TCS_SECTIONS:
        raise ValueError(f"Unknown TCS section: {section}")
    rate = Decimal(str(rate_override)) if rate_override is not None else TCS_SECTIONS[section]["rate"]
    if rate < Decimal("0") or rate > Decimal("100"):
        raise ValueError("TCS rate must be between 0 and 100")
    return rate, _q2(Decimal(str(base_amount)) * rate / Decimal("100"))


def _register_side(entries: list[dict], section_table: dict) -> dict:
    """Group raw register entries section-wise with per-section and grand totals."""
    by_section: dict[str, dict] = {}
    for e in entries:
        sec = e["section"]
        bucket = by_section.setdefault(sec, {
            "section": sec,
            "label": (section_table.get(sec) or {}).get("label", sec),
            "entries": [],
            "total_base": Decimal("0.00"),
            "total_tax": Decimal("0.00"),
        })
        bucket["entries"].append(e)
        bucket["total_base"] += Decimal(e["base_amount"])
        bucket["total_tax"] += Decimal(e["tax_amount"])
    sections = []
    grand_base = Decimal("0.00")
    grand_tax = Decimal("0.00")
    for sec in sorted(by_section):
        bucket = by_section[sec]
        bucket["entries"].sort(key=lambda e: (e["doc_date"], e["doc_number"]))
        grand_base += bucket["total_base"]
        grand_tax += bucket["total_tax"]
        bucket["total_base"] = str(_q2(bucket["total_base"]))
        bucket["total_tax"] = str(_q2(bucket["total_tax"]))
        sections.append(bucket)
    return {
        "sections": sections,
        "total_base": str(_q2(grand_base)),
        "total_tax": str(_q2(grand_tax)),
        "entry_count": len(entries),
        "pan_missing_count": sum(1 for e in entries if e.get("pan_missing")),
    }


def assemble_tds_register(*, quarter: str, period_start: date, period_end: date,
                          tds_entries: list[dict], tcs_entries: list[dict]) -> dict:
    """Quarterly TDS/TCS register (Form 26Q / 27EQ working paper).

    Entries are dicts with: section, doc_date, doc_number, party_name, pan,
    pan_missing, base_amount, rate, tax_amount, doc_id. Pure — callers fetch.
    """
    return {
        "quarter": quarter,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "tds": _register_side(tds_entries, TDS_SECTIONS),   # feeds Form 26Q
        "tcs": _register_side(tcs_entries, TCS_SECTIONS),   # feeds Form 27EQ
        "generated_notes": [
            "TDS is deducted on the GST-exclusive taxable value (CBDT Circular 23/2017).",
            "TCS u/s 206C(1H) is collected on the GST-inclusive consideration (CBDT Circular 17/2020).",
            "Deposit deducted/collected tax by the 7th of the following month (challan ITNS 281).",
            "Entries flagged 'PAN missing' attract a 20% rate under section 206AA — verify before filing.",
        ],
    }


def _doc_register_entry(doc: dict, *, kind: str) -> dict:
    """Map a posted purchase bill (kind='tds') or sales invoice (kind='tcs')
    to a register entry. Caller guarantees the doc carries the tax fields."""
    if kind == "tds":
        return {
            "section": doc["tds_section"],
            "doc_date": doc["bill_date"],
            "doc_number": doc["bill_number"],
            "doc_id": doc["bill_id"],
            "party_name": doc.get("vendor_name"),
            "pan": doc.get("deductee_pan"),
            "pan_missing": bool(doc.get("deductee_pan_missing")),
            "base_amount": doc["tds_base_amount"],
            "rate": doc["tds_rate"],
            "tax_amount": doc["tds_amount"],
        }
    return {
        "section": doc["tcs_section"],
        "doc_date": doc["invoice_date"],
        "doc_number": doc["invoice_number"],
        "doc_id": doc["invoice_id"],
        "party_name": doc.get("customer_name"),
        "pan": doc.get("collectee_pan"),
        "pan_missing": bool(doc.get("collectee_pan_missing")),
        "base_amount": doc["tcs_base_amount"],
        "rate": doc["tcs_rate"],
        "tax_amount": doc["tcs_amount"],
    }


async def build_tds_register(*, tenant_id: str, app_key: str, accounting_entity_id: str, quarter: str) -> dict:
    """Gather posted documents with TDS/TCS in the FY quarter and assemble."""
    from app.modules.business.gst_returns import _quarter_bounds
    from app.modules.business.service import PURCHASE_BILLS_COLLECTION, SALES_INVOICES_COLLECTION
    from app.db.mongo import get_collection

    period_start, period_end = _quarter_bounds(quarter)
    scope = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id,
             "status": "posted"}

    bills = await get_collection(PURCHASE_BILLS_COLLECTION).find({
        **scope,
        "bill_date": {"$gte": period_start.isoformat(), "$lte": period_end.isoformat()},
        "tds_section": {"$nin": [None, ""]},
    }).to_list(length=5000)
    invoices = await get_collection(SALES_INVOICES_COLLECTION).find({
        **scope,
        "invoice_date": {"$gte": period_start.isoformat(), "$lte": period_end.isoformat()},
        "tcs_section": {"$nin": [None, ""]},
    }).to_list(length=5000)

    return assemble_tds_register(
        quarter=quarter,
        period_start=period_start,
        period_end=period_end,
        tds_entries=[_doc_register_entry(b, kind="tds") for b in bills],
        tcs_entries=[_doc_register_entry(i, kind="tcs") for i in invoices],
    )
