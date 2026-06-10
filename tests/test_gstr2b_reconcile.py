"""GSTR-2B / ITC reconciliation — parse the portal JSON and match it against
booked input GST (matched / mismatch / available-not-booked / at-risk)."""
from decimal import Decimal

from app.modules.business.gst_returns import parse_gstr2b, reconcile_gstr2b


def _gstr2b_json():
    return {
        "data": {
            "rtnprd": "052026",
            "docdata": {
                "b2b": [
                    {"ctin": "29AAAAA0000A1Z5", "inv": [
                        {"inum": "S-1", "dt": "03-05-2026", "val": 1180,
                         "itms": [{"rt": 18, "txval": 1000, "igst": 0, "cgst": 90, "sgst": 90}]},
                        {"inum": "S-2", "dt": "10-05-2026", "val": 2360,
                         "itms": [{"rt": 18, "txval": 2000, "igst": 360, "cgst": 0, "sgst": 0}]},
                    ]},
                    {"ctin": "27BBBBB1111B1Z4", "inv": [
                        {"inum": "X-9", "dt": "12-05-2026", "val": 1180,
                         "itms": [{"rt": 18, "txval": 1000, "igst": 0, "cgst": 90, "sgst": 90}]},
                    ]},
                ]
            },
        }
    }


def test_parse_gstr2b_normalises_invoices_and_tax():
    rows = parse_gstr2b(_gstr2b_json())
    assert len(rows) == 3
    s1 = next(r for r in rows if r["invoice_number"] == "S-1")
    assert s1["gstin"] == "29AAAAA0000A1Z5"
    assert s1["cgst"] == Decimal("90.00") and s1["sgst"] == Decimal("90.00")
    assert s1["tax_total"] == Decimal("180.00")
    s2 = next(r for r in rows if r["invoice_number"] == "S-2")
    assert s2["igst"] == Decimal("360.00") and s2["tax_total"] == Decimal("360.00")


def test_parse_tolerates_iamt_keys_and_flat_structure():
    flat = {"b2b": [{"ctin": "29AAAAA0000A1Z5", "inv": [
        {"inum": "F-1", "val": 590, "itms": [{"itm_det": {"camt": 45, "samt": 45, "iamt": 0}}]}]}]}
    rows = parse_gstr2b(flat)
    assert rows[0]["tax_total"] == Decimal("90.00")


def _books():
    # Booked input GST per purchase bill (tax_total).
    return [
        # S-1 matches the 2B exactly.
        {"gstin": "29AAAAA0000A1Z5", "invoice_number": "S-1", "tax_total": Decimal("180.00"), "bill_id": "b1"},
        # S-2 booked at a different amount -> mismatch.
        {"gstin": "29AAAAA0000A1Z5", "invoice_number": "S-2", "tax_total": Decimal("300.00"), "bill_id": "b2"},
        # Z-7 booked but absent from 2B -> at risk.
        {"gstin": "24CCCCC2222C1Z3", "invoice_number": "Z-7", "tax_total": Decimal("500.00"), "bill_id": "b3"},
    ]


def test_reconcile_classifies_all_four_buckets():
    r = reconcile_gstr2b(
        period="2026-05",
        gstr2b_invoices=parse_gstr2b(_gstr2b_json()),
        book_invoices=_books(),
    )
    s = r["summary"]
    # S-1 matched exactly.
    assert s["matched_count"] == 1
    assert r["matched"][0]["invoice_number"] == "S-1"
    assert r["matched"][0]["itc"] == Decimal("180.00")

    # S-2 present in both but amounts differ.
    assert s["mismatch_count"] == 1
    assert r["mismatch"][0]["invoice_number"] == "S-2"
    assert r["mismatch"][0]["difference"] == Decimal("60.00")   # 360 (2B) - 300 (books)

    # X-9 is in 2B but not booked -> available, not booked.
    assert s["available_not_booked"] == Decimal("180.00")
    assert s["available_not_booked_count"] == 1

    # Z-7 booked but not in 2B -> at risk.
    assert s["at_risk_not_in_2b"] == Decimal("500.00")
    assert s["at_risk_count"] == 1

    assert s["itc_as_per_2b"] == Decimal("720.00")    # 180 + 360 + 180
    assert s["itc_as_per_books"] == Decimal("980.00") # 180 + 300 + 500


def test_reconcile_matches_on_normalised_invoice_number():
    # Whitespace differences in the invoice number should still match.
    twob = [{"gstin": "29A", "invoice_number": "INV 100", "tax_total": Decimal("90.00"),
             "igst": Decimal("0"), "cgst": Decimal("45"), "sgst": Decimal("45"), "value": Decimal("590")}]
    books = [{"gstin": "29A", "invoice_number": "INV100", "tax_total": Decimal("90.00"), "bill_id": "b9"}]
    r = reconcile_gstr2b(period="2026-05", gstr2b_invoices=twob, book_invoices=books)
    assert r["summary"]["matched_count"] == 1
