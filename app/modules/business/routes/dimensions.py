"""Dimension routes (cost centres, projects, dimension reports).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from datetime import date

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import dimensions as dimensions_module
from app.modules.business import export_governance
from app.modules.business import report_export
from app.modules.business.router import _created_by, router


@router.post("/dimensions")
async def business_create_dimension(
    payload: dict = Body(..., description='{"dimension_type": "cost_centre|project", "code": "...", "name": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Create a cost centre or project (a reporting tag — no ledger impact)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension create",
    )
    try:
        return await dimensions_module.create_dimension(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/dimensions")
async def business_list_dimensions(
    include_inactive: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Dimension masters, split into cost_centres and projects."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension list",
    )
    return await dimensions_module.list_dimensions(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, include_inactive=include_inactive,
    )


@router.patch("/dimensions/{dimension_id}/deactivate")
async def business_deactivate_dimension(
    dimension_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Soft-deactivate a dimension (existing documents keep their tag)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension deactivate",
    )
    try:
        return await dimensions_module.deactivate_dimension(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            dimension_id=dimension_id, updated_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/dimensions/report")
async def business_dimension_report(
    dimension_type: str = Query(..., pattern="^(cost_centre|project)$"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Income/expense/net per cost centre or project over a period (defaults
    to the current financial year), with the untagged bucket and totals."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension report",
    )
    return await dimensions_module.build_dimension_report(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        dimension_type=dimension_type, from_date=from_date, to_date=to_date,
        session=session,
    )


@router.get("/dimensions/report/export")
async def business_dimension_report_export(
    dimension_type: str = Query(..., pattern="^(cost_centre|project)$"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf|json)$"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension report export",
    )
    export_format = export_governance.validate_export_format(format, allowed={"csv", "xlsx", "pdf", "json"})
    export_governance.require_export_permission(current_user, export_type="dimension_report")
    try:
        report = await dimensions_module.build_dimension_report(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            dimension_type=dimension_type, from_date=from_date, to_date=to_date,
            session=session,
        )
        response = report_export.export_report(export_format, **dimensions_module.dimension_report_export_spec(report))
        return await export_governance.govern_export_response(
            response,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            current_user=current_user,
            export_type="dimension_report",
            export_format=export_format,
            report_key=dimension_type,
            filters={
                "dimension_type": dimension_type,
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
            },
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dimensions/branch-report")
async def business_branch_consolidated_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Consolidated branch P&L derived from branch -> cost-centre mappings."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="branch consolidated report",
    )
    return await dimensions_module.build_branch_consolidated_report(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        from_date=from_date, to_date=to_date,
        session=session,
    )
