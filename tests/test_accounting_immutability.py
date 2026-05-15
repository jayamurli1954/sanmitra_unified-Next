from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalLine, LedgerImmutabilityError
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry


async def _create_accounting_pair(session: AsyncSession) -> tuple[Account, Account]:
    cash = Account(
        app_key="mitrabooks",
        tenant_id="tenant-immutable",
        accounting_entity_id="primary",
        code="1000",
        name="Cash",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    income = Account(
        app_key="mitrabooks",
        tenant_id="tenant-immutable",
        accounting_entity_id="primary",
        code="4000",
        name="Service Income",
        type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    session.add_all([cash, income])
    await session.commit()
    return cash, income


async def _post_entry(session: AsyncSession):
    cash, income = await _create_accounting_pair(session)
    entry, created = await post_journal_entry(
        session,
        tenant_id="tenant-immutable",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key=None,
        payload=JournalPostRequest(
            entry_date=date(2026, 5, 15),
            description="Immutable ledger test",
            reference="IMM-001",
            lines=[
                JournalLineIn(account_id=cash.id, debit=Decimal("100.00"), credit=Decimal("0.00")),
                JournalLineIn(account_id=income.id, debit=Decimal("0.00"), credit=Decimal("100.00")),
            ],
        ),
    )
    assert created is True
    await session.refresh(entry, attribute_names=["lines"])
    assert len(entry.lines) == 2
    return entry, cash


@pytest.mark.asyncio
async def test_posted_journal_entry_cannot_be_updated(async_session: AsyncSession) -> None:
    entry, _cash = await _post_entry(async_session)

    entry.description = "Changed after posting"

    with pytest.raises(LedgerImmutabilityError, match="reversal or adjustment"):
        await async_session.commit()


@pytest.mark.asyncio
async def test_posted_journal_entry_cannot_be_deleted(async_session: AsyncSession) -> None:
    entry, _cash = await _post_entry(async_session)

    await async_session.delete(entry)

    with pytest.raises(LedgerImmutabilityError, match="cannot be deleted"):
        await async_session.commit()


@pytest.mark.asyncio
async def test_posted_journal_line_cannot_be_updated(async_session: AsyncSession) -> None:
    entry, _cash = await _post_entry(async_session)

    entry.lines[0].debit = Decimal("99.00")

    with pytest.raises(LedgerImmutabilityError, match="reversal or adjustment"):
        await async_session.commit()


@pytest.mark.asyncio
async def test_posted_journal_line_cannot_be_deleted(async_session: AsyncSession) -> None:
    entry, _cash = await _post_entry(async_session)

    await async_session.delete(entry.lines[0])

    with pytest.raises(LedgerImmutabilityError, match="cannot be deleted"):
        await async_session.commit()


@pytest.mark.asyncio
async def test_posted_journal_cannot_accept_late_lines(async_session: AsyncSession) -> None:
    entry, cash = await _post_entry(async_session)

    async_session.add(
        JournalLine(
            app_key=entry.app_key,
            tenant_id=entry.tenant_id,
            accounting_entity_id=entry.accounting_entity_id,
            journal_id=entry.id,
            account_id=cash.id,
            debit=Decimal("1.00"),
            credit=Decimal("0.00"),
        )
    )

    with pytest.raises((LedgerImmutabilityError, StatementError), match="immutable|reversal"):
        await async_session.commit()
