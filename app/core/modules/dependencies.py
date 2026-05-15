from collections.abc import Callable

from fastapi import Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.modules.registry import ModuleAccessError, require_module_access
from app.core.tenants.service import get_tenant


def require_enabled_module(module_key: str) -> Callable:
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        tenant_id = str(current_user.get("tenant_id") or "").strip()
        app_key = str(current_user.get("app_key") or "").strip()
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context missing")

        tenant = await get_tenant(tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")

        try:
            require_module_access(
                module_key=module_key,
                organization_type=tenant.get("organization_type"),
                enabled_modules=tenant.get("enabled_modules") or [],
                app_key=app_key,
            )
        except ModuleAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        return {
            "tenant": tenant,
            "user": current_user,
            "module_key": module_key,
            "app_key": app_key,
        }

    return dependency
