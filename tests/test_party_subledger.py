"""Party sub-ledger (party_id on journal lines) — party-wise Debtors/Creditors
that ties to the Trial Balance, per-party outstanding, and reversal tag retention."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalLine
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    get_party_outstanding,
    get_party_wise_balances,
    get_trial_balance,
    post_journal_entry,
    reverse_journal_entry,
)

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"


async def _account(session, *, tenant_id, code, name, account_type, classification,
                   is_cash_bank=False, is_receivable=False, is_payable=False) -> Account:
    acc = Account(
        app_key=APP_KEY, tenant_id=tenant_id, accounting_entity_id=ENTITY_ID,
        code=code, name=name, type=account_type, classification=classification,
        is_cash_bank=is_cash_bank, is_receivable=is_receivable, is_payable=is_payable,
    )
    session.add(acc)
    return acc


async def _setup_accounts(session, tenant_id):
    recv = await _account(session, tenant_id=tenant_id, code="12001", name="Sundry Debtors",
                          account_type="asset", classification="personal", is_receivable=True)
    cash = await _account(session, tenant_id=tenant_id, code="11010", name="Bank",
                          account_type="asset", classification="real", is_cash_bank=True)
    income = await _account(session, tenant_id=tenant_id, code="41001", name="Sales",
                            account_type="income", classification="nominal")
    await session.commit()
    return recv, cash, income


async def _post(session, tenant_id, *, lines, key, entry_date=date(2026, 6, 1)):
    entry, _ = await post_journal_entry(
        session, tenant_id=tenant_id, app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
        created_by="tester",
        payload=JournalPostRequest(entry_date=entry_date, description="t", reference=key, lines=lines),
        idempotency_key=key,
    )
    return entry


@pytest.mark.asyncio
async def test_party_wise_receivables_tie_to_trial_balance(async_session: AsyncSession):
    tenant = "tenant-subledger-1"
    recv, cash, income = await _setup_accounts(async_session, tenant)

    # Customer A invoice 1000, Customer B invoice 600, A receipt 400, and a manual
    # receivable entry with NO party (the "Unallocated" bucket).
    await _post(async_session, tenant, key="invA", lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("1000"), credit=Decimal("0"), party_id="cust-A"),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("1000")),
    ])
    await _post(async_session, tenant, key="invB", lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("600"), credit=Decimal("0"), party_id="cust-B"),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("600")),
    ])
    await _post(async_session, tenant, key="rcptA", lines=[
        JournalLineIn(account_id=cash.id, debit=Decimal("400"), credit=Decimal("0")),
        JournalLineIn(account_id=recv.id, debit=Decimal("0"), credit=Decimal("400"), party_id="cust-A"),
    ])
    await _post(async_session, tenant, key="manual", lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("100"), credit=Decimal("0")),  # no party
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("100")),
    ])

    lines, total = await get_party_wise_balances(
        async_session, tenant_id=tenant, as_of=date(2026, 6, 30), kind="receivable",
        app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
    )
    by_party = {l["party_id"]: l["balance"] for l in lines}
    assert by_party["cust-A"] == Decimal("600.00")   # 1000 - 400
    assert by_party["cust-B"] == Decimal("600.00")
    assert by_party[None] == Decimal("100.00")        # Unallocated bucket
    assert total == Decimal("1300.00")

    # Ties to the Trial Balance: Sundry Debtors net == party-wise total.
    tb_lines, _td, _tc = await get_trial_balance(
        async_session, tenant_id=tenant, as_of=date(2026, 6, 30), app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
    )
    recv_net = next(l["net_balance"] for l in tb_lines if l["account_code"] == "12001")
    assert recv_net == total == Decimal("1300.00")


@pytest.mark.asyncio
async def test_party_outstanding_after_partial_receipt(async_session: AsyncSession):
    tenant = "tenant-subledger-2"
    recv, cash, income = await _setup_accounts(async_session, tenant)
    await _post(async_session, tenant, key="inv", lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("1000"), credit=Decimal("0"), party_id="cust-X"),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("1000")),
    ])
    await _post(async_session, tenant, key="rcpt", lines=[
        JournalLineIn(account_id=cash.id, debit=Decimal("300"), credit=Decimal("0")),
        JournalLineIn(account_id=recv.id, debit=Decimal("0"), credit=Decimal("300"), party_id="cust-X"),
    ])
    out = await get_party_outstanding(
        async_session, tenant_id=tenant, party_id="cust-X", as_of=date(2026, 6, 30),
        app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
    )
    assert out["receivable"] == Decimal("700.00")
    assert out["payable"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_party_id_persists_and_reversal_retains_it(async_session: AsyncSession):
    tenant = "tenant-subledger-3"
    recv, cash, income = await _setup_accounts(async_session, tenant)
    entry = await _post(async_session, tenant, key="inv", lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("500"), credit=Decimal("0"), party_id="cust-Z"),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("500")),
    ])
    # party_id persisted on the receivable line only.
    rows = (await async_session.execute(
        select(JournalLine.account_id, JournalLine.party_id).where(JournalLine.journal_id == entry.id)
    )).all()
    tags = {acc: pid for acc, pid in rows}
    assert tags[recv.id] == "cust-Z"
    assert tags[income.id] is None

    reversal, _ = await reverse_journal_entry(
        async_session, tenant_id=tenant, journal_id=entry.id, app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, created_by="tester", reversal_date=date(2026, 6, 5),
        idempotency_key="rev-inv",
    )
    rev_rows = (await async_session.execute(
        select(JournalLine.account_id, JournalLine.party_id).where(JournalLine.journal_id == reversal.id)
    )).all()
    rev_tags = {acc: pid for acc, pid in rev_rows}
    assert rev_tags[recv.id] == "cust-Z"  # reversal keeps the sub-ledger tag

    # Net receivable for the party is zero after reversal.
    out = await get_party_outstanding(
        async_session, tenant_id=tenant, party_id="cust-Z", as_of=date(2026, 6, 30),
        app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
    )
    assert out["receivable"] == Decimal("0.00")


@pytest.mark.asyncio
async def test_party_wise_rejects_bad_kind(async_session: AsyncSession):
    from app.accounting.service import AccountingValidationError
    with pytest.raises(AccountingValidationError):
        await get_party_wise_balances(
            async_session, tenant_id="t", as_of=date(2026, 6, 30), kind="bogus",
            app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
        )
