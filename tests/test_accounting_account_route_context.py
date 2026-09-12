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


def test_legacy_coa_preview_route_uses_trusted_accounting_context(monkeypatch, accounting_account_client):
    captured = {}

    async def fake_preview(_session, **kwargs):
        captured.update(kwargs)
        return {
            "source_system": kwargs["source_system"],
            "rows": [],
            "canonical_accounts": [],
            "row_count": 0,
            "suggested_count": 0,
            "unmatched_count": 0,
            "already_mapped_count": 0,
            "can_confirm_suggested": False,
        }

    monkeypatch.setattr(accounting_router, "preview_legacy_coa_csv", fake_preview)

    response = accounting_account_client.post(
        "/api/v1/accounting/coa/legacy-import/preview",
        json={
            "csv": "source_account_code,source_account_name\n1001,Cash\n",
            "source_system": "tally",
            "tenant_id": "tenant-body-spoofed",
        },
    )

    assert response.status_code == 200
    _assert_trusted_context(captured, expected_extra={"source_system": "tally"})
    assert "1001" in captured["csv_text"]


def test_legacy_coa_confirm_route_uses_trusted_context_and_role(monkeypatch, accounting_account_client):
    captured = {}

    async def fake_confirm(_session, **kwargs):
        captured.update(kwargs)
        return {
            "source_system": kwargs["source_system"],
            "confirmed_count": 1,
            "created_account_count": 0,
            "mapped_existing_count": 1,
            "decisions": [],
        }

    monkeypatch.setattr(accounting_router, "confirm_legacy_coa_decisions", fake_confirm)
    accounting_account_client.app.dependency_overrides[accounting_router.get_current_user] = lambda: {
        "sub": TRUSTED_CONTEXT.user_id,
        "tenant_id": TRUSTED_CONTEXT.tenant_id,
        "app_key": TRUSTED_CONTEXT.app_key,
        "role": "tenant_admin",
    }

    response = accounting_account_client.post(
        "/api/v1/accounting/coa/legacy-import/confirm",
        json={
            "source_system": "tally",
            "decisions": [
                {
                    "source_account_code": "CASH-01",
                    "source_account_name": "Cash in Hand",
                    "action": "map_existing",
                    "canonical_account_id": 101,
                }
            ],
            "tenant_id": "tenant-body-spoofed",
        },
    )

    assert response.status_code == 200
    _assert_trusted_context(
        captured,
        expected_extra={"source_system": "tally", "decided_by": TRUSTED_CONTEXT.user_id},
    )
    assert captured["decisions"][0].source_account_code == "CASH-01"

