"""Cost-centre accounting (enterprise add-on) — hierarchy, ledger P&L, and the
tenant-isolation guard. Isolation is the paramount invariant here: a cost centre
must never aggregate or attach across tenants/entities, or every departmental
P&L is corrupted. These tests pin that down."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import JournalEntry, JournalLine
from app.accounting.service import create_account, get_cost_centre_ledger_pl
from app.modules.business.dimensions import (
    build_cost_centre_tree,
    validate_ledger_cost_centre_ids,
)

FROM, TO = date(2026, 4, 1), date(2026, 6, 30)


# --------------------------------------------------------------------------- #
# 1c — hierarchy roll-up (pure assembly).
# --------------------------------------------------------------------------- #

def test_build_cost_centre_tree_nests_by_parent_code():
    dims = [
        {"dimension_type": "cost_centre", "code": "OPS", "name": "Operations", "parent_code": None},
        {"dimension_type": "cost_centre", "code": "FACT-A", "name": "Factory A", "parent_code": "OPS"},
        {"dimension_type": "cost_centre", "code": "ASSY-1", "name": "Assembly 1", "parent_code": "FACT-A"},
        {"dimension_type": "project", "code": "ALPHA", "name": "Alpha", "parent_code": None},  # ignored
    ]
    roots = build_cost_centre_tree(dims)
    assert [r["code"] for r in roots] == ["OPS"]
    fact = roots[0]["children"]
    assert [c["code"] for c in fact] == ["FACT-A"]
    assert [c["code"] for c in fact[0]["children"]] == ["ASSY-1"]


def test_build_cost_centre_tree_surfaces_orphans_at_top():
    dims = [
        {"dimension_type": "cost_centre", "code": "ASSY-1", "name": "Assembly 1", "parent_code": "GONE"},
        {"dimension_type": "cost_centre", "code": "OPS", "name": "Operations", "parent_code": None},
    ]
    roots = build_cost_centre_tree(dims)
    # Orphan (parent missing in this scope) does not silently vanish.
    assert {r["code"] for r in roots} == {"ASSY-1", "OPS"}


# --------------------------------------------------------------------------- #
# Helper: post a balanced P&L entry directly (bypasses the Mongo guard so the
# ledger-aggregation test stays pure-SQL).
# --------------------------------------------------------------------------- #

async def _seed_pl(session, *, app_key, tenant, entity, cc, income, expense):
    cash = await create_account(
        session, app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
        code="1001", name="Cash", account_type="asset", classification="real",
        is_cash_bank=True, is_receivable=False, is_payable=False,
    )
    inc = await create_account(
        session, app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
        code="4001", name="Sales", account_type="income", classification="nominal",
        is_cash_bank=False, is_receivable=False, is_payable=False,
    )
    exp = await create_account(
        session, app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
        code="5001", name="Materials", account_type="expense", classification="nominal",
        is_cash_bank=False, is_receivable=False, is_payable=False,
    )
    entry = JournalEntry(
        app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
        entry_date=date(2026, 5, 1), description="cc seed",
        total_debit=Decimal(income) + Decimal(expense),
        total_credit=Decimal(income) + Decimal(expense), created_by="t",
    )
    entry.lines = [
        JournalLine(app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
                    account_id=cash.id, debit=Decimal(income), credit=Decimal("0.00")),
        JournalLine(app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
                    account_id=inc.id, debit=Decimal("0.00"), credit=Decimal(income), cost_center_id=cc),
        JournalLine(app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
                    account_id=exp.id, debit=Decimal(expense), credit=Decimal("0.00"), cost_center_id=cc),
        JournalLine(app_key=app_key, tenant_id=tenant, accounting_entity_id=entity,
                    account_id=cash.id, debit=Decimal("0.00"), credit=Decimal(expense)),
    ]
    session.add(entry)
    await session.commit()


@pytest.mark.asyncio
async def test_cost_centre_pl_does_not_aggregate_across_tenants(async_session: AsyncSession):
    """Two tenants use the SAME cost-centre code 'CC-A'. Each tenant's P&L must
    reflect only its own postings — the headline isolation guarantee."""
    await _seed_pl(async_session, app_key="mitrabooks", tenant="firm-A", entity="primary",
                   cc="CC-A", income="10000.00", expense="4000.00")
    await _seed_pl(async_session, app_key="mitrabooks", tenant="firm-B", entity="primary",
                   cc="CC-A", income="99999.00", expense="1.00")

    a = await get_cost_centre_ledger_pl(
        async_session, app_key="mitrabooks", tenant_id="firm-A",
        accounting_entity_id="primary", from_date=FROM, to_date=TO,
    )
    assert a["buckets"]["CC-A"]["income"] == Decimal("10000.00")
    assert a["buckets"]["CC-A"]["expense"] == Decimal("4000.00")
    # firm-B's 99999 must NOT have leaked in.
    assert Decimal("99999.00") not in {v["income"] for v in a["buckets"].values()}


@pytest.mark.asyncio
async def test_cost_centre_pl_isolates_entities_within_a_tenant(async_session: AsyncSession):
    """Same tenant, two accounting entities sharing code 'CC-X' (CA-firm case)."""
    await _seed_pl(async_session, app_key="mitrabooks", tenant="firm-1", entity="client-a",
                   cc="CC-X", income="5000.00", expense="2000.00")
    await _seed_pl(async_session, app_key="mitrabooks", tenant="firm-1", entity="client-b",
                   cc="CC-X", income="7000.00", expense="500.00")

    b = await get_cost_centre_ledger_pl(
        async_session, app_key="mitrabooks", tenant_id="firm-1",
        accounting_entity_id="client-b", from_date=FROM, to_date=TO,
    )
    assert b["buckets"]["CC-X"]["income"] == Decimal("7000.00")
    assert b["buckets"]["CC-X"]["expense"] == Decimal("500.00")


# --------------------------------------------------------------------------- #
# 1f — posting isolation guard (Mongo-independent via a fake collection).
# --------------------------------------------------------------------------- #

class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query, projection=None):
        ids = set(query.get("dimension_id", {}).get("$in", []))
        scope_keys = ("tenant_id", "app_key", "accounting_entity_id")
        out = [
            {"dimension_id": d["dimension_id"]}
            for d in self._docs
            if d["dimension_id"] in ids
            and d.get("is_active")
            and d.get("dimension_type") == "cost_centre"
            and all(d.get(k) == query.get(k) for k in scope_keys)
        ]
        return _FakeCursor(out)


@pytest.fixture
def fake_dimensions(monkeypatch):
    docs = [
        {"dimension_id": "cc-own", "dimension_type": "cost_centre", "is_active": True,
         "tenant_id": "firm-A", "app_key": "mitrabooks", "accounting_entity_id": "primary"},
        {"dimension_id": "cc-inactive", "dimension_type": "cost_centre", "is_active": False,
         "tenant_id": "firm-A", "app_key": "mitrabooks", "accounting_entity_id": "primary"},
        # Belongs to ANOTHER tenant — must be invisible to firm-A.
        {"dimension_id": "cc-other-tenant", "dimension_type": "cost_centre", "is_active": True,
         "tenant_id": "firm-B", "app_key": "mitrabooks", "accounting_entity_id": "primary"},
    ]
    import app.db.mongo as mongo_mod
    monkeypatch.setattr(mongo_mod, "get_collection", lambda name: _FakeCollection(docs))


@pytest.mark.asyncio
async def test_guard_accepts_own_active_cost_centre(fake_dimensions):
    await validate_ledger_cost_centre_ids(
        tenant_id="firm-A", app_key="mitrabooks", accounting_entity_id="primary",
        cost_centre_ids={"cc-own"},
    )  # no raise


@pytest.mark.asyncio
async def test_guard_rejects_other_tenants_cost_centre(fake_dimensions):
    from app.accounting.service import AccountingValidationError
    with pytest.raises(AccountingValidationError):
        await validate_ledger_cost_centre_ids(
            tenant_id="firm-A", app_key="mitrabooks", accounting_entity_id="primary",
            cost_centre_ids={"cc-other-tenant"},
        )


@pytest.mark.asyncio
async def test_guard_rejects_inactive_cost_centre(fake_dimensions):
    from app.accounting.service import AccountingValidationError
    with pytest.raises(AccountingValidationError):
        await validate_ledger_cost_centre_ids(
            tenant_id="firm-A", app_key="mitrabooks", accounting_entity_id="primary",
            cost_centre_ids={"cc-inactive"},
        )


@pytest.mark.asyncio
async def test_guard_noop_when_untagged(fake_dimensions):
    # Empty set is a pure no-op (untagged postings pay nothing).
    await validate_ledger_cost_centre_ids(
        tenant_id="firm-A", app_key="mitrabooks", accounting_entity_id="primary",
        cost_centre_ids=set(),
    )
