"""GSTR-1 outward-supplies return — state-code resolver and the pure section
assembler (B2B / B2CL / B2CS / CDNR / HSN / DOCS), no DB needed."""
from decimal import Decimal

from app.modules.business.gst_states import resolve_state_code, state_label
from app.modules.business.gst_returns import assemble_gstr1


# --------------------------------------------------------------------------- #
# State-code resolver
# --------------------------------------------------------------------------- #
def test_resolve_state_code_from_name_code_and_gstin():
    assert resolve_state_code("Karnataka") == "29"
    assert resolve_state_code("29-Karnataka") == "29"
    assert resolve_state_code("29") == "29"
    assert resolve_state_code("Orissa") == "21"            # alias
    assert resolve_state_code(None, "29ABCDE1234F1Z5") == "29"  # GSTIN fallback
    assert resolve_state_code("", "27XYZAB5678C1Z3") == "27"
    assert resolve_state_code("Nowhere") == ""             # unknown
    assert state_label("29") == "29-Karnataka"


# --------------------------------------------------------------------------- #
# GSTR-1 section assembler
# --------------------------------------------------------------------------- #
def _line(rate, txval, cgst=0, sgst=0, igst=0, hsn="9983", uqc="NOS", qty=1):
    return {
        "gst_rate": str(rate), "taxable_amount": str(txval),
        "cgst": str(cgst), "sgst": str(sgst), "igst": str(igst),
        "hsn_sac": hsn, "uqc": uqc, "quantity": str(qty), "supply_type": "taxable",
    }


def _build():
    invoices = [
        # B2B — registered customer, intra-state.
        {"invoice_number": "INV-1", "invoice_date": "2026-05-03", "invoice_total": "1180",
         "customer_gstin": "29ABCDE1234F1Z5", "place_of_supply": "29-Karnataka", "is_inter_state": False,
         "line_items": [_line(18, 1000, cgst=90, sgst=90)]},
        # B2CL — unregistered, inter-state, value > threshold.
        {"invoice_number": "INV-2", "invoice_date": "2026-05-10", "invoice_total": "236000",
         "customer_gstin": None, "place_of_supply": "27-Maharashtra", "is_inter_state": True,
         "line_items": [_line(18, 200000, igst=36000, hsn="1234", qty=10)]},
        # B2CS — unregistered, intra-state.
        {"invoice_number": "INV-3", "invoice_date": "2026-05-12", "invoice_total": "590",
         "customer_gstin": None, "place_of_supply": "29", "is_inter_state": False,
         "line_items": [_line(18, 500, cgst=45, sgst=45)]},
    ]
    credit_notes = [
        # CDNR — credit note to the registered customer.
        {"credit_note_number": "CN-1", "note_date": "2026-05-20", "note_total": "118",
         "customer_gstin": "29ABCDE1234F1Z5", "place_of_supply": "29-Karnataka", "is_inter_state": False,
         "line_items": [_line(18, 100, cgst=9, sgst=9)]},
    ]
    return assemble_gstr1(gstin="29SELLER1234F1Z5", period="2026-05",
                          invoices=invoices, credit_notes=credit_notes)


def test_gstr1_section_summaries():
    r = _build()
    s = r["sections"]
    assert s["b2b"] == {"recipients": 1, "invoices": 1,
                        "taxable_value": Decimal("1000.00"), "tax": Decimal("180.00")}
    assert s["b2cl"] == {"places": 1, "invoices": 1,
                         "taxable_value": Decimal("200000.00"), "tax": Decimal("36000.00")}
    assert s["b2cs"] == {"rows": 1, "taxable_value": Decimal("500.00"), "tax": Decimal("90.00")}
    assert s["cdnr"] == {"recipients": 1, "notes": 1,
                         "taxable_value": Decimal("100.00"), "tax": Decimal("18.00")}
    # HSN nets the credit note out of the matching bucket.
    assert s["hsn"]["rows"] == 2
    assert s["hsn"]["taxable_value"] == Decimal("201400.00")  # (1000+500-100) + 200000
    assert s["docs"] == {"total": 3, "from": "INV-1", "to": "INV-3"}


def test_gstr1_b2cs_and_hsn_rows():
    r = _build()
    b2cs = r["b2cs_rows"]
    assert len(b2cs) == 1
    assert b2cs[0]["supply_type"] == "INTRA"
    assert b2cs[0]["pos"] == "29-Karnataka"
    assert b2cs[0]["taxable_value"] == Decimal("500.00")
    assert b2cs[0]["cgst"] == Decimal("45.00")

    hsn = {row["hsn_sac"]: row for row in r["hsn_rows"]}
    # 9983 bucket = INV-1 + INV-3 - CN-1.
    assert hsn["9983"]["quantity"] == Decimal("1.00")        # 1 + 1 - 1
    assert hsn["9983"]["taxable_value"] == Decimal("1400.00")
    assert hsn["9983"]["cgst"] == Decimal("126.00")          # 90 + 45 - 9
    assert hsn["1234"]["igst"] == Decimal("36000.00")


def test_gstr1_gstn_json_shape():
    j = _build()["gstn_json"]
    assert j["gstin"] == "29SELLER1234F1Z5"
    assert j["fp"] == "052026"

    assert j["b2b"][0]["ctin"] == "29ABCDE1234F1Z5"
    b2b_inv = j["b2b"][0]["inv"][0]
    assert b2b_inv["inum"] == "INV-1" and b2b_inv["pos"] == "29" and b2b_inv["rchrg"] == "N"
    assert b2b_inv["itms"][0]["itm_det"] == {
        "rt": 18.0, "txval": 1000.0, "iamt": 0.0, "camt": 90.0, "samt": 90.0, "csamt": 0.0
    }

    assert j["b2cl"][0]["pos"] == "27"
    assert j["b2cl"][0]["inv"][0]["val"] == 236000.0

    b2cs = j["b2cs"][0]
    assert b2cs["sply_ty"] == "INTRA" and b2cs["pos"] == "29" and b2cs["rt"] == 18.0
    assert b2cs["txval"] == 500.0

    assert j["cdnr"][0]["nt"][0]["ntty"] == "C"
    assert len(j["hsn"]["data"]) == 2
    assert j["doc_issue"]["doc_det"][0]["docs"][0]["totnum"] == 3


def test_gstr1_empty_period():
    r = assemble_gstr1(gstin=None, period="2026-04", invoices=[], credit_notes=[])
    assert r["sections"]["b2b"]["invoices"] == 0
    assert r["sections"]["docs"] == {"total": 0, "from": None, "to": None}
    assert r["gstn_json"]["b2b"] == []
    assert r["gstn_json"]["doc_issue"] == {"doc_det": []}
