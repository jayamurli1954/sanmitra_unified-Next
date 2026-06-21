"""Map a posted MitraBooks sales invoice into the shared document renderer.

This is the app-side mapping for Phase 1 of the shared document-PDF layer
(``app/core/documents``). It decides the columns and totals — notably dropping
GST columns for a composition Bill of Supply — and hands a ``DocumentSpec`` to
the renderer. Money is formatted with an ASCII "Rs." prefix because the core PDF
font cannot render the ₹ glyph.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.core.documents import (
    DocumentColumn,
    DocumentLine,
    DocumentParty,
    DocumentSpec,
    TotalRow,
    render_document_pdf,
)


def _dec(value) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else "0"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _money(value) -> str:
    return f"Rs. {_dec(value):,.2f}"


def _qty(value) -> str:
    d = _dec(value)
    return f"{d:,.3f}".rstrip("0").rstrip(".") if d != d.to_integral_value() else f"{int(d):,}"


def _seller_from_branding(branding: dict) -> DocumentParty:
    branding = branding or {}
    name = str(branding.get("business_name") or "").strip() or "Your Business"
    address = str(branding.get("address") or "").strip()
    address_lines = [seg.strip() for seg in address.replace("\r", "").split("\n") if seg.strip()]
    return DocumentParty(name=name, address_lines=address_lines, gstin=branding.get("gstin") or None)


def build_sales_invoice_spec(invoice: dict, branding: dict) -> DocumentSpec:
    is_composition = bool(invoice.get("is_composition"))
    is_inter_state = bool(invoice.get("is_inter_state"))
    title = "Bill of Supply" if is_composition else "Tax Invoice"

    seller = _seller_from_branding(branding)
    buyer = DocumentParty(
        name=str(invoice.get("customer_name") or "Customer"),
        gstin=invoice.get("customer_gstin") or None,
    )

    meta: list[tuple[str, str]] = []
    if invoice.get("invoice_date"):
        meta.append(("Date", str(invoice["invoice_date"])))
    if invoice.get("due_date"):
        meta.append(("Due date", str(invoice["due_date"])))
    if invoice.get("place_of_supply"):
        meta.append(("Place of supply", str(invoice["place_of_supply"])))
    if invoice.get("reference"):
        meta.append(("Reference", str(invoice["reference"])))

    # Columns differ for composition (no GST) vs a regular tax invoice.
    columns = [
        DocumentColumn("sn", "#", "center", 0.5),
        DocumentColumn("description", "Description", "left", 4.2),
        DocumentColumn("hsn", "HSN/SAC", "left", 1.4),
        DocumentColumn("qty", "Qty", "right", 1.0),
        DocumentColumn("rate", "Rate", "right", 1.6),
        DocumentColumn("taxable", "Amount", "right", 1.8),
    ]
    if not is_composition:
        columns.append(DocumentColumn("gst", "GST", "right", 1.8))
        columns.append(DocumentColumn("total", "Total", "right", 1.8))

    lines: list[DocumentLine] = []
    for idx, item in enumerate(invoice.get("line_items") or [], start=1):
        gst_amount = _dec(item.get("cgst")) + _dec(item.get("sgst")) + _dec(item.get("igst"))
        cells = {
            "sn": str(idx),
            "description": str(item.get("description") or ""),
            "hsn": str(item.get("hsn_sac") or ""),
            "qty": _qty(item.get("quantity")),
            "rate": _money(item.get("rate")),
            "taxable": _money(item.get("taxable_amount")),
        }
        if not is_composition:
            gst_rate = _dec(item.get("gst_rate"))
            cells["gst"] = f"{_money(gst_amount)} ({gst_rate:g}%)"
            cells["total"] = _money(item.get("line_total"))
        lines.append(DocumentLine(cells=cells))

    totals = [TotalRow("Taxable value", _money(invoice.get("taxable_total")))]
    if not is_composition:
        if is_inter_state:
            totals.append(TotalRow("IGST", _money(invoice.get("igst_total"))))
        else:
            totals.append(TotalRow("CGST", _money(invoice.get("cgst_total"))))
            totals.append(TotalRow("SGST", _money(invoice.get("sgst_total"))))
    if str(invoice.get("tcs_section") or "").strip() and _dec(invoice.get("tcs_amount")) > 0:
        totals.append(TotalRow(f"TCS ({invoice.get('tcs_section')})", _money(invoice.get("tcs_amount"))))
    grand = invoice.get("grand_total") or invoice.get("invoice_total")
    totals.append(TotalRow("Grand total", _money(grand), emphasize=True))

    if is_composition:
        declaration = (
            "Composition taxable person, not eligible to collect tax on supplies."
        )
    else:
        declaration = "Certified that the particulars given above are true and correct."

    return DocumentSpec(
        title=title,
        number=str(invoice.get("invoice_number") or invoice.get("invoice_id") or ""),
        seller=seller,
        buyer=buyer,
        columns=columns,
        lines=lines,
        totals=totals,
        meta=meta,
        notes=str(invoice.get("notes") or "").strip() or None,
        declaration=declaration,
        footer_note="This is a computer-generated document.",
    )


def build_sales_invoice_pdf(invoice: dict, branding: dict) -> bytes:
    return render_document_pdf(build_sales_invoice_spec(invoice, branding))
