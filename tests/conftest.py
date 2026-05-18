"""
Phase 1: Foundation - Pytest Configuration and Fixtures

Provides test fixtures for:
- Database (PostgreSQL, MongoDB)
- HTTP client
- Authentication (JWT tokens)
- Test data

Usage in tests:
    def test_something(async_session, mongo_client, auth_token):
        # Use fixtures
        pass
"""

import pytest
import pytest_asyncio

# These suites target the pre-unification package layout (`modules.*`) and
# service contracts that are not present in this workspace. Keep them out of
# active collection until they are rewritten against `app.accounting` and the
# Mandir compatibility modules; current replacement coverage lives in the
# `test_accounting_*` and `test_mandir_*` suites.
collect_ignore = [
    "test_core_accounting_journal.py",
    "test_core_accounting_reconciliation.py",
    "test_core_accounting_service.py",
    "test_donations.py",
    "test_sevas.py",
    "test_temples.py",
]
from httpx import AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import json
import os

from app.phase1_main import app
from app.config import get_settings
import app.db.mongo as runtime_mongo
from app.phase1_config import settings
from app.db.phase1_postgres import Base, get_async_session
from app.db.phase1_mongo import get_collection
from app.core.phase1_auth import create_access_token
from app.accounting.models.base import Base as AccountingBase
from app.accounting.models import Account, JournalEntry, JournalLine


# ============================================================================
# Database Fixtures
# ============================================================================


def _resolve_test_db_url() -> str:
    # Highest priority: explicit test connection.
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit

    # Next: reuse runtime Postgres URI if provided in env.
    runtime_pg = os.getenv("POSTGRES_URI", "").strip()
    if runtime_pg:
        return str(make_url(runtime_pg).set(database="sanmitra_test"))

    # Fallback: Phase-1 config URL.
    return str(make_url(settings.DATABASE_URL).set(database="sanmitra_test"))


@pytest_asyncio.fixture(scope="session")
async def postgres_engine():
    """
    Create test database engine.
    Uses in-memory SQLite for isolation tests, PostgreSQL for main app tests.
    """
    # For accounting isolation tests, try to use SQLite in-memory first
    # Fall back to PostgreSQL if available
    try:
        # Try SQLite in-memory for faster, isolated tests
        from sqlalchemy.ext.asyncio import create_async_engine as create_engine
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        async with engine.begin() as conn:
            # Create Phase 1 tables
            await conn.run_sync(Base.metadata.create_all)
            # Create accounting tables
            await conn.run_sync(AccountingBase.metadata.create_all)

        yield engine
        await engine.dispose()
    except Exception as sqlite_exc:
        # Fall back to PostgreSQL test database
        test_db_url = _resolve_test_db_url()

        engine = create_async_engine(
            test_db_url,
            echo=False,
        )

        # Create all tables; skip postgres-backed tests when local DB is unavailable.
        try:
            async with engine.begin() as conn:
                # Create Phase 1 tables
                await conn.run_sync(Base.metadata.create_all)
                # Create accounting tables
                await conn.run_sync(AccountingBase.metadata.create_all)
        except Exception as exc:  # pragma: no cover - environment dependent
            await engine.dispose()
            pytest.skip(f"Neither SQLite nor PostgreSQL test database available: SQLite failed ({sqlite_exc}), PostgreSQL failed ({exc})")

        yield engine

        # Cleanup: Drop all tables
        async with engine.begin() as conn:
            await conn.run_sync(AccountingBase.metadata.drop_all)
            await conn.run_sync(Base.metadata.drop_all)

        await engine.dispose()


@pytest_asyncio.fixture
async def async_session(postgres_engine):
    """
    Provide AsyncSession for individual tests.
    Each test gets a fresh session that rolls back after test for isolation.

    Note: For in-memory SQLite, we need to clear tables before each test
    since all tests share the same in-memory database.
    """
    session_maker = async_sessionmaker(
        postgres_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Clear all tables before the test (for SQLite in-memory database isolation)
    async with session_maker() as clear_session:
        from sqlalchemy import text
        async with clear_session.begin():
            # Delete all data from accounting tables to ensure test isolation
            await clear_session.execute(text("DELETE FROM journal_lines"))
            await clear_session.execute(text("DELETE FROM journal_entries"))
            await clear_session.execute(text("DELETE FROM accounts"))
            await clear_session.execute(text("DELETE FROM coa_mappings"))
            await clear_session.execute(text("DELETE FROM coa_source_accounts"))

    # Now create a fresh session for the test
    session = session_maker()
    try:
        yield session
    finally:
        # Rollback all changes to ensure test isolation
        await session.rollback()
        await session.close()

@pytest_asyncio.fixture
async def db_session(async_session):
    """
    Backward-compatible alias for older tests that still request db_session.
    """
    yield async_session


@pytest_asyncio.fixture
async def session(async_session):
    """
    Backward-compatible alias for tests expecting `session`.
    """
    yield async_session


@pytest_asyncio.fixture
async def mongo_client():
    """
    Provide MongoDB client for tests.
    Uses test database.
    """
    client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,
    )
    runtime_settings = get_settings()
    original_runtime_client = runtime_mongo._client
    original_runtime_db_name = runtime_settings.MONGO_DB_NAME
    runtime_mongo._client = client
    runtime_settings.MONGO_DB_NAME = "sanmitra_test"

    try:
        yield client
    finally:
        # Cleanup: Drop test database and restore app-global Mongo state.
        await client.drop_database("sanmitra_test")
        runtime_mongo._client = original_runtime_client
        runtime_settings.MONGO_DB_NAME = original_runtime_db_name
        client.close()


# ============================================================================
# HTTP Client Fixture
# ============================================================================


@pytest_asyncio.fixture
async def http_client():
    """
    Provide AsyncClient for testing HTTP endpoints.
    Uses test FastAPI app.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def test_tenant_id():
    """Test tenant ID for multi-tenant isolation tests."""
    return "test-tenant-001"


@pytest.fixture
def test_app_key():
    """Test app key (mandirmitra, gruhamitra, etc.)."""
    return "mandirmitra"


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return "test-user-001"


@pytest.fixture
def auth_token(test_user_id, test_tenant_id, test_app_key):
    """
    Create a valid JWT token for testing.

    Usage:
        def test_protected_endpoint(http_client, auth_token):
            response = await http_client.get(
                "/api/v1/donations",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
    """
    return create_access_token(
        subject=test_user_id,
        tenant_id=test_tenant_id,
        app_key=test_app_key,
        expires_delta=timedelta(hours=24),
    )


@pytest.fixture
def auth_headers(auth_token):
    """
    Authorization headers for HTTP requests.

    Usage:
        def test_protected_endpoint(http_client, auth_headers):
            response = await http_client.get(
                "/api/v1/donations",
                headers=auth_headers
            )
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def multi_tenant_auth_token(test_user_id, test_app_key):
    """
    Create JWT token for different tenant (for isolation tests).
    """
    other_tenant = "test-tenant-002"
    return create_access_token(
        subject=test_user_id,
        tenant_id=other_tenant,
        app_key=test_app_key,
        expires_delta=timedelta(hours=24),
    )


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_donation_payload():
    """
    Sample donation creation payload for tests.

    Usage:
        def test_create_donation(http_client, auth_headers, sample_donation_payload):
            response = await http_client.post(
                "/api/v1/donations",
                json=sample_donation_payload,
                headers=auth_headers
            )
    """
    return {
        "amount": 1000.00,
        "category": "General Donations",
        "donor_name": "Test Donor",
        "donor_phone": "9876543210",
        "payment_mode": "cash",
        "notes": "Test donation",
        "idempotency_key": "test-donation-001",
    }


@pytest.fixture
def sample_journal_entry_payload():
    """
    Sample journal entry creation payload for tests.

    Debits and credits are balanced (critical for journal validation).
    """
    return {
        "entry_date": datetime.utcnow().isoformat(),
        "description": "Test journal entry",
        "reference": "test:donation:001",
        "lines": [
            {
                "account_id": 1001,  # Bank account
                "debit": 1000.00,
                "credit": 0.00,
                "description": "Cash received",
            },
            {
                "account_id": 4001,  # Income account
                "debit": 0.00,
                "credit": 1000.00,
                "description": "Donation income",
            },
        ],
    }


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def mock_audit_event():
    """
    Sample audit event for testing audit logging.
    """
    return {
        "entity_type": "donation",
        "entity_id": "donation-001",
        "action": "created",
        "user_id": "user-001",
        "tenant_id": "tenant-001",
        "before_state": None,
        "after_state": {
            "amount": 1000.00,
            "category": "General",
            "donor_name": "Test",
        },
    }


@pytest.fixture
def request_context(test_user_id, test_tenant_id, test_app_key):
    """
    Sample request context (user + tenant info).

    Mirrors what's passed from app.core.phase1_dependencies.get_request_context()
    """
    return {
        "user_id": test_user_id,
        "tenant_id": test_tenant_id,
        "app_key": test_app_key,
    }


# ============================================================================
# Configuration and Markers
# ============================================================================


def pytest_configure(config):
    """
    Register custom pytest markers.

    Usage:
        @pytest.mark.asyncio
        async def test_async_function():
            pass

        @pytest.mark.unit
        def test_unit():
            pass

        @pytest.mark.integration
        async def test_integration(async_session):
            pass
    """
    config.addinivalue_line("markers", "unit: Unit tests (isolated, no DB)")
    config.addinivalue_line("markers", "integration: Integration tests (with DB)")
    config.addinivalue_line("markers", "asyncio: Async tests")


# ============================================================================
# Async Context Manager for Multiple Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def services_context(async_session, mongo_client, test_tenant_id):
    """
    Combined fixture for services that need both PostgreSQL and MongoDB.

    Usage:
        async def test_donation_service(services_context):
            session, db, tenant_id = services_context
            # Use both session and db
    """
    return (async_session, mongo_client, test_tenant_id)


# ============================================================================
# Phase 2: Core_Accounting Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_accounts(async_session, test_tenant_id):
    """
    Create test chart of accounts for accounting tests.

    Provides: cash, bank, income, expense accounts ready for testing.
    """
    from modules.core_accounting.models.entities import Account

    accounts = {
        'cash': Account(
            tenant_id=test_tenant_id,
            account_number='1000',
            account_name='Cash',
            account_type='asset',
            account_category='Current Assets'
        ),
        'bank': Account(
            tenant_id=test_tenant_id,
            account_number='1010',
            account_name='Bank Account',
            account_type='asset',
            account_category='Current Assets'
        ),
        'receivables': Account(
            tenant_id=test_tenant_id,
            account_number='1200',
            account_name='Accounts Receivable',
            account_type='asset',
            account_category='Current Assets'
        ),
        'liability': Account(
            tenant_id=test_tenant_id,
            account_number='2000',
            account_name='Accounts Payable',
            account_type='liability',
            account_category='Current Liabilities'
        ),
        'equity': Account(
            tenant_id=test_tenant_id,
            account_number='3000',
            account_name='Retained Earnings',
            account_type='equity',
            account_category='Equity'
        ),
        'income': Account(
            tenant_id=test_tenant_id,
            account_number='4000',
            account_name='Donation Income',
            account_type='income',
            account_category='Revenue'
        ),
        'service_income': Account(
            tenant_id=test_tenant_id,
            account_number='4100',
            account_name='Service Income',
            account_type='income',
            account_category='Revenue'
        ),
        'expense': Account(
            tenant_id=test_tenant_id,
            account_number='5000',
            account_name='Operating Expense',
            account_type='expense',
            account_category='Operating Expenses'
        ),
        'utilities': Account(
            tenant_id=test_tenant_id,
            account_number='5100',
            account_name='Utilities',
            account_type='expense',
            account_category='Operating Expenses'
        ),
    }

    # Add all accounts to session
    for account in accounts.values():
        async_session.add(account)

    await async_session.commit()

    # Refresh to get IDs
    for account in accounts.values():
        await async_session.refresh(account)

    return accounts

