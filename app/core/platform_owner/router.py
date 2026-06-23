from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.platform_owner.service import get_platform_owner_dashboard
from app.core.tenants.service import set_addon_available, set_hr_addon_available

router = APIRouter(prefix="/platform-owner", tags=["platform-owner"])


def _require_super_admin(current_user: dict, *, detail: str) -> None:
    if str(current_user.get("role") or "").strip() != "super_admin":
        raise HTTPException(status_code=403, detail=detail)


@router.get("/dashboard")
async def platform_owner_dashboard(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    _require_super_admin(current_user, detail="Only super admins can view platform owner dashboard")
    return await get_platform_owner_dashboard(limit=limit)


@router.put("/tenants/{tenant_id}/hr-addon")
async def set_tenant_hr_addon(
    tenant_id: str,
    available: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
):
    """Provision (or revoke) the MitraBooks HR add-on for a tenant — platform-owner only."""
    _require_super_admin(current_user, detail="Only super admins can perform platform owner actions")
    updated_by = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "platform-owner")
    try:
        tenant = await set_hr_addon_available(tenant_id=tenant_id, available=available, updated_by=updated_by)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tenant_id": tenant["tenant_id"], "hr_addon_available": tenant["hr_addon_available"]}


_ADDON_FLAGS = {
    "cost-centre": "cost_centre_addon_available",
    "manufacturing": "manufacturing_addon_available",
}


@router.put("/tenants/{tenant_id}/addon/{addon}")
async def set_tenant_addon(
    tenant_id: str,
    addon: str,
    available: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
):
    """Provision (or revoke) an enterprise add-on for a tenant — platform-owner only.
    addon = 'cost-centre' | 'manufacturing'. Manufacturing implies cost centres."""
    _require_super_admin(current_user, detail="Only super admins can perform platform owner actions")
    flag = _ADDON_FLAGS.get(addon)
    if flag is None:
        raise HTTPException(status_code=400, detail="Unknown add-on")
    updated_by = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "platform-owner")
    try:
        tenant = await set_addon_available(tenant_id=tenant_id, flag=flag, available=available, updated_by=updated_by)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "tenant_id": tenant["tenant_id"],
        "cost_centre_addon_available": tenant["cost_centre_addon_available"],
        "manufacturing_addon_available": tenant["manufacturing_addon_available"],
    }
