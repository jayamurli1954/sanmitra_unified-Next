from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.accounting.models import Account, JournalEntry
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import AccountingNotFoundError, post_journal_entry, reverse_journal_entry


async def _create_accounts(session: AsyncSession, *, tenant_id: str = "tenant-reversal") -> tuple[Account, Account]:
    cash = Account(
        app_key="mitrabooks",
        tenant_id=tenant_id,
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
        tenant_id=tenant_id,
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


async def _post_original(session: AsyncSession, *, tenant_id: str = "tenant-reversal") -> JournalEntry:
    cash, income = await _create_accounts(session, tenant_id=tenant_id)
    entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="original-sale-001",
        payload=JournalPostRequest(
            entry_date=date(2026, 5, 15),
            description="Original receipt",
            reference="SALE-001",
            lines=[
                JournalLineIn(account_id=cash.id, debit=Decimal("250.00"), credit=Decimal("0.00")),
                JournalLineIn(account_id=income.id, debit=Decimal("0.00"), credit=Decimal("250.00")),
            ],
        ),
    )
    assert created is True
    await session.refresh(entry, attribute_names=["lines"])
    return entry


async def _load_entry(session: AsyncSession, journal_id: int) -> JournalEntry:
    stmt = select(JournalEntry).where(JournalEntry.id == journal_id).options(selectinload(JournalEntry.lines))
    entry = (await session.execute(stmt)).scalar_one()
    return entry


@pytest.mark.asyncio
async def test_reverse_journal_entry_posts_equal_opposite_entry(async_session: AsyncSession) -> None:
    original = await _post_original(async_session)

    reversal, created = await reverse_journal_entry(
        async_session,
        tenant_id=original.tenant_id,
        app_key=original.app_key,
        accounting_entity_id=original.accounting_entity_id,
        created_by="reviewer",
        journal_id=original.id,
        reversal_date=date(2026, 5, 16),
        reason="Wrong receipt",
    )
    await async_session.refresh(reversal, attribute_names=["lines"])

    assert created is True
    assert reversal.id != original.id
    assert reversal.entry_date == date(2026, 5, 16)
    assert reversal.reference == f"REV-{original.id}-SALE-001"
    assert reversal.total_debit == original.total_debit
    assert reversal.total_credit == original.total_credit
    assert reversal.idempotency_key == f"journal-reversal:{original.id}"

    original_by_account = {line.account_id: line for line in original.lines}
    for reversal_line in reversal.lines:
        original_line = original_by_account[reversal_line.account_id]
        assert reversal_line.debit == original_line.credit
        assert reversal_line.credit == original_line.debit


@pytest.mark.asyncio
async def test_reverse_journal_entry_does_not_mutate_original(async_session: AsyncSession) -> None:
    original = await _post_original(async_session)
    original_description = original.description
    original_reference = original.reference
    original_line_values = [(line.account_id, line.debit, line.credit) for line in original.lines]

    await reverse_journal_entry(
        async_session,
        tenant_id=original.tenant_id,
        app_key=original.app_key,
        accounting_entity_id=original.accounting_entity_id,
        created_by="reviewer",
        journal_id=original.id,
        reason="Correction",
    )

    reloaded = await _load_entry(async_session, original.id)
    assert reloaded.description == original_description
    assert reloaded.reference == original_reference
    assert [(line.account_id, line.debit, line.credit) for line in reloaded.lines] == original_line_values


@pytest.mark.asyncio
async def test_reverse_journal_entry_is_idempotent(async_session: AsyncSession) -> None:
    original = await _post_original(async_session)

    first, first_created = await reverse_journal_entry(
        async_session,
        tenant_id=original.tenant_id,
        app_key=original.app_key,
        accounting_entity_id=original.accounting_entity_id,
        created_by="reviewer",
        journal_id=original.id,
    )
    second, second_created = await reverse_journal_entry(
        async_session,
        tenant_id=original.tenant_id,
        app_key=original.app_key,
        accounting_entity_id=original.accounting_entity_id,
        created_by="reviewer",
        journal_id=original.id,
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id


@pytest.mark.asyncio
async def test_reverse_journal_entry_blocks_cross_tenant_access(async_session: AsyncSession) -> None:
    original = await _post_original(async_session, tenant_id="tenant-a")

    with pytest.raises(AccountingNotFoundError):
        await reverse_journal_entry(
            async_session,
            tenant_id="tenant-b",
            app_key=original.app_key,
            accounting_entity_id=original.accounting_entity_id,
            created_by="reviewer",
            journal_id=original.id,
        )


@pytest.mark.asyncio
async def test_reverse_journal_entry_blocks_cross_app_access(async_session: AsyncSession) -> None:
    original = await _post_original(async_session)

    with pytest.raises(AccountingNotFoundError):
        await reverse_journal_entry(
            async_session,
            tenant_id=original.tenant_id,
            app_key="mandirmitra",
            accounting_entity_id=original.accounting_entity_id,
            created_by="reviewer",
            journal_id=original.id,
        )
