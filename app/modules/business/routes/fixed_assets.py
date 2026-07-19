"""Fixed-asset and depreciation routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
import re

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import fixed_assets
from app.modules.business.router import _created_by, router


@router.post("/fixed-assets")
async def business_create_fixed_asset(
    payload: dict = Body(...),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Register a fixed asset (metadata only — the purchase posts via the
    normal bill/voucher to its 16xxx account)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="fixed asset create",
    )
    try:
        return await fixed_assets.create_fixed_asset(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/fixed-assets")
async def business_list_fixed_assets(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Fixed-asset register with accumulated depreciation and book value."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="fixed asset list",
    )
    return await fixed_assets.list_fixed_assets(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )


@router.post("/fixed-assets/{asset_id}/dispose")
async def business_dispose_fixed_asset(
    asset_id: str,
    payload: dict = Body(...),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Dispose an active fixed asset through a balanced journal and mark the
    register row disposed. Admin only; posted journals stay immutable."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="fixed asset disposal",
    )
    try:
        return await fixed_assets.dispose_fixed_asset(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, asset_id=asset_id,
            payload=payload, created_by=_created_by(current_user),
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/depreciation/preview")
async def business_depreciation_preview(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Per-asset depreciation schedule for the FY (SLM/WDV, day-prorated)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="depreciation preview",
    )
    return await fixed_assets.build_depreciation_preview(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )


@router.post("/depreciation/run")
async def business_depreciation_run(
    payload: dict = Body(..., description='{"financial_year": "YYYY-YY"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the FY depreciation journal (admin only): Dr Depreciation Expense,
    Cr Accumulated Depreciation. Idempotent per financial year."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="depreciation run",
    )
    financial_year = str(payload.get("financial_year") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", financial_year):
        raise HTTPException(status_code=422, detail="financial_year must be 'YYYY-YY' (e.g. 2026-27)")
    try:
        return await fixed_assets.post_depreciation_run(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, financial_year=financial_year,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
