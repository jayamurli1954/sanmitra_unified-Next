"""e-Invoicing foundation — INV-01 payload assembly and readiness validation.
Pure functions, clean-room to the GSTN e-invoice schema v1.1. No IRP call —
the payload is what the portal/offline utility accepts."""
from decimal import Decimal

from app.modules.business.einvoice import (
    assemble_inv01_payload,
    validate_einvoice_readiness,
)

SELLER = {
    "gstin": "29ABCDE1234F1Z5",
    "business_name": "Sanmitra Traders Pvt Ltd",
    "address": "12 MG Road, Bengaluru 560001",
}
BUYER = {
    "party_name": "Acme Industries",
    "gstin": "27XYZAB5678C1Z3",
    "billing_address": "Plot 4, Andheri East",
    "city": "Mumbai",
    "pincode": "400069",
}


def _line(**overrides):
    base = {
        "description": "Consulting services",
        "hsn_sac": "998311",
        "uqc": "NOS",
        "supply_type": "taxable",
        "quantity": "2",
        "rate": "5000.00",
        "gst_rate": "18",
        "taxable_amount": "10000.00",
        "cgst": "0.00", "sgst": "0.00", "igst": "1800.00",
    }
    base.update(overrides)
    return base


def _invoice(**overrides):
    base = {
        "invoice_id": "i1",
        "invoice_number": "INV-2026-01",
        "invoice_date": "2026-05-10",
        "status": "posted",
        "is_inter_state": True,
        "line_items": [_line()],
        "taxable_total": "10000.00",
        "invoice_total": "11800.00",
    }
    base.update(overrides)
    return base


def test_clean_b2b_invoice_is_ready():
    assert validate_einvoice_readiness(invoice=_invoice(), seller=SELLER, buyer=BUYER) == []


def test_readiness_catches_the_common_rejections():
    errors = validate_einvoice_readiness(
        invoice=_invoice(invoice_number="0/BAD*NO", status="cancelled",
                         line_items=[_line(hsn_sac="99")]),
        seller={"gstin": "BAD", "business_name": "", "address": "no pin here"},
        buyer={"party_name": "Walk-in", "gstin": "", "billing_address": ""},
    )
    text = " ".join(errors)
    assert "Seller GSTIN" in text
    assert "legal name" in text
    assert "Seller address needs a 6-digit pincode" in text
    assert "Buyer GSTIN" in text
    assert "Invoice number" in text
    assert "Only posted invoices" in text
    assert "HSN/SAC must be 4-8 digits" in text


def test_composition_bill_of_supply_excluded():
    errors = validate_einvoice_readiness(
        invoice=_invoice(is_composition=True, document_type="bill_of_supply"),
        seller=SELLER, buyer=BUYER,
    )
    assert any("outside the e-invoicing mandate" in e for e in errors)


def test_inv01_payload_b2b_shape_and_totals():
    p = assemble_inv01_payload(invoice=_invoice(), seller=SELLER, buyer=BUYER)
    assert p["Version"] == "1.1"
    assert p["TranDtls"] == {"TaxSch": "GST", "SupTyp": "B2B", "RegRev": "N", "IgstOnIntra": "N"}
    assert p["DocDtls"] == {"Typ": "INV", "No": "INV-2026-01", "Dt": "10/05/2026"}
    assert p["SellerDtls"]["Gstin"] == "29ABCDE1234F1Z5"
    assert p["SellerDtls"]["Stcd"] == "29"
    assert p["SellerDtls"]["Pin"] == 560001
    assert p["BuyerDtls"]["Gstin"] == "27XYZAB5678C1Z3"
    assert p["BuyerDtls"]["Pos"] == "27"
    assert p["BuyerDtls"]["Pin"] == 400069
    item = p["ItemList"][0]
    assert item["IsServc"] == "Y"                  # SAC chapter 99
    assert item["HsnCd"] == "998311"
    assert item["Unit"] == "NOS"
    assert item["AssAmt"] == 10000.0
    assert item["IgstAmt"] == 1800.0
    assert item["TotItemVal"] == 11800.0
    assert p["ValDtls"]["AssVal"] == 10000.0
    assert p["ValDtls"]["IgstVal"] == 1800.0
    assert p["ValDtls"]["TotInvVal"] == 11800.0
    assert p["ValDtls"]["OthChrg"] == 0.0


def test_inv01_zero_rated_export_and_sez():
    export_inv = _invoice(line_items=[_line(supply_type="zero_rated", gst_rate="0",
                                            igst="0.00")],
                          invoice_total="10000.00")
    p = assemble_inv01_payload(invoice=export_inv, seller=SELLER,
                               buyer={"party_name": "Overseas Co", "gstin": "", "billing_address": ""})
    assert p["TranDtls"]["SupTyp"] == "EXPWOP"
    assert p["BuyerDtls"]["Gstin"] == "URP"
    assert p["BuyerDtls"]["Pos"] == "96"           # other country
    # Same document to an SEZ unit (registered buyer) -> SEZWOP.
    p2 = assemble_inv01_payload(invoice=export_inv, seller=SELLER, buyer=BUYER)
    assert p2["TranDtls"]["SupTyp"] == "SEZWOP"


def test_inv01_tcs_lands_in_other_charges():
    inv = _invoice(grand_total="11811.80", tcs_amount="11.80")
    p = assemble_inv01_payload(invoice=inv, seller=SELLER, buyer=BUYER)
    assert p["ValDtls"]["TotInvVal"] == 11811.8
    assert p["ValDtls"]["OthChrg"] == 11.8
