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
@pytest.mark.asyncio
async def test_me_excludes_hashed_password(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {"tenant_id": "tenant-1"}

    class FakeUsers:
        async def find_one(self, query):
            return {
                "user_id": "user-1",
                "email": "user@example.com",
                "hashed_password": "bcrypt-hash-should-not-leak",
                "role": "operator",
                "tenant_id": "tenant-1",
            }

    monkeypatch.setattr(users_router, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(users_router, "get_collection", lambda _name: FakeUsers())

    result = await users_router.me(
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-1",
            "role": "operator",
            "app_key": "mitrabooks",
        }
    )

    assert "hashed_password" not in result
    assert result["email"] == "user@example.com"

