import pytest
from fastapi import HTTPException

from app.accounting.context import resolve_accounting_context


def test_accounting_context_rejects_shared_default_tenant():
    with pytest.raises(HTTPException) as exc:
        resolve_accounting_context(
            current_user={
                "sub": "user-1",
                "tenant_id": "default",
                "app_key": "gruhamitra",
            },
            x_tenant_id=None,
            x_app_key="gruhamitra",
        )

    assert exc.value.status_code == 403


def test_accounting_context_allows_seed_temple_tenant_for_mandir_local_smoke():
    context = resolve_accounting_context(
        current_user={
            "sub": "seed-user-1",
            "tenant_id": "seed-tenant-1",
            "app_key": "mandirmitra",
        },
        x_tenant_id=None,
        x_app_key="mandirmitra",
        x_accounting_entity_id="primary",
    )

    assert context.app_key == "mandirmitra"
    assert context.tenant_id == "seed-tenant-1"
    assert context.accounting_entity_id == "primary"


def test_accounting_context_keeps_app_tenant_and_entity_boundary():
    context = resolve_accounting_context(
        current_user={
            "sub": "user-1",
            "tenant_id": "gruhamitra-local",
            "app_key": "gruhamitra",
        },
        x_tenant_id=None,
        x_app_key="gruhamitra",
        x_accounting_entity_id="society-books",
    )

    assert context.app_key == "gruhamitra"
    assert context.tenant_id == "gruhamitra-local"
    assert context.accounting_entity_id == "society-books"
    assert context.user_id == "user-1"
