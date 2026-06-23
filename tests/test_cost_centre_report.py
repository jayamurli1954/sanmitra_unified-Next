"""Cost-centre P&L presentation layer — name resolution and export shaping.
The underlying ledger aggregation is scoped/tested elsewhere; here we pin the
name-resolution, untagged/total handling, and export spec."""
from decimal import Decimal

import pytest

from app.modules.manufacturing import service as mfg_service


@pytest.mark.asyncio
async def test_build_cost_centre_pl_resolves_names_and_untagged(monkeypatch):
    from datetime import date

    import app.accounting.service as acc_service
    import app.modules.business.dimensions as dims

    async def fake_pl(session, **kw):
        return {"buckets": {
            "cc-a": {"income": Decimal("10000.00"), "expense": Decimal("4000.00")},
            "cc-gone": {"income": Decimal("0.00"), "expense": Decimal("500.00")},
            "__untagged__": {"income": Decimal("2000.00"), "expense": Decimal("1000.00")},
        }}

    async def fake_masters(**kw):
        return {"cost_centres": [{"dimension_id": "cc-a", "code": "A", "name": "Alpha"}]}

    monkeypatch.setattr(acc_service, "get_cost_centre_ledger_pl", fake_pl)
    monkeypatch.setattr(dims, "list_dimensions", fake_masters)

    out = await mfg_service.build_cost_centre_pl(
        session=None, tenant_id="t", app_key="mitrabooks", accounting_entity_id="primary",
        from_date=date(2026, 4, 1), to_date=date(2026, 6, 30),
    )
    rows = {r["code"]: r for r in out["rows"]}
    assert rows["A"]["name"] == "Alpha"
    assert rows["A"]["net"] == "6000.00"
    # A tag whose master is gone still appears (history never vanishes).
    deleted = [r for r in out["rows"] if r["cost_centre_id"] == "cc-gone"][0]
    assert deleted["name"] == "(deleted cost centre)"
    assert deleted["net"] == "-500.00"
    # Sorted by net descending (A first, then the negative one).
    assert out["rows"][0]["code"] == "A"
    assert out["untagged"]["net"] == "1000.00"
    # Totals include tagged + untagged.
    assert out["totals"] == {"income": "12000.00", "expense": "5500.00", "net": "6500.00"}


def test_export_spec_appends_untagged_and_total():
    report = {
        "from_date": "2026-04-01", "to_date": "2026-06-30",
        "rows": [{"cost_centre_id": "cc-a", "code": "A", "name": "Alpha",
                  "income": "10000.00", "expense": "4000.00", "net": "6000.00"}],
        "untagged": {"income": "2000.00", "expense": "1000.00", "net": "1000.00"},
        "totals": {"income": "12000.00", "expense": "5000.00", "net": "7000.00"},
    }
    spec = mfg_service.cost_centre_pl_export_spec(report)
    assert [c["key"] for c in spec["columns"]] == ["code", "name", "income", "expense", "net"]
    # Untagged row appended after data rows; Total in the footer.
    assert spec["rows"][-1]["name"] == "Untagged"
    assert spec["footer"]["name"] == "Total"
    assert spec["footer"]["net"] == "7000.00"
    assert "Cost-Centre P&L" in spec["title"]
