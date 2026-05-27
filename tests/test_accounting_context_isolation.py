import pytest
from fastapi import HTTPException

import app.accounting.router as accounting_router
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


@pytest.mark.asyncio
async def test_accounting_route_dependency_requires_enabled_accounting_module(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "tenant-temple"
        return {
            "tenant_id": tenant_id,
            "status": "active",
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "accounting", "audit"],
        }

    monkeypatch.setattr(accounting_router, "get_tenant", fake_get_tenant)

    context = await accounting_router.enforce_accounting_route_tenant(
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-temple",
            "app_key": "mandirmitra",
        },
        x_tenant_id=None,
        x_app_key="mandirmitra",
        x_accounting_entity_id="primary",
    )

    assert context.tenant_id == "tenant-temple"
    assert context.app_key == "mandirmitra"


@pytest.mark.asyncio
async def test_accounting_route_dependency_blocks_disabled_accounting_module(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-temple",
            "status": "active",
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "audit"],
        }

    monkeypatch.setattr(accounting_router, "get_tenant", fake_get_tenant)

    with pytest.raises(HTTPException) as exc:
        await accounting_router.enforce_accounting_route_tenant(
            current_user={
                "sub": "user-1",
                "tenant_id": "tenant-temple",
                "app_key": "mandirmitra",
            },
            x_tenant_id=None,
            x_app_key="mandirmitra",
            x_accounting_entity_id="primary",
        )

    assert exc.value.status_code == 403
    assert "not enabled" in exc.value.detail


@pytest.mark.asyncio
async def test_accounting_route_dependency_blocks_wrong_organization_type(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-legal",
            "status": "active",
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "accounting", "audit"],
        }

    monkeypatch.setattr(accounting_router, "get_tenant", fake_get_tenant)

    with pytest.raises(HTTPException) as exc:
        await accounting_router.enforce_accounting_route_tenant(
            current_user={
                "sub": "user-1",
                "tenant_id": "tenant-legal",
                "app_key": "mitrabooks",
            },
            x_tenant_id=None,
            x_app_key="mitrabooks",
            x_accounting_entity_id="primary",
        )

    assert exc.value.status_code == 403
    assert "organization_type=LEGAL" in exc.value.detail


@pytest.mark.asyncio
async def test_accounting_route_dependency_blocks_inactive_tenant(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-business",
            "status": "inactive",
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "accounting", "audit"],
        }

    monkeypatch.setattr(accounting_router, "get_tenant", fake_get_tenant)

    with pytest.raises(HTTPException) as exc:
        await accounting_router.enforce_accounting_route_tenant(
            current_user={
                "sub": "user-1",
                "tenant_id": "tenant-business",
                "app_key": "mitrabooks",
            },
            x_tenant_id=None,
            x_app_key="mitrabooks",
            x_accounting_entity_id="primary",
        )

    assert exc.value.status_code == 403
    assert "not active" in exc.value.detail
