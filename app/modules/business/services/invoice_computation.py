"""Shared invoice line computation, numbering, and response shaping.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
_reserve_invoice_number uses runtime lookup on the service module for
get_collection so existing tests that monkeypatch business_service.get_collection
keep working.
"""
from decimal import Decimal, ROUND_HALF_UP

from app.accounting.service import AccountingValidationError
from app.modules.business import service as business_service
from app.modules.business.schemas import SalesInvoiceCreateRequest


def _q2(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _invoice_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = business_service._json_safe_doc(doc)
    business_service._apply_approval_defaults(result)
    result.setdefault("created", created)
    return result


def _compute_invoice_lines(payload: SalesInvoiceCreateRequest, *, composition: bool = False):
    """Compute per-line taxable + GST split and roll up invoice totals.

    Each monetary value is quantized to 2dp; totals are sums of rounded line
    values so debits and credits stay balanced. For intra-state supply GST is
    split CGST/SGST (with the remainder assigned to SGST to avoid rounding
    drift); for inter-state it posts fully to IGST.
    """
    lines: list[dict] = []
    taxable_total = Decimal("0.00")
    cgst_total = Decimal("0.00")
    sgst_total = Decimal("0.00")
    igst_total = Decimal("0.00")
    for item in payload.line_items:
        taxable = _q2(Decimal(item.quantity) * Decimal(item.rate))
        # Composition dealers issue a Bill of Supply — no GST is charged or split,
        # whatever rate is on the line. gst_amount of 0 zeroes every head below.
        # Zero-rated (export/SEZ under LUT) lines likewise carry no tax.
        is_zero_rated = getattr(item, "supply_type", "taxable") == "zero_rated"
        gst_amount = Decimal("0.00") if (composition or is_zero_rated) else _q2(taxable * Decimal(item.gst_rate) / Decimal("100"))
        if payload.is_inter_state:
            cgst = Decimal("0.00")
            sgst = Decimal("0.00")
            igst = gst_amount
        else:
            cgst = _q2(gst_amount / Decimal("2"))
            sgst = _q2(gst_amount - cgst)
            igst = Decimal("0.00")
        line_total = _q2(taxable + cgst + sgst + igst)
        lines.append({
            "description": item.description.strip(),
            "hsn_sac": item.hsn_sac,
            "uqc": getattr(item, "uqc", None),
            "supply_type": getattr(item, "supply_type", "taxable"),
            "item_id": getattr(item, "item_id", None),
            "quantity": str(Decimal(item.quantity)),
            "rate": business_service._money(item.rate),
            "gst_rate": str(Decimal(item.gst_rate)),
            "cost_centre_id": getattr(item, "cost_centre_id", None),
            "project_id": getattr(item, "project_id", None),
            "taxable_amount": str(taxable),
            "cgst": str(cgst),
            "sgst": str(sgst),
            "igst": str(igst),
            "line_total": str(line_total),
        })
        taxable_total += taxable
        cgst_total += cgst
        sgst_total += sgst
        igst_total += igst
    gst_total = cgst_total + sgst_total + igst_total
    invoice_total = taxable_total + gst_total
    return lines, taxable_total, cgst_total, sgst_total, igst_total, gst_total, invoice_total


def _financial_year_strings(invoice_date):
    if invoice_date.month >= 4:
        start, end = invoice_date.year, invoice_date.year + 1
    else:
        start, end = invoice_date.year - 1, invoice_date.year
    full = f"{start}-{end}"
    short = f"{start}-{str(end)[-2:]}"
    return full, short


def _format_invoice_number(numbering, *, financial_year: str, fy_short: str, seq: int) -> str:
    padded = str(seq).zfill(int(getattr(numbering, "seq_padding", 6) or 6))
    return (
        str(getattr(numbering, "number_format", "{PREFIX}-{FY}-{SEQ}") or "{PREFIX}-{FY}-{SEQ}")
        .replace("{PREFIX}", str(getattr(numbering, "prefix", "INV") or "INV"))
        .replace("{FYSHORT}", fy_short)
        .replace("{FY}", financial_year)
        .replace("{SEQ}", padded)
    )


def _validate_required_invoice_fields(payload: SalesInvoiceCreateRequest, settings: dict) -> None:
    """Enforce 'required' rules an admin set on standard optional fields."""
    field_config = settings.get("field_config") or {}
    labels = {
        "due_date": "Due date",
        "place_of_supply": "Place of supply",
        "reference": "Reference / PO",
        "notes": "Notes",
    }
    for key in ("due_date", "place_of_supply", "reference", "notes"):
        rule = field_config.get(key) or {}
        if rule.get("required") and not getattr(payload, key, None):
            raise AccountingValidationError(f"{labels[key]} is required by this business's invoice settings")
    hsn_rule = field_config.get("hsn_sac") or {}
    if hsn_rule.get("required"):
        for item in payload.line_items:
            if not (item.hsn_sac and str(item.hsn_sac).strip()):
                raise AccountingValidationError("HSN/SAC is required on every line by this business's invoice settings")


async def _reserve_invoice_number(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    invoice_date,
    numbering,
) -> str:
    financial_year, fy_short = _financial_year_strings(invoice_date)
    reset_yearly = bool(getattr(numbering, "reset_yearly", True))
    scope = financial_year if reset_yearly else "all"
    counter_id = f"{tenant_id}:{app_key}:{accounting_entity_id}:sales_invoice:{scope}"
    counters = business_service.get_collection(business_service.VOUCHER_COUNTERS_COLLECTION)
    try:
        from pymongo import ReturnDocument

        counter = await counters.find_one_and_update(
            {"_id": counter_id},
            {
                "$inc": {"seq": 1},
                "$setOnInsert": {
                    "tenant_id": tenant_id,
                    "app_key": app_key,
                    "accounting_entity_id": accounting_entity_id,
                    "voucher_type": "sales_invoice",
                    "financial_year": financial_year,
                    "created_at": business_service._now(),
                },
                "$set": {"updated_at": business_service._now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        raw_seq = int((counter or {}).get("seq") or 1)
    except Exception:
        existing = await business_service.get_collection(business_service.SALES_INVOICES_COLLECTION).count_documents(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
        )
        raw_seq = int(existing) + 1
    # Honor a custom starting number: first invoice == start_number.
    seq = int(getattr(numbering, "start_number", 1) or 1) + raw_seq - 1
    return _format_invoice_number(numbering, financial_year=financial_year, fy_short=fy_short, seq=seq)
