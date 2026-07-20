"""Bank reconciliation and bank/cash-book routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. Pure move: handlers still call the same
``bank_recon`` / ``banking_books`` service modules, so ledger posting behaviour
is unaffected (match/unmatch are metadata-only; statement-voucher posts only
through the normal typed-voucher review path). The shared ``_created_by`` helper
stays in router.py.

Named ``bank_recon_routes`` (not ``bank_recon``) to avoid shadowing the existing
``app.modules.business.bank_recon`` service module.
"""
from datetime import date

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import bank_recon
from app.modules.business import banking_books
from app.modules.business.schemas import (
    BankStatementVoucherRequest,
    BankStatementVoucherResponse,
)
from app.modules.business.router import _created_by, router


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
