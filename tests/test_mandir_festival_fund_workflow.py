from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.modules.mandir_compat.router as mandir_router


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, *_args):
        return self

    async def to_list(self, length=None):
        return list(self.docs if length is None else self.docs[:length])


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query):
        return next((dict(row) for row in self.docs if all(row.get(key) == value for key, value in query.items())), None)

    def find(self, query):
        return FakeCursor([dict(row) for row in self.docs if all(row.get(key) == value for key, value in query.items())])

    async def delete_one(self, query):
        self.docs = [row for row in self.docs if not all(row.get(key) == value for key, value in query.items())]

    async def update_one(self, query, update, **_kwargs):
        for row in self.docs:
            if all(row.get(key) == value for key, value in query.items()):
                row.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


@pytest.fixture()
def store(monkeypatch):
    collections = {
        "mandir_funds": FakeCollection(),
        "mandir_festivals": FakeCollection(),
        "mandir_donations": FakeCollection(),
        "mandir_donation_compliance_config": FakeCollection(),
        "mandir_fund_transfers": FakeCollection(),
        "mandir_fund_opening_balances": FakeCollection(),
    }
    monkeypatch.setattr(mandir_router, "get_collection", lambda name: collections[name])
    dimensions = []

    async def create_dimension(**kwargs):
        dimension = {"dimension_id": f"fund-dimension-{len(dimensions) + 1}", **kwargs}
        dimensions.append(dimension)
        return dimension

    async def deactivate_dimension(**_kwargs):
        return None

    monkeypatch.setattr(mandir_router, "create_dimension", create_dimension)
    monkeypatch.setattr(mandir_router, "deactivate_dimension", deactivate_dimension)
    return collections


def actor(tenant_id="temple-1"):
    return {"sub": "admin-1", "tenant_id": tenant_id, "app_key": "mandirmitra", "role": "tenant_admin"}


@pytest.mark.asyncio
async def test_fund_and_festival_masters_are_tenant_scoped(store):
    fund = await mandir_router.create_mandir_fund(
        {"name": "Gopuram Renovation", "fund_type": "restricted"}, actor(), None, "mandirmitra"
    )
    festival = await mandir_router.create_mandir_festival(
        {"name": "Navaratri", "start_date": "2026-10-11", "end_date": "2026-10-19"},
        actor(), None, "mandirmitra",
    )
    assert fund["fund_type"] == "restricted"
    assert fund["accounting_dimension_id"] == "fund-dimension-1"
    assert festival["start_date"] == "2026-10-11"
    assert len(await mandir_router.list_mandir_funds(actor(), None, "mandirmitra")) == 1
    assert await mandir_router.list_mandir_funds(actor("temple-2"), None, "mandirmitra") == []

    store["mandir_funds"].docs.append(
        {"id": "other-fund", "tenant_id": "temple-2", "app_key": "mandirmitra", "active": True, "name": "Other"}
    )
    assert all(row["id"] != "other-fund" for row in await mandir_router.list_mandir_funds(actor(), None, "mandirmitra"))


@pytest.mark.asyncio
async def test_designated_donation_posts_to_specific_purpose_and_sponsorship_income(store, monkeypatch):
    fund = await mandir_router.create_mandir_fund(
        {"name": "Gopuram Renovation", "fund_type": "restricted"}, actor(), None, "mandirmitra"
    )
    festival = await mandir_router.create_mandir_festival(
        {"name": "Navaratri", "start_date": "2026-10-11", "end_date": "2026-10-19"},
        actor(), None, "mandirmitra",
    )
    income_categories = []
    posted = []

    async def noop(*_args, **_kwargs):
        return None

    async def receipt(**_kwargs):
        return f"DON-{len(posted) + 1:07d}"

    async def payment(*_args, **_kwargs):
        return 11001

    async def income(_session, _tenant_id, category):
        income_categories.append(category)
        return 44003 if category == "Specific Purpose Donations" else 45001

    async def post(**kwargs):
        posted.append(kwargs)
        return SimpleNamespace(id=900 + len(posted)), True

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_next_receipt_number", receipt)
    monkeypatch.setattr(mandir_router, "_resolve_mandir_payment_account_id", payment)
    monkeypatch.setattr(mandir_router, "_resolve_mandir_income_account", income)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "_upsert_devotee_from_contribution", noop)

    designated = await mandir_router.create_donation(
        {"amount": "101.25", "category": "General Donation", "fund_id": fund["id"], "devotee_name": "Donor One"},
        SimpleNamespace(), actor(), None, "mandirmitra", None,
    )
    sponsored = await mandir_router.create_donation(
        {
            "amount": "202.50", "category": "General Donation", "festival_id": festival["id"],
            "is_sponsorship": True, "devotee_name": "Donor Two",
        },
        SimpleNamespace(), actor(), None, "mandirmitra", None,
    )

    assert designated["fund_name"] == "Gopuram Renovation"
    assert designated["income_category"] == "Specific Purpose Donations"
    assert sponsored["festival_name"] == "Navaratri"
    assert sponsored["income_category"] == "Sponsorship Income"
    assert income_categories == ["Specific Purpose Donations", "Sponsorship Income"]
    for call in posted:
        lines = call["payload"].lines
        assert lines[0].debit == lines[1].credit
    assert posted[0]["payload"].lines[1].cost_center_id == fund["accounting_dimension_id"]
    assert posted[0]["payload"].source_document_type == "donation"
    assert posted[0]["idempotency_key"].startswith("don_")


@pytest.mark.asyncio
async def test_cross_tenant_designation_is_rejected_before_donation_insert(store, monkeypatch):
    store["mandir_funds"].docs.append(
        {
            "id": "other-fund", "tenant_id": "temple-2", "app_key": "mandirmitra", "active": True,
            "name": "Other Tenant Fund", "fund_type": "restricted",
        }
    )

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_donation(
            {"amount": "10.00", "fund_id": "other-fund"}, SimpleNamespace(), actor(), None, "mandirmitra", None
        )
    assert exc.value.status_code == 404
    assert store["mandir_donations"].docs == []


@pytest.mark.asyncio
async def test_designation_reports_use_posted_rows_only(monkeypatch):
    async def posted_only(*_args, **_kwargs):
        return [
            {"fund_id": "fund-1", "fund_name": "Corpus", "amount": 50.25},
            {"fund_id": "fund-1", "fund_name": "Corpus", "amount": 49.75},
            {"fund_id": "", "fund_name": "", "amount": 999},
        ]

    monkeypatch.setattr(mandir_router, "posted_donations", posted_only)
    report = await mandir_router._mandir_donation_designation_report(
        SimpleNamespace(), tenant_id="temple-1", app_key="mandirmitra",
        from_date=date(2026, 1, 1), to_date=date(2026, 12, 31), id_field="fund_id", name_field="fund_name",
    )
    assert report["items"] == [{"id": "fund-1", "name": "Corpus", "count": 2, "amount": 100.0}]
    assert report["total_amount"] == 100.0


@pytest.mark.asyncio
async def test_fund_transfer_requires_maker_checker_posts_dimensions_and_reverses(store, monkeypatch):
    source = await mandir_router.create_mandir_fund(
        {"name": "General Fund", "fund_type": "general"}, actor(), None, "mandirmitra"
    )
    destination = await mandir_router.create_mandir_fund(
        {"name": "Renovation Fund", "fund_type": "restricted"}, actor(), None, "mandirmitra"
    )
    transfer = await mandir_router.create_mandir_fund_transfer(
        {
            "from_fund_id": source["id"], "to_fund_id": destination["id"],
            "amount": "83.45", "transfer_date": "2026-07-13", "reason": "Trustee allocation",
        },
        {**actor(), "sub": "maker-1", "role": "operator"}, None, "mandirmitra",
    )
    assert transfer["status"] == "pending_approval"
    assert transfer["amount"] == "83.45"

    seen = {}

    async def noop(*_args, **_kwargs):
        return None

    async def control(*_args, **_kwargs):
        return 32001

    async def post(**kwargs):
        seen["post"] = kwargs
        return SimpleNamespace(id=1001), True

    async def reverse(_session, **kwargs):
        seen["reverse"] = kwargs
        return SimpleNamespace(id=1002), True

    async def balances(*_args, **_kwargs):
        return {"items": [{"fund_id": source["id"], "closing_balance": 1000.00}]}

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", control)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)
    monkeypatch.setattr(mandir_router, "_mandir_fund_subledger_data", balances)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_fund_transfer(
            transfer["id"], SimpleNamespace(), {**actor(), "sub": "maker-1"}, None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    approved = await mandir_router.approve_mandir_fund_transfer(
        transfer["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
    )
    payload = seen["post"]["payload"]
    assert approved["status"] == "posted"
    assert payload.lines[0].debit == payload.lines[1].credit
    assert payload.lines[0].cost_center_id == source["accounting_dimension_id"]
    assert payload.lines[1].cost_center_id == destination["accounting_dimension_id"]
    assert payload.source_document_type == "fund_transfer"
    assert seen["post"]["idempotency_key"] == f"fund_transfer_{transfer['id']}"

    repeated = await mandir_router.approve_mandir_fund_transfer(
        transfer["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True

    reversed_row = await mandir_router.cancel_mandir_fund_transfer(
        transfer["id"], {"reason": "Trustee correction"}, SimpleNamespace(),
        {**actor(), "sub": "approver-2"}, None, "mandirmitra",
    )
    assert reversed_row["status"] == "reversed"
    assert reversed_row["reversal_journal_id"] == 1002
    assert seen["reverse"]["source_key"] == f"fund_transfer_{transfer['id']}"


@pytest.mark.asyncio
async def test_fund_opening_balance_requires_maker_checker_posts_and_reverses(store, monkeypatch):
    fund = await mandir_router.create_mandir_fund(
        {"name": "Corpus Fund", "fund_type": "corpus"}, actor(), None, "mandirmitra"
    )
    maker = {**actor(), "sub": "maker-1", "role": "operator"}
    opening = await mandir_router.create_mandir_fund_opening_balance(
        {
            "fund_id": fund["id"], "amount": "1000.25", "opening_date": "2026-04-01",
            "reason": "Audited brought-forward balance",
        },
        maker, None, "mandirmitra",
    )
    assert opening["status"] == "pending_approval"
    assert opening["amount"] == "1000.25"

    seen = {}

    async def noop(*_args, **_kwargs):
        return None

    async def account(_session, _tenant, *, code, **_kwargs):
        return int(code)

    async def post(**kwargs):
        seen["post"] = kwargs
        return SimpleNamespace(id=1201), True

    async def reverse(_session, **kwargs):
        seen["reverse"] = kwargs
        return SimpleNamespace(id=1202), True

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", account)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_fund_opening_balance(
            opening["id"], SimpleNamespace(), maker, None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    posted = await mandir_router.approve_mandir_fund_opening_balance(
        opening["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
    )
    payload = seen["post"]["payload"]
    assert posted["status"] == "posted"
    assert payload.lines[0].account_id == 33001
    assert payload.lines[0].debit == payload.lines[1].credit == Decimal("1000.25")
    assert payload.lines[0].cost_center_id is None
    assert payload.lines[1].account_id == 32001
    assert payload.lines[1].cost_center_id == fund["accounting_dimension_id"]
    assert payload.source_document_type == "fund_opening_balance"
    assert seen["post"]["idempotency_key"] == f"fund_opening_balance_{opening['id']}"

    repeated = await mandir_router.approve_mandir_fund_opening_balance(
        opening["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True

    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_fund_opening_balance(
            {
                "fund_id": fund["id"], "amount": "1.00", "opening_date": "2026-04-01",
                "reason": "Duplicate balance",
            },
            maker, None, "mandirmitra",
        )
    assert exc.value.status_code == 409

    reversed_row = await mandir_router.cancel_mandir_fund_opening_balance(
        opening["id"], {"reason": "Audit correction"}, SimpleNamespace(),
        {**actor(), "sub": "approver-2"}, None, "mandirmitra",
    )
    assert reversed_row["status"] == "reversed"
    assert reversed_row["reversal_journal_id"] == 1202
    assert seen["reverse"]["source_key"] == f"fund_opening_balance_{opening['id']}"


@pytest.mark.asyncio
async def test_fund_opening_balance_rejects_cross_tenant_fund(store):
    store["mandir_funds"].docs.append({
        "id": "other-fund", "tenant_id": "temple-2", "app_key": "mandirmitra", "active": True,
        "name": "Other Corpus", "accounting_dimension_id": "other-dimension",
    })
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_fund_opening_balance(
            {
                "fund_id": "other-fund", "amount": "100.00", "opening_date": "2026-04-01",
                "reason": "Invalid cross-tenant opening",
            },
            {**actor(), "sub": "maker-1"}, None, "mandirmitra",
        )
    assert exc.value.status_code == 404
    assert store["mandir_fund_opening_balances"].docs == []


@pytest.mark.asyncio
async def test_fund_transfer_rejects_cross_tenant_fund(store):
    local = await mandir_router.create_mandir_fund(
        {"name": "Local Fund", "fund_type": "general"}, actor(), None, "mandirmitra"
    )
    store["mandir_funds"].docs.append(
        {
            "id": "other-fund", "tenant_id": "temple-2", "app_key": "mandirmitra", "active": True,
            "name": "Other Fund", "accounting_dimension_id": "other-dimension",
        }
    )
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_fund_transfer(
            {
                "from_fund_id": local["id"], "to_fund_id": "other-fund", "amount": "10.00",
                "reason": "Invalid transfer",
            },
            {**actor(), "sub": "maker-1"}, None, "mandirmitra",
        )
    assert exc.value.status_code == 404
    assert store["mandir_fund_transfers"].docs == []


@pytest.mark.asyncio
async def test_fund_transfer_approval_rejects_insufficient_source_balance(store, monkeypatch):
    source = await mandir_router.create_mandir_fund(
        {"name": "General Fund", "fund_type": "general"}, actor(), None, "mandirmitra"
    )
    destination = await mandir_router.create_mandir_fund(
        {"name": "Renovation Fund", "fund_type": "restricted"}, actor(), None, "mandirmitra"
    )
    transfer = await mandir_router.create_mandir_fund_transfer(
        {
            "from_fund_id": source["id"], "to_fund_id": destination["id"], "amount": "50.00",
            "transfer_date": "2026-07-13", "reason": "Trustee allocation",
        },
        {**actor(), "sub": "maker-1"}, None, "mandirmitra",
    )

    async def balances(*_args, **_kwargs):
        return {"items": [{"fund_id": source["id"], "closing_balance": 49.99}]}

    monkeypatch.setattr(mandir_router, "_mandir_fund_subledger_data", balances)
    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_fund_transfer(
            transfer["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
        )
    assert exc.value.status_code == 409
    assert "49.99" in exc.value.detail


@pytest.mark.asyncio
async def test_fund_subledger_combines_posted_ledger_and_transfer_activity(store, monkeypatch):
    source = await mandir_router.create_mandir_fund(
        {"name": "General Fund", "fund_type": "general"}, actor(), None, "mandirmitra"
    )
    destination = await mandir_router.create_mandir_fund(
        {"name": "Renovation Fund", "fund_type": "restricted"}, actor(), None, "mandirmitra"
    )
    store["mandir_fund_transfers"].docs.append(
        {
            "id": "transfer-1", "tenant_id": "temple-1", "app_key": "mandirmitra",
            "from_fund_id": source["id"], "to_fund_id": destination["id"], "amount": "25.00",
            "transfer_date": "2026-07-13", "status": "posted", "journal_entry_id": 77,
        }
    )
    store["mandir_fund_opening_balances"].docs.append(
        {
            "id": "opening-1", "tenant_id": "temple-1", "app_key": "mandirmitra",
            "fund_id": source["id"], "amount": "200.00", "opening_date": "2026-01-01",
            "status": "posted", "journal_entry_id": 76,
        }
    )

    async def ledger(*_args, **kwargs):
        from_date = kwargs["from_date"]
        to_date = kwargs["to_date"]
        if from_date == date(1900, 1, 1) and to_date == date(2026, 6, 30):
            source_values = {"income": 20, "expense": 2}
            destination_values = {}
        elif from_date == date(1900, 1, 1):
            source_values = {"income": 120, "expense": 12}
            destination_values = {"income": 50, "expense": 5}
        else:
            source_values = {"income": 100, "expense": 10}
            destination_values = {"income": 50, "expense": 5}
        return {
            "buckets": {
                source["accounting_dimension_id"]: source_values,
                destination["accounting_dimension_id"]: destination_values,
            }
        }

    monkeypatch.setattr(mandir_router, "get_cost_centre_ledger_pl", ledger)
    report = await mandir_router.mandir_report_fund_subledger(
        date(2026, 7, 1), date(2026, 7, 31), SimpleNamespace(), actor(), None, "mandirmitra"
    )
    rows = {row["fund_id"]: row for row in report["items"]}
    assert rows[source["id"]]["opening_balance"] == 218.0
    assert rows[source["id"]]["net_activity"] == 65.0
    assert rows[source["id"]]["closing_balance"] == 283.0
    assert rows[destination["id"]]["net_activity"] == 70.0
    assert report["totals"]["transfers_in"] == report["totals"]["transfers_out"] == 25.0

    as_of = await mandir_router.mandir_report_funds_as_of(
        date(2026, 7, 31), SimpleNamespace(), actor(), None, "mandirmitra"
    )
    as_of_rows = {row["fund_id"]: row for row in as_of["items"]}
    assert as_of_rows[source["id"]]["balance"] == 283.0
    assert as_of_rows[destination["id"]]["balance"] == 70.0
    assert as_of["total_balance"] == 353.0


@pytest.mark.asyncio
async def test_fund_transfer_approval_compensates_when_domain_update_fails(store, monkeypatch):
    store["mandir_fund_transfers"].docs.append(
        {
            "id": "transfer-2", "tenant_id": "temple-1", "app_key": "mandirmitra",
            "from_fund_id": "fund-1", "to_fund_id": "fund-2",
            "from_fund_name": "General", "to_fund_name": "Corpus",
            "from_dimension_id": "dimension-1", "to_dimension_id": "dimension-2",
            "amount": "75.25", "transfer_date": "2026-07-13", "reference": "FTR-TRANSFER2",
            "status": "pending_approval", "created_by": "maker-1",
        }
    )
    compensated = {}

    async def noop(*_args, **_kwargs):
        return None

    async def control(*_args, **_kwargs):
        return 32001

    async def post(**_kwargs):
        return SimpleNamespace(id=1101), True

    async def reverse(**kwargs):
        compensated.update(kwargs)
        return SimpleNamespace(id=1102), True

    async def fail_update(*_args, **_kwargs):
        raise RuntimeError("mongo unavailable")

    async def balances(*_args, **_kwargs):
        return {"items": [{"fund_id": "fund-1", "closing_balance": 1000.00}]}

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", control)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "reverse_journal_entry", reverse)
    monkeypatch.setattr(mandir_router, "_mandir_fund_subledger_data", balances)
    monkeypatch.setattr(store["mandir_fund_transfers"], "update_one", fail_update)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_fund_transfer(
            "transfer-2", SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
        )
    assert exc.value.status_code == 500
    assert compensated["journal_id"] == 1101
    assert compensated["idempotency_key"] == "fund_transfer_transfer-2_approval_compensation"


@pytest.mark.asyncio
async def test_fund_opening_approval_compensates_when_domain_update_fails(store, monkeypatch):
    fund = await mandir_router.create_mandir_fund(
        {"name": "Corpus Fund", "fund_type": "corpus"}, actor(), None, "mandirmitra"
    )
    opening = await mandir_router.create_mandir_fund_opening_balance(
        {
            "fund_id": fund["id"], "amount": "600.75", "opening_date": "2026-04-01",
            "reason": "Audited brought-forward balance",
        },
        {**actor(), "sub": "maker-1"}, None, "mandirmitra",
    )
    compensated = {}

    async def noop(*_args, **_kwargs):
        return None

    async def account(_session, _tenant, *, code, **_kwargs):
        return int(code)

    async def post(**_kwargs):
        return SimpleNamespace(id=1301), True

    async def reverse(**kwargs):
        compensated.update(kwargs)
        return SimpleNamespace(id=1302), True

    async def fail_update(*_args, **_kwargs):
        raise RuntimeError("mongo unavailable")

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", account)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "reverse_journal_entry", reverse)
    monkeypatch.setattr(store["mandir_fund_opening_balances"], "update_one", fail_update)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_fund_opening_balance(
            opening["id"], SimpleNamespace(), {**actor(), "sub": "approver-1"}, None, "mandirmitra"
        )
    assert exc.value.status_code == 500
    assert compensated["journal_id"] == 1301
    assert compensated["idempotency_key"] == f"fund_opening_balance_{opening['id']}_approval_compensation"
