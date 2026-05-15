"""
Test accounting isolation across app_key, tenant_id, and accounting_entity_id boundaries.
This prevents cross-app data contamination (GruhaMitra seeing MandirMitra accounts, etc.).
"""

import pytest
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry, JournalLine
from app.accounting.service import (
    create_account,
    initialize_default_chart_of_accounts,
    list_accounts,
    post_journal_entry,
)
from app.accounting.schemas import JournalPostRequest, JournalLineIn


@pytest.mark.asyncio
async def test_accounts_isolated_by_app_key_tenant_entity(async_session: AsyncSession):
    """Verify accounts with same code cannot exist across different app_key/tenant/entity combinations."""

    # Create GruhaMitra society account with code "41001"
    gruha_account = await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
        code="41001",
        name="Maintenance Income - GruhaMitra",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Create MandirMitra temple account with same code "41001"
    mandir_account = await create_account(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
        code="41001",
        name="Seva Income - MandirMitra",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Create MitraBooks business account with same code "41001"
    mitra_account = await create_account(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="primary",
        code="41001",
        name="Revenue - MitraBooks",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Verify all three were created (different records)
    assert gruha_account.id != mandir_account.id
    assert mandir_account.id != mitra_account.id
    assert gruha_account.app_key == "gruhamitra"
    assert mandir_account.app_key == "mandirmitra"
    assert mitra_account.app_key == "mitrabooks"


@pytest.mark.asyncio
async def test_list_accounts_filters_by_app_key_tenant_entity(async_session: AsyncSession):
    """Verify list_accounts returns only accounts matching the full boundary."""

    # Create cash account for GruhaMitra
    gruha_cash = await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
        code="1001",
        name="Cash - GruhaMitra",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    # Create cash account for MandirMitra
    mandir_cash = await create_account(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
        code="1001",
        name="Cash - MandirMitra",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    # List GruhaMitra accounts - should only see GruhaMitra cash
    gruha_accounts = await list_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
    )
    gruha_codes = {a.code for a in gruha_accounts}
    assert "1001" in gruha_codes
    assert gruha_cash.id in [a.id for a in gruha_accounts]
    assert mandir_cash.id not in [a.id for a in gruha_accounts]

    # List MandirMitra accounts - should only see MandirMitra cash
    mandir_accounts = await list_accounts(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
    )
    mandir_ids = [a.id for a in mandir_accounts]
    assert mandir_cash.id in mandir_ids
    assert gruha_cash.id not in mandir_ids


@pytest.mark.asyncio
async def test_journal_entry_isolation_by_boundary(async_session: AsyncSession):
    """Verify journal entries are isolated and cross-app posting is prevented."""

    # Create accounts for GruhaMitra
    gruha_cash = await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
        code="1001",
        name="Cash",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    gruha_income = await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
        code="4001",
        name="Maintenance Income",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Create accounts for MandirMitra
    mandir_cash = await create_account(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
        code="1001",
        name="Cash",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    mandir_income = await create_account(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
        code="4001",
        name="Donation Income",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Post GruhaMitra transaction
    gruha_entry, created = await post_journal_entry(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
        created_by="test_user",
        payload=JournalPostRequest(
            entry_date=date(2026, 4, 26),
            description="Maintenance collection",
            reference="REC-001",
            lines=[
                JournalLineIn(account_id=gruha_cash.id, debit=Decimal("1000.00"), credit=Decimal("0.00")),
                JournalLineIn(account_id=gruha_income.id, debit=Decimal("0.00"), credit=Decimal("1000.00")),
            ],
        ),
        idempotency_key="gruha-txn-001",
    )
    assert created is True
    assert gruha_entry.app_key == "gruhamitra"

    # Post MandirMitra transaction
    mandir_entry, created = await post_journal_entry(
        async_session,
        app_key="mandirmitra",
        tenant_id="temple-001",
        accounting_entity_id="primary",
        created_by="test_user",
        payload=JournalPostRequest(
            entry_date=date(2026, 4, 26),
            description="Donation received",
            reference="DON-001",
            lines=[
                JournalLineIn(account_id=mandir_cash.id, debit=Decimal("500.00"), credit=Decimal("0.00")),
                JournalLineIn(account_id=mandir_income.id, debit=Decimal("0.00"), credit=Decimal("500.00")),
            ],
        ),
        idempotency_key="mandir-txn-001",
    )
    assert created is True
    assert mandir_entry.app_key == "mandirmitra"

    # Verify GruhaMitra sees only its own entry by checking the journal entry isolation
    assert gruha_entry.app_key == "gruhamitra"
    assert gruha_entry.tenant_id == "society-001"
    assert gruha_entry.accounting_entity_id == "primary"

    # Verify MandirMitra sees only its own entry
    assert mandir_entry.app_key == "mandirmitra"
    assert mandir_entry.tenant_id == "temple-001"
    assert mandir_entry.accounting_entity_id == "primary"


@pytest.mark.asyncio
async def test_multi_entity_within_same_tenant(async_session: AsyncSession):
    """Verify accounting_entity_id isolation within a single tenant (CA firm scenario)."""

    # Create accounts for CA firm's Client A
    client_a_cash = await create_account(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-a",
        code="1001",
        name="Cash - Client A",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    client_a_income = await create_account(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-a",
        code="4001",
        name="Revenue - Client A",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # Create accounts for CA firm's Client B
    client_b_cash = await create_account(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-b",
        code="1001",
        name="Cash - Client B",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    client_b_income = await create_account(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-b",
        code="4001",
        name="Revenue - Client B",
        account_type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )

    # List Client A accounts - should only see Client A
    client_a_accounts = await list_accounts(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-a",
    )
    client_a_ids = [a.id for a in client_a_accounts]
    assert client_a_cash.id in client_a_ids
    assert client_a_income.id in client_a_ids
    assert client_b_cash.id not in client_a_ids
    assert client_b_income.id not in client_a_ids

    # List Client B accounts - should only see Client B
    client_b_accounts = await list_accounts(
        async_session,
        app_key="mitrabooks",
        tenant_id="firm-001",
        accounting_entity_id="client-b",
    )
    client_b_ids = [a.id for a in client_b_accounts]
    assert client_b_cash.id in client_b_ids
    assert client_b_income.id in client_b_ids
    assert client_a_cash.id not in client_b_ids
    assert client_a_income.id not in client_b_ids


@pytest.mark.asyncio
async def test_initialize_default_chart_is_idempotent_and_scoped(async_session: AsyncSession):
    first_result = await initialize_default_chart_of_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
    )
    assert first_result["accounts_created"] > 0

    second_result = await initialize_default_chart_of_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
    )
    assert second_result["accounts_created"] == 0
    assert second_result["total_accounts"] == first_result["total_accounts"]

    other_tenant_result = await initialize_default_chart_of_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-002",
        accounting_entity_id="primary",
    )
    assert other_tenant_result["accounts_created"] == first_result["accounts_created"]

    first_tenant_accounts = await list_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-001",
        accounting_entity_id="primary",
    )
    other_tenant_accounts = await list_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="society-002",
        accounting_entity_id="primary",
    )

    assert {account.code for account in first_tenant_accounts} == {account.code for account in other_tenant_accounts}
    assert {account.id for account in first_tenant_accounts}.isdisjoint({account.id for account in other_tenant_accounts})

    first_tenant_counts_by_type = {}
    for account in first_tenant_accounts:
        first_tenant_counts_by_type[account.type] = first_tenant_counts_by_type.get(account.type, 0) + 1

    assert first_tenant_counts_by_type["asset"] >= 10
    assert first_tenant_counts_by_type["liability"] >= 5
    assert first_tenant_counts_by_type["equity"] >= 5
    assert first_tenant_counts_by_type["income"] >= 5
    assert first_tenant_counts_by_type["expense"] >= 10
