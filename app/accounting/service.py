"""Accounting service facade.

Quarantined posting core (LARGE_FILE_MODULARIZATION_PLAN.md §6):
validate_journal_lines, cash guards, post_journal_entry, reverse_journal_entry,
post_source_journal_entry. Chart/COA-mapping/report implementations live in
sibling modules and are re-exported here for compatibility.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.decorators import async_audit_logger

_logger = logging.getLogger(__name__)

from app.accounting.common import (
    AccountingIdempotencyConflictError as AccountingIdempotencyConflictError,
    AccountingNotFoundError as AccountingNotFoundError,
    AccountingValidationError as AccountingValidationError,
    _accounting_scope as _accounting_scope,
    _money_float as _money_float,
    _q as _q,
)
from app.accounting.models import Account, CoaMapping, CoaSourceAccount, JournalEntry, JournalLine
from app.accounting.schemas import (
    JournalLineIn,
    JournalPostRequest,
    SourceJournalLineIn,
    SourceJournalPostRequest,
)


# ════════════════════════════════════════════════════════════════════════
# QUARANTINED posting core (LARGE_FILE_MODULARIZATION_PLAN.md §6)
# ════════════════════════════════════════════════════════════════════════

def _is_cash_account(account: Account) -> bool:
    if not bool(account.is_cash_bank) or str(account.type or "").lower() != "asset":
        return False
    name = str(account.name or "").lower()
    code = str(account.code or "").strip()
    return "cash" in name or code in {"11001", "11010", "11011", "1000", "1001", "1010", "1020"}


async def _cash_account_balance(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
) -> Decimal:
    stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalLine.account_id == account_id,
        )
    )
    debit_total, credit_total = (await session.execute(stmt)).one()
    return Decimal(debit_total or 0) - Decimal(credit_total or 0)


async def _validate_cash_accounts_do_not_go_negative(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    accounts_by_id: dict[int, Account],
    normalized_lines: list[tuple[int, Decimal, Decimal]],
) -> None:
    net_changes: dict[int, Decimal] = {}
    for account_id, debit, credit in normalized_lines:
        account = accounts_by_id.get(account_id)
        if account is None or not _is_cash_account(account):
            continue
        net_changes[account_id] = net_changes.get(account_id, Decimal("0")) + debit - credit

    for account_id, net_change in net_changes.items():
        if net_change >= 0:
            continue
        current_balance = await _cash_account_balance(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            account_id=account_id,
        )
        projected_balance = current_balance + net_change
        if projected_balance < 0:
            account = accounts_by_id[account_id]
            raise AccountingValidationError(
                f"Insufficient cash balance in {account.code or account.id} - {account.name}. "
                f"Available {current_balance.quantize(Decimal('0.01'))}, "
                f"payment {abs(net_change).quantize(Decimal('0.01'))}."
            )


async def validate_cash_balance_for_journal_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    normalized_lines: list[tuple[int, Decimal, Decimal]],
) -> None:
    account_ids = [line[0] for line in normalized_lines]
    if not account_ids:
        return
    account_stmt = select(Account).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        Account.id.in_(account_ids),
    )
    accounts_by_id = {int(account.id): account for account in (await session.execute(account_stmt)).scalars().all()}
    await _validate_cash_accounts_do_not_go_negative(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        accounts_by_id=accounts_by_id,
        normalized_lines=normalized_lines,
    )

def validate_journal_lines(lines: list[JournalLineIn]) -> tuple[Decimal, Decimal, list[tuple[int, Decimal, Decimal]]]:
    if len(lines) < 2:
        raise AccountingValidationError("At least two journal lines are required")

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    debit_lines = 0
    credit_lines = 0
    account_ids: set[int] = set()
    account_line_keys: set[tuple[int, str]] = set()
    normalized_lines: list[tuple[int, Decimal, Decimal]] = []

    for line in lines:
        debit = _q(Decimal(line.debit))
        credit = _q(Decimal(line.credit))

        if debit == 0 and credit == 0:
            raise AccountingValidationError("Each journal line must have debit or credit")
        if debit > 0 and credit > 0:
            raise AccountingValidationError("A journal line cannot have both debit and credit")

        if debit > 0:
            debit_lines += 1
        if credit > 0:
            credit_lines += 1

        total_debit += debit
        total_credit += credit
        account_ids.add(line.account_id)
        account_line_keys.add((line.account_id, str(getattr(line, "cost_center_id", None) or "")))
        normalized_lines.append((line.account_id, debit, credit))

    total_debit = _q(total_debit)
    total_credit = _q(total_credit)

    if debit_lines == 0 or credit_lines == 0:
        raise AccountingValidationError("Journal entry must include at least one debit line and one credit line")

    if len(account_line_keys) < 2:
        raise AccountingValidationError("Journal entry must impact at least two distinct accounts")

    if total_debit <= 0 or total_credit <= 0:
        raise AccountingValidationError("Total debit and total credit must be greater than zero")

    if total_debit != total_credit:
        raise AccountingValidationError("Debits and credits must be equal")

    return total_debit, total_credit, normalized_lines


def _journal_line_signature(lines: list[tuple[int, Decimal, Decimal]]) -> list[tuple[int, Decimal, Decimal]]:
    return sorted((account_id, _q(debit), _q(credit)) for account_id, debit, credit in lines)


def _existing_journal_signature(entry: JournalEntry) -> list[tuple[int, Decimal, Decimal]]:
    return _journal_line_signature([(line.account_id, Decimal(line.debit), Decimal(line.credit)) for line in entry.lines])


def _requested_journal_matches_existing(
    *,
    existing: JournalEntry,
    payload: JournalPostRequest,
    total_debit: Decimal,
    total_credit: Decimal,
    normalized_lines: list[tuple[int, Decimal, Decimal]],
    reversal_of_journal_id: int | None,
) -> bool:
    return (
        existing.entry_date == payload.entry_date
        and existing.description == payload.description
        and existing.reference == payload.reference
        and existing.source_module == payload.source_module
        and existing.source_document_type == payload.source_document_type
        and existing.source_document_id == payload.source_document_id
        and existing.reversal_of_journal_id == reversal_of_journal_id
        and _q(Decimal(existing.total_debit)) == total_debit
        and _q(Decimal(existing.total_credit)) == total_credit
        and _existing_journal_signature(existing) == _journal_line_signature(normalized_lines)
    )


def validate_source_journal_lines(lines: list[SourceJournalLineIn]) -> tuple[Decimal, Decimal, list[tuple[str, Decimal, Decimal]]]:
    if len(lines) < 2:
        raise AccountingValidationError("At least two source journal lines are required")

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    debit_lines = 0
    credit_lines = 0
    source_account_codes: set[str] = set()
    normalized_lines: list[tuple[str, Decimal, Decimal]] = []

    for line in lines:
        source_account_code = line.source_account_code.strip()
        debit = _q(Decimal(line.debit))
        credit = _q(Decimal(line.credit))

        if not source_account_code:
            raise AccountingValidationError("source_account_code is required for each source journal line")
        if debit == 0 and credit == 0:
            raise AccountingValidationError("Each source journal line must have debit or credit")
        if debit > 0 and credit > 0:
            raise AccountingValidationError("A source journal line cannot have both debit and credit")

        if debit > 0:
            debit_lines += 1
        if credit > 0:
            credit_lines += 1

        total_debit += debit
        total_credit += credit
        source_account_codes.add(source_account_code)
        normalized_lines.append((source_account_code, debit, credit))

    total_debit = _q(total_debit)
    total_credit = _q(total_credit)

    if debit_lines == 0 or credit_lines == 0:
        raise AccountingValidationError("Source journal entry must include at least one debit line and one credit line")
    if len(source_account_codes) < 2:
        raise AccountingValidationError("Source journal entry must impact at least two distinct source accounts")
    if total_debit <= 0 or total_credit <= 0:
        raise AccountingValidationError("Total debit and total credit must be greater than zero")
    if total_debit != total_credit:
        raise AccountingValidationError("Debits and credits must be equal")

    return total_debit, total_credit, normalized_lines

async def post_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    created_by: str,
    payload: JournalPostRequest,
    idempotency_key: str | None,
    reversal_of_journal_id: int | None = None,
) -> tuple[JournalEntry, bool]:
    total_debit, total_credit, normalized_lines = validate_journal_lines(payload.lines)

    if idempotency_key:
        existing_stmt = (
            select(JournalEntry)
            .where(
                *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
                JournalEntry.idempotency_key == idempotency_key,
            )
            .options(selectinload(JournalEntry.lines))
        )
        existing = (await session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            if not _requested_journal_matches_existing(
                existing=existing,
                payload=payload,
                total_debit=total_debit,
                total_credit=total_credit,
                normalized_lines=normalized_lines,
                reversal_of_journal_id=reversal_of_journal_id,
            ):
                raise AccountingIdempotencyConflictError("Idempotency key already used for a different journal payload")
            return existing, False

    account_ids = [line[0] for line in normalized_lines]
    account_stmt = select(Account).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        Account.id.in_(account_ids),
    )
    accounts_by_id = {int(account.id): account for account in (await session.execute(account_stmt)).scalars().all()}
    available_account_ids = set(accounts_by_id)
    missing_account_ids = sorted(set(account_ids) - available_account_ids)
    if missing_account_ids:
        raise AccountingNotFoundError(f"Accounts not found for tenant: {missing_account_ids}")
    await validate_cash_balance_for_journal_lines(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        normalized_lines=normalized_lines,
    )

    # Tenant-isolation guard: any cost-centre tag on a line must belong to THIS
    # tenant+entity. This is the single ledger chokepoint, so no posting path can
    # smuggle in another tenant's cost centre. Untagged postings skip it entirely.
    cost_centre_ids = {
        cc for cc in (getattr(line, "cost_center_id", None) for line in payload.lines) if cc
    }
    if cost_centre_ids:
        from app.modules.business.dimensions import validate_ledger_cost_centre_ids

        await validate_ledger_cost_centre_ids(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            cost_centre_ids=cost_centre_ids,
        )

    journal_entry = JournalEntry(
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        entry_date=payload.entry_date,
        description=payload.description,
        reference=payload.reference,
        source_module=payload.source_module,
        source_document_type=payload.source_document_type,
        source_document_id=payload.source_document_id,
        reversal_of_journal_id=reversal_of_journal_id,
        idempotency_key=idempotency_key,
        total_debit=total_debit,
        total_credit=total_credit,
        created_by=created_by,
    )
    session.add(journal_entry)

    # normalized_lines preserves payload order, so zip to carry the sub-ledger tags.
    for (account_id, debit, credit), source_line in zip(normalized_lines, payload.lines):
        journal_entry.lines.append(
            JournalLine(
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
                account_id=account_id,
                debit=debit,
                credit=credit,
                party_id=getattr(source_line, "party_id", None),
                cost_center_id=getattr(source_line, "cost_center_id", None),
            )
        )

    await session.commit()
    await session.refresh(journal_entry)
    return journal_entry, True


async def reverse_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: str,
    journal_id: int,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    created_by: str,
    reversal_date: date | None = None,
    reason: str | None = None,
    idempotency_key: str | None = None,
) -> tuple[JournalEntry, bool]:
    reversal_key = (idempotency_key or f"journal-reversal:{journal_id}").strip()[:120]
    if not reversal_key:
        raise AccountingValidationError("Reversal idempotency key is required")

    existing_stmt = (
        select(JournalEntry)
        .where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.idempotency_key == reversal_key,
        )
        .options(selectinload(JournalEntry.lines))
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        return existing, False

    original_stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.id == journal_id,
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        )
        .options(selectinload(JournalEntry.lines))
    )
    original = (await session.execute(original_stmt)).scalar_one_or_none()
    if original is None:
        raise AccountingNotFoundError(f"Journal entry {journal_id} not found")
    if len(original.lines) < 2:
        raise AccountingValidationError("Original journal entry does not have enough lines to reverse")

    reason_text = (reason or "Reversal").strip() or "Reversal"
    reference = f"REV-{original.id}"
    if original.reference:
        reference = f"{reference}-{original.reference}"[:120]

    reversal_lines = [
        JournalLineIn(
            account_id=line.account_id,
            debit=line.credit,
            credit=line.debit,
            party_id=line.party_id,
            cost_center_id=line.cost_center_id,
        )
        for line in original.lines
    ]
    reversal_payload = JournalPostRequest(
        entry_date=reversal_date or date.today(),
        description=f"Reversal of journal entry #{original.id}: {reason_text}",
        reference=reference,
        source_module="accounting",
        source_document_type="journal_reversal",
        source_document_id=str(original.id),
        lines=reversal_lines,
    )
    return await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=reversal_payload,
        idempotency_key=reversal_key,
        reversal_of_journal_id=original.id,
    )


def _source_idempotency_key(source_system: str, idempotency_key: str | None) -> str | None:
    if not idempotency_key:
        return None
    normalized = f"{source_system}:{idempotency_key.strip()}"
    return normalized[:120]

async def post_source_journal_entry(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    created_by: str,
    payload: SourceJournalPostRequest,
    idempotency_key: str | None,
) -> tuple[JournalEntry, bool, list[dict]]:
    _total_debit, _total_credit, normalized_lines = validate_source_journal_lines(payload.lines)

    source_account_codes = {code for code, _debit, _credit in normalized_lines}
    source_accounts_stmt = select(CoaSourceAccount).where(
        *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaSourceAccount.source_system == payload.source_system,
        CoaSourceAccount.source_account_code.in_(source_account_codes),
        CoaSourceAccount.is_active.is_(True),
    )
    source_accounts = list((await session.execute(source_accounts_stmt)).scalars().all())
    source_by_code = {source_account.source_account_code: source_account for source_account in source_accounts}

    missing_source_codes = sorted(source_account_codes - set(source_by_code.keys()))
    if missing_source_codes:
        raise AccountingNotFoundError(f"Source accounts not found for tenant/system: {missing_source_codes}")

    source_ids = [source_account.id for source_account in source_accounts]
    mapping_stmt = select(CoaMapping).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.status == "active",
        CoaMapping.source_account_id.in_(source_ids),
    )
    mappings = list((await session.execute(mapping_stmt)).scalars().all())
    mapping_by_source_id = {mapping.source_account_id: mapping for mapping in mappings}

    missing_mapping_codes = sorted(
        source_account.source_account_code
        for source_account in source_accounts
        if source_account.id not in mapping_by_source_id
    )
    if missing_mapping_codes:
        raise AccountingValidationError(f"Active COA mapping missing for source accounts: {missing_mapping_codes}")

    canonical_lines: list[JournalLineIn] = []
    resolved_lines: list[dict] = []

    for source_account_code, debit, credit in normalized_lines:
        source_account = source_by_code[source_account_code]
        mapping = mapping_by_source_id[source_account.id]

        canonical_lines.append(
            JournalLineIn(
                account_id=mapping.canonical_account_id,
                debit=debit,
                credit=credit,
            )
        )
        resolved_lines.append(
            {
                "source_account_code": source_account_code,
                "canonical_account_id": mapping.canonical_account_id,
                "debit": debit,
                "credit": credit,
            }
        )

    canonical_payload = JournalPostRequest(
        entry_date=payload.entry_date,
        description=payload.description,
        reference=payload.reference,
        source_module=payload.source_system,
        source_document_type=payload.source_document_type,
        source_document_id=payload.source_document_id,
        lines=canonical_lines,
    )

    entry, created = await post_journal_entry(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=canonical_payload,
        idempotency_key=_source_idempotency_key(payload.source_system, idempotency_key),
    )

    return entry, created, resolved_lines


# Chart of accounts (moved to chart.py)
from app.accounting.chart import (  # noqa: E402
    DEFAULT_BUSINESS_CHART_OF_ACCOUNTS as DEFAULT_BUSINESS_CHART_OF_ACCOUNTS,
    DEFAULT_HOUSING_CHART_OF_ACCOUNTS as DEFAULT_HOUSING_CHART_OF_ACCOUNTS,
    create_account as create_account,
    get_default_chart_of_accounts as get_default_chart_of_accounts,
    initialize_default_chart_of_accounts as initialize_default_chart_of_accounts,
    list_accounts as list_accounts,
    update_account as update_account,
)

# COA mapping / onboarding (moved to coa_mapping.py)
from app.accounting.coa_mapping import (  # noqa: E402
    approve_coa_mappings as approve_coa_mappings,
    get_coa_mapping_gaps as get_coa_mapping_gaps,
    get_coa_onboarding_status as get_coa_onboarding_status,
    list_coa_mappings as list_coa_mappings,
    list_source_accounts as list_source_accounts,
    suggest_canonical_account as suggest_canonical_account,
    upsert_coa_mappings as upsert_coa_mappings,
    upsert_source_accounts as upsert_source_accounts,
)

# Reports / ledger reads (moved to reports/)
from app.accounting.reports import (  # noqa: E402
    _financial_year_start as _financial_year_start,
    _gl_sums_by_account as _gl_sums_by_account,
    _net_profit_from_rows as _net_profit_from_rows,
    get_accounts_payable as get_accounts_payable,
    get_accounts_receivable as get_accounts_receivable,
    get_balance_sheet as get_balance_sheet,
    get_business_dashboard as get_business_dashboard,
    get_cost_centre_account_actuals as get_cost_centre_account_actuals,
    get_cost_centre_ledger_pl as get_cost_centre_ledger_pl,
    get_journal_drilldown as get_journal_drilldown,
    get_journal_entry_detail as get_journal_entry_detail,
    get_journal_voucher_detail as get_journal_voucher_detail,
    get_ledger_lines as get_ledger_lines,
    get_party_ledger_lines as get_party_ledger_lines,
    get_party_outstanding as get_party_outstanding,
    get_party_wise_balances as get_party_wise_balances,
    get_profit_loss as get_profit_loss,
    get_receipts_payments as get_receipts_payments,
    get_trial_balance as get_trial_balance,
    list_journal_entries as list_journal_entries,
)
