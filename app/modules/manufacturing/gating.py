"""Access control for the Manufacturing & Cost-Centre Accounting add-on.

Two independent enterprise layers, each with the same two-level gate used by HR:

  Cost-Centre Accounting   platform: core_tenants.cost_centre_addon_available
                           tenant:   InvoiceSettings.cost_centre_enabled
  Manufacturing            platform: core_tenants.manufacturing_addon_available
                           tenant:   InvoiceSettings.manufacturing_enabled

Both flags must be true for a layer to be active. Manufacturing depends on cost
centres (it posts WIP/variance to cost centres), so the manufacturing gate also
requires the cost-centre layer to be active. Everything defaults OFF — a business
that needs neither sees no menu, no tabs, no behaviour change.

Lives inside MitraBooks, so the app context is always ``mitrabooks`` and tenant
isolation comes from the same resolver the rest of MitraBooks uses.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant

MFG_APP_KEY = "mitrabooks"

# Manage = create/post (cost centres, budgets, BOMs, work orders). super_admin is
# included for platform support; tenant_admin so an SMB owner can run it directly.
MFG_MANAGE_ROLES = frozenset({"production_manager", "tenant_admin", "super_admin"})
# Read adds the shop-floor operator (sees work orders / cost reports, posts nothing).
MFG_READ_ROLES = frozenset(MFG_MANAGE_ROLES | {"production_operator"})


async def _resolve_flags(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id, operation: str,
) -> tuple[AppTenantContext, dict]:
    """Resolve tenant context and the four entitlement flags WITHOUT raising on a
    disabled add-on (so the never-403 probe can report state). Still raises for a
    wrong app context / missing tenant — those are genuine auth failures."""
    from app.modules.business.service import get_invoice_settings

    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key=MFG_APP_KEY,
        operation=operation,
        x_accounting_entity_id=x_accounting_entity_id,
    )
    tenant = await get_tenant(context.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    settings = await get_invoice_settings(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
    )

    cc_available = bool(tenant.get("cost_centre_addon_available"))
    cc_enabled = bool(settings.get("cost_centre_enabled"))
    mfg_available = bool(tenant.get("manufacturing_addon_available"))
    mfg_enabled = bool(settings.get("manufacturing_enabled"))

    cost_centre_active = cc_available and cc_enabled
    # Manufacturing is only active when its own gate AND cost centres are active.
    manufacturing_active = mfg_available and mfg_enabled and cost_centre_active
    return context, {
        "cost_centre_available": cc_available,
        "cost_centre_enabled": cc_enabled,
        "cost_centre_active": cost_centre_active,
        "manufacturing_available": mfg_available,
        "manufacturing_enabled": mfg_enabled,
        "manufacturing_active": manufacturing_active,
    }


def _require(
    layer: str, operation: str, roles: Iterable[str] | None,
) -> Callable:
    allowed = frozenset(roles) if roles is not None else None

    async def _dependency(
        current_user: dict = Depends(get_current_user),
        x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
        x_app_key: str | None = Header(default=None, alias="X-App-Key"),
        x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
    ) -> AppTenantContext:
        context, flags = await _resolve_flags(
            current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
            x_accounting_entity_id=x_accounting_entity_id, operation=operation,
        )
        if layer == "cost_centre" and not flags["cost_centre_active"]:
            if not flags["cost_centre_available"]:
                raise HTTPException(status_code=403, detail="Cost-Centre add-on is not provisioned for this tenant")
            raise HTTPException(status_code=403, detail="Cost-Centre module is disabled — enable it in MitraBooks settings")
        if layer == "manufacturing" and not flags["manufacturing_active"]:
            if not flags["manufacturing_available"]:
                raise HTTPException(status_code=403, detail="Manufacturing add-on is not provisioned for this tenant")
            if not flags["cost_centre_active"]:
                raise HTTPException(status_code=403, detail="Manufacturing requires the Cost-Centre module to be enabled first")
            raise HTTPException(status_code=403, detail="Manufacturing module is disabled — enable it in MitraBooks settings")
        if allowed is not None:
            role = str(current_user.get("role") or "").strip()
            if role not in allowed:
                raise HTTPException(status_code=403, detail="This action requires a manufacturing/cost-centre role")
        return context

    return _dependency


def require_cost_centre_context(
    operation: str = "cost-centre operation", roles: Iterable[str] | None = MFG_READ_ROLES,
) -> Callable:
    """Dependency: enforce the cost-centre gate (both flags) and, by default, a role.
    Pass ``roles=MFG_MANAGE_ROLES`` on mutating endpoints."""
    return _require("cost_centre", operation, roles)


def require_manufacturing_context(
    operation: str = "manufacturing operation", roles: Iterable[str] | None = MFG_READ_ROLES,
) -> Callable:
    """Dependency: enforce the manufacturing gate (its flags + cost centres active)."""
    return _require("manufacturing", operation, roles)


async def resolve_mfg_access(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id,
) -> dict:
    """Never-403 entitlement probe for the frontend: reports which layers are
    available/enabled/active and what the caller may do, so the UI shows only what
    this entity has turned on."""
    _context, flags = await _resolve_flags(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        x_accounting_entity_id=x_accounting_entity_id, operation="add-on access check",
    )
    role = str(current_user.get("role") or "").strip()
    can_manage = role in MFG_MANAGE_ROLES
    return {
        **flags,
        "role": role,
        "can_manage_cost_centre": flags["cost_centre_active"] and can_manage,
        "can_view_cost_centre": flags["cost_centre_active"] and role in MFG_READ_ROLES,
        "can_manage_manufacturing": flags["manufacturing_active"] and can_manage,
        "can_view_manufacturing": flags["manufacturing_active"] and role in MFG_READ_ROLES,
        # Provisioned-but-not-enabled: an admin can flip the enable flag.
        "can_enable_cost_centre": flags["cost_centre_available"] and can_manage,
        "can_enable_manufacturing": flags["manufacturing_available"] and can_manage,
    }
