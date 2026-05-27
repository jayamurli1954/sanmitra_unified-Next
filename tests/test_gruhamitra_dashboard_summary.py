from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.api import legacy_alias_router


class _Cursor:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    async def to_list(self, length=None):
        return self.rows[:length] if length else self.rows


class _Collection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []

    def find(self, query):
        return _Cursor([row for row in self.rows if _matches(row, query)])

    async def count_documents(self, query):
        return sum(1 for row in self.rows if _matches(row, query))


class _Rows:
    def __init__(self, rows: list):
        self.rows = rows

    def all(self):
        return self.rows


class _Session:
    def __init__(self):
        self.calls = 0

    async def execute(self, _stmt):
        self.calls += 1
        if self.calls == 2:
            return _Rows(
                [
                    SimpleNamespace(
                        code="1100",
                        debit_total=9945.20,
                        credit_total=1000,
                    ),
                ]
            )
        if self.calls == 3:
            return _Rows(
                [
                    SimpleNamespace(
                        id=40,
                        entry_date=date(2026, 5, 27),
                        reference="RV-000001",
                        description="Maintenance receipt from A-101",
                        created_at="2026-05-27T09:00:00Z",
                        amount=1000,
                    ),
                ]
            )
        return _Rows(
            [
                SimpleNamespace(
                    code="1010",
                    name="HDFC Bank Current Account",
                    is_cash_bank=True,
                    debit_total=300000,
                    credit_total=37256,
                ),
            ]
        )


def _matches(row: dict, query: dict) -> bool:
    for key, expected in query.items():
        value = row.get(key)
        if isinstance(expected, dict):
            if "$nin" in expected and value in expected["$nin"]:
                return False
            continue
        if value != expected:
            return False
    return True


@pytest.mark.asyncio
async def test_gruhamitra_dashboard_summary_uses_bills_and_cash_bank_balance(monkeypatch):
    collections = {
        "housing_maintenance_bills": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "month": 4,
                    "year": 2026,
                    "flat_number": "A-101",
                    "amount": 5415.20,
                    "status": "posted",
                    "is_posted": True,
                    "created_at": "2026-05-26T10:00:00Z",
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "month": 4,
                    "year": 2026,
                    "flat_number": "A-102",
                    "amount": 4530.00,
                    "status": "posted",
                    "is_posted": True,
                    "created_at": "2026-05-26T10:01:00Z",
                },
                {
                    "tenant_id": "society-2",
                    "app_key": "gruhamitra",
                    "month": 4,
                    "year": 2026,
                    "flat_number": "B-101",
                    "amount": 9999,
                    "status": "posted",
                },
            ]
        ),
        "housing_complaints": _Collection(
            [
                {"tenant_id": "society-1", "app_key": "gruhamitra", "status": "open"},
                {"tenant_id": "society-1", "app_key": "gruhamitra", "status": "closed"},
            ]
        ),
    }

    monkeypatch.setattr(legacy_alias_router, "get_collection", lambda name: collections[name])

    result = await legacy_alias_router._gruhamitra_dashboard_summary(
        _Session(),
        tenant_id="society-1",
        app_key="gruhamitra",
    )

    assert result["admin_stats"]["society_balance"] == 262744
    assert result["admin_stats"]["monthly_billing"] == 9945.20
    assert result["admin_stats"]["dues_pending"] == 8945.20
    assert result["admin_stats"]["complaints_open"] == 1
    assert result["admin_stats"]["billing_period"] == {"month": 4, "year": 2026}
    assert result["recent_activities"][0]["icon"] == "receipt"
    assert result["recent_activities"][0]["title"] == "Maintenance receipt RV-000001"
