"""
Tests for Sevas Module (Phase 3B)

Tests for:
- Seva category management
- Seva CRUD operations
- Booking workflow (create, advance, complete, cancel, refund)
- Accounting integration
- Reporting
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from modules.mandir.sevas.models import Seva, SevaCategory, SevaBooking, SevaBookingStatus
from modules.mandir.sevas.service import (
    create_seva_category, list_seva_categories,
    create_seva, get_seva, list_sevas, update_seva,
    create_seva_booking, get_seva_booking, list_seva_bookings,
    record_booking_advance, complete_seva_booking,
    cancel_seva_booking, request_refund,
    get_booking_schedule, get_seva_revenue_report
)
from modules.mandir.sevas.schemas import (
    SevaCategoryCreate, SevaCreate, SevaBookingCreate,
    SevaBookingAdvanceRequest, SevaBookingCompletionRequest,
    SevaBookingRefundRequest
)
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
async def test_seva_category(db_session: AsyncSession, test_tenant_id: str, test_temple):
    """Create a test seva category"""
    payload = SevaCategoryCreate(
        name='Pujas',
        description='Daily pujas and rituals'
    )
    category = await create_seva_category(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload
    )
    await db_session.commit()
    return category


@pytest.fixture
async def test_seva(db_session: AsyncSession, test_tenant_id: str, test_temple, test_seva_category):
    """Create a test seva"""
    payload = SevaCreate(
        name='Rudra Abhisheka',
        category_id=test_seva_category.id,
        description='Abhisheka of Lord Shiva',
        price=Decimal('5000.00'),
        account_id=4001,
        requires_advance=True,
        advance_amount=Decimal('2000.00')
    )
    seva = await create_seva(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()
    return seva


# ============================================================================
# SEVA CATEGORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_seva_category(db_session: AsyncSession, test_tenant_id: str, test_temple):
    """Test creating a seva category"""
    payload = SevaCategoryCreate(
        name='Rituals',
        description='Special rituals'
    )

    category = await create_seva_category(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload
    )

    assert category.name == 'Rituals'
    assert category.temple_id == test_temple.id
    assert category.tenant_id == test_tenant_id
    assert category.is_active is True


@pytest.mark.asyncio
async def test_list_seva_categories(db_session: AsyncSession, test_tenant_id: str, test_temple):
    """Test listing seva categories"""
    # Create multiple categories
    for i in range(3):
        payload = SevaCategoryCreate(
            name=f'Category {i}',
            description=f'Description {i}'
        )
        await create_seva_category(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload
        )

    await db_session.commit()

    categories = await list_seva_categories(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(categories) == 3


# ============================================================================
# SEVA CRUD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_seva(db_session: AsyncSession, test_tenant_id: str, test_temple, test_seva_category):
    """Test creating a seva"""
    payload = SevaCreate(
        name='Sahasra Namavali',
        category_id=test_seva_category.id,
        description='Thousand names recitation',
        price=Decimal('3000.00'),
        account_id=4001,
        requires_advance=False
    )

    seva = await create_seva(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    assert seva.name == 'Sahasra Namavali'
    assert seva.price == Decimal('3000.00')
    assert seva.is_available is True


@pytest.mark.asyncio
async def test_get_seva(db_session: AsyncSession, test_tenant_id: str, test_temple, test_seva):
    """Test retrieving a seva"""
    retrieved = await get_seva(
        db_session,
        test_temple.id,
        test_tenant_id,
        test_seva.id
    )

    assert retrieved is not None
    assert retrieved.name == 'Rudra Abhisheka'
    assert retrieved.price == Decimal('5000.00')


@pytest.mark.asyncio
async def test_list_sevas(db_session: AsyncSession, test_tenant_id: str, test_temple, test_seva):
    """Test listing sevas"""
    sevas = await list_sevas(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(sevas) >= 1
    assert any(s.name == 'Rudra Abhisheka' for s in sevas)


@pytest.mark.asyncio
async def test_update_seva(db_session: AsyncSession, test_tenant_id: str, test_temple, test_seva):
    """Test updating a seva"""
    updated = await update_seva(
        db_session,
        test_temple.id,
        test_tenant_id,
        test_seva.id,
        {'price': Decimal('6000.00'), 'is_available': False}
    )

    assert updated.price == Decimal('6000.00')
    assert updated.is_available is False


# ============================================================================
# SEVA BOOKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_booking_without_advance(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test creating a booking without advance payment"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Rajesh Kumar',
        customer_phone='+91-9876543210',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5)
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    assert booking.customer_name == 'Rajesh Kumar'
    assert booking.total_price == test_seva.price
    assert booking.status == SevaBookingStatus.PENDING
    assert booking.advance_paid == 0


@pytest.mark.asyncio
async def test_create_booking_with_advance(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test creating a booking with advance payment"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Priya Sharma',
        customer_phone='+91-9999999999',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=10),
        advance_amount=Decimal('2000.00'),
        advance_payment_mode='bank'
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    await db_session.commit()

    assert booking.advance_paid == Decimal('2000.00')
    assert booking.status == SevaBookingStatus.CONFIRMED
    assert booking.advance_journal_entry_id is not None


@pytest.mark.asyncio
async def test_get_booking(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test retrieving a booking"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Test Customer',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5)
    )

    created = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    retrieved = await get_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        created.id
    )

    assert retrieved is not None
    assert retrieved.customer_name == 'Test Customer'


@pytest.mark.asyncio
async def test_list_bookings(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test listing bookings"""
    # Create multiple bookings
    for i in range(3):
        payload = SevaBookingCreate(
            seva_id=test_seva.id,
            customer_name=f'Customer {i}',
            quantity=1,
            scheduled_date=date.today() + timedelta(days=5+i)
        )
        await create_seva_booking(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    bookings, total = await list_seva_bookings(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(bookings) == 3
    assert total == 3


# ============================================================================
# BOOKING PAYMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_record_advance_payment(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test recording advance payment for a booking"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Advance Test',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5)
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    advance_payload = SevaBookingAdvanceRequest(
        amount=Decimal('1500.00'),
        payment_mode='bank',
        notes='Advance payment'
    )

    updated = await record_booking_advance(
        db_session,
        test_temple.id,
        test_tenant_id,
        booking.id,
        advance_payload,
        'test_user_id'
    )

    assert updated.advance_paid == Decimal('1500.00')
    assert updated.status == SevaBookingStatus.CONFIRMED


@pytest.mark.asyncio
async def test_complete_booking(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test completing a booking"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Completion Test',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5),
        advance_amount=Decimal('2000.00'),
        advance_payment_mode='bank'
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    completion_payload = SevaBookingCompletionRequest(
        completion_date=date.today(),
        amount=Decimal('3000.00'),
        payment_mode='bank',
        notes='Seva completed'
    )

    completed = await complete_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        booking.id,
        completion_payload,
        'test_user_id'
    )

    assert completed.status == SevaBookingStatus.COMPLETED
    assert completed.completion_paid == Decimal('3000.00')


@pytest.mark.asyncio
async def test_cancel_booking(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test cancelling a booking"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Cancel Test',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5),
        advance_amount=Decimal('1000.00'),
        advance_payment_mode='cash'
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    cancelled = await cancel_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        booking.id,
        'Customer requested cancellation',
        'test_user_id'
    )

    assert cancelled.is_cancelled is True
    assert cancelled.status == SevaBookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_request_refund(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test requesting a refund"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Refund Test',
        quantity=1,
        scheduled_date=date.today() + timedelta(days=5),
        advance_amount=Decimal('2000.00'),
        advance_payment_mode='bank'
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )
    await db_session.commit()

    refund_payload = SevaBookingRefundRequest(
        refund_amount=Decimal('1000.00'),
        reason='Partial refund requested',
        refund_mode='bank'
    )

    refunded = await request_refund(
        db_session,
        test_temple.id,
        test_tenant_id,
        booking.id,
        refund_payload,
        'test_user_id'
    )

    assert refunded.refund_amount == Decimal('1000.00')
    assert refunded.status == SevaBookingStatus.REFUND_REQUESTED


# ============================================================================
# REPORTING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_booking_schedule_report(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test booking schedule report"""
    today = date.today()
    scheduled_date = today + timedelta(days=3)

    # Create bookings with advance
    for i in range(2):
        payload = SevaBookingCreate(
            seva_id=test_seva.id,
            customer_name=f'Customer {i}',
            quantity=1,
            scheduled_date=scheduled_date,
            advance_amount=Decimal('2000.00'),
            advance_payment_mode='bank'
        )
        await create_seva_booking(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    schedule = await get_booking_schedule(
        db_session,
        test_temple.id,
        test_tenant_id,
        today,
        today + timedelta(days=10)
    )

    assert scheduled_date.isoformat() in schedule


@pytest.mark.asyncio
async def test_revenue_report(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test seva revenue report"""
    # Create bookings
    for i in range(3):
        payload = SevaBookingCreate(
            seva_id=test_seva.id,
            customer_name=f'Customer {i}',
            quantity=1,
            scheduled_date=date.today() + timedelta(days=5),
            advance_amount=Decimal('1000.00'),
            advance_payment_mode='bank'
        )
        await create_seva_booking(
            db_session,
            test_temple.id,
            test_tenant_id,
            payload,
            'test_user_id'
        )

    await db_session.commit()

    report = await get_seva_revenue_report(
        db_session,
        test_temple.id,
        test_tenant_id
    )

    assert len(report) > 0
    seva_report = [r for r in report if r['seva_id'] == test_seva.id][0]
    assert seva_report['total_bookings'] == 3


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_booking_to_dict(
    db_session: AsyncSession,
    test_tenant_id: str,
    test_temple,
    test_seva
):
    """Test booking.to_dict() serialization"""
    payload = SevaBookingCreate(
        seva_id=test_seva.id,
        customer_name='Dict Test',
        quantity=2,
        scheduled_date=date.today() + timedelta(days=5),
        advance_amount=Decimal('2000.00'),
        advance_payment_mode='bank'
    )

    booking = await create_seva_booking(
        db_session,
        test_temple.id,
        test_tenant_id,
        payload,
        'test_user_id'
    )

    booking_dict = booking.to_dict()

    assert booking_dict['customer_name'] == 'Dict Test'
    assert booking_dict['quantity'] == 2
    assert booking_dict['advance_paid'] == '2000.00'
    assert 'created_at' in booking_dict
