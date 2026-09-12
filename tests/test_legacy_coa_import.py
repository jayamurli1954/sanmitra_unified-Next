from __future__ import annotations

from decimal import Decimal

import pytest

from app.accounting.legacy_coa_import import (
    confirm_legacy_coa_decisions,
    legacy_account_lookups,
    parse_legacy_coa_csv,
    preview_legacy_coa_csv,
)
from app.accounting.models import Account
from app.accounting.schemas import LegacyCoaCreateAccountIn, LegacyCoaDecisionIn
from app.accounting.service import AccountingValidationError
from app.modules.business.opening_close import _account_lookups


def test_parse_legacy_coa_csv_unique_code_and_name():
    rows = parse_legacy_coa_csv(
        "code,ledger name,type\n"
        "1001,Cash in Hand,asset\n"
        "2001,Sundry Creditors,liability\n"
    )
    assert len(rows) == 2
    assert rows[0]["source_account_code"] == "1001"
    assert rows[0]["source_account_name"] == "Cash in Hand"
    assert rows[0]["source_account_type"] == "asset"


def test_parse_legacy_coa_csv_rejects_duplicate_codes():
    with pytest.raises(ValueError, match="Duplicate legacy account code"):
        parse_legacy_coa_csv(
            "source_account_code,source_account_name\n"
            "1001,Cash\n"
            "1001,Cash at Bank\n"
        )


def test_parse_legacy_coa_csv_ignores_unknown_tally_groups():
    rows = parse_legacy_coa_csv(
        "source_account_code,source_account_name,source_account_type\n"
        "1001,Cash in Hand,Current Assets\n"
    )
    assert rows[0]["source_account_type"] is None


@pytest.mark.asyncio
async def test_preview_suggests_exact_name_and_leaves_unmatched(async_session, monkeypatch):
    cash = Account(
        app_key="mitrabooks",
        tenant_id="t-legacy",
        accounting_entity_id="primary",
        code="11001",
        name="Cash in Hand",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    async_session.add(cash)
    await async_session.commit()

    async def _noop_init(*_args, **_kwargs):
        return {"accounts_created": 0, "accounts_existing": 1, "total_accounts": 1}

    monkeypatch.setattr(
        "app.accounting.chart.initialize_default_chart_of_accounts",
        _noop_init,
    )

    preview = await preview_legacy_coa_csv(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        source_system="tally",
        csv_text=(
            "source_account_code,source_account_name\n"
            "CASH-01,Cash in Hand\n"
            "EXP-99,Festival Pandhal\n"
        ),
    )
    by_code = {row["source_account_code"]: row for row in preview["rows"]}
    assert by_code["CASH-01"]["match_status"] == "suggested"
    assert by_code["CASH-01"]["suggestion"]["reason"] == "exact_name_match"
    assert by_code["EXP-99"]["match_status"] == "unmatched"
    assert preview["unmatched_count"] == 1
    assert preview["suggested_count"] == 1


@pytest.mark.asyncio
async def test_confirm_map_existing_writes_decision_and_legacy_lookup(async_session, monkeypatch):
    cash = Account(
        app_key="mitrabooks",
        tenant_id="t-legacy",
        accounting_entity_id="primary",
        code="11001",
        name="Cash in Hand",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    async_session.add(cash)
    await async_session.commit()
    await async_session.refresh(cash)

    audit_box = {}

    async def fake_audit(**kwargs):
        audit_box.update(kwargs)
        return "evt-1"

    monkeypatch.setattr("app.accounting.legacy_coa_import.log_audit_event", fake_audit)

    result = await confirm_legacy_coa_decisions(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        source_system="tally",
        decided_by="ca-user",
        decisions=[
            LegacyCoaDecisionIn(
                source_account_code="CASH-01",
                source_account_name="Cash in Hand",
                action="map_existing",
                canonical_account_id=cash.id,
                notes="Matched Tally cash to MitraBooks cash",
                suggestion={
                    "canonical_account_id": cash.id,
                    "canonical_account_name": "Cash in Hand",
                    "confidence": Decimal("0.90"),
                    "reason": "exact_name_match",
                },
            )
        ],
    )
    assert result["confirmed_count"] == 1
    assert result["mapped_existing_count"] == 1
    assert result["created_account_count"] == 0
    decision = result["decisions"][0]
    assert decision["action"] == "mapped_to_existing"
    assert decision["decided_by"] == "ca-user"
    assert decision["source_account_code"] == "CASH-01"
    assert audit_box["action"] == "coa_legacy_mapping_confirmed"
    assert audit_box["tenant_id"] == "t-legacy"
    assert audit_box["new_value"]["action"] == "mapped_to_existing"

    lookups = await legacy_account_lookups(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert lookups["CASH-01"]["account_id"] == cash.id

    by_code, _by_name = await _account_lookups(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert by_code["CASH-01"]["account_id"] == cash.id
    assert by_code["11001"]["account_id"] == cash.id


@pytest.mark.asyncio
async def test_confirm_create_new_uses_mitrabooks_account_create(async_session, monkeypatch):
    async def fake_audit(**_kwargs):
        return "evt-2"

    monkeypatch.setattr("app.accounting.legacy_coa_import.log_audit_event", fake_audit)

    result = await confirm_legacy_coa_decisions(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        source_system="zoho",
        decided_by="admin",
        decisions=[
            LegacyCoaDecisionIn(
                source_account_code="PANDAL",
                source_account_name="Festival Pandhal",
                action="create_new",
                create=LegacyCoaCreateAccountIn(
                    code="53099",
                    name="Festival Pandal",
                    type="expense",
                    classification="nominal",
                ),
            )
        ],
    )
    assert result["created_account_count"] == 1
    decision = result["decisions"][0]
    assert decision["action"] == "created_then_mapped"
    assert decision["canonical_account_code"] == "53099"
    assert decision["created_account"] is True

    lookups = await legacy_account_lookups(
        async_session,
        tenant_id="t-legacy",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert lookups["PANDAL"]["code"] == "53099"


@pytest.mark.asyncio
async def test_confirm_map_without_account_is_rejected(async_session):
    with pytest.raises(AccountingValidationError, match="canonical_account_id is required"):
        await confirm_legacy_coa_decisions(
            async_session,
            tenant_id="t-legacy",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            source_system="tally",
            decided_by="ca-user",
            decisions=[
                LegacyCoaDecisionIn(
                    source_account_code="CASH-01",
                    source_account_name="Cash",
                    action="map_existing",
                )
            ],
        )


@pytest.mark.asyncio
async def test_legacy_lookup_is_tenant_scoped(async_session, monkeypatch):
    cash = Account(
        app_key="mitrabooks",
        tenant_id="t-a",
        accounting_entity_id="primary",
        code="11001",
        name="Cash in Hand",
        type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    async_session.add(cash)
    await async_session.commit()
    await async_session.refresh(cash)

    async def fake_audit(**_kwargs):
        return "evt-3"

    monkeypatch.setattr("app.accounting.legacy_coa_import.log_audit_event", fake_audit)

    await confirm_legacy_coa_decisions(
        async_session,
        tenant_id="t-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        source_system="tally",
        decided_by="ca-user",
        decisions=[
            LegacyCoaDecisionIn(
                source_account_code="CASH-01",
                source_account_name="Cash in Hand",
                action="map_existing",
                canonical_account_id=cash.id,
            )
        ],
    )
    other = await legacy_account_lookups(
        async_session,
        tenant_id="t-b",
        app_key="mitrabooks",
        accounting_entity_id="primary",
    )
    assert other == {}
