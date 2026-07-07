from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry
from app.modules.business.banking_books import build_bank_cash_book

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"


async def _account(
    session: AsyncSession,
    *,
    tenant_id: str,
    code: str,
    name: str,
    account_type: str,
    is_cash_bank: bool = False,
    accounting_entity_id: str = ENTITY_ID,
) -> Account:
    account = Account(
        app_key=APP_KEY,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        code=code,
        name=name,
        type=account_type,
        classification="real" if account_type in {"asset", "liability", "equity"} else "nominal",
        is_cash_bank=is_cash_bank,
        is_receivable=False,
        is_payable=False,
    )
    session.add(account)
    await session.flush()
    return account


async def _post(
    session: AsyncSession,
    *,
    tenant_id: str,
    entry_date: date,
    debit_account_id: int,
    credit_account_id: int,
    amount: str,
    key: str,
    accounting_entity_id: str = ENTITY_ID,
    reference: str | None = None,
):
    entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        created_by="tester",
        idempotency_key=key,
        payload=JournalPostRequest(
            entry_date=entry_date,
            description=f"Book test {key}",
            reference=reference or key,
            source_module="business",
            source_document_type="book_test",
            source_document_id=key,
            lines=[
                JournalLineIn(account_id=debit_account_id, debit=Decimal(amount), credit=Decimal("0.00")),
                JournalLineIn(account_id=credit_account_id, debit=Decimal("0.00"), credit=Decimal(amount)),
            ],
        ),
    )
    assert created is True
    return entry


@pytest.mark.asyncio
async def test_bank_cash_book_builds_opening_period_and_closing_from_posted_ledger(async_session: AsyncSession):
    tenant = "bank-book-tenant"
    cash = await _account(async_session, tenant_id=tenant, code="11001", name="Cash in Hand", account_type="asset", is_cash_bank=True)
    bank = await _account(async_session, tenant_id=tenant, code="11010", name="Bank Account", account_type="asset", is_cash_bank=True)
    income = await _account(async_session, tenant_id=tenant, code="41001", name="Sales", account_type="income")
    expense = await _account(async_session, tenant_id=tenant, code="54001", name="Bank Charges", account_type="expense")

    await _post(async_session, tenant_id=tenant, entry_date=date(2026, 3, 31), debit_account_id=bank.id, credit_account_id=income.id, amount="1000.00", key="bank-opening")
    await _post(async_session, tenant_id=tenant, entry_date=date(2026, 4, 5), debit_account_id=bank.id, credit_account_id=income.id, amount="250.00", key="bank-receipt", reference="BR-1")
    await _post(async_session, tenant_id=tenant, entry_date=date(2026, 4, 6), debit_account_id=expense.id, credit_account_id=bank.id, amount="50.00", key="bank-payment", reference="BP-1")
    await _post(async_session, tenant_id=tenant, entry_date=date(2026, 4, 7), debit_account_id=cash.id, credit_account_id=income.id, amount="125.00", key="cash-receipt", reference="CR-1")

    out = await build_bank_cash_book(
        async_session,
        tenant_id=tenant,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30),
        book_type="bank",
    )

    assert out["book_type"] == "bank"
    assert out["summary"]["opening_balance"] == "1000.00"
    assert out["summary"]["total_receipts"] == "250.00"
    assert out["summary"]["total_payments"] == "50.00"
    assert out["summary"]["closing_balance"] == "1200.00"
    assert [row["account_code"] for row in out["accounts"]] == ["11010"]
    bank_rows = out["accounts"][0]["lines"]
    assert [(row["reference"], row["receipt"], row["payment"], row["running_balance"]) for row in bank_rows] == [
        ("BR-1", "250.00", "0.00", "1250.00"),
        ("BP-1", "0.00", "50.00", "1200.00"),
    ]

    cash_out = await build_bank_cash_book(
        async_session,
        tenant_id=tenant,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30),
        book_type="cash",
    )
    assert cash_out["summary"]["total_receipts"] == "125.00"
    assert cash_out["accounts"][0]["account_code"] == "11001"


@pytest.mark.asyncio
async def test_bank_cash_book_is_tenant_and_entity_scoped(async_session: AsyncSession):
    tenant = "bank-book-scope-a"
    other_tenant = "bank-book-scope-b"
    cash = await _account(async_session, tenant_id=tenant, code="11001", name="Cash in Hand", account_type="asset", is_cash_bank=True)
    income = await _account(async_session, tenant_id=tenant, code="41001", name="Sales", account_type="income")
    other_cash = await _account(async_session, tenant_id=other_tenant, code="11001", name="Cash in Hand", account_type="asset", is_cash_bank=True)
    other_income = await _account(async_session, tenant_id=other_tenant, code="41001", name="Sales", account_type="income")
    branch_cash = await _account(async_session, tenant_id=tenant, code="11001", name="Cash Branch", account_type="asset", is_cash_bank=True, accounting_entity_id="branch-a")
    branch_income = await _account(async_session, tenant_id=tenant, code="41001", name="Sales Branch", account_type="income", accounting_entity_id="branch-a")

    await _post(async_session, tenant_id=tenant, entry_date=date(2026, 5, 1), debit_account_id=cash.id, credit_account_id=income.id, amount="100.00", key="scope-primary")
    await _post(async_session, tenant_id=other_tenant, entry_date=date(2026, 5, 1), debit_account_id=other_cash.id, credit_account_id=other_income.id, amount="999.00", key="scope-other-tenant")
    await _post(async_session, tenant_id=tenant, accounting_entity_id="branch-a", entry_date=date(2026, 5, 1), debit_account_id=branch_cash.id, credit_account_id=branch_income.id, amount="555.00", key="scope-branch")

    out = await build_bank_cash_book(
        async_session,
        tenant_id=tenant,
        app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID,
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
        book_type="all",
    )

    assert out["summary"]["total_receipts"] == "100.00"
    assert out["summary"]["closing_balance"] == "100.00"
    assert [row["account_name"] for row in out["accounts"]] == ["Cash in Hand"]
