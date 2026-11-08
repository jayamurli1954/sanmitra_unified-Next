"""AI Document Capture routes (Phase 1).

Registered on the shared ``router`` from ``app.modules.business.router``. Gated by
the business module flag AND the capture two-flag add-on gate (default OFF).
Upload a bill → LLM-vision extract → validate → score → it lands as a draft or a
needs_review CaptureItem. No ledger posting happens here.
"""
from fastapi import Body, Depends, File, Header, HTTPException, Query, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import AppTenantContext
from app.modules.business.capture import gating
from app.modules.business.capture import service as capture_service
from app.modules.business.router import _created_by, router


async def _read_upload(file: UploadFile) -> bytes:
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > capture_service.MAX_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB limit")
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return bytes(data)


@router.post("/capture/upload")
async def capture_upload(
    file: UploadFile = File(...),
    _module_context: dict = Depends(require_enabled_module("business")),
    context: AppTenantContext = Depends(
        gating.require_capture_context("capture upload", gating.CAPTURE_MANAGE_ROLES)
    ),
    current_user: dict = Depends(get_current_user),
):
    raw = await _read_upload(file)
    try:
        return await capture_service.ingest_upload(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            raw=raw,
            media_type=file.content_type or "",
            filename=file.filename or "upload",
            created_by=_created_by(current_user),
        )
    except capture_service.CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/capture/items")
async def capture_list(
    status: str | None = Query(default=None, pattern="^(captured|drafted|needs_review|duplicate|rejected)$"),
    limit: int = Query(default=100, ge=1, le=500),
    context: AppTenantContext = Depends(gating.require_capture_context("capture list")),
):
    return await capture_service.list_items(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=context.accounting_entity_id,
        status=status,
        limit=limit,
    )


@router.get("/capture/items/{capture_id}")
async def capture_get(
    capture_id: str,
    context: AppTenantContext = Depends(gating.require_capture_context("capture get")),
):
    try:
        return await capture_service.get_item(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            capture_id=capture_id,
        )
    except capture_service.CaptureError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/capture/items/{capture_id}/reject")
async def capture_reject(
    capture_id: str,
    reason: str = Body(default="", embed=True),
    context: AppTenantContext = Depends(
        gating.require_capture_context("capture reject", gating.CAPTURE_MANAGE_ROLES)
    ),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await capture_service.reject_item(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=context.accounting_entity_id,
            capture_id=capture_id,
            reason=reason,
            actor=_created_by(current_user),
        )
    except capture_service.CaptureError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/capture/access")
async def capture_access(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
):
    return await gating.resolve_capture_access(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        x_accounting_entity_id=x_accounting_entity_id,
    )
