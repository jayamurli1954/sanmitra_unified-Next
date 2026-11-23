from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.platform_owner.complimentary import (
    MAX_DAYS,
    MIN_DAYS,
    grant_complimentary_plan,
    list_complimentary_plans,
    revoke_complimentary_plan,
)
from app.core.platform_owner.service import get_platform_owner_dashboard
from app.core.reconciliation.ledger_sync import reconcile_ledger, save_report
from app.db.postgres import get_async_session
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


@router.get("/ledger-reconciliation")
async def ledger_reconciliation(
    days: float = Query(default=7, gt=0, le=366),
    tenant_id: str | None = Query(default=None, max_length=64),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """MongoDB vs PostgreSQL ledger check (report only) - platform-owner only."""
    _require_super_admin(current_user, detail="Only super admins can run ledger reconciliation")
    report = await reconcile_ledger(
        session,
        since=datetime.now(timezone.utc) - timedelta(days=days),
        tenant_id=tenant_id or None,
    )
    try:
        await save_report(report)
    except Exception:
        pass
    report.pop("_id", None)
    return report


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


class ComplimentaryPlanGrant(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    full_name: str | None = Field(default=None, max_length=120)
    organization_name: str | None = Field(default=None, max_length=160)
    app_key: str = Field(default="legalmitra", max_length=32)
    tier: str = Field(default="pro", max_length=16)
    days: int = Field(default=90, ge=MIN_DAYS, le=MAX_DAYS)
    note: str | None = Field(default=None, max_length=300)
    send_email: bool = True


def _actor(current_user: dict) -> str:
    return str(current_user.get("email") or current_user.get("sub") or current_user.get("user_id") or "platform-owner")


@router.get("/complimentary-plans")
async def get_complimentary_plans(current_user: dict = Depends(get_current_user)):
    """List users holding a complimentary (trial) plan - platform-owner only."""
    _require_super_admin(current_user, detail="Only super admins can view complimentary plans")
    return {"items": await list_complimentary_plans()}


@router.post("/complimentary-plans")
async def create_complimentary_plan(
    payload: ComplimentaryPlanGrant,
    current_user: dict = Depends(get_current_user),
):
    """Give someone free access for N days; creates their account if needed - platform-owner only."""
    _require_super_admin(current_user, detail="Only super admins can grant complimentary plans")
    try:
        return await grant_complimentary_plan(
            email=payload.email,
            full_name=payload.full_name,
            organization_name=payload.organization_name,
            app_key=payload.app_key,
            tier=payload.tier,
            days=payload.days,
            note=payload.note,
            granted_by=_actor(current_user),
            send_email=payload.send_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/complimentary-plans/{email}")
async def delete_complimentary_plan(email: str, current_user: dict = Depends(get_current_user)):
    """End a complimentary plan now (user drops to free) - platform-owner only."""
    _require_super_admin(current_user, detail="Only super admins can revoke complimentary plans")
    try:
        return await revoke_complimentary_plan(email=email, revoked_by=_actor(current_user))
    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
