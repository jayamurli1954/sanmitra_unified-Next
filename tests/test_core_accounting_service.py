"""
Tests for Core_Accounting Account Service

Tests CRUD operations on Chart of Accounts.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.core_accounting.service import AccountService, get_trial_balance
from modules.core_accounting.models.entities import Account
from app.models.phase1_schemas import AccountCreate, AccountUpdate


@pytest.mark.asyncio
async def test_list_accounts(session: AsyncSession, test_tenant_id: str, test_accounts: dict):
    """Test listing accounts"""

    accounts = await AccountService.list_accounts(session, test_tenant_id)

    assert len(accounts) > 0
    assert all(a.tenant_id == test_tenant_id for a in accounts)


@pytest.mark.asyncio
async def test_list_accounts_filtered_by_type(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test listing accounts filtered by type"""

    asset_accounts = await AccountService.list_accounts(
        session, test_tenant_id, account_type='asset'
    )

    assert len(asset_accounts) > 0
    assert all(a.account_type == 'asset' for a in asset_accounts)


@pytest.mark.asyncio
async def test_get_account(session: AsyncSession, test_tenant_id: str, test_accounts: dict):
    """Test retrieving a single account"""

    account = await AccountService.get_account(
        session, test_tenant_id, test_accounts['cash'].id
    )

    assert account is not None
    assert account.id == test_accounts['cash'].id
    assert account.account_name == 'Cash'


@pytest.mark.asyncio
async def test_get_account_by_number(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test retrieving account by account number"""

    account = await AccountService.get_account_by_number(
        session, test_tenant_id, '1000'
    )

    assert account is not None
    assert account.account_number == '1000'


@pytest.mark.asyncio
async def test_create_account(session: AsyncSession, test_tenant_id: str):
    """Test creating a new account"""

    payload = AccountCreate(
        account_number='5000',
        account_name='New Test Account',
        account_type='expense',
        account_category='Operating Expenses',
        description='Test expense account'
    )

    account = await AccountService.create_account(session, test_tenant_id, payload)
    await session.commit()

    assert account.id is not None
    assert account.account_number == '5000'
    assert account.is_active is True


@pytest.mark.asyncio
async def test_create_account_duplicate_number(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test that duplicate account numbers are prevented"""

    payload = AccountCreate(
        account_number='1000',  # Already exists
        account_name='Duplicate',
        account_type='asset'
    )

    with pytest.raises(ValueError) as exc:
        await AccountService.create_account(session, test_tenant_id, payload)

    assert 'already exists' in str(exc.value)


@pytest.mark.asyncio
async def test_update_account(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test updating an account"""

    payload = AccountUpdate(
        account_name='Updated Cash Account',
        description='Updated description'
    )

    updated = await AccountService.update_account(
        session, test_tenant_id, test_accounts['cash'].id, payload
    )
    await session.commit()

    assert updated.account_name == 'Updated Cash Account'
    assert updated.description == 'Updated description'


@pytest.mark.asyncio
async def test_deactivate_account(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test deactivating an account"""

    account = await AccountService.deactivate_account(
        session, test_tenant_id, test_accounts['cash'].id
    )
    await session.commit()

    assert account.is_active is False

    # Verify list no longer includes it with active_only=True
    active_accounts = await AccountService.list_accounts(
        session, test_tenant_id, active_only=True
    )
    assert all(a.id != test_accounts['cash'].id for a in active_accounts)


@pytest.mark.asyncio
async def test_get_account_hierarchy(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test getting accounts grouped by type"""

    hierarchy = await AccountService.get_account_hierarchy(session, test_tenant_id)

    assert 'asset' in hierarchy
    assert 'liability' in hierarchy
    assert 'income' in hierarchy
    assert 'expense' in hierarchy
    assert len(hierarchy['asset']) > 0
    assert len(hierarchy['income']) > 0


@pytest.mark.asyncio
async def test_get_account_balance_with_details(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test getting account balance with details"""

    details = await AccountService.get_account_balance_with_details(
        session, test_tenant_id, test_accounts['cash'].id
    )

    assert details['account_id'] == test_accounts['cash'].id
    assert 'total_debit' in details
    assert 'total_credit' in details
    assert 'balance' in details
    assert 'transaction_count' in details


@pytest.mark.asyncio
async def test_import_chart_from_list(session: AsyncSession, test_tenant_id: str):
    """Test bulk importing chart of accounts"""

    accounts_list = [
        {
            'account_number': '6000',
            'account_name': 'Salaries & Wages',
            'account_type': 'expense',
            'account_category': 'Payroll',
            'description': 'Employee salaries'
        },
        {
            'account_number': '6100',
            'account_name': 'Rent Expense',
            'account_type': 'expense',
            'account_category': 'Facilities',
            'description': 'Building rent'
        }
    ]

    created = await AccountService.import_chart_from_list(
        session, test_tenant_id, accounts_list
    )
    await session.commit()

    assert len(created) == 2
    assert created[0].account_number == '6000'
    assert created[1].account_number == '6100'


@pytest.mark.asyncio
async def test_import_chart_with_duplicates(
    session: AsyncSession, test_tenant_id: str
):
    """Test that import with duplicate numbers is rejected"""

    accounts_list = [
        {
            'account_number': '7000',
            'account_name': 'Account 1',
            'account_type': 'expense'
        },
        {
            'account_number': '7000',  # Duplicate
            'account_name': 'Account 2',
            'account_type': 'expense'
        }
    ]

    with pytest.raises(ValueError) as exc:
        await AccountService.import_chart_from_list(
            session, test_tenant_id, accounts_list
        )

    assert 'Duplicate' in str(exc.value)


@pytest.mark.asyncio
async def test_get_trial_balance(
    session: AsyncSession, test_tenant_id: str, test_accounts: dict
):
    """Test getting trial balance"""

    trial_balance = await get_trial_balance(session, test_tenant_id)

    assert len(trial_balance) > 0
    assert all('account_number' in acc for acc in trial_balance)
    assert all('balance' in acc for acc in trial_balance)
    assert all(acc['total_debit'] >= 0 for acc in trial_balance)
    assert all(acc['total_credit'] >= 0 for acc in trial_balance)


@pytest.mark.asyncio
async def test_get_non_existent_account(
    session: AsyncSession, test_tenant_id: str
):
    """Test retrieving non-existent account"""

    account = await AccountService.get_account(session, test_tenant_id, 99999)

    assert account is None


@pytest.mark.asyncio
async def test_update_non_existent_account(
    session: AsyncSession, test_tenant_id: str
):
    """Test updating non-existent account"""

    payload = AccountUpdate(account_name='Updated')

    with pytest.raises(ValueError) as exc:
        await AccountService.update_account(
            session, test_tenant_id, 99999, payload
        )

    assert 'not found' in str(exc.value)


@pytest.mark.asyncio
async def test_deactivate_non_existent_account(
    session: AsyncSession, test_tenant_id: str
):
    """Test deactivating non-existent account"""

    with pytest.raises(ValueError) as exc:
        await AccountService.deactivate_account(session, test_tenant_id, 99999)

    assert 'not found' in str(exc.value)
