"""
Tests for Core_Accounting Reconciliation Service

Tests bank reconciliation, ledger queries, and financial reporting.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core_accounting.reconciliation import ReconciliationService
from modules.core_accounting.journal import post_journal_entry
from app.models.phase1_schemas import JournalEntryCreate, JournalLineRequest


@pytest.mark.asyncio
async def test_get_account_ledger(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test getting detailed ledger for an account"""

    # Create a few entries
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

    # Get ledger
    ledger = await ReconciliationService.get_account_ledger(
        session, test_tenant_id, test_accounts['cash'].id
    )

    assert len(ledger) >= 3
    assert all('entry_date' in item for item in ledger)
    assert all('debit' in item for item in ledger)
    assert all('running_balance' in item for item in ledger)


@pytest.mark.asyncio
async def test_get_account_ledger_with_date_filter(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test ledger with date filtering"""

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create entry yesterday
    payload_yesterday = JournalEntryCreate(
        entry_date=yesterday,
        description="Yesterday's transaction",
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
    await post_journal_entry(session, test_tenant_id, payload_yesterday, "test-user")

    # Create entry today
    payload_today = JournalEntryCreate(
        entry_date=today,
        description="Today's transaction",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('200'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('200')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload_today, "test-user")

    await session.commit()

    # Get ledger for today only
    ledger = await ReconciliationService.get_account_ledger(
        session, test_tenant_id, test_accounts['cash'].id,
        start_date=today
    )

    assert all(item['entry_date'] >= today for item in ledger)


@pytest.mark.asyncio
async def test_calculate_balance_sheet(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test balance sheet calculation"""

    # Create entries
    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Test balance sheet",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('5000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('5000')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Calculate balance sheet
    bs = await ReconciliationService.calculate_balance_sheet(
        session, test_tenant_id
    )

    assert 'assets' in bs
    assert 'liabilities' in bs
    assert 'equity' in bs
    assert 'total_assets' in bs
    assert 'total_liabilities' in bs
    assert 'total_equity' in bs


@pytest.mark.asyncio
async def test_calculate_profit_loss(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test profit & loss calculation"""

    today = date.today()
    start_date = today - timedelta(days=30)

    # Create income entry
    payload = JournalEntryCreate(
        entry_date=today,
        description="Income for P&L",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('10000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('10000')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Calculate P&L
    pl = await ReconciliationService.calculate_profit_loss(
        session, test_tenant_id, start_date, today
    )

    assert 'income' in pl
    assert 'expenses' in pl
    assert 'total_income' in pl
    assert 'total_expenses' in pl
    assert 'net_profit_loss' in pl
    assert pl['total_income'] > 0


@pytest.mark.asyncio
async def test_match_bank_statement(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test bank statement matching"""

    # Create entry
    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Deposit",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['bank'].id,
                debit=Decimal('5000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=None,
                credit=Decimal('5000')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Match bank statement
    result = await ReconciliationService.match_bank_statement(
        session, test_tenant_id,
        test_accounts['bank'].id,
        Decimal('5000'),
        date.today()
    )

    assert result['bank_amount'] == 5000
    assert result['book_balance'] == 5000
    assert result['is_reconciled'] is True
    assert result['difference'] == 0


@pytest.mark.asyncio
async def test_match_bank_statement_with_variance(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test bank statement with unreconciled variance"""

    # Create entry for 4000
    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Deposit",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['bank'].id,
                debit=Decimal('4000'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('4000')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Bank shows 5000 (difference of 1000)
    result = await ReconciliationService.match_bank_statement(
        session, test_tenant_id,
        test_accounts['bank'].id,
        Decimal('5000'),
        date.today()
    )

    assert result['bank_amount'] == 5000
    assert result['book_balance'] == 4000
    assert result['difference'] == 1000
    assert result['is_reconciled'] is False


@pytest.mark.asyncio
async def test_match_bank_statement_uncleared_items(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test bank match with future-dated (uncleared) items"""

    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Create posted entry for today
    payload_today = JournalEntryCreate(
        entry_date=today,
        description="Today's deposit",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['bank'].id,
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
    await post_journal_entry(session, test_tenant_id, payload_today, "test-user")

    # Create entry for tomorrow (uncleared)
    payload_tomorrow = JournalEntryCreate(
        entry_date=tomorrow,
        description="Tomorrow's deposit",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['bank'].id,
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
    await post_journal_entry(session, test_tenant_id, payload_tomorrow, "test-user")

    await session.commit()

    # Match as of today (1000 should be on books, 500 should be uncleared)
    result = await ReconciliationService.match_bank_statement(
        session, test_tenant_id,
        test_accounts['bank'].id,
        Decimal('1000'),
        today
    )

    assert result['book_balance'] == 1000
    assert result['is_reconciled'] is True
    assert len(result['uncleared_items']) > 0


@pytest.mark.asyncio
async def test_reconcile_account(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test account reconciliation"""

    # Create entry
    payload = JournalEntryCreate(
        entry_date=date.today(),
        description="Reconciliation test",
        lines=[
            JournalLineRequest(
                account_id=test_accounts['cash'].id,
                debit=Decimal('2500'),
                credit=None
            ),
            JournalLineRequest(
                account_id=test_accounts['income'].id,
                debit=None,
                credit=Decimal('2500')
            )
        ]
    )
    await post_journal_entry(session, test_tenant_id, payload, "test-user")

    await session.commit()

    # Reconcile at book balance
    result = await ReconciliationService.reconcile_account(
        session, test_tenant_id,
        test_accounts['cash'].id,
        date.today(),
        Decimal('2500')
    )

    assert result['actual_balance'] == 2500
    assert result['reconciled_amount'] == 2500
    assert result['is_balanced'] is True
    assert result['variance'] == 0
