import re
from datetime import date
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, Response, UploadFile
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
    BusinessAdminSettingsResponse,
    BusinessAdminSettingsUpdateRequest,
    ApprovalQueueResponse,
    ApprovalReviewRequest,
    BankStatementVoucherRequest,
    BankStatementVoucherResponse,
    BillPaymentUpdateRequest,
    BusinessDocumentAttachmentListResponse,
    BusinessDocumentAttachmentResponse,
    CreditNoteCancelRequest,
    CreditNoteCreateRequest,
    CreditNoteListResponse,
    CreditNoteResponse,
    DebitNoteCancelRequest,
    DebitNoteCreateRequest,
    DebitNoteListResponse,
    DebitNoteResponse,
    GstPeriodLockListResponse,
    GstPeriodLockResponse,
    GstPeriodLockUpdateRequest,
    GstSettlementCreateRequest,
    GstSettlementReverseRequest,
    GstSettlementResponse,
    ItcReclaimActionRequest,
    ItcReversalActionRequest,
    ItcReversalPreviewResponse,
    InvoiceSettingsResponse,
    InvoiceSettingsUpdateRequest,
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
    SalesInvoiceCancelRequest,
    SalesInvoiceCreateRequest,
    SalesInvoiceListResponse,
    SalesInvoiceResponse,
)
from app.modules.business import allocation_service
from app.modules.business import banking_books
from app.modules.business import data_health as data_health_module
from app.modules.business import export_governance
from app.modules.business import financial_health
from app.modules.business import mis as mis_module
from app.modules.business import report_export
from app.modules.business import tally_xml
from app.modules.business import bank_recon
from app.modules.business import statements
from app.core.tenants.service import get_tenant
from app.modules.business.service import (
    cancel_credit_note,
    cancel_debit_note,
    cancel_purchase_bill,
    cancel_sales_invoice,
    create_business_document_attachment,
    create_credit_note,
    create_debit_note,
    download_business_document_attachment,
    create_gst_settlement,
    create_party,
    create_purchase_bill,
    create_sales_invoice,
    deactivate_party,
    get_credit_note,
    get_business_admin_settings,
    get_debit_note,
    get_invoice_settings,
    get_purchase_bill,
    get_sales_invoice,
    list_credit_notes,
    list_debit_notes,
    list_business_document_attachments,
    list_documents_for_approval_queue,
    preview_gst_settlement,
    reverse_gst_settlement,
    get_party,
    list_gst_period_locks,
    list_parties,
    list_purchase_bills,
    list_sales_invoices,
    mark_bill_payment,
    party_outstanding_summary,
    party_wise_ledger,
    preview_itc_reversals,
    reclaim_itc_for_bill,
    review_credit_note,
    review_debit_note,
    review_purchase_bill,
    review_sales_invoice,
    reverse_itc_for_bill,
    save_business_admin_settings,
    save_invoice_settings,
    set_gst_period_lock,
    update_party,
)
from app.modules.business.invoice_pdf import build_sales_invoice_pdf
from app.core.permissions.rbac import Role, require_roles

router = APIRouter(prefix="/business", tags=["business"])


def _created_by(current_user: dict) -> str:
    return str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")


def _require_posted_document_for_output(document: dict | None, *, not_found_detail: str, label: str) -> dict:
    if document is None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if str(document.get("status") or "").strip().lower() != "posted":
        raise HTTPException(status_code=409, detail=f"Only posted {label} can be rendered or exported")
    return document


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


# Payment-allocation routes moved to routes/allocations.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

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


@router.get("/mis/kpis")
async def business_mis_kpis(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Source-backed MIS KPI contract for trends, top parties and overdue views."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "MIS KPI contracts")
    try:
        return await mis_module.build_mis_kpis(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/data-health")
async def business_data_health(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Read-only Data Health Score for tenant-scoped MitraBooks records."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "data health")
    return await data_health_module.build_data_health_score(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


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
    format: str = Query("csv", pattern="^(csv|xlsx|pdf|json)$"),
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
    export_format = export_governance.validate_export_format(format, allowed={"csv", "xlsx", "pdf", "json"})
    export_governance.require_export_permission(current_user, export_type="business_report")
    try:
        spec = await _build_business_report(
            report, session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of, account_id=account_id,
            from_date=from_date, to_date=to_date, party_id=party_id,
        )
        response = report_export.export_report(export_format, **spec)
        return await export_governance.govern_export_response(
            response,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            current_user=current_user,
            export_type="business_report",
            export_format=export_format,
            report_key=report,
            filters={
                "kind": kind,
                "as_of": as_of.isoformat() if as_of else None,
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
                "account_id": account_id,
                "party_id": party_id,
            },
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tally/xml-export")
async def export_business_tally_xml(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Proof-of-concept Tally XML export for posted trial-balance ledger masters."""
    context = _alloc_context(current_user, x_tenant_id, x_app_key, "Tally XML export")
    export_governance.require_export_permission(current_user, export_type="tally_xml")
    try:
        spec = await _build_business_report(
            "trial_balance", session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, kind="receivable", as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    as_of_str = (as_of or date.today()).isoformat()
    xml_bytes = tally_xml.build_trial_balance_tally_xml(spec=spec, company_name=spec.get("org_name"), as_of=as_of_str)
    response = Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="tally_trial_balance_{as_of_str}.xml"'},
    )
    return await export_governance.govern_export_response(
        response,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        current_user=current_user,
        export_type="tally_xml",
        export_format="xml",
        report_key="trial_balance",
        filters={"as_of": as_of_str},
    )


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


# CA client / document metadata routes moved to routes/ca_clients.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

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


# Voucher routes moved to routes/vouchers.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

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
    export_governance.require_export_permission(current_user, export_type="sales_invoice_pdf")
    invoice = await get_sales_invoice(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        invoice_id=invoice_id,
    )
    invoice = _require_posted_document_for_output(
        invoice,
        not_found_detail="Sales invoice not found",
        label="sales invoices",
    )
    settings = await get_invoice_settings(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )
    pdf_bytes = build_sales_invoice_pdf(invoice, settings.get("branding") or {})
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
    return await export_governance.govern_export_response(
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
        operation="purchase bill listing",
    )
    return await list_purchase_bills(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        approval_status=approval_status,
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


@router.post("/bills/{bill_id}/review", response_model=PurchaseBillResponse)
async def review_business_purchase_bill(
    bill_id: str,
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
        operation="purchase bill approval review",
    )
    try:
        return await review_purchase_bill(
            session=session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            bill_id=bill_id,
            reviewed_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        operation="credit note listing",
    )
    return await list_credit_notes(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        approval_status=approval_status,
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


@router.post("/credit-notes/{credit_note_id}/review", response_model=CreditNoteResponse)
async def review_business_credit_note(
    credit_note_id: str,
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
        operation="credit note approval review",
    )
    try:
        return await review_credit_note(
            session=session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            credit_note_id=credit_note_id,
            reviewed_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        operation="debit note listing",
    )
    return await list_debit_notes(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        status=status,
        approval_status=approval_status,
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


@router.post("/debit-notes/{debit_note_id}/review", response_model=DebitNoteResponse)
async def review_business_debit_note(
    debit_note_id: str,
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
        operation="debit note approval review",
    )
    try:
        return await review_debit_note(
            session=session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            debit_note_id=debit_note_id,
            reviewed_by=_created_by(current_user),
            payload=payload,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
