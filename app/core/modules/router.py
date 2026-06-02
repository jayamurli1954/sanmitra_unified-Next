from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.registry import build_navigation_groups, get_module_context_for_tenant
from app.core.tenants.service import get_tenant

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("/me")
async def get_my_modules(
    include_available: bool = Query(default=True),
    current_user: dict = Depends(get_current_user),
):
    tenant_id = str(current_user.get("tenant_id") or "").strip()
    app_key = str(current_user.get("app_key") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant context missing")

    tenant = await get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    module_context = get_module_context_for_tenant(
        organization_type=tenant.get("organization_type"),
        enabled_modules=tenant.get("enabled_modules") or [],
        app_key=app_key,
        include_available=include_available,
    )
    role = str(current_user.get("role") or "").strip()
    is_platform_owner = role == "super_admin" or tenant_id == "platform"

    return {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "role": role,
        "is_platform_owner": is_platform_owner,
        "organization_type": module_context["organization_type"],
        "subscription_plan": tenant.get("subscription_plan", "free"),
        "enabled_modules": module_context["enabled_modules"],
        "available_modules": module_context["available_modules"],
        "navigation": build_navigation_groups(module_context["enabled_modules"]),
    }
