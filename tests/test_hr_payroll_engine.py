"""Pure payroll engine — statutory math against known values."""
from __future__ import annotations

from decimal import Decimal

from app.modules.hr.payroll_engine import (
    PayrollInput,
    SalaryComponent,
    compute_epf,
    compute_esi,
    compute_gratuity,
    compute_income_tax,
    compute_payroll,
    compute_professional_tax,
    evaluate_earnings,
)

D = Decimal


def _structure():
    return [
        SalaryComponent("Basic", "BASIC", formula="GROSS * 0.5", statutory_kind="basic"),
        SalaryComponent("HRA", "HRA", formula="BASIC * 0.5"),
        SalaryComponent("Special Allowance", "SPECIAL", formula="GROSS - BASIC - HRA"),
    ]


# ── earnings formula engine ───────────────────────────────────────────────────

def test_evaluate_earnings_resolves_dependent_formulas():
    out = evaluate_earnings(_structure(), monthly_gross=D("100000"))
    assert out == {"BASIC": D("50000.00"), "HRA": D("25000.00"), "SPECIAL": D("25000.00")}


def test_bad_formula_raises():
    import pytest

    with pytest.raises(ValueError):
        evaluate_earnings([SalaryComponent("X", "X", formula="GROSS *")], monthly_gross=D("1000"))


# ── EPF ───────────────────────────────────────────────────────────────────────

def test_epf_caps_at_wage_ceiling():
    assert compute_epf(D("50000"))["employee"] == D("1800.00")   # 12% of 15000
    assert compute_epf(D("10000"))["employee"] == D("1200.00")   # 12% of 10000
    assert compute_epf(D("50000"), eligible=False)["employee"] == D("0.00")


# ── ESI ───────────────────────────────────────────────────────────────────────

def test_esi_threshold_and_rates():
    low = compute_esi(D("20000"), eligible=True)
    assert low["employee"] == D("150.00") and low["employer"] == D("650.00")
    # Above the ₹21,000 gross threshold -> no ESI.
    assert compute_esi(D("25000"), eligible=True)["employee"] == D("0.00")
    assert compute_esi(D("20000"), eligible=False)["employee"] == D("0.00")


# ── Professional tax ──────────────────────────────────────────────────────────

def test_professional_tax_state_tables():
    assert compute_professional_tax(D("50000"), state="Karnataka") == D("200.00")
    assert compute_professional_tax(D("20000"), state="Karnataka") == D("0.00")
    assert compute_professional_tax(D("8000"), state="Maharashtra") == D("175.00")
    assert compute_professional_tax(D("12000"), state="Maharashtra") == D("200.00")
    # Unknown state -> default table.
    assert compute_professional_tax(D("50000"), state="Goa") == D("200.00")


# ── Income tax ────────────────────────────────────────────────────────────────

def test_new_regime_tax_with_cess():
    out = compute_income_tax(D("1500000"), regime="new")
    assert out["taxable_income"] == D("1425000.00")
    assert out["annual_tax"] == D("97500.00")     # 93750 + 4% cess
    assert out["monthly_tds"] == D("8125.00")


def test_old_regime_tax_with_80c():
    out = compute_income_tax(D("1000000"), regime="old", deductions=D("150000"))
    # taxable 800000 -> 12500 + 60000 = 72500; +4% cess = 75400
    assert out["taxable_income"] == D("800000.00")
    assert out["annual_tax"] == D("75400.00")


def test_rebate_makes_tax_nil():
    assert compute_income_tax(D("1200000"), regime="new")["annual_tax"] == D("0.00")
    assert compute_income_tax(D("550000"), regime="old")["annual_tax"] == D("0.00")


def test_new_regime_marginal_relief():
    # Income 1,285,000 -> taxable 1,210,000 (just above 12L rebate limit).
    out = compute_income_tax(D("1285000"), regime="new")
    # Slab tax 61,500 but marginal relief caps payable to (1,210,000 - 1,200,000) = 10,000; +cess.
    assert out["annual_tax"] == D("10400.00")


# ── Gratuity ──────────────────────────────────────────────────────────────────

def test_gratuity_formula_eligibility_and_cap():
    assert compute_gratuity(D("50000"), 6) == D("173076.92")   # 50000*15*6/26
    assert compute_gratuity(D("50000"), 4) == D("0.00")        # under 5 years
    assert compute_gratuity(D("500000"), 10) == D("2000000.00")  # capped at 20L


# ── Orchestrator ──────────────────────────────────────────────────────────────

def test_full_month_payroll():
    inp = PayrollInput(
        monthly_gross=D("125000"), components=_structure(),
        payment_days=D("30"), total_days=D("30"),
        regime="new", pf_eligible=True, esi_eligible=False, pt_state="Karnataka",
    )
    out = compute_payroll(inp)
    assert out["earned_gross"] == D("125000.00")
    assert out["earned_basic"] == D("62500.00")
    assert out["deductions"]["epf_employee"] == D("1800.00")   # capped
    assert out["deductions"]["professional_tax"] == D("200.00")
    assert out["deductions"]["tds"] == D("8125.00")            # annual 1.5M
    assert out["deductions"]["total"] == D("10125.00")
    assert out["net_pay"] == D("114875.00")


def test_lop_prorates_earnings_not_tds():
    # 3 LOP days out of 30 -> 27 paid days, ratio 0.9.
    inp = PayrollInput(
        monthly_gross=D("125000"), components=_structure(),
        payment_days=D("27"), total_days=D("30"),
        regime="new", pf_eligible=True, esi_eligible=False, pt_state="Karnataka",
    )
    out = compute_payroll(inp)
    assert out["earned_gross"] == D("112500.00")   # 125000 * 0.9
    assert out["earned_basic"] == D("56250.00")
    assert out["deductions"]["epf_employee"] == D("1800.00")   # basic still > ceiling
    assert out["deductions"]["tds"] == D("8125.00")            # projected on full annual
    assert out["net_pay"] == D("102375.00")


def test_low_wage_triggers_esi_and_no_tds():
    inp = PayrollInput(
        monthly_gross=D("18000"), components=_structure(),
        payment_days=D("30"), total_days=D("30"),
        regime="new", pf_eligible=True, esi_eligible=True, pt_state="Karnataka",
    )
    out = compute_payroll(inp)
    assert out["earned_basic"] == D("9000.00")
    assert out["deductions"]["epf_employee"] == D("1080.00")        # 12% of 9000
    assert out["deductions"]["esi_employee"] == D("135.00")          # 0.75% of 18000
    assert out["employer_contributions"]["esi_employer"] == D("585.00")  # 3.25% of 18000
    assert out["deductions"]["tds"] == D("0.00")                     # below taxable
    assert out["deductions"]["professional_tax"] == D("0.00")        # 18000 < 25000
