"""Live business dashboard — KPIs/balances/trend computed from the posted ledger
(replaces the old hard-coded mock dashboard numbers)."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import get_business_dashboard, post_journal_entry

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"
AS_OF = date(2026, 6, 30)  # FY 2026-27 (starts 2026-04-01)


async def _acct(session, *, tenant_id, code, name, account_type, classification="real",
                is_cash_bank=False, is_receivable=False, is_payable=False) -> Account:
    acc = Account(
        app_key=APP_KEY, tenant_id=tenant_id, accounting_entity_id=ENTITY_ID,
        code=code, name=name, type=account_type, classification=classification,
        is_cash_bank=is_cash_bank, is_receivable=is_receivable, is_payable=is_payable,
    )
    session.add(acc)
    return acc


async def _post(session, tenant_id, *, lines, key, entry_date):
    await post_journal_entry(
        session, tenant_id=tenant_id, app_key=APP_KEY, accounting_entity_id=ENTITY_ID,
        created_by="tester",
        payload=JournalPostRequest(entry_date=entry_date, description="t", reference=key, lines=lines),
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_dashboard_computes_from_ledger(async_session: AsyncSession):
    tenant = "tenant-dash-1"
    recv = await _acct(async_session, tenant_id=tenant, code="12001", name="Sundry Debtors",
                       account_type="asset", classification="personal", is_receivable=True)
    cash = await _acct(async_session, tenant_id=tenant, code="11010", name="Bank",
                       account_type="asset", is_cash_bank=True)
    income = await _acct(async_session, tenant_id=tenant, code="41001", name="Sales",
                         account_type="income", classification="nominal")
    expense = await _acct(async_session, tenant_id=tenant, code="51001", name="Purchases",
                          account_type="expense", classification="nominal")
    payable = await _acct(async_session, tenant_id=tenant, code="22001", name="Sundry Creditors",
                          account_type="liability", classification="personal", is_payable=True)
    gst = await _acct(async_session, tenant_id=tenant, code="22004", name="GST Payable",
                      account_type="liability")
    await async_session.commit()

    # Sales invoice 1000, receipt 400, expense bill 600 (on credit), GST payable 50.
    await _post(async_session, tenant, key="inv", entry_date=date(2026, 6, 1), lines=[
        JournalLineIn(account_id=recv.id, debit=Decimal("1000"), credit=Decimal("0"), party_id="cust-A"),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("1000")),
    ])
    await _post(async_session, tenant, key="rcpt", entry_date=date(2026, 6, 5), lines=[
        JournalLineIn(account_id=cash.id, debit=Decimal("400"), credit=Decimal("0")),
        JournalLineIn(account_id=recv.id, debit=Decimal("0"), credit=Decimal("400"), party_id="cust-A"),
    ])
    await _post(async_session, tenant, key="bill", entry_date=date(2026, 6, 10), lines=[
        JournalLineIn(account_id=expense.id, debit=Decimal("600"), credit=Decimal("0")),
        JournalLineIn(account_id=payable.id, debit=Decimal("0"), credit=Decimal("600"), party_id="vend-B"),
    ])
    await _post(async_session, tenant, key="gst", entry_date=date(2026, 6, 12), lines=[
        JournalLineIn(account_id=expense.id, debit=Decimal("50"), credit=Decimal("0")),
        JournalLineIn(account_id=gst.id, debit=Decimal("0"), credit=Decimal("50")),
    ])

    dash = await get_business_dashboard(
        async_session, tenant_id=tenant, app_key=APP_KEY, accounting_entity_id=ENTITY_ID, as_of=AS_OF,
    )

    assert dash["income"]["fytd"] == "1000.00"
    assert dash["expenses"]["fytd"] == "650.00"          # 600 + 50
    assert dash["net_position"]["profit_loss"] == "350.00"
    assert dash["cash_and_bank"] == "400.00"
    assert dash["receivables"] == "600.00"               # 1000 - 400
    assert dash["payables"] == "600.00"                  # gst (code 22004) excluded from payable group
    assert dash["gst"]["payable"] == "50.00"
    assert dash["gst"]["status"] == "Due"

    assert len(dash["monthly_trend"]) == 6
    assert dash["monthly_trend"][-1][0] == "Jun"
    assert dash["monthly_trend"][-1][1] == round(1000 / 100000, 2)   # income in lakhs
    # Earlier months in the FY window have no postings.
    assert dash["monthly_trend"][0][1] == 0.0


@pytest.mark.asyncio
async def test_dashboard_empty_ledger_is_all_zeros(async_session: AsyncSession):
    dash = await get_business_dashboard(
        async_session, tenant_id="tenant-dash-empty", app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, as_of=AS_OF,
    )
    assert dash["income"]["fytd"] == "0.00"
    assert dash["net_position"]["profit_loss"] == "0.00"
    assert dash["cash_and_bank"] == "0.00"
    assert dash["gst"]["status"] == "Nil"
    assert dash["income"]["ytd_growth"] == 0.0
