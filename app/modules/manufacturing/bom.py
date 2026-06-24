"""Bill of Materials (BOM) — the recipe for a manufactured finished good.

A BOM names a finished-good item (from the existing inventory item master), the
component items it consumes (each with a standard rate and a scrap allowance), and
the operations performed (each on a cost centre, with an overhead rate). From these
it computes a deterministic STANDARD cost — the theoretical cost to produce the
output quantity — which Work Orders (2b) compare against actual cost to book a
variance.

Discrete manufacturing, single-level explosion in v1 (components are raw/bought
items, not sub-assemblies). All Decimal math; everything scoped by tenant + app +
entity; component items and operation cost centres are validated against this
entity's own masters, so a BOM can never reference another tenant's data.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

BOMS_COLLECTION = "manufacturing_boms"

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


# --------------------------------------------------------------------------- #
# Standard-cost roll-up — pure.
# --------------------------------------------------------------------------- #

def compute_bom_standard_cost(*, components: list[dict], operations: list[dict], output_qty) -> dict:
    """Deterministic standard cost for ONE BOM.

    material = Σ  qty × (1 + scrap%/100) × rate     (per component)
    overhead = Σ  runtime_hrs × overhead_rate       (per operation)
    total    = material + overhead   (to produce ``output_qty`` of the finished good)
    per_unit = total / output_qty
    """
    output_qty = _q3(output_qty)
    if output_qty <= 0:
        raise ValueError("output_qty must be greater than zero")

    material = Decimal("0.00")
    for c in components:
        qty = _q3(c.get("qty"))
        scrap = _q2(c.get("scrap_pct") or 0)
        rate = _q2(c.get("rate") or 0)
        effective_qty = qty * (Decimal("1") + scrap / Decimal("100"))
        material += _q2(effective_qty * rate)

    overhead = Decimal("0.00")
    for op in operations:
        runtime = _q3(op.get("runtime_hrs") or 0)
        op_rate = _q2(op.get("overhead_rate") or 0)
        overhead += _q2(runtime * op_rate)

    total = _q2(material + overhead)
    per_unit = _q2(total / output_qty)
    return {
        "material_cost": str(_q2(material)),
        "overhead_cost": str(_q2(overhead)),
        "total_cost": str(total),
        "output_qty": str(output_qty),
        "per_unit_cost": str(per_unit),
    }


# --------------------------------------------------------------------------- #
# Validation helpers.
# --------------------------------------------------------------------------- #

async def _validate_items(*, scope: dict, item_ids: set[str]) -> dict[str, dict]:
    """Every item id must be an ACTIVE item in this scope. Returns {item_id: doc}."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.business.inventory import ITEMS_COLLECTION

    wanted = {i for i in item_ids if i}
    if not wanted:
        return {}
    rows = await get_collection(ITEMS_COLLECTION).find(
        {**scope, "item_id": {"$in": list(wanted)}, "is_active": True}
    ).to_list(length=len(wanted))
    found = {str(r["item_id"]): r for r in rows}
    missing = sorted(wanted - set(found))
    if missing:
        raise AccountingValidationError(f"Unknown or inactive inventory item(s): {', '.join(missing)}")
    return found


# --------------------------------------------------------------------------- #
# CRUD.
# --------------------------------------------------------------------------- #

async def create_bom(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, payload: dict, created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection
    from app.modules.business.dimensions import validate_ledger_cost_centre_ids

    scope = _scope(tenant_id, app_key, accounting_entity_id)

    fg_item_id = str(payload.get("fg_item_id") or "").strip()
    if not fg_item_id:
        raise AccountingValidationError("fg_item_id (finished good) is required")
    output_qty = _q3(payload.get("output_qty") or 1)
    if output_qty <= 0:
        raise AccountingValidationError("output_qty must be greater than zero")

    raw_components = payload.get("components") or []
    if not raw_components:
        raise AccountingValidationError("A BOM needs at least one component")
    components = []
    component_item_ids: set[str] = set()
    for c in raw_components:
        item_id = str(c.get("item_id") or "").strip()
        if not item_id:
            raise AccountingValidationError("Each component needs an item_id")
        qty = _q3(c.get("qty"))
        if qty <= 0:
            raise AccountingValidationError("Component qty must be greater than zero")
        scrap = _q2(c.get("scrap_pct") or 0)
        rate = _q2(c.get("rate") or 0)
        if scrap < 0 or rate < 0:
            raise AccountingValidationError("Component scrap_pct and rate cannot be negative")
        component_item_ids.add(item_id)
        components.append({"item_id": item_id, "qty": str(qty), "scrap_pct": str(scrap), "rate": str(rate)})

    raw_ops = payload.get("operations") or []
    operations = []
    op_cost_centres: set[str] = set()
    for i, op in enumerate(raw_ops, start=1):
        cc_id = str(op.get("cost_centre_id") or "").strip() or None
        if cc_id:
            op_cost_centres.add(cc_id)
        runtime = _q3(op.get("runtime_hrs") or 0)
        op_rate = _q2(op.get("overhead_rate") or 0)
        if runtime < 0 or op_rate < 0:
            raise AccountingValidationError("Operation runtime_hrs and overhead_rate cannot be negative")
        operations.append({
            "seq": int(op.get("seq") or i),
            "work_centre": str(op.get("work_centre") or "").strip() or None,
            "cost_centre_id": cc_id,
            "runtime_hrs": str(runtime),
            "overhead_rate": str(op_rate),
        })

    # Isolation: finished good + components must be this entity's items; operation
    # cost centres must be this entity's active cost centres.
    items = await _validate_items(scope=scope, item_ids={fg_item_id} | component_item_ids)
    if op_cost_centres:
        await validate_ledger_cost_centre_ids(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
            cost_centre_ids=op_cost_centres,
        )

    code = str(payload.get("code") or "").strip().upper()
    if not code:
        fg_code = items[fg_item_id].get("code") or "BOM"
        code = f"BOM-{fg_code}"
    col = get_collection(BOMS_COLLECTION)
    if await col.find_one({**scope, "code": code}):
        raise AccountingValidationError(f"A BOM with code '{code}' already exists")

    standard = compute_bom_standard_cost(
        components=components, operations=operations, output_qty=output_qty,
    )
    now = _now()
    doc = {
        **scope,
        "bom_id": str(uuid4()),
        "code": code,
        "fg_item_id": fg_item_id,
        "fg_item_code": items[fg_item_id].get("code"),
        "fg_item_name": items[fg_item_id].get("name"),
        "output_qty": str(output_qty),
        "revision": str(payload.get("revision") or "1").strip() or "1",
        "components": components,
        "operations": operations,
        "standard_cost": standard,
        "is_active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(doc)
    return _response(doc)


async def list_boms(
    *, tenant_id: str, app_key: str, accounting_entity_id: str,
    fg_item_id: str | None = None, include_inactive: bool = False,
) -> dict:
    from app.db.mongo import get_collection

    filters = _scope(tenant_id, app_key, accounting_entity_id)
    if fg_item_id:
        filters["fg_item_id"] = fg_item_id
    if not include_inactive:
        filters["is_active"] = True
    rows = await get_collection(BOMS_COLLECTION).find(filters).sort("code", 1).to_list(length=2000)
    items = [_response(r) for r in rows]
    return {"items": items, "count": len(items)}


async def get_bom(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, bom_id: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await get_collection(BOMS_COLLECTION).find_one({**scope, "bom_id": bom_id})
    if row is None:
        raise AccountingNotFoundError("BOM not found")
    return _response(row)


async def deactivate_bom(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, bom_id: str, updated_by: str,
) -> dict:
    from app.accounting.service import AccountingNotFoundError
    from app.db.mongo import get_collection

    col = get_collection(BOMS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "bom_id": bom_id})
    if row is None:
        raise AccountingNotFoundError("BOM not found")
    await col.update_one(
        {**scope, "bom_id": bom_id},
        {"$set": {"is_active": False, "updated_by": updated_by, "updated_at": _now()}},
    )
    row["is_active"] = False
    return _response(row)
