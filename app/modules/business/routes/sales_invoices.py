"""Sales invoice routes (create / list / get / review / PDF / cancel).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. This is a pure move: handlers still call the
same app.modules.business.service functions, so double-entry/posting behaviour
is unaffected. The output-guard helper _require_posted_document_for_output moved
here (its only caller was the invoice PDF route); the shared _created_by helper
stays in router.py.
"""
from urllib.parse import quote

from fastapi import Depends, Header, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    SalesInvoiceListResponse,
    SalesInvoiceResponse,
)
from app.modules.business.service import (
    cancel_sales_invoice,
    create_sales_invoice,
    get_invoice_settings,
    get_sales_invoice,
    list_sales_invoices,
    review_sales_invoice,
)
from app.modules.business import router as business_router
from app.modules.business.router import _created_by, router


def _require_posted_document_for_output(document: dict | None, *, not_found_detail: str, label: str) -> dict:
    if document is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if str(document.get("status") or "").strip().lower() != "posted":
        raise HTTPException(status_code=409, detail=f"Only posted {label} can be rendered or exported")
    return document


@router.post("/invoices", response_model=SalesInvoiceResponse)
async def create_business_sales_invoice(
    payload: SalesInvoiceCreateRequest,
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
        operation="sales invoice posting",
    )
    try:
        return await create_sales_invoice(
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


@router.get("/invoices", response_model=SalesInvoiceListResponse)
async def list_business_sales_invoices(
    status: str | None = Query(default=None, pattern="^(draft|pending_approval|posted|rejected|cancelled)$"),
    approval_status: str | None = Query(default=None, pattern="^(auto_posted|not_submitted|pending_approval|approved|rejected)$"),
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
        operation="sales invoice listing",
    )
    return await list_sales_invoices(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        approval_status=approval_status,
        limit=limit,
    )


@router.get("/invoices/{invoice_id}", response_model=SalesInvoiceResponse)
async def get_business_sales_invoice(
    invoice_id: str,
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
        operation="sales invoice lookup",
    )
    invoice = await get_sales_invoice(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        invoice_id=invoice_id,
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Sales invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/review", response_model=SalesInvoiceResponse)
async def review_business_sales_invoice(
    invoice_id: str,
    payload: ApprovalReviewRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="sales invoice approval review",
    )
    try:
        return await review_sales_invoice(
            session=session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            invoice_id=invoice_id,
            reviewed_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/invoices/{invoice_id}/pdf")
async def get_business_sales_invoice_pdf(
    invoice_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Render a posted sales invoice (or Bill of Supply) to PDF via the shared
    document renderer (app/core/documents)."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="sales invoice PDF",
    )
    business_router.export_governance.require_export_permission(current_user, export_type="sales_invoice_pdf")
    # Resolve via router facade so tests can monkeypatch business_router.get_sales_invoice.
    invoice = await business_router.get_sales_invoice(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        invoice_id=invoice_id,
    )
    invoice = business_router._require_posted_document_for_output(
        invoice,
        not_found_detail="Sales invoice not found",
        label="sales invoices",
    )
    settings = await business_router.get_invoice_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )
    pdf_bytes = business_router.build_sales_invoice_pdf(invoice, settings.get("branding") or {})
    raw_name = f"{invoice.get('invoice_number') or invoice_id}.pdf".replace('"', "").replace("/", "-")
    # A non-ASCII invoice number (e.g. a local-language prefix) cannot be encoded
    # in a Latin-1 header value, which would make Starlette raise. Emit an ASCII
    # fallback plus an RFC 5987 filename* for the UTF-8 form.
    ascii_name = raw_name.encode("ascii", "ignore").decode("ascii").strip() or "invoice.pdf"
    encoded = quote(raw_name)
    response = Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}"},
    )
    return await business_router.export_governance.govern_export_response(
        response,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        current_user=current_user,
        export_type="sales_invoice_pdf",
        export_format="pdf",
        report_key="sales_invoice",
        entity_id=invoice_id,
        filters={"invoice_id": invoice_id},
    )


@router.post("/invoices/{invoice_id}/cancel", response_model=SalesInvoiceResponse)
async def cancel_business_sales_invoice(
    invoice_id: str,
    payload: SalesInvoiceCancelRequest,
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
        operation="sales invoice cancellation",
    )
    try:
        return await cancel_sales_invoice(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            invoice_id=invoice_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
