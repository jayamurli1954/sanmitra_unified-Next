import pytest

import app.core.users.router as users_router


@pytest.mark.asyncio
async def test_me_returns_tenant_module_context(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "tenant-1"
        return {
            "tenant_id": "tenant-1",
            "organization_type": "HOUSING",
            "enabled_modules": ["housing", "accounting", "audit"],
            "subscription_plan": "pro",
        }

    monkeypatch.setattr(users_router, "get_tenant", fake_get_tenant)

    result = await users_router.me(
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "role": "tenant_admin",
            "app_key": "gruhamitra",
        }
    )

    assert result["organization_type"] == "HOUSING"
    assert result["enabled_modules"] == ["housing", "accounting", "audit"]
    assert result["subscription_plan"] == "pro"
    assert result["tenant"]["tenant_id"] == "tenant-1"
