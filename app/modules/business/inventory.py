"""Inventory accounting — opt-in per business.

The `inventory_enabled` flag lives on the entity's invoice settings and is
OFF by default: service businesses and traders who don't want stock keeping
see no inventory screens and no behavioural change anywhere.

When enabled, v1 is the PERIODIC method most Indian SMEs actually use:

  * Item master (code, name, UQC, HSN, opening stock).
  * Invoice/bill lines may reference an item; the stock register derives
    per-item movements from posted documents — opening + purchases − sales —
    valued at the weighted-average purchase cost. Nothing extra is posted per
    document, so the GST/TDS/RCM journal logic is untouched.
  * At period end the admin posts the CLOSING-STOCK journal —
    Dr Inventory / Stock in Hand (13001), Cr Cost of Goods Sold (51002) —
    which is what makes the P&L show true COGS and the Balance Sheet show
    stock. Reverse the previous closing entry before posting a fresh one.

Perpetual inventory (COGS per sale) is a v2 — the register's weighted-average
math is already the costing engine it would need.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

ITEMS_COLLECTION = "business_items"

INVENTORY_ACCOUNT_CODE = "13001"   # Inventory / Stock in Hand (asset)
COGS_ACCOUNT_CODE = "51002"        # Cost of Goods Sold (expense)

_CENT = Decimal("0.01")
_QTY = Decimal("0.001")


def _q2(value) -> Decimal:
    return Decimal(str(value if value not in (None, "") else 0)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _q3(value) -> Decimal:
    return Decimal(str(value if value not in (None, "") else 0)).quantize(_QTY, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


def _response(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


async def is_inventory_enabled(*, tenant_id: str, app_key: str, accounting_entity_id: str) -> bool:
    from app.modules.business.service import get_invoice_settings

    settings = await get_invoice_settings(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    return bool(settings.get("inventory_enabled"))


# --------------------------------------------------------------------------- #
# Item master.
# --------------------------------------------------------------------------- #

async def create_item(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, payload: dict, created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    name = str(payload.get("name") or "").strip()
    if not name:
        raise AccountingValidationError("Item name is required")
    code = str(payload.get("code") or "").strip().upper() or name[:12].upper().replace(" ", "-")
    opening_qty = _q3(payload.get("opening_qty") or 0)
    opening_value = _q2(payload.get("opening_value") or 0)
    if opening_qty < 0 or opening_value < 0:
        raise AccountingValidationError("Opening stock cannot be negative")
    if opening_qty == 0 and opening_value > 0:
        raise AccountingValidationError("Opening value needs an opening quantity")

    col = get_collection(ITEMS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    if await col.find_one({**scope, "code": code}):
        raise AccountingValidationError(f"An item with code '{code}' already exists")

    now = _now()
    doc = {
        **scope,
        "item_id": str(uuid4()),
        "code": code,
        "name": name,
        "uqc": str(payload.get("uqc") or "NOS").strip().upper() or "NOS",
        "hsn_sac": str(payload.get("hsn_sac") or "").strip() or None,
        "gst_rate": str(_q2(payload.get("gst_rate") or 0)),
        "opening_qty": str(opening_qty),
        "opening_value": str(opening_value),
        "is_active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(doc)
    return _response(doc)


async def list_items(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, include_inactive: bool = False,
) -> dict:
    from app.db.mongo import get_collection

    filters = _scope(tenant_id, app_key, accounting_entity_id)
    if not include_inactive:
        filters["is_active"] = True
    rows = await get_collection(ITEMS_COLLECTION).find(filters).sort("code", 1).to_list(length=2000)
    items = [_response(r) for r in rows]
    return {"items": items, "count": len(items)}


async def deactivate_item(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, item_id: str, updated_by: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError
    from app.db.mongo import get_collection

    col = get_collection(ITEMS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "item_id": item_id})
    if row is None:
        raise AccountingNotFoundError("Item not found")
    await col.update_one(
        {**scope, "item_id": item_id},
        {"$set": {"is_active": False, "updated_by": updated_by, "updated_at": _now()}},
    )
    row["is_active"] = False
    return _response(row)


async def validate_item_refs(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, line_items: list,
) -> None:
    """Raise when a document line references an unknown item. Lazy — documents
    without item tags never touch the items collection."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    ids = {str(getattr(ln, "item_id", None) or "") for ln in line_items}
    ids.discard("")
    if not ids:
        return
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    rows = await get_collection(ITEMS_COLLECTION).find(
        {**scope, "item_id": {"$in": sorted(ids)}}, {"item_id": 1}
    ).to_list(length=len(ids))
    found = {str(r.get("item_id")) for r in rows}
    missing = ids - found
    if missing:
        raise AccountingValidationError(f"Unknown inventory item(s): {', '.join(sorted(missing))}")


# --------------------------------------------------------------------------- #
# Stock register — pure assembly.
# --------------------------------------------------------------------------- #

def assemble_stock_register(
    *,
    as_of: date,
    items: list[dict],
    purchase_lines: list[dict],   # {item_id, quantity, taxable_amount}
    sales_lines: list[dict],      # {item_id, quantity}
    produced_lines: list[dict] | None = None,   # {item_id, quantity, value}  (manufactured FG)
    consumed_lines: list[dict] | None = None,   # {item_id, quantity}         (raw materials issued)
) -> dict:
    """Per-item stock position as of a date, periodic method:

        closing qty   = opening + purchased + produced − sold − consumed
        avg cost      = (opening value + purchase value + production value)
                        / (opening qty + purchased qty + produced qty)
        closing value = closing qty × avg cost

    Sales and manufacturing consumption are valued at that same weighted-average
    cost. Manufactured finished goods are added at their production cost (work-order
    actual cost). Items driven negative are flagged — that means more was sold/
    consumed than the books ever received or produced."""
    produced_lines = produced_lines or []
    consumed_lines = consumed_lines or []
    by_item: dict[str, dict] = {}
    for it in items:
        by_item[str(it["item_id"])] = {
            "item": it,
            "purchased_qty": Decimal("0"), "purchased_value": Decimal("0"),
            "produced_qty": Decimal("0"), "produced_value": Decimal("0"),
            "sold_qty": Decimal("0"), "consumed_qty": Decimal("0"),
        }
    untracked_purchase_value = Decimal("0")
    for ln in purchase_lines:
        bucket = by_item.get(str(ln.get("item_id") or ""))
        if bucket is None:
            untracked_purchase_value += _q2(ln.get("taxable_amount"))
            continue
        bucket["purchased_qty"] += _q3(ln.get("quantity"))
        bucket["purchased_value"] += _q2(ln.get("taxable_amount"))
    for ln in produced_lines:
        bucket = by_item.get(str(ln.get("item_id") or ""))
        if bucket is None:
            continue
        bucket["produced_qty"] += _q3(ln.get("quantity"))
        bucket["produced_value"] += _q2(ln.get("value"))
    for ln in sales_lines:
        bucket = by_item.get(str(ln.get("item_id") or ""))
        if bucket is None:
            continue
        bucket["sold_qty"] += _q3(ln.get("quantity"))
    for ln in consumed_lines:
        bucket = by_item.get(str(ln.get("item_id") or ""))
        if bucket is None:
            continue
        bucket["consumed_qty"] += _q3(ln.get("quantity"))

    rows: list[dict] = []
    total_closing_value = Decimal("0.00")
    negative_items = 0
    for item_id, b in by_item.items():
        it = b["item"]
        opening_qty = _q3(it.get("opening_qty"))
        opening_value = _q2(it.get("opening_value"))
        in_qty = b["purchased_qty"] + b["produced_qty"]
        available_qty = opening_qty + in_qty
        available_value = opening_value + b["purchased_value"] + b["produced_value"]
        avg_cost = _q2(available_value / available_qty) if available_qty > 0 else Decimal("0.00")
        out_qty = b["sold_qty"] + b["consumed_qty"]
        closing_qty = _q3(available_qty - out_qty)
        negative = closing_qty < 0
        if negative:
            negative_items += 1
        closing_value = _q2(max(closing_qty, Decimal("0")) * avg_cost)
        total_closing_value += closing_value
        rows.append({
            "item_id": item_id,
            "code": it.get("code"),
            "name": it.get("name"),
            "uqc": it.get("uqc"),
            "opening_qty": str(opening_qty),
            "purchased_qty": str(_q3(b["purchased_qty"])),
            "produced_qty": str(_q3(b["produced_qty"])),
            "sold_qty": str(_q3(b["sold_qty"])),
            "consumed_qty": str(_q3(b["consumed_qty"])),
            "closing_qty": str(closing_qty),
            "avg_cost": str(avg_cost),
            "closing_value": str(closing_value),
            "negative_stock": negative,
        })
    rows.sort(key=lambda r: str(r["code"]))

    return {
        "as_of": as_of.isoformat(),
        "rows": rows,
        "item_count": len(rows),
        "total_closing_value": str(_q2(total_closing_value)),
        "negative_stock_items": negative_items,
        "untracked_purchase_value": str(_q2(untracked_purchase_value)),
        "notes": [
            "Valuation is weighted-average cost of purchases + production (taxable value, GST excluded).",
            "Negative closing stock means more was sold/consumed than the books purchased or "
            "produced — fix the documents or the item's opening stock before posting.",
            "Purchase lines without an item tag are listed as 'untracked' — they stay pure "
            "expense and are not part of closing stock.",
            "Manufactured finished goods are added at work-order production cost; raw materials "
            "consumed by completed work orders reduce stock at weighted-average cost.",
        ],
    }


async def build_stock_register(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, as_of: date | None = None,
) -> dict:
    from app.db.mongo import get_collection
    from app.modules.business.service import PURCHASE_BILLS_COLLECTION, SALES_INVOICES_COLLECTION

    as_of = as_of or date.today()
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    items = await get_collection(ITEMS_COLLECTION).find(scope).to_list(length=2000)

    purchase_lines: list[dict] = []
    bills = await get_collection(PURCHASE_BILLS_COLLECTION).find({
        **scope, "status": "posted", "bill_date": {"$lte": as_of.isoformat()},
    }).to_list(length=20000)
    for bill in bills:
        for ln in bill.get("line_items") or []:
            purchase_lines.append({
                "item_id": ln.get("item_id"),
                "quantity": ln.get("quantity"),
                "taxable_amount": ln.get("taxable_amount"),
            })

    sales_lines: list[dict] = []
    invoices = await get_collection(SALES_INVOICES_COLLECTION).find({
        **scope, "status": "posted", "invoice_date": {"$lte": as_of.isoformat()},
    }).to_list(length=20000)
    for inv in invoices:
        for ln in inv.get("line_items") or []:
            sales_lines.append({"item_id": ln.get("item_id"), "quantity": ln.get("quantity")})

    # Manufacturing movements: completed work orders add finished goods (at
    # production cost) and consume raw materials. Periodic, so nothing is posted
    # to the ledger here — this only keeps closing-stock valuation correct.
    produced_lines: list[dict] = []
    consumed_lines: list[dict] = []
    work_orders = await get_collection("manufacturing_work_orders").find({
        **scope, "status": "completed",
    }).to_list(length=20000)
    for wo in work_orders:
        completed_at = wo.get("completed_at")
        # completed_at is a datetime; compare its date against as_of.
        if completed_at is not None and hasattr(completed_at, "date") and completed_at.date() > as_of:
            continue
        actual = wo.get("actual") or {}
        produced_lines.append({
            "item_id": wo.get("fg_item_id"),
            "quantity": wo.get("produced_qty"),
            "value": actual.get("actual_cost"),
        })
        for comp in actual.get("components") or []:
            consumed_lines.append({"item_id": comp.get("item_id"), "quantity": comp.get("qty")})

    return assemble_stock_register(
        as_of=as_of, items=[_response(i) for i in items],
        purchase_lines=purchase_lines, sales_lines=sales_lines,
        produced_lines=produced_lines, consumed_lines=consumed_lines,
    )


# --------------------------------------------------------------------------- #
# Closing-stock journal (periodic method).
# --------------------------------------------------------------------------- #

async def find_closing_stock_entries(
    session, *, tenant_id: str, app_key: str, accounting_entity_id: str,
) -> list[dict]:
    from sqlalchemy import select
    from app.accounting.models.entities import JournalEntry
    from app.accounting.service import _accounting_scope

    rows = (await session.execute(
        select(JournalEntry.id, JournalEntry.entry_date, JournalEntry.description).where(
            *_accounting_scope(JournalEntry, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            JournalEntry.source_document_type == "closing_stock",
        ).order_by(JournalEntry.id.desc())
    )).all()
    return [{"journal_entry_id": r.id,
             "entry_date": r.entry_date.isoformat() if hasattr(r.entry_date, "isoformat") else str(r.entry_date),
             "description": r.description} for r in rows]


async def post_closing_stock(
    session, *, tenant_id: str, app_key: str, accounting_entity_id: str,
    as_of: date, created_by: str, idempotency_key: str | None = None,
) -> dict:
    """Book the closing stock as of a date: Dr Inventory (13001) /
    Cr Cost of Goods Sold (51002) at the register's weighted-average value.
    Reverse the previous closing-stock entry before posting a fresh one —
    otherwise stock would double-count on the balance sheet."""
    from app.accounting.schemas import JournalLineIn, JournalPostRequest
    from app.accounting.service import (
        AccountingValidationError,
        initialize_default_chart_of_accounts,
        post_journal_entry,
    )
    from app.modules.business.opening_close import _account_lookups

    register = await build_stock_register(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )
    if register["negative_stock_items"]:
        raise AccountingValidationError(
            f"{register['negative_stock_items']} item(s) have negative closing stock — "
            "fix the documents or opening stock first"
        )
    value = Decimal(register["total_closing_value"])
    if value <= 0:
        raise AccountingValidationError(f"No closing stock value to post as of {as_of.isoformat()}")

    existing = await find_closing_stock_entries(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    if existing:
        first = existing[0]
        raise AccountingValidationError(
            f"A closing-stock entry already exists (entry #{first['journal_entry_id']} dated "
            f"{first['entry_date']}). Reverse it first, then post the new position."
        )

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id=accounting_entity_id, organization_type="BUSINESS",
        )
    accounts_by_code, _ = await _account_lookups(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    inventory = accounts_by_code.get(INVENTORY_ACCOUNT_CODE)
    cogs = accounts_by_code.get(COGS_ACCOUNT_CODE)
    if inventory is None or cogs is None:
        raise AccountingValidationError(
            f"Inventory accounts missing from the chart ({INVENTORY_ACCOUNT_CODE} / {COGS_ACCOUNT_CODE})"
        )

    journal_entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=as_of,
            description=f"Closing stock as of {as_of.isoformat()}",
            reference=f"CLSTK-{as_of.isoformat()}",
            source_module="business",
            source_document_type="closing_stock",
            source_document_id=f"closing-stock:{as_of.isoformat()}",
            lines=[
                JournalLineIn(account_id=inventory["account_id"], debit=value, credit=Decimal("0")),
                JournalLineIn(account_id=cogs["account_id"], debit=Decimal("0"), credit=value),
            ],
        ),
        idempotency_key=idempotency_key or f"closing-stock:{accounting_entity_id}:{as_of.isoformat()}",
    )
    return {
        "journal_entry_id": journal_entry.id,
        "created": created,
        "as_of": as_of.isoformat(),
        "closing_stock_value": str(value),
        "item_count": register["item_count"],
    }
