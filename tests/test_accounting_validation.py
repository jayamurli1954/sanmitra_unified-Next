from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.accounting.service as accounting_service
from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest, SourceJournalLineIn
from app.accounting.service import (
    AccountingIdempotencyConflictError,
    AccountingValidationError,
    _net_profit_from_rows,
    post_journal_entry,
    suggest_canonical_account,
    validate_journal_lines,
    validate_source_journal_lines,
)


def test_validate_journal_lines_balanced() -> None:
    lines = [
        JournalLineIn(account_id=1, debit=Decimal("100.00"), credit=Decimal("0")),
        JournalLineIn(account_id=2, debit=Decimal("0"), credit=Decimal("100.00")),
    ]

    total_debit, total_credit, normalized = validate_journal_lines(lines)
    assert total_debit == Decimal("100.00")
    assert total_credit == Decimal("100.00")
    assert len(normalized) == 2


def test_validate_journal_lines_rejects_unbalanced() -> None:
    lines = [
        JournalLineIn(account_id=1, debit=Decimal("80.00"), credit=Decimal("0")),
        JournalLineIn(account_id=2, debit=Decimal("0"), credit=Decimal("100.00")),
    ]

    with pytest.raises(AccountingValidationError):
        validate_journal_lines(lines)


def test_validate_journal_requires_both_sides() -> None:
    lines = [
        JournalLineIn(account_id=1, debit=Decimal("50.00"), credit=Decimal("0")),
        JournalLineIn(account_id=2, debit=Decimal("50.00"), credit=Decimal("0")),
    ]

    with pytest.raises(AccountingValidationError, match="at least one debit line and one credit line"):
        validate_journal_lines(lines)


def test_validate_journal_requires_two_distinct_accounts() -> None:
    lines = [
        JournalLineIn(account_id=1, debit=Decimal("50.00"), credit=Decimal("0")),
        JournalLineIn(account_id=1, debit=Decimal("0"), credit=Decimal("50.00")),
    ]

    with pytest.raises(AccountingValidationError, match="at least two distinct accounts"):
        validate_journal_lines(lines)


def test_validate_journal_rejects_dual_side_single_line() -> None:
    lines = [
        JournalLineIn(account_id=1, debit=Decimal("10.00"), credit=Decimal("10.00")),
        JournalLineIn(account_id=2, debit=Decimal("0"), credit=Decimal("0")),
    ]

    with pytest.raises(AccountingValidationError):
        validate_journal_lines(lines)


def test_validate_source_journal_lines_balanced() -> None:
    lines = [
        SourceJournalLineIn(source_account_code="SR-101", debit=Decimal("250.00"), credit=Decimal("0")),
        SourceJournalLineIn(source_account_code="SR-201", debit=Decimal("0"), credit=Decimal("250.00")),
    ]

    total_debit, total_credit, normalized = validate_source_journal_lines(lines)
    assert total_debit == Decimal("250.00")
    assert total_credit == Decimal("250.00")
    assert len(normalized) == 2


def test_validate_source_journal_lines_rejects_same_source_account() -> None:
    lines = [
        SourceJournalLineIn(source_account_code="SR-101", debit=Decimal("100.00"), credit=Decimal("0")),
        SourceJournalLineIn(source_account_code="SR-101", debit=Decimal("0"), credit=Decimal("100.00")),
    ]

    with pytest.raises(AccountingValidationError, match="two distinct source accounts"):
        validate_source_journal_lines(lines)


def test_suggest_canonical_account_prefers_exact_code_match() -> None:
    candidates = [
        Account(
            id=1,
            tenant_id="t1",
            code="CASH-001",
            name="Cash in Hand",
            type="asset",
            classification="real",
            is_cash_bank=True,
            is_receivable=False,
            is_payable=False,
        ),
        Account(
            id=2,
            tenant_id="t1",
            code="REV-100",
            name="Donation Income",
            type="income",
            classification="nominal",
            is_cash_bank=False,
            is_receivable=False,
            is_payable=False,
        ),
    ]

    suggestion = suggest_canonical_account("CASH-001", "Cash Box", candidates)
    assert suggestion is not None
    assert suggestion["canonical_account_id"] == 1
    assert suggestion["reason"] == "exact_code_match"


async def _create_idempotency_accounts(async_session, tenant_id: str) -> tuple[Account, Account]:
    cash = Account(
        app_key="mitrabooks",
        tenant_id=tenant_id,
        accounting_entity_id="primary",
        code="1000",
        name="Cash",
        type="asset",
        classification="real",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    income = Account(
        app_key="mitrabooks",
        tenant_id=tenant_id,
        accounting_entity_id="primary",
        code="4000",
        name="Service Income",
        type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    async_session.add_all([cash, income])
    await async_session.commit()
    return cash, income


def _journal_payload(
    cash_id: int,
    income_id: int,
    amount: str = "100.00",
    *,
    source_document_id: str | None = None,
) -> JournalPostRequest:
    return JournalPostRequest(
        entry_date=date(2026, 5, 27),
        description="Idempotency receipt",
        reference="IDEMP-001",
        source_module="mitrabooks",
        source_document_type="receipt",
        source_document_id=source_document_id,
        lines=[
            JournalLineIn(account_id=cash_id, debit=Decimal(amount), credit=Decimal("0.00")),
            JournalLineIn(account_id=income_id, debit=Decimal("0.00"), credit=Decimal(amount)),
        ],
    )


@pytest.mark.asyncio
async def test_post_journal_entry_reuses_idempotency_key_for_same_payload(async_session) -> None:
    tenant_id = "tenant-idempotency-same"
    cash, income = await _create_idempotency_accounts(async_session, tenant_id)

    first, first_created = await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-duplicate-key",
        payload=_journal_payload(cash.id, income.id),
    )
    second, second_created = await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-duplicate-key",
        payload=_journal_payload(cash.id, income.id),
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id


@pytest.mark.asyncio
async def test_post_journal_entry_persists_source_metadata(async_session) -> None:
    tenant_id = "tenant-source-metadata"
    cash, income = await _create_idempotency_accounts(async_session, tenant_id)

    entry, created = await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-source-key",
        payload=_journal_payload(cash.id, income.id, source_document_id="receipt-101"),
    )

    assert created is True
    assert entry.source_module == "mitrabooks"
    assert entry.source_document_type == "receipt"
    assert entry.source_document_id == "receipt-101"


@pytest.mark.asyncio
async def test_post_journal_entry_rejects_idempotency_key_for_different_payload(async_session) -> None:
    tenant_id = "tenant-idempotency-conflict"
    cash, income = await _create_idempotency_accounts(async_session, tenant_id)

    await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-conflict-key",
        payload=_journal_payload(cash.id, income.id, "100.00"),
    )

    with pytest.raises(AccountingIdempotencyConflictError, match="different journal payload"):
        await post_journal_entry(
            async_session,
            tenant_id=tenant_id,
            app_key="mitrabooks",
            accounting_entity_id="primary",
            created_by="test-user",
            idempotency_key="receipt-conflict-key",
            payload=_journal_payload(cash.id, income.id, "125.00"),
        )


@pytest.mark.asyncio
async def test_post_journal_entry_rejects_idempotency_key_for_different_source_metadata(async_session) -> None:
    tenant_id = "tenant-idempotency-source-conflict"
    cash, income = await _create_idempotency_accounts(async_session, tenant_id)

    await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-source-conflict-key",
        payload=_journal_payload(cash.id, income.id, source_document_id="receipt-101"),
    )

    with pytest.raises(AccountingIdempotencyConflictError, match="different journal payload"):
        await post_journal_entry(
            async_session,
            tenant_id=tenant_id,
            app_key="mitrabooks",
            accounting_entity_id="primary",
            created_by="test-user",
            idempotency_key="receipt-source-conflict-key",
            payload=_journal_payload(cash.id, income.id, source_document_id="receipt-102"),
        )


@pytest.mark.asyncio
async def test_post_journal_entry_rejects_idempotency_key_for_different_reversal_link(async_session) -> None:
    tenant_id = "tenant-idempotency-reversal-conflict"
    cash, income = await _create_idempotency_accounts(async_session, tenant_id)

    await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mitrabooks",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="receipt-reversal-conflict-key",
        payload=_journal_payload(cash.id, income.id),
    )

    with pytest.raises(AccountingIdempotencyConflictError, match="different journal payload"):
        await post_journal_entry(
            async_session,
            tenant_id=tenant_id,
            app_key="mitrabooks",
            accounting_entity_id="primary",
            created_by="test-user",
            idempotency_key="receipt-reversal-conflict-key",
            payload=_journal_payload(cash.id, income.id),
            reversal_of_journal_id=999,
        )



def test_net_profit_from_rows_handles_income_and_expense() -> None:
    rows = [
        SimpleNamespace(account_type="income", debit_total=Decimal("0"), credit_total=Decimal("15500")),
        SimpleNamespace(account_type="expense", debit_total=Decimal("2300"), credit_total=Decimal("0")),
    ]

    assert _net_profit_from_rows(rows) == Decimal("13200.00")


def test_net_profit_from_rows_handles_net_loss() -> None:
    rows = [
        SimpleNamespace(account_type="income", debit_total=Decimal("0"), credit_total=Decimal("1200")),
        SimpleNamespace(account_type="expense", debit_total=Decimal("2500"), credit_total=Decimal("0")),
    ]

    assert _net_profit_from_rows(rows) == Decimal("-1300.00")


@pytest.mark.asyncio
async def test_get_balance_sheet_includes_unclosed_earnings(monkeypatch) -> None:
    async def fake_gl_sums_by_account(_session, **kwargs):
        account_types = kwargs.get("account_types")
        if account_types == ("asset", "liability", "equity"):
            return [
                SimpleNamespace(
                    account_id=1,
                    account_code="1001",
                    account_name="Cash",
                    account_type="asset",
                    debit_total=Decimal("15500"),
                    credit_total=Decimal("0"),
                )
            ]
        if account_types == ("income", "expense"):
            return [
                SimpleNamespace(
                    account_id=2,
                    account_code="4100",
                    account_name="Service Income",
                    account_type="income",
                    debit_total=Decimal("0"),
                    credit_total=Decimal("15500"),
                )
            ]
        return []

    monkeypatch.setattr(accounting_service, "_gl_sums_by_account", fake_gl_sums_by_account)

    assets, liabilities, equity, total_assets, total_liabilities, total_equity = await accounting_service.get_balance_sheet(
        None,
        tenant_id="t1",
        as_of=date(2026, 3, 23),
    )

    assert liabilities == []
    assert total_assets == Decimal("15500.00")
    assert total_liabilities == Decimal("0.00")
    assert total_equity == Decimal("15500.00")
    assert any(line["account_id"] == 0 and line["balance"] == Decimal("15500.00") for line in equity)


@pytest.mark.asyncio
async def test_post_journal_entry_blocks_negative_cash_balance(async_session) -> None:
    tenant_id = "tenant-cash-negative-guard"
    cash = Account(
        app_key="mandirmitra",
        tenant_id=tenant_id,
        accounting_entity_id="primary",
        code="11001",
        name="Cash in Hand - Counter",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    bank = Account(
        app_key="mandirmitra",
        tenant_id=tenant_id,
        accounting_entity_id="primary",
        code="12001",
        name="Bank - Current Account",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    income = Account(
        app_key="mandirmitra",
        tenant_id=tenant_id,
        accounting_entity_id="primary",
        code="44001",
        name="General Donations",
        type="income",
        classification="nominal",
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    async_session.add_all([cash, bank, income])
    await async_session.commit()

    await post_journal_entry(
        async_session,
        tenant_id=tenant_id,
        app_key="mandirmitra",
        accounting_entity_id="primary",
        created_by="test-user",
        idempotency_key="cash-negative-opening",
        payload=JournalPostRequest(
            entry_date=date(2026, 5, 24),
            description="Cash donation",
            reference="DON-001",
            lines=[
                JournalLineIn(account_id=cash.id, debit=Decimal("7839.00"), credit=Decimal("0.00")),
                JournalLineIn(account_id=income.id, debit=Decimal("0.00"), credit=Decimal("7839.00")),
            ],
        ),
    )

    with pytest.raises(AccountingValidationError, match="Insufficient cash balance"):
        await post_journal_entry(
            async_session,
            tenant_id=tenant_id,
            app_key="mandirmitra",
            accounting_entity_id="primary",
            created_by="test-user",
            idempotency_key="cash-negative-transfer",
            payload=JournalPostRequest(
                entry_date=date(2026, 5, 24),
                description="Cash transferred to bank",
                reference="TRF-001",
                lines=[
                    JournalLineIn(account_id=bank.id, debit=Decimal("8000.00"), credit=Decimal("0.00")),
                    JournalLineIn(account_id=cash.id, debit=Decimal("0.00"), credit=Decimal("8000.00")),
                ],
            ),
        )
