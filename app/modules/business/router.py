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
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """CFO-Insight Financial Health: ledger-backed KPIs, charts and alerts.

    Every figure is computed deterministically from the posted ledger (see
    ``financial_health.assemble_financial_health``); the response is a fixed
    chart-spec vocabulary the frontend renders directly."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "financial health")
    try:
        return await financial_health.build_financial_health(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
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
    account_id=None, from_date=None, to_date=None,
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

    else:
        raise AccountingValidationError(
            "report must be one of: party_ledger, aging, itc_reversals, trial_balance, general_ledger"
        )

    spec["org_name"] = org_name
    return spec


@router.get("/reports/export")
async def export_business_report(
    report: str = Query(..., pattern="^(party_ledger|aging|itc_reversals|trial_balance|general_ledger|balance_sheet|profit_loss)$"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    account_id: int | None = Query(default=None),
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
            from_date=from_date, to_date=to_date,
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
    return await gst_returns.build_cmp08(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        quarter=quarter,
        gstin=gstin,
    )


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
