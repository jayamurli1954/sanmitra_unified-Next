"""Balance Sheet & Profit-and-Loss export — _build_business_report maps the
ledger into (title, columns, rows, footer, meta) and produces real files,
matching the CSV/XLSX/PDF treatment the other business reports already get."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry
from app.modules.business import report_export
from app.modules.business.router import _build_business_report

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"
AS_OF = date(2026, 6, 30)


async def _acct(session, *, tenant_id, code, name, account_type, classification="real"):
    acc = Account(app_key=APP_KEY, tenant_id=tenant_id, accounting_entity_id=ENTITY_ID,
                  code=code, name=name, type=account_type, classification=classification)
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
async def test_balance_sheet_export_spec_and_files(async_session: AsyncSession):
    tenant = "tenant-bs-1"
    bank = await _acct(async_session, tenant_id=tenant, code="11010", name="Bank", account_type="asset")
    inventory = await _acct(async_session, tenant_id=tenant, code="13001", name="Inventory", account_type="asset")
    creditors = await _acct(async_session, tenant_id=tenant, code="21001", name="Sundry Creditors",
                            account_type="liability", classification="personal")
    capital = await _acct(async_session, tenant_id=tenant, code="31001", name="Owner Capital",
                          account_type="equity", classification="personal")
    await async_session.commit()

    # Capital introduced 5000; goods bought on credit 2000.
    await _post(async_session, tenant, key="cap", entry_date=date(2026, 6, 1), lines=[
        JournalLineIn(account_id=bank.id, debit=Decimal("5000"), credit=Decimal("0")),
        JournalLineIn(account_id=capital.id, debit=Decimal("0"), credit=Decimal("5000")),
    ])
    await _post(async_session, tenant, key="buy", entry_date=date(2026, 6, 5), lines=[
        JournalLineIn(account_id=inventory.id, debit=Decimal("2000"), credit=Decimal("0")),
        JournalLineIn(account_id=creditors.id, debit=Decimal("0"), credit=Decimal("2000")),
    ])

    spec = await _build_business_report(
        "balance_sheet", session=async_session, tenant_id=tenant, app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, kind="receivable", as_of=AS_OF,
    )

    assert spec["title"] == "Balance Sheet"
    assert [c["key"] for c in spec["columns"]] == ["section", "account_code", "account_name", "amount"]
    assert ("As of", "2026-06-30") in spec["meta"]

    rows = spec["rows"]
    # Section subtotals are present and correct.
    subtotals = {r["account_name"]: r["amount"] for r in rows if r["section"] == ""}
    assert subtotals["Total Assets"] == Decimal("7000.00")          # 5000 bank + 2000 inventory
    assert subtotals["Total Liabilities"] == Decimal("2000.00")
    assert subtotals["Total Equity"] == Decimal("5000.00")
    # The balance check ties: L + E == A.
    assert spec["footer"]["amount"] == Decimal("7000.00")
    assert spec["filename_base"] == "balance_sheet_2026-06-30"

    csv_resp = report_export.export_report("csv", **spec)
    assert 'filename="balance_sheet_2026-06-30.csv"' in csv_resp.headers["content-disposition"]
    assert "spreadsheetml" in report_export.export_report("xlsx", **spec).media_type
    assert report_export.export_report("pdf", **spec).media_type == "application/pdf"


@pytest.mark.asyncio
async def test_profit_loss_export_spec_and_files(async_session: AsyncSession):
    tenant = "tenant-pnl-1"
    bank = await _acct(async_session, tenant_id=tenant, code="11010", name="Bank", account_type="asset")
    sales = await _acct(async_session, tenant_id=tenant, code="41001", name="Sales",
                        account_type="income", classification="nominal")
    purchases = await _acct(async_session, tenant_id=tenant, code="51001", name="Purchases",
                            account_type="expense", classification="nominal")
    await async_session.commit()

    await _post(async_session, tenant, key="sale", entry_date=date(2026, 6, 3), lines=[
        JournalLineIn(account_id=bank.id, debit=Decimal("1000"), credit=Decimal("0")),
        JournalLineIn(account_id=sales.id, debit=Decimal("0"), credit=Decimal("1000")),
    ])
    await _post(async_session, tenant, key="buy", entry_date=date(2026, 6, 4), lines=[
        JournalLineIn(account_id=purchases.id, debit=Decimal("600"), credit=Decimal("0")),
        JournalLineIn(account_id=bank.id, debit=Decimal("0"), credit=Decimal("600")),
    ])

    spec = await _build_business_report(
        "profit_loss", session=async_session, tenant_id=tenant, app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, kind="receivable", as_of=AS_OF,
        from_date=date(2026, 6, 1), to_date=date(2026, 6, 30),
    )

    assert spec["title"] == "Profit and Loss"
    assert ("From", "2026-06-01") in spec["meta"]
    assert ("To", "2026-06-30") in spec["meta"]

    subtotals = {r["account_name"]: r["amount"] for r in spec["rows"] if r["section"] == ""}
    assert subtotals["Total Income"] == Decimal("1000.00")
    assert subtotals["Total Expenses"] == Decimal("600.00")
    assert spec["footer"]["account_name"] == "Net Profit"
    assert spec["footer"]["amount"] == Decimal("400.00")
    assert spec["filename_base"] == "profit_loss_2026-06-01_2026-06-30"

    csv_resp = report_export.export_report("csv", **spec)
    assert 'filename="profit_loss_2026-06-01_2026-06-30.csv"' in csv_resp.headers["content-disposition"]
    assert report_export.export_report("pdf", **spec).media_type == "application/pdf"
