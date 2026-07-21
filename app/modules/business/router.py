from fastapi import APIRouter, Depends, Header, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session  # noqa: F401  # re-exported for smoke-test dependency overrides
from app.modules.business.schemas import (
    ApprovalQueueResponse,
    BusinessAdminSettingsResponse,
    BusinessAdminSettingsUpdateRequest,
    InvoiceSettingsResponse,
    InvoiceSettingsUpdateRequest,
)
from app.modules.business.service import (
    get_business_admin_settings,
    get_invoice_settings,
    list_documents_for_approval_queue,
    save_business_admin_settings,
    save_invoice_settings,
)

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

# GST settlement / period-lock routes moved to routes/gst_settlement.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# GST return routes moved to routes/gst_returns.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# TDS routes moved to routes/tds.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Bank-recon / bank-cash-book routes moved to routes/bank_recon_routes.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

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
from app.modules.business.routes import gst_settlement as _gst_settlement_routes  # noqa: E402,F401
from app.modules.business.routes import bank_recon_routes as _bank_recon_routes  # noqa: E402,F401

# Test / monkeypatch surface: handlers live in routes/*, but phase2 patches these
# names on the router facade (same pattern as service.py domain re-exports).
from app.modules.business import export_governance as export_governance  # noqa: E402,F401
from app.modules.business.invoice_pdf import build_sales_invoice_pdf as build_sales_invoice_pdf  # noqa: E402,F401
from app.modules.business.service import get_sales_invoice as get_sales_invoice  # noqa: E402,F401
from app.modules.business.routes.sales_invoices import (  # noqa: E402,F401
    _require_posted_document_for_output as _require_posted_document_for_output,
    get_business_sales_invoice_pdf as get_business_sales_invoice_pdf,
)
