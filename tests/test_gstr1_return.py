"""GSTR-1 outward-supplies return — state-code resolver and the pure section
assembler (B2B / B2CL / B2CS / CDNR / HSN / DOCS), no DB needed."""
from decimal import Decimal

from app.modules.business.gst_states import resolve_state_code, state_label
from app.modules.business.gst_returns import (
    assemble_gstr1, assemble_cmp08, assemble_gstr4, _quarter_bounds, _fy_bounds,
)
from datetime import date
from decimal import Decimal


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


def test_gstr1_zero_rated_goes_to_exp_section():
    invoices = [
        # Export under LUT — zero-rated lines carry no tax.
        {"invoice_number": "EXP-1", "invoice_date": "2026-05-15", "invoice_total": "50000",
         "customer_gstin": None, "place_of_supply": None, "is_inter_state": True,
         "line_items": [dict(_line(0, 50000), supply_type="zero_rated")]},
        # Normal domestic B2CS invoice stays where it was.
        {"invoice_number": "INV-9", "invoice_date": "2026-05-16", "invoice_total": "590",
         "customer_gstin": None, "place_of_supply": "29", "is_inter_state": False,
         "line_items": [_line(18, 500, cgst=45, sgst=45)]},
    ]
    r = assemble_gstr1(gstin=None, period="2026-05", invoices=invoices, credit_notes=[])
    assert r["sections"]["exp"] == {"invoices": 1, "taxable_value": Decimal("50000.00"),
                                    "tax": Decimal("0.00")}
    assert r["sections"]["b2cs"]["taxable_value"] == Decimal("500.00")
    # GSTN JSON: one WOPAY (LUT) bucket with the export invoice.
    exp = r["gstn_json"]["exp"]
    assert exp[0]["exp_typ"] == "WOPAY"
    assert exp[0]["inv"][0]["inum"] == "EXP-1"
    assert exp[0]["inv"][0]["val"] == 50000.0
    # A registered SEZ customer's zero-rated invoice also lands in EXP, not B2B.
    sez = assemble_gstr1(gstin=None, period="2026-05", credit_notes=[], invoices=[
        {"invoice_number": "SEZ-1", "invoice_date": "2026-05-20", "invoice_total": "1000",
         "customer_gstin": "27SEZAB1234C1Z9", "place_of_supply": "27", "is_inter_state": True,
         "line_items": [dict(_line(0, 1000), supply_type="zero_rated")]},
    ])
    assert sez["sections"]["exp"]["invoices"] == 1
    assert sez["sections"]["b2b"]["invoices"] == 0


def test_gstr1_empty_period():
    r = assemble_gstr1(gstin=None, period="2026-04", invoices=[], credit_notes=[])
    assert r["sections"]["b2b"]["invoices"] == 0
    assert r["sections"]["docs"] == {"total": 0, "from": None, "to": None}
    assert r["gstn_json"]["b2b"] == []
    assert r["gstn_json"]["doc_issue"] == {"doc_det": []}


# --------------------------------------------------------------------------- #
# CMP-08 (composition quarterly)
# --------------------------------------------------------------------------- #
def test_quarter_bounds_fy_quarters():
    assert _quarter_bounds("2026-Q1") == (date(2026, 4, 1), date(2026, 6, 30))
    assert _quarter_bounds("2026-Q2") == (date(2026, 7, 1), date(2026, 9, 30))
    assert _quarter_bounds("2026-Q3") == (date(2026, 10, 1), date(2026, 12, 31))
    assert _quarter_bounds("2026-Q4") == (date(2027, 1, 1), date(2027, 3, 31))


def test_cmp08_tax_is_rate_times_turnover_split_cgst_sgst():
    from decimal import Decimal
    # Restaurant @ 5% on a quarter's turnover of 2,00,000 -> 10,000 (5k + 5k).
    r = assemble_cmp08(gstin="29SELLER1234F1Z5", quarter="2026-Q1", category="restaurant",
                       rate=Decimal("5"), outward_turnover=Decimal("200000"), is_composition=True)
    assert r["outward_supplies"]["turnover"] == Decimal("200000.00")
    assert r["outward_supplies"]["cgst"] == Decimal("5000.00")
    assert r["outward_supplies"]["sgst"] == Decimal("5000.00")
    assert r["outward_supplies"]["igst"] == Decimal("0.00")     # composition is intra-state only
    assert r["tax_payable"]["total"] == Decimal("10000.00")
    j = r["gstn_json"]
    assert j["ret_period"] == "2026-Q1"
    os_row = next(x for x in j["summ"]["typ_summ"] if x["typ"] == "OS")
    assert os_row == {"typ": "OS", "txval": 200000.0, "iamt": 0.0, "camt": 5000.0, "samt": 5000.0, "csamt": 0.0}


def test_cmp08_flags_non_composition_entity():
    r = assemble_cmp08(gstin=None, quarter="2026-Q1", category=None, rate=0,
                       outward_turnover=Decimal("50000"), is_composition=False)
    assert r["tax_payable"]["total"] == Decimal("0.00")
    assert any("not registered under the composition" in n for n in r["notes"])


# --------------------------------------------------------------------------- #
# GSTR-4 (composition annual)
# --------------------------------------------------------------------------- #
def test_cmp08_includes_rcm_inward():
    r = assemble_cmp08(
        gstin=None, quarter="2026-Q1", category="goods", rate=1,
        outward_turnover=Decimal("100000"), is_composition=True,
        rcm_inward={"taxable_value": Decimal("5000"), "igst": Decimal("0"),
                    "cgst": Decimal("450"), "sgst": Decimal("450")},
    )
    # Outward levy 1% of 1L = 1000 (500/500) + RCM 900 = 1900 total payable.
    assert r["outward_supplies"]["total_tax"] == Decimal("1000.00")
    assert r["inward_reverse_charge"]["cgst"] == Decimal("450.00")
    assert r["tax_payable"]["cgst"] == Decimal("950.00")
    assert r["tax_payable"]["total"] == Decimal("1900.00")
    rc_row = r["gstn_json"]["summ"]["typ_summ"][1]
    assert rc_row == {"typ": "RC", "txval": 5000.0, "iamt": 0.0,
                      "camt": 450.0, "samt": 450.0, "csamt": 0.0}


def test_fy_bounds():
    assert _fy_bounds("2026-27") == (2026, date(2026, 4, 1), date(2027, 3, 31))


def test_gstr4_consolidates_quarters_outward_and_inward():
    # Goods @ 1%, four quarters of turnover; one registered + one unregistered purchase bucket.
    r = assemble_gstr4(
        gstin="29SELLER1234F1Z5", financial_year="2026-27", category="goods", rate=Decimal("1"),
        quarter_turnovers={"Q1": Decimal("100000"), "Q2": Decimal("150000"),
                           "Q3": Decimal("0"), "Q4": Decimal("250000")},
        inward_registered={Decimal("18"): {"txval": Decimal("50000"), "iamt": Decimal("0"),
                                            "camt": Decimal("4500"), "samt": Decimal("4500")}},
        inward_unregistered={Decimal("5"): {"txval": Decimal("10000"), "iamt": Decimal("0"),
                                            "camt": Decimal("250"), "samt": Decimal("250")}},
        is_composition=True,
    )
    # Table 5 — annual turnover 5,00,000; tax @1% = 5,000 (2,500 + 2,500).
    s = r["cmp08_summary"]
    assert s["total_turnover"] == Decimal("500000.00")
    assert s["cgst"] == Decimal("2500.00") and s["sgst"] == Decimal("2500.00")
    assert s["total_tax"] == Decimal("5000.00")
    assert len(s["quarters"]) == 4 and s["quarters"][3]["quarter"] == "Q4"

    # Table 6 — outward liability ties to table 5.
    assert r["outward_supplies"]["total_tax"] == Decimal("5000.00")

    # Table 4 — inward split.
    assert r["inward_supplies"]["registered"]["taxable_value"] == Decimal("50000.00")
    assert r["inward_supplies"]["registered"]["tax"] == Decimal("9000.00")
    assert r["inward_supplies"]["unregistered"]["taxable_value"] == Decimal("10000.00")

    j = r["gstn_json"]
    assert j["fy"] == "2026-27"
    assert j["txos"][0] == {"rt": 1.0, "txval": 500000.0, "iamt": 0.0, "camt": 2500.0, "samt": 2500.0, "csamt": 0.0}
    assert len(j["cmp08_summ"]) == 4
    assert {row["sup_typ"] for row in j["inward_sup"]} == {"REG", "UNREG"}
