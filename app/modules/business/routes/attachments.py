"""Business document attachment routes (sales invoice / purchase bill / CA document).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. The attachment-only helpers
_safe_content_disposition and _read_business_upload moved here with the handlers;
the shared _created_by helper stays in router.py.
"""
import re
from urllib.parse import quote

from fastapi import Depends, File, Header, HTTPException, Query, Response, UploadFile

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business.schemas import (
    BusinessDocumentAttachmentListResponse,
    BusinessDocumentAttachmentResponse,
)
from app.modules.business.service import (
    create_business_document_attachment,
    download_business_document_attachment,
    list_business_document_attachments,
)
from app.modules.business.router import _created_by, router


def _safe_content_disposition(filename: str) -> str:
    safe_name = re.sub(r"[\x00-\x1f\x7f]", "", filename)
    encoded = quote(safe_name, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.")
    return f"attachment; filename*=UTF-8''{encoded}"


async def _read_business_upload(file: UploadFile) -> bytes:
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Attachment file exceeds the 10 MB limit")
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return bytes(data)


@router.post("/invoices/{invoice_id}/attachments", response_model=BusinessDocumentAttachmentResponse)
async def upload_sales_invoice_attachment(
    invoice_id: str,
    file: UploadFile = File(...),
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
        operation="sales invoice attachment upload",
    )
    try:
        return await create_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="sales_invoice",
            owner_id=invoice_id,
            uploaded_by=_created_by(current_user),
            file_name=file.filename or "attachment",
            content_type=file.content_type,
            payload=await _read_business_upload(file),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/invoices/{invoice_id}/attachments", response_model=BusinessDocumentAttachmentListResponse)
async def list_sales_invoice_attachments(
    invoice_id: str,
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
        operation="sales invoice attachment listing",
    )
    try:
        return await list_business_document_attachments(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="sales_invoice",
            owner_id=invoice_id,
            limit=limit,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/invoices/{invoice_id}/attachments/{attachment_id}/download")
async def download_sales_invoice_attachment(
    invoice_id: str,
    attachment_id: str,
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
        operation="sales invoice attachment download",
    )
    try:
        result = await download_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="sales_invoice",
            owner_id=invoice_id,
            attachment_id=attachment_id,
            downloaded_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=bytes(result["payload"]),
        media_type=result.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": _safe_content_disposition(result.get("file_name") or "attachment")},
    )


@router.post("/bills/{bill_id}/attachments", response_model=BusinessDocumentAttachmentResponse)
async def upload_purchase_bill_attachment(
    bill_id: str,
    file: UploadFile = File(...),
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
        operation="purchase bill attachment upload",
    )
    try:
        return await create_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="purchase_bill",
            owner_id=bill_id,
            uploaded_by=_created_by(current_user),
            file_name=file.filename or "attachment",
            content_type=file.content_type,
            payload=await _read_business_upload(file),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/bills/{bill_id}/attachments", response_model=BusinessDocumentAttachmentListResponse)
async def list_purchase_bill_attachments(
    bill_id: str,
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
        operation="purchase bill attachment listing",
    )
    try:
        return await list_business_document_attachments(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="purchase_bill",
            owner_id=bill_id,
            limit=limit,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/bills/{bill_id}/attachments/{attachment_id}/download")
async def download_purchase_bill_attachment(
    bill_id: str,
    attachment_id: str,
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
        operation="purchase bill attachment download",
    )
    try:
        result = await download_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="purchase_bill",
            owner_id=bill_id,
            attachment_id=attachment_id,
            downloaded_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=bytes(result["payload"]),
        media_type=result.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": _safe_content_disposition(result.get("file_name") or "attachment")},
    )


@router.post("/ca-documents/{document_id}/attachments", response_model=BusinessDocumentAttachmentResponse)
async def upload_ca_document_attachment(
    document_id: str,
    file: UploadFile = File(...),
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
        operation="CA document attachment upload",
    )
    try:
        return await create_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="ca_document",
            owner_id=document_id,
            uploaded_by=_created_by(current_user),
            file_name=file.filename or "attachment",
            content_type=file.content_type,
            payload=await _read_business_upload(file),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/ca-documents/{document_id}/attachments", response_model=BusinessDocumentAttachmentListResponse)
async def list_ca_document_attachments(
    document_id: str,
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
        operation="CA document attachment listing",
    )
    try:
        return await list_business_document_attachments(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="ca_document",
            owner_id=document_id,
            limit=limit,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/ca-documents/{document_id}/attachments/{attachment_id}/download")
async def download_ca_document_attachment(
    document_id: str,
    attachment_id: str,
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
        operation="CA document attachment download",
    )
    try:
        result = await download_business_document_attachment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            owner_type="ca_document",
            owner_id=document_id,
            attachment_id=attachment_id,
            downloaded_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=bytes(result["payload"]),
        media_type=result.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": _safe_content_disposition(result.get("file_name") or "attachment")},
    )
