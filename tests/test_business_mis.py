from datetime import date

from app.modules.business.mis import assemble_mis_kpis


AS_OF = date(2026, 6, 30)


def _dashboard() -> dict:
    return {
        "as_of": AS_OF.isoformat(),
        "financial_year_start": "2026-04-01",
        "income": {"fytd": "1000000.00", "current_month": "250000.00", "ytd_growth": 8.0},
        "expenses": {"fytd": "600000.00"},
        "net_position": {"profit_loss": "400000.00"},
        "cash_and_bank": "300000.00",
        "receivables": "250000.00",
        "payables": "150000.00",
        "gst": {"payable": "50000.00", "status": "Due"},
        "monthly_trend": [
            ["Jan", 1.0, 0.8],
            ["Feb", 1.2, 0.9],
            ["Mar", 1.1, 1.0],
            ["Apr", 1.5, 1.1],
            ["May", 1.3, 1.0],
            ["Jun", 2.5, 1.2],
        ],
    }


def _aging(*, kind: str) -> dict:
    if kind == "receivable":
        return {
            "kind": kind,
            "as_of": AS_OF.isoformat(),
            "accounting_entity_id": "primary",
            "buckets_order": ["0-30", "31-60", "61-90", "90+"],
            "totals": {"0-30": "175000.00", "31-60": "50000.00", "61-90": "15000.00", "90+": "10000.00"},
            "grand_total": "250000.00",
            "by_party": [
                {
                    "party_id": "cust-b",
                    "party_name": "Beta Stores",
                    "buckets": {"0-30": "50000.00", "31-60": "50000.00", "61-90": "15000.00", "90+": "10000.00"},
                    "total": "125000.00",
                },
                {
                    "party_id": "cust-a",
                    "party_name": "Apex Retail",
                    "buckets": {"0-30": "125000.00", "31-60": "0.00", "61-90": "0.00", "90+": "0.00"},
                    "total": "125000.00",
                },
            ],
        }
    return {
        "kind": kind,
        "as_of": AS_OF.isoformat(),
        "accounting_entity_id": "primary",
        "buckets_order": ["0-30", "31-60", "61-90", "90+"],
        "totals": {"0-30": "120000.00", "31-60": "30000.00", "61-90": "0.00", "90+": "0.00"},
        "grand_total": "150000.00",
        "by_party": [
            {
                "party_id": "vend-a",
                "party_name": "Vendor One",
                "buckets": {"0-30": "120000.00", "31-60": "30000.00", "61-90": "0.00", "90+": "0.00"},
                "total": "150000.00",
            },
        ],
    }


def test_mis_contract_assembles_source_backed_sections():
    out = assemble_mis_kpis(
        dashboard=_dashboard(),
        ar_aging=_aging(kind="receivable"),
        ap_aging=_aging(kind="payable"),
        as_of=AS_OF,
    )

    assert out["as_of"] == "2026-06-30"
    assert out["source"] == {
        "sales_purchase_trend": "posted_ledger",
        "working_capital": "posted_ledger",
        "top_parties": "open_item_aging",
        "overdue_dashboards": "open_item_aging",
        "financial_health": "deterministic_financial_health",
    }
    assert out["monthly_sales_purchase_trend"][-1] == {
        "month": "Jun",
        "sales_lakhs": 2.5,
        "purchases_lakhs": 1.2,
        "sales": "250000.00",
        "purchases": "120000.00",
        "net": "130000.00",
    }
    assert out["working_capital"]["net_working_capital"] == "350000.00"
    assert out["working_capital"]["current_ratio"] == 2.75
    assert out["overdue"]["receivables"]["overdue"] == "75000.00"
    assert out["overdue"]["payables"]["overdue"] == "30000.00"
    assert out["top_customers"][0]["party_name"] == "Beta Stores"
    assert out["top_customers"][0]["overdue"] == "75000.00"
    assert out["top_vendors"][0]["party_name"] == "Vendor One"
    assert out["financial_health"]["summary"]
    assert {kpi["key"] for kpi in out["financial_health"]["kpis"]} >= {"working_capital", "current_ratio"}
