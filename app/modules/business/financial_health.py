"""Financial Health — the CFO-Insight "compute" layer.

Implements the **compute → (narrate) → visualize** pipeline from
``docs/FOSS_CONCEPTUAL_BORROWING.md`` §5. The non-negotiable guardrail is that
*every figure is computed deterministically from the posted ledger* — this module
never lets an LLM invent numbers. It derives a catalog of KPIs, a small fixed
vocabulary of chart specs, and a deterministic alert set from two trusted inputs:

* ``get_business_dashboard`` — FYTD P&L (income/expense/net), as-of balances
  (cash, receivables, payables, GST), and a 6-month income-vs-expense trend.
* ``ar_ap_aging`` — receivable / payable open-item outstanding bucketed by age.

``assemble_financial_health`` is a pure function over those inputs (easily unit
tested); ``build_financial_health`` is the thin async gatherer that fetches them.
A future slice can add AI narration on top of the ``summary`` field — the model
would only rewrite prose, never the figures or the chart renderer.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import get_business_dashboard
from app.config import get_settings
from app.modules.business import allocation_service

_logger = logging.getLogger(__name__)

# Aging buckets considered "overdue" (past the current 0-30 window) and "at risk".
_OVERDUE_BUCKETS = ("31-60", "61-90", "90+")
_AT_RISK_BUCKET = "90+"

# Average days per month for annualising FYTD figures into monthly run-rates.
_DAYS_PER_MONTH = Decimal("30.44")


def _d(value) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal("0")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pct(part: Decimal, whole: Decimal) -> float:
    if whole == 0:
        return 0.0
    return float(_q(part / whole * 100))


def _money(value: Decimal) -> str:
    return str(_q(value))


def _overdue_total(aging: dict) -> Decimal:
    totals = (aging or {}).get("totals") or {}
    return sum((_d(totals.get(b)) for b in _OVERDUE_BUCKETS), Decimal("0"))


def _kpi(key, label, value, unit, hint, tone="neutral") -> dict:
    return {"key": key, "label": label, "value": value, "unit": unit, "hint": hint, "tone": tone}


def _band(value, *, good, warn, higher_is_better=True) -> str:
    """Three-way tone for a metric against good/warn thresholds.

    higher_is_better: value >= good -> good, >= warn -> warn, else bad.
    Otherwise the comparison is inverted (lower is better)."""
    if value is None:
        return "neutral"
    if higher_is_better:
        if value >= good:
            return "good"
        if value >= warn:
            return "warn"
        return "bad"
    if value <= good:
        return "good"
    if value <= warn:
        return "warn"
    return "bad"


def assemble_financial_health(*, dashboard: dict, ar_aging: dict, ap_aging: dict, as_of: date) -> dict:
    """Derive KPIs, chart specs and alerts from already-computed ledger figures.

    Pure function — all inputs are trusted, deterministic numbers; the output is
    safe to send to an LLM for narration because it contains no free-text the
    model could contradict."""
    income = _d(dashboard.get("income", {}).get("fytd"))
    expense = _d(dashboard.get("expenses", {}).get("fytd"))
    net = _d(dashboard.get("net_position", {}).get("profit_loss"))
    cash = _d(dashboard.get("cash_and_bank"))
    receivable = _d(dashboard.get("receivables"))
    payable = _d(dashboard.get("payables"))
    gst_payable = _d(dashboard.get("gst", {}).get("payable"))

    fy_start = date.fromisoformat(dashboard["financial_year_start"])
    days_elapsed = max((as_of - fy_start).days + 1, 1)
    months_elapsed = max(Decimal(days_elapsed) / _DAYS_PER_MONTH, Decimal("1"))

    # --- Derived ratios (all guard against divide-by-zero) ---------------- #
    net_margin = _pct(net, income)

    avg_monthly_expense = _q(expense / months_elapsed) if expense > 0 else Decimal("0")
    runway_months = (
        float(_q(cash / avg_monthly_expense)) if avg_monthly_expense > 0 else None
    )

    # Days Sales/Payables Outstanding scaled to the elapsed FY window.
    debtor_days = int(_q(receivable / income * days_elapsed)) if income > 0 else None
    creditor_days = int(_q(payable / expense * days_elapsed)) if expense > 0 else None

    current_assets = cash + receivable
    current_liabilities = payable + (gst_payable if gst_payable > 0 else Decimal("0"))
    working_capital = current_assets - current_liabilities
    current_ratio = (
        float(_q(current_assets / current_liabilities)) if current_liabilities > 0 else None
    )

    kpis = [
        _kpi("revenue", "Revenue (FYTD)", _money(income), "₹",
             "Posted income, financial-year-to-date."),
        _kpi("expenses", "Expenses (FYTD)", _money(expense), "₹",
             "Posted expenses, financial-year-to-date."),
        _kpi("net_profit", "Net profit (FYTD)", _money(net), "₹",
             "Income less expenses.", "good" if net > 0 else "bad"),
        _kpi("net_margin", "Net margin", net_margin, "%",
             "Net profit as a percentage of revenue.",
             _band(net_margin, good=10, warn=0)),
        _kpi("cash", "Cash & bank", _money(cash), "₹",
             "As-of balance across cash and bank accounts.",
             "bad" if cash <= 0 else "neutral"),
        _kpi("receivables", "Receivables", _money(receivable), "₹",
             "Outstanding amounts owed by customers."),
        _kpi("payables", "Payables", _money(payable), "₹",
             "Outstanding amounts owed to vendors."),
        _kpi("working_capital", "Working capital", _money(working_capital), "₹",
             "Current assets (cash + receivables) less current liabilities.",
             "good" if working_capital > 0 else "bad"),
        _kpi("current_ratio", "Current ratio",
             current_ratio if current_ratio is not None else "—", "x",
             "Current assets divided by current liabilities.",
             _band(current_ratio, good=1.5, warn=1.0)),
        _kpi("cash_runway", "Cash runway",
             runway_months if runway_months is not None else "—", "months",
             "Cash divided by average monthly expense.",
             _band(runway_months, good=3, warn=1)),
        _kpi("debtor_days", "Debtor days",
             debtor_days if debtor_days is not None else "—", "days",
             "Average collection period (DSO).",
             _band(debtor_days, good=45, warn=75, higher_is_better=False)),
        _kpi("creditor_days", "Creditor days",
             creditor_days if creditor_days is not None else "—", "days",
             "Average payment period (DPO)."),
    ]

    # --- Charts: small fixed vocabulary, rendered deterministically -------- #
    trend = dashboard.get("monthly_trend") or []
    months = [row[0] for row in trend]
    inc_series = [row[1] for row in trend]
    exp_series = [row[2] for row in trend]
    profit_series = [round(row[1] - row[2], 2) for row in trend]

    def _aging_series(aging: dict) -> list[float]:
        totals = (aging or {}).get("totals") or {}
        order = (aging or {}).get("buckets_order") or ["0-30", "31-60", "61-90", "90+"]
        return [float(_d(totals.get(b))) for b in order]

    aging_order = (ar_aging or {}).get("buckets_order") or ["0-30", "31-60", "61-90", "90+"]

    charts = [
        {
            "key": "income_expense",
            "type": "grouped_bar",
            "title": "Income vs expenses (6 months)",
            "unit": "₹ lakhs",
            "x": months,
            "series": [
                {"name": "Income", "data": inc_series},
                {"name": "Expenses", "data": exp_series},
            ],
        },
        {
            "key": "profit_trend",
            "type": "line",
            "title": "Profit trend (6 months)",
            "unit": "₹ lakhs",
            "x": months,
            "series": [{"name": "Net profit", "data": profit_series}],
        },
        {
            "key": "receivables_aging",
            "type": "bar",
            "title": "Receivables aging",
            "unit": "₹",
            "x": aging_order,
            "series": [{"name": "Receivable", "data": _aging_series(ar_aging)}],
        },
        {
            "key": "payables_aging",
            "type": "bar",
            "title": "Payables aging",
            "unit": "₹",
            "x": aging_order,
            "series": [{"name": "Payable", "data": _aging_series(ap_aging)}],
        },
    ]

    # --- Alerts: deterministic thresholds over the computed figures -------- #
    alerts: list[dict] = []

    if net < 0:
        alerts.append({"severity": "danger", "title": "Operating at a loss",
                       "message": f"Net position is ₹{_money(net)} for the year so far."})
    elif income > 0 and net_margin < 5:
        alerts.append({"severity": "warning", "title": "Thin net margin",
                       "message": f"Net margin is {net_margin}%, below a 5% comfort line."})

    if cash <= 0:
        alerts.append({"severity": "danger", "title": "Cash balance is zero or negative",
                       "message": f"Cash & bank stands at ₹{_money(cash)}."})
    elif runway_months is not None and runway_months < 2:
        alerts.append({"severity": "warning", "title": "Low cash runway",
                       "message": f"About {runway_months} months of cash at the current burn rate."})

    overdue_ar = _overdue_total(ar_aging)
    at_risk_ar = _d(((ar_aging or {}).get("totals") or {}).get(_AT_RISK_BUCKET))
    if at_risk_ar > 0:
        alerts.append({"severity": "danger", "title": "Receivables over 90 days",
                       "message": f"₹{_money(at_risk_ar)} is more than 90 days overdue and at risk."})
    elif overdue_ar > 0:
        alerts.append({"severity": "warning", "title": "Overdue receivables",
                       "message": f"₹{_money(overdue_ar)} is past its due date."})

    if current_ratio is not None and current_ratio < 1:
        alerts.append({"severity": "warning", "title": "Current ratio below 1",
                       "message": f"Current liabilities exceed current assets (ratio {current_ratio})."})

    if gst_payable > 0:
        alerts.append({"severity": "info", "title": "GST payable",
                       "message": f"₹{_money(gst_payable)} GST is due for settlement."})

    if not alerts:
        alerts.append({"severity": "info", "title": "All clear",
                       "message": "Key indicators are within healthy thresholds."})

    # --- Deterministic headline (AI narration can replace this later) ------ #
    profit_word = "a profit" if net >= 0 else "a loss"
    summary = (
        f"Financial-year-to-date revenue is ₹{_money(income)} against ₹{_money(expense)} "
        f"of expenses, {profit_word} of ₹{_money(abs(net))} ({net_margin}% margin). "
        f"Cash & bank stands at ₹{_money(cash)}; receivables ₹{_money(receivable)}, "
        f"payables ₹{_money(payable)}."
    )

    return {
        "as_of": as_of.isoformat(),
        "financial_year_start": fy_start.isoformat(),
        "period_days": days_elapsed,
        "summary": summary,
        "kpis": kpis,
        "charts": charts,
        "alerts": alerts,
    }


# --------------------------------------------------------------------------- #
# AI narration — the "narrate" step. The model only rewrites the already-computed
# figures into a CFO-style narrative; it never invents numbers. Privacy guardrail:
# we send aggregate KPIs/alerts only — no party names, invoice numbers or PII.
# --------------------------------------------------------------------------- #

_NARRATION_SYSTEM_PROMPT = (
    "You are a CFO advisor for an Indian small business inside MitraBooks. You are "
    "given a JSON snapshot of financial figures that were computed deterministically "
    "from the company's accounting ledger. Write a short, plain-English narrative "
    "(at most 120 words, 2-3 short paragraphs or a few bullet points) highlighting "
    "what is going well, what needs attention, and one or two concrete next actions. "
    "CRITICAL RULES: use ONLY the numbers given to you — never invent, estimate, or "
    "extrapolate any figure. Quote amounts exactly as provided (they are in INR). "
    "Do not give tax or legal advice. Be direct and practical."
)


def build_narration_prompt(payload: dict) -> str:
    """Compact, figure-only prompt for the narrator. Pure: deterministic snapshot
    of the KPIs, alerts and headline — nothing the model could contradict."""
    snapshot = {
        "as_of": payload.get("as_of"),
        "financial_year_start": payload.get("financial_year_start"),
        "headline": payload.get("summary"),
        "kpis": [
            {"label": k.get("label"), "value": k.get("value"),
             "unit": k.get("unit"), "tone": k.get("tone")}
            for k in payload.get("kpis", [])
        ],
        "alerts": [
            {"severity": a.get("severity"), "title": a.get("title"),
             "message": a.get("message")}
            for a in payload.get("alerts", [])
        ],
    }
    return (
        "Here is the financial snapshot (all figures already computed from the ledger):\n\n"
        + json.dumps(snapshot, ensure_ascii=False, indent=2)
        + "\n\nWrite the CFO narrative now."
    )


async def narrate_financial_health(payload: dict) -> str | None:
    """Call Claude to narrate the snapshot. Returns None (caller falls back to the
    deterministic summary) when disabled, unkeyed, or on any error."""
    settings = get_settings()
    if not settings.FINANCIAL_HEALTH_AI_ENABLED:
        return None
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        _logger.info("financial_health narration skipped: ANTHROPIC_API_KEY not configured")
        return None

    api_base = settings.ANTHROPIC_API_BASE.rstrip("/")
    model = settings.FINANCIAL_HEALTH_AI_MODEL
    body = {
        "model": model,
        "max_tokens": settings.FINANCIAL_HEALTH_AI_MAX_TOKENS,
        "temperature": 0.3,
        "system": _NARRATION_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_narration_prompt(payload)}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{api_base}/messages", headers=headers, json=body)
        if response.status_code >= 400:
            _logger.error("financial_health narration http_error status=%d body=%s",
                          response.status_code, (response.text or "")[:300])
            return None
        content = response.json().get("content") or []
        text = "\n".join(
            str(part.get("text") or "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
        return text or None
    except Exception as exc:
        _logger.exception("financial_health narration exception: %s", exc)
        return None


async def build_financial_health(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    as_of: date | None = None,
    narrate: bool = True,
) -> dict:
    """Gather the trusted ledger figures, assemble the Financial Health view, and
    (optionally) attach an AI narrative. The narrative is advisory prose only — the
    deterministic ``summary`` and all figures remain authoritative."""
    as_of = as_of or date.today()
    dashboard = await get_business_dashboard(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )
    ar_aging = await allocation_service.ar_ap_aging(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, kind="receivable", as_of=as_of,
    )
    ap_aging = await allocation_service.ar_ap_aging(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, kind="payable", as_of=as_of,
    )
    payload = assemble_financial_health(
        dashboard=dashboard, ar_aging=ar_aging, ap_aging=ap_aging, as_of=as_of,
    )
    payload["narrative"] = await narrate_financial_health(payload) if narrate else None
    return payload
