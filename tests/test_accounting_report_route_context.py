from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import app.accounting.router as accounting_router
from app.accounting.context import AccountingContext
from app.main import app


TRUSTED_CONTEXT = AccountingContext(
    app_key="mitrabooks",
    tenant_id="tenant-trusted",
    accounting_entity_id="entity-trusted",
    user_id="route-user",
)


@pytest.fixture
def accounting_report_client():
    async def fake_session():
        yield object()

    async def fake_context():
        return TRUSTED_CONTEXT

    app.dependency_overrides[accounting_router.get_async_session] = fake_session
    app.dependency_overrides[accounting_router.enforce_accounting_route_tenant] = fake_context
    app.dependency_overrides[accounting_router.get_current_user] = lambda: {
        "sub": TRUSTED_CONTEXT.user_id,
        "tenant_id": TRUSTED_CONTEXT.tenant_id,
        "app_key": TRUSTED_CONTEXT.app_key,
    }

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.pop(accounting_router.get_async_session, None)
    app.dependency_overrides.pop(accounting_router.enforce_accounting_route_tenant, None)
    app.dependency_overrides.pop(accounting_router.get_current_user, None)


def _assert_trusted_context(kwargs: dict, *, expected_extra: dict | None = None) -> None:
    assert kwargs["app_key"] == TRUSTED_CONTEXT.app_key
    assert kwargs["tenant_id"] == TRUSTED_CONTEXT.tenant_id
    assert kwargs["accounting_entity_id"] == TRUSTED_CONTEXT.accounting_entity_id
    if expected_extra:
        for key, value in expected_extra.items():
            assert kwargs[key] == value


def test_trial_balance_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_trial_balance(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00"), Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_trial_balance", fake_get_trial_balance)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/trial-balance",
        params={"as_of": "2026-05-27", "tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()["balanced"] is True
    _assert_trusted_context(captured, expected_extra={"as_of": date(2026, 5, 27)})


def test_balance_sheet_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_balance_sheet(_session, **kwargs):
        captured.update(kwargs)
        return [], [], [], Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_balance_sheet", fake_get_balance_sheet)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/balance-sheet",
        params={"as_of": "2026-05-27", "tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()["balanced"] is True
    _assert_trusted_context(captured, expected_extra={"as_of": date(2026, 5, 27)})


def test_ledger_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_ledger_lines(_session, **kwargs):
        captured.update(kwargs)
        return object(), []

    monkeypatch.setattr(accounting_router, "get_ledger_lines", fake_get_ledger_lines)

    response = accounting_report_client.get(
        "/api/v1/accounting/ledger/42",
        params={"tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json() == []
    _assert_trusted_context(captured, expected_extra={"account_id": 42})


def test_drilldown_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_journal_drilldown(_session, **kwargs):
        captured.update(kwargs)
        return {"level": kwargs["level"], "items": [], "summary": {"voucher_count": 0}}

    monkeypatch.setattr(accounting_router, "get_journal_drilldown", fake_get_journal_drilldown)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/drilldown",
        params={
            "from_date": "2026-05-01",
            "to_date": "2026-05-27",
            "level": "voucher",
            "tenant_id": "tenant-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={
            "from_date": date(2026, 5, 1),
            "to_date": date(2026, 5, 27),
            "level": "voucher",
        },
    )


def test_voucher_detail_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_journal_voucher_detail(_session, **kwargs):
        captured.update(kwargs)
        return {
            "id": kwargs["journal_id"],
            "tenant_id": kwargs["tenant_id"],
            "app_key": kwargs["app_key"],
            "accounting_entity_id": kwargs["accounting_entity_id"],
            "lines": [],
        }

    monkeypatch.setattr(accounting_router, "get_journal_voucher_detail", fake_get_journal_voucher_detail)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/vouchers/77",
        params={"tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == TRUSTED_CONTEXT.tenant_id
    _assert_trusted_context(captured, expected_extra={"journal_id": 77})
