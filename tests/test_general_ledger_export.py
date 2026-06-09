"""General Ledger export — the _build_business_report dispatch maps ledger lines
to (title, columns, rows, footer, meta) and produces real files."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import AccountingValidationError, post_journal_entry
from app.modules.business import report_export
from app.modules.business.router import _build_business_report

APP_KEY = "mitrabooks"
ENTITY_ID = "primary"
AS_OF = date(2026, 6, 30)


async def _acct(session, *, tenant_id, code, name, account_type, is_cash_bank=False):
    acc = Account(app_key=APP_KEY, tenant_id=tenant_id, accounting_entity_id=ENTITY_ID,
                  code=code, name=name, type=account_type, classification="real",
                  is_cash_bank=is_cash_bank)
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
async def test_general_ledger_export_spec_and_files(async_session: AsyncSession):
    tenant = "tenant-gl-1"
    cash = await _acct(async_session, tenant_id=tenant, code="11010", name="Bank Account",
                       account_type="asset", is_cash_bank=True)
    income = await _acct(async_session, tenant_id=tenant, code="41001", name="Sales",
                         account_type="income")
    await async_session.commit()

    await _post(async_session, tenant, key="s1", entry_date=date(2026, 6, 1), lines=[
        JournalLineIn(account_id=cash.id, debit=Decimal("1000"), credit=Decimal("0")),
        JournalLineIn(account_id=income.id, debit=Decimal("0"), credit=Decimal("1000")),
    ])
    await _post(async_session, tenant, key="s2", entry_date=date(2026, 6, 5), lines=[
        JournalLineIn(account_id=cash.id, debit=Decimal("0"), credit=Decimal("250")),
        JournalLineIn(account_id=income.id, debit=Decimal("250"), credit=Decimal("0")),
    ])

    spec = await _build_business_report(
        "general_ledger", session=async_session, tenant_id=tenant, app_key=APP_KEY,
        accounting_entity_id=ENTITY_ID, kind="receivable", as_of=AS_OF, account_id=cash.id,
    )

    assert spec["title"] == "General Ledger"
    assert [c["key"] for c in spec["columns"]] == ["entry_date", "description", "reference", "debit", "credit", "running_balance"]
    # Period + account in the header meta (company name handled separately via org_name).
    assert spec["meta"][0] == ("Account", "11010 - Bank Account")
    assert ("As of", "2026-06-30") in spec["meta"]
    # Two ledger lines; running balance after both = 1000 - 250 = 750.
    assert len(spec["rows"]) == 2
    assert spec["rows"][0]["debit"] == Decimal("1000")
    assert spec["rows"][1]["credit"] == Decimal("250")
    assert spec["footer"]["running_balance"] == Decimal("750.00")
    assert spec["footer"]["debit"] == Decimal("1000.00")
    assert spec["footer"]["credit"] == Decimal("250.00")

    # Real files build from the full spec via export_report (org_name resolves to
    # None without Mongo; filename_base drives the download name).
    csv_resp = report_export.export_report("csv", **spec)
    assert csv_resp.media_type == "text/csv"
    assert 'filename="general_ledger_11010_2026-06-30.csv"' in csv_resp.headers["content-disposition"]
    assert report_export.export_report("pdf", **spec).media_type == "application/pdf"


@pytest.mark.asyncio
async def test_general_ledger_requires_account_id(async_session: AsyncSession):
    with pytest.raises(AccountingValidationError, match="account_id is required"):
        await _build_business_report(
            "general_ledger", session=async_session, tenant_id="t", app_key=APP_KEY,
            accounting_entity_id=ENTITY_ID, kind="receivable", as_of=AS_OF, account_id=None,
        )
