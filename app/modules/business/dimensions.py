"""Accounting dimensions — cost centres and projects on transactions.

Dimensions are tags, not ledger structure: the immutable double-entry journal
stays untouched. A document (sales invoice / purchase bill) may carry a
cost-centre and/or a project, and reporting aggregates the posted documents —
income from invoices, expense from bills — per dimension with an explicit
"untagged" bucket, so the report always reconciles to the document totals.

v1 scope: tagging on sales invoices and purchase bills (the dominant income/
expense sources here). Vouchers, credit/debit notes and per-line dimensions
are v2 — noted in the report.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

DIMENSIONS_COLLECTION = "business_dimensions"

DIMENSION_TYPES = ("cost_centre", "project")

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


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
# Masters.
# --------------------------------------------------------------------------- #

async def create_dimension(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, payload: dict, created_by: str,
) -> dict:
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    dim_type = str(payload.get("dimension_type") or "").strip()
    if dim_type not in DIMENSION_TYPES:
        raise AccountingValidationError("dimension_type must be 'cost_centre' or 'project'")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise AccountingValidationError("name is required")
    code = str(payload.get("code") or "").strip().upper() or name[:12].upper().replace(" ", "-")

    col = get_collection(DIMENSIONS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    if await col.find_one({**scope, "dimension_type": dim_type, "code": code}):
        raise AccountingValidationError(f"A {dim_type.replace('_', ' ')} with code '{code}' already exists")

    now = _now()
    doc = {
        **scope,
        "dimension_id": str(uuid4()),
        "dimension_type": dim_type,
        "code": code,
        "name": name,
        "is_active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(doc)
    return _response(doc)


async def list_dimensions(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, include_inactive: bool = False,
) -> dict:
    from app.db.mongo import get_collection

    filters = _scope(tenant_id, app_key, accounting_entity_id)
    if not include_inactive:
        filters["is_active"] = True
    rows = await get_collection(DIMENSIONS_COLLECTION).find(filters).sort(
        [("dimension_type", 1), ("code", 1)]
    ).to_list(length=1000)
    items = [_response(r) for r in rows]
    return {
        "items": items,
        "cost_centres": [i for i in items if i["dimension_type"] == "cost_centre"],
        "projects": [i for i in items if i["dimension_type"] == "project"],
        "count": len(items),
    }


async def deactivate_dimension(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, dimension_id: str, updated_by: str,
) -> dict:
    """Soft-deactivate (history keeps the tag; new documents stop offering it)."""
    from app.accounting.service import AccountingNotFoundError
    from app.db.mongo import get_collection

    col = get_collection(DIMENSIONS_COLLECTION)
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    row = await col.find_one({**scope, "dimension_id": dimension_id})
    if row is None:
        raise AccountingNotFoundError("Dimension not found")
    await col.update_one(
        {**scope, "dimension_id": dimension_id},
        {"$set": {"is_active": False, "updated_by": updated_by, "updated_at": _now()}},
    )
    row["is_active"] = False
    return _response(row)


async def validate_dimension_refs(
    *, tenant_id: str, app_key: str, accounting_entity_id: str,
    cost_centre_id: str | None, project_id: str | None,
) -> None:
    """Raise when a document references a dimension that doesn't exist."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    for dim_id, dim_type in ((cost_centre_id, "cost_centre"), (project_id, "project")):
        if not dim_id:
            continue  # untagged documents never touch the dimensions collection
        row = await get_collection(DIMENSIONS_COLLECTION).find_one(
            {**scope, "dimension_id": dim_id, "dimension_type": dim_type}
        )
        if row is None:
            raise AccountingValidationError(f"Unknown {dim_type.replace('_', ' ')} '{dim_id}'")


# --------------------------------------------------------------------------- #
# Report — pure assembly.
# --------------------------------------------------------------------------- #

def assemble_dimension_report(
    *,
    dimension_type: str,
    from_date: date,
    to_date: date,
    dimensions: list[dict],
    invoices: list[dict],
    bills: list[dict],
) -> dict:
    """Income/expense/net per dimension over a period, plus the untagged
    bucket. Income = posted sales invoices' taxable_total; expense = posted
    purchase bills' taxable_total (GST is not P&L). The rows always sum to the
    document totals, so nothing silently disappears."""
    field = "cost_centre_id" if dimension_type == "cost_centre" else "project_id"
    rows: dict[str | None, dict] = {}

    def _bucket(dim_id: str | None) -> dict:
        return rows.setdefault(dim_id, {"income": Decimal("0.00"), "expense": Decimal("0.00")})

    for inv in invoices:
        _bucket(inv.get(field) or None)["income"] += _q2(inv.get("taxable_total") or 0)
    for bill in bills:
        _bucket(bill.get(field) or None)["expense"] += _q2(bill.get("taxable_total") or 0)

    names = {d["dimension_id"]: d for d in dimensions if d.get("dimension_type") == dimension_type}
    out_rows: list[dict] = []
    for dim_id, sums in rows.items():
        if dim_id is None:
            continue
        meta = names.get(dim_id, {})
        out_rows.append({
            "dimension_id": dim_id,
            "code": meta.get("code") or dim_id,
            "name": meta.get("name") or "(deleted dimension)",
            "income": str(_q2(sums["income"])),
            "expense": str(_q2(sums["expense"])),
            "net": str(_q2(sums["income"] - sums["expense"])),
        })
    out_rows.sort(key=lambda r: -Decimal(r["net"]))

    untagged = rows.get(None, {"income": Decimal("0.00"), "expense": Decimal("0.00")})
    total_income = sum((v["income"] for v in rows.values()), Decimal("0.00"))
    total_expense = sum((v["expense"] for v in rows.values()), Decimal("0.00"))

    return {
        "dimension_type": dimension_type,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "rows": out_rows,
        "untagged": {
            "income": str(_q2(untagged["income"])),
            "expense": str(_q2(untagged["expense"])),
            "net": str(_q2(untagged["income"] - untagged["expense"])),
        },
        "totals": {
            "income": str(_q2(total_income)),
            "expense": str(_q2(total_expense)),
            "net": str(_q2(total_income - total_expense)),
        },
        "document_counts": {"invoices": len(invoices), "bills": len(bills)},
        "notes": [
            "Income = posted sales invoices' taxable value; expense = posted purchase "
            "bills' taxable value (GST is excluded — it is not P&L).",
            "The 'untagged' bucket holds documents without this dimension, so the "
            "report always ties to the period's document totals.",
            "Vouchers, credit/debit notes and per-line dimensions are not yet tagged (v2).",
        ],
    }


async def build_dimension_report(
    *, tenant_id: str, app_key: str, accounting_entity_id: str,
    dimension_type: str, from_date: date | None = None, to_date: date | None = None,
) -> dict:
    from app.accounting.service import AccountingValidationError, _financial_year_start
    from app.db.mongo import get_collection
    from app.modules.business.service import PURCHASE_BILLS_COLLECTION, SALES_INVOICES_COLLECTION

    if dimension_type not in DIMENSION_TYPES:
        raise AccountingValidationError("dimension_type must be 'cost_centre' or 'project'")
    to_date = to_date or date.today()
    from_date = from_date or _financial_year_start(to_date)

    scope = _scope(tenant_id, app_key, accounting_entity_id)
    dims = await get_collection(DIMENSIONS_COLLECTION).find(scope).to_list(length=1000)
    invoices = await get_collection(SALES_INVOICES_COLLECTION).find({
        **scope, "status": "posted",
        "invoice_date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
    }).to_list(length=20000)
    bills = await get_collection(PURCHASE_BILLS_COLLECTION).find({
        **scope, "status": "posted",
        "bill_date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
    }).to_list(length=20000)

    return assemble_dimension_report(
        dimension_type=dimension_type, from_date=from_date, to_date=to_date,
        dimensions=[_response(d) for d in dims], invoices=invoices, bills=bills,
    )
