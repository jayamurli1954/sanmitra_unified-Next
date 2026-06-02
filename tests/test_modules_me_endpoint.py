import pytest
from fastapi import HTTPException

import app.core.modules.router as modules_router


@pytest.mark.asyncio
async def test_get_my_modules_returns_enabled_and_available_modules(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "tenant-invest"
        return {
            "tenant_id": tenant_id,
            "organization_type": "INVESTMENT",
            "enabled_modules": ["investment", "portfolio", "audit"],
            "subscription_plan": "pro",
        }

    monkeypatch.setattr(modules_router, "get_tenant", fake_get_tenant)

    result = await modules_router.get_my_modules(
        include_available=True,
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-invest",
            "role": "tenant_admin",
            "app_key": "investmitra",
        },
    )

    enabled_keys = {item["module_key"] for item in result["enabled_modules"]}
    available_keys = {item["module_key"] for item in result["available_modules"]}

    assert result["organization_type"] == "INVESTMENT"
    assert result["subscription_plan"] == "pro"
    assert {"investment", "portfolio", "audit"}.issubset(enabled_keys)
    assert "broker_research" in available_keys
    assert "investment_research" in available_keys
    assert all(item["frontend_path"] for item in result["enabled_modules"])
    assert result["navigation"][0]["display_name"] == "Portfolio"
    assert result["role"] == "tenant_admin"
    assert result["is_platform_owner"] is False


@pytest.mark.asyncio
async def test_get_my_modules_can_hide_available_modules(monkeypatch):
    async def fake_get_tenant(_tenant_id: str):
        return {
            "tenant_id": "tenant-legal",
            "organization_type": "LEGAL",
            "enabled_modules": ["legal", "rag", "compliance", "audit"],
            "subscription_plan": "free",
        }

    monkeypatch.setattr(modules_router, "get_tenant", fake_get_tenant)

    result = await modules_router.get_my_modules(
        include_available=False,
        current_user={
            "sub": "user-1",
            "tenant_id": "tenant-legal",
            "role": "tenant_admin",
            "app_key": "legalmitra",
        },
    )

    assert result["available_modules"] == []
    assert {item["module_key"] for item in result["enabled_modules"]} == {
        "audit",
        "compliance",
        "legal",
        "rag",
    }


@pytest.mark.parametrize(
    ("organization_type", "app_key", "enabled_modules", "expected_nav_groups", "expected_enabled"),
    [
        (
            "HOUSING",
            "gruhamitra",
            ["housing", "accounting", "audit"],
            ["Operations", "Finance", "Administration"],
            {"housing", "accounting", "audit"},
        ),
        (
            "TEMPLE",
            "mandirmitra",
            ["temple", "accounting", "audit"],
            ["Operations", "Finance", "Administration"],
            {"temple", "accounting", "audit"},
        ),
        (
            "BUSINESS",
            "mitrabooks",
            ["business", "accounting", "gst", "inventory", "audit"],
            ["Operations", "Finance", "Compliance", "Administration"],
            {"business", "accounting", "gst", "inventory", "audit"},
        ),
        (
            "LEGAL",
            "legalmitra",
            ["legal", "rag", "compliance", "audit"],
            ["Compliance", "Legal", "Administration"],
            {"legal", "rag", "compliance", "audit"},
        ),
        (
            "INVESTMENT",
            "investmitra",
            ["investment", "portfolio", "audit"],
            ["Portfolio", "Administration"],
            {"investment", "portfolio", "audit"},
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_my_modules_contract_by_organization_type(
    monkeypatch,
    organization_type,
    app_key,
    enabled_modules,
    expected_nav_groups,
    expected_enabled,
):
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": organization_type,
            "enabled_modules": enabled_modules,
            "subscription_plan": "pro",
        }

    monkeypatch.setattr(modules_router, "get_tenant", fake_get_tenant)

    result = await modules_router.get_my_modules(
        include_available=True,
        current_user={
            "sub": "user-1",
            "tenant_id": f"tenant-{organization_type.lower()}",
            "role": "tenant_admin",
            "app_key": app_key,
        },
    )

    assert {item["module_key"] for item in result["enabled_modules"]} == expected_enabled
    assert [group["display_name"] for group in result["navigation"]] == expected_nav_groups
    for group in result["navigation"]:
        assert group["group_key"]
        assert group["items"]
        assert all(item["enabled"] is True for item in group["items"])
        assert all(item["frontend_path"] for item in group["items"])
        assert all(item["api_prefix"] for item in group["items"])


@pytest.mark.asyncio
async def test_get_my_modules_requires_tenant_context():
    with pytest.raises(HTTPException) as exc:
        await modules_router.get_my_modules(
            include_available=True,
            current_user={"sub": "user-1", "role": "tenant_admin", "app_key": "mitrabooks"},
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_my_modules_marks_platform_owner_context(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == "platform"
        return {
            "tenant_id": tenant_id,
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "accounting", "audit"],
            "subscription_plan": "enterprise",
        }

    monkeypatch.setattr(modules_router, "get_tenant", fake_get_tenant)

    result = await modules_router.get_my_modules(
        include_available=True,
        current_user={
            "sub": "platform-owner-1",
            "tenant_id": "platform",
            "role": "super_admin",
            "app_key": "mitrabooks",
        },
    )

    assert result["tenant_id"] == "platform"
    assert result["role"] == "super_admin"
    assert result["is_platform_owner"] is True
