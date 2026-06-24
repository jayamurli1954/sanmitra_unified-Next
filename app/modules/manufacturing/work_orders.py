"""Work Orders (Phase 2b) — discrete production runs against a BOM.

A work order plans the production of a finished good from a BOM. On completion it
records ACTUAL material consumption and overhead and computes the variance against
the BOM standard (cost-centre tagged) for management reporting.

IMPORTANT — financial model: our inventory is PERIODIC (stock is derived and
recognised via the period-end closing-stock journal). To avoid double-counting,
work orders do NOT post per-WO WIP/Finished-Goods ledger entries. Their value is
(a) production tracking, (b) standard-vs-actual variance analysis, and (c) feeding
raw-material consumption / finished-goods output into the stock register (2c) so
closing-stock valuation stays correct. Perpetual per-WO postings are a v2 that
would require switching inventory to perpetual.

Lifecycle: draft -> released -> in_progress -> completed  (+ cancelled).
All Decimal math; scoped by tenant + app + entity; BOM and cost centre validated
against this entity's own masters.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

WORK_ORDERS_COLLECTION = "manufacturing_work_orders"
WO_COUNTERS_COLLECTION = "manufacturing_wo_counters"

STATUSES = ("draft", "released", "in_progress", "completed", "cancelled")
# Forward-only operational transitions; any open state may be cancelled.
_ALLOWED_TRANSITIONS = {
    "draft": {"released", "cancelled"},
    "released": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

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
    for key in ("created_at", "updated_at", "completed_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


# --------------------------------------------------------------------------- #
# Pure costing.
# --------------------------------------------------------------------------- #

def scale_standard_cost(*, bom_standard: dict, bom_output_qty, planned_qty) -> dict:
    """Scale a BOM's per-output standard cost to the work order's planned qty."""
    bom_output_qty = _q3(bom_output_qty)
    planned_qty = _q3(planned_qty)
    if bom_output_qty <= 0 or planned_qty <= 0:
        raise ValueError("output_qty and planned_qty must be greater than zero")
    factor = planned_qty / bom_output_qty
    material = _q2(Decimal(bom_standard["material_cost"]) * factor)
    overhead = _q2(Decimal(bom_standard["overhead_cost"]) * factor)
    return {
        "material_cost": str(material),
        "overhead_cost": str(overhead),
        "total_cost": str(_q2(material + overhead)),
        "planned_qty": str(planned_qty),
    }


def compute_variance(*, standard: dict, actual_material, actual_overhead) -> dict:
    """Actual-vs-standard variance. Positive variance = overspend (unfavourable)."""
    std_total = _q2(standard["total_cost"])
    actual_material = _q2(actual_material)
    actual_overhead = _q2(actual_overhead)
    actual_total = _q2(actual_material + actual_overhead)
    variance = _q2(actual_total - std_total)
    return {
        "standard_cost": str(std_total),
        "actual_material": str(actual_material),
        "actual_overhead": str(actual_overhead),
        "actual_cost": str(actual_total),
        "variance": str(variance),
        "material_variance": str(_q2(actual_material - Decimal(standard["material_cost"]))),
        "overhead_variance": str(_q2(actual_overhead - Decimal(standard["overhead_cost"]))),
        "favourable": variance < 0,
    }


# --------------------------------------------------------------------------- #
# CRUD + lifecycle.
# --------------------------------------------------------------------------- #

async def _next_wo_number(*, scope: dict) -> str:
    from app.db.mongo import get_collection

    counter = await get_collection(WO_COUNTERS_COLLECTION).find_one_and_update(
        {**scope, "_counter": "work_order"},
        {"$inc": {"seq": 1}},
        upsert=True, return_document=True,
    )
    seq = int((counter or {}).get("seq") or 1)
    return f"WO-{seq:04d}"


async def create_work_order(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, payload: dict, created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.business.dimensions import validate_ledger_cost_centre_ids
    from app.modules.manufacturing.bom import get_bom

    scope = _scope(tenant_id, app_key, accounting_entity_id)

    bom_id = str(payload.get("bom_id") or "").strip()
    if not bom_id:
        raise AccountingValidationError("bom_id is required")
    bom = await get_bom(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, bom_id=bom_id,
    )
    if not bom.get("is_active"):
        raise AccountingValidationError("Cannot create a work order against an inactive BOM")

    planned_qty = _q3(payload.get("planned_qty") or 0)
    if planned_qty <= 0:
        raise AccountingValidationError("planned_qty must be greater than zero")

    # Production cost centre carries the variance for cost-centre reporting.
    cost_centre_id = str(payload.get("cost_centre_id") or "").strip() or None
    if cost_centre_id:
        await validate_ledger_cost_centre_ids(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            cost_centre_ids={cost_centre_id},
        )

    standard = scale_standard_cost(
        bom_standard=bom["standard_cost"], bom_output_qty=bom["output_qty"], planned_qty=planned_qty,
    )
    now = _now()
    doc = {
        **scope,
        "wo_id": str(uuid4()),
        "wo_number": await _next_wo_number(scope=scope),
        "bom_id": bom_id,
        "bom_code": bom.get("code"),
        "fg_item_id": bom["fg_item_id"],
        "fg_item_code": bom.get("fg_item_code"),
        "fg_item_name": bom.get("fg_item_name"),
        "planned_qty": str(planned_qty),
        "cost_centre_id": cost_centre_id,
        "status": "draft",
        "standard_cost": standard,
        "produced_qty": None,
        "actual": None,
        "variance": None,
        "completed_at": None,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(WORK_ORDERS_COLLECTION).insert_one(doc)
    return _response(doc)


async def list_work_orders(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, status: str | None = None,
) -> dict:
    from app.db.mongo import get_collection

    filters = _scope(tenant_id, app_key, accounting_entity_id)
    if status:
        filters["status"] = status
    rows = await get_collection(WORK_ORDERS_COLLECTION).find(filters).sort("wo_number", -1).to_list(length=2000)
    items = [_response(r) for r in rows]
    return {"items": items, "count": len(items)}


async def get_work_order(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, wo_id: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await get_collection(WORK_ORDERS_COLLECTION).find_one({**scope, "wo_id": wo_id})
    if row is None:
        raise AccountingNotFoundError("Work order not found")
    return _response(row)


async def update_status(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, wo_id: str, status: str, updated_by: str,
) -> dict:
    """Move a work order along the operational lifecycle (not completion — use
    complete_work_order, which needs actuals)."""
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError
    from app.db.mongo import get_collection

    status = str(status or "").strip().lower()
    if status not in STATUSES:
        raise AccountingValidationError(f"status must be one of {', '.join(STATUSES)}")
    if status == "completed":
        raise AccountingValidationError("Use the complete endpoint to finish a work order")

    col = get_collection(WORK_ORDERS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "wo_id": wo_id})
    if row is None:
        raise AccountingNotFoundError("Work order not found")
    current = str(row.get("status") or "draft")
    if status != current and status not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise AccountingValidationError(f"Cannot move work order from {current} to {status}")

    await col.update_one(
        {**scope, "wo_id": wo_id},
        {"$set": {"status": status, "updated_by": updated_by, "updated_at": _now()}},
    )
    row["status"] = status
    return _response(row)


async def complete_work_order(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, wo_id: str, payload: dict, updated_by: str,
) -> dict:
    """Finish a work order: record actual material consumption + overhead and the
    produced quantity, then compute the variance against standard. Records only —
    no ledger posting (periodic inventory; recognition flows via closing stock)."""
    from app.accounting.service import AccountingNotFoundError, AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.manufacturing.bom import _validate_items

    col = get_collection(WORK_ORDERS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "wo_id": wo_id})
    if row is None:
        raise AccountingNotFoundError("Work order not found")
    if row.get("status") not in ("released", "in_progress"):
        raise AccountingValidationError("Only a released or in-progress work order can be completed")

    produced_qty = _q3(payload.get("produced_qty") or 0)
    if produced_qty <= 0:
        raise AccountingValidationError("produced_qty must be greater than zero")

    raw_actuals = payload.get("actual_components") or []
    if not raw_actuals:
        raise AccountingValidationError("Actual material consumption is required to complete a work order")
    actual_components = []
    actual_material = Decimal("0.00")
    item_ids: set[str] = set()
    for c in raw_actuals:
        item_id = str(c.get("item_id") or "").strip()
        if not item_id:
            raise AccountingValidationError("Each actual component needs an item_id")
        qty = _q3(c.get("qty"))
        rate = _q2(c.get("rate") or 0)
        if qty < 0 or rate < 0:
            raise AccountingValidationError("Actual qty and rate cannot be negative")
        item_ids.add(item_id)
        line_value = _q2(qty * rate)
        actual_material += line_value
        actual_components.append({"item_id": item_id, "qty": str(qty), "rate": str(rate),
                                  "value": str(line_value)})
    await _validate_items(scope=scope, item_ids=item_ids)

    actual_overhead = _q2(payload.get("actual_overhead") or 0)
    if actual_overhead < 0:
        raise AccountingValidationError("actual_overhead cannot be negative")

    variance = compute_variance(
        standard=row["standard_cost"], actual_material=actual_material, actual_overhead=actual_overhead,
    )
    now = _now()
    update = {
        "status": "completed",
        "produced_qty": str(produced_qty),
        "actual": {
            "components": actual_components,
            "actual_material": str(_q2(actual_material)),
            "actual_overhead": str(actual_overhead),
            "actual_cost": variance["actual_cost"],
        },
        "variance": variance,
        "completed_at": now,
        "updated_by": updated_by,
        "updated_at": now,
    }
    await col.update_one({**scope, "wo_id": wo_id}, {"$set": update})
    row.update(update)
    return _response(row)
