"""HTTP routes for the Manufacturing & Cost-Centre Accounting add-on.

Phase 1 surface: entitlement probe, tenant-admin enable toggles, cost-centre
hierarchy tree, cost-centre P&L (with CSV/Excel/PDF export), and cost-centre
budgets + budget-vs-actual. Manufacturing (BOM/work orders) is Phase 2.

Every data endpoint is behind the two-flag gate (require_cost_centre_context),
and the gate's context carries the tenant+app+entity scope used for all reads.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import AppTenantContext, resolve_business_app_tenant
from app.core.tenants.service import get_tenant
from app.db.postgres import get_async_session
from app.modules.business import cost_centre_budgets as budgets_module
from app.modules.business import report_export
from app.modules.manufacturing import service as mfg_service
from app.modules.manufacturing.gating import (
    MFG_MANAGE_ROLES,
    require_cost_centre_context,
    resolve_mfg_access,
)

router = APIRouter(prefix="/business/mfg", tags=["manufacturing-costcentre"])


def _actor(current_user: dict) -> str:
    return str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "user")


def _period(from_date: str | None, to_date: str | None) -> tuple[date, date]:
    from app.accounting.service import _financial_year_start

    to = date.fromisoformat(to_date) if to_date else date.today()
    frm = date.fromisoformat(from_date) if from_date else _financial_year_start(to)
    if frm > to:
        raise HTTPException(status_code=400, detail="from_date must be on or before to_date")
    return frm, to


# --------------------------------------------------------------------------- #
# Entitlement + enable toggles.
# --------------------------------------------------------------------------- #

@router.get("/access")
async def mfg_access(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    """Never-403 probe: which layers are available/enabled/active and what the
    caller may do. The frontend uses it to decide what to render."""
    return await resolve_mfg_access(
        current_user=current_user, x_tenant_id=x_tenant_id,
        x_app_key=x_app_key, x_accounting_entity_id=x_accounting_entity_id,
    )


async def _set_enabled(layer: str, available_flag: str, flag: str, enabled: bool,
                       current_user: dict, x_tenant_id, x_app_key, x_accounting_entity_id) -> dict:
    from app.modules.business.service import set_module_enabled

    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation=f"{layer} enable toggle",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    tenant = await get_tenant(context.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.get(available_flag):
        raise HTTPException(status_code=403, detail=f"{layer} add-on is not provisioned for this tenant")
    if str(current_user.get("role") or "").strip() not in MFG_MANAGE_ROLES:
        raise HTTPException(status_code=403, detail=f"Only an admin can enable {layer}")
    result = await set_module_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        flag=flag, enabled=bool(enabled), updated_by=_actor(current_user),
    )
    return result


@router.put("/cost-centre/enabled")
async def cost_centre_set_enabled(
    enabled: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    return await _set_enabled(
        "Cost-Centre", "cost_centre_addon_available", "cost_centre_enabled", enabled,
        current_user, x_tenant_id, x_app_key, x_accounting_entity_id,
    )


@router.put("/manufacturing/enabled")
async def manufacturing_set_enabled(
    enabled: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    return await _set_enabled(
        "Manufacturing", "manufacturing_addon_available", "manufacturing_enabled", enabled,
        current_user, x_tenant_id, x_app_key, x_accounting_entity_id,
    )


# --------------------------------------------------------------------------- #
# Cost-centre hierarchy + P&L.
# --------------------------------------------------------------------------- #

@router.get("/cost-centre/tree")
async def cost_centre_tree(
    include_inactive: bool = Query(default=False),
    context: AppTenantContext = Depends(require_cost_centre_context("cost-centre tree")),
):
    return await mfg_service.build_cost_centre_tree(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id, include_inactive=include_inactive,
    )


@router.get("/cost-centre/pl")
async def cost_centre_pl(
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    context: AppTenantContext = Depends(require_cost_centre_context("cost-centre P&L")),
):
    frm, to = _period(from_date, to_date)
    return await mfg_service.build_cost_centre_pl(
        session=session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id, from_date=frm, to_date=to,
    )


@router.get("/cost-centre/pl/export")
async def cost_centre_pl_export(
    format: str = Query(default="csv"),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    context: AppTenantContext = Depends(require_cost_centre_context("cost-centre P&L export")),
):
    frm, to = _period(from_date, to_date)
    report = await mfg_service.build_cost_centre_pl(
        session=session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id, from_date=frm, to_date=to,
    )
    spec = mfg_service.cost_centre_pl_export_spec(report)
    try:
        return report_export.export_report(format, **spec, filename_base="cost_centre_pl")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Cost-centre budgets.
# --------------------------------------------------------------------------- #

@router.post("/cost-centre/budgets")
async def create_budget(
    payload: dict = Body(...),
    context: AppTenantContext = Depends(require_cost_centre_context("budget create", roles=MFG_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    from app.accounting.service import AccountingValidationError

    try:
        return await budgets_module.create_budget(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            payload=payload, created_by=_actor(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cost-centre/budgets")
async def list_budgets(
    cost_centre_id: str | None = Query(default=None),
    context: AppTenantContext = Depends(require_cost_centre_context("budget list")),
):
    return await budgets_module.list_budgets(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id, cost_centre_id=cost_centre_id,
    )


@router.put("/cost-centre/budgets/{budget_id}/status")
async def set_budget_status(
    budget_id: str,
    status: str = Body(..., embed=True),
    context: AppTenantContext = Depends(require_cost_centre_context("budget status", roles=MFG_MANAGE_ROLES)),
    current_user: dict = Depends(get_current_user),
):
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError

    try:
        return await budgets_module.set_budget_status(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            budget_id=budget_id, status=status, updated_by=_actor(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cost-centre/budgets/{budget_id}/vs-actual")
async def budget_vs_actual(
    budget_id: str,
    session: AsyncSession = Depends(get_async_session),
    context: AppTenantContext = Depends(require_cost_centre_context("budget vs actual")),
):
    from app.accounting.service import AccountingNotFoundError

    try:
        return await budgets_module.build_budget_vs_actual(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id, budget_id=budget_id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
