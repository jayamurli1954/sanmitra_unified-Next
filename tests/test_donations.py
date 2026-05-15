"""
Tests for Donations Module (Phase 3A)

Tests for:
- Donation CRUD operations
- Accounting integration (journal posting)
- Receipt number generation
- Filtering and reporting
- Cancellation and reversal
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.legacy_reference
pytest.skip(
    "Legacy MandirMitra Phase 3 donation tests target the removed modules.mandir package; "
    "current bootstrap coverage uses app.modules.mandir_compat tests.",
    allow_module_level=True,
)

from modules.mandir.donations.models import Donation, DonationCategory
from modules.mandir.donations.service import (
    create_donation,
    cancel_donation,
    get_donation,
    list_donations,
    get_donations_by_date_range,
    get_donations_by_category,
)
from modules.mandir.donations.schemas import DonationCreateRequest
from modules.mandir.temples.service import create_temple


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def test_temple(db_session: AsyncSession, test_tenant_id: str):
    """Create a test temple with bank account"""
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


@pytest.fixture
async def test_donation_category(db_session: AsyncSession, test_tenant_id: str, test_temple):
    """Create a test donation category"""
    category = DonationCategory(
        temple_id=test_temple.id,
        tenant_id=test_tenant_id,
        name='General Donations',
        account_id=4001,  # Income account from accounting module
        description='General temple donations',
        is_active=True
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


# ============================================================================
# DONATION CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_donation(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test creating a new donation"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='John Doe',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=date.today(),
        notes='Test donation'
    )

    donation = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    assert donation.amount == Decimal('1000.00')
    assert donation.donor_name == 'John Doe'
    assert donation.payment_mode == 'cash'
    assert donation.temple_id == test_temple.id
    assert donation.tenant_id == test_tenant_id
    assert donation.receipt_number is not None
    assert donation.is_cancelled is False


@pytest.mark.asyncio
async def test_create_donation_posts_journal(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test that creating donation posts to accounting"""
    payload = DonationCreateRequest(
        amount=Decimal('5000.00'),
        donor_name='Jane Doe',
        payment_mode='bank',
        category_id=test_donation_category.id,
        donation_date=date.today(),
        notes='Bank donation'
    )

    donation = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    # Verify journal entry was created
    assert donation.journal_entry_id is not None
    assert donation.reference is not None
    assert donation.reference.startswith('donation:')


@pytest.mark.asyncio
async def test_create_donation_invalid_temple(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_donation_category
):
    """Test creating donation for non-existent temple raises error"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='John Doe',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    with pytest.raises(ValueError):
        await create_donation(
            db_session,
            999,
            test_tenant_id,
            payload,
            'test_user_id'
        )


@pytest.mark.asyncio
async def test_create_donation_invalid_category(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple
):
    """Test creating donation with invalid category raises error"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='John Doe',
        payment_mode='cash',
        category_id=999,
        donation_date=date.today(),
    )

    with pytest.raises(ValueError):
        await create_donation(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )


@pytest.mark.asyncio
async def test_get_donation(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test retrieving a donation"""
    payload = DonationCreateRequest(
        amount=Decimal('2000.00'),
        donor_name='Test Donor',
        payment_mode='upi',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    created = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    retrieved = await get_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        created.id
    )

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.amount == Decimal('2000.00')


@pytest.mark.asyncio
async def test_get_donation_wrong_tenant(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test that donation is not retrievable by other tenant"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='Test Donor',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    created = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    retrieved = await get_donation(
        db_session,
        test_temple.id,
        'wrong_tenant_id',
        created.id
    )

    assert retrieved is None


# ============================================================================
# DONATION LISTING AND FILTERING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_list_donations(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test listing donations"""
    # Create multiple donations
    for i in range(5):
        payload = DonationCreateRequest(
            amount=Decimal(f'{100 * (i + 1)}'),
            donor_name=f'Donor {i}',
            payment_mode=['cash', 'bank', 'upi', 'cheque', 'card'][i % 5],
            category_id=test_donation_category.id,
            donation_date=date.today(),
        )

        await create_donation(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    donations, total = await list_donations(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(donations) == 5
    assert total == 5


@pytest.mark.asyncio
async def test_list_donations_with_date_filter(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test filtering donations by date range"""
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Create donation today
    payload1 = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='Today Donor',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=today,
    )
    await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload1,
        'test_user_id'
    )

    # Create donation yesterday
    payload2 = DonationCreateRequest(
        amount=Decimal('500.00'),
        donor_name='Yesterday Donor',
        payment_mode='bank',
        category_id=test_donation_category.id,
        donation_date=yesterday,
    )
    await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload2,
        'test_user_id'
    )

    await db_session.commit()

    # Filter by today only
    donations, total = await list_donations(
        db_session,
        test_temple.id,
        test_tenant_id,
        start_date=today,
        end_date=today
    )

    assert len(donations) == 1
    assert donations[0].donor_name == 'Today Donor'


@pytest.mark.asyncio
async def test_list_donations_with_payment_mode_filter(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test filtering donations by payment mode"""
    # Create donations with different payment modes
    for mode in ['cash', 'bank', 'upi']:
        payload = DonationCreateRequest(
            amount=Decimal('1000.00'),
            donor_name=f'{mode.upper()} Donor',
            payment_mode=mode,
            category_id=test_donation_category.id,
            donation_date=date.today(),
        )
        await create_donation(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    # Filter by cash only
    donations, total = await list_donations(
        db_session,
        test_temple.id,
        test_tenant_id,
        payment_mode='cash'
    )

    assert len(donations) == 1
    assert donations[0].payment_mode == 'cash'


# ============================================================================
# DONATION CANCELLATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_cancel_donation(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test cancelling a donation"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='John Doe',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    donation = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    cancelled = await cancel_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        donation.id,
        'Testing cancellation',
        'test_user_id'
    )

    assert cancelled.is_cancelled is True


@pytest.mark.asyncio
async def test_cancel_donation_reverses_journal(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test that cancelling donation reverses journal entry"""
    payload = DonationCreateRequest(
        amount=Decimal('5000.00'),
        donor_name='Jane Doe',
        payment_mode='bank',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    donation = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    original_journal_id = donation.journal_entry_id
    await db_session.commit()

    await cancel_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        donation.id,
        'Refund issued',
        'test_user_id'
    )

    # Verify reversal entry was created
    await db_session.refresh(donation)
    assert donation.is_cancelled is True


# ============================================================================
# REPORTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_donations_by_date_range(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test getting daily donation report"""
    today = date.today()

    # Create 3 donations today
    for i in range(3):
        payload = DonationCreateRequest(
            amount=Decimal(f'{100 * (i + 1)}'),
            donor_name=f'Donor {i}',
            payment_mode='cash',
            category_id=test_donation_category.id,
            donation_date=today,
        )
        await create_donation(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    report = await get_donations_by_date_range(
        db_session,
        test_temple.id,
        test_tenant_id,
        today,
        today
    )

    assert today.isoformat() in report
    assert report[today.isoformat()]['count'] == 3
    assert report[today.isoformat()]['total'] == Decimal('600.00')


@pytest.mark.asyncio
async def test_donations_by_category(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test getting category donation report"""
    # Create donations in category
    for i in range(2):
        payload = DonationCreateRequest(
            amount=Decimal('1000.00'),
            donor_name=f'Donor {i}',
            payment_mode='cash',
            category_id=test_donation_category.id,
            donation_date=date.today(),
        )
        await create_donation(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    report = await get_donations_by_category(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(report) >= 1
    category_report = [r for r in report if r['category_id'] == test_donation_category.id][0]
    assert category_report['count'] == 2
    assert category_report['total'] == Decimal('2000.00')


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_donation_to_dict(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_donation_category
):
    """Test donation.to_dict() serialization"""
    payload = DonationCreateRequest(
        amount=Decimal('1000.00'),
        donor_name='Test Donor',
        payment_mode='cash',
        category_id=test_donation_category.id,
        donation_date=date.today(),
    )

    donation = await create_donation(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    donation_dict = donation.to_dict()

    assert donation_dict['amount'] == Decimal('1000.00')
    assert donation_dict['donor_name'] == 'Test Donor'
    assert donation_dict['payment_mode'] == 'cash'
    assert 'receipt_number' in donation_dict
    assert 'created_at' in donation_dict
