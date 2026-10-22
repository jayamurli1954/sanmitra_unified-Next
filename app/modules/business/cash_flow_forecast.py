"""Cash Flow Forecast — the "runway" compute layer.

A near-sibling of ``financial_health.py``, following the same **compute → (narrate)
→ visualize** pipeline and the same non-negotiable guardrail: *every figure is
computed deterministically from the posted ledger; the LLM only rewrites prose,
never a number.* It derives a short-horizon cash projection, a runway estimate and
a burn-rate breakdown from two trusted inputs:

* ``get_business_dashboard`` — as-of cash balance, FYTD income/expense (for the
  operating run-rate), and the financial-year start (to size the elapsed window).
* ``ar_ap_aging`` — receivable / payable open-item outstanding (the one-time
  working-capital unwind that converts the balance sheet into near-term cash).

Model (deliberately simple and auditable for v1):

* **Operating cash flow / month** = (FYTD income − FYTD expense) / months elapsed.
  A forward run-rate applied to every projected month. Negative = net burn.
* **Working-capital unwind** = total outstanding AR − total outstanding AP, applied
  **once** in month 1. This is the collection/settlement of what is *already on the
  books*, kept separate from the operating run-rate so the two never double-count.
* **Projected month-end cash**: ``closing[1] = cash + operating_cf + wc_unwind``;
  ``closing[i>1] = closing[i-1] + operating_cf``.
* **Runway** = near-term liquidity (cash + AR − AP) ÷ monthly net burn, or ∞ when the
  business is operating cash-positive.

TIMING ASSUMPTION (v1): aging buckets are *days past due*, not future due dates, so
all currently-outstanding AR/AP is treated as a single month-1 unwind rather than a
precise payment schedule. The response labels this in ``assumptions`` so it is not
read as an exact AR/AP calendar. A later slice can use real invoice due dates.

``assemble_cash_flow_forecast`` is a pure function over those inputs (easily unit
tested); ``build_cash_flow_forecast`` is the thin async gatherer that fetches them.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import get_business_dashboard
from app.config import get_settings
from app.modules.business import allocation_service

_logger = logging.getLogger(__name__)

# Average days per month, for annualising FYTD figures into a monthly run-rate and
# for turning a fractional-month runway into a calendar date. Matches financial_health.
_DAYS_PER_MONTH = Decimal("30.44")

# Default projection horizon (months) and the clamp applied to the request param.
_DEFAULT_HORIZON = 6
_MIN_HORIZON = 1
_MAX_HORIZON = 24

# Aging bucket considered a collection risk that undermines the forecast.
_AT_RISK_BUCKET = "90+"

_MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _d(value) -> Decimal:
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal("0")


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> str:
    return str(_q(value))


def _band(value, *, good, warn, higher_is_better=True) -> str:
    """Three-way tone against good/warn thresholds (mirrors financial_health._band)."""
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


def _kpi(key, label, value, unit, hint, tone="neutral") -> dict:
    return {"key": key, "label": label, "value": value, "unit": unit, "hint": hint, "tone": tone}


def _aging_total(aging: dict) -> Decimal:
    """Grand total outstanding across all buckets, tolerant of the aging payload shape."""
    if not aging:
        return Decimal("0")
    grand = aging.get("grand_total")
    if grand is not None:
        return _d(grand)
    totals = aging.get("totals") or {}
    return sum((_d(v) for v in totals.values()), Decimal("0"))


def _month_label(start: date, offset: int) -> str:
    """Abbreviated month label ``offset`` months after ``start`` (e.g. 'Jul 26')."""
    month_index = (start.month - 1 + offset) % 12
    year = start.year + (start.month - 1 + offset) // 12
    return f"{_MONTH_ABBR[month_index]} {year % 100:02d}"


def assemble_cash_flow_forecast(
    *, dashboard: dict, ar_aging: dict, ap_aging: dict, as_of: date, horizon_months: int = _DEFAULT_HORIZON
) -> dict:
    """Derive the cash projection, runway, burn-rate KPIs, chart specs and alerts
    from already-computed ledger figures. Pure function — all inputs are trusted,
    deterministic numbers, so the output is safe to hand to an LLM for narration."""
    horizon = max(_MIN_HORIZON, min(int(horizon_months or _DEFAULT_HORIZON), _MAX_HORIZON))

    income = _d(dashboard.get("income", {}).get("fytd"))
    expense = _d(dashboard.get("expenses", {}).get("fytd"))
    cash = _d(dashboard.get("cash_and_bank"))

    ar_total = _aging_total(ar_aging)
    ap_total = _aging_total(ap_aging)
    at_risk_ar = _d(((ar_aging or {}).get("totals") or {}).get(_AT_RISK_BUCKET))

    fy_start = date.fromisoformat(dashboard["financial_year_start"])
    days_elapsed = max((as_of - fy_start).days + 1, 1)
    months_elapsed = max(Decimal(days_elapsed) / _DAYS_PER_MONTH, Decimal("1"))

    # --- Run-rate: the forward operating cash flow per month -------------- #
    avg_monthly_income = _q(income / months_elapsed)
    avg_monthly_expense = _q(expense / months_elapsed)
    operating_cf = _q(avg_monthly_income - avg_monthly_expense)  # +ve = cash generative
    monthly_net_burn = -operating_cf  # +ve = burning cash
    gross_burn = avg_monthly_expense

    # --- One-time working-capital unwind (collect AR, settle AP) ---------- #
    wc_unwind = _q(ar_total - ap_total)

    # Near-term liquidity: cash once the current book is converted to cash.
    liquidity = _q(cash + wc_unwind)

    # --- Runway ---------------------------------------------------------- #
    # Cash-positive (operating_cf >= 0) → the business funds itself: infinite runway.
    if monthly_net_burn <= 0:
        runway_months = None
        zero_crossing = None
    else:
        runway_months = float(_q(liquidity / monthly_net_burn)) if liquidity > 0 else 0.0
        # A tiny burn against large liquidity yields a runway of thousands of years,
        # whose day count overflows datetime.timedelta (max ~2.7M days). Treat anything
        # beyond ~100 years as effectively unlimited: no finite zero-crossing date.
        days_to_zero = runway_months * float(_DAYS_PER_MONTH)
        if days_to_zero > 36500:
            zero_crossing = None
        else:
            zero_crossing = (as_of + timedelta(days=days_to_zero)).isoformat()

    # --- Projected month-end cash series --------------------------------- #
    # Month 1 carries the one-time WC unwind; every month carries operating_cf.
    projection: list[dict] = []
    labels: list[str] = ["Now"]
    series: list[float] = [float(_q(cash))]
    running = cash
    for i in range(1, horizon + 1):
        opening = running
        wc = wc_unwind if i == 1 else Decimal("0")
        closing = _q(opening + operating_cf + wc)
        running = closing
        label = _month_label(as_of, i)
        labels.append(label)
        series.append(float(closing))
        projection.append({
            "month": i,
            "label": label,
            "opening": _money(opening),
            "operating_cf": _money(operating_cf),
            "wc_unwind": _money(wc),
            "closing": _money(closing),
        })

    projected_end = _q(running)

    # --- KPIs ------------------------------------------------------------ #
    burn_tone = "good" if operating_cf >= 0 else ("warn" if monthly_net_burn <= gross_burn / 2 else "bad")
    kpis = [
        _kpi("opening_cash", "Cash & bank (now)", _money(cash), "₹",
             "As-of balance across cash and bank accounts.",
             "bad" if cash <= 0 else "neutral"),
        _kpi("operating_cf", "Operating cash flow", _money(operating_cf), "₹/mo",
             "Average monthly income less expense (run-rate). Negative means net burn.",
             burn_tone),
        _kpi("net_burn", "Net burn", _money(monthly_net_burn if monthly_net_burn > 0 else Decimal("0")), "₹/mo",
             "Monthly cash consumed at the current run-rate (0 when cash-positive).",
             "good" if monthly_net_burn <= 0 else "warn"),
        _kpi("gross_burn", "Gross burn", _money(gross_burn), "₹/mo",
             "Average monthly expense, regardless of income."),
        _kpi("expected_collections", "Expected collections", _money(ar_total), "₹",
             "Total outstanding receivables (one-time inflow as the book is collected)."),
        _kpi("upcoming_payments", "Upcoming payments", _money(ap_total), "₹",
             "Total outstanding payables (one-time outflow as the book is settled)."),
        _kpi("projected_liquidity", "Near-term liquidity", _money(liquidity), "₹",
             "Cash plus receivables less payables — cash available once the book clears.",
             "bad" if liquidity <= 0 else "neutral"),
        _kpi("runway", "Cash runway",
             runway_months if runway_months is not None else "∞", "months",
             "Near-term liquidity divided by monthly net burn. ∞ when cash-positive.",
             "good" if runway_months is None else _band(runway_months, good=6, warn=3)),
        _kpi("projected_end_cash", "Projected cash",
             _money(projected_end), "₹",
             f"Projected month-end cash after {horizon} months at the current run-rate.",
             "bad" if projected_end < 0 else "neutral"),
    ]

    # --- Charts: fixed vocabulary, rendered deterministically ------------ #
    charts = [
        {
            "key": "projected_cash",
            "type": "line",
            "title": f"Projected cash balance ({horizon} months)",
            "unit": "₹",
            "x": labels,
            "series": [{"name": "Projected cash", "data": series}],
        },
        {
            "key": "collections_vs_payments",
            "type": "grouped_bar",
            "title": "Outstanding collections vs payments",
            "unit": "₹",
            "x": ["Receivables", "Payables"],
            "series": [{"name": "Outstanding", "data": [float(ar_total), float(ap_total)]}],
        },
    ]

    # --- Alerts: deterministic thresholds over the computed figures ------- #
    alerts: list[dict] = []

    if cash <= 0:
        alerts.append({"severity": "danger", "title": "Cash balance is zero or negative",
                       "message": f"Cash & bank stands at ₹{_money(cash)}."})

    if runway_months is None:
        alerts.append({"severity": "info", "title": "Cash generative",
                       "message": "The business is covering its costs from operations — "
                                  "no burn-down at the current run-rate."})
    elif runway_months < 3:
        alerts.append({"severity": "danger", "title": "Runway under 3 months",
                       "message": f"About {runway_months} months of cash at the current "
                                  f"burn of ₹{_money(monthly_net_burn)}/month."})
    elif runway_months < 6:
        alerts.append({"severity": "warning", "title": "Runway under 6 months",
                       "message": f"About {runway_months} months of cash at the current "
                                  f"burn of ₹{_money(monthly_net_burn)}/month."})

    if ap_total > cash and ap_total > 0:
        alerts.append({"severity": "warning", "title": "Payables exceed cash on hand",
                       "message": f"₹{_money(ap_total)} is payable against ₹{_money(cash)} "
                                  f"cash — collections are needed to cover it."})

    if at_risk_ar > 0:
        alerts.append({"severity": "warning", "title": "Collection risk over 90 days",
                       "message": f"₹{_money(at_risk_ar)} of receivables is more than 90 days "
                                  f"overdue and may not arrive as forecast."})

    if projected_end < 0 and runway_months is not None:
        alerts.append({"severity": "danger", "title": "Projection turns cash-negative",
                       "message": f"Projected cash is ₹{_money(projected_end)} by "
                                  f"{labels[-1]} on the current run-rate."})

    if not alerts:
        alerts.append({"severity": "info", "title": "Cash position stable",
                       "message": "Projected cash stays positive across the horizon."})

    # --- Deterministic headline (AI narration can replace this later) ----- #
    if runway_months is None:
        runway_phrase = "the business is cash generative (no runway limit at the current run-rate)"
    else:
        runway_phrase = f"about {runway_months} months of runway at a net burn of ₹{_money(monthly_net_burn)}/month"
    summary = (
        f"Cash & bank is ₹{_money(cash)} with ₹{_money(ar_total)} receivable and "
        f"₹{_money(ap_total)} payable, giving ₹{_money(liquidity)} of near-term liquidity. "
        f"Operating cash flow runs at ₹{_money(operating_cf)}/month, so {runway_phrase}. "
        f"Projected cash after {horizon} months is ₹{_money(projected_end)}."
    )

    return {
        "as_of": as_of.isoformat(),
        "financial_year_start": fy_start.isoformat(),
        "horizon_months": horizon,
        "summary": summary,
        "runway_months": runway_months,
        "zero_crossing_date": zero_crossing,
        "kpis": kpis,
        "charts": charts,
        "projection": projection,
        "alerts": alerts,
        "assumptions": [
            "Figures are computed from the posted ledger; the AI narrative never changes them.",
            "Aging buckets are days past due, not future due dates: all currently-outstanding "
            "receivables and payables are modelled as a one-time month-1 unwind, not a precise "
            "payment schedule.",
            "Operating cash flow is the FYTD income-less-expense run-rate projected forward; it "
            "assumes trading continues at the year-to-date average.",
        ],
    }


# --------------------------------------------------------------------------- #
# AI narration — the "narrate" step. The model only rewrites the already-computed
# figures into a CFO-style narrative; it never invents numbers. Privacy guardrail:
# we send aggregate KPIs/alerts only — no party names, invoice numbers or PII.
# --------------------------------------------------------------------------- #

_NARRATION_SYSTEM_PROMPT = (
    "You are a CFO advisor for an Indian small business inside MitraBooks. You are "
    "given a JSON snapshot of cash-flow and runway figures that were computed "
    "deterministically from the company's accounting ledger. Write a short, plain-English "
    "narrative (at most 120 words, 2-3 short paragraphs or a few bullet points) covering "
    "the cash position, how long the runway lasts, what is driving the burn, and one or "
    "two concrete next actions to extend runway or improve collections. "
    "CRITICAL RULES: use ONLY the numbers given to you — never invent, estimate, or "
    "extrapolate any figure. Quote amounts exactly as provided (they are in INR). Treat "
    "the forecast as an estimate, not a guarantee. Do not give tax or legal advice. "
    "Be direct and practical."
)


def build_narration_prompt(payload: dict) -> str:
    """Compact, figure-only prompt for the narrator. Pure: deterministic snapshot of
    the KPIs, alerts and headline — nothing the model could contradict."""
    snapshot = {
        "as_of": payload.get("as_of"),
        "horizon_months": payload.get("horizon_months"),
        "runway_months": payload.get("runway_months"),
        "zero_crossing_date": payload.get("zero_crossing_date"),
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
        "Here is the cash-flow snapshot (all figures already computed from the ledger):\n\n"
        + json.dumps(snapshot, ensure_ascii=False, indent=2)
        + "\n\nWrite the CFO cash-flow narrative now."
    )


async def narrate_cash_flow_forecast(payload: dict) -> str | None:
    """Call Claude to narrate the snapshot. Returns None (caller falls back to the
    deterministic summary) when disabled, unkeyed, or on any error."""
    settings = get_settings()
    if not settings.CASH_FLOW_AI_ENABLED:
        return None
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        _logger.info("cash_flow_forecast narration skipped: ANTHROPIC_API_KEY not configured")
        return None

    api_base = settings.ANTHROPIC_API_BASE.rstrip("/")
    body = {
        "model": settings.CASH_FLOW_AI_MODEL,
        "max_tokens": settings.CASH_FLOW_AI_MAX_TOKENS,
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
            _logger.error("cash_flow_forecast narration http_error status=%d body=%s",
                          response.status_code, (response.text or "")[:300])
            return None
        content = response.json().get("content") or []
        text = "\n".join(
            str(part.get("text") or "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
        return text or None
    except Exception as exc:
        _logger.exception("cash_flow_forecast narration exception: %s", exc)
        return None


async def build_cash_flow_forecast(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    as_of: date | None = None,
    horizon_months: int = _DEFAULT_HORIZON,
    narrate: bool = True,
) -> dict:
    """Gather the trusted ledger figures, assemble the Cash Flow Forecast, and
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
    payload = assemble_cash_flow_forecast(
        dashboard=dashboard, ar_aging=ar_aging, ap_aging=ap_aging,
        as_of=as_of, horizon_months=horizon_months,
    )
    payload["narrative"] = await narrate_cash_flow_forecast(payload) if narrate else None
    return payload
