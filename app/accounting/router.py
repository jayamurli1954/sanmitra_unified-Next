import asyncio
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import (
    ARApResponse,
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
    BalanceSheetResponse,
    ChartOfAccountsInitializeResponse,
    CoaMappingApproveRequest,
    CoaMappingApproveResponse,
    CoaMappingBulkUpsertRequest,
    CoaMappingGapResponse,
    CoaMappingResponse,
    CoaOnboardingStatusResponse,
    CoaSourceAccountBulkUpsertRequest,
    CoaSourceAccountResponse,
    JournalPostRequest,
    JournalPostResponse,
    JournalEntryResponse,
    JournalLineResponse,
    JournalReversalRequest,
    JournalReversalResponse,
    LedgerLineResponse,
    MappingStatus,
    ProfitLossResponse,
    ReceiptsPaymentsResponse,
    SourceJournalPostRequest,
    SourceJournalPostResponse,
    SourceSystem,
    TrialBalanceResponse,
)
from app.accounting.service import (
    AccountingIdempotencyConflictError,
    AccountingNotFoundError,
    AccountingValidationError,
    approve_coa_mappings,
    create_account,
    get_accounts_payable,
    get_accounts_receivable,
    get_balance_sheet,
    get_coa_mapping_gaps,
    get_coa_onboarding_status,
    get_ledger_lines,
    get_journal_drilldown,
    get_journal_voucher_detail,
    get_journal_entry_detail,
    get_profit_loss,
    get_receipts_payments,
    get_trial_balance,
    initialize_default_chart_of_accounts,
    list_accounts,
    list_journal_entries,
    list_coa_mappings,
    list_source_accounts,
    post_journal_entry,
    post_source_journal_entry,
    reverse_journal_entry,
    update_account,
    upsert_coa_mappings,
    upsert_source_accounts,
)
from app.accounting.context import AccountingContext, resolve_accounting_context
from app.core.auth.dependencies import get_current_user
from app.core.modules.registry import ModuleAccessError, require_module_access
from app.core.tenants.service import get_tenant
from app.db.postgres import get_async_session

router = APIRouter(prefix="/accounting", tags=["accounting"])


def _journal_entry_response(entry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        app_key=entry.app_key,
        accounting_entity_id=entry.accounting_entity_id,
        entry_date=entry.entry_date,
        description=entry.description,
        reference=entry.reference,
        source_module=entry.source_module,
        source_document_type=entry.source_document_type,
        source_document_id=entry.source_document_id,
        reversal_of_journal_id=entry.reversal_of_journal_id,
        idempotency_key=entry.idempotency_key,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
        created_by=entry.created_by,
        lines=[
            JournalLineResponse(
                id=line.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
            )
            for line in entry.lines
        ],
    )


async def enforce_accounting_route_tenant(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_accounting_entity_id: str | None = Header(default=None, alias="X-Accounting-Entity-ID"),
) -> AccountingContext:
    accounting_context = resolve_accounting_context(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        x_accounting_entity_id=x_accounting_entity_id,
    )
    tenant = await get_tenant(accounting_context.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if str(tenant.get("status") or "active").strip().lower() != "active":
        raise HTTPException(status_code=403, detail="Tenant is not active")
    try:
        require_module_access(
            module_key="accounting",
            organization_type=tenant.get("organization_type"),
            enabled_modules=tenant.get("enabled_modules") or [],
            app_key=accounting_context.app_key,
        )
    except ModuleAccessError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return accounting_context

@router.post("/accounts", response_model=AccountResponse)
async def create_account_endpoint(
    payload: AccountCreateRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        account = await create_account(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            code=payload.code,
            name=payload.name,
            account_type=payload.type,
            classification=payload.classification,
            is_cash_bank=payload.is_cash_bank,
            is_receivable=payload.is_receivable,
            is_payable=payload.is_payable,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Account code already exists for tenant")

    return AccountResponse(
        id=account.id,
        code=account.code,
        name=account.name,
        type=account.type,
        classification=account.classification,
        is_cash_bank=account.is_cash_bank,
        is_receivable=account.is_receivable,
        is_payable=account.is_payable,
    )


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts_endpoint(
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        accounts = await list_accounts(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
        )
    except (asyncio.TimeoutError, TimeoutError, SQLAlchemyTimeoutError):
        raise HTTPException(status_code=503, detail="Accounting service is temporarily busy. Please retry.")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Accounting database is temporarily unavailable. Please retry.")
    return [
        AccountResponse(
            id=a.id,
            code=a.code,
            name=a.name,
            type=a.type,
            classification=a.classification,
            is_cash_bank=a.is_cash_bank,
            is_receivable=a.is_receivable,
            is_payable=a.is_payable,
        )
        for a in accounts
    ]


@router.patch("/accounts/{code}", response_model=AccountResponse)
async def update_account_endpoint(
    code: str,
    payload: AccountUpdateRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        account = await update_account(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            code=code,
            name=payload.name or "",
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return AccountResponse(
        id=account.id,
        code=account.code,
        name=account.name,
        type=account.type,
        classification=account.classification,
        is_cash_bank=account.is_cash_bank,
        is_receivable=account.is_receivable,
        is_payable=account.is_payable,
    )


@router.post("/initialize-chart-of-accounts", response_model=ChartOfAccountsInitializeResponse)
async def initialize_chart_of_accounts_endpoint(
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        return await initialize_default_chart_of_accounts(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Chart of accounts was initialized by another request. Please refresh.")



@router.post("/coa/source-accounts/bulk", response_model=list[CoaSourceAccountResponse])
async def upsert_source_accounts_endpoint(
    payload: CoaSourceAccountBulkUpsertRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        rows = await upsert_source_accounts(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            items=payload.items,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate source account code for source system")

    return [CoaSourceAccountResponse(**row) for row in rows]


@router.get("/coa/source-accounts", response_model=list[CoaSourceAccountResponse])
async def list_source_accounts_endpoint(
    source_system: SourceSystem | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    rows = await list_source_accounts(
        session,
        app_key=accounting_context.app_key,
        tenant_id=accounting_context.tenant_id,
        accounting_entity_id=accounting_context.accounting_entity_id,
        source_system=source_system,
    )
    return [CoaSourceAccountResponse(**row) for row in rows]


@router.post("/coa/mappings/bulk", response_model=list[CoaMappingResponse])
async def upsert_coa_mappings_endpoint(
    payload: CoaMappingBulkUpsertRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        rows = await upsert_coa_mappings(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            mapped_by=accounting_context.user_id,
            items=payload.items,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [CoaMappingResponse(**row) for row in rows]


@router.get("/coa/mappings", response_model=list[CoaMappingResponse])
async def list_coa_mappings_endpoint(
    source_system: SourceSystem | None = Query(default=None),
    status: MappingStatus | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    rows = await list_coa_mappings(
        session,
        app_key=accounting_context.app_key,
        tenant_id=accounting_context.tenant_id,
        accounting_entity_id=accounting_context.accounting_entity_id,
        source_system=source_system,
        status=status,
    )
    return [CoaMappingResponse(**row) for row in rows]


@router.get("/coa/mapping-gaps", response_model=list[CoaMappingGapResponse])
async def coa_mapping_gaps_endpoint(
    source_system: SourceSystem = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    rows = await get_coa_mapping_gaps(
        session,
        app_key=accounting_context.app_key,
        tenant_id=accounting_context.tenant_id,
        accounting_entity_id=accounting_context.accounting_entity_id,
        source_system=source_system,
    )
    return [CoaMappingGapResponse(**row) for row in rows]



@router.get("/coa/onboarding-status", response_model=CoaOnboardingStatusResponse)
async def coa_onboarding_status_endpoint(
    source_system: SourceSystem = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    row = await get_coa_onboarding_status(
        session,
        app_key=accounting_context.app_key,
        tenant_id=accounting_context.tenant_id,
        accounting_entity_id=accounting_context.accounting_entity_id,
        source_system=source_system,
    )
    return CoaOnboardingStatusResponse(**row)


@router.post("/coa/mappings/approve", response_model=CoaMappingApproveResponse)
async def approve_coa_mappings_endpoint(
    payload: CoaMappingApproveRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        row = await approve_coa_mappings(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            source_system=payload.source_system,
            approved_by=accounting_context.user_id,
            source_account_codes=payload.source_account_codes,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return CoaMappingApproveResponse(**row)


@router.get("/journal", response_model=list[JournalEntryResponse])
async def list_journal_entries_endpoint(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        entries = await list_journal_entries(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return [_journal_entry_response(entry) for entry in entries]


@router.get("/journal/{journal_id}", response_model=JournalEntryResponse)
async def get_journal_entry_endpoint(
    journal_id: int,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        entry = await get_journal_entry_detail(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            journal_id=journal_id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return _journal_entry_response(entry)


@router.post("/journal/from-source", response_model=SourceJournalPostResponse)
async def post_source_journal_endpoint(
    payload: SourceJournalPostRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    try:
        entry, created, resolved_lines = await post_source_journal_entry(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            created_by=accounting_context.user_id,
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    return SourceJournalPostResponse(
        id=entry.id,
        tenant_id=accounting_context.tenant_id,
        created=created,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
        source_system=payload.source_system,
        resolved_lines=resolved_lines,
    )

@router.post("/journal", response_model=JournalPostResponse)
async def post_journal_endpoint(
    payload: JournalPostRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    try:
        entry, created = await post_journal_entry(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            created_by=accounting_context.user_id,
            payload=payload,
            idempotency_key=x_idempotency_key,
        )
    except AccountingIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    return JournalPostResponse(
        id=entry.id,
        tenant_id=accounting_context.tenant_id,
        created=created,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
    )


@router.post("/journal/{journal_id}/reverse", response_model=JournalReversalResponse)
async def reverse_journal_endpoint(
    journal_id: int,
    payload: JournalReversalRequest,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    try:
        entry, created = await reverse_journal_entry(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            created_by=accounting_context.user_id,
            journal_id=journal_id,
            reversal_date=payload.entry_date,
            reason=payload.reason,
            idempotency_key=x_idempotency_key,
        )
    except AccountingIdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    return JournalReversalResponse(
        id=entry.id,
        original_journal_id=journal_id,
        tenant_id=accounting_context.tenant_id,
        created=created,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
    )


@router.get("/ledger/{account_id}", response_model=list[LedgerLineResponse])
async def ledger_endpoint(
    account_id: int,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        _account, lines = await get_ledger_lines(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            account_id=account_id,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [LedgerLineResponse(**line) for line in lines]


@router.get("/reports/trial-balance", response_model=TrialBalanceResponse)
async def trial_balance_endpoint(
    as_of: date,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict | None = Depends(get_current_user),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, total_debit, total_credit = await get_trial_balance(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return TrialBalanceResponse(
        as_of=as_of,
        lines=lines,
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=total_debit == total_credit,
    )


@router.get("/reports/pnl", response_model=ProfitLossResponse)
async def pnl_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, income_total, expense_total, net_profit = await get_profit_loss(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ProfitLossResponse(
        from_date=from_date,
        to_date=to_date,
        income_total=income_total,
        expense_total=expense_total,
        net_profit=net_profit,
        lines=lines,
    )


@router.get("/reports/income-expenditure", response_model=ProfitLossResponse)
async def income_expenditure_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, income_total, expense_total, net_profit = await get_profit_loss(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ProfitLossResponse(
        from_date=from_date,
        to_date=to_date,
        income_total=income_total,
        expense_total=expense_total,
        net_profit=net_profit,
        lines=lines,
    )


@router.get("/reports/receipts-payments", response_model=ReceiptsPaymentsResponse)
async def receipts_payments_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, total_receipts, total_payments, net_receipts = await get_receipts_payments(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ReceiptsPaymentsResponse(
        from_date=from_date,
        to_date=to_date,
        total_receipts=total_receipts,
        total_payments=total_payments,
        net_receipts=net_receipts,
        lines=lines,
    )


@router.get("/reports/drilldown")
async def reports_drilldown_endpoint(
    from_date: date = Query(...),
    to_date: date = Query(...),
    level: str = Query(default="month", pattern="^(month|week|day|voucher)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    week_start: date | None = Query(default=None),
    day: date | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        return await get_journal_drilldown(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            from_date=from_date,
            to_date=to_date,
            level=level,
            month=month,
            week_start=week_start,
            day=day,
            limit=limit,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/reports/vouchers/{journal_id}")
async def reports_voucher_detail_endpoint(
    journal_id: int,
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        return await get_journal_voucher_detail(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            journal_id=journal_id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/reports/balance-sheet", response_model=BalanceSheetResponse)
async def balance_sheet_endpoint(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        assets, liabilities, equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return BalanceSheetResponse(
        as_of=as_of,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        balanced=total_assets == (total_liabilities + total_equity),
    )


@router.get("/reports/accounts-receivable", response_model=ARApResponse)
async def accounts_receivable_endpoint(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, total_balance = await get_accounts_receivable(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ARApResponse(as_of=as_of, total_balance=total_balance, lines=lines)


@router.get("/reports/accounts-payable", response_model=ARApResponse)
async def accounts_payable_endpoint(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    accounting_context: AccountingContext = Depends(enforce_accounting_route_tenant),
):
    try:
        lines, total_balance = await get_accounts_payable(
            session,
            app_key=accounting_context.app_key,
            tenant_id=accounting_context.tenant_id,
            accounting_entity_id=accounting_context.accounting_entity_id,
            as_of=as_of,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ARApResponse(as_of=as_of, total_balance=total_balance, lines=lines)












