"""HTTP regression: non-super-admin X-Tenant-ID override is 403 on each vertical."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.core.modules.dependencies as module_deps
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_gruha_tenant, resolve_mandir_tenant
from app.main import app


def _user(*, tenant_id: str, app_key: str, role: str = "tenant_admin") -> dict:
    return {
        "sub": "user-b",
        "tenant_id": tenant_id,
        "app_key": app_key,
        "role": role,
    }


@pytest.fixture()
def override_client():
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(
    ("path", "app_key", "organization_type", "enabled_modules"),
    [
        ("/api/v1/legal/cases", "legalmitra", "LEGAL", ["legal", "audit"]),
        (
            "/api/v1/business/ca-clients?active_only=true&limit=10",
            "mitrabooks",
            "BUSINESS",
            ["business", "audit"],
        ),
    ],
)
def test_http_rejects_cross_tenant_header_override(
    override_client,
    monkeypatch,
    path: str,
    app_key: str,
    organization_type: str,
    enabled_modules: list[str],
) -> None:
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "status": "active",
            "organization_type": organization_type,
            "enabled_modules": enabled_modules,
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    app.dependency_overrides[get_current_user] = lambda: _user(
        tenant_id="tenant-b",
        app_key=app_key,
    )

    response = override_client.get(
        path,
        headers={"X-App-Key": app_key, "X-Tenant-ID": "tenant-a"},
    )

    assert response.status_code == 403
    assert response.json().get("detail") == "Tenant override not allowed"


def test_mandir_resolver_rejects_cross_tenant_header_override() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_mandir_tenant(
            current_user=_user(tenant_id="tenant-b", app_key="mandirmitra"),
            x_tenant_id="tenant-a",
            x_app_key="mandirmitra",
            operation="read",
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "Tenant override not allowed"


def test_gruha_resolver_rejects_cross_tenant_header_override() -> None:
    with pytest.raises(HTTPException) as exc:
        resolve_gruha_tenant(
            current_user=_user(tenant_id="tenant-b", app_key="gruhamitra"),
            x_tenant_id="tenant-a",
            x_app_key="gruhamitra",
            operation="read",
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "Tenant override not allowed"
