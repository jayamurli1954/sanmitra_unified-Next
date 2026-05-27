from types import SimpleNamespace

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
    user_id="account-route-user",
)


def _account(**overrides):
    data = {
        "id": 101,
        "code": "1000",
        "name": "Cash",
        "type": "asset",
        "classification": "real",
        "is_cash_bank": True,
        "is_receivable": False,
        "is_payable": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.fixture
def accounting_account_client():
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


def test_create_account_route_uses_trusted_accounting_context(monkeypatch, accounting_account_client):
    captured = {}

    async def fake_create_account(_session, **kwargs):
        captured.update(kwargs)
        return _account(code=kwargs["code"], name=kwargs["name"])

    monkeypatch.setattr(accounting_router, "create_account", fake_create_account)

    response = accounting_account_client.post(
        "/api/v1/accounting/accounts",
        json={
            "code": "1000",
            "name": "Cash",
            "type": "asset",
            "classification": "real",
            "is_cash_bank": True,
            "tenant_id": "tenant-body-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={
            "code": "1000",
            "name": "Cash",
            "account_type": "asset",
            "classification": "real",
            "is_cash_bank": True,
            "is_receivable": False,
            "is_payable": False,
        },
    )


def test_list_accounts_route_uses_trusted_accounting_context(monkeypatch, accounting_account_client):
    captured = {}

    async def fake_list_accounts(_session, **kwargs):
        captured.update(kwargs)
        return [_account()]

    monkeypatch.setattr(accounting_router, "list_accounts", fake_list_accounts)

    response = accounting_account_client.get(
        "/api/v1/accounting/accounts",
        params={"tenant_id": "tenant-query-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()[0]["code"] == "1000"
    _assert_trusted_context(captured)


def test_update_account_route_uses_trusted_accounting_context(monkeypatch, accounting_account_client):
    captured = {}

    async def fake_update_account(_session, **kwargs):
        captured.update(kwargs)
        return _account(code=kwargs["code"], name=kwargs["name"])

    monkeypatch.setattr(accounting_router, "update_account", fake_update_account)

    response = accounting_account_client.patch(
        "/api/v1/accounting/accounts/1000",
        json={"name": "Main Cash", "tenant_id": "tenant-body-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Main Cash"
    _assert_trusted_context(captured, expected_extra={"code": "1000", "name": "Main Cash"})


def test_update_account_route_maps_validation_errors(monkeypatch, accounting_account_client):
    async def fake_update_account(_session, **_kwargs):
        raise AccountingValidationError("Account name must be at least 2 characters")

    monkeypatch.setattr(accounting_router, "update_account", fake_update_account)

    response = accounting_account_client.patch(
        "/api/v1/accounting/accounts/1000",
        json={"name": "Main Cash"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Account name must be at least 2 characters"


def test_update_account_route_maps_not_found_errors(monkeypatch, accounting_account_client):
    async def fake_update_account(_session, **_kwargs):
        raise AccountingNotFoundError("Account not found")

    monkeypatch.setattr(accounting_router, "update_account", fake_update_account)

    response = accounting_account_client.patch(
        "/api/v1/accounting/accounts/4040",
        json={"name": "Missing Account"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"
