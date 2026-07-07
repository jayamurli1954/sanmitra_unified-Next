from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry, JournalLine

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(_CENT, rounding=ROUND_HALF_UP)


def _scope(model, *, tenant_id: str, app_key: str, accounting_entity_id: str):
    return (
        model.tenant_id == tenant_id,
        model.app_key == app_key,
        model.accounting_entity_id == accounting_entity_id,
    )


def _book_nature(account: Account) -> str:
    code = str(account.code or "").strip()
    name = str(account.name or "").strip().lower()
    if "bank" in name or code in {"11010", "11011", "1001", "1010", "1020"}:
        return "bank"
    return "cash"


async def build_bank_cash_book(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    from_date: date,
    to_date: date,
    book_type: str = "all",
) -> dict:
    if from_date > to_date:
        raise ValueError("from_date must be on or before to_date")
    normalized_type = str(book_type or "all").strip().lower()
    if normalized_type not in {"all", "cash", "bank"}:
        raise ValueError("book_type must be one of: all, cash, bank")

    accounts = (
        await session.execute(
            select(Account)
            .where(
                *_scope(Account, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id),
                Account.is_cash_bank.is_(True),
                Account.type == "asset",
            )
            .order_by(Account.code.asc(), Account.name.asc())
        )
    ).scalars().all()
    accounts = [account for account in accounts if normalized_type == "all" or _book_nature(account) == normalized_type]
    account_ids = [account.id for account in accounts]

    result = {
        "book_type": normalized_type,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "accounts": [],
        "summary": {
            "opening_balance": "0.00",
            "total_receipts": "0.00",
            "total_payments": "0.00",
            "closing_balance": "0.00",
            "account_count": len(accounts),
        },
    }
    if not account_ids:
        return result

    opening_rows = (
        await session.execute(
            select(
                JournalLine.account_id,
                func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0).label("opening"),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(
                *_scope(JournalEntry, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id),
                *_scope(JournalLine, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id),
                JournalLine.account_id.in_(account_ids),
                JournalEntry.entry_date < from_date,
            )
            .group_by(JournalLine.account_id)
        )
    ).all()
    opening_by_account = {row.account_id: _q2(row.opening) for row in opening_rows}

    line_rows = (
        await session.execute(
            select(
                JournalLine.account_id,
                JournalLine.id.label("line_id"),
                JournalLine.journal_id,
                JournalLine.debit,
                JournalLine.credit,
                JournalEntry.entry_date,
                JournalEntry.reference,
                JournalEntry.description,
                JournalEntry.source_document_type,
                JournalEntry.source_document_id,
                JournalEntry.reversal_of_journal_id,
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(
                *_scope(JournalEntry, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id),
                *_scope(JournalLine, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id),
                JournalLine.account_id.in_(account_ids),
                JournalEntry.entry_date >= from_date,
                JournalEntry.entry_date <= to_date,
            )
            .order_by(JournalEntry.entry_date.asc(), JournalLine.id.asc())
        )
    ).all()

    lines_by_account: dict[int, list[dict]] = {account_id: [] for account_id in account_ids}
    running_by_account = {account_id: opening_by_account.get(account_id, Decimal("0.00")) for account_id in account_ids}
    for row in line_rows:
        debit = _q2(row.debit)
        credit = _q2(row.credit)
        running_by_account[row.account_id] = _q2(running_by_account[row.account_id] + debit - credit)
        entry_date = row.entry_date.isoformat() if hasattr(row.entry_date, "isoformat") else str(row.entry_date)
        lines_by_account[row.account_id].append(
            {
                "line_id": row.line_id,
                "journal_id": row.journal_id,
                "entry_date": entry_date,
                "reference": row.reference,
                "description": row.description,
                "source_document_type": row.source_document_type,
                "source_document_id": row.source_document_id,
                "reversal_of_journal_id": row.reversal_of_journal_id,
                "receipt": str(debit),
                "payment": str(credit),
                "running_balance": str(running_by_account[row.account_id]),
            }
        )

    total_opening = Decimal("0.00")
    total_receipts = Decimal("0.00")
    total_payments = Decimal("0.00")
    total_closing = Decimal("0.00")
    for account in accounts:
        opening = opening_by_account.get(account.id, Decimal("0.00"))
        lines = lines_by_account.get(account.id, [])
        receipts = sum((_q2(line["receipt"]) for line in lines), Decimal("0.00"))
        payments = sum((_q2(line["payment"]) for line in lines), Decimal("0.00"))
        closing = _q2(opening + receipts - payments)
        total_opening += opening
        total_receipts += receipts
        total_payments += payments
        total_closing += closing
        result["accounts"].append(
            {
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "book_type": _book_nature(account),
                "opening_balance": str(_q2(opening)),
                "total_receipts": str(_q2(receipts)),
                "total_payments": str(_q2(payments)),
                "closing_balance": str(_q2(closing)),
                "lines": lines,
            }
        )

    result["summary"] = {
        "opening_balance": str(_q2(total_opening)),
        "total_receipts": str(_q2(total_receipts)),
        "total_payments": str(_q2(total_payments)),
        "closing_balance": str(_q2(total_closing)),
        "account_count": len(accounts),
    }
    return result
