"""e-Invoicing (IRN) foundation — credential-free.

Generating an IRN requires calling the government's Invoice Registration
Portal (IRP), which needs GSP/sandbox credentials the tenant must obtain.
Everything BEFORE and AFTER that call is built here, clean-room to the GSTN
e-invoice schema (INV-01 / version 1.1):

  * `validate_einvoice_readiness` — every reason the IRP would reject the
    document, caught locally first (missing GSTINs, HSN, pincodes, doc-no
    format ...).
  * `assemble_inv01_payload` — the upload-ready INV-01 JSON built purely from
    the posted invoice + seller profile + buyer party. The accountant can
    upload it to the e-invoice portal / offline utility today.
  * Manual IRN recording — once the portal returns the IRN + Ack, it is
    recorded against the invoice (status 'registered'), giving a complete
    audit trail without any API integration.

When IRP credentials exist, an API client only has to POST the same payload
and call the same recording step — the seam is deliberate.
"""
import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

EINVOICE_SCHEMA_VERSION = "1.1"

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value if value not in (None, "") else 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _f(value) -> float:
    return float(_q2(value))


def _now() -> datetime:
    return datetime.now(timezone.utc)


_GSTIN_RE = re.compile(r"^\d{2}[0-9A-Z]{13}$")
# IRP rule: document number <= 16 chars, alphanumeric plus '/' and '-',
# must not start with 0, '/' or '-'.
_DOCNO_RE = re.compile(r"^[a-zA-Z1-9][a-zA-Z0-9/-]{0,15}$")
_PIN_RE = re.compile(r"\b([1-9]\d{5})\b")


def _ddmmyyyy(iso_date: str) -> str:
    y, m, d = str(iso_date)[:10].split("-")
    return f"{d}/{m}/{y}"


def _extract_pin(text: str | None) -> str | None:
    match = _PIN_RE.search(str(text or ""))
    return match.group(1) if match else None


def _supply_type(invoice: dict, buyer_gstin: str) -> str:
    """INV-01 SupTyp: zero-rated documents are SEZ (with GSTIN) or export
    (without), both 'without payment' since zero-rated lines carry no tax
    here (LUT). Everything else is B2B."""
    zero_rated = any(
        str(ln.get("supply_type") or "") == "zero_rated"
        for ln in invoice.get("line_items") or []
    )
    if zero_rated:
        return "SEZWOP" if buyer_gstin else "EXPWOP"
    return "B2B"


def validate_einvoice_readiness(*, invoice: dict, seller: dict, buyer: dict) -> list[str]:
    """Every local reason the IRP would reject this document. Empty = ready."""
    errors: list[str] = []

    seller_gstin = str(seller.get("gstin") or "").strip().upper()
    if not _GSTIN_RE.fullmatch(seller_gstin):
        errors.append("Seller GSTIN is missing or malformed — set it in Invoice Settings → branding")
    if not str(seller.get("business_name") or "").strip():
        errors.append("Seller legal name is missing — set the business name in Invoice Settings")
    if not _extract_pin(seller.get("address")):
        errors.append("Seller address needs a 6-digit pincode (add it to the address in Invoice Settings)")

    sup_typ = _supply_type(invoice, str(buyer.get("gstin") or "").strip())
    buyer_gstin = str(buyer.get("gstin") or "").strip().upper()
    if sup_typ == "B2B":
        if not _GSTIN_RE.fullmatch(buyer_gstin):
            errors.append("Buyer GSTIN is missing or malformed — e-invoicing applies to B2B/SEZ/export documents only")
    elif sup_typ == "SEZWOP" and not _GSTIN_RE.fullmatch(buyer_gstin):
        errors.append("SEZ buyer GSTIN is malformed")
    if sup_typ != "EXPWOP" and not _extract_pin(buyer.get("pincode") or buyer.get("billing_address")):
        errors.append("Buyer needs a 6-digit pincode on the party record")

    doc_no = str(invoice.get("invoice_number") or "").strip()
    if not _DOCNO_RE.fullmatch(doc_no):
        errors.append("Invoice number must be 1-16 chars (letters, digits, '/', '-') and not start with 0/'/'/'-'")
    if not invoice.get("invoice_date"):
        errors.append("Invoice date is missing")
    if str(invoice.get("status") or "").lower() != "posted":
        errors.append("Only posted invoices can be registered")
    if invoice.get("is_composition") or invoice.get("document_type") == "bill_of_supply":
        errors.append("Composition dealers (Bill of Supply) are outside the e-invoicing mandate")

    for idx, ln in enumerate(invoice.get("line_items") or [], start=1):
        hsn = str(ln.get("hsn_sac") or "").strip()
        if not re.fullmatch(r"\d{4,8}", hsn):
            errors.append(f"Line {idx}: HSN/SAC must be 4-8 digits (got '{hsn or 'blank'}')")
    if not invoice.get("line_items"):
        errors.append("The invoice has no line items")
    return errors


def assemble_inv01_payload(*, invoice: dict, seller: dict, buyer: dict) -> dict:
    """The INV-01 JSON the IRP accepts (and the offline utility uploads).
    Pure — every figure comes from the posted invoice document."""
    seller_gstin = str(seller.get("gstin") or "").strip().upper()
    buyer_gstin = str(buyer.get("gstin") or "").strip().upper()
    sup_typ = _supply_type(invoice, buyer_gstin)
    buyer_pos = buyer_gstin[:2] if buyer_gstin else "96"  # 96 = other country (exports)

    items = []
    total_ass = Decimal("0.00")
    total_igst = Decimal("0.00")
    total_cgst = Decimal("0.00")
    total_sgst = Decimal("0.00")
    for idx, ln in enumerate(invoice.get("line_items") or [], start=1):
        qty = Decimal(str(ln.get("quantity") or 0))
        ass = _q2(ln.get("taxable_amount"))
        igst, cgst, sgst = _q2(ln.get("igst")), _q2(ln.get("cgst")), _q2(ln.get("sgst"))
        hsn = str(ln.get("hsn_sac") or "").strip()
        items.append({
            "SlNo": str(idx),
            "PrdDesc": str(ln.get("description") or "")[:300],
            # Services sit in SAC chapter 99.
            "IsServc": "Y" if hsn.startswith("99") else "N",
            "HsnCd": hsn,
            "Qty": float(qty),
            "Unit": (str(ln.get("uqc") or "").strip().upper() or "OTH"),
            "UnitPrice": _f(ln.get("rate")),
            "TotAmt": _f(ass),
            "AssAmt": _f(ass),
            "GstRt": float(Decimal(str(ln.get("gst_rate") or 0))),
            "IgstAmt": _f(igst),
            "CgstAmt": _f(cgst),
            "SgstAmt": _f(sgst),
            "CesAmt": 0.0,
            "TotItemVal": _f(ass + igst + cgst + sgst),
        })
        total_ass += ass
        total_igst += igst
        total_cgst += cgst
        total_sgst += sgst

    grand_total = _q2(invoice.get("grand_total") or invoice.get("invoice_total"))
    seller_pin = _extract_pin(seller.get("address")) or "000000"
    buyer_pin = _extract_pin(buyer.get("pincode") or buyer.get("billing_address")) or ("999999" if sup_typ == "EXPWOP" else "000000")

    return {
        "Version": EINVOICE_SCHEMA_VERSION,
        "TranDtls": {
            "TaxSch": "GST",
            "SupTyp": sup_typ,
            "RegRev": "N",
            "IgstOnIntra": "N",
        },
        "DocDtls": {
            "Typ": "INV",
            "No": str(invoice.get("invoice_number") or ""),
            "Dt": _ddmmyyyy(invoice.get("invoice_date")),
        },
        "SellerDtls": {
            "Gstin": seller_gstin,
            "LglNm": str(seller.get("business_name") or "")[:100],
            "Addr1": (str(seller.get("address") or "").strip() or "Address on file")[:100],
            "Loc": (str(seller.get("location") or "").strip() or "India")[:50],
            "Pin": int(seller_pin),
            "Stcd": seller_gstin[:2] if seller_gstin else "",
        },
        "BuyerDtls": {
            "Gstin": buyer_gstin or "URP",   # URP = unregistered (exports)
            "LglNm": str(buyer.get("party_name") or "")[:100],
            "Pos": buyer_pos,
            "Addr1": (str(buyer.get("billing_address") or "").strip() or "Address on file")[:100],
            "Loc": (str(buyer.get("city") or "").strip() or "India")[:50],
            "Pin": int(buyer_pin),
            "Stcd": buyer_gstin[:2] if buyer_gstin else "96",
        },
        "ItemList": items,
        "ValDtls": {
            "AssVal": _f(total_ass),
            "IgstVal": _f(total_igst),
            "CgstVal": _f(total_cgst),
            "SgstVal": _f(total_sgst),
            "CesVal": 0.0,
            "Discount": 0.0,
            "OthChrg": _f(grand_total - total_ass - total_igst - total_cgst - total_sgst),  # e.g. TCS
            "RndOffAmt": 0.0,
            "TotInvVal": _f(grand_total),
        },
    }


# --------------------------------------------------------------------------- #
# Async service layer.
# --------------------------------------------------------------------------- #

async def build_einvoice_view(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, invoice_id: str,
) -> dict:
    """Readiness + payload + current registration status for one invoice."""
    from app.accounting.service import AccountingNotFoundError
    from app.modules.business.service import get_invoice_settings, get_party, get_sales_invoice

    invoice = await get_sales_invoice(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, invoice_id=invoice_id,
    )
    if invoice is None:
        raise AccountingNotFoundError("Invoice not found")
    settings = await get_invoice_settings(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    seller = dict(settings.get("branding") or {})
    seller["gst_registration_type"] = (settings.get("branding") or {}).get("gst_registration_type")
    buyer = await get_party(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, party_id=invoice.get("customer_party_id"),
    ) or {}

    errors = validate_einvoice_readiness(invoice=invoice, seller=seller, buyer=buyer)
    payload = assemble_inv01_payload(invoice=invoice, seller=seller, buyer=buyer) if not errors else None
    einvoice = invoice.get("einvoice") or {"status": "not_generated"}
    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.get("invoice_number"),
        "eligible": not errors,
        "errors": errors,
        "payload": payload,
        "einvoice": einvoice,
        "notes": [
            "Download the INV-01 JSON and upload it on the e-invoice portal / offline "
            "utility; record the returned IRN and Ack here to complete the trail.",
            "Direct IRP API registration plugs in later — it will reuse this exact payload.",
        ],
    }


async def record_irn(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, invoice_id: str,
    irn: str, ack_no: str | None, ack_date: str | None, signed_qr: str | None,
    created_by: str,
) -> dict:
    """Record the IRN the portal returned (manual today, API later)."""
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.business.service import SALES_INVOICES_COLLECTION

    irn = str(irn or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", irn):
        raise AccountingValidationError("IRN must be the 64-character hash the portal returned")

    col = get_collection(SALES_INVOICES_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key,
               "accounting_entity_id": accounting_entity_id, "invoice_id": invoice_id}
    invoice = await col.find_one(filters)
    if invoice is None:
        raise AccountingNotFoundError("Invoice not found")
    existing = (invoice.get("einvoice") or {})
    if existing.get("status") == "registered":
        raise AccountingValidationError(
            f"An IRN is already recorded for this invoice ({existing.get('irn', '')[:16]}…)"
        )

    einvoice = {
        "status": "registered",
        "irn": irn,
        "ack_no": str(ack_no or "").strip() or None,
        "ack_date": str(ack_date or "").strip() or None,
        "signed_qr": str(signed_qr or "").strip() or None,
        "recorded_by": created_by,
        "recorded_at": _now().isoformat(),
    }
    await col.update_one(filters, {"$set": {"einvoice": einvoice, "updated_at": _now()}})
    return {"invoice_id": invoice_id, "einvoice": einvoice}
