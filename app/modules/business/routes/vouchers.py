"""Typed voucher routes (create/list/get/review/reverse + bulk import).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import bulk_import
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    TypedVoucherCreateRequest,
    TypedVoucherListResponse,
    TypedVoucherResponse,
    TypedVoucherReversalRequest,
)
from app.modules.business.service import (
    get_voucher,
    list_vouchers,
    post_typed_voucher,
    review_typed_voucher,
    reverse_typed_voucher,
)
from app.modules.business.router import _created_by, router


@router.post("/vouchers", response_model=TypedVoucherResponse)
async def create_typed_voucher(
    payload: TypedVoucherCreateRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="voucher creation",
    )
    try:
        return await post_typed_voucher(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/vouchers", response_model=TypedVoucherListResponse)
async def list_business_vouchers(
    voucher_type: str | None = Query(default=None, pattern="^(payment|receipt|contra|journal)$"),
    status: str | None = Query(default=None, pattern="^(pending_approval|posted|rejected|reversed|posting)$"),
    approval_status: str | None = Query(default=None, pattern="^(auto_posted|not_submitted|pending_approval|approved|rejected)$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_async_session),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="voucher listing",
    )
    return await list_vouchers(
        session=session,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        voucher_type=voucher_type,
        status=status,
        approval_status=approval_status,
        limit=limit,
    )


@router.get("/vouchers/{voucher_id}", response_model=TypedVoucherResponse)
async def get_business_voucher(
    voucher_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="voucher lookup",
    )
    voucher = await get_voucher(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        voucher_id=voucher_id,
    )
    if voucher is None:
        raise HTTPException(status_code=404, detail="Voucher not found")
    voucher["created"] = False
    return voucher


@router.post("/vouchers/{voucher_id}/review", response_model=TypedVoucherResponse)
async def review_business_voucher(
    voucher_id: str,
    payload: ApprovalReviewRequest,
    session: AsyncSession = Depends(get_async_session),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="voucher approval review",
    )
    try:
        return await review_typed_voucher(
            session=session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            voucher_id=voucher_id,
            reviewed_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/vouchers/{voucher_id}/reverse", response_model=TypedVoucherResponse)
async def reverse_business_voucher(
    voucher_id: str,
    payload: TypedVoucherReversalRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="voucher reversal",
    )
    try:
        return await reverse_typed_voucher(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            voucher_id=voucher_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/vouchers/bulk-import/template")
async def business_voucher_bulk_import_template(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Sample CSV template for the bulk voucher import."""
    resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="voucher bulk import template",
    )
    from fastapi.responses import Response
    return Response(
        content=bulk_import.voucher_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="vouchers_bulk_import_template.csv"'},
    )


@router.post("/vouchers/bulk-import/preview")
async def business_voucher_bulk_import_preview(
    payload: dict = Body(..., description='{"csv": "<vouchers CSV>"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Parse + resolve the uploaded voucher CSV without posting."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="voucher bulk import preview",
    )
    try:
        return await bulk_import.build_bulk_import_preview(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/vouchers/bulk-import")
async def business_voucher_bulk_import(
    payload: dict = Body(..., description='{"csv": "<vouchers CSV>"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Post bulk vouchers atomically."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="voucher bulk import posting",
    )
    try:
        return await bulk_import.post_bulk_import_vouchers(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""),
            created_by=_created_by(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
