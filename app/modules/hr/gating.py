"""Two-level access gate for the MitraBooks HR add-on.

1. Platform owner provisions it per tenant  -> core_tenants.hr_addon_available
2. Tenant admin turns it on in settings      -> InvoiceSettings.hr_enabled

Both must be true. HR lives inside MitraBooks, so the app context is always
``mitrabooks`` and tenant isolation comes from the same resolver the rest of
MitraBooks uses (tenant_id from JWT, never from the request body).
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant

HR_APP_KEY = "mitrabooks"


def require_hr_context(operation: str = "HR operation") -> Callable:
    async def _dependency(
        current_user: dict = Depends(get_current_user),
        x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
        x_app_key: str | None = Header(default=None, alias="X-App-Key"),
        x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
    ) -> AppTenantContext:
        # Importing here avoids a circular import (business.service imports schemas
        # that may, in future, reference HR helpers).
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
        if not tenant.get("hr_addon_available"):
            raise HTTPException(status_code=403, detail="HR add-on is not provisioned for this tenant")

        settings = await get_invoice_settings(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
        )
        if not settings.get("hr_enabled"):
            raise HTTPException(
                status_code=403,
                detail="HR module is disabled — enable it in MitraBooks settings",
            )

        return context

    return _dependency
