import re
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    get_balance_sheet,
    get_business_dashboard,
    get_ledger_lines,
    get_profit_loss,
    get_trial_balance,
)
from app.accounting.service import _financial_year_start
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business.schemas import (
    AllocationCreateRequest,
    AllocationCreateResponse,
    AllocationRecord,
    BillPaymentUpdateRequest,
    CaDocumentCreateRequest,
    CaDocumentListResponse,
    CaDocumentResponse,
    CaDocumentUpdateRequest,
    CreditNoteCancelRequest,
    CreditNoteCreateRequest,
    CreditNoteListResponse,
    CreditNoteResponse,
    DebitNoteCancelRequest,
    DebitNoteCreateRequest,
    AgingResponse,
    DebitNoteListResponse,
    DebitNoteResponse,
    FifoSuggestionResponse,
    GstPeriodLockListResponse,
    GstPeriodLockResponse,
    GstPeriodLockUpdateRequest,
    GstSettlementCreateRequest,
    GstSettlementResponse,
    ItcReclaimActionRequest,
    ItcReversalActionRequest,
    ItcReversalPreviewResponse,
    InvoiceSettingsResponse,
    InvoiceSettingsUpdateRequest,
    OpenItemListResponse,
    PartyCreateRequest,
    PartyLedgerResponse,
    PartyListResponse,
    PartyOutstandingResponse,
    PartyResponse,
    PartyUpdateRequest,
    PurchaseBillCancelRequest,
    PurchaseBillCreateRequest,
    PurchaseBillListResponse,
    PurchaseBillResponse,
    ReconciliationResponse,
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    SalesInvoiceListResponse,
    SalesInvoiceResponse,
    TypedVoucherCreateRequest,
    TypedVoucherListResponse,
    TypedVoucherReversalRequest,
    TypedVoucherResponse,
    UnallocatedPaymentListResponse,
)
from app.modules.business import allocation_service
from app.modules.business import financial_health
from app.modules.business import gst_returns
from app.modules.business import report_export
from app.modules.business import bank_recon
from app.modules.business import dimensions as dimensions_module
from app.modules.business import einvoice as einvoice_module
from app.modules.business import inventory as inventory_module
from app.modules.business import fixed_assets
from app.modules.business import opening_close
from app.modules.business import statements
from app.modules.business import tds as tds_module
from app.core.tenants.service import get_tenant
from app.modules.business.service import (
    cancel_credit_note,
    cancel_debit_note,
    cancel_purchase_bill,
    cancel_sales_invoice,
    create_ca_document_metadata,
    create_credit_note,
    create_debit_note,
    create_gst_settlement,
    create_party,
    create_purchase_bill,
    create_sales_invoice,
    deactivate_party,
    get_credit_note,
    get_debit_note,
    get_invoice_settings,
    get_purchase_bill,
    get_sales_invoice,
    list_credit_notes,
    list_debit_notes,
    preview_gst_settlement,
    list_ca_document_metadata,
    get_party,
    get_voucher,
    list_gst_period_locks,
    list_parties,
    list_purchase_bills,
    list_sales_invoices,
    list_vouchers,
    mark_bill_payment,
    party_outstanding_summary,
    party_wise_ledger,
    post_typed_voucher,
    preview_itc_reversals,
    reclaim_itc_for_bill,
    reverse_itc_for_bill,
    reverse_typed_voucher,
    save_invoice_settings,
    set_gst_period_lock,
    update_ca_document_metadata,
    update_party,
)
from app.core.permissions.rbac import Role, require_roles

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


@router.get("/parties/{party_id}/outstanding", response_model=PartyOutstandingResponse)
async def get_business_party_outstanding(
    party_id: str,
    as_of: date | None = Query(default=None),
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
        operation="party outstanding",
    )
    try:
        return await party_outstanding_summary(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            party_id=party_id,
            as_of=as_of,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/party-ledger", response_model=PartyLedgerResponse)
async def get_business_party_ledger(
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
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
        operation="party-wise ledger",
    )
    try:
        return await party_wise_ledger(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            kind=kind,
            as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ===================== Payment allocation (open-item AR/AP) =====================


def _alloc_context(current_user, x_tenant_id, x_app_key, operation):
    return resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation=operation,
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


@router.get("/dashboard")
async def business_dashboard(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Live executive dashboard (KPIs, balances, 6-month trend) from the ledger."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "dashboard")
    return await get_business_dashboard(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


@router.get("/financial-health")
async def business_financial_health(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    narrate: bool = Query(default=True),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """CFO-Insight Financial Health: ledger-backed KPIs, charts and alerts, plus an
    optional AI narrative.

    Every figure is computed deterministically from the posted ledger (see
    ``financial_health.assemble_financial_health``); the response is a fixed
    chart-spec vocabulary the frontend renders directly. The AI narrative only
    rewrites those figures into prose and never invents numbers."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "financial health")
    try:
        return await financial_health.build_financial_health(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of, narrate=narrate,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ===================== Report export (CSV / XLSX / PDF) =====================


async def _resolve_org_name(tenant_id: str, app_key: str, accounting_entity_id: str) -> str | None:
    """Company name for report headers: invoice-settings business name, else the
    tenant's display name."""
    try:
        settings = await get_invoice_settings(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        name = ((settings or {}).get("branding") or {}).get("business_name")
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    try:
        tenant = await get_tenant(tenant_id)
        name = (tenant or {}).get("display_name")
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    return None


async def _build_business_report(
    report: str, *, session, tenant_id, app_key, accounting_entity_id, kind, as_of,
    account_id=None, from_date=None, to_date=None, party_id=None,
) -> dict:
    """Assemble (title, columns, rows, footer, meta, org_name, filename_base) for a report."""
    as_of_str = (as_of or date.today()).isoformat()
    org_name = await _resolve_org_name(tenant_id, app_key, accounting_entity_id)

    if report == "party_ledger":
        data = await party_wise_ledger(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
        )
        title = "Sundry Debtors" if kind == "receivable" else "Sundry Creditors"
        spec = {
            "title": title,
            "columns": [{"key": "party_name", "label": "Party"},
                        {"key": "balance", "label": "Balance", "numeric": True}],
            "rows": data["items"],
            "footer": {"party_name": "Total", "balance": data.get("total_balance")},
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"{'debtors' if kind == 'receivable' else 'creditors'}_{as_of_str}",
        }

    elif report == "aging":
        data = await allocation_service.ar_ap_aging(
            tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
        )
        order = data["buckets_order"]
        columns = [{"key": "party_name", "label": "Party"}]
        columns += [{"key": b, "label": b, "numeric": True} for b in order]
        columns += [{"key": "total", "label": "Total", "numeric": True}]
        rows = [{"party_name": r.get("party_name") or "Unallocated",
                 **r["buckets"], "total": r["total"]} for r in data["by_party"]]
        footer = {"party_name": "Total", **data["totals"], "total": data["grand_total"]}
        title = "Receivables Aging" if kind == "receivable" else "Payables Aging"
        spec = {
            "title": title, "columns": columns, "rows": rows, "footer": footer,
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"aging_{kind}_{as_of_str}",
        }

    elif report == "itc_reversals":
        data = await preview_itc_reversals(
            tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
        )
        data = data if isinstance(data, dict) else data.model_dump()
        spec = {
            "title": "ITC Reversals (GST Rule 37)",
            "columns": [
                {"key": "bill_number", "label": "Bill No."},
                {"key": "vendor_name", "label": "Vendor"},
                {"key": "bill_date", "label": "Bill Date"},
                {"key": "days_overdue", "label": "Days Overdue", "numeric": True},
                {"key": "itc_total", "label": "ITC Total", "numeric": True},
                {"key": "interest_amount", "label": "Interest", "numeric": True},
            ],
            "rows": data.get("candidates", []),
            "footer": {"bill_number": "Total", "itc_total": data.get("total_itc"),
                       "interest_amount": data.get("total_interest")},
            "meta": [("As of", as_of_str)],
            "filename_base": f"itc_reversals_{as_of_str}",
        }

    elif report == "balance_sheet":
        assets, liabilities, equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
            session, tenant_id=tenant_id, as_of=(as_of or date.today()),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )

        def _bs_section(section_label, items, subtotal_label, subtotal_value):
            section_rows = [{
                "section": section_label,
                "account_code": item.get("account_code"),
                "account_name": item.get("account_name"),
                "amount": item.get("balance"),
            } for item in items]
            section_rows.append({
                "section": "", "account_code": "", "account_name": subtotal_label, "amount": subtotal_value,
            })
            return section_rows

        rows = (
            _bs_section("Assets", assets, "Total Assets", total_assets)
            + _bs_section("Liabilities", liabilities, "Total Liabilities", total_liabilities)
            + _bs_section("Equity", equity, "Total Equity", total_equity)
        )
        spec = {
            "title": "Balance Sheet",
            "columns": [
                {"key": "section", "label": "Section"},
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "amount", "label": "Amount", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Total Liabilities + Equity",
                       "amount": total_liabilities + total_equity},
            "meta": [("As of", as_of_str)],
            "filename_base": f"balance_sheet_{as_of_str}",
        }

    elif report == "profit_loss":
        pnl_from = from_date or _financial_year_start(as_of or date.today())
        pnl_to = to_date or as_of or date.today()
        lines, income_total, expense_total, net_profit = await get_profit_loss(
            session, tenant_id=tenant_id, from_date=pnl_from, to_date=pnl_to,
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        income_lines = [l for l in lines if l.get("account_type") == "income"]
        expense_lines = [l for l in lines if l.get("account_type") == "expense"]

        def _pnl_section(section_label, items, subtotal_label, subtotal_value):
            section_rows = [{
                "section": section_label,
                "account_code": item.get("account_code"),
                "account_name": item.get("account_name"),
                "amount": item.get("net_amount"),
            } for item in items]
            section_rows.append({
                "section": "", "account_code": "", "account_name": subtotal_label, "amount": subtotal_value,
            })
            return section_rows

        rows = (
            _pnl_section("Income", income_lines, "Total Income", income_total)
            + _pnl_section("Expenses", expense_lines, "Total Expenses", expense_total)
        )
        spec = {
            "title": "Profit and Loss",
            "columns": [
                {"key": "section", "label": "Section"},
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "amount", "label": "Amount", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Net Profit", "amount": net_profit},
            "meta": [("From", pnl_from.isoformat()), ("To", pnl_to.isoformat())],
            "filename_base": f"profit_loss_{pnl_from.isoformat()}_{pnl_to.isoformat()}",
        }

    elif report == "trial_balance":
        lines, _total_debit, _total_credit = await get_trial_balance(
            session, tenant_id=tenant_id, as_of=(as_of or date.today()),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        # Match the on-screen Trial Balance: show each account's NET in its natural
        # column (Dr if positive, Cr if negative) — not raw debit + credit + net.
        rows = []
        net_debit_total = Decimal("0.00")
        net_credit_total = Decimal("0.00")
        for line in lines:
            net = line.get("net_balance")
            net = Decimal(str(net if net is not None
                             else Decimal(str(line.get("debit_total") or 0)) - Decimal(str(line.get("credit_total") or 0))))
            debit_cell = net if net > 0 else None
            credit_cell = -net if net < 0 else None
            if debit_cell:
                net_debit_total += debit_cell
            if credit_cell:
                net_credit_total += credit_cell
            rows.append({
                "account_code": line.get("account_code"),
                "account_name": line.get("account_name"),
                "debit": debit_cell,
                "credit": credit_cell,
            })
        spec = {
            "title": "Trial Balance",
            "columns": [
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
            ],
            "rows": rows,
            "footer": {"account_name": "Total", "debit": net_debit_total, "credit": net_credit_total},
            "meta": [("As of", as_of_str)],
            "filename_base": f"trial_balance_{as_of_str}",
        }

    elif report == "general_ledger":
        if not account_id:
            raise AccountingValidationError("account_id is required for the general ledger export")
        account, lines = await get_ledger_lines(
            session, tenant_id=tenant_id, account_id=int(account_id),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        total_debit = sum((Decimal(str(l["debit"] or 0)) for l in lines), Decimal("0.00"))
        total_credit = sum((Decimal(str(l["credit"] or 0)) for l in lines), Decimal("0.00"))
        closing = lines[-1]["running_balance"] if lines else Decimal("0.00")
        rows = [{
            "entry_date": l["entry_date"],
            "description": l["description"],
            "reference": l["reference"],
            "debit": l["debit"] or None,
            "credit": l["credit"] or None,
            "running_balance": l["running_balance"],
        } for l in lines]
        spec = {
            "title": "General Ledger",
            "columns": [
                {"key": "entry_date", "label": "Date"},
                {"key": "description", "label": "Particulars"},
                {"key": "reference", "label": "Reference"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
                {"key": "running_balance", "label": "Balance", "numeric": True},
            ],
            "rows": rows,
            "footer": {"description": "Total", "debit": total_debit, "credit": total_credit, "running_balance": closing},
            "meta": [("Account", f"{account.code} - {account.name}"), ("As of", as_of_str)],
            "filename_base": f"general_ledger_{account.code}_{as_of_str}",
        }

    elif report == "statement":
        if not party_id:
            raise AccountingValidationError("party_id is required for the statement export")
        data = await statements.build_party_statement(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, party_id=party_id,
            kind=kind, from_date=from_date, to_date=to_date or as_of,
        )
        rows = [{
            "entry_date": r["entry_date"], "document_type": r["document_type"],
            "reference": r["reference"], "description": r["description"],
            "debit": r["debit"] if Decimal(str(r["debit"] or 0)) else None,
            "credit": r["credit"] if Decimal(str(r["credit"] or 0)) else None,
            "balance": r["balance"],
        } for r in data["transactions"]]
        rows.insert(0, {"entry_date": data["from_date"], "document_type": "",
                        "reference": "", "description": "Opening balance",
                        "debit": None, "credit": None, "balance": data["opening_balance"]})
        spec = {
            "title": f"Statement of Account — {data['party']['party_name']}",
            "columns": [
                {"key": "entry_date", "label": "Date"},
                {"key": "document_type", "label": "Document"},
                {"key": "reference", "label": "Reference"},
                {"key": "description", "label": "Particulars"},
                {"key": "debit", "label": "Debit", "numeric": True},
                {"key": "credit", "label": "Credit", "numeric": True},
                {"key": "balance", "label": "Balance", "numeric": True},
            ],
            "rows": rows,
            "footer": {"description": "Closing balance", "debit": data["total_debit"],
                       "credit": data["total_credit"], "balance": data["closing_balance"]},
            "meta": [("Party", data["party"]["party_name"]), ("Type", kind),
                     ("From", data["from_date"]), ("To", data["to_date"])],
            "filename_base": f"statement_{party_id}_{data['to_date']}",
        }

    else:
        raise AccountingValidationError(
            "report must be one of: party_ledger, aging, itc_reversals, trial_balance, general_ledger, statement"
        )

    spec["org_name"] = org_name
    return spec


@router.get("/reports/export")
async def export_business_report(
    report: str = Query(..., pattern="^(party_ledger|aging|itc_reversals|trial_balance|general_ledger|balance_sheet|profit_loss|statement)$"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
    party_id: str | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "report export")
    try:
        spec = await _build_business_report(
            report, session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of, account_id=account_id,
            from_date=from_date, to_date=to_date, party_id=party_id,
        )
        return report_export.export_report(format, **spec)
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
    status: str | None = Query(default=None, pattern="^(posted|cancelled)$"),
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


@router.post("/bills", response_model=PurchaseBillResponse)
async def create_business_purchase_bill(
    payload: PurchaseBillCreateRequest,
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
        operation="purchase bill posting",
    )
    try:
        return await create_purchase_bill(
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


@router.get("/bills", response_model=PurchaseBillListResponse)
async def list_business_purchase_bills(
    status: str | None = Query(default=None, pattern="^(posted|cancelled)$"),
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
        operation="purchase bill listing",
    )
    return await list_purchase_bills(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        limit=limit,
    )


@router.get("/bills/{bill_id}", response_model=PurchaseBillResponse)
async def get_business_purchase_bill(
    bill_id: str,
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
        operation="purchase bill lookup",
    )
    bill = await get_purchase_bill(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        bill_id=bill_id,
    )
    if bill is None:
        raise HTTPException(status_code=404, detail="Purchase bill not found")
    return bill


@router.post("/bills/{bill_id}/cancel", response_model=PurchaseBillResponse)
async def cancel_business_purchase_bill(
    bill_id: str,
    payload: PurchaseBillCancelRequest,
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
        operation="purchase bill cancellation",
    )
    try:
        return await cancel_purchase_bill(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            bill_id=bill_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/bills/{bill_id}/payment", response_model=PurchaseBillResponse)
async def update_business_bill_payment(
    bill_id: str,
    payload: BillPaymentUpdateRequest,
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
        operation="bill payment update",
    )
    try:
        return await mark_bill_payment(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            bill_id=bill_id,
            created_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/itc-reversals/preview", response_model=ItcReversalPreviewResponse)
async def preview_business_itc_reversals(
    as_of: date | None = Query(default=None),
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
        operation="ITC reversal preview",
    )
    return await preview_itc_reversals(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        as_of=as_of,
    )


@router.post("/bills/{bill_id}/itc-reversal", response_model=PurchaseBillResponse)
async def reverse_business_bill_itc(
    bill_id: str,
    payload: ItcReversalActionRequest,
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
        operation="ITC reversal",
    )
    try:
        return await reverse_itc_for_bill(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            bill_id=bill_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/bills/{bill_id}/itc-reclaim", response_model=PurchaseBillResponse)
async def reclaim_business_bill_itc(
    bill_id: str,
    payload: ItcReclaimActionRequest,
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
        operation="ITC reclaim",
    )
    try:
        return await reclaim_itc_for_bill(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            bill_id=bill_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@router.post("/credit-notes", response_model=CreditNoteResponse)
async def create_business_credit_note(
    payload: CreditNoteCreateRequest,
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
        operation="credit note posting",
    )
    try:
        return await create_credit_note(
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


@router.get("/credit-notes", response_model=CreditNoteListResponse)
async def list_business_credit_notes(
    status: str | None = Query(default=None, pattern="^(posted|cancelled)$"),
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
        operation="credit note listing",
    )
    return await list_credit_notes(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        limit=limit,
    )


@router.get("/credit-notes/{credit_note_id}", response_model=CreditNoteResponse)
async def get_business_credit_note(
    credit_note_id: str,
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
        operation="credit note lookup",
    )
    note = await get_credit_note(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        credit_note_id=credit_note_id,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Credit note not found")
    return note


@router.post("/credit-notes/{credit_note_id}/cancel", response_model=CreditNoteResponse)
async def cancel_business_credit_note(
    credit_note_id: str,
    payload: CreditNoteCancelRequest,
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
        operation="credit note reversal",
    )
    try:
        return await cancel_credit_note(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            credit_note_id=credit_note_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/debit-notes", response_model=DebitNoteResponse)
async def create_business_debit_note(
    payload: DebitNoteCreateRequest,
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
        operation="debit note posting",
    )
    try:
        return await create_debit_note(
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


@router.get("/debit-notes", response_model=DebitNoteListResponse)
async def list_business_debit_notes(
    status: str | None = Query(default=None, pattern="^(posted|cancelled)$"),
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
        operation="debit note listing",
    )
    return await list_debit_notes(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        limit=limit,
    )


@router.get("/debit-notes/{debit_note_id}", response_model=DebitNoteResponse)
async def get_business_debit_note(
    debit_note_id: str,
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
        operation="debit note lookup",
    )
    note = await get_debit_note(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        debit_note_id=debit_note_id,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Debit note not found")
    return note


@router.post("/debit-notes/{debit_note_id}/cancel", response_model=DebitNoteResponse)
async def cancel_business_debit_note(
    debit_note_id: str,
    payload: DebitNoteCancelRequest,
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
        operation="debit note reversal",
    )
    try:
        return await cancel_debit_note(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            debit_note_id=debit_note_id,
            created_by=_created_by(current_user),
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


async def _resolve_business_gstin(tenant_id: str, app_key: str, accounting_entity_id: str) -> str | None:
    """Seller GSTIN for return headers, from invoice-settings branding (if set)."""
    try:
        settings = await get_invoice_settings(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        gstin = ((settings or {}).get("branding") or {}).get("gstin")
        if gstin and str(gstin).strip():
            return str(gstin).strip()
    except Exception:
        pass
    return None


@router.get("/returns/gstr-3b")
async def business_gstr3b_return(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """GSTR-3B monthly summary return for a 'YYYY-MM' period. Tax heads come from
    the immutable ledger (reusing the settlement set-off); taxable value from the
    posted sales-invoice/credit-note documents. Includes the GSTN JSON shape."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-3B return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr3b(
        session,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstin=gstin,
    )


@router.get("/returns/gstr-1")
async def business_gstr1_return(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """GSTR-1 outward-supplies return for a 'YYYY-MM' period. Built from posted
    sales-invoice and credit-note documents, grouped into the statutory sections
    (B2B / B2CL / B2CS / CDNR / HSN / DOCS). Includes the GSTN JSON shape."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-1 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr1(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstin=gstin,
    )


@router.get("/returns/cmp-08")
async def business_cmp08_return(
    quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Form CMP-08 — quarterly self-assessed liability for a composition dealer
    ('YYYY-Q1'..'YYYY-Q4', FY quarters). Tax = turnover x composition rate."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CMP-08 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    report = await gst_returns.build_cmp08(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        quarter=quarter,
        gstin=gstin,
    )
    report["liability_posting"] = await gst_returns.find_cmp08_posting(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, quarter=quarter,
    )
    return report


@router.post("/returns/cmp-08/post")
async def business_cmp08_post_liability(
    payload: dict = Body(..., description='{"quarter": "YYYY-Q1"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Book the quarter's composition levy in the ledger (admin only):
    Dr GST Expense (Composition) 54007 / Cr GST Payable (Net) 22004 on the
    quarter-end date. Idempotent per quarter; reverse the journal to redo."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="CMP-08 liability posting",
    )
    quarter = str(payload.get("quarter") or "").strip().upper()
    if not re.fullmatch(r"\d{4}-Q[1-4]", quarter):
        raise HTTPException(status_code=422, detail="quarter must be 'YYYY-Q1'..'YYYY-Q4'")
    try:
        return await gst_returns.post_cmp08_liability(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, quarter=quarter,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/returns/gstr-4")
async def business_gstr4_return(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Form GSTR-4 — annual composition return for a financial year ('YYYY-YY',
    e.g. '2026-27'). Consolidates the four CMP-08 quarters, the annual outward
    liability, and inward purchases (registered / unregistered)."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-4 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr4(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        financial_year=financial_year,
        gstin=gstin,
    )


@router.post("/returns/gstr-2b/reconcile")
async def business_gstr2b_reconcile(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    gstr2b: dict = Body(..., description="The GSTR-2B JSON downloaded from the GST portal."),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Reconcile an uploaded GSTR-2B JSON for a 'YYYY-MM' period against the input
    GST booked on posted purchase bills. Classifies matched / mismatch / available-
    not-booked / at-risk (booked but not in 2B, per Section 16(2)(aa))."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-2B reconciliation",
    )
    return await gst_returns.build_gstr2b_reconciliation(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstr2b_payload=gstr2b,
    )


@router.get("/tds/sections")
async def business_tds_sections(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """TDS / TCS section masters (default rates) for the document forms."""
    resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="TDS sections",
    )
    return tds_module.list_sections()


@router.get("/tds/register")
async def business_tds_register(
    quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Quarterly TDS/TCS register ('YYYY-Q1'..'YYYY-Q4', FY quarters) — the
    section-wise deductee/collectee working paper that feeds Form 26Q / 27EQ."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="TDS register",
    )
    return await tds_module.build_tds_register(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        quarter=quarter,
    )


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


@router.get("/statements/{party_id}")
async def business_party_statement(
    party_id: str,
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Statement of account for one customer/vendor: opening balance, dated
    transactions with running balance, closing balance, open items with aging,
    and (for receivables) the dunning suggestion + reminder letter + log."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="party statement",
    )
    try:
        return await statements.build_party_statement(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            party_id=party_id,
            kind=kind,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/statements/{party_id}/dunning")
async def business_record_dunning(
    party_id: str,
    payload: dict = Body(..., description='{"level": 1-3, "note": "...", "overdue_total": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Record that a payment reminder was sent (sending itself is manual —
    print/email/WhatsApp). Builds the dunning audit trail for the party."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="dunning record",
    )
    try:
        return await statements.record_dunning_sent(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            party_id=party_id,
            level=int(payload.get("level") or 0),
            note=payload.get("note"),
            overdue_total=payload.get("overdue_total"),
            created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/opening-balances/template")
async def business_opening_balance_template(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Sample CSV for the opening-balance import."""
    resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance template",
    )
    from fastapi.responses import Response
    return Response(
        content=opening_close.csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="opening_balances_template.csv"'},
    )


@router.post("/opening-balances/preview")
async def business_opening_balance_preview(
    payload: dict = Body(..., description='{"csv": "<opening balance CSV>", "as_of": "YYYY-MM-DD"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Parse + resolve the uploaded opening-balance CSV WITHOUT posting:
    resolved lines, row errors, totals and the Opening-Balance-Equity
    balancing line. Posting requires zero errors (maker-checker)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance preview",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else None
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await opening_close.build_opening_preview(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""), as_of=as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/opening-balances")
async def business_post_opening_balances(
    payload: dict = Body(..., description='{"csv": "...", "as_of": "YYYY-MM-DD", "allow_duplicate": false}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the opening balances as ONE journal entry (admin only). Any
    debit/credit difference goes to Opening Balance Equity; party rows carry
    party_id so they flow into aging/statements/allocation."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance posting",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else None
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await opening_close.post_opening_balances(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""), as_of=as_of,
            allow_duplicate=bool(payload.get("allow_duplicate")),
            created_by=_created_by(current_user),
            idempotency_key=x_idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/year-end/preview")
async def business_year_end_preview(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Year-end close preview for 'YYYY-YY': per-account closing lines, the
    Retained Earnings movement, and whether the FY is already closed."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="year-end preview",
    )
    return await opening_close.build_year_end_preview(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )


@router.post("/year-end/close")
async def business_year_end_close(
    payload: dict = Body(..., description='{"financial_year": "YYYY-YY"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the year-end closing journal (admin only): income/expense accounts
    zeroed to Retained Earnings on 31 March. Idempotent per financial year;
    reverse the entry to reopen the year."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="year-end close",
    )
    financial_year = str(payload.get("financial_year") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", financial_year):
        raise HTTPException(status_code=422, detail="financial_year must be 'YYYY-YY' (e.g. 2026-27)")
    try:
        return await opening_close.post_year_end_close(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, financial_year=financial_year,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/invoices/{invoice_id}/einvoice")
async def business_einvoice_view(
    invoice_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """e-Invoice view for one posted invoice: readiness errors, the INV-01
    JSON payload (when clean), and the recorded IRN status."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="e-invoice view",
    )
    try:
        return await einvoice_module.build_einvoice_view(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, invoice_id=invoice_id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/invoices/{invoice_id}/einvoice/record")
async def business_einvoice_record(
    invoice_id: str,
    payload: dict = Body(..., description='{"irn": "<64-hex>", "ack_no": "...", "ack_date": "...", "signed_qr": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Record the IRN/Ack the e-invoice portal returned for this invoice
    (manual flow today; the future IRP API client will call the same step)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="e-invoice IRN record",
    )
    try:
        return await einvoice_module.record_irn(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, invoice_id=invoice_id,
            irn=str(payload.get("irn") or ""), ack_no=payload.get("ack_no"),
            ack_date=payload.get("ack_date"), signed_qr=payload.get("signed_qr"),
            created_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/inventory/items")
async def business_create_item(
    payload: dict = Body(..., description='{"code": "...", "name": "...", "uqc": "NOS", "hsn_sac": "...", "opening_qty": 0, "opening_value": 0}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Create an inventory item (requires inventory accounting to be enabled)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item create",
    )
    if not await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    ):
        raise HTTPException(status_code=422, detail="Inventory accounting is disabled — enable it in Invoice Settings first")
    try:
        return await inventory_module.create_item(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/inventory/items")
async def business_list_items(
    include_inactive: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Item master. Also reports whether inventory accounting is enabled."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item list",
    )
    enabled = await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    )
    result = await inventory_module.list_items(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, include_inactive=include_inactive,
    )
    result["inventory_enabled"] = enabled
    return result


@router.patch("/inventory/items/{item_id}/deactivate")
async def business_deactivate_item(
    item_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Soft-deactivate an item (existing documents keep their tag)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item deactivate",
    )
    try:
        return await inventory_module.deactivate_item(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            item_id=item_id, updated_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/stock-register")
async def business_stock_register(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Per-item stock position as of a date (weighted-average valuation)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="stock register",
    )
    return await inventory_module.build_stock_register(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


@router.get("/inventory/closing-stock/entries")
async def business_closing_stock_entries(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Previously posted closing-stock journals (newest first)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="closing stock entries",
    )
    return {"items": await inventory_module.find_closing_stock_entries(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )}


@router.post("/inventory/closing-stock")
async def business_post_closing_stock(
    payload: dict = Body(..., description='{"as_of": "YYYY-MM-DD"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the closing-stock journal (admin only): Dr Inventory 13001 /
    Cr COGS 51002 at the register's value. Reverse the previous closing entry
    before posting a fresh position."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="closing stock posting",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await inventory_module.post_closing_stock(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/dimensions")
async def business_create_dimension(
    payload: dict = Body(..., description='{"dimension_type": "cost_centre|project", "code": "...", "name": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Create a cost centre or project (a reporting tag — no ledger impact)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension create",
    )
    try:
        return await dimensions_module.create_dimension(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/dimensions")
async def business_list_dimensions(
    include_inactive: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Dimension masters, split into cost_centres and projects."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension list",
    )
    return await dimensions_module.list_dimensions(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, include_inactive=include_inactive,
    )


@router.patch("/dimensions/{dimension_id}/deactivate")
async def business_deactivate_dimension(
    dimension_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Soft-deactivate a dimension (existing documents keep their tag)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension deactivate",
    )
    try:
        return await dimensions_module.deactivate_dimension(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            dimension_id=dimension_id, updated_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/dimensions/report")
async def business_dimension_report(
    dimension_type: str = Query(..., pattern="^(cost_centre|project)$"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Income/expense/net per cost centre or project over a period (defaults
    to the current financial year), with the untagged bucket and totals."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="dimension report",
    )
    return await dimensions_module.build_dimension_report(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        dimension_type=dimension_type, from_date=from_date, to_date=to_date,
    )


@router.post("/fixed-assets")
async def business_create_fixed_asset(
    payload: dict = Body(...),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Register a fixed asset (metadata only — the purchase posts via the
    normal bill/voucher to its 16xxx account)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="fixed asset create",
    )
    try:
        return await fixed_assets.create_fixed_asset(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/fixed-assets")
async def business_list_fixed_assets(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Fixed-asset register with accumulated depreciation and book value."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="fixed asset list",
    )
    return await fixed_assets.list_fixed_assets(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )


@router.get("/depreciation/preview")
async def business_depreciation_preview(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Per-asset depreciation schedule for the FY (SLM/WDV, day-prorated)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="depreciation preview",
    )
    return await fixed_assets.build_depreciation_preview(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )


@router.post("/depreciation/run")
async def business_depreciation_run(
    payload: dict = Body(..., description='{"financial_year": "YYYY-YY"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the FY depreciation journal (admin only): Dr Depreciation Expense,
    Cr Accumulated Depreciation. Idempotent per financial year."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="depreciation run",
    )
    financial_year = str(payload.get("financial_year") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", financial_year):
        raise HTTPException(status_code=422, detail="financial_year must be 'YYYY-YY' (e.g. 2026-27)")
    try:
        return await fixed_assets.post_depreciation_run(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, financial_year=financial_year,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
