"""Pure Indian payroll math — no DB, no I/O. Inputs -> dict.

This is the statutory core of the HR add-on. Keeping it pure makes it trivially
unit-testable and means a Union-Budget change is an edit to the slab/constant
tables here (or, later, to seeded config) rather than a logic rewrite.

Design split (borrowed idea, our shape):
- **Earnings** come from a configurable salary structure of components, each with
  a formula (e.g. Basic = ``GROSS * 0.5``). This solves the "Basic = 50% of what?"
  ambiguity — the tenant declares it.
- **Statutory deductions** (EPF / ESI / PT / TDS) are computed by dedicated
  legally-correct functions, NOT formulas, because they carry caps, thresholds
  and slabs that a formula string cannot safely express.

All money is ``Decimal`` quantized to paise, matching the accounting engine.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# --------------------------------------------------------------------------- #
# Statutory constants (FY 2025-26 / 2026-27). Edit here on a Budget change.
# --------------------------------------------------------------------------- #

EPF_RATE = Decimal("0.12")           # employee & employer each
EPF_WAGE_CEILING = Decimal("15000")  # monthly basic ceiling for EPF
ESI_EMPLOYEE_RATE = Decimal("0.0075")
ESI_EMPLOYER_RATE = Decimal("0.0325")
ESI_GROSS_THRESHOLD = Decimal("21000")  # monthly gross at/under which ESI applies
CESS_RATE = Decimal("0.04")             # Health & Education Cess

STANDARD_DEDUCTION = {
    "new": Decimal("75000"),
    "old": Decimal("50000"),
}

# 87A rebate: taxable income (after deductions) at/under which tax is nil.
REBATE_LIMIT = {
    "new": Decimal("1200000"),
    "old": Decimal("500000"),
}

# Annual income-tax slabs as data: (lower_bound_exclusive, rate). The last band
# has no upper bound. New Regime per Budget 2025 (FY 2025-26).
TAX_SLABS = {
    "new": [
        (Decimal("0"), Decimal("0.00")),
        (Decimal("400000"), Decimal("0.05")),
        (Decimal("800000"), Decimal("0.10")),
        (Decimal("1200000"), Decimal("0.15")),
        (Decimal("1600000"), Decimal("0.20")),
        (Decimal("2000000"), Decimal("0.25")),
        (Decimal("2400000"), Decimal("0.30")),
    ],
    "old": [
        (Decimal("0"), Decimal("0.00")),
        (Decimal("250000"), Decimal("0.05")),
        (Decimal("500000"), Decimal("0.20")),
        (Decimal("1000000"), Decimal("0.30")),
    ],
}

# Professional Tax — state-wise monthly slabs as data: ordered list of
# (gross_at_or_above, monthly_pt). First matching-from-top wins. PT is a state
# subject; these are common defaults and are meant to be overridden by seeded
# config later. "default" is used when a state has no table.
PT_SLABS = {
    "karnataka": [(Decimal("25000"), Decimal("200"))],
    "maharashtra": [(Decimal("10000"), Decimal("200")), (Decimal("7500"), Decimal("175"))],
    "westbengal": [(Decimal("40000"), Decimal("200")), (Decimal("15001"), Decimal("110"))],
    "default": [(Decimal("25000"), Decimal("200"))],
}

_PAISE = Decimal("0.01")


def q(value) -> Decimal:
    """Quantize to paise (2dp, half-up) — the accounting engine's money precision."""
    return Decimal(value).quantize(_PAISE, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- #
# Salary structure (earnings) — the configurable, formula-driven part.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SalaryComponent:
    """One earning line. ``formula`` references prior component abbrs + ``GROSS``.

    e.g. SalaryComponent("Basic", "BASIC", formula="GROSS * 0.5")
         SalaryComponent("HRA", "HRA", formula="BASIC * 0.5")
         SalaryComponent("Special Allowance", "SPECIAL", formula="GROSS - BASIC - HRA")
    """
    name: str
    abbr: str
    formula: str
    statutory_kind: str | None = None        # "basic" tags the EPF base
    depends_on_payment_days: bool = True       # pro-rated by LOP


# Arithmetic helpers available inside formulas (no builtins reachable).
_SAFE_FUNCS = {"min": min, "max": max, "round": round, "abs": abs, "Decimal": Decimal}

# Whitelisted AST node types — formulas are HR-admin authored, but we still only
# allow pure arithmetic over names and whitelisted function calls.
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
    ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.FloorDiv,
)


def _safe_eval(formula: str, context: dict) -> Decimal:
    """Evaluate an arithmetic formula with all numeric literals promoted to
    ``Decimal`` (so ``GROSS * 0.5`` stays exact money), rejecting anything that
    isn't pure arithmetic over whitelisted names/functions."""
    tree = ast.parse(formula, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Disallowed expression element: {type(node).__name__}")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCS
        ):
            raise ValueError("Only whitelisted functions may be called in a formula")

    class _Promote(ast.NodeTransformer):
        def visit_Constant(self, node):  # numbers -> Decimal(str(n))
            if isinstance(node.value, (int, float)):
                return ast.Call(
                    func=ast.Name(id="Decimal", ctx=ast.Load()),
                    args=[ast.Constant(value=str(node.value))],
                    keywords=[],
                )
            return node

    tree = ast.fix_missing_locations(_Promote().visit(tree))
    code = compile(tree, "<formula>", "eval")
    return eval(code, {"__builtins__": {}}, context)  # noqa: S307 - sandboxed above


def evaluate_earnings(
    components: list[SalaryComponent],
    *,
    monthly_gross: Decimal,
) -> dict[str, Decimal]:
    """Evaluate each component's formula in order. Returns {abbr: amount}.

    ``GROSS`` is the full (un-prorated) monthly gross; proration by payment days
    happens later so statutory bases are computed on the contractual figure.
    """
    context: dict[str, object] = dict(_SAFE_FUNCS)
    context["GROSS"] = Decimal(monthly_gross)
    results: dict[str, Decimal] = {}
    for comp in components:
        try:
            value = _safe_eval(comp.formula, context)
        except Exception as exc:
            raise ValueError(f"Bad formula for component {comp.name!r}: {exc}") from exc
        amount = q(Decimal(str(value)))
        results[comp.abbr] = amount
        context[comp.abbr] = amount
    return results


# --------------------------------------------------------------------------- #
# Statutory deduction functions (legal logic, not formulas).
# --------------------------------------------------------------------------- #

def compute_epf(earned_basic: Decimal, *, eligible: bool = True) -> dict[str, Decimal]:
    """Employee & employer EPF — 12% of basic capped at the ₹15,000 wage ceiling.

    Computed on *earned* basic so LOP scales the contribution down naturally.
    Employer EPS/EDLI/admin split is not modelled in v1 (single EPF Payable head).
    """
    if not eligible:
        return {"employee": q(0), "employer": q(0)}
    base = min(Decimal(earned_basic), EPF_WAGE_CEILING)
    contribution = q(base * EPF_RATE)
    return {"employee": contribution, "employer": contribution}


def compute_esi(earned_gross: Decimal, *, eligible: bool = True) -> dict[str, Decimal]:
    """ESI applies only when monthly gross is at/under ₹21,000."""
    gross = Decimal(earned_gross)
    if not eligible or gross > ESI_GROSS_THRESHOLD:
        return {"employee": q(0), "employer": q(0)}
    return {
        "employee": q(gross * ESI_EMPLOYEE_RATE),
        "employer": q(gross * ESI_EMPLOYER_RATE),
    }


def compute_professional_tax(earned_gross: Decimal, *, state: str | None) -> Decimal:
    """Monthly PT from the state slab table (data-driven)."""
    key = "".join((state or "").lower().split())
    slabs = PT_SLABS.get(key) or PT_SLABS["default"]
    gross = Decimal(earned_gross)
    for threshold, amount in slabs:  # ordered high -> low
        if gross >= threshold:
            return q(amount)
    return q(0)


def _slab_tax(taxable: Decimal, slabs: list[tuple[Decimal, Decimal]]) -> Decimal:
    """Progressive tax across the slab bands (pre-rebate, pre-cess)."""
    tax = Decimal("0")
    for i, (lower, rate) in enumerate(slabs):
        upper = slabs[i + 1][0] if i + 1 < len(slabs) else None
        if taxable <= lower:
            break
        band_top = taxable if upper is None else min(taxable, upper)
        tax += (band_top - lower) * rate
    return tax


def compute_income_tax(
    annual_income: Decimal,
    *,
    regime: str = "new",
    deductions: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    """Annual income tax with standard deduction, 87A rebate, marginal relief, cess.

    ``deductions`` is Chapter VI-A (80C/80D/…) — only meaningful in the old regime;
    it flows in from the Form 12BB engine (Step 5). Returns annual + monthly figures.
    """
    regime = regime if regime in TAX_SLABS else "new"
    income = Decimal(annual_income)
    taxable = income - STANDARD_DEDUCTION[regime]
    if regime == "old":
        taxable -= Decimal(deductions)
    taxable = max(Decimal("0"), taxable)

    tax = _slab_tax(taxable, TAX_SLABS[regime])

    # Section 87A rebate: nil tax at/under the limit.
    rebate_limit = REBATE_LIMIT[regime]
    if taxable <= rebate_limit:
        tax = Decimal("0")
    elif regime == "new":
        # Marginal relief: tax payable cannot exceed income above the rebate limit.
        tax = min(tax, taxable - rebate_limit)

    annual_tax = q(tax * (Decimal("1") + CESS_RATE))
    return {
        "taxable_income": q(taxable),
        "annual_tax": annual_tax,
        "monthly_tds": q(annual_tax / Decimal("12")),
    }


# --------------------------------------------------------------------------- #
# Gratuity (used by F&F, Step 6) — kept here as pure math.
# --------------------------------------------------------------------------- #

GRATUITY_CEILING = Decimal("2000000")  # ₹20 lakh statutory cap (Sec 10(10))


def compute_gratuity(last_drawn_basic: Decimal, years_of_service: int) -> Decimal:
    """(Last Basic × 15 × Years) / 26, capped at ₹20 lakh. Nil under 5 years."""
    if years_of_service < 5:
        return q(0)
    raw = (Decimal(last_drawn_basic) * Decimal("15") * Decimal(years_of_service)) / Decimal("26")
    return q(min(raw, GRATUITY_CEILING))


def compute_leave_encashment(last_drawn_basic: Decimal, unutilized_leaves: Decimal) -> Decimal:
    """Per-day basis = Basic / 30, times unused leave days."""
    return q((Decimal(last_drawn_basic) / Decimal("30")) * Decimal(unutilized_leaves))


def compute_notice_recovery(last_drawn_basic: Decimal, unpaid_notice_days: Decimal) -> Decimal:
    """Recovery when the notice period is not served — Basic/30 per shortfall day."""
    return q((Decimal(last_drawn_basic) / Decimal("30")) * Decimal(unpaid_notice_days))


def compute_fnf(
    *,
    last_drawn_basic: Decimal,
    years_of_service: int,
    unutilized_leaves: Decimal = Decimal("0"),
    unpaid_notice_days: Decimal = Decimal("0"),
    other_payouts: Decimal = Decimal("0"),
    other_recoveries: Decimal = Decimal("0"),
) -> dict:
    """Full & Final settlement: gratuity + leave encashment + other payouts,
    less notice recovery and other recoveries. Pure math."""
    gratuity = compute_gratuity(last_drawn_basic, years_of_service)
    encashment = compute_leave_encashment(last_drawn_basic, unutilized_leaves)
    notice = compute_notice_recovery(last_drawn_basic, unpaid_notice_days)

    gross_payout = q(gratuity + encashment + Decimal(other_payouts))
    total_recovery = q(notice + Decimal(other_recoveries))
    net = q(gross_payout - total_recovery)
    return {
        "gratuity": gratuity,
        "leave_encashment": encashment,
        "other_payouts": q(other_payouts),
        "gross_payout": gross_payout,
        "notice_recovery": notice,
        "other_recoveries": q(other_recoveries),
        "total_recovery": total_recovery,
        "net_settlement": net,
        "eligible_for_gratuity": years_of_service >= 5,
    }


# --------------------------------------------------------------------------- #
# Orchestrator — one employee, one month.
# --------------------------------------------------------------------------- #

@dataclass
class PayrollInput:
    monthly_gross: Decimal           # contractual monthly gross (full month)
    components: list[SalaryComponent]
    payment_days: Decimal            # days to be paid (total_days - lop)
    total_days: Decimal              # calendar/working days in the period
    regime: str = "new"
    pf_eligible: bool = True
    esi_eligible: bool = False
    pt_state: str | None = None
    annual_other_income: Decimal = Decimal("0")    # added to annualised gross for TDS
    chapter_via_deductions: Decimal = Decimal("0")  # old-regime 80C etc.


def compute_payroll(inp: PayrollInput) -> dict:
    """Full monthly payroll for one employee. Returns earnings / deductions /
    employer contributions / net, plus the totals the GL posting (Step 3) needs."""
    total_days = Decimal(inp.total_days)
    payment_days = max(Decimal("0"), min(Decimal(inp.payment_days), total_days))
    ratio = (payment_days / total_days) if total_days > 0 else Decimal("0")

    full = evaluate_earnings(inp.components, monthly_gross=inp.monthly_gross)
    # Pro-rate each earning by payment days.
    earned = {abbr: q(amount * ratio) for abbr, amount in full.items()}
    earned_gross = q(sum(earned.values(), Decimal("0")))

    # Basic = the component tagged statutory_kind="basic" (fallback: abbr "BASIC").
    basic_abbr = next(
        (c.abbr for c in inp.components if c.statutory_kind == "basic"),
        "BASIC",
    )
    earned_basic = earned.get(basic_abbr, Decimal("0"))

    epf = compute_epf(earned_basic, eligible=inp.pf_eligible)
    esi = compute_esi(earned_gross, eligible=inp.esi_eligible)
    pt = compute_professional_tax(earned_gross, state=inp.pt_state)

    # TDS projected off the *contractual* annual gross (LOP-independent), per
    # standard practice of projecting annual liability.
    annual_income = q(Decimal(inp.monthly_gross) * Decimal("12") + Decimal(inp.annual_other_income))
    tax = compute_income_tax(
        annual_income, regime=inp.regime, deductions=inp.chapter_via_deductions
    )
    tds = tax["monthly_tds"]

    employee_deductions = q(epf["employee"] + esi["employee"] + pt + tds)
    net = q(earned_gross - employee_deductions)

    return {
        "earnings": {abbr: earned[abbr] for abbr in earned},
        "earned_gross": earned_gross,
        "earned_basic": earned_basic,
        "payment_days": q(payment_days),
        "total_days": q(total_days),
        "deductions": {
            "epf_employee": epf["employee"],
            "esi_employee": esi["employee"],
            "professional_tax": pt,
            "tds": tds,
            "total": employee_deductions,
        },
        "employer_contributions": {
            "epf_employer": epf["employer"],
            "esi_employer": esi["employer"],
        },
        "tds_detail": tax,
        "net_pay": net,
    }
