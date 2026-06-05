from __future__ import annotations

from datetime import date

import pytest

from app.accounting import report_alias_router


def test_member_dues_route_is_registered():
    assert any(route.path == "/reports/member-dues" for route in report_alias_router.router.routes)


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


def _matches(row: dict, query: dict) -> bool:
    for key, expected in query.items():
        if row.get(key) != expected:
            return False
    return True


@pytest.mark.asyncio
async def test_member_dues_report_is_tenant_scoped_and_ignores_reversed_or_paid_bills(monkeypatch):
    collections = {
        "housing_maintenance_bills": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-101",
                    "amount": 5415.20,
                    "paid_amount": 1000,
                    "status": "posted",
                    "created_at": "2026-05-26T10:00:00Z",
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-102",
                    "amount": 4530,
                    "status": "generated",
                    "created_at": "2026-05-26T10:01:00Z",
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-103",
                    "amount": 999,
                    "status": "reversed",
                    "created_at": "2026-05-26T10:02:00Z",
                },
                {
                    "tenant_id": "society-2",
                    "app_key": "gruhamitra",
                    "flat_number": "B-101",
                    "amount": 9999,
                    "status": "generated",
                    "created_at": "2026-05-26T10:03:00Z",
                },
            ]
        ),
        "housing_members": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-101",
                    "name": "Asha Rao",
                    "status": "active",
                    "is_primary": True,
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-102",
                    "name": "Bharat Jain",
                    "status": "active",
                    "is_primary": True,
                },
                {
                    "tenant_id": "society-2",
                    "app_key": "gruhamitra",
                    "flat_number": "B-101",
                    "name": "Other Tenant",
                    "status": "active",
                },
            ]
        ),
        "housing_flats": _Collection([]),
        "mb_transactions": _Collection([]),
    }

    monkeypatch.setattr(report_alias_router, "get_collection", lambda name: collections[name])

    result = await report_alias_router._member_dues_payload(
        tenant_id="society-1",
        app_key="gruhamitra",
        from_date=date(2025, 12, 31),
        to_date=date(2026, 5, 27),
    )

    assert result["total_outstanding"] == 8945.20
    assert [row["flat_number"] for row in result["members"]] == ["A-101", "A-102"]
    assert result["members"][0]["member_name"] == "Asha Rao"
    assert result["members"][0]["outstanding_amount"] == 4415.20
    assert result["members"][1]["outstanding_amount"] == 4530.00


@pytest.mark.asyncio
async def test_member_dues_report_nets_posted_receipts_by_flat_or_member_name(monkeypatch):
    collections = {
        "housing_maintenance_bills": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-101",
                    "amount": 5415.20,
                    "status": "posted",
                    "created_at": "2026-05-26T10:00:00Z",
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-102",
                    "amount": 5704.00,
                    "status": "posted",
                    "created_at": "2026-05-26T10:01:00Z",
                },
            ]
        ),
        "housing_members": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-101",
                    "name": "Vivek Achari",
                    "status": "active",
                    "is_primary": True,
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "flat_number": "A-102",
                    "name": "Aparna Rao",
                    "status": "active",
                    "is_primary": True,
                },
            ]
        ),
        "housing_flats": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "id": "flat-a-101",
                    "flat_number": "A-101",
                },
            ]
        ),
        "mb_transactions": _Collection(
            [
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "voucher_type": "receipt",
                    "status": "posted",
                    "account_code": "12001",
                    "amount": 5415.20,
                    "received_from": "Mr. Vivek Achari",
                    "voucher_date": "2026-05-27",
                },
                {
                    "tenant_id": "society-1",
                    "app_key": "gruhamitra",
                    "voucher_type": "receipt",
                    "status": "draft",
                    "flat_number": "A-102",
                    "account_code": "12001",
                    "amount": 5704.00,
                    "voucher_date": "2026-05-27",
                },
            ]
        ),
    }

    monkeypatch.setattr(report_alias_router, "get_collection", lambda name: collections[name])

    result = await report_alias_router._member_dues_payload(
        tenant_id="society-1",
        app_key="gruhamitra",
        from_date=date(2025, 12, 31),
        to_date=date(2026, 5, 31),
    )

    assert result["total_outstanding"] == 5704.00
    assert [row["flat_number"] for row in result["members"]] == ["A-102"]
    assert result["members"][0]["last_payment_date"] is None
