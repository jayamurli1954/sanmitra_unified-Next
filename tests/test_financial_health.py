"""Financial Health assembler — derives KPIs, chart specs and alerts purely from
already-computed ledger figures (the dashboard + AR/AP aging). Pure function, no
DB: it must never invent numbers, only reshape the trusted inputs."""
from datetime import date

from app.modules.business.financial_health import assemble_financial_health

AS_OF = date(2026, 6, 30)


def _dashboard(**overrides) -> dict:
    base = {
        "as_of": AS_OF.isoformat(),
        "financial_year_start": "2026-04-01",
        "income": {"fytd": "1000000.00", "current_month": "200000.00", "ytd_growth": 5.0},
        "expenses": {"fytd": "600000.00"},
        "net_position": {"profit_loss": "400000.00"},
        "cash_and_bank": "300000.00",
        "receivables": "250000.00",
        "payables": "150000.00",
        "gst": {"payable": "50000.00", "status": "Due"},
        "monthly_trend": [
            ["Jan", 1.0, 0.8], ["Feb", 1.2, 0.9], ["Mar", 1.1, 1.0],
            ["Apr", 1.5, 1.1], ["May", 1.3, 1.0], ["Jun", 2.0, 1.2],
        ],
    }
    base.update(overrides)
    return base


def _aging(totals: dict) -> dict:
    order = ["0-30", "31-60", "61-90", "90+"]
    return {"buckets_order": order, "totals": {b: totals.get(b, "0.00") for b in order},
            "grand_total": "0.00", "by_party": []}


def test_kpis_and_charts_shape():
    out = assemble_financial_health(
        dashboard=_dashboard(),
        ar_aging=_aging({"0-30": "200000.00", "31-60": "50000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}),
        as_of=AS_OF,
    )
    kpis = {k["key"]: k for k in out["kpis"]}
    assert kpis["revenue"]["value"] == "1000000.00"
    assert kpis["net_profit"]["value"] == "400000.00"
    assert kpis["net_profit"]["tone"] == "good"
    # Net margin = 400000 / 1000000 = 40%
    assert kpis["net_margin"]["value"] == 40.0
    assert kpis["net_margin"]["tone"] == "good"
    # Working capital = (cash 300k + recv 250k) - (pay 150k + gst 50k) = 350k
    assert kpis["working_capital"]["value"] == "350000.00"
    # Current ratio = 550000 / 200000 = 2.75
    assert kpis["current_ratio"]["value"] == 2.75
    assert kpis["current_ratio"]["tone"] == "good"

    charts = {c["key"]: c for c in out["charts"]}
    assert charts["income_expense"]["type"] == "grouped_bar"
    assert charts["income_expense"]["x"] == ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    assert charts["income_expense"]["series"][0]["data"] == [1.0, 1.2, 1.1, 1.5, 1.3, 2.0]
    # Profit trend = income - expense per month
    assert charts["profit_trend"]["series"][0]["data"] == [0.2, 0.3, 0.1, 0.4, 0.3, 0.8]
    # Receivables aging mirrors the buckets
    assert charts["receivables_aging"]["series"][0]["data"] == [200000.0, 50000.0, 0.0, 0.0]


def test_healthy_books_only_emit_info_alerts():
    out = assemble_financial_health(
        # Ample cash (≈4 months runway) and no GST due → nothing to flag.
        dashboard=_dashboard(cash_and_bank="800000.00", gst={"payable": "0.00", "status": "Nil"}),
        ar_aging=_aging({"0-30": "250000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}),
        as_of=AS_OF,
    )
    severities = {a["severity"] for a in out["alerts"]}
    assert severities == {"info"}
    assert any(a["title"] == "All clear" for a in out["alerts"])


def test_loss_low_cash_and_overdue_raise_alerts():
    out = assemble_financial_health(
        dashboard=_dashboard(
            income={"fytd": "100000.00", "current_month": "0", "ytd_growth": 0.0},
            expenses={"fytd": "300000.00"},
            net_position={"profit_loss": "-200000.00"},
            cash_and_bank="5000.00",
        ),
        ar_aging=_aging({"0-30": "10000.00", "90+": "40000.00"}),
        ap_aging=_aging({"0-30": "150000.00"}),
        as_of=AS_OF,
    )
    titles = {a["title"]: a["severity"] for a in out["alerts"]}
    assert titles["Operating at a loss"] == "danger"
    assert titles["Low cash runway"] == "warning"
    assert titles["Receivables over 90 days"] == "danger"
    # No "All clear" when real alerts exist
    assert "All clear" not in titles


def test_zero_revenue_does_not_divide_by_zero():
    out = assemble_financial_health(
        dashboard=_dashboard(
            income={"fytd": "0.00", "current_month": "0", "ytd_growth": 0.0},
            expenses={"fytd": "0.00"},
            net_position={"profit_loss": "0.00"},
            cash_and_bank="0.00",
            receivables="0.00",
            payables="0.00",
            gst={"payable": "0.00", "status": "Nil"},
        ),
        ar_aging=_aging({}),
        ap_aging=_aging({}),
        as_of=AS_OF,
    )
    kpis = {k["key"]: k for k in out["kpis"]}
    assert kpis["net_margin"]["value"] == 0.0
    assert kpis["current_ratio"]["value"] == "—"
    assert kpis["cash_runway"]["value"] == "—"
    assert kpis["debtor_days"]["value"] == "—"
