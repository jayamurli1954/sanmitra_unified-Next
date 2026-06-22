"""Access control for the MitraBooks HR add-on.

Three layers, all enforced here:
1. **Tenant entitlement** — platform owner provisions (core_tenants.hr_addon_available)
   AND tenant admin enables (InvoiceSettings.hr_enabled). Both must be true.
2. **Per-user role** — within an entitled tenant, the caller must hold an HR role.
   ``hr_manager``/``super_admin`` manage; ``payroll_auditor`` is read-only. Plain
   ``tenant_admin`` is intentionally NOT granted HR access by default — it must be
   given an HR role (sensitive comp data).
3. (Frontend visibility consumes ``resolve_hr_access`` — a never-403 probe.)

HR lives inside MitraBooks, so the app context is always ``mitrabooks`` and tenant
isolation comes from the same resolver the rest of MitraBooks uses.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant

HR_APP_KEY = "mitrabooks"

# Role sets. super_admin (platform owner) is included for support/operations.
HR_MANAGE_ROLES = frozenset({"hr_manager", "super_admin"})
HR_READ_ROLES = frozenset({"hr_manager", "payroll_auditor", "super_admin"})
HR_SELF_ROLE = "employee_self"


async def _resolve_flags(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id, operation: str
) -> tuple[AppTenantContext, bool, bool]:
    """Resolve tenant context and the two entitlement flags WITHOUT raising on
    a disabled add-on (so the probe can report state). Still raises for wrong
    app context / missing tenant — those are genuine auth failures."""
    from app.modules.business.service import get_invoice_settings

    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key=HR_APP_KEY,
        operation=operation,
        x_accounting_entity_id=x_accounting_entity_id,
    )
    tenant = await get_tenant(context.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    available = bool(tenant.get("hr_addon_available"))

    settings = await get_invoice_settings(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
    )
    enabled = bool(settings.get("hr_enabled"))
    return context, available, enabled


def require_hr_context(operation: str = "HR operation", roles: Iterable[str] | None = HR_READ_ROLES) -> Callable:
    """Dependency: enforce entitlement (both flags) and, by default, an HR role.

    Pass ``roles=HR_MANAGE_ROLES`` on mutating endpoints. Pass ``roles=None`` to
    skip the role check (entitlement only) — rarely needed.
    """
    allowed = frozenset(roles) if roles is not None else None

    async def _dependency(
        current_user: dict = Depends(get_current_user),
        x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
        x_app_key: str | None = Header(default=None, alias="X-App-Key"),
        x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
    ) -> AppTenantContext:
        context, available, enabled = await _resolve_flags(
            current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
            x_accounting_entity_id=x_accounting_entity_id, operation=operation,
        )
        if not available:
            raise HTTPException(status_code=403, detail="HR add-on is not provisioned for this tenant")
        if not enabled:
            raise HTTPException(status_code=403, detail="HR module is disabled — enable it in MitraBooks settings")
        if allowed is not None:
            role = str(current_user.get("role") or "").strip()
            if role not in allowed:
                raise HTTPException(status_code=403, detail="This action requires an HR role")
        return context

    return _dependency


async def resolve_hr_access(
    *, current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id
) -> dict:
    """Never-403 entitlement probe for the frontend: reports whether HR is
    available/enabled for the tenant and what the caller may do."""
    context, available, enabled = await _resolve_flags(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        x_accounting_entity_id=x_accounting_entity_id, operation="hr access check",
    )
    role = str(current_user.get("role") or "").strip()
    entitled = available and enabled
    return {
        "available": available,
        "enabled": enabled,
        "entitled": entitled,
        "role": role,
        "can_manage": entitled and role in HR_MANAGE_ROLES,
        "can_view": entitled and role in HR_READ_ROLES,
        "is_self": role == HR_SELF_ROLE,
    }
