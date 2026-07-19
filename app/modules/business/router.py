import re
from datetime import date

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
)
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business.schemas import (
    BusinessAdminSettingsResponse,
    BusinessAdminSettingsUpdateRequest,
    ApprovalQueueResponse,
    BankStatementVoucherRequest,
    BankStatementVoucherResponse,
    GstPeriodLockListResponse,
    GstPeriodLockResponse,
    GstPeriodLockUpdateRequest,
    GstSettlementCreateRequest,
    GstSettlementReverseRequest,
    GstSettlementResponse,
    InvoiceSettingsResponse,
    InvoiceSettingsUpdateRequest,
)
from app.modules.business import banking_books
from app.modules.business import bank_recon
from app.modules.business.service import (
    create_gst_settlement,
    get_business_admin_settings,
    get_invoice_settings,
    list_documents_for_approval_queue,
    preview_gst_settlement,
    reverse_gst_settlement,
    list_gst_period_locks,
    save_business_admin_settings,
    save_invoice_settings,
    set_gst_period_lock,
)
from app.core.permissions.rbac import Role, require_roles

router = APIRouter(prefix="/business", tags=["business"])


def _created_by(current_user: dict) -> str:
    return str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")


@router.get("/approval-queue", response_model=ApprovalQueueResponse)
async def business_approval_queue(
    document_type: str | None = Query(default=None, pattern="^(voucher|sales_invoice|purchase_bill|credit_note|debit_note)$"),
    status: str | None = Query(default=None, pattern="^(draft|pending_approval|posted|rejected|cancelled|reversed|posting)$"),
    approval_status: str | None = Query(default=None, pattern="^(auto_posted|not_submitted|pending_approval|approved|rejected)$"),
    include_reviewed: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    limit: int = Query(default=100, ge=1, le=500),
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
        operation="business approval queue",
    )
    return await list_documents_for_approval_queue(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        document_type=document_type,
        status=status,
        approval_status=approval_status,
        include_reviewed=include_reviewed,
        limit=limit,
    )


# Business party routes moved to routes/parties.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# ===================== Payment allocation (open-item AR/AP) =====================


def _alloc_context(current_user, x_tenant_id, x_app_key, operation):
    return resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation=operation,
    )


# Payment-allocation routes moved to routes/allocations.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Dashboard / analytics / report-export routes moved to routes/reports.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# CA client / document metadata routes moved to routes/ca_clients.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Business document attachment routes moved to routes/attachments.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Voucher routes moved to routes/vouchers.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Sales invoice routes moved to routes/sales_invoices.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

@router.get("/invoice-settings", response_model=InvoiceSettingsResponse)
async def get_business_invoice_settings(
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
        operation="invoice settings lookup",
    )
    return await get_invoice_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )


@router.get("/admin-settings", response_model=BusinessAdminSettingsResponse)
async def get_business_admin_settings_route(
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
        operation="business admin settings lookup",
    )
    return await get_business_admin_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )


@router.put("/admin-settings", response_model=BusinessAdminSettingsResponse)
async def update_business_admin_settings_route(
    payload: BusinessAdminSettingsUpdateRequest,
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
        operation="business admin settings update",
    )
    return await save_business_admin_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        updated_by=_created_by(current_user),
        payload=payload,
    )


@router.put("/invoice-settings", response_model=InvoiceSettingsResponse)
async def update_business_invoice_settings(
    payload: InvoiceSettingsUpdateRequest,
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
        operation="invoice settings update",
    )
    return await save_invoice_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        updated_by=_created_by(current_user),
        payload=payload,
    )


# Purchase bill routes moved to routes/purchase_bills.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# GST input-tax-credit (ITC) routes moved to routes/itc.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

@router.get("/gst-period-locks", response_model=GstPeriodLockListResponse)
async def list_business_gst_period_locks(
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
        operation="GST period lock listing",
    )
    return await list_gst_period_locks(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )


@router.put("/gst-period-locks", response_model=GstPeriodLockResponse)
async def update_business_gst_period_lock(
    payload: GstPeriodLockUpdateRequest,
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
        operation="GST period lock update",
    )
    return await set_gst_period_lock(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        updated_by=_created_by(current_user),
        payload=payload,
    )


# Credit-note / debit-note routes moved to routes/credit_debit_notes.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

@router.get("/gst-settlement/preview", response_model=GstSettlementResponse)
async def preview_business_gst_settlement(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GST settlement preview",
    )
    return await preview_gst_settlement(
        session,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
    )


@router.post("/gst-settlement", response_model=GstSettlementResponse)
async def create_business_gst_settlement(
    payload: GstSettlementCreateRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GST settlement",
    )
    try:
        return await create_gst_settlement(
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


@router.post("/gst-settlement/{period}/reverse", response_model=GstSettlementResponse)
async def reverse_business_gst_settlement(
    period: str,
    payload: GstSettlementReverseRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
        raise HTTPException(status_code=422, detail="period must be 'YYYY-MM'")
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GST settlement reversal",
    )
    try:
        return await reverse_gst_settlement(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            created_by=_created_by(current_user),
            period=period,
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# GST return routes moved to routes/gst_returns.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# TDS routes moved to routes/tds.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

@router.post("/bank-recon/statement")
async def business_bank_statement_upload(
    account_id: int = Query(..., ge=1),
    payload: dict = Body(..., description='{"csv": "<bank statement CSV text>"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Import a bank-statement CSV for a bank ledger account. Lines are stored
    for matching; re-uploading the same rows is skipped (dedupe fingerprint)."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank statement upload",
    )
    csv_text = str(payload.get("csv") or "")
    try:
        return await bank_recon.upload_bank_statement(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            account_id=account_id,
            csv_text=csv_text,
            created_by=_created_by(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/bank-recon")
async def business_bank_reconciliation(
    account_id: int = Query(..., ge=1),
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Bank reconciliation for one bank account: matched lines, in-bank-not-in-
    books, in-books-not-in-bank, match suggestions, and the BRS summary."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank reconciliation",
    )
    try:
        return await bank_recon.build_bank_reconciliation(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            account_id=account_id,
            as_of=as_of,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/bank-recon/match")
async def business_bank_recon_match(
    payload: dict = Body(..., description='{"statement_line_id": "...", "line_id": 123, "account_id": 1}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Confirm a statement-line <-> book-entry match. Metadata only — never
    posts to the ledger. Amount and direction must agree exactly."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank reconciliation match",
    )
    try:
        return await bank_recon.create_bank_recon_match(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            account_id=int(payload.get("account_id") or 0),
            statement_line_id=str(payload.get("statement_line_id") or ""),
            line_id=int(payload.get("line_id") or 0),
            created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/bank-recon/match/{match_id}/reverse")
async def business_bank_recon_unmatch(
    match_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Undo a confirmed match (soft reverse — the lines become unmatched again)."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank reconciliation unmatch",
    )
    try:
        return await bank_recon.reverse_bank_recon_match(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            match_id=match_id,
            reversed_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/bank-recon/statement-voucher", response_model=BankStatementVoucherResponse)
async def business_bank_recon_statement_voucher(
    payload: BankStatementVoucherRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Create a voucher for a bank-only statement line, such as bank charges,
    interest, or direct credits. The accounting entry is posted only through
    the normal typed-voucher review path."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank reconciliation statement voucher",
    )
    try:
        return await bank_recon.post_bank_statement_line_voucher(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=payload.accounting_entity_id,
            account_id=payload.account_id,
            statement_line_id=payload.statement_line_id,
            offset_account_id=payload.offset_account_id,
            offset_account_code=payload.offset_account_code,
            description=payload.description,
            reference=payload.reference,
            approve=payload.approve,
            created_by=_created_by(current_user),
            idempotency_key=x_idempotency_key,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/banking/books")
async def business_bank_cash_book(
    from_date: date,
    to_date: date,
    book_type: str = Query(default="all", pattern="^(all|cash|bank)$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="bank and cash book",
    )
    try:
        return await banking_books.build_bank_cash_book(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
            book_type=book_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# Statement/dunning routes moved to routes/statements.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Opening-balance / year-end routes moved to routes/opening_close.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# e-Invoice routes moved to routes/einvoice.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Inventory routes moved to routes/inventory.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Dimension routes moved to routes/dimensions.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Fixed-asset / depreciation routes moved to routes/fixed_assets.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# CA access routes moved to routes/ca_access.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Sub-routers registered on the shared ``router`` above (imported for side effects).
from app.modules.business.routes import allocations as _allocations_routes  # noqa: E402,F401
from app.modules.business.routes import inventory as _inventory_routes  # noqa: E402,F401
from app.modules.business.routes import dimensions as _dimensions_routes  # noqa: E402,F401
from app.modules.business.routes import fixed_assets as _fixed_assets_routes  # noqa: E402,F401
from app.modules.business.routes import gst_returns as _gst_returns_routes  # noqa: E402,F401
from app.modules.business.routes import tds as _tds_routes  # noqa: E402,F401
from app.modules.business.routes import statements as _statements_routes  # noqa: E402,F401
from app.modules.business.routes import opening_close as _opening_close_routes  # noqa: E402,F401
from app.modules.business.routes import einvoice as _einvoice_routes  # noqa: E402,F401
from app.modules.business.routes import ca_clients as _ca_clients_routes  # noqa: E402,F401
from app.modules.business.routes import vouchers as _vouchers_routes  # noqa: E402,F401
from app.modules.business.routes import ca_access as _ca_access_routes  # noqa: E402,F401
from app.modules.business.routes import reports as _reports_routes  # noqa: E402,F401

# Backward-compatible re-export: _build_business_report moved to routes/reports.py
# but existing callers/tests import it from this module.
from app.modules.business.routes.reports import _build_business_report  # noqa: E402,F401
from app.modules.business.routes import parties as _parties_routes  # noqa: E402,F401
from app.modules.business.routes import attachments as _attachments_routes  # noqa: E402,F401
from app.modules.business.routes import sales_invoices as _sales_invoices_routes  # noqa: E402,F401
from app.modules.business.routes import purchase_bills as _purchase_bills_routes  # noqa: E402,F401
from app.modules.business.routes import itc as _itc_routes  # noqa: E402,F401
from app.modules.business.routes import credit_debit_notes as _credit_debit_notes_routes  # noqa: E402,F401
