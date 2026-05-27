from datetime import date
from decimal import Decimal
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
    user_id="journal-route-user",
)


def _line(**overrides):
    data = {
        "id": 501,
        "account_id": 1001,
        "debit": Decimal("25.00"),
        "credit": Decimal("0.00"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _journal(**overrides):
    data = {
        "id": 77,
        "tenant_id": TRUSTED_CONTEXT.tenant_id,
        "app_key": TRUSTED_CONTEXT.app_key,
        "accounting_entity_id": TRUSTED_CONTEXT.accounting_entity_id,
        "entry_date": date(2026, 5, 27),
        "description": "Journal read test",
        "reference": "JV-77",
        "source_module": "accounting",
        "source_document_type": "manual_journal",
        "source_document_id": "manual-77",
        "reversal_of_journal_id": None,
        "idempotency_key": "idem-77",
        "total_debit": Decimal("25.00"),
        "total_credit": Decimal("25.00"),
        "created_by": TRUSTED_CONTEXT.user_id,
        "lines": [_line(), _line(id=502, account_id=4001, debit=Decimal("0.00"), credit=Decimal("25.00"))],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.fixture
def accounting_journal_client():
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


def test_list_journal_route_uses_trusted_accounting_context(monkeypatch, accounting_journal_client):
    captured = {}

    async def fake_list_journal_entries(_session, **kwargs):
        captured.update(kwargs)
        return [_journal()]

    monkeypatch.setattr(accounting_router, "list_journal_entries", fake_list_journal_entries)

    response = accounting_journal_client.get(
        "/api/v1/accounting/journal",
        params={
            "from_date": "2026-05-01",
            "to_date": "2026-05-27",
            "limit": 25,
            "offset": 5,
            "tenant_id": "tenant-query-spoofed",
        },
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["tenant_id"] == TRUSTED_CONTEXT.tenant_id
    assert payload[0]["lines"][0]["debit"] == "25.00"
    _assert_trusted_context(
        captured,
        expected_extra={
            "from_date": date(2026, 5, 1),
            "to_date": date(2026, 5, 27),
            "limit": 25,
            "offset": 5,
        },
    )


def test_get_journal_route_uses_trusted_accounting_context(monkeypatch, accounting_journal_client):
    captured = {}

    async def fake_get_journal_entry_detail(_session, **kwargs):
        captured.update(kwargs)
        return _journal(id=88)

    monkeypatch.setattr(accounting_router, "get_journal_entry_detail", fake_get_journal_entry_detail)

    response = accounting_journal_client.get(
        "/api/v1/accounting/journal/88",
        params={"tenant_id": "tenant-query-spoofed"},
        headers={"X-Tenant-ID": "tenant-header-spoofed"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 88
    _assert_trusted_context(captured, expected_extra={"journal_id": 88})


def test_list_journal_route_maps_accounting_validation_errors(monkeypatch, accounting_journal_client):
    async def fake_list_journal_entries(_session, **_kwargs):
        raise AccountingValidationError("from_date cannot be greater than to_date")

    monkeypatch.setattr(accounting_router, "list_journal_entries", fake_list_journal_entries)

    response = accounting_journal_client.get(
        "/api/v1/accounting/journal",
        params={"from_date": "2026-05-27", "to_date": "2026-05-01"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "from_date cannot be greater than to_date"


def test_get_journal_route_maps_not_found_errors(monkeypatch, accounting_journal_client):
    async def fake_get_journal_entry_detail(_session, **_kwargs):
        raise AccountingNotFoundError("Journal entry 404 not found")

    monkeypatch.setattr(accounting_router, "get_journal_entry_detail", fake_get_journal_entry_detail)

    response = accounting_journal_client.get("/api/v1/accounting/journal/404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Journal entry 404 not found"
