"""Accounting dimensions — the P&L-by-dimension report assembler. Pure: the
dimension masters and posted documents are passed in as Mongo shapes them."""
from datetime import date
from decimal import Decimal

from app.modules.business.dimensions import assemble_dimension_report

FROM, TO = date(2026, 4, 1), date(2026, 6, 30)

DIMS = [
    {"dimension_id": "cc1", "dimension_type": "cost_centre", "code": "BLR", "name": "Bengaluru"},
    {"dimension_id": "cc2", "dimension_type": "cost_centre", "code": "MUM", "name": "Mumbai"},
    {"dimension_id": "p1", "dimension_type": "project", "code": "ALPHA", "name": "Project Alpha"},
]


def _inv(taxable, cc=None, proj=None):
    return {"taxable_total": taxable, "cost_centre_id": cc, "project_id": proj}


def _bill(taxable, cc=None, proj=None):
    return {"taxable_total": taxable, "cost_centre_id": cc, "project_id": proj}


def _cn(taxable, cc=None, proj=None):
    return {"taxable_total": taxable, "cost_centre_id": cc, "project_id": proj}


def _dn(taxable, cc=None, proj=None):
    return {"taxable_total": taxable, "cost_centre_id": cc, "project_id": proj}


def _line(taxable, cc=None, proj=None):
    return {"taxable_amount": taxable, "cost_centre_id": cc, "project_id": proj}


def _voucher(income="0", expense="0", cc=None, proj=None):
    return {"income": income, "expense": expense, "cost_centre_id": cc, "project_id": proj}


def test_report_groups_income_expense_and_untagged():
    out = assemble_dimension_report(
        dimension_type="cost_centre", from_date=FROM, to_date=TO, dimensions=DIMS,
        invoices=[_inv("10000", cc="cc1"), _inv("5000", cc="cc2"), _inv("2000")],
        bills=[_bill("4000", cc="cc1"), _bill("1000")],
        credit_notes=[_cn("1500", cc="cc1"), _cn("200")],
        debit_notes=[_dn("500", cc="cc1"), _dn("100")],
        voucher_impacts=[_voucher(income="750", cc="cc1"), _voucher(expense="250")],
    )
    rows = {r["code"]: r for r in out["rows"]}
    assert rows["BLR"] == {"dimension_id": "cc1", "code": "BLR", "name": "Bengaluru",
                           "income": "9250.00", "expense": "3500.00", "net": "5750.00"}
    assert rows["MUM"]["net"] == "5000.00"
    # Sorted by net descending.
    assert [r["code"] for r in out["rows"]] == ["BLR", "MUM"]
    assert out["untagged"] == {"income": "1800.00", "expense": "1150.00", "net": "650.00"}
    # Totals tie to all documents (tagged + untagged).
    assert out["totals"] == {"income": "16050.00", "expense": "4650.00", "net": "11400.00"}
    assert out["document_counts"] == {"invoices": 3, "bills": 2, "credit_notes": 2, "debit_notes": 2, "vouchers": 2}


def test_report_allocates_line_dimensions_with_document_fallback():
    out = assemble_dimension_report(
        dimension_type="cost_centre", from_date=FROM, to_date=TO, dimensions=DIMS,
        invoices=[
            {
                "taxable_total": "1000",
                "cost_centre_id": "cc1",
                "line_items": [_line("600", cc="cc2"), _line("400")],
            },
        ],
        bills=[
            {
                "taxable_total": "500",
                "cost_centre_id": "cc1",
                "line_items": [_line("300", cc="cc2"), _line("200")],
            },
        ],
    )
    rows = {r["code"]: r for r in out["rows"]}
    assert rows["MUM"]["income"] == "600.00"
    assert rows["MUM"]["expense"] == "300.00"
    assert rows["BLR"]["income"] == "400.00"
    assert rows["BLR"]["expense"] == "200.00"
    assert out["document_counts"]["invoices"] == 1
    assert out["document_counts"]["bills"] == 1


def test_report_by_project_uses_project_field_and_keeps_deleted_tags():
    out = assemble_dimension_report(
        dimension_type="project", from_date=FROM, to_date=TO, dimensions=DIMS,
        invoices=[_inv("8000", cc="cc1", proj="p1"), _inv("3000", proj="ghost")],
        bills=[], credit_notes=[_cn("500", proj="p1")], debit_notes=[],
    )
    rows = {r["dimension_id"]: r for r in out["rows"]}
    assert rows["p1"]["name"] == "Project Alpha"
    assert rows["p1"]["income"] == "7500.00"
    # A tag whose master was removed still appears (history never vanishes).
    assert rows["ghost"]["name"] == "(deleted dimension)"
    # Cost-centre tags are irrelevant for the project view.
    assert out["untagged"]["income"] == "0.00"


def test_report_empty_period():
    out = assemble_dimension_report(
        dimension_type="cost_centre", from_date=FROM, to_date=TO,
        dimensions=DIMS, invoices=[], bills=[],
    )
    assert out["rows"] == []
    assert out["totals"]["net"] == "0.00"
