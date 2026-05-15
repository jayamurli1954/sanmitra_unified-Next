import pytest
from fastapi import HTTPException

from app.core.tenants.app_resolvers import resolve_gruha_tenant, resolve_mandir_tenant


def test_mandir_write_blocks_superadmin_default_without_explicit_tenant() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_mandir_tenant(
            current_user={"role": "super_admin", "tenant_id": "default", "app_key": "mandirmitra"},
            x_tenant_id=None,
            x_app_key="mandirmitra",
            operation="donation creation",
        )

    assert exc.value.status_code == 400
    assert "Explicit tenant selection" in exc.value.detail


def test_mandir_write_allows_superadmin_explicit_tenant() -> None:
    context = resolve_mandir_tenant(
        current_user={"role": "super_admin", "tenant_id": "default", "app_key": "mandirmitra"},
        x_tenant_id="demo-mandir-tenant",
        x_app_key="mandirmitra",
        operation="donation creation",
    )

    assert context.app_key == "mandirmitra"
    assert context.tenant_id == "demo-mandir-tenant"


def test_mandir_write_rejects_wrong_app_key() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_mandir_tenant(
            current_user={"role": "tenant_admin", "tenant_id": "demo-mandir-tenant", "app_key": "mandirmitra"},
            x_tenant_id=None,
            x_app_key="gruhamitra",
            operation="seva booking",
        )

    assert exc.value.status_code == 403


def test_gruha_write_rejects_wrong_app_key() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_gruha_tenant(
            current_user={"role": "tenant_admin", "tenant_id": "society-1", "app_key": "gruhamitra"},
            x_tenant_id=None,
            x_app_key="mandirmitra",
            operation="maintenance bill generation",
        )

    assert exc.value.status_code == 403
