from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.core.modules.dependencies as module_deps
from app.core.auth.dependencies import get_current_user
from app.main import app


@pytest.fixture()
def compat_client():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_housing_admin_route_rejects_viewer_role(compat_client, monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": "HOUSING",
            "enabled_modules": ["housing", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    app.dependency_overrides[get_current_user] = lambda: {
        "tenant_id": "tenant-1",
        "role": "viewer",
        "app_key": "gruhamitra",
        "sub": "viewer-1",
    }

    response = compat_client.post(
        "/api/v1/maintenance/regenerate-bill",
        json={"flat_id": "flat-1", "month": 4, "year": 2026},
        headers={"X-App-Key": "gruhamitra"},
    )

    assert response.status_code == 403
    assert response.json().get("detail") == "Insufficient permissions"


def test_housing_admin_route_rejects_disabled_module(compat_client, monkeypatch):
    async def fake_get_tenant_without_housing(tenant_id: str):
        return {"tenant_id": tenant_id, "organization_type": "HOUSING", "enabled_modules": ["audit"]}

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant_without_housing)
    app.dependency_overrides[get_current_user] = lambda: {
        "tenant_id": "tenant-1",
        "role": "tenant_admin",
        "app_key": "gruhamitra",
        "sub": "admin-1",
    }

    response = compat_client.post(
        "/api/v1/maintenance/regenerate-bill",
        json={"flat_id": "flat-1", "month": 4, "year": 2026},
        headers={"X-App-Key": "gruhamitra"},
    )

    assert response.status_code == 403
    assert "not enabled" in str(response.json().get("detail", "")).lower()


def test_mitrabooks_posting_route_rejects_viewer_role(compat_client, monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    app.dependency_overrides[get_current_user] = lambda: {
        "tenant_id": "tenant-1",
        "role": "viewer",
        "app_key": "mitrabooks",
        "sub": "viewer-1",
    }

    response = compat_client.post(
        "/api/v1/transactions/1/approve",
        json={"approved": True},
        headers={"X-App-Key": "mitrabooks"},
    )

    assert response.status_code == 403
    assert response.json().get("detail") == "Insufficient permissions"
