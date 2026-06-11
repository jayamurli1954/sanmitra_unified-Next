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


def test_report_groups_income_expense_and_untagged():
    out = assemble_dimension_report(
        dimension_type="cost_centre", from_date=FROM, to_date=TO, dimensions=DIMS,
        invoices=[_inv("10000", cc="cc1"), _inv("5000", cc="cc2"), _inv("2000")],
        bills=[_bill("4000", cc="cc1"), _bill("1000")],
    )
    rows = {r["code"]: r for r in out["rows"]}
    assert rows["BLR"] == {"dimension_id": "cc1", "code": "BLR", "name": "Bengaluru",
                           "income": "10000.00", "expense": "4000.00", "net": "6000.00"}
    assert rows["MUM"]["net"] == "5000.00"
    # Sorted by net descending.
    assert [r["code"] for r in out["rows"]] == ["BLR", "MUM"]
    assert out["untagged"] == {"income": "2000.00", "expense": "1000.00", "net": "1000.00"}
    # Totals tie to all documents (tagged + untagged).
    assert out["totals"] == {"income": "17000.00", "expense": "5000.00", "net": "12000.00"}
    assert out["document_counts"] == {"invoices": 3, "bills": 2}


def test_report_by_project_uses_project_field_and_keeps_deleted_tags():
    out = assemble_dimension_report(
        dimension_type="project", from_date=FROM, to_date=TO, dimensions=DIMS,
        invoices=[_inv("8000", cc="cc1", proj="p1"), _inv("3000", proj="ghost")],
        bills=[],
    )
    rows = {r["dimension_id"]: r for r in out["rows"]}
    assert rows["p1"]["name"] == "Project Alpha"
    assert rows["p1"]["income"] == "8000.00"
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
