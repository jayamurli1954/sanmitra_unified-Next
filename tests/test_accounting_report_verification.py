from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingValidationError,
    get_balance_sheet,
    get_ledger_lines,
    get_profit_loss,
    get_receipts_payments,
    get_trial_balance,
    post_journal_entry,
    reverse_journal_entry,
)


APP_KEY = "mitrabooks"
ENTITY_ID = "primary"


async def _create_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    code: str,
    name: str,
    account_type: str,
    classification: str,
    is_cash_bank: bool = False,
) -> Account:
    account = Account(
        app_key=APP_KEY,
        tenant_id=tenant_id,
        accounting_entity_id=ENTITY_ID,
        code=code,
        name=name,
        type=account_type,
        classification=classification,
        is_cash_bank=is_cash_bank,
        is_receivable=False,
        is_payable=False,
    )
    session.add(account)
    return account


async def _create_basic_accounts(session: AsyncSession, *, tenant_id: str) -> tuple[Account, Account, Account]:
    cash = await _create_account(
        session,
        tenant_id=tenant_id,
        code="1000",
        name="Cash",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
    )
    income = await _create_account(
        session,
        tenant_id=tenant_id,
        code="4000",
        name="Service Income",
        account_type="income",
        classification="nominal",
    )
    expense = await _create_account(
        session,
        tenant_id=tenant_id,
        code="5000",
        name="Operating Expense",
        account_type="expense",
        classification="nominal",
    )
    await session.commit()
    return cash, income, expense


async def _post_receipt(
    session: AsyncSession,
    *,
    tenant_id: str,
    amount: Decimal = Decimal("250.00"),
    idempotency_key: str = "receipt-001",
) -> tuple[JournalEntry, Account, Account, Account]:
    cash, income, expense = await _create_basic_accounts(session, tenant_id=tenant_id)
    entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        created_by="test-user",
        idempotency_key=idempotency_key,
        payload=JournalPostRequest(
            entry_date=date(2026, 5, 15),
            description="Report verification receipt",
            reference="RV-001",
            lines=[
                JournalLineIn(account_id=cash.id, debit=amount, credit=Decimal("0.00")),
                JournalLineIn(account_id=income.id, debit=Decimal("0.00"), credit=amount),
            ],
        ),
    )
    assert created is True
    await session.refresh(entry, attribute_names=["lines"])
    return entry, cash, income, expense


def _line_by_account(lines: list[dict], account_id: int) -> dict:
    return next(line for line in lines if line["account_id"] == account_id)


@pytest.mark.asyncio
async def test_trial_balance_reflects_reversal_without_mutating_history(async_session: AsyncSession) -> None:
    tenant_id = "tenant-report-reversal"
    original, cash, income, _expense = await _post_receipt(async_session, tenant_id=tenant_id)

    await reverse_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        created_by="reviewer",
        journal_id=original.id,
        reversal_date=date(2026, 5, 16),
        reason="Report verification reversal",
    )

    lines, total_debit, total_credit = await get_trial_balance(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        as_of=date(2026, 5, 16),
    )

    assert total_debit == Decimal("500.00")
    assert total_credit == Decimal("500.00")
    assert _line_by_account(lines, cash.id)["net_balance"] == Decimal("0.00")
    assert _line_by_account(lines, income.id)["net_balance"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_ledger_running_balance_returns_to_zero_after_reversal(async_session: AsyncSession) -> None:
    tenant_id = "tenant-report-ledger"
    original, cash, _income, _expense = await _post_receipt(async_session, tenant_id=tenant_id)

    await reverse_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        created_by="reviewer",
        journal_id=original.id,
        reversal_date=date(2026, 5, 16),
    )

    _account, ledger_lines = await get_ledger_lines(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        account_id=cash.id,
    )

    assert [line["running_balance"] for line in ledger_lines] == [Decimal("250.00"), Decimal("0.00")]
    assert ledger_lines[0]["debit"] == Decimal("250.00")
    assert ledger_lines[1]["credit"] == Decimal("250.00")


@pytest.mark.asyncio
async def test_profit_loss_returns_to_zero_after_reversal(async_session: AsyncSession) -> None:
    tenant_id = "tenant-report-pl"
    original, _cash, _income, _expense = await _post_receipt(async_session, tenant_id=tenant_id)

    await reverse_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        created_by="reviewer",
        journal_id=original.id,
        reversal_date=date(2026, 5, 16),
    )

    _lines, income_total, expense_total, net_profit = await get_profit_loss(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
    )

    assert income_total == Decimal("0.00")
    assert expense_total == Decimal("0.00")
    assert net_profit == Decimal("0.00")


@pytest.mark.asyncio
async def test_balance_sheet_equation_holds_before_and_after_reversal(async_session: AsyncSession) -> None:
    tenant_id = "tenant-report-balance-sheet"
    original, _cash, _income, _expense = await _post_receipt(async_session, tenant_id=tenant_id)

    _assets, _liabilities, _equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        as_of=date(2026, 5, 15),
    )
    assert total_assets == total_liabilities + total_equity
    assert total_assets == Decimal("250.00")
    assert total_equity == Decimal("250.00")

    await reverse_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        created_by="reviewer",
        journal_id=original.id,
        reversal_date=date(2026, 5, 16),
    )

    _assets, _liabilities, _equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        as_of=date(2026, 5, 16),
    )
    assert total_assets == total_liabilities + total_equity
    assert total_assets == Decimal("0.00")
    assert total_liabilities == Decimal("0.00")
    assert total_equity == Decimal("0.00")


@pytest.mark.asyncio
async def test_reports_keep_tenant_boundary(async_session: AsyncSession) -> None:
    tenant_id = "tenant-report-owner"
    other_tenant_id = "tenant-report-other"
    _original, cash, _income, _expense = await _post_receipt(
        async_session,
        tenant_id=tenant_id,
        amount=Decimal("175.00"),
        idempotency_key="owner-receipt-001",
    )
    await _post_receipt(
        async_session,
        tenant_id=other_tenant_id,
        amount=Decimal("900.00"),
        idempotency_key="other-receipt-001",
    )

    lines, total_debit, total_credit = await get_trial_balance(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        as_of=date(2026, 5, 15),
    )
    _account, ledger_lines = await get_ledger_lines(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        account_id=cash.id,
    )
    _assets, _liabilities, equity, total_assets, total_liabilities, total_equity = await get_balance_sheet(
        async_session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        as_of=date(2026, 5, 15),
    )

    assert total_debit == Decimal("175.00")
    assert total_credit == Decimal("175.00")
    assert len(lines) == 2
    assert all(line["debit_total"] != Decimal("900.00") for line in lines)
    assert ledger_lines[-1]["running_balance"] == Decimal("175.00")
    assert total_assets == Decimal("175.00")
    assert total_liabilities == Decimal("0.00")
    assert total_equity == Decimal("175.00")
    assert equity == [{"account_id": 0, "account_name": "Current Period Earnings (System)", "balance": Decimal("175.00")}]


@pytest.mark.asyncio
async def test_profit_loss_rejects_reversed_date_range(async_session: AsyncSession) -> None:
    with pytest.raises(AccountingValidationError, match="from_date cannot be greater than to_date"):
        await get_profit_loss(
            async_session,
            tenant_id="tenant-report-range",
            app_key=APP_KEY,
            accounting_entity_id=ENTITY_ID,
            from_date=date(2026, 5, 31),
            to_date=date(2026, 5, 1),
        )


@pytest.mark.asyncio
async def test_receipts_payments_rejects_reversed_date_range(async_session: AsyncSession) -> None:
    with pytest.raises(AccountingValidationError, match="from_date cannot be greater than to_date"):
        await get_receipts_payments(
            async_session,
            tenant_id="tenant-report-range",
            app_key=APP_KEY,
            accounting_entity_id=ENTITY_ID,
            from_date=date(2026, 5, 31),
            to_date=date(2026, 5, 1),
        )
