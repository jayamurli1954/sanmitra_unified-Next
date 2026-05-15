"""
Tests for Temples Module (Phase 3C)

Tests for:
- Temple CRUD operations
- Bank account management
- Module enable/disable
- Multi-tenancy isolation
"""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.legacy_reference
pytest.skip(
    "Legacy MandirMitra Phase 3 temple tests target the removed modules.mandir package; "
    "current bootstrap coverage uses app.modules.mandir_compat tests.",
    allow_module_level=True,
)

from modules.mandir.temples.models import Temple, BankAccount
from modules.mandir.temples.service import (
    create_temple,
    get_temple,
    list_temples,
    update_temple,
    add_bank_account,
    list_bank_accounts,
    get_default_bank_account,
    enable_module,
    disable_module,
)
from modules.mandir.temples.schemas import (
    TempleCreateRequest,
    BankAccountCreateRequest,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def test_temple(db_session: AsyncSession, test_tenant_id: str):
    """Create a test temple"""
    temple_data = {
        'name': 'Test Temple',
        'primary_deity': 'Test Deity',
        'address': '123 Temple St',
        'phone': '+91-9876543210',
        'email': 'test@temple.com',
        'bank_account_number': '1234567890',
        'ifsc': 'HDFC0000001',
        'account_holder': 'Temple Trust',
        'financial_year_start': '04-01',
    }

    temple = await create_temple(
        db_session,
        test_tenant_id,
        'Test Temple',
        temple_data,
        'test_user_id'
    )
    await db_session.commit()
    return temple


# ============================================================================
# TEMPLE CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_temple(db_session: AsyncSession, test_tenant_id: str):
    """Test creating a new temple with bank account"""
    temple_data = {
        'name': 'Sri Veerabhadra Temple',
        'primary_deity': 'Sri Veerabhadra',
        'address': '456 Shrine Road',
        'phone': '+91-9999999999',
        'email': 'veerabhadra@temple.com',
        'bank_account_number': '0987654321',
        'ifsc': 'ICIC0000002',
        'account_holder': 'Temple Trust',
        'financial_year_start': '04-01',
    }

    temple = await create_temple(
        db_session,
        test_tenant_id,
        'Sri Veerabhadra Temple',
        temple_data,
        'test_user_id'
    )

    assert temple.name == 'Sri Veerabhadra Temple'
    assert temple.tenant_id == test_tenant_id
    assert temple.primary_deity == 'Sri Veerabhadra'
    assert temple.address == '456 Shrine Road'
    assert temple.phone == '+91-9999999999'
    assert temple.email == 'veerabhadra@temple.com'
    assert temple.financial_year_start == '04-01'
    assert temple.module_donations is True
    assert temple.module_sevas is True
    assert temple.bank_account_id is not None


@pytest.mark.asyncio
async def test_get_temple(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test retrieving a temple"""
    retrieved = await get_temple(db_session, test_temple.id, test_tenant_id)

    assert retrieved is not None
    assert retrieved.id == test_temple.id
    assert retrieved.name == test_temple.name
    assert retrieved.tenant_id == test_tenant_id


@pytest.mark.asyncio
async def test_get_temple_wrong_tenant(
    db_session: AsyncSession,
    test_temple: Temple
):
    """Test that temple is not retrievable by other tenant"""
    retrieved = await get_temple(db_session, test_temple.id, 'wrong_tenant_id')

    assert retrieved is None


@pytest.mark.asyncio
async def test_list_temples(db_session: AsyncSession, test_tenant_id: str):
    """Test listing temples for a tenant"""
    # Create multiple temples
    for i in range(3):
        temple_data = {
            'name': f'Temple {i}',
            'primary_deity': f'Deity {i}',
            'address': f'Address {i}',
            'phone': f'+91-{i}',
            'email': f'temple{i}@example.com',
            'bank_account_number': f'1234567{i}',
            'ifsc': 'HDFC0000001',
            'account_holder': 'Temple Trust',
            'financial_year_start': '04-01',
        }

        await create_temple(
            db_session,
            test_tenant_id,
            f'Temple {i}',
            temple_data,
            'test_user_id'
        )

    await db_session.commit()

    temples = await list_temples(db_session, test_tenant_id)

    assert len(temples) == 3
    # Check ordered by name
    assert temples[0].name == 'Temple 0'
    assert temples[1].name == 'Temple 1'
    assert temples[2].name == 'Temple 2'


@pytest.mark.asyncio
async def test_update_temple(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test updating temple settings"""
    update_data = {
        'primary_deity': 'Updated Deity',
        'phone': '+91-1111111111',
        'module_sevas': False,
    }

    updated = await update_temple(
        db_session,
        test_temple.id,
        test_tenant_id,
        update_data
    )

    assert updated.primary_deity == 'Updated Deity'
    assert updated.phone == '+91-1111111111'
    assert updated.module_sevas is False
    assert updated.module_donations is True  # unchanged


@pytest.mark.asyncio
async def test_update_temple_not_found(
    db_session: AsyncSession,
    test_tenant_id: str
):
    """Test updating non-existent temple raises error"""
    with pytest.raises(ValueError):
        await update_temple(
            db_session,
            999,
            test_tenant_id,
            {'name': 'Updated'}
        )


# ============================================================================
# BANK ACCOUNT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_add_bank_account(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test adding a bank account to temple"""
    account_data = BankAccountCreateRequest(
        account_number='5555555555',
        ifsc='AXIS0000005',
        account_holder='Secondary Account',
    )

    account = await add_bank_account(
        db_session,
        test_temple.id,
        test_tenant_id,
        account_data
    )

    assert account.temple_id == test_temple.id
    assert account.account_number == '5555555555'
    assert account.ifsc == 'AXIS0000005'
    assert account.is_default is False


@pytest.mark.asyncio
async def test_add_bank_account_temple_not_found(
    db_session: AsyncSession,
    test_tenant_id: str
):
    """Test adding account to non-existent temple raises error"""
    account_data = BankAccountCreateRequest(
        account_number='1234567890',
        ifsc='HDFC0000001',
        account_holder='Test Account',
    )

    with pytest.raises(ValueError):
        await add_bank_account(
            db_session,
            999,
            test_tenant_id,
            account_data
        )


@pytest.mark.asyncio
async def test_list_bank_accounts(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test listing bank accounts for temple"""
    # Add secondary account
    account_data = BankAccountCreateRequest(
        account_number='2222222222',
        ifsc='ICIC0000002',
        account_holder='Secondary Account',
    )

    await add_bank_account(
        db_session,
        test_temple.id,
        test_tenant_id,
        account_data
    )

    await db_session.commit()

    accounts = await list_bank_accounts(db_session, test_temple.id, test_tenant_id)

    assert len(accounts) == 2
    # Default account appears first
    assert accounts[0].is_default is True
    assert accounts[1].is_default is False


@pytest.mark.asyncio
async def test_get_default_bank_account(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test retrieving default bank account"""
    default_account = await get_default_bank_account(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert default_account is not None
    assert default_account.is_default is True
    assert default_account.temple_id == test_temple.id


@pytest.mark.asyncio
async def test_get_default_bank_account_not_set(
    db_session: AsyncSession,
    test_tenant_id: str
):
    """Test getting default account when not set returns None"""
    default_account = await get_default_bank_account(
        db_session,
        999,
        test_tenant_id
    )

    assert default_account is None


# ============================================================================
# MODULE MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_enable_module(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test enabling a module"""
    # Disable sevas first
    await disable_module(db_session, test_temple.id, test_tenant_id, 'sevas')

    # Enable devotees
    temple = await enable_module(
        db_session,
        test_temple.id,
        test_tenant_id,
        'devotees'
    )

    assert temple.module_devotees is True


@pytest.mark.asyncio
async def test_disable_module(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test disabling a module"""
    temple = await disable_module(
        db_session,
        test_temple.id,
        test_tenant_id,
        'donations'
    )

    assert temple.module_donations is False
    assert temple.module_sevas is True  # unchanged


@pytest.mark.asyncio
async def test_enable_invalid_module(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test enabling invalid module raises error"""
    with pytest.raises(ValueError):
        await enable_module(
            db_session,
            test_temple.id,
            test_tenant_id,
            'invalid_module'
        )


@pytest.mark.asyncio
async def test_disable_invalid_module(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test disabling invalid module raises error"""
    with pytest.raises(ValueError):
        await disable_module(
            db_session,
            test_temple.id,
            test_tenant_id,
            'invalid_module'
        )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_temple_to_dict(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test temple.to_dict() serialization"""
    temple_dict = test_temple.to_dict()

    assert temple_dict['id'] == test_temple.id
    assert temple_dict['tenant_id'] == test_tenant_id
    assert temple_dict['name'] == test_temple.name
    assert 'created_at' in temple_dict
    assert 'updated_at' in temple_dict


@pytest.mark.asyncio
async def test_bank_account_to_dict(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple: Temple
):
    """Test bank_account.to_dict() serialization"""
    account = await get_default_bank_account(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    account_dict = account.to_dict()

    assert account_dict['temple_id'] == test_temple.id
    assert account_dict['account_number'] == test_temple.to_dict()['bank_account_id']  # has been set
    assert account_dict['is_default'] is True
    assert 'created_at' in account_dict
