"""Access control for the AI Document Capture add-on.

Same two-level gate the Manufacturing/HR add-ons use:

  Capture   platform: core_tenants.capture_addon_available
            tenant:   InvoiceSettings.capture_enabled

Both flags must be true for the add-on to be active. Everything defaults OFF — a
business that hasn't opted in sees no capture endpoints or behaviour. Lives inside
MitraBooks, so the app context is always ``mitrabooks``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant

CAPTURE_APP_KEY = "mitrabooks"

# Manage = upload / draft / reject captured documents.
CAPTURE_MANAGE_ROLES = frozenset({"tenant_admin", "super_admin"})
CAPTURE_READ_ROLES = frozenset(CAPTURE_MANAGE_ROLES)


async def _resolve_flags(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id, operation: str,
) -> tuple[AppTenantContext, dict]:
    from app.modules.business.service import get_invoice_settings

    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key=CAPTURE_APP_KEY,
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
    available = bool(tenant.get("capture_addon_available"))
    enabled = bool(settings.get("capture_enabled"))
    return context, {
        "capture_available": available,
        "capture_enabled": enabled,
        "capture_active": available and enabled,
    }


def require_capture_context(
    operation: str = "capture operation", roles: Iterable[str] | None = CAPTURE_READ_ROLES,
) -> Callable:
    """Dependency: enforce the two-flag gate and, by default, a role."""
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
        if not flags["capture_active"]:
            if not flags["capture_available"]:
                raise HTTPException(status_code=403, detail="AI Document Capture add-on is not provisioned for this tenant")
            raise HTTPException(status_code=403, detail="AI Document Capture is disabled — enable it in MitraBooks settings")
        if allowed is not None:
            role = str(current_user.get("role") or "").strip()
            if role not in allowed:
                raise HTTPException(status_code=403, detail="This action requires a capture role")
        return context

    return _dependency


async def resolve_capture_access(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id,
) -> dict:
    """Never-403 entitlement probe for the frontend."""
    _context, flags = await _resolve_flags(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        x_accounting_entity_id=x_accounting_entity_id, operation="capture access check",
    )
    role = str(current_user.get("role") or "").strip()
    can_manage = role in CAPTURE_MANAGE_ROLES
    return {
        **flags,
        "role": role,
        "can_manage_capture": flags["capture_active"] and can_manage,
        "can_view_capture": flags["capture_active"] and role in CAPTURE_READ_ROLES,
        "can_enable_capture": flags["capture_available"] and can_manage,
    }
