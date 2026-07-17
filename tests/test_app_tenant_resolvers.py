import pytest
from fastapi import HTTPException

from app.core.tenants.app_resolvers import resolve_business_app_tenant, resolve_gruha_tenant, resolve_mandir_tenant
from app.core.tenants.context import set_tenant_id


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


def test_mandir_resolver_prefers_middleware_temple_context_over_stale_header() -> None:
    set_tenant_id("tenant-from-selected-temple")
    try:
        context = resolve_mandir_tenant(
            current_user={"role": "super_admin", "tenant_id": "default", "app_key": "mandirmitra"},
            x_tenant_id="stale-tenant-from-local-storage",
            x_app_key="mandirmitra",
            operation="devotee mobile search",
        )
    finally:
        set_tenant_id(None)

    assert context.app_key == "mandirmitra"
    assert context.tenant_id == "tenant-from-selected-temple"


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


def test_bookkeeper_can_use_only_assigned_accounting_entity() -> None:
    current_user = {
        "role": "accountant",
        "tenant_id": "practice-1",
        "app_key": "mitrabooks",
        "accounting_entity_ids": ["client-book-a"],
    }

    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=None,
        x_app_key="mitrabooks",
        x_accounting_entity_id="client-book-a",
        expected_app_key="mitrabooks",
        operation="client book report",
    )

    assert context.accounting_entity_id == "client-book-a"

    with pytest.raises(HTTPException) as exc:
        resolve_business_app_tenant(
            current_user=current_user,
            x_tenant_id=None,
            x_app_key="mitrabooks",
            x_accounting_entity_id="client-book-b",
            expected_app_key="mitrabooks",
            operation="client book report",
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Accounting entity access denied"


def test_unassigned_staff_defaults_to_primary_book_only() -> None:
    current_user = {"role": "operator", "tenant_id": "practice-1", "app_key": "mitrabooks"}

    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=None,
        x_app_key="mitrabooks",
        expected_app_key="mitrabooks",
        operation="voucher listing",
    )
    assert context.accounting_entity_id == "primary"

    with pytest.raises(HTTPException) as exc:
        resolve_business_app_tenant(
            current_user=current_user,
            x_tenant_id=None,
            x_app_key="mitrabooks",
            x_accounting_entity_id="unassigned-book",
            expected_app_key="mitrabooks",
            operation="voucher listing",
        )

    assert exc.value.status_code == 403


def test_tenant_admin_can_switch_between_tenant_books() -> None:
    context = resolve_business_app_tenant(
        current_user={"role": "tenant_admin", "tenant_id": "practice-1", "app_key": "mitrabooks"},
        x_tenant_id=None,
        x_app_key="mitrabooks",
        x_accounting_entity_id="client-book-b",
        expected_app_key="mitrabooks",
        operation="client book administration",
    )

    assert context.accounting_entity_id == "client-book-b"
