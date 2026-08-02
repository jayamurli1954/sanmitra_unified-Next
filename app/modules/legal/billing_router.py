"""HTTP routes for LegalMitra Stage 6 — practice fees and time entries."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.postgres import get_async_session
from app.modules.legal import billing_service
from app.modules.legal.billing_schemas import (
    FeeCollectionCreateRequest,
    FeeCollectionListResponse,
    FeeCollectionResponse,
    FeeGlMapResponse,
    FeeGlMapUpsertRequest,
    FeeInvoiceCreateRequest,
    FeeInvoiceListResponse,
    FeeInvoiceResponse,
    FeeInvoiceUpdateRequest,
    FeeInvoiceVoidRequest,
    FeeSummaryResponse,
    TimeEntryCreateRequest,
    TimeEntryListResponse,
    TimeEntryResponse,
)
from app.modules.legal.practice_service import PracticeNotFoundError

DEFAULT_APP_KEY = "legalmitra"

billing_router = APIRouter(tags=["legal-billing"])


def _resolve_legal_app_key(x_app_key: str | None) -> str:
    return resolve_app_key((x_app_key or DEFAULT_APP_KEY).strip())


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("sub") or "system")


def _http_for_billing_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (billing_service.BillingNotFoundError, PracticeNotFoundError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, billing_service.BillingValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, billing_service.BillingConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, billing_service.BillingDisabledError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Billing operation failed")


@billing_router.get("/practice/fees/summary", response_model=FeeSummaryResponse)
async def fee_summary(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.get_fee_summary(
            tenant_id=tenant_id, app_key=app_key
        )
    except billing_service.BillingDisabledError as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.post("/practice/fees/invoices", response_model=FeeInvoiceResponse)
async def create_invoice(
    payload: FeeInvoiceCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.create_fee_invoice(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            payload=payload,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingValidationError,
        billing_service.BillingConflictError,
        PracticeNotFoundError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.get("/practice/fees/invoices", response_model=FeeInvoiceListResponse)
async def list_invoices(
    matter_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.list_fee_invoices(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            status=status,
            limit=limit,
        )
    except billing_service.BillingDisabledError as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.get(
    "/practice/fees/invoices/{invoice_id}", response_model=FeeInvoiceResponse
)
async def get_invoice(
    invoice_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.get_fee_invoice(
            tenant_id=tenant_id, app_key=app_key, invoice_id=invoice_id
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.patch(
    "/practice/fees/invoices/{invoice_id}", response_model=FeeInvoiceResponse
)
async def update_invoice(
    invoice_id: str,
    payload: FeeInvoiceUpdateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.update_fee_invoice(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            invoice_id=invoice_id,
            payload=payload,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
        billing_service.BillingValidationError,
        billing_service.BillingConflictError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.post(
    "/practice/fees/invoices/{invoice_id}/issue", response_model=FeeInvoiceResponse
)
async def issue_invoice(
    invoice_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.issue_fee_invoice(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            invoice_id=invoice_id,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
        billing_service.BillingConflictError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.post(
    "/practice/fees/invoices/{invoice_id}/void", response_model=FeeInvoiceResponse
)
async def void_invoice(
    invoice_id: str,
    payload: FeeInvoiceVoidRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.void_fee_invoice(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            invoice_id=invoice_id,
            payload=payload,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
        billing_service.BillingValidationError,
        billing_service.BillingConflictError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.post(
    "/practice/fees/invoices/{invoice_id}/collections",
    response_model=FeeCollectionResponse,
)
async def record_collection(
    invoice_id: str,
    payload: FeeCollectionCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.record_fee_collection(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            invoice_id=invoice_id,
            payload=payload,
            session=session if payload.post_to_mitrabooks else None,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
        billing_service.BillingValidationError,
        billing_service.BillingConflictError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.get(
    "/practice/fees/invoices/{invoice_id}/collections",
    response_model=FeeCollectionListResponse,
)
async def list_collections(
    invoice_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.list_fee_collections(
            tenant_id=tenant_id,
            app_key=app_key,
            invoice_id=invoice_id,
            limit=limit,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingNotFoundError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.get("/practice/fees/gl-map", response_model=FeeGlMapResponse)
async def get_gl_map(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.get_fee_gl_map(
            tenant_id=tenant_id, app_key=app_key
        )
    except billing_service.BillingDisabledError as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.put("/practice/fees/gl-map", response_model=FeeGlMapResponse)
async def upsert_gl_map(
    payload: FeeGlMapUpsertRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.upsert_fee_gl_map(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            payload=payload,
        )
    except billing_service.BillingDisabledError as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.post("/practice/time-entries", response_model=TimeEntryResponse)
async def create_time_entry(
    payload: TimeEntryCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.create_time_entry(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            payload=payload,
        )
    except (
        billing_service.BillingDisabledError,
        billing_service.BillingValidationError,
        PracticeNotFoundError,
    ) as exc:
        raise _http_for_billing_error(exc) from exc


@billing_router.get("/practice/time-entries", response_model=TimeEntryListResponse)
async def list_time_entries(
    matter_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await billing_service.list_time_entries(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            limit=limit,
        )
    except billing_service.BillingDisabledError as exc:
        raise _http_for_billing_error(exc) from exc
