"""Accounting dimensions — cost centres and projects on transactions.

Dimensions are tags, not ledger structure: the immutable double-entry journal
stays untouched. A document (sales invoice / purchase bill / credit note /
debit note) may carry a cost-centre and/or a project, and reporting aggregates
the posted documents — income from invoices less credit notes, expense from
bills less debit notes — per dimension with an explicit "untagged" bucket, so
the report always reconciles to the document totals.

Current scope: document-level tagging on invoices, bills, credit notes, and
debit notes. Vouchers and per-line dimensions remain v2 — noted in the report.
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

    # Optional hierarchy (cost centres roll up: Assembly -> Factory -> Operations).
    # The parent must already exist in THIS tenant+entity scope and be the same
    # dimension type — a cross-tenant or cross-type parent is impossible.
    parent_code = str(payload.get("parent_code") or "").strip().upper() or None
    if parent_code:
        if parent_code == code:
            raise AccountingValidationError("A cost centre cannot be its own parent")
        parent = await col.find_one({**scope, "dimension_type": dim_type, "code": parent_code})
        if parent is None:
            raise AccountingValidationError(f"Parent {dim_type.replace('_', ' ')} '{parent_code}' does not exist")

    now = _now()
    doc = {
        **scope,
        "dimension_id": str(uuid4()),
        "dimension_type": dim_type,
        "code": code,
        "name": name,
        "parent_code": parent_code,
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


async def validate_ledger_cost_centre_ids(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, cost_centre_ids: set[str],
) -> None:
    """Tenant-isolation guard for cost-centre tags on POSTED ledger lines.

    Every cost_center_id attached to a journal line must resolve to an ACTIVE
    cost centre owned by the SAME tenant + app + accounting entity. This is the
    single chokepoint that makes cross-tenant (or cross-entity) cost-centre
    contamination impossible: a code that lives only in another tenant's books
    simply will not be found in this scope, and the posting is rejected before
    it touches the immutable ledger. Empty input is a no-op (untagged postings
    pay nothing and are unaffected).
    """
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    wanted = {cid for cid in cost_centre_ids if cid}
    if not wanted:
        return
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    rows = await get_collection(DIMENSIONS_COLLECTION).find(
        {**scope, "dimension_type": "cost_centre", "is_active": True,
         "dimension_id": {"$in": list(wanted)}},
        {"dimension_id": 1},
    ).to_list(length=len(wanted))
    found = {r["dimension_id"] for r in rows}
    missing = sorted(wanted - found)
    if missing:
        raise AccountingValidationError(
            "Unknown or inactive cost centre(s) for this entity: "
            + ", ".join(missing)
            + ". A cost centre from another tenant or entity cannot be used."
        )


def build_cost_centre_tree(dimensions: list[dict]) -> list[dict]:
    """Roll cost-centre masters into a parent/child forest (by code) for display.
    Pure assembly; isolation is the caller's responsibility (pass one scope's
    masters only)."""
    centres = [d for d in dimensions if d.get("dimension_type") == "cost_centre"]
    by_code = {c["code"]: {**c, "children": []} for c in centres}
    roots: list[dict] = []
    for node in by_code.values():
        parent = by_code.get(node.get("parent_code"))
        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)  # orphans (missing parent) surface at the top
    roots.sort(key=lambda n: n["code"])
    return roots


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
    credit_notes: list[dict] | None = None,
    debit_notes: list[dict] | None = None,
    voucher_impacts: list[dict] | None = None,
) -> dict:
    """Income/expense/net per dimension over a period, plus the untagged
    bucket. Income = posted sales invoices' taxable_total less credit notes;
    expense = posted purchase bills' taxable_total less debit notes (GST is not
    P&L). The rows always sum to the document totals, so nothing silently
    disappears."""
    field = "cost_centre_id" if dimension_type == "cost_centre" else "project_id"
    rows: dict[str | None, dict] = {}
    credit_notes = credit_notes or []
    debit_notes = debit_notes or []
    voucher_impacts = voucher_impacts or []

    def _bucket(dim_id: str | None) -> dict:
        return rows.setdefault(dim_id, {"income": Decimal("0.00"), "expense": Decimal("0.00")})

    def _apply_document(doc: dict, *, amount_key: str, side: str, sign: int) -> None:
        line_items = doc.get("line_items") if isinstance(doc.get("line_items"), list) else []
        if line_items:
            for line in line_items:
                dim_id = line.get(field) or doc.get(field) or None
                _bucket(dim_id)[side] += _q2(line.get("taxable_amount") or 0) * sign
            return
        _bucket(doc.get(field) or None)[side] += _q2(doc.get(amount_key) or 0) * sign

    for inv in invoices:
        _apply_document(inv, amount_key="taxable_total", side="income", sign=1)
    for note in credit_notes:
        _apply_document(note, amount_key="taxable_total", side="income", sign=-1)
    for bill in bills:
        _apply_document(bill, amount_key="taxable_total", side="expense", sign=1)
    for note in debit_notes:
        _apply_document(note, amount_key="taxable_total", side="expense", sign=-1)
    for impact in voucher_impacts:
        bucket = _bucket(impact.get(field) or None)
        bucket["income"] += _q2(impact.get("income") or 0)
        bucket["expense"] += _q2(impact.get("expense") or 0)

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
        "document_counts": {
            "invoices": len(invoices),
            "bills": len(bills),
            "credit_notes": len(credit_notes),
            "debit_notes": len(debit_notes),
            "vouchers": len(voucher_impacts),
        },
        "notes": [
            "Income = posted sales invoices' taxable value; expense = posted purchase "
            "bills' taxable value (GST is excluded — it is not P&L). Credit notes "
            "reduce income, debit notes reduce expense, and vouchers count only "
            "when their debit or credit account is income or expense.",
            "The 'untagged' bucket holds documents without this dimension, so the "
            "report always ties to the period's document totals.",
            "Per-line dimensions are not yet tagged; voucher dimensions are header-level.",
        ],
    }


def assemble_branch_consolidated_report(*, branches: list[dict], cost_centre_report: dict) -> dict:
    """Roll a cost-centre P&L report up to configured branches.

    Branches map to cost centres by `cost_centre_code`; unmatched cost centres
    and the dimension report's own untagged bucket remain visible as
    `unassigned`, so branch reporting never hides unallocated P&L.
    """
    active_branches = [b for b in branches if b.get("active", True)]
    report_rows = cost_centre_report.get("rows") or []
    rows_by_code = {str(row.get("code") or "").upper(): row for row in report_rows}
    consumed_codes: set[str] = set()
    branch_rows: list[dict] = []

    for branch in active_branches:
        cc_code = str(branch.get("cost_centre_code") or branch.get("branch_code") or "").strip().upper()
        source = rows_by_code.get(cc_code)
        income = _q2((source or {}).get("income") or 0)
        expense = _q2((source or {}).get("expense") or 0)
        if source:
            consumed_codes.add(cc_code)
        branch_rows.append({
            "branch_code": str(branch.get("branch_code") or "").strip().upper(),
            "branch_name": branch.get("branch_name") or branch.get("branch_code") or "(unnamed branch)",
            "gstin": branch.get("gstin"),
            "cost_centre_code": cc_code or None,
            "cost_centre_name": (source or {}).get("name"),
            "income": str(_q2(income)),
            "expense": str(_q2(expense)),
            "net": str(_q2(income - expense)),
        })

    unassigned_income = _q2((cost_centre_report.get("untagged") or {}).get("income") or 0)
    unassigned_expense = _q2((cost_centre_report.get("untagged") or {}).get("expense") or 0)
    unmatched_cost_centres: list[dict] = []
    for row in report_rows:
        code = str(row.get("code") or "").upper()
        if code in consumed_codes:
            continue
        income = _q2(row.get("income") or 0)
        expense = _q2(row.get("expense") or 0)
        unassigned_income += income
        unassigned_expense += expense
        unmatched_cost_centres.append({
            "code": row.get("code"),
            "name": row.get("name"),
            "income": str(_q2(income)),
            "expense": str(_q2(expense)),
            "net": str(_q2(income - expense)),
        })

    totals = cost_centre_report.get("totals") or {}
    return {
        "report_type": "branch_consolidated",
        "from_date": cost_centre_report.get("from_date"),
        "to_date": cost_centre_report.get("to_date"),
        "rows": branch_rows,
        "unassigned": {
            "income": str(_q2(unassigned_income)),
            "expense": str(_q2(unassigned_expense)),
            "net": str(_q2(unassigned_income - unassigned_expense)),
            "unmatched_cost_centres": unmatched_cost_centres,
        },
        "totals": {
            "income": str(_q2(totals.get("income") or 0)),
            "expense": str(_q2(totals.get("expense") or 0)),
            "net": str(_q2(totals.get("net") or 0)),
        },
        "document_counts": cost_centre_report.get("document_counts") or {},
        "notes": [
            "Branch consolidation maps each active branch to the cost centre code configured in business admin settings.",
            "Unassigned includes untagged P&L and cost centres that are not mapped to an active branch, so totals still reconcile.",
        ],
    }


async def _voucher_impacts_from_account_types(
    *,
    session,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    vouchers: list[dict],
) -> list[dict]:
    if not vouchers or session is None:
        return []

    from sqlalchemy import select

    from app.accounting.models.entities import Account

    account_ids = {
        int(v.get("debit_account_id"))
        for v in vouchers
        if v.get("debit_account_id") is not None
    } | {
        int(v.get("credit_account_id"))
        for v in vouchers
        if v.get("credit_account_id") is not None
    }
    if not account_ids:
        return []

    result = await session.execute(
        select(Account.id, Account.type).where(
            Account.app_key == app_key,
            Account.tenant_id == tenant_id,
            Account.accounting_entity_id == accounting_entity_id,
            Account.id.in_(account_ids),
        )
    )
    account_types = {int(row[0]): str(row[1]) for row in result.all()}
    impacts: list[dict] = []
    income_types = {"income", "revenue"}

    for voucher in vouchers:
        amount = _q2(voucher.get("amount") or 0)
        debit_type = account_types.get(int(voucher.get("debit_account_id") or 0))
        credit_type = account_types.get(int(voucher.get("credit_account_id") or 0))
        income = Decimal("0.00")
        expense = Decimal("0.00")
        if debit_type == "expense":
            expense += amount
        elif debit_type in income_types:
            income -= amount
        if credit_type == "expense":
            expense -= amount
        elif credit_type in income_types:
            income += amount
        if income or expense:
            impacts.append({
                "cost_centre_id": voucher.get("cost_centre_id"),
                "project_id": voucher.get("project_id"),
                "income": str(_q2(income)),
                "expense": str(_q2(expense)),
            })
    return impacts


def dimension_report_export_spec(report: dict) -> dict:
    label = "Cost centre" if report.get("dimension_type") == "cost_centre" else "Project"
    rows = [
        {
            "dimension": f"{row.get('code', '')} - {row.get('name', '')}",
            "income": row.get("income", "0.00"),
            "expense": row.get("expense", "0.00"),
            "net": row.get("net", "0.00"),
        }
        for row in report.get("rows", [])
    ]
    untagged = report.get("untagged") or {}
    rows.append({
        "dimension": "Untagged",
        "income": untagged.get("income", "0.00"),
        "expense": untagged.get("expense", "0.00"),
        "net": untagged.get("net", "0.00"),
    })
    return {
        "title": f"Income / expense by {label.lower()}",
        "columns": [
            {"key": "dimension", "label": label},
            {"key": "income", "label": "Income", "type": "amount"},
            {"key": "expense", "label": "Expense", "type": "amount"},
            {"key": "net", "label": "Net", "type": "amount"},
        ],
        "rows": rows,
        "footer": {"dimension": "Total", **(report.get("totals") or {})},
        "meta": [
            ("From", report.get("from_date")),
            ("To", report.get("to_date")),
            ("Document counts", ", ".join(
                f"{key}: {value}" for key, value in (report.get("document_counts") or {}).items()
            )),
        ],
        "filename_base": f"dimension_{report.get('dimension_type')}_{report.get('to_date')}",
    }


async def build_dimension_report(
    *, tenant_id: str, app_key: str, accounting_entity_id: str,
    dimension_type: str, from_date: date | None = None, to_date: date | None = None,
    session=None,
) -> dict:
    from app.accounting.service import AccountingValidationError, _financial_year_start
    from app.db.mongo import get_collection
    from app.modules.business.service import (
        CREDIT_NOTES_COLLECTION,
        DEBIT_NOTES_COLLECTION,
        PURCHASE_BILLS_COLLECTION,
        SALES_INVOICES_COLLECTION,
        VOUCHERS_COLLECTION,
    )

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
    credit_notes = await get_collection(CREDIT_NOTES_COLLECTION).find({
        **scope, "status": "posted",
        "note_date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
    }).to_list(length=20000)
    debit_notes = await get_collection(DEBIT_NOTES_COLLECTION).find({
        **scope, "status": "posted",
        "note_date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
    }).to_list(length=20000)
    vouchers = await get_collection(VOUCHERS_COLLECTION).find({
        **scope, "status": "posted",
        "entry_date": {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()},
    }).to_list(length=20000)
    voucher_impacts = await _voucher_impacts_from_account_types(
        session=session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        vouchers=vouchers,
    )

    return assemble_dimension_report(
        dimension_type=dimension_type, from_date=from_date, to_date=to_date,
        dimensions=[_response(d) for d in dims], invoices=invoices, bills=bills,
        credit_notes=credit_notes, debit_notes=debit_notes,
        voucher_impacts=voucher_impacts,
    )


async def build_branch_consolidated_report(
    *, tenant_id: str, app_key: str, accounting_entity_id: str,
    from_date: date | None = None, to_date: date | None = None,
    session=None,
) -> dict:
    from app.db.mongo import get_collection
    from app.modules.business.service import ADMIN_SETTINGS_COLLECTION

    cost_centre_report = await build_dimension_report(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        dimension_type="cost_centre",
        from_date=from_date,
        to_date=to_date,
        session=session,
    )
    settings = await get_collection(ADMIN_SETTINGS_COLLECTION).find_one(
        _scope(tenant_id, app_key, accounting_entity_id)
    )
    return assemble_branch_consolidated_report(
        branches=list((settings or {}).get("branches") or []),
        cost_centre_report=cost_centre_report,
    )
