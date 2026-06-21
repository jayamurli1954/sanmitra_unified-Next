"""Tenant / app-key / module isolation matrix.

These tests assert the platform's access-control invariants end to end at the
dependency and registry layers, so that no app can reach another app's modules
and InvestMitra remains excluded from the unified backend scope.

The cases mirror the isolation matrix tracked for production readiness:

    | Test                                       | Expected |
    | ------------------------------------------ | -------- |
    | MandirMitra user -> housing (GruhaMitra)   | Denied   |
    | GruhaMitra user -> temple (MandirMitra)    | Denied   |
    | LegalMitra user -> accounting              | Denied   |
    | Temple app -> business module              | Denied   |
    | Disabled-but-permitted module              | Denied   |
    | Wrong X-App-Key for module                 | Denied   |
    | Missing tenant context                     | 401      |
    | Unknown tenant                             | 404      |
    | tenant_id sourced only from trusted JWT    | Enforced |
    | InvestMitra app key / routes               | Excluded |

The dependency-layer tests use the same monkeypatch pattern as
``test_module_access_dependency`` so they stay fast and DB-free.
"""

import pytest
from fastapi import HTTPException

import app.core.modules.dependencies as module_deps
from app.core.modules.registry import ModuleAccessError, require_module_access
from app.core.tenants.context import resolve_app_key
from app.config import get_settings


def _patch_tenant(monkeypatch, *, organization_type: str, enabled_modules: list[str], tenant_id: str = "tenant-x"):
    """Monkeypatch the dependency's get_tenant to return a fixed tenant doc."""

    async def fake_get_tenant(requested_tenant_id: str):
        # The dependency must look up exactly the tenant_id from the trusted
        # JWT claims and nothing else.
        assert requested_tenant_id == tenant_id
        return {
            "tenant_id": tenant_id,
            "organization_type": organization_type,
            "enabled_modules": enabled_modules,
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)


async def _call(module_key: str, *, app_key: str, tenant_id: str = "tenant-x", role: str = "tenant_admin"):
    dependency = module_deps.require_enabled_module(module_key)
    return await dependency(
        current_user={
            "sub": "user-1",
            "tenant_id": tenant_id,
            "role": role,
            "app_key": app_key,
        }
    )


# ---------------------------------------------------------------------------
# Cross-app denial: one app must not reach another app's module
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mandirmitra_user_cannot_access_housing_module(monkeypatch):
    """A temple (MandirMitra) tenant must not reach the GruhaMitra housing module."""
    _patch_tenant(monkeypatch, organization_type="TEMPLE", enabled_modules=["temple", "accounting", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("housing", app_key="mandirmitra")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_gruhamitra_user_cannot_access_temple_module(monkeypatch):
    """A housing (GruhaMitra) tenant must not reach the MandirMitra temple module."""
    _patch_tenant(monkeypatch, organization_type="HOUSING", enabled_modules=["housing", "accounting", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("temple", app_key="gruhamitra")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_legalmitra_user_cannot_access_accounting_module(monkeypatch):
    """A LegalMitra tenant must not reach the shared accounting engine."""
    _patch_tenant(monkeypatch, organization_type="LEGAL", enabled_modules=["legal", "rag", "compliance", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("accounting", app_key="legalmitra")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_temple_app_cannot_access_business_module(monkeypatch):
    """The business operations module is reserved for MitraBooks BUSINESS tenants."""
    _patch_tenant(monkeypatch, organization_type="TEMPLE", enabled_modules=["temple", "accounting", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("business", app_key="mandirmitra")

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Module-enablement and app-key gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permitted_module_denied_when_not_enabled(monkeypatch):
    """Org-type and app-key allow it, but it is not in the tenant's enabled_modules."""
    # BUSINESS + mitrabooks may use gst, but this tenant has not enabled it.
    _patch_tenant(monkeypatch, organization_type="BUSINESS", enabled_modules=["business", "accounting", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("gst", app_key="mitrabooks")

    assert exc.value.status_code == 403
    assert "not enabled" in exc.value.detail


@pytest.mark.asyncio
async def test_wrong_app_key_denied_for_otherwise_valid_tenant(monkeypatch):
    """Temple module is enabled and org-type matches, but the app_key is wrong."""
    _patch_tenant(monkeypatch, organization_type="TEMPLE", enabled_modules=["temple", "accounting", "audit"])

    with pytest.raises(HTTPException) as exc:
        await _call("temple", app_key="legalmitra")

    assert exc.value.status_code == 403
    assert "app_key" in exc.value.detail


# ---------------------------------------------------------------------------
# Positive controls: legitimate access must still succeed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mitrabooks_business_tenant_reaches_accounting(monkeypatch):
    _patch_tenant(
        monkeypatch,
        organization_type="BUSINESS",
        enabled_modules=["business", "accounting", "gst", "inventory", "audit"],
    )

    result = await _call("accounting", app_key="mitrabooks")
    assert result["module_key"] == "accounting"
    assert result["app_key"] == "mitrabooks"


# ---------------------------------------------------------------------------
# Tenant context: must come from trusted JWT, never a request body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_tenant_context_returns_401(monkeypatch):
    async def fail_get_tenant(_tenant_id: str):  # pragma: no cover - must not be reached
        raise AssertionError("get_tenant must not be called without tenant context")

    monkeypatch.setattr(module_deps, "get_tenant", fail_get_tenant)

    dependency = module_deps.require_enabled_module("accounting")
    with pytest.raises(HTTPException) as exc:
        await dependency(current_user={"sub": "user-1", "role": "tenant_admin", "app_key": "mitrabooks"})

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unknown_tenant_returns_404(monkeypatch):
    async def missing_tenant(_tenant_id: str):
        return None

    monkeypatch.setattr(module_deps, "get_tenant", missing_tenant)

    with pytest.raises(HTTPException) as exc:
        await _call("accounting", app_key="mitrabooks", tenant_id="ghost-tenant")

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_tenant_id_is_sourced_only_from_trusted_claims(monkeypatch):
    """The dependency must resolve the tenant strictly from the JWT tenant_id.

    A caller cannot smuggle a different tenant in; the only tenant_id the
    dependency ever looks up is the one on the authenticated principal.
    """
    looked_up: list[str] = []

    async def recording_get_tenant(tenant_id: str):
        looked_up.append(tenant_id)
        return {
            "tenant_id": tenant_id,
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "accounting", "audit"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", recording_get_tenant)

    dependency = module_deps.require_enabled_module("accounting")
    # Extra/forged fields on the principal must be ignored for tenant resolution.
    result = await dependency(
        current_user={
            "sub": "user-1",
            "tenant_id": "trusted-tenant",
            "x_tenant_id": "attacker-tenant",
            "body_tenant_id": "attacker-tenant",
            "role": "tenant_admin",
            "app_key": "mitrabooks",
        }
    )

    assert looked_up == ["trusted-tenant"]
    assert result["tenant"]["tenant_id"] == "trusted-tenant"


# ---------------------------------------------------------------------------
# Registry-level matrix (pure function, no monkeypatch)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("module_key", "organization_type", "app_key", "enabled_modules", "should_allow"),
    [
        # Legitimate access per app
        ("temple", "TEMPLE", "mandirmitra", ["temple", "accounting", "audit"], True),
        ("housing", "HOUSING", "gruhamitra", ["housing", "accounting", "audit"], True),
        ("accounting", "BUSINESS", "mitrabooks", ["business", "accounting", "audit"], True),
        ("legal", "LEGAL", "legalmitra", ["legal", "rag", "compliance", "audit"], True),
        # Cross-app denials
        ("housing", "TEMPLE", "mandirmitra", ["housing"], False),
        ("temple", "HOUSING", "gruhamitra", ["temple"], False),
        ("accounting", "LEGAL", "legalmitra", ["accounting"], False),
        ("legal", "TEMPLE", "mandirmitra", ["legal"], False),
        # Right app/org but module not enabled
        ("gst", "BUSINESS", "mitrabooks", ["business", "accounting"], False),
    ],
)
def test_require_module_access_matrix(module_key, organization_type, app_key, enabled_modules, should_allow):
    if should_allow:
        definition = require_module_access(
            module_key=module_key,
            organization_type=organization_type,
            enabled_modules=enabled_modules,
            app_key=app_key,
        )
        assert definition.module_key == module_key
    else:
        with pytest.raises(ModuleAccessError):
            require_module_access(
                module_key=module_key,
                organization_type=organization_type,
                enabled_modules=enabled_modules,
                app_key=app_key,
            )


# ---------------------------------------------------------------------------
# InvestMitra is excluded from the unified backend scope (guards PR: disable)
# ---------------------------------------------------------------------------


def test_investmitra_app_key_not_in_allowed_keys():
    assert "investmitra" not in get_settings().ALLOWED_APP_KEYS


def test_investmitra_app_key_resolves_to_default():
    """An incoming X-App-Key of investmitra is coerced to the default app key."""
    settings = get_settings()
    assert resolve_app_key("investmitra") == settings.DEFAULT_APP_KEY
    assert resolve_app_key("investmitra") != "investmitra"


def test_investment_routes_are_not_mounted():
    """The investment router must not be mounted under the unified API."""
    from app.api.v1.router import api_router

    investment_paths = [route.path for route in api_router.routes if "/investment" in getattr(route, "path", "")]
    assert investment_paths == []


@pytest.mark.asyncio
async def test_investment_module_unreachable_with_runtime_app_key(monkeypatch):
    """Even a tenant flagged INVESTMENT cannot reach investment modules, because no
    request can carry the investmitra app key once it is excluded from scope."""
    _patch_tenant(monkeypatch, organization_type="INVESTMENT", enabled_modules=["investment", "portfolio", "audit"])

    # A real request's app key resolves to the default (never investmitra), so the
    # investment module's app-key gate rejects it.
    runtime_app_key = resolve_app_key("investmitra")
    with pytest.raises(HTTPException) as exc:
        await _call("investment", app_key=runtime_app_key)

    assert exc.value.status_code == 403
