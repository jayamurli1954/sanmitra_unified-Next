"""CA client and CA document metadata routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from fastapi import Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business.schemas import (
    CaClientCreateRequest,
    CaClientListResponse,
    CaClientResponse,
    CaClientUpdateRequest,
    CaDocumentCreateRequest,
    CaDocumentListResponse,
    CaDocumentResponse,
    CaDocumentUpdateRequest,
)
from app.modules.business.service import (
    create_ca_client,
    create_ca_document_metadata,
    list_ca_clients,
    list_ca_document_metadata,
    update_ca_client,
    update_ca_document_metadata,
)
from app.modules.business.router import _created_by, router


@router.post("/ca-clients", response_model=CaClientResponse)
async def create_ca_client_record(
    payload: CaClientCreateRequest,
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
        operation="CA client creation",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    return await create_ca_client(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id or payload.accounting_entity_id,
        created_by=_created_by(current_user),
        payload=payload,
    )


@router.get("/ca-clients", response_model=CaClientListResponse)
async def list_ca_client_records(
    q: str | None = Query(default=None, min_length=1, max_length=160),
    active_only: bool = Query(default=True),
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
        operation="CA client listing",
        x_accounting_entity_id=accounting_entity_id,
    )
    return await list_ca_clients(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        q=q,
        active_only=active_only,
        limit=limit,
    )


@router.patch("/ca-clients/{client_id}", response_model=CaClientResponse)
async def update_ca_client_record(
    client_id: str,
    payload: CaClientUpdateRequest,
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
        operation="CA client update",
        x_accounting_entity_id=payload.accounting_entity_id,
    )
    result = await update_ca_client(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        client_id=client_id,
        updated_by=_created_by(current_user),
        payload=payload,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="CA client not found")
    return result


@router.post("/ca-documents", response_model=CaDocumentResponse)
async def create_ca_document(
    payload: CaDocumentCreateRequest,
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
        operation="CA document metadata creation",
        x_accounting_entity_id=x_accounting_entity_id,
    )
    return await create_ca_document_metadata(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id or payload.accounting_entity_id,
        created_by=_created_by(current_user),
        payload=payload,
    )


@router.get("/ca-documents", response_model=CaDocumentListResponse)
async def list_ca_documents(
    status: str | None = Query(default=None, pattern="^(uploaded|under_review|query_raised|reviewed|posted)$"),
    client_name: str | None = Query(default=None, min_length=1, max_length=160),
    assigned_to: str | None = Query(default=None, min_length=1, max_length=120),
    priority: str | None = Query(default=None, pattern="^(low|normal|high|urgent)$"),
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
        operation="CA document metadata listing",
    )
    return await list_ca_document_metadata(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        client_name=client_name,
        assigned_to=assigned_to,
        priority=priority,
        limit=limit,
    )


@router.patch("/ca-documents/{document_id}", response_model=CaDocumentResponse)
async def update_ca_document(
    document_id: str,
    payload: CaDocumentUpdateRequest,
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
        operation="CA document metadata update",
    )
    result = await update_ca_document_metadata(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=payload.accounting_entity_id,
        document_id=document_id,
        updated_by=_created_by(current_user),
        payload=payload,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="CA document metadata not found")
    return result
