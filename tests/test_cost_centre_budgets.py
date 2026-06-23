"""Cost-centre budgets — the budget-vs-actual assembler and lifecycle rules."""
from decimal import Decimal

import pytest

from app.modules.business.cost_centre_budgets import (
    _ALLOWED_TRANSITIONS,
    _period_bounds,
    assemble_budget_vs_actual,
)

BUDGET = {
    "cost_centre_id": "cc-assembly",
    "fiscal_year": 2026,
    "fiscal_month": 5,
    "status": "APPROVED",
    "lines": [
        {"account_id": 501, "allocated_amount": "10000.00"},
        {"account_id": 502, "allocated_amount": "5000.00"},
    ],
}


def test_budget_vs_actual_computes_variance_and_burn():
    actuals = {
        501: {"code": "5001", "name": "Materials", "type": "expense", "actual": Decimal("6500.00")},
        502: {"code": "5002", "name": "Power", "type": "expense", "actual": Decimal("5000.00")},
    }
    out = assemble_budget_vs_actual(budget=BUDGET, actuals_by_account=actuals)
    rows = {r["account_id"]: r for r in out["rows"]}
    # Under budget on materials.
    assert rows[501]["variance"] == "3500.00"
    assert rows[501]["burn_rate_pct"] == "65.00"
    # Exactly on budget on power.
    assert rows[502]["variance"] == "0.00"
    assert rows[502]["burn_rate_pct"] == "100.00"
    assert out["totals"] == {"allocated": "15000.00", "actual": "11500.00", "variance": "3500.00"}


def test_budget_vs_actual_flags_unbudgeted_spend():
    actuals = {
        501: {"code": "5001", "name": "Materials", "type": "expense", "actual": Decimal("11000.00")},
        999: {"code": "5009", "name": "Rogue spend", "type": "expense", "actual": Decimal("250.00")},
    }
    out = assemble_budget_vs_actual(budget=BUDGET, actuals_by_account=actuals)
    rows = {r["account_id"]: r for r in out["rows"]}
    # Overspend shows negative variance.
    assert rows[501]["variance"] == "-1000.00"
    # Spend with no allocation surfaces as an unbudgeted row (nothing hidden).
    assert rows[999]["unbudgeted"] is True
    assert rows[999]["allocated"] == "0.00"
    assert rows[999]["variance"] == "-250.00"


def test_budget_vs_actual_zero_actuals():
    out = assemble_budget_vs_actual(budget=BUDGET, actuals_by_account={})
    assert out["totals"]["actual"] == "0.00"
    assert out["totals"]["variance"] == "15000.00"
    assert all(r["actual"] == "0.00" for r in out["rows"])


def test_lifecycle_is_forward_only():
    assert _ALLOWED_TRANSITIONS["DRAFT"] == {"APPROVED"}
    assert _ALLOWED_TRANSITIONS["APPROVED"] == {"LOCKED"}
    assert _ALLOWED_TRANSITIONS["LOCKED"] == set()


@pytest.mark.parametrize("year,month,start,end", [
    (2026, 5, "2026-05-01", "2026-05-31"),
    (2026, 2, "2026-02-01", "2026-02-28"),
    (2026, None, "2026-01-01", "2026-12-31"),
])
def test_period_bounds(year, month, start, end):
    f, t = _period_bounds(year, month)
    assert f.isoformat() == start
    assert t.isoformat() == end
