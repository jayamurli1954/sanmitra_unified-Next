from types import SimpleNamespace
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.testclient import TestClient

import pytest

import app.core.tenants.router as tenant_router
import app.core.tenants.service as tenant_service
from app.core.auth.dependencies import get_current_user
from app.main import app


class FakeCollection:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    async def create_index(self, *_args, **_kwargs):
        return None

    async def find_one(self, filters, _projection=None):
        tenant_id = filters.get("tenant_id")
        if not tenant_id:
            return None
        doc = self.docs.get(tenant_id)
        if not doc:
            return None
        return dict(doc)

    async def update_one(self, filters, update, upsert=False):
        set_on_insert_keys = set(update.get("$setOnInsert", {}))
        set_keys = set(update.get("$set", {}))
        overlap = set_on_insert_keys & set_keys
        if overlap:
            raise AssertionError(f"Mongo update path conflict: {sorted(overlap)}")

        tenant_id = filters.get("tenant_id")
        doc = self.docs.get(tenant_id)

        if not doc:
            if not upsert:
                return SimpleNamespace(matched_count=0)
            doc = {}
            for key, value in update.get("$setOnInsert", {}).items():
                doc[key] = value
            self.docs[tenant_id] = doc

        for key, value in update.get("$set", {}).items():
            doc[key] = value

        self.docs[tenant_id] = doc
        return SimpleNamespace(matched_count=1)


@pytest.mark.asyncio
async def test_ensure_tenant_exists_creates_active(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    tenant = await tenant_service.ensure_tenant_exists("tenant-a", display_name="Tenant A")

    assert tenant["tenant_id"] == "tenant-a"
    assert tenant["status"] == "active"
    assert tenant["organization_type"] == "BUSINESS"
    assert tenant["enabled_modules"] == ["business", "accounting", "gst", "inventory", "audit"]


@pytest.mark.asyncio
async def test_ensure_tenant_exists_sets_org_type_and_modules(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    tenant = await tenant_service.ensure_tenant_exists(
        "tenant-temple",
        display_name="Temple Tenant",
        organization_type="TEMPLE",
        app_keys=["mandirmitra"],
    )

    assert tenant["organization_type"] == "TEMPLE"
    assert tenant["enabled_modules"] == ["temple", "accounting", "audit"]
    assert tenant["app_keys"] == ["mandirmitra"]


@pytest.mark.asyncio
async def test_ensure_seed_tenant_repairs_mandirmitra_context(monkeypatch):
    fake = FakeCollection()
    fake.docs["seed-tenant-1"] = {
        "tenant_id": "seed-tenant-1",
        "display_name": "SanMitra Seed Tenant",
        "status": "active",
        "organization_type": "BUSINESS",
        "enabled_modules": ["business", "accounting", "gst", "inventory", "audit"],
        "app_keys": [],
    }
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    await tenant_service.ensure_seed_tenant()

    tenant = await tenant_service.get_tenant("seed-tenant-1")
    assert tenant["organization_type"] == "TEMPLE"
    assert tenant["enabled_modules"] == ["temple", "accounting", "audit"]
    assert tenant["app_keys"] == ["mandirmitra"]


@pytest.mark.asyncio
async def test_ensure_tenant_exists_rejects_investment_modules(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    with pytest.raises(ValueError, match="Unknown module"):
        await tenant_service.ensure_tenant_exists(
            "tenant-invest",
            organization_type="INVESTMENT",
            enabled_modules=["investment", "portfolio", "audit"],
            app_keys=["investmitra"],
        )


@pytest.mark.asyncio
async def test_set_tenant_status_and_block_access(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    await tenant_service.ensure_tenant_exists("tenant-inactive")
    updated = await tenant_service.set_tenant_status(
        tenant_id="tenant-inactive",
        status="inactive",
        updated_by="admin-user",
    )

    assert updated["status"] == "inactive"

    with pytest.raises(HTTPException) as exc:
        await tenant_service.ensure_tenant_is_active("tenant-inactive")

    assert "Tenant is inactive" in str(exc.value)


@pytest.mark.asyncio
async def test_ensure_tenant_is_active_bootstraps_missing(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    await tenant_service.ensure_tenant_is_active("tenant-new")

    tenant = await tenant_service.get_tenant("tenant-new")
    assert tenant is not None
    assert tenant["status"] == "active"


@pytest.mark.asyncio
async def test_update_tenant_entitlements_sets_plan_and_modules(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    await tenant_service.ensure_tenant_exists(
        "tenant-temple-entitlements",
        display_name="Temple Tenant",
        organization_type="TEMPLE",
        app_keys=["mandirmitra"],
    )

    updated = await tenant_service.update_tenant_entitlements(
        tenant_id="tenant-temple-entitlements",
        subscription_plan="basic",
        enabled_modules=["temple", "accounting", "audit"],
        updated_by="platform-owner",
    )

    assert updated["subscription_plan"] == "basic"
    assert updated["enabled_modules"] == ["temple", "accounting", "audit"]
    assert updated["updated_by"] == "platform-owner"


@pytest.mark.asyncio
async def test_update_tenant_entitlements_rejects_module_outside_org_type(monkeypatch):
    fake = FakeCollection()
    monkeypatch.setattr(tenant_service, "get_collection", lambda _name: fake)

    await tenant_service.ensure_tenant_exists(
        "tenant-temple-invalid-module",
        display_name="Temple Tenant",
        organization_type="TEMPLE",
        app_keys=["mandirmitra"],
    )

    with pytest.raises(ValueError, match="not available for organization_type=TEMPLE"):
        await tenant_service.update_tenant_entitlements(
            tenant_id="tenant-temple-invalid-module",
            enabled_modules=["temple", "inventory"],
            updated_by="platform-owner",
        )


def test_update_tenant_entitlements_endpoint_rejects_tenant_admin(monkeypatch):
    async def fake_update_tenant_entitlements(**_kwargs):
        raise AssertionError("Tenant admin must not reach entitlement update service")

    monkeypatch.setattr(tenant_router, "update_tenant_entitlements", fake_update_tenant_entitlements)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "tenant@example.com",
        "role": "tenant_admin",
        "tenant_id": "tenant-temple",
        "app_key": "mandirmitra",
    }

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/tenants/tenant-temple/entitlements",
            json={"subscription_plan": "pro"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Only super admins can change tenant entitlements"


def test_update_tenant_entitlements_endpoint_allows_super_admin(monkeypatch):
    async def fake_update_tenant_entitlements(**kwargs):
        assert kwargs["tenant_id"] == "tenant-temple"
        assert kwargs["subscription_plan"] == "pro"
        assert kwargs["enabled_modules"] == ["temple", "accounting", "audit"]
        assert kwargs["updated_by"] == "owner@example.com"
        now = datetime.now(timezone.utc)
        return {
            "tenant_id": "tenant-temple",
            "display_name": "Temple Tenant",
            "status": "active",
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "accounting", "audit"],
            "app_keys": ["mandirmitra"],
            "subscription_plan": "pro",
            "created_at": now,
            "updated_at": now,
            "updated_by": "owner@example.com",
        }

    monkeypatch.setattr(tenant_router, "update_tenant_entitlements", fake_update_tenant_entitlements)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "owner@example.com",
        "role": "super_admin",
        "tenant_id": "platform",
        "app_key": "mitrabooks",
    }

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/tenants/tenant-temple/entitlements",
            json={"subscription_plan": "pro", "enabled_modules": ["temple", "accounting", "audit"]},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["subscription_plan"] == "pro"


def test_update_tenant_status_endpoint_rejects_tenant_admin(monkeypatch):
    async def fake_set_tenant_status(**_kwargs):
        raise AssertionError("Tenant admin must not reach status update service")

    monkeypatch.setattr(tenant_router, "set_tenant_status", fake_set_tenant_status)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "tenant@example.com",
        "role": "tenant_admin",
        "tenant_id": "tenant-temple",
        "app_key": "mandirmitra",
    }

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/tenants/tenant-temple/status",
            json={"status": "inactive"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Only super admins can change tenant status"


def test_update_tenant_status_endpoint_allows_super_admin(monkeypatch):
    async def fake_set_tenant_status(**kwargs):
        assert kwargs["tenant_id"] == "tenant-temple"
        assert kwargs["status"] == "inactive"
        assert kwargs["updated_by"] == "owner@example.com"
        now = datetime.now(timezone.utc)
        return {
            "tenant_id": "tenant-temple",
            "display_name": "Temple Tenant",
            "status": "inactive",
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "accounting", "audit"],
            "app_keys": ["mandirmitra"],
            "subscription_plan": "pro",
            "created_at": now,
            "updated_at": now,
            "updated_by": "owner@example.com",
        }

    monkeypatch.setattr(tenant_router, "set_tenant_status", fake_set_tenant_status)
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "owner@example.com",
        "role": "super_admin",
        "tenant_id": "platform",
        "app_key": "mitrabooks",
    }

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/tenants/tenant-temple/status",
            json={"status": "inactive"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
