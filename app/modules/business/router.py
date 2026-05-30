from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business.schemas import (
    PartyCreateRequest,
    PartyListResponse,
    PartyResponse,
    PartyUpdateRequest,
    TypedVoucherCreateRequest,
    TypedVoucherListResponse,
    TypedVoucherReversalRequest,
    TypedVoucherResponse,
)
from app.modules.business.service import (
    create_party,
    deactivate_party,
    get_party,
    get_voucher,
    list_parties,
    list_vouchers,
    post_typed_voucher,
    reverse_typed_voucher,
    update_party,
)

router = APIRouter(prefix="/business", tags=["business"])


def _created_by(current_user: dict) -> str:
    return str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")


@router.post("/parties", response_model=PartyResponse)
async def create_business_party(
    payload: PartyCreateRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="party creation",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    return await create_party(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        created_by=_created_by(current_user),
        payload=payload,
    )


@router.get("/parties", response_model=PartyListResponse)
async def list_business_parties(
    party_type: str | None = Query(default=None, pattern="^(customer|vendor|both)$"),
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="party listing",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    return await list_parties(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        party_type=party_type,
        limit=limit,
    )


@router.get("/parties/{party_id}", response_model=PartyResponse)
async def get_business_party(
    party_id: str,
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
        operation="party lookup",
    )
    party = await get_party(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    if party is None:
        raise HTTPException(status_code=404, detail="Business party not found")
    return party


@router.patch("/parties/{party_id}", response_model=PartyResponse)
async def update_business_party(
    party_id: str,
    payload: PartyUpdateRequest,
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
        operation="party update",
    )
    party = await update_party(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
        updated_by=_created_by(current_user),
        payload=payload,
    )
    if party is None:
        raise HTTPException(status_code=404, detail="Business party not found")
    return party


@router.post("/parties/{party_id}/deactivate", response_model=PartyResponse)
async def deactivate_business_party(
    party_id: str,
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
        operation="party deactivation",
    )
    party = await deactivate_party(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
        deactivated_by=_created_by(current_user),
    )
    if party is None:
        raise HTTPException(status_code=404, detail="Business party not found")
    return party


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
        operation="voucher posting",
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
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
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
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        voucher_type=voucher_type,
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
