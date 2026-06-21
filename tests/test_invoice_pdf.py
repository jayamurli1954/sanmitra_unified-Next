"""Shared document renderer + MitraBooks sales-invoice PDF mapping.

These run headless: they assert the mapper builds the right DocumentSpec (GST vs
composition, intra vs inter-state) and that the reportlab renderer produces valid
PDF bytes.
"""
from __future__ import annotations

from app.modules.business.invoice_pdf import build_sales_invoice_spec, build_sales_invoice_pdf
from app.core.documents import render_document_pdf


def _regular_invoice() -> dict:
    return {
        "invoice_id": "inv-1",
        "invoice_number": "INV-2026-000001",
        "invoice_date": "2026-06-21",
        "due_date": "2026-07-21",
        "customer_name": "Acme Traders",
        "customer_gstin": "29ABCDE1234F1Z5",
        "place_of_supply": "29-Karnataka",
        "is_inter_state": False,
        "is_composition": False,
        "reference": "PO-77",
        "notes": "Thanks for your business.",
        "line_items": [
            {
                "description": "Consulting services", "hsn_sac": "9983", "quantity": "2",
                "rate": "5000.00", "gst_rate": "18", "taxable_amount": "10000.00",
                "cgst": "900.00", "sgst": "900.00", "igst": "0", "line_total": "11800.00",
            },
        ],
        "taxable_total": "10000.00", "cgst_total": "900.00", "sgst_total": "900.00",
        "igst_total": "0", "gst_total": "1800.00", "invoice_total": "11800.00",
        "tcs_section": None, "tcs_amount": "0", "grand_total": "11800.00",
    }


_BRANDING = {"business_name": "SanMitra Tech", "address": "1 MG Road\nBengaluru", "gstin": "29AAAAA0000A1Z5"}


def test_regular_invoice_spec_has_gst_columns_and_totals():
    spec = build_sales_invoice_spec(_regular_invoice(), _BRANDING)
    assert spec.title == "Tax Invoice"
    col_keys = {c.key for c in spec.columns}
    assert {"gst", "total"}.issubset(col_keys)
    labels = {t.label for t in spec.totals}
    assert "CGST" in labels and "SGST" in labels
    assert spec.seller.name == "SanMitra Tech"
    assert spec.buyer.name == "Acme Traders"
    assert any(t.emphasize and t.label == "Grand total" for t in spec.totals)


def test_inter_state_invoice_uses_igst():
    inv = _regular_invoice()
    inv["is_inter_state"] = True
    inv["cgst_total"], inv["sgst_total"], inv["igst_total"] = "0", "0", "1800.00"
    inv["line_items"][0].update({"cgst": "0", "sgst": "0", "igst": "1800.00"})
    spec = build_sales_invoice_spec(inv, _BRANDING)
    labels = {t.label for t in spec.totals}
    assert "IGST" in labels
    assert "CGST" not in labels


def test_composition_bill_of_supply_drops_gst():
    inv = _regular_invoice()
    inv["is_composition"] = True
    spec = build_sales_invoice_spec(inv, _BRANDING)
    assert spec.title == "Bill of Supply"
    col_keys = {c.key for c in spec.columns}
    assert "gst" not in col_keys
    labels = {t.label for t in spec.totals}
    assert "CGST" not in labels and "IGST" not in labels
    assert "composition" in (spec.declaration or "").lower()


def test_tcs_appears_in_totals_when_present():
    inv = _regular_invoice()
    inv["tcs_section"] = "206C(1H)"
    inv["tcs_amount"] = "118.00"
    inv["grand_total"] = "11918.00"
    spec = build_sales_invoice_spec(inv, _BRANDING)
    assert any("TCS" in t.label for t in spec.totals)


def test_render_produces_valid_pdf_bytes():
    pdf = build_sales_invoice_pdf(_regular_invoice(), _BRANDING)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000  # a real multi-element document, not an empty shell


def test_render_handles_missing_branding_and_many_lines():
    inv = _regular_invoice()
    # 60 lines exercises automatic pagination in the renderer.
    inv["line_items"] = inv["line_items"] * 60
    pdf = build_sales_invoice_pdf(inv, {})
    spec = build_sales_invoice_spec(inv, {})
    assert spec.seller.name == "Your Business"  # fallback when branding is empty
    assert pdf.startswith(b"%PDF")
