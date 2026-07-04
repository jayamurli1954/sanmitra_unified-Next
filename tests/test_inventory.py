"""Inventory (periodic method) — the stock-register assembler. Pure: items
and document lines are passed in as Mongo shapes them."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.accounting.service import AccountingValidationError
from app.modules.business import inventory
from app.modules.business.inventory import assemble_stock_register

AS_OF = date(2026, 6, 30)


def _item(item_id, code, opening_qty="0", opening_value="0", uqc="NOS"):
    return {"item_id": item_id, "code": code, "name": f"Item {code}", "uqc": uqc,
            "opening_qty": opening_qty, "opening_value": opening_value}


def test_register_weighted_average_and_closing():
    out = assemble_stock_register(
        as_of=AS_OF,
        items=[_item("i1", "WIDGET", opening_qty="10", opening_value="1000.00")],
        purchase_lines=[
            {"item_id": "i1", "quantity": "20", "taxable_amount": "2600.00"},  # @130
        ],
        sales_lines=[{"item_id": "i1", "quantity": "12"}],
    )
    row = out["rows"][0]
    # Avg cost = (1000 + 2600) / (10 + 20) = 120.
    assert row["avg_cost"] == "120.00"
    assert row["opening_qty"] == "10.000"
    assert row["purchased_qty"] == "20.000"
    assert row["sold_qty"] == "12.000"
    assert row["closing_qty"] == "18.000"
    assert row["closing_value"] == "2160.00"     # 18 x 120
    assert row["negative_stock"] is False
    assert out["total_closing_value"] == "2160.00"
    assert out["negative_stock_items"] == 0


def test_register_flags_negative_stock_and_untracked_purchases():
    out = assemble_stock_register(
        as_of=AS_OF,
        items=[_item("i1", "GADGET")],
        purchase_lines=[
            {"item_id": "i1", "quantity": "5", "taxable_amount": "500.00"},
            {"item_id": None, "quantity": "3", "taxable_amount": "999.00"},   # expense-only line
        ],
        sales_lines=[{"item_id": "i1", "quantity": "8"}],                      # oversold
    )
    row = out["rows"][0]
    assert row["closing_qty"] == "-3.000"
    assert row["negative_stock"] is True
    assert row["closing_value"] == "0.00"        # never values negative stock
    assert out["negative_stock_items"] == 1
    assert out["untracked_purchase_value"] == "999.00"


def test_register_item_with_no_movement_keeps_opening():
    out = assemble_stock_register(
        as_of=AS_OF,
        items=[_item("i1", "STATIC", opening_qty="4", opening_value="400.00")],
        purchase_lines=[], sales_lines=[],
    )
    row = out["rows"][0]
    assert row["closing_qty"] == "4.000"
    assert row["avg_cost"] == "100.00"
    assert row["closing_value"] == "400.00"


def test_register_empty():
    out = assemble_stock_register(as_of=AS_OF, items=[], purchase_lines=[], sales_lines=[])
    assert out["rows"] == []
    assert out["total_closing_value"] == "0.00"


def test_register_manufacturing_consumes_raw_and_produces_finished_goods():
    """A completed work order consumes a raw material and adds a finished good at
    production cost. Closing stock must reflect both, valued correctly."""
    out = assemble_stock_register(
        as_of=AS_OF,
        items=[
            _item("rm", "BRASS", opening_qty="100", opening_value="20000.00"),  # @200
            _item("fg", "FRAME", opening_qty="0", opening_value="0"),
        ],
        purchase_lines=[],
        sales_lines=[],
        # Produced 10 frames at a production cost of 3837.50; consumed 15 brass sheets.
        produced_lines=[{"item_id": "fg", "quantity": "10", "value": "3837.50"}],
        consumed_lines=[{"item_id": "rm", "quantity": "15"}],
    )
    rows = {r["code"]: r for r in out["rows"]}
    # Raw material: 100 opening - 15 consumed = 85 @200 = 17000.
    assert rows["BRASS"]["consumed_qty"] == "15.000"
    assert rows["BRASS"]["closing_qty"] == "85.000"
    assert rows["BRASS"]["closing_value"] == "17000.00"
    # Finished good: 10 produced at production cost -> avg 383.75, closing 3837.50.
    assert rows["FRAME"]["produced_qty"] == "10.000"
    assert rows["FRAME"]["avg_cost"] == "383.75"
    assert rows["FRAME"]["closing_qty"] == "10.000"
    assert rows["FRAME"]["closing_value"] == "3837.50"
    assert out["total_closing_value"] == "20837.50"  # 17000 + 3837.50


def test_register_manufacturing_overconsumption_flags_negative():
    out = assemble_stock_register(
        as_of=AS_OF,
        items=[_item("rm", "BRASS", opening_qty="10", opening_value="2000.00")],
        purchase_lines=[], sales_lines=[],
        produced_lines=[],
        consumed_lines=[{"item_id": "rm", "quantity": "15"}],  # only 10 on hand
    )
    row = out["rows"][0]
    assert row["closing_qty"] == "-5.000"
    assert row["negative_stock"] is True
    assert out["negative_stock_items"] == 1


class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row.get(field), reverse=direction < 0)
        return self

    async def to_list(self, length):
        return self.rows[:length]


class _FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    @staticmethod
    def _matches(row, query):
        for key, expected in query.items():
            actual = row.get(key)
            if isinstance(expected, dict):
                if "$lte" in expected and not (actual <= expected["$lte"]):
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                continue
            if actual != expected:
                return False
        return True

    async def find_one(self, query):
        return next((row for row in self.rows if self._matches(row, query)), None)

    def find(self, query, projection=None):
        rows = [row for row in self.rows if self._matches(row, query)]
        if projection:
            keys = {key for key, include in projection.items() if include}
            rows = [{key: row.get(key) for key in keys if key in row} for row in rows]
        return _FakeCursor(rows)

    async def insert_one(self, doc):
        self.rows.append(doc)
        return SimpleNamespace(inserted_id=doc.get("item_id"))

    async def update_one(self, query, update):
        row = await self.find_one(query)
        if row is not None:
            row.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1 if row else 0)


@pytest.fixture
def fake_inventory_collections(monkeypatch):
    collections = {}

    def _get_collection(name):
        return collections.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.db.mongo.get_collection", _get_collection)
    return collections


@pytest.mark.asyncio
async def test_item_master_crud_is_scoped_and_validates_references(fake_inventory_collections):
    created = await inventory.create_item(
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        payload={"code": "widget-a", "name": "Widget A", "opening_qty": "5", "opening_value": "750"},
        created_by="tester",
    )

    assert created["code"] == "WIDGET-A"
    assert created["opening_qty"] == "5.000"
    assert created["opening_value"] == "750.00"

    scoped_rows = await inventory.list_items(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert [row["item_id"] for row in scoped_rows["items"]] == [created["item_id"]]

    other_tenant_rows = await inventory.list_items(
        tenant_id="tenant-b", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert other_tenant_rows["items"] == []

    await inventory.validate_item_refs(
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        line_items=[SimpleNamespace(item_id=created["item_id"])],
    )
    with pytest.raises(AccountingValidationError, match="Unknown inventory item"):
        await inventory.validate_item_refs(
            tenant_id="tenant-b",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            line_items=[SimpleNamespace(item_id=created["item_id"])],
        )

    deactivated = await inventory.deactivate_item(
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        item_id=created["item_id"],
        updated_by="tester",
    )
    assert deactivated["is_active"] is False
    active_rows = await inventory.list_items(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
    )
    assert active_rows["items"] == []
    all_rows = await inventory.list_items(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary", include_inactive=True,
    )
    assert all_rows["count"] == 1


@pytest.mark.asyncio
async def test_item_master_rejects_duplicate_code_and_bad_opening_stock(fake_inventory_collections):
    payload = {"code": "DUP", "name": "Duplicate", "opening_qty": "1", "opening_value": "10"}
    await inventory.create_item(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        payload=payload, created_by="tester",
    )

    with pytest.raises(AccountingValidationError, match="already exists"):
        await inventory.create_item(
            tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            payload=payload, created_by="tester",
        )

    with pytest.raises(AccountingValidationError, match="Opening value needs"):
        await inventory.create_item(
            tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            payload={"code": "BAD", "name": "Bad", "opening_qty": "0", "opening_value": "10"},
            created_by="tester",
        )


@pytest.mark.asyncio
async def test_build_stock_register_uses_only_posted_same_scope_documents(fake_inventory_collections):
    from app.modules.business.service import PURCHASE_BILLS_COLLECTION, SALES_INVOICES_COLLECTION

    fake_inventory_collections[inventory.ITEMS_COLLECTION] = _FakeCollection([
        {**_item("i1", "WIDGET", opening_qty="10", opening_value="1000.00"),
         "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary"},
        {**_item("i2", "OTHER"),
         "tenant_id": "tenant-b", "app_key": "mitrabooks", "accounting_entity_id": "primary"},
    ])
    fake_inventory_collections[PURCHASE_BILLS_COLLECTION] = _FakeCollection([
        {
            "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary",
            "status": "posted", "bill_date": "2026-06-10",
            "line_items": [{"item_id": "i1", "quantity": "5", "taxable_amount": "750.00"}],
        },
        {
            "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary",
            "status": "draft", "bill_date": "2026-06-10",
            "line_items": [{"item_id": "i1", "quantity": "99", "taxable_amount": "9900.00"}],
        },
        {
            "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary",
            "status": "posted", "bill_date": "2026-07-01",
            "line_items": [{"item_id": "i1", "quantity": "99", "taxable_amount": "9900.00"}],
        },
        {
            "tenant_id": "tenant-b", "app_key": "mitrabooks", "accounting_entity_id": "primary",
            "status": "posted", "bill_date": "2026-06-10",
            "line_items": [{"item_id": "i2", "quantity": "99", "taxable_amount": "9900.00"}],
        },
    ])
    fake_inventory_collections[SALES_INVOICES_COLLECTION] = _FakeCollection([
        {
            "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary",
            "status": "posted", "invoice_date": "2026-06-20",
            "line_items": [{"item_id": "i1", "quantity": "4"}],
        },
        {
            "tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "other",
            "status": "posted", "invoice_date": "2026-06-20",
            "line_items": [{"item_id": "i1", "quantity": "99"}],
        },
    ])

    out = await inventory.build_stock_register(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary", as_of=AS_OF,
    )

    assert out["item_count"] == 1
    row = out["rows"][0]
    assert row["code"] == "WIDGET"
    assert row["purchased_qty"] == "5.000"
    assert row["sold_qty"] == "4.000"
    assert row["closing_qty"] == "11.000"
    assert out["total_closing_value"] == "1283.37"


@pytest.mark.asyncio
async def test_post_closing_stock_posts_balanced_inventory_journal(monkeypatch):
    captured = {}

    async def fake_build_stock_register(**kwargs):
        return {"negative_stock_items": 0, "total_closing_value": "2160.00", "item_count": 1}

    async def fake_find_entries(*args, **kwargs):
        return []

    async def fake_init(*args, **kwargs):
        captured["init"] = kwargs

    async def fake_accounts(*args, **kwargs):
        return {
            inventory.INVENTORY_ACCOUNT_CODE: {"account_id": 13001},
            inventory.COGS_ACCOUNT_CODE: {"account_id": 51002},
        }, {}

    async def fake_post(*args, **kwargs):
        captured["post"] = kwargs
        return SimpleNamespace(id=9001), True

    monkeypatch.setattr(inventory, "build_stock_register", fake_build_stock_register)
    monkeypatch.setattr(inventory, "find_closing_stock_entries", fake_find_entries)
    monkeypatch.setattr("app.accounting.service.initialize_default_chart_of_accounts", fake_init)
    monkeypatch.setattr("app.modules.business.opening_close._account_lookups", fake_accounts)
    monkeypatch.setattr("app.accounting.service.post_journal_entry", fake_post)

    result = await inventory.post_closing_stock(
        object(),
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        as_of=AS_OF,
        created_by="tester",
        idempotency_key="inventory-closing-test",
    )

    assert result == {
        "journal_entry_id": 9001,
        "created": True,
        "as_of": "2026-06-30",
        "closing_stock_value": "2160.00",
        "item_count": 1,
    }
    payload = captured["post"]["payload"]
    assert captured["post"]["idempotency_key"] == "inventory-closing-test"
    assert payload.source_document_type == "closing_stock"
    assert payload.lines[0].account_id == 13001
    assert payload.lines[0].debit == Decimal("2160.00")
    assert payload.lines[0].credit == Decimal("0")
    assert payload.lines[1].account_id == 51002
    assert payload.lines[1].debit == Decimal("0")
    assert payload.lines[1].credit == Decimal("2160.00")


@pytest.mark.asyncio
async def test_post_closing_stock_blocks_negative_stock_and_duplicate_entry(monkeypatch):
    async def fake_negative_register(**kwargs):
        return {"negative_stock_items": 1, "total_closing_value": "2160.00", "item_count": 1}

    monkeypatch.setattr(inventory, "build_stock_register", fake_negative_register)

    with pytest.raises(AccountingValidationError, match="negative closing stock"):
        await inventory.post_closing_stock(
            object(),
            tenant_id="tenant-a",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            as_of=AS_OF,
            created_by="tester",
        )

    async def fake_positive_register(**kwargs):
        return {"negative_stock_items": 0, "total_closing_value": "2160.00", "item_count": 1}

    async def fake_existing(*args, **kwargs):
        return [{"journal_entry_id": 9001, "entry_date": "2026-06-30"}]

    monkeypatch.setattr(inventory, "build_stock_register", fake_positive_register)
    monkeypatch.setattr(inventory, "find_closing_stock_entries", fake_existing)

    with pytest.raises(AccountingValidationError, match="already exists"):
        await inventory.post_closing_stock(
            object(),
            tenant_id="tenant-a",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            as_of=AS_OF,
            created_by="tester",
        )
