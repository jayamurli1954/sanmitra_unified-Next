"""
Tests for Core_Accounting Journal Posting Engine

Tests double-entry bookkeeping, balance validation, idempotency, and error handling.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.legacy_reference
pytest.skip(
    "Legacy Phase 2 journal tests target the removed modules.core_accounting package; "
    "current bootstrap coverage uses app.accounting tests.",
    allow_module_level=True,
)

from modules.core_accounting.models.entities import (
    Account, JournalEntry, JournalLine
)
from modules.core_accounting.journal import (
    post_journal_entry,
    get_journal_entry,
    list_journal_entries,
    reverse_journal_entry,
    get_account_balance,
    UnbalancedEntryError,
    DuplicateEntryError,
    AccountNotFoundError,
    InvalidLineError
)
from app.models.phase1_schemas import JournalEntryCreate, JournalLineRequest


@pytest.mark.asyncio
async def test_post_journal_entry_basic(session: AsyncSession, test_tenant_id: str, test_accounts: dict):
    """Test posting a basic journal entry"""

    # Create payload
    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Test donation received",
        reference="test-001",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('1000'),
                credit=None,
                description="Cash received"
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('1000'),
                description="Donation income"
            )
        ]
    )

    # Post entry
    entry = await post_journal_entry(
        session, test_tenant_id, payload, "test-user"
    )

    # Verify
    assert entry.id is not None
    assert entry.status == 'posted'
    assert entry.is_balanced
    assert len(entry.lines) == 2
    assert entry.total_debit == Decimal('1000')
    assert entry.total_credit == Decimal('1000')


@pytest.mark.asyncio
async def test_post_journal_entry_unbalanced(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test that unbalanced entries are rejected"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Unbalanced entry",
        reference="unbalanced-001",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('1000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('800')  # Not equal to debit
            )
        ]
    )

    with pytest.raises(UnbalancedEntryError):
        await post_journal_entry(
            session, test_tenant_id, payload, "test-user"
        )


@pytest.mark.asyncio
async def test_post_journal_entry_account_not_found(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test that posting with non-existent account fails"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Invalid account",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('1000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=99999,  # Non-existent account
                debit=None,
                credit=Decimal('1000')
            )
        ]
    )

    with pytest.raises(AccountNotFoundError):
        await post_journal_entry(
            session, test_tenant_id, payload, "test-user"
        )


@pytest.mark.asyncio
async def test_post_journal_entry_idempotency(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test that duplicate references are prevented"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Test donation",
        reference="duplicate-check-001",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('1000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('1000')
            )
        ]
    )

    # Post first time
    entry1 = await post_journal_entry(
        session, test_tenant_id, payload, "test-user"
    )
    await session.commit()

    # Try to post with same reference
    with pytest.raises(DuplicateEntryError):
        await post_journal_entry(
            session, test_tenant_id, payload, "test-user"
        )


@pytest.mark.asyncio
async def test_get_journal_entry(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test retrieving a journal entry"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Test retrieve",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('500'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('500')
            )
        ]
    )

    entry = await post_journal_entry(
        session, test_tenant_id, payload, "test-user"
    )
    await session.commit()

    # Retrieve
    retrieved = await get_journal_entry(session, test_tenant_id, entry.id)

    assert retrieved is not None
    assert retrieved.id == entry.id
    assert retrieved.description == "Test retrieve"
    assert len(retrieved.lines) == 2


@pytest.mark.asyncio
async def test_list_journal_entries(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test listing journal entries"""

    # Create multiple entries
    for i in range(3):
        payload = JournalEntryCreate(
            entry_date=date.today(),
            description=f"Test entry {i}",
            lines=[
                JournalLineRequest(
                    account_id=test_accounts['cash'].id,
                    debit=Decimal('100'),
                    credit=None
                ),
                JournalLineRequest(
                    account_id=test_accounts['income'].id,
                    debit=None,
                    credit=Decimal('100')
                )
            ]
        )
        await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # List
    entries = await list_journal_entries(session, test_tenant_id)

    assert len(entries) >= 3
    assert all(e.status == 'posted' for e in entries)


@pytest.mark.asyncio
async def test_reverse_journal_entry(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test reversing a journal entry"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Entry to reverse",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('1000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('1000')
            )
        ]
    )

    entry = await post_journal_entry(
        session, test_tenant_id, payload, "test-user"
    )
    await session.commit()

    # Reverse
    reversing_entry = await reverse_journal_entry(
        session, test_tenant_id, entry.id, "test-user"
    )
    await session.commit()

    # Verify original is marked reversed
    original = await get_journal_entry(session, test_tenant_id, entry.id)
    assert original.status == 'reversed'

    # Verify reversing entry has opposite debits/credits
    assert reversing_entry.lines[0].debit == original.lines[0].credit
    assert reversing_entry.lines[0].credit == original.lines[0].debit


@pytest.mark.asyncio
async def test_get_account_balance(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test calculating account balance"""

    # Post multiple entries affecting an account
    for i in range(3):
        payload = JournalEntryCreate(
            entry_date=date.today(),
            description=f"Transaction {i}",
            lines=[
                JournalLineRequest(
                    account_id=test_accounts['cash'].id,
                    debit=Decimal('100'),
                    credit=None
                ),
                JournalLineRequest(
                    account_id=test_accounts['income'].id,
                    debit=None,
                    credit=Decimal('100')
                )
            ]
        )
        await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Get balance
    balance = await get_account_balance(
        session, test_tenant_id, test_accounts['cash'].id
    )

    assert balance == Decimal('300')


@pytest.mark.asyncio
async def test_multi_line_entry(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test posting entry with more than 2 lines"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Multi-line transaction",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('500'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['bank'].id,
                debit=Decimal('300'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('800')
            )
        ]
    )

    entry = await post_journal_entry(
        session, test_tenant_id, payload, "test-user"
    )
    await session.commit()

    assert len(entry.lines) == 3
    assert entry.is_balanced
    assert entry.total_debit == Decimal('800')
    assert entry.total_credit == Decimal('800')


@pytest.mark.asyncio
async def test_invalid_line_both_zero(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test that line with both debit and credit as zero is rejected"""

    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Invalid line",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('0'),  # Zero
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('100')
            )
        ]
    )

    with pytest.raises(InvalidLineError):
        await post_journal_entry(
            session, test_tenant_id, payload, "test-user"
        )


@pytest.mark.asyncio
async def test_list_with_filters(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test listing journal entries with date filters"""

    # Create entries on different dates
    today = date.today()
    yesterday = today - timedelta(days=1)

    for entry_date in [yesterday, today]:
        payload = JournalEntryCreate(
            entry_date=entry_date,
            description=f"Entry on {entry_date}",
            lines=[
                JournalLineRequest(
                    account_id=test_accounts['cash'].id,
                    debit=Decimal('100'),
                    credit=None
                ),
                JournalLineRequest(
                    account_id=test_accounts['income'].id,
                    debit=None,
                    credit=Decimal('100')
                )
            ]
        )
        await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # List with start date filter
    entries = await list_journal_entries(
        session, test_tenant_id, start_date=today
    )

    assert all(e.entry_date >= today for e in entries)
