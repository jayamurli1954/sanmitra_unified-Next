"""Payment allocation routes (open-item AR/AP).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from datetime import date

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.db.postgres import get_async_session
from app.modules.business import allocation_service
from app.modules.business.router import _alloc_context, _created_by, router
from app.modules.business.schemas import (
    AgingResponse,
    AllocationCreateRequest,
    AllocationCreateResponse,
    AllocationRecord,
    FifoSuggestionResponse,
    OpenItemListResponse,
    ReconciliationResponse,
    UnallocatedPaymentListResponse,
)


@router.get("/allocations/open-items", response_model=OpenItemListResponse)
async def list_open_items(
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    party_id: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    include_settled: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "open items")
    try:
        return await allocation_service.list_open_items(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind,
            party_id=party_id, as_of=as_of, include_settled=include_settled,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allocations/unallocated-payments", response_model=UnallocatedPaymentListResponse)
async def list_unallocated_payments(
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    party_id: str | None = Query(default=None),
    include_settled: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "unallocated payments")
    try:
        return await allocation_service.list_unallocated_payments(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind,
            party_id=party_id, include_settled=include_settled,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allocations/fifo-suggestion", response_model=FifoSuggestionResponse)
async def fifo_suggestion(
    payment_id: str = Query(..., min_length=1),
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "fifo suggestion")
    try:
        return await allocation_service.fifo_suggestion(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind,
            payment_id=payment_id, as_of=as_of,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allocations/reconciliation", response_model=ReconciliationResponse)
async def allocation_reconciliation(
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    party_id: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "allocation reconciliation")
    try:
        return await allocation_service.reconciliation(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind,
            party_id=party_id, as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allocations/aging", response_model=AgingResponse)
async def allocation_aging(
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    party_id: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "aging report")
    try:
        return await allocation_service.ar_ap_aging(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind,
            party_id=party_id, as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/allocations", response_model=AllocationCreateResponse)
async def create_allocation(
    payload: AllocationCreateRequest,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "create allocation")
    try:
        return await allocation_service.allocate_payment(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, created_by=_created_by(current_user),
            kind=payload.kind, payment_id=payload.payment_id,
            allocations=[a.model_dump() for a in payload.allocations],
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/allocations/{allocation_id}/reverse", response_model=AllocationRecord)
async def reverse_allocation(
    allocation_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "reverse allocation")
    try:
        return await allocation_service.reverse_allocation(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, allocation_id=allocation_id,
            reversed_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
