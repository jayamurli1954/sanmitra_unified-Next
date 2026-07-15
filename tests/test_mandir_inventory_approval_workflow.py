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
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def matches(row, query):
        return all(row.get(key) == value for key, value in query.items())

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query):
        return next((dict(row) for row in self.docs if self.matches(row, query)), None)

    def find(self, query):
        return FakeCursor([dict(row) for row in self.docs if self.matches(row, query)])

    async def update_one(self, query, update, **_kwargs):
        for row in self.docs:
            if self.matches(row, query):
                row.update(update.get("$set", {}))
                return SimpleNamespace(modified_count=1)
        return SimpleNamespace(modified_count=0)


@pytest.fixture()
def store(monkeypatch):
    collections = {
        "mandir_donations": FakeCollection(),
        "mandir_temples": FakeCollection([
            {"tenant_id": "temple-1", "app_key": "mandirmitra", "module_inventory_enabled": True}
        ]),
        "mandir_inventory_items": FakeCollection([
            {
                "id": "rice-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "is_active": True,
                "name": "Rice", "category": "FOOD", "opening_quantity": "0.000", "opening_unit_value": "50.00",
            }
        ]),
        "mandir_inventory_movements": FakeCollection(),
        "mandir_inventory_consumptions": FakeCollection(),
        "mandir_funds": FakeCollection(),
    }
    monkeypatch.setattr(mandir_router, "get_collection", lambda name: collections[name])
    return collections


def actor(user_id, tenant_id="temple-1"):
    return {"sub": user_id, "tenant_id": tenant_id, "app_key": "mandirmitra", "role": "tenant_admin"}


def pending_donation():
    return {
        "id": "don-1", "donation_id": "don-1", "tenant_id": "temple-1", "app_key": "mandirmitra",
        "receipt_number": "DON-0000001", "donation_type": "in_kind", "category": "Annadanam",
        "in_kind_item_name": "Rice bags", "in_kind_item_type": "rice", "in_kind_valuation_basis": "Invoice",
        "inventory_item_id": "rice-1", "inventory_quantity": "10", "amount": 500,
        "status": "pending_valuation", "valuation_status": "pending_approval", "created_by": "maker-1",
        "devotee": {"name": "Rice Sponsor"},
    }


@pytest.mark.asyncio
async def test_in_kind_valuation_maker_checker_posts_inventory_receipt(store, monkeypatch):
    store["mandir_donations"].docs.append(pending_donation())
    seen = {}

    async def noop(*_args, **_kwargs):
        return None

    async def account(_session, _tenant, *, code, **_kwargs):
        return int(code)

    async def income(*_args, **_kwargs):
        return 45002

    async def post(**kwargs):
        seen["post"] = kwargs
        return SimpleNamespace(id=1201), True

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", account)
    monkeypatch.setattr(mandir_router, "_resolve_mandir_income_account", income)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_in_kind_valuation(
            "don-1", {"approval_basis": "Invoice checked"}, SimpleNamespace(), actor("maker-1"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    approved = await mandir_router.approve_mandir_in_kind_valuation(
        "don-1",
        {"approved_amount": "525.50", "approved_quantity": "10", "approval_basis": "Invoice checked"},
        SimpleNamespace(), actor("approver-1"), None, "mandirmitra",
    )
    payload = seen["post"]["payload"]
    assert approved["status"] == "posted"
    assert approved["valuation_status"] == "approved"
    assert payload.lines[0].debit == payload.lines[1].credit
    assert payload.lines[0].account_id == 14004
    assert payload.lines[1].account_id == 45002
    assert payload.source_document_type == "in_kind_donation"
    assert seen["post"]["idempotency_key"] == "don_don-1"
    assert store["mandir_inventory_movements"].docs[0]["movement_type"] == "receipt"
    assert store["mandir_inventory_movements"].docs[0]["status"] == "posted"
    balance = await mandir_router._mandir_inventory_item_balance(
        tenant_id="temple-1", app_key="mandirmitra", item=store["mandir_inventory_items"].docs[0]
    )
    assert str(balance) == "10.000"

    repeated = await mandir_router.approve_mandir_in_kind_valuation(
        "don-1", {"approval_basis": "Invoice checked"}, SimpleNamespace(), actor("approver-1"), None, "mandirmitra"
    )
    assert repeated["_idempotent"] is True


@pytest.mark.asyncio
async def test_inventory_consumption_posts_issue_blocks_negative_and_reverses(store, monkeypatch):
    store["mandir_inventory_movements"].docs.append({
        "id": "receipt-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
        "movement_type": "receipt", "quantity": "10.000", "unit_value": "50.00",
        "total_value": "500.00", "status": "posted",
    })
    consumption = await mandir_router.create_mandir_inventory_consumption(
        {"item_id": "rice-1", "quantity": "4.500", "unit_value": "999.00", "reason": "Annadanam service"},
        actor("maker-1"), None, "mandirmitra",
    )
    assert consumption["unit_value"] == "50.00"
    store["mandir_inventory_movements"].docs.append({
        "id": "receipt-2", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
        "movement_type": "receipt", "quantity": "10.000", "unit_value": "100.00",
        "total_value": "1000.00", "status": "posted",
    })
    seen = {}

    async def noop(*_args, **_kwargs):
        return None

    async def account(_session, _tenant, *, code, **_kwargs):
        return int(code)

    async def post(**kwargs):
        seen["post"] = kwargs
        return SimpleNamespace(id=1301), True

    async def reverse(_session, **kwargs):
        seen["reverse"] = kwargs
        return SimpleNamespace(id=1302), True

    monkeypatch.setattr(mandir_router, "_ensure_default_mandir_sql_accounts_safe", noop)
    monkeypatch.setattr(mandir_router, "_resolve_or_create_mandir_account", account)
    monkeypatch.setattr(mandir_router, "post_journal_entry", post)
    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)

    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_inventory_consumption(
            consumption["id"], SimpleNamespace(), actor("maker-1"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    posted = await mandir_router.approve_mandir_inventory_consumption(
        consumption["id"], SimpleNamespace(), actor("approver-1"), None, "mandirmitra"
    )
    payload = seen["post"]["payload"]
    assert posted["status"] == "posted"
    assert posted["unit_value"] == "75.00"
    assert payload.lines[0].debit == payload.lines[1].credit == 337.5
    assert payload.lines[0].account_id == 54007
    assert payload.lines[1].account_id == 14004
    assert payload.source_document_type == "inventory_consumption"
    balance = await mandir_router._mandir_inventory_item_balance(
        tenant_id="temple-1", app_key="mandirmitra", item=store["mandir_inventory_items"].docs[0]
    )
    assert str(balance) == "15.500"

    too_large = await mandir_router.create_mandir_inventory_consumption(
        {"item_id": "rice-1", "quantity": "16", "unit_value": "50", "reason": "Excess issue"},
        actor("maker-2"), None, "mandirmitra",
    )
    with pytest.raises(HTTPException) as exc:
        await mandir_router.approve_mandir_inventory_consumption(
            too_large["id"], SimpleNamespace(), actor("approver-1"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    reversed_row = await mandir_router.cancel_mandir_inventory_consumption(
        consumption["id"], {"reason": "Consumption correction"}, SimpleNamespace(),
        actor("approver-2"), None, "mandirmitra",
    )
    assert reversed_row["status"] == "reversed"
    assert reversed_row["reversal_journal_id"] == 1302
    assert seen["reverse"]["source_key"] == f"inventory_consumption_{consumption['id']}"
    balance = await mandir_router._mandir_inventory_item_balance(
        tenant_id="temple-1", app_key="mandirmitra", item=store["mandir_inventory_items"].docs[0]
    )
    assert str(balance) == "20.000"


@pytest.mark.asyncio
async def test_inventory_workflows_reject_cross_tenant_item(store):
    store["mandir_inventory_items"].docs.append({
        "id": "other-item", "tenant_id": "temple-2", "app_key": "mandirmitra", "is_active": True,
        "name": "Other rice", "category": "FOOD", "opening_quantity": "5", "opening_unit_value": "10",
    })
    with pytest.raises(HTTPException) as exc:
        await mandir_router.create_mandir_inventory_consumption(
            {"item_id": "other-item", "quantity": "1", "unit_value": "10", "reason": "Invalid issue"},
            actor("maker-1"), None, "mandirmitra",
        )
    assert exc.value.status_code == 404
    assert store["mandir_inventory_consumptions"].docs == []


@pytest.mark.asyncio
async def test_inventory_reports_derive_fixed_precision_quantity_value_and_average(store):
    store["mandir_inventory_items"].docs[0].update({
        "code": "RICE", "unit": "KG", "reorder_level": 8,
        "opening_quantity": "5.000", "opening_unit_value": "40.00",
    })
    store["mandir_inventory_movements"].docs.extend([
        {
            "id": "receipt-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
            "movement_type": "receipt", "quantity": "10.000", "total_value": "800.00", "status": "posted",
        },
        {
            "id": "issue-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
            "movement_type": "issue", "quantity": "5.000", "total_value": "333.35", "status": "posted",
        },
        {
            "id": "foreign", "tenant_id": "temple-2", "app_key": "mandirmitra", "item_id": "rice-1",
            "movement_type": "receipt", "quantity": "999", "total_value": "99999", "status": "posted",
        },
    ])

    balances = await mandir_router.mandir_inventory_stock_balances(actor("viewer"), None, "mandirmitra")
    summary = await mandir_router.mandir_inventory_summary(actor("viewer"), None, "mandirmitra")

    assert balances == [{
        "item_id": "rice-1", "item_code": "RICE", "item_name": "Rice", "unit": "KG",
        "on_hand_qty": "10.000", "on_hand_value": "666.65",
        "weighted_average_unit_value": "66.67", "reorder_level": 8, "reorder_required": False,
    }]
    assert summary["totalItems"] == 1
    assert summary["lowStockItems"] == 0
    assert summary["totalValue"] == "666.65"
    assert summary["summary"]["total_value"] == "666.65"


@pytest.mark.asyncio
async def test_in_kind_donation_reversal_requires_unconsumed_stock(store, monkeypatch):
    donation = {
        **pending_donation(), "status": "posted", "valuation_status": "approved",
        "inventory_movement_id": "receipt-1", "journal_entry_id": 1401,
    }
    store["mandir_donations"].docs.append(donation)
    store["mandir_inventory_movements"].docs.append({
        "id": "receipt-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
        "item_name": "Rice", "movement_type": "receipt", "quantity": "10.000",
        "unit_value": "50.00", "total_value": "500.00", "status": "posted",
    })

    async def reverse(_session, **_kwargs):
        return SimpleNamespace(id=1402), True

    async def audit(**_kwargs):
        return None

    monkeypatch.setattr(mandir_router, "_reverse_mandir_source_journal", reverse)
    monkeypatch.setattr(mandir_router, "log_audit_event", audit)

    store["mandir_inventory_movements"].docs.append({
        "id": "issue-1", "tenant_id": "temple-1", "app_key": "mandirmitra", "item_id": "rice-1",
        "movement_type": "issue", "quantity": "1.000", "unit_value": "50.00",
        "total_value": "50.00", "status": "posted",
    })
    with pytest.raises(HTTPException) as exc:
        await mandir_router.cancel_donation_receipt(
            "don-1", {"reason": "Sponsor correction"}, SimpleNamespace(), actor("approver-2"), None, "mandirmitra"
        )
    assert exc.value.status_code == 409

    store["mandir_inventory_movements"].docs.pop()
    cancelled = await mandir_router.cancel_donation_receipt(
        "don-1", {"reason": "Sponsor correction"}, SimpleNamespace(), actor("approver-2"), None, "mandirmitra"
    )
    assert cancelled["status"] == "reversed"
    reversal = next(
        row for row in store["mandir_inventory_movements"].docs if row["movement_type"] == "receipt_reversal"
    )
    assert reversal["status"] == "posted"
    assert reversal["quantity"] == "10.000"
    balance = await mandir_router._mandir_inventory_item_balance(
        tenant_id="temple-1", app_key="mandirmitra", item=store["mandir_inventory_items"].docs[0]
    )
    assert str(balance) == "0.000"
