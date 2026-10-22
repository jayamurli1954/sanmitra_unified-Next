"""Cash Flow Forecast assembler — derives the cash projection, runway and burn-rate
KPIs/alerts purely from already-computed ledger figures (dashboard + AR/AP aging).
Pure function, no DB: it must never invent numbers, only reshape the trusted inputs."""
import json
from datetime import date

import pytest

from app.modules.business import cash_flow_forecast
from app.modules.business.cash_flow_forecast import (
    assemble_cash_flow_forecast,
    build_narration_prompt,
    narrate_cash_flow_forecast,
)

AS_OF = date(2026, 6, 30)  # 91 days into FY (Apr 1) → ~2.99 months elapsed


def _dashboard(**overrides) -> dict:
    base = {
        "as_of": AS_OF.isoformat(),
        "financial_year_start": "2026-04-01",
        "income": {"fytd": "900000.00"},
        "expenses": {"fytd": "600000.00"},
        "net_position": {"profit_loss": "300000.00"},
        "cash_and_bank": "300000.00",
        "receivables": "250000.00",
        "payables": "150000.00",
        "gst": {"payable": "50000.00"},
        "monthly_trend": [],
    }
    base.update(overrides)
    return base


def _aging(totals: dict) -> dict:
    order = ["0-30", "31-60", "61-90", "90+"]
    grand = sum(float(totals.get(b, 0)) for b in order)
    return {
        "buckets_order": order,
        "totals": {b: totals.get(b, "0.00") for b in order},
        "grand_total": f"{grand:.2f}",
        "by_party": [],
    }


def test_cash_positive_books_have_infinite_runway():
    # Income (900k) > expense (600k) over the elapsed window → operating cash-positive.
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(),
        ar_aging=_aging({"0-30": "250000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}),
        as_of=AS_OF,
    )
    assert out["runway_months"] is None  # ∞ / cash generative
    assert out["zero_crossing_date"] is None
    kpis = {k["key"]: k for k in out["kpis"]}
    assert kpis["runway"]["value"] == "∞"
    assert kpis["runway"]["tone"] == "good"
    # Operating CF positive → net burn reported as zero.
    assert kpis["net_burn"]["value"] == "0.00"
    severities = {a["title"] for a in out["alerts"]}
    assert "Cash generative" in severities


def test_burning_books_report_finite_runway_and_alert():
    # Expense (900k) > income (300k): burning. months_elapsed ≈ 2.99.
    # avg income ≈ 100,334; avg expense ≈ 301,003; operating_cf ≈ -200,669/mo.
    # liquidity = cash 300k + (AR 100k - AP 50k) = 350k.
    # runway = 350k / 200,669 ≈ 1.74 months.
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(
            income={"fytd": "300000.00"},
            expenses={"fytd": "900000.00"},
        ),
        ar_aging=_aging({"0-30": "100000.00"}),
        ap_aging=_aging({"0-30": "50000.00"}),
        as_of=AS_OF,
    )
    assert out["runway_months"] is not None
    assert 1.5 < out["runway_months"] < 2.0
    assert out["zero_crossing_date"] is not None
    titles = {a["title"] for a in out["alerts"]}
    assert "Runway under 3 months" in titles


def test_projection_series_carries_wc_unwind_in_month_one_only():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(
            income={"fytd": "300000.00"},
            expenses={"fytd": "600000.00"},
        ),
        ar_aging=_aging({"0-30": "120000.00"}),
        ap_aging=_aging({"0-30": "20000.00"}),
        as_of=AS_OF,
        horizon_months=3,
    )
    proj = out["projection"]
    assert len(proj) == 3
    # WC unwind (120k - 20k = 100k) only in month 1.
    assert proj[0]["wc_unwind"] == "100000.00"
    assert proj[1]["wc_unwind"] == "0.00"
    assert proj[2]["wc_unwind"] == "0.00"
    # Each month's closing = previous closing + operating_cf (+ wc in m1).
    op = float(proj[0]["operating_cf"])
    assert op < 0  # burning
    m1 = float(proj[0]["closing"])
    m2 = float(proj[1]["closing"])
    assert round(m2 - m1, 2) == round(op, 2)
    # Chart x-axis starts at "Now" and has horizon+1 points.
    cash_chart = next(c for c in out["charts"] if c["key"] == "projected_cash")
    assert cash_chart["x"][0] == "Now"
    assert len(cash_chart["series"][0]["data"]) == 4


def test_payables_exceed_cash_raises_warning():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(cash_and_bank="50000.00"),
        ar_aging=_aging({"0-30": "100000.00"}),
        ap_aging=_aging({"0-30": "200000.00"}),  # AP 200k > cash 50k
        as_of=AS_OF,
    )
    titles = {a["title"] for a in out["alerts"]}
    assert "Payables exceed cash on hand" in titles


def test_at_risk_receivables_flagged_as_collection_risk():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(),
        ar_aging=_aging({"0-30": "100000.00", "90+": "80000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}),
        as_of=AS_OF,
    )
    titles = {a["title"] for a in out["alerts"]}
    assert "Collection risk over 90 days" in titles


def test_empty_ledger_degrades_without_error():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(
            income={"fytd": "0.00"}, expenses={"fytd": "0.00"},
            cash_and_bank="0.00", receivables="0.00", payables="0.00",
        ),
        ar_aging=_aging({}),
        ap_aging=_aging({}),
        as_of=AS_OF,
    )
    # No income or expense → operating_cf 0 → treated as cash-positive (no burn).
    assert out["runway_months"] is None
    kpis = {k["key"]: k for k in out["kpis"]}
    assert kpis["opening_cash"]["value"] == "0.00"
    assert kpis["projected_liquidity"]["value"] == "0.00"
    # Cash is zero → the zero-cash danger alert fires.
    assert any(a["title"] == "Cash balance is zero or negative" for a in out["alerts"])


def test_horizon_is_clamped():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(), ar_aging=_aging({}), ap_aging=_aging({}),
        as_of=AS_OF, horizon_months=999,
    )
    assert out["horizon_months"] == 24
    assert len(out["projection"]) == 24


def test_narration_prompt_is_figure_only_json():
    out = assemble_cash_flow_forecast(
        dashboard=_dashboard(), ar_aging=_aging({"0-30": "250000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}), as_of=AS_OF,
    )
    prompt = build_narration_prompt(out)
    assert "cash-flow snapshot" in prompt
    # The embedded JSON must round-trip (no free text the model could contradict).
    start = prompt.index("{")
    end = prompt.rindex("}") + 1
    snapshot = json.loads(prompt[start:end])
    assert snapshot["headline"] == out["summary"]
    assert "kpis" in snapshot and "alerts" in snapshot


@pytest.mark.asyncio
async def test_narration_disabled_returns_none(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "CASH_FLOW_AI_ENABLED", False, raising=False)
    assert await narrate_cash_flow_forecast({"summary": "x", "kpis": [], "alerts": []}) is None


@pytest.mark.asyncio
async def test_narration_without_api_key_returns_none(monkeypatch):
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "CASH_FLOW_AI_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "", raising=False)
    assert await narrate_cash_flow_forecast({"summary": "x", "kpis": [], "alerts": []}) is None
