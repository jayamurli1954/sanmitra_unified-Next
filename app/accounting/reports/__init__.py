"""Accounting report and ledger read APIs.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Posting core remains in app.accounting.service.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.accounting.common import (
    AccountingNotFoundError,
    AccountingValidationError,
    _accounting_scope,
    _money_float,
    _q,
)
from app.accounting.models import Account, JournalEntry, JournalLine

_logger = logging.getLogger(__name__)

async def get_ledger_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    account_id: int,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> tuple[Account, list[dict]]:
    account = (
        await session.execute(
            select(Account).where(
                Account.id == account_id,
                *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            )
        )
    ).scalar_one_or_none()
    if account is None:
        raise AccountingNotFoundError("Account not found")

    stmt = (
        select(
            JournalLine.id.label("line_id"),
            JournalLine.journal_id,
            JournalLine.debit,
            JournalLine.credit,
            JournalEntry.entry_date,
            JournalEntry.reference,
            JournalEntry.description,
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalLine.account_id == account_id,
        )
        .order_by(JournalEntry.entry_date.asc(), JournalLine.id.asc())
    )
    rows = (await session.execute(stmt)).all()

    running = Decimal("0")
    output: list[dict] = []
    for row in rows:
        debit = Decimal(row.debit)
        credit = Decimal(row.credit)
        running += debit - credit
        entry_date_val = row.entry_date
        entry_date_str = (
            entry_date_val.isoformat()
            if hasattr(entry_date_val, "isoformat")
            else str(entry_date_val)[:10]
            if entry_date_val is not None
            else None
        )
        output.append(
            {
                "line_id": row.line_id,
                "journal_id": row.journal_id,
                "entry_date": entry_date_str,
                "reference": row.reference,
                "description": row.description,
                "debit": debit,
                "credit": credit,
                "running_balance": running,
            }
        )

    return account, output


async def get_trial_balance(
    session: AsyncSession,
    *,
    tenant_id: str,
    as_of: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> tuple[list[dict], Decimal, Decimal]:
    stmt = (
        select(
            Account.id.label("account_id"),
            Account.code.label("account_code"),
            Account.name.label("account_name"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .where(
            *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.entry_date <= as_of,
        )
        .group_by(Account.id, Account.code, Account.name)
        .order_by(Account.name.asc())
    )

    rows = (await session.execute(stmt)).all()

    lines: list[dict] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for row in rows:
        debit_total = _q(Decimal(row.debit_total))
        credit_total = _q(Decimal(row.credit_total))
        total_debit += debit_total
        total_credit += credit_total
        lines.append(
            {
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "debit_total": debit_total,
                "credit_total": credit_total,
                "net_balance": _q(debit_total - credit_total),
            }
        )

    return lines, _q(total_debit), _q(total_credit)


def _net_balance(account_type: str, debit_total: Decimal, credit_total: Decimal) -> Decimal:
    if account_type in {"asset", "expense"}:
        return _q(debit_total - credit_total)
    return _q(credit_total - debit_total)


def _net_profit_from_rows(rows) -> Decimal:
    income_total = Decimal("0")
    expense_total = Decimal("0")

    for row in rows:
        debit_total = _q(Decimal(row.debit_total))
        credit_total = _q(Decimal(row.credit_total))

        if row.account_type == "income":
            income_total += _q(credit_total - debit_total)
        elif row.account_type == "expense":
            expense_total += _q(debit_total - credit_total)

    return _q(income_total - expense_total)


def _validate_report_date_range(*, from_date: date | None = None, to_date: date | None = None) -> None:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise AccountingValidationError("from_date cannot be greater than to_date")


async def _gl_sums_by_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    from_date: date | None = None,
    to_date: date | None = None,
    as_of: date | None = None,
    account_types: tuple[str, ...] | None = None,
    only_cash_bank: bool = False,
    only_receivable: bool = False,
    only_payable: bool = False,
):
    _validate_report_date_range(from_date=from_date, to_date=to_date)

    conditions = [
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
    ]

    if from_date is not None:
        conditions.append(JournalEntry.entry_date >= from_date)
    if to_date is not None:
        conditions.append(JournalEntry.entry_date <= to_date)
    if as_of is not None:
        conditions.append(JournalEntry.entry_date <= as_of)

    if account_types is not None:
        conditions.append(Account.type.in_(account_types))
    if only_cash_bank:
        conditions.append(Account.is_cash_bank.is_(True))
    if only_receivable:
        conditions.append(Account.is_receivable.is_(True))
    if only_payable:
        conditions.append(Account.is_payable.is_(True))

    stmt = (
        select(
            Account.id.label("account_id"),
            Account.code.label("account_code"),
            Account.name.label("account_name"),
            Account.type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .where(and_(*conditions))
        .group_by(Account.id, Account.code, Account.name, Account.type)
        .order_by(Account.name.asc())
    )

    return (await session.execute(stmt)).all()


async def get_profit_loss(
    session: AsyncSession,
    *,
    tenant_id: str,
    from_date: date,
    to_date: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    rows = await _gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        from_date=from_date,
        to_date=to_date,
        account_types=("income", "expense"),
    )

    lines: list[dict] = []
    income_total = Decimal("0")
    expense_total = Decimal("0")

    for row in rows:
        debit_total = _q(Decimal(row.debit_total))
        credit_total = _q(Decimal(row.credit_total))

        if row.account_type == "income":
            net_amount = _q(credit_total - debit_total)
            income_total += net_amount
        else:
            net_amount = _q(debit_total - credit_total)
            expense_total += net_amount

        lines.append(
            {
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "account_type": row.account_type,
                "debit_total": debit_total,
                "credit_total": credit_total,
                "net_amount": net_amount,
            }
        )

    income_total = _q(income_total)
    expense_total = _q(expense_total)
    net_profit = _q(income_total - expense_total)

    return lines, income_total, expense_total, net_profit


async def get_receipts_payments(
    session: AsyncSession,
    *,
    tenant_id: str,
    from_date: date,
    to_date: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    rows = await _gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        from_date=from_date,
        to_date=to_date,
        only_cash_bank=True,
    )

    lines: list[dict] = []
    total_receipts = Decimal("0")
    total_payments = Decimal("0")

    for row in rows:
        receipts = _q(Decimal(row.debit_total))
        payments = _q(Decimal(row.credit_total))
        net_receipts = _q(receipts - payments)

        total_receipts += receipts
        total_payments += payments

        lines.append(
            {
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "receipts": receipts,
                "payments": payments,
                "net_receipts": net_receipts,
            }
        )

    return lines, _q(total_receipts), _q(total_payments), _q(total_receipts - total_payments)


def _journal_voucher_row(entry: JournalEntry) -> dict:
    return {
        "id": entry.id,
        "entry_date": entry.entry_date.isoformat(),
        "description": entry.description,
        "reference": entry.reference,
        "idempotency_key": entry.idempotency_key,
        "reversal_of_journal_id": entry.reversal_of_journal_id,
        "total_debit": _money_float(entry.total_debit),
        "total_credit": _money_float(entry.total_credit),
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def _journal_drilldown_summary(rows: list[dict]) -> dict:
    return {
        "voucher_count": len(rows),
        "total_debit": _money_float(sum((Decimal(str(row.get("total_debit") or 0)) for row in rows), Decimal("0"))),
        "total_credit": _money_float(sum((Decimal(str(row.get("total_credit") or 0)) for row in rows), Decimal("0"))),
        "last_voucher": rows[0] if rows else None,
    }


def _journal_week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


async def get_journal_drilldown(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    from_date: date,
    to_date: date,
    level: str = "month",
    month: str | None = None,
    week_start: date | None = None,
    day: date | None = None,
    limit: int = 1000,
) -> dict:
    normalized_level = str(level or "month").strip().lower()
    if normalized_level not in {"month", "week", "day", "voucher"}:
        raise AccountingValidationError("level must be month, week, day, or voucher")
    _validate_report_date_range(from_date=from_date, to_date=to_date)

    stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.app_key == app_key,
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.accounting_entity_id == accounting_entity_id,
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
        )
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .limit(limit)
    )
    rows = [_journal_voucher_row(entry) for entry in (await session.execute(stmt)).scalars().all()]

    if month:
        rows = [row for row in rows if str(row["entry_date"])[:7] == month]
    if week_start:
        week_end = week_start + timedelta(days=6)
        rows = [row for row in rows if week_start.isoformat() <= str(row["entry_date"])[:10] <= week_end.isoformat()]
    if day:
        rows = [row for row in rows if str(row["entry_date"])[:10] == day.isoformat()]

    filters = {
        "month": month,
        "week_start": week_start.isoformat() if week_start else None,
        "day": day.isoformat() if day else None,
    }
    if normalized_level == "voucher":
        return {
            "level": "voucher",
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "filters": filters,
            "summary": _journal_drilldown_summary(rows),
            "items": rows,
        }

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        entry_date = date.fromisoformat(str(row["entry_date"])[:10])
        if normalized_level == "month":
            key = entry_date.strftime("%Y-%m")
        elif normalized_level == "week":
            key = _journal_week_start(entry_date).isoformat()
        else:
            key = entry_date.isoformat()
        grouped.setdefault(key, []).append(row)

    items: list[dict] = []
    for key, group_rows in grouped.items():
        if normalized_level == "month":
            item = {"month": key, "label": date.fromisoformat(f"{key}-01").strftime("%B %Y")}
        elif normalized_level == "week":
            start = date.fromisoformat(key)
            item = {"week_start": key, "week_end": (start + timedelta(days=6)).isoformat()}
        else:
            item = {"day": key}
        item.update(_journal_drilldown_summary(group_rows))
        items.append(item)

    items.sort(key=lambda item: item.get("month") or item.get("week_start") or item.get("day") or "", reverse=True)
    return {
        "level": normalized_level,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "filters": filters,
        "summary": _journal_drilldown_summary(rows),
        "items": items,
    }


async def get_journal_voucher_detail(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    journal_id: int,
) -> dict:
    entry = (
        await session.execute(
            select(JournalEntry).where(
                JournalEntry.id == journal_id,
                JournalEntry.app_key == app_key,
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.accounting_entity_id == accounting_entity_id,
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise AccountingNotFoundError("Journal voucher not found")

    line_rows = (
        await session.execute(
            select(JournalLine, Account)
            .join(
                Account,
                and_(
                    Account.id == JournalLine.account_id,
                    Account.app_key == app_key,
                    Account.tenant_id == tenant_id,
                    Account.accounting_entity_id == accounting_entity_id,
                ),
            )
            .where(
                JournalLine.journal_id == entry.id,
                JournalLine.app_key == app_key,
                JournalLine.tenant_id == tenant_id,
                JournalLine.accounting_entity_id == accounting_entity_id,
            )
            .order_by(JournalLine.id.asc())
        )
    ).all()
    lines = [
        {
            "line_id": line.id,
            "account_id": account.id,
            "account_code": account.code,
            "account_name": account.name,
            "account_type": account.type,
            "debit": _money_float(line.debit),
            "credit": _money_float(line.credit),
        }
        for line, account in line_rows
    ]
    reversal_ids = (
        await session.execute(
            select(JournalEntry.id)
            .where(
                JournalEntry.app_key == app_key,
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.accounting_entity_id == accounting_entity_id,
                JournalEntry.reversal_of_journal_id == entry.id,
            )
            .order_by(JournalEntry.id.asc())
        )
    ).scalars().all()
    return {
        **_journal_voucher_row(entry),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "reversed_by_journal_ids": [int(value) for value in reversal_ids],
        "lines": lines,
    }


async def get_balance_sheet(
    session: AsyncSession,
    *,
    tenant_id: str,
    as_of: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    # Resolve via facade so tests can monkeypatch accounting.service._gl_sums_by_account.
    from app.accounting import service as accounting_service

    rows = await accounting_service._gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        as_of=as_of,
        account_types=("asset", "liability", "equity"),
    )

    assets: list[dict] = []
    liabilities: list[dict] = []
    equity: list[dict] = []

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for row in rows:
        debit_total = _q(Decimal(row.debit_total))
        credit_total = _q(Decimal(row.credit_total))
        balance = _net_balance(row.account_type, debit_total, credit_total)

        line = {
            "account_id": row.account_id,
            "account_code": row.account_code,
            "account_name": row.account_name,
            "balance": balance,
        }

        if row.account_type == "asset":
            assets.append(line)
            total_assets += balance
        elif row.account_type == "liability":
            liabilities.append(line)
            total_liabilities += balance
        else:
            equity.append(line)
            total_equity += balance

    pnl_rows = await accounting_service._gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        as_of=as_of,
        account_types=("income", "expense"),
    )
    unclosed_earnings = _net_profit_from_rows(pnl_rows)
    if unclosed_earnings != Decimal("0.00"):
        equity.append(
            {
                "account_id": 0,
                "account_name": "Current Period Earnings (System)",
                "balance": unclosed_earnings,
            }
        )
        total_equity += unclosed_earnings

    total_assets = _q(total_assets)
    total_liabilities = _q(total_liabilities)
    total_equity = _q(total_equity)

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity


async def get_accounts_receivable(
    session: AsyncSession,
    *,
    tenant_id: str,
    as_of: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    rows = await _gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        as_of=as_of,
        only_receivable=True,
    )

    lines: list[dict] = []
    total_balance = Decimal("0")

    for row in rows:
        balance = _net_balance(row.account_type, _q(Decimal(row.debit_total)), _q(Decimal(row.credit_total)))
        total_balance += balance
        lines.append(
            {
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "balance": balance,
            }
        )

    return lines, _q(total_balance)


async def get_accounts_payable(
    session: AsyncSession,
    *,
    tenant_id: str,
    as_of: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    rows = await _gl_sums_by_account(
        session,
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        as_of=as_of,
        only_payable=True,
    )

    lines: list[dict] = []
    total_balance = Decimal("0")

    for row in rows:
        balance = _net_balance(row.account_type, _q(Decimal(row.debit_total)), _q(Decimal(row.credit_total)))
        total_balance += balance
        lines.append(
            {
                "account_id": row.account_id,
                "account_code": row.account_code,
                "account_name": row.account_name,
                "balance": balance,
            }
        )

    return lines, _q(total_balance)


async def get_party_wise_balances(
    session: AsyncSession,
    *,
    tenant_id: str,
    as_of: date,
    kind: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
):
    """Party-wise net balances over receivable (or payable) accounts, grouped by the
    journal-line party sub-ledger. Lines with no party_id collapse into a single
    NULL bucket so the grand total equals the account-level total (ties to the TB)."""
    if kind not in ("receivable", "payable"):
        raise AccountingValidationError("kind must be 'receivable' or 'payable'")

    conditions = [
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        JournalEntry.entry_date <= as_of,
        (Account.is_receivable.is_(True) if kind == "receivable" else Account.is_payable.is_(True)),
    ]
    stmt = (
        select(
            JournalLine.party_id.label("party_id"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(*conditions))
        .group_by(JournalLine.party_id)
    )
    try:
        rows = (await session.execute(stmt)).all()
    except SQLAlchemyError as exc:
        # Degrade gracefully if the party_id sub-ledger column is missing (DB migrations
        # behind). Return an empty party-wise view instead of a 500.
        await session.rollback()
        _logger.warning("Party-wise balances unavailable (run 'alembic upgrade head'?): %s", exc)
        return [], Decimal("0.00")

    lines: list[dict] = []
    total_balance = Decimal("0")
    for row in rows:
        debit = _q(Decimal(row.debit_total))
        credit = _q(Decimal(row.credit_total))
        balance = _q(debit - credit) if kind == "receivable" else _q(credit - debit)
        total_balance += balance
        lines.append({"party_id": row.party_id, "balance": balance})

    return lines, _q(total_balance)


async def get_cost_centre_ledger_pl(
    session: AsyncSession,
    *,
    tenant_id: str,
    from_date: date,
    to_date: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> dict:
    """Income / expense / net per cost centre, straight from the POSTED ledger
    (the enterprise upgrade over the document-tag report). Only P&L accounts
    (Account.type in income/expense) over the period count. Lines with no
    cost_center_id collapse into a single 'untagged' bucket so the totals tie to
    the period P&L. Strictly scoped by app_key + tenant_id + accounting_entity_id
    on every table — a cost centre can never aggregate across tenants/entities."""
    conditions = [
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        JournalEntry.entry_date >= from_date,
        JournalEntry.entry_date <= to_date,
        Account.type.in_(("income", "expense")),
    ]
    stmt = (
        select(
            JournalLine.cost_center_id.label("cost_center_id"),
            Account.type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(*conditions))
        .group_by(JournalLine.cost_center_id, Account.type)
    )
    try:
        rows = (await session.execute(stmt)).all()
    except SQLAlchemyError as exc:
        # Degrade gracefully if the cost_center_id column is missing (migrations behind).
        await session.rollback()
        _logger.warning("Cost-centre P&L unavailable (run 'alembic upgrade head'?): %s", exc)
        rows = []

    buckets: dict[str | None, dict] = {}

    def _bucket(cc_id: str | None) -> dict:
        return buckets.setdefault(cc_id, {"income": Decimal("0.00"), "expense": Decimal("0.00")})

    for row in rows:
        debit = _q(Decimal(row.debit_total))
        credit = _q(Decimal(row.credit_total))
        if row.account_type == "income":
            _bucket(row.cost_center_id)["income"] += _q(credit - debit)
        else:  # expense
            _bucket(row.cost_center_id)["expense"] += _q(debit - credit)

    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        # cost_centre_id -> {income, expense} (names resolved by the caller from
        # this tenant's masters; None key is the untagged bucket).
        "buckets": {(k or "__untagged__"): v for k, v in buckets.items()},
    }


async def get_cost_centre_account_actuals(
    session: AsyncSession,
    *,
    tenant_id: str,
    cost_centre_id: str,
    from_date: date,
    to_date: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> dict[int, dict]:
    """Per-account actuals for ONE cost centre over a period — the actual side of
    budget-vs-actual. Returns {account_id: {code, name, type, actual}}. 'actual'
    is the natural-sign amount (income: credit−debit; expense: debit−credit).
    Strictly scoped on every table and filtered to this cost centre, so figures
    can never bleed across tenants/entities."""
    conditions = [
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        JournalLine.cost_center_id == cost_centre_id,
        JournalEntry.entry_date >= from_date,
        JournalEntry.entry_date <= to_date,
    ]
    stmt = (
        select(
            Account.id.label("account_id"),
            Account.code.label("code"),
            Account.name.label("name"),
            Account.type.label("account_type"),
            func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(*conditions))
        .group_by(Account.id, Account.code, Account.name, Account.type)
    )
    try:
        rows = (await session.execute(stmt)).all()
    except SQLAlchemyError as exc:
        await session.rollback()
        _logger.warning("Cost-centre actuals unavailable (run 'alembic upgrade head'?): %s", exc)
        rows = []

    out: dict[int, dict] = {}
    for row in rows:
        debit = _q(Decimal(row.debit_total))
        credit = _q(Decimal(row.credit_total))
        actual = _q(credit - debit) if row.account_type == "income" else _q(debit - credit)
        out[int(row.account_id)] = {
            "code": row.code, "name": row.name, "type": row.account_type, "actual": actual,
        }
    return out


async def get_party_ledger_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    party_id: str,
    kind: str,
    from_date: date,
    to_date: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> tuple[Decimal, list[dict]]:
    """(opening_balance, transactions) for one party's receivable or payable
    sub-ledger over a period — the data behind a statement of account.

    Opening balance is the party's net balance before `from_date` in the
    natural sign for the side (receivable: debit−credit; payable: credit−debit).
    """
    flag = Account.is_receivable if kind == "receivable" else Account.is_payable
    base_conditions = [
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        flag.is_(True),
        JournalLine.party_id == party_id,
    ]

    opening_stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(*base_conditions, JournalEntry.entry_date < from_date))
    )
    lines_stmt = (
        select(
            JournalLine.journal_id,
            JournalLine.debit,
            JournalLine.credit,
            JournalEntry.entry_date,
            JournalEntry.reference,
            JournalEntry.description,
            JournalEntry.source_document_type,
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(and_(*base_conditions, JournalEntry.entry_date >= from_date, JournalEntry.entry_date <= to_date))
        .order_by(JournalEntry.entry_date.asc(), JournalLine.id.asc())
    )
    try:
        debit_total, credit_total = (await session.execute(opening_stmt)).one()
        rows = (await session.execute(lines_stmt)).all()
    except SQLAlchemyError as exc:
        await session.rollback()
        _logger.warning("Party statement unavailable (run 'alembic upgrade head'?): %s", exc)
        return Decimal("0.00"), []

    opening_debit = _q(Decimal(debit_total))
    opening_credit = _q(Decimal(credit_total))
    opening = _q(opening_debit - opening_credit) if kind == "receivable" else _q(opening_credit - opening_debit)

    transactions: list[dict] = []
    for row in rows:
        entry_date_val = row.entry_date
        entry_date_str = (
            entry_date_val.isoformat() if hasattr(entry_date_val, "isoformat") else str(entry_date_val)[:10]
        )
        transactions.append({
            "journal_id": row.journal_id,
            "entry_date": entry_date_str,
            "reference": row.reference,
            "description": row.description,
            "document_type": row.source_document_type,
            "debit": _q(Decimal(row.debit)),
            "credit": _q(Decimal(row.credit)),
        })
    return opening, transactions


async def get_party_outstanding(
    session: AsyncSession,
    *,
    tenant_id: str,
    party_id: str,
    as_of: date,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> dict:
    """Net receivable and payable outstanding for a single party as of a date."""
    result: dict[str, Decimal] = {}
    for kind, flag in (("receivable", Account.is_receivable), ("payable", Account.is_payable)):
        conditions = [
            *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.entry_date <= as_of,
            flag.is_(True),
            JournalLine.party_id == party_id,
        ]
        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(and_(*conditions))
        )
        try:
            debit_total, credit_total = (await session.execute(stmt)).one()
        except SQLAlchemyError as exc:
            # Degrade gracefully if the party_id sub-ledger column is missing.
            await session.rollback()
            _logger.warning("Party outstanding unavailable (run 'alembic upgrade head'?): %s", exc)
            return {"receivable": Decimal("0.00"), "payable": Decimal("0.00")}
        debit = _q(Decimal(debit_total))
        credit = _q(Decimal(credit_total))
        result[kind] = _q(debit - credit) if kind == "receivable" else _q(credit - debit)
    return result


_MONTH_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _financial_year_start(as_of: date) -> date:
    """Indian financial year starts 1 April."""
    year = as_of.year if as_of.month >= 4 else as_of.year - 1
    return date(year, 4, 1)


def _last_months(as_of: date, count: int) -> list[tuple[int, int]]:
    """List of (year, month) for the last `count` months, oldest first, ending at as_of's month."""
    out: list[tuple[int, int]] = []
    y, m = as_of.year, as_of.month
    for _ in range(count):
        out.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(out))


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end - timedelta(days=1)


async def get_business_dashboard(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    as_of: date | None = None,
) -> dict:
    """Live executive dashboard computed from the posted ledger (no hard-coded data).

    P&L figures (income/expense/net) are financial-year-to-date; balance-sheet
    groups (cash, receivables, payables, GST payable) are as-of balances. A 6-month
    income-vs-expense trend (in lakhs) backs the dashboard chart. Degrades to zeros
    (never 500) if the ledger is unavailable."""
    as_of = as_of or date.today()
    fy_start = _financial_year_start(as_of)

    async def _sum(*, type_=None, flag=None, code=None, codes=None, date_from=None, date_to=None):
        conds = [
            *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            *_accounting_scope(JournalLine, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        ]
        if type_ is not None:
            conds.append(Account.type == type_)
        if flag is not None:
            conds.append(flag.is_(True))
        if code is not None:
            conds.append(Account.code == code)
        if codes is not None:
            conds.append(Account.code.in_(codes))
        if date_from is not None:
            conds.append(JournalEntry.entry_date >= date_from)
        if date_to is not None:
            conds.append(JournalEntry.entry_date <= date_to)
        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.debit), 0),
                func.coalesce(func.sum(JournalLine.credit), 0),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(and_(*conds))
        )
        try:
            debit_total, credit_total = (await session.execute(stmt)).one()
        except SQLAlchemyError as exc:
            await session.rollback()
            _logger.warning("Dashboard aggregate unavailable (run 'alembic upgrade head'?): %s", exc)
            return Decimal("0"), Decimal("0")
        return Decimal(debit_total), Decimal(credit_total)

    # P&L, financial-year-to-date.
    inc_d, inc_c = await _sum(type_="income", date_from=fy_start, date_to=as_of)
    exp_d, exp_c = await _sum(type_="expense", date_from=fy_start, date_to=as_of)
    income = _q(inc_c - inc_d)        # income accounts carry credit balances
    expense = _q(exp_d - exp_c)       # expense accounts carry debit balances
    net = _q(income - expense)

    # Balance-sheet groups, as-of.
    cash_d, cash_c = await _sum(flag=Account.is_cash_bank, date_to=as_of)
    recv_d, recv_c = await _sum(flag=Account.is_receivable, date_to=as_of)
    pay_d, pay_c = await _sum(flag=Account.is_payable, date_to=as_of)
    # Net GST liability = Output GST (22001/22002/23003) less Input ITC
    # (14001/14002/14003) plus the net clearing account (22004) after set-off.
    # Summing all heads gives the correct running position whether or not a GST
    # set-off journal has been posted (pre-settlement the balance sits in the
    # Output/Input heads; post-settlement it moves to 22004).
    gst_d, gst_c = await _sum(
        codes=("22001", "22002", "22003", "22004", "14001", "14002", "14003"),
        date_to=as_of,
    )
    cash = _q(cash_d - cash_c)
    receivable = _q(recv_d - recv_c)
    payable = _q(pay_c - pay_d)
    gst_payable = _q(gst_c - gst_d)

    # 6-month income-vs-expense trend (lakhs for the chart).
    trend: list[list] = []
    monthly_income: list[Decimal] = []
    for (y, m) in _last_months(as_of, 6):
        m_start, m_end = _month_bounds(y, m)
        m_end = min(m_end, as_of)
        mi_d, mi_c = await _sum(type_="income", date_from=m_start, date_to=m_end)
        me_d, me_c = await _sum(type_="expense", date_from=m_start, date_to=m_end)
        m_income = _q(mi_c - mi_d)
        m_expense = _q(me_d - me_c)
        monthly_income.append(m_income)
        trend.append([
            _MONTH_ABBR[m],
            round(float(m_income) / 100000, 2),
            round(float(m_expense) / 100000, 2),
        ])

    # Month-over-month income growth (last vs previous month in the trend window).
    growth = 0.0
    if len(monthly_income) >= 2 and monthly_income[-2] != 0:
        growth = float(_q((monthly_income[-1] - monthly_income[-2]) / monthly_income[-2] * 100))

    return {
        "as_of": as_of.isoformat(),
        "financial_year_start": fy_start.isoformat(),
        "income": {
            "fytd": str(income),
            "current_month": str(monthly_income[-1]) if monthly_income else "0.00",
            "ytd_growth": growth,
        },
        "expenses": {"fytd": str(expense)},
        "net_position": {"profit_loss": str(net)},
        "cash_and_bank": str(cash),
        "receivables": str(receivable),
        "payables": str(payable),
        "gst": {"payable": str(gst_payable), "status": "Due" if gst_payable > 0 else "Nil"},
        "monthly_trend": trend,
    }


async def list_journal_entries(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[JournalEntry]:
    _validate_report_date_range(from_date=from_date, to_date=to_date)

    stmt = select(JournalEntry).where(
        *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id)
    )
    if from_date:
        stmt = stmt.where(JournalEntry.entry_date >= from_date)
    if to_date:
        stmt = stmt.where(JournalEntry.entry_date <= to_date)
    
    stmt = stmt.order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc()).limit(limit).offset(offset)
    stmt = stmt.options(selectinload(JournalEntry.lines))
    
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_journal_entry_detail(
    session: AsyncSession,
    *,
    tenant_id: str,
    journal_id: int,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> JournalEntry:
    stmt = (
        select(JournalEntry)
        .where(
            JournalEntry.id == journal_id,
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        )
        .options(selectinload(JournalEntry.lines))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if not entry:
        raise AccountingNotFoundError(f"Journal entry {journal_id} not found")
    return entry

