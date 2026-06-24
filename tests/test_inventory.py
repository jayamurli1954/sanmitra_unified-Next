"""Inventory (periodic method) — the stock-register assembler. Pure: items
and document lines are passed in as Mongo shapes them."""
from datetime import date
from decimal import Decimal

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
