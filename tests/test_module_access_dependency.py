import pytest
from fastapi import HTTPException

import app.core.modules.dependencies as module_deps


@pytest.mark.asyncio
async def test_require_enabled_module_allows_matching_tenant(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "tenant-temple"
        return {
            "tenant_id": tenant_id,
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "accounting", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)

    dependency = module_deps.require_enabled_module("temple")
    result = await dependency(
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-temple",
            "role": "tenant_admin",
            "app_key": "mandirmitra",
        }
    )

    assert result["module_key"] == "temple"
    assert result["tenant"]["tenant_id"] == "tenant-temple"


@pytest.mark.asyncio
async def test_require_enabled_temple_module_allows_mitrabooks_erp_context(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "tenant-temple"
        return {
            "tenant_id": tenant_id,
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "accounting", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)

    dependency = module_deps.require_enabled_module("temple")
    result = await dependency(
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-temple",
            "role": "tenant_admin",
            "app_key": "mitrabooks",
        }
    )

    assert result["module_key"] == "temple"
    assert result["app_key"] == "mitrabooks"


@pytest.mark.asyncio
async def test_require_enabled_module_blocks_disabled_module(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-invest",
            "organization_type": "INVESTMENT",
            "enabled_modules": ["investment", "portfolio", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)

    dependency = module_deps.require_enabled_module("broker_research")
    with pytest.raises(HTTPException) as exc:
        await dependency(
            current_user={
                "sub": "user-1",
                "tenant_id": "tenant-invest",
                "role": "tenant_admin",
                "app_key": "investmitra",
            }
        )

    assert exc.value.status_code == 403
    assert "not enabled" in exc.value.detail


@pytest.mark.asyncio
async def test_require_enabled_module_blocks_wrong_app_key(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-legal",
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "rag", "compliance", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)

    dependency = module_deps.require_enabled_module("legal")
    with pytest.raises(HTTPException) as exc:
        await dependency(
            current_user={
                "sub": "user-1",
                "tenant_id": "tenant-legal",
                "role": "tenant_admin",
                "app_key": "mandirmitra",
            }
        )

    assert exc.value.status_code == 403
    assert "app_key" in exc.value.detail
