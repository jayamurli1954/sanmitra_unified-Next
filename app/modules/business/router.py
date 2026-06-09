from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    get_business_dashboard,
    get_trial_balance,
)
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
from app.modules.business import report_export
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


# ===================== Report export (CSV / XLSX / PDF) =====================


async def _build_business_report(
    report: str, *, session, tenant_id, app_key, accounting_entity_id, kind, as_of,
) -> dict:
    """Assemble (title, columns, rows, footer, meta, filename_base) for a report."""
    as_of_str = (as_of or date.today()).isoformat()

    if report == "party_ledger":
        data = await party_wise_ledger(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
        )
        title = "Sundry Debtors" if kind == "receivable" else "Sundry Creditors"
        return {
            "title": title,
            "columns": [{"key": "party_name", "label": "Party"},
                        {"key": "balance", "label": "Balance", "numeric": True}],
            "rows": data["items"],
            "footer": {"party_name": "Total", "balance": data.get("total_balance")},
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"{'debtors' if kind == 'receivable' else 'creditors'}_{as_of_str}",
        }

    if report == "aging":
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
        return {
            "title": title, "columns": columns, "rows": rows, "footer": footer,
            "meta": [("As of", as_of_str), ("Type", kind)],
            "filename_base": f"aging_{kind}_{as_of_str}",
        }

    if report == "itc_reversals":
        data = await preview_itc_reversals(
            tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
        )
        data = data if isinstance(data, dict) else data.model_dump()
        return {
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

    if report == "trial_balance":
        lines, total_debit, total_credit = await get_trial_balance(
            session, tenant_id=tenant_id, as_of=(as_of or date.today()),
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        return {
            "title": "Trial Balance",
            "columns": [
                {"key": "account_code", "label": "Code"},
                {"key": "account_name", "label": "Account"},
                {"key": "debit_total", "label": "Debit", "numeric": True},
                {"key": "credit_total", "label": "Credit", "numeric": True},
                {"key": "net_balance", "label": "Net", "numeric": True},
            ],
            "rows": lines,
            "footer": {"account_name": "Total", "debit_total": total_debit, "credit_total": total_credit},
            "meta": [("As of", as_of_str)],
            "filename_base": f"trial_balance_{as_of_str}",
        }

    raise AccountingValidationError(
        "report must be one of: party_ledger, aging, itc_reversals, trial_balance"
    )


@router.get("/reports/export")
async def export_business_report(
    report: str = Query(..., pattern="^(party_ledger|aging|itc_reversals|trial_balance)$"),
    format: str = Query("csv", pattern="^(csv|xlsx|pdf)$"),
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    as_of: date | None = Query(default=None),
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
            accounting_entity_id=accounting_entity_id, kind=kind, as_of=as_of,
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
