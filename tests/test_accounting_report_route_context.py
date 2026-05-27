from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import app.accounting.router as accounting_router
from app.accounting.context import AccountingContext
from app.accounting.service import AccountingNotFoundError, AccountingValidationError
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


def test_pnl_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_profit_loss(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_profit_loss", fake_get_profit_loss)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/pnl",
        params={
            "from_date": "2026-05-01",
            "to_date": "2026-05-27",
            "tenant_id": "tenant-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={"from_date": date(2026, 5, 1), "to_date": date(2026, 5, 27)},
    )


def test_income_expenditure_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_profit_loss(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_profit_loss", fake_get_profit_loss)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/income-expenditure",
        params={
            "from_date": "2026-05-01",
            "to_date": "2026-05-27",
            "tenant_id": "tenant-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={"from_date": date(2026, 5, 1), "to_date": date(2026, 5, 27)},
    )


def test_receipts_payments_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_receipts_payments(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_receipts_payments", fake_get_receipts_payments)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/receipts-payments",
        params={
            "from_date": "2026-05-01",
            "to_date": "2026-05-27",
            "tenant_id": "tenant-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={"from_date": date(2026, 5, 1), "to_date": date(2026, 5, 27)},
    )


def test_accounts_receivable_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_accounts_receivable(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_accounts_receivable", fake_get_accounts_receivable)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/accounts-receivable",
        params={"as_of": "2026-05-27", "tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(captured, expected_extra={"as_of": date(2026, 5, 27)})


def test_accounts_payable_route_uses_trusted_accounting_context(monkeypatch, accounting_report_client):
    captured = {}

    async def fake_get_accounts_payable(_session, **kwargs):
        captured.update(kwargs)
        return [], Decimal("0.00")

    monkeypatch.setattr(accounting_router, "get_accounts_payable", fake_get_accounts_payable)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/accounts-payable",
        params={"as_of": "2026-05-27", "tenant_id": "tenant-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(captured, expected_extra={"as_of": date(2026, 5, 27)})


def test_trial_balance_route_maps_accounting_validation_errors(monkeypatch, accounting_report_client):
    async def fake_get_trial_balance(_session, **_kwargs):
        raise AccountingValidationError("Report date is outside the allowed accounting period")

    monkeypatch.setattr(accounting_router, "get_trial_balance", fake_get_trial_balance)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/trial-balance",
        params={"as_of": "2026-05-27"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Report date is outside the allowed accounting period"


def test_balance_sheet_route_maps_accounting_validation_errors(monkeypatch, accounting_report_client):
    async def fake_get_balance_sheet(_session, **_kwargs):
        raise AccountingValidationError("Report date is outside the allowed accounting period")

    monkeypatch.setattr(accounting_router, "get_balance_sheet", fake_get_balance_sheet)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/balance-sheet",
        params={"as_of": "2026-05-27"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Report date is outside the allowed accounting period"


def test_ledger_route_maps_accounting_validation_errors(monkeypatch, accounting_report_client):
    async def fake_get_ledger_lines(_session, **_kwargs):
        raise AccountingValidationError("Ledger report is not available for closed books")

    monkeypatch.setattr(accounting_router, "get_ledger_lines", fake_get_ledger_lines)

    response = accounting_report_client.get("/api/v1/accounting/ledger/42")

    assert response.status_code == 422
    assert response.json()["detail"] == "Ledger report is not available for closed books"


def test_ledger_route_maps_accounting_not_found_errors(monkeypatch, accounting_report_client):
    async def fake_get_ledger_lines(_session, **_kwargs):
        raise AccountingNotFoundError("Account not found")

    monkeypatch.setattr(accounting_router, "get_ledger_lines", fake_get_ledger_lines)

    response = accounting_report_client.get("/api/v1/accounting/ledger/404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"


def test_drilldown_route_maps_accounting_validation_errors(monkeypatch, accounting_report_client):
    async def fake_get_journal_drilldown(_session, **_kwargs):
        raise AccountingValidationError("from_date cannot be greater than to_date")

    monkeypatch.setattr(accounting_router, "get_journal_drilldown", fake_get_journal_drilldown)

    response = accounting_report_client.get(
        "/api/v1/accounting/reports/drilldown",
        params={"from_date": "2026-05-27", "to_date": "2026-05-01"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "from_date cannot be greater than to_date"


def test_voucher_detail_route_maps_accounting_not_found_errors(monkeypatch, accounting_report_client):
    async def fake_get_journal_voucher_detail(_session, **_kwargs):
        raise AccountingNotFoundError("Journal voucher not found")

    monkeypatch.setattr(accounting_router, "get_journal_voucher_detail", fake_get_journal_voucher_detail)

    response = accounting_report_client.get("/api/v1/accounting/reports/vouchers/404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Journal voucher not found"


@pytest.mark.parametrize(
    ("route", "service_name"),
    [
        ("/api/v1/accounting/reports/pnl", "get_profit_loss"),
        ("/api/v1/accounting/reports/income-expenditure", "get_profit_loss"),
        ("/api/v1/accounting/reports/receipts-payments", "get_receipts_payments"),
    ],
)
def test_period_report_routes_map_accounting_validation_errors(
    monkeypatch,
    accounting_report_client,
    route,
    service_name,
):
    async def fake_period_report(_session, **_kwargs):
        raise AccountingValidationError("from_date cannot be greater than to_date")

    monkeypatch.setattr(accounting_router, service_name, fake_period_report)

    response = accounting_report_client.get(
        route,
        params={"from_date": "2026-05-27", "to_date": "2026-05-01"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "from_date cannot be greater than to_date"


@pytest.mark.parametrize(
    ("route", "service_name"),
    [
        ("/api/v1/accounting/reports/accounts-receivable", "get_accounts_receivable"),
        ("/api/v1/accounting/reports/accounts-payable", "get_accounts_payable"),
    ],
)
def test_ar_ap_routes_map_accounting_validation_errors(
    monkeypatch,
    accounting_report_client,
    route,
    service_name,
):
    async def fake_ar_ap_report(_session, **_kwargs):
        raise AccountingValidationError("Report date is outside the allowed accounting period")

    monkeypatch.setattr(accounting_router, service_name, fake_ar_ap_report)

    response = accounting_report_client.get(route, params={"as_of": "2026-05-27"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Report date is outside the allowed accounting period"
