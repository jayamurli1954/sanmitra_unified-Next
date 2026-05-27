from datetime import date
from decimal import Decimal

import pytest

from app.accounting.models import JournalEntry
from app.accounting.models.entities import Account, JournalLine
from app.accounting.service import AccountingNotFoundError, get_journal_drilldown, get_journal_voucher_detail


@pytest.mark.asyncio
async def test_journal_drilldown_groups_month_week_day_and_vouchers(async_session):
    async_session.add_all(
        [
            JournalEntry(
                app_key="mandirmitra",
                tenant_id="tenant-1",
                accounting_entity_id="primary",
                entry_date=date(2026, 5, 1),
                description="May donation",
                reference="DON-1",
                total_debit=Decimal("501.00"),
                total_credit=Decimal("501.00"),
            ),
            JournalEntry(
                app_key="mandirmitra",
                tenant_id="tenant-1",
                accounting_entity_id="primary",
                entry_date=date(2026, 5, 8),
                description="May seva",
                reference="SEV-1",
                total_debit=Decimal("301.00"),
                total_credit=Decimal("301.00"),
            ),
            JournalEntry(
                app_key="gruhamitra",
                tenant_id="tenant-1",
                accounting_entity_id="primary",
                entry_date=date(2026, 5, 9),
                description="Other app collection",
                reference="GRU-1",
                total_debit=Decimal("999.00"),
                total_credit=Decimal("999.00"),
            ),
            JournalEntry(
                app_key="mandirmitra",
                tenant_id="tenant-2",
                accounting_entity_id="primary",
                entry_date=date(2026, 5, 10),
                description="Other tenant donation",
                reference="TENANT-2-DON",
                total_debit=Decimal("777.00"),
                total_credit=Decimal("777.00"),
            ),
            JournalEntry(
                app_key="mandirmitra",
                tenant_id="tenant-1",
                accounting_entity_id="secondary",
                entry_date=date(2026, 5, 11),
                description="Other accounting entity donation",
                reference="ENTITY-2-DON",
                total_debit=Decimal("888.00"),
                total_credit=Decimal("888.00"),
            ),
        ]
    )
    await async_session.commit()

    month = await get_journal_drilldown(
        async_session,
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
        level="month",
    )
    assert month["items"][0]["month"] == "2026-05"
    assert month["items"][0]["voucher_count"] == 2
    assert month["items"][0]["last_voucher"]["reference"] == "SEV-1"
    assert month["summary"]["total_debit"] == 802.0

    week = await get_journal_drilldown(
        async_session,
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
        level="week",
        month="2026-05",
    )
    assert [row["week_start"] for row in week["items"]] == ["2026-05-04", "2026-04-27"]

    day = await get_journal_drilldown(
        async_session,
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
        level="day",
        week_start=date(2026, 5, 4),
    )
    assert day["items"] == [
        {
            "day": "2026-05-08",
            "voucher_count": 1,
            "total_debit": 301.0,
            "total_credit": 301.0,
            "last_voucher": day["items"][0]["last_voucher"],
        }
    ]

    vouchers = await get_journal_drilldown(
        async_session,
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 31),
        level="voucher",
        day=date(2026, 5, 8),
    )
    assert [row["reference"] for row in vouchers["items"]] == ["SEV-1"]
    all_payloads = str(month) + str(vouchers)
    assert "TENANT-2-DON" not in all_payloads
    assert "ENTITY-2-DON" not in all_payloads


@pytest.mark.asyncio
async def test_journal_voucher_detail_returns_lines_and_enforces_app_scope(async_session):
    cash = Account(
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        code="11001",
        name="Cash in Hand",
        type="asset",
        classification="real",
        is_cash_bank=True,
    )
    income = Account(
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        code="44001",
        name="General Donations",
        type="income",
        classification="nominal",
    )
    async_session.add_all([cash, income])
    await async_session.flush()

    entry = JournalEntry(
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        entry_date=date(2026, 5, 10),
        description="Donation posted",
        reference="DON-99",
        total_debit=Decimal("501.00"),
        total_credit=Decimal("501.00"),
        lines=[
            JournalLine(
                app_key="mandirmitra",
                tenant_id="tenant-1",
                accounting_entity_id="primary",
                account_id=cash.id,
                debit=Decimal("501.00"),
                credit=Decimal("0.00"),
            ),
            JournalLine(
                app_key="mandirmitra",
                tenant_id="tenant-1",
                accounting_entity_id="primary",
                account_id=income.id,
                debit=Decimal("0.00"),
                credit=Decimal("501.00"),
            ),
        ],
    )
    async_session.add(entry)
    await async_session.commit()

    detail = await get_journal_voucher_detail(
        async_session,
        app_key="mandirmitra",
        tenant_id="tenant-1",
        accounting_entity_id="primary",
        journal_id=entry.id,
    )

    assert detail["reference"] == "DON-99"
    assert detail["total_debit"] == 501.0
    assert [line["account_code"] for line in detail["lines"]] == ["11001", "44001"]
    assert detail["lines"][0]["debit"] == 501.0
    assert detail["lines"][1]["credit"] == 501.0

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="gruhamitra",
            tenant_id="tenant-1",
            accounting_entity_id="primary",
            journal_id=entry.id,
        )

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mandirmitra",
            tenant_id="tenant-2",
            accounting_entity_id="primary",
            journal_id=entry.id,
        )

    with pytest.raises(AccountingNotFoundError):
        await get_journal_voucher_detail(
            async_session,
            app_key="mandirmitra",
            tenant_id="tenant-1",
            accounting_entity_id="secondary",
            journal_id=entry.id,
        )
