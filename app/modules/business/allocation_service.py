"""Payment allocation (open-item AR/AP) + reconciliation to the ledger.

This is a thin *matching* layer on top of the immutable double-entry ledger. It
records WHICH receipts settle WHICH sales invoices (receivable side), and which
payment vouchers settle which purchase bills (payable side). It posts **no new
journal entries** — the cash/receivable legs already hit the ledger when the
receipt/voucher was recorded. Allocations are pure metadata in MongoDB.

Invariant (the reconciliation guard ties metadata back to the ledger):

    Σ(open-item outstanding) − Σ(unallocated payments)  ==  party-tagged ledger balance

Every allocation links one payment to one open item, so the allocated amount
cancels out of both sides, leaving (Σ invoice_total − Σ receipt amount), which is
exactly the party's receivable balance in the ledger. Manual journal entries to a
receivable/payable account with no source document have no Mongo open item; they
live in the ledger's NULL "Unallocated" bucket and are reported separately, so the
reconciliation difference (excluding that bucket) is always zero when consistent.

The core math is in module-level pure functions (unit-tested without any DB); the
async functions only do Mongo/Postgres I/O and delegate to them.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    get_party_outstanding,
    get_party_wise_balances,
)
from app.db.mongo import get_collection

PAYMENT_ALLOCATIONS_COLLECTION = "business_payment_allocations"
PARTIES_COLLECTION = "business_parties"
VOUCHERS_COLLECTION = "business_vouchers"
SALES_INVOICES_COLLECTION = "business_sales_invoices"
PURCHASE_BILLS_COLLECTION = "business_purchase_bills"

# Per side: (open-item collection, id field, number field, total field, date field,
#            party field, voucher_type that pays it down)
_SIDE = {
    "receivable": {
        "collection": SALES_INVOICES_COLLECTION,
        "id_field": "invoice_id",
        "number_field": "invoice_number",
        "total_field": "invoice_total",
        "date_field": "invoice_date",
        "party_field": "customer_party_id",
        "voucher_type": "receipt",
    },
    "payable": {
        "collection": PURCHASE_BILLS_COLLECTION,
        "id_field": "bill_id",
        "number_field": "bill_number",
        "total_field": "bill_total",
        "date_field": "bill_date",
        "party_field": "vendor_party_id",
        "voucher_type": "payment",
    },
}

_CENT = Decimal("0.01")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _d(value) -> Decimal:
    """Coerce strings/None/numbers to a 2dp Decimal."""
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(_CENT)


def _require_side(kind: str) -> dict:
    spec = _SIDE.get(kind)
    if spec is None:
        raise AccountingValidationError("kind must be 'receivable' or 'payable'")
    return spec


def _days_overdue(item_date: str | None, due_date: str | None, as_of: date) -> int:
    """Days past the due date (or the document date if no due date), >= 0."""
    ref = due_date or item_date
    if not ref:
        return 0
    try:
        ref_date = date.fromisoformat(ref[:10])
    except (ValueError, TypeError):
        return 0
    return max((as_of - ref_date).days, 0)


# --------------------------------------------------------------------------- #
# Pure functions — no I/O, fully unit-testable.
# --------------------------------------------------------------------------- #

def sum_allocated(allocations: list[dict]) -> Decimal:
    """Total of active allocated_amount across the given allocation docs."""
    total = Decimal("0.00")
    for a in allocations:
        if a.get("status", "active") == "active":
            total += _d(a.get("allocated_amount"))
    return total


def open_item_view(
    item: dict,
    allocs_for_item: list[dict],
    *,
    spec: dict,
    as_of: date,
) -> dict:
    """Shape one open item (invoice/bill) with its outstanding + age."""
    total = _d(item.get(spec["total_field"]))
    allocated = sum_allocated(allocs_for_item)
    outstanding = (total - allocated).quantize(_CENT)
    item_date = item.get(spec["date_field"])
    return {
        "open_item_id": item.get(spec["id_field"]),
        "open_item_number": item.get(spec["number_field"]),
        "party_id": item.get(spec["party_field"]),
        "item_date": item_date,
        "due_date": item.get("due_date"),
        "total": str(total),
        "allocated": str(allocated),
        "outstanding": str(outstanding),
        "days_overdue": _days_overdue(item_date, item.get("due_date"), as_of),
    }


def compute_open_items(
    items: list[dict],
    allocs_by_item: dict[str, list[dict]],
    *,
    spec: dict,
    as_of: date,
    include_settled: bool = False,
) -> list[dict]:
    """Open items with outstanding > 0 (oldest first), unless include_settled."""
    out: list[dict] = []
    for item in items:
        view = open_item_view(item, allocs_by_item.get(item.get(spec["id_field"]), []), spec=spec, as_of=as_of)
        if include_settled or _d(view["outstanding"]) > Decimal("0.00"):
            out.append(view)
    out.sort(key=lambda v: (v["item_date"] or "", v["open_item_number"] or ""))
    return out


def payment_view(payment: dict, allocs_for_payment: list[dict]) -> dict:
    """Shape one payment (receipt/payment voucher) with its unallocated balance."""
    amount = _d(payment.get("amount"))
    allocated = sum_allocated(allocs_for_payment)
    unallocated = (amount - allocated).quantize(_CENT)
    return {
        "payment_id": payment.get("voucher_id"),
        "payment_number": payment.get("voucher_number"),
        "party_id": payment.get("party_id"),
        "payment_date": payment.get("entry_date"),
        "amount": str(amount),
        "allocated": str(allocated),
        "unallocated": str(unallocated),
    }


def compute_unallocated_payments(
    payments: list[dict],
    allocs_by_payment: dict[str, list[dict]],
    *,
    include_settled: bool = False,
) -> list[dict]:
    out: list[dict] = []
    for p in payments:
        view = payment_view(p, allocs_by_payment.get(p.get("voucher_id"), []))
        if include_settled or _d(view["unallocated"]) > Decimal("0.00"):
            out.append(view)
    out.sort(key=lambda v: (v["payment_date"] or "", v["payment_number"] or ""))
    return out


def validate_allocation(
    *,
    payment_unallocated: Decimal,
    outstanding_by_item: dict[str, Decimal],
    requested: list[tuple[str, Decimal]],
) -> None:
    """Reject zero/negative amounts, over-allocating a payment, or over-paying an
    open item. Raises AccountingValidationError; returns None when valid."""
    if not requested:
        raise AccountingValidationError("At least one allocation line is required")
    total = Decimal("0.00")
    for item_id, amount in requested:
        if amount <= Decimal("0.00"):
            raise AccountingValidationError("Allocated amount must be greater than zero")
        if item_id not in outstanding_by_item:
            raise AccountingValidationError(f"Open item {item_id} not found or already settled")
        if amount > outstanding_by_item[item_id] + _CENT / 2:
            raise AccountingValidationError(
                f"Allocation {amount} exceeds outstanding {outstanding_by_item[item_id]} on item {item_id}"
            )
        total += amount
    if total > payment_unallocated + _CENT / 2:
        raise AccountingValidationError(
            f"Total allocation {total} exceeds the payment's unallocated balance {payment_unallocated}"
        )


def suggest_fifo(open_items: list[dict], available: Decimal) -> list[dict]:
    """Greedily apply `available` to open items oldest-first. open_items must be
    pre-sorted oldest-first (compute_open_items already does this)."""
    remaining = available.quantize(_CENT)
    suggestion: list[dict] = []
    for item in open_items:
        if remaining <= Decimal("0.00"):
            break
        outstanding = _d(item["outstanding"])
        take = min(outstanding, remaining)
        if take > Decimal("0.00"):
            suggestion.append({
                "open_item_id": item["open_item_id"],
                "open_item_number": item["open_item_number"],
                "allocated_amount": str(take),
            })
            remaining -= take
    return suggestion


def reconcile(
    *,
    open_items_outstanding: Decimal,
    unallocated_payments: Decimal,
    ledger_balance: Decimal,
) -> dict:
    """The core invariant. computed_net should equal the party-tagged ledger
    balance; difference surfaces any drift (or un-invoiced manual entries when
    run against a party that also has manual ledger postings)."""
    computed_net = (open_items_outstanding - unallocated_payments).quantize(_CENT)
    difference = (computed_net - ledger_balance).quantize(_CENT)
    return {
        "open_items_outstanding": str(open_items_outstanding.quantize(_CENT)),
        "unallocated_payments": str(unallocated_payments.quantize(_CENT)),
        "computed_net": str(computed_net),
        "ledger_balance": str(ledger_balance.quantize(_CENT)),
        "difference": str(difference),
        "balanced": abs(difference) < _CENT,
    }


# Standard AR/AP aging buckets, by days past due (0-30 includes not-yet-due).
AGING_BUCKETS = ["0-30", "31-60", "61-90", "90+"]


def aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 30:
        return "0-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


def aging_summary(open_items: list[dict]) -> dict:
    """Aggregate open-item outstanding into aging buckets, grouped by party.
    Each open_items entry must carry `outstanding`, `days_overdue`, `party_id`."""
    totals = {b: Decimal("0.00") for b in AGING_BUCKETS}
    grand = Decimal("0.00")
    by_party: dict = {}
    for it in open_items:
        amount = _d(it["outstanding"])
        bucket = aging_bucket(int(it.get("days_overdue") or 0))
        pid = it.get("party_id")
        row = by_party.setdefault(
            pid, {"party_id": pid, "buckets": {b: Decimal("0.00") for b in AGING_BUCKETS}, "total": Decimal("0.00")},
        )
        row["buckets"][bucket] += amount
        row["total"] += amount
        totals[bucket] += amount
        grand += amount
    rows = [
        {
            "party_id": r["party_id"],
            "buckets": {b: str(r["buckets"][b]) for b in AGING_BUCKETS},
            "total": str(r["total"]),
        }
        for r in by_party.values()
    ]
    rows.sort(key=lambda r: Decimal(r["total"]), reverse=True)
    return {
        "buckets_order": AGING_BUCKETS,
        "totals": {b: str(totals[b]) for b in AGING_BUCKETS},
        "grand_total": str(grand),
        "by_party": rows,
    }


def _group_by(docs: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for d in docs:
        grouped.setdefault(d.get(key), []).append(d)
    return grouped


# --------------------------------------------------------------------------- #
# Async I/O wrappers.
# --------------------------------------------------------------------------- #

def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


async def _fetch_allocations(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, side: str,
    party_id: str | None = None, status: str = "active",
) -> list[dict]:
    flt = {**_scope(tenant_id, app_key, accounting_entity_id), "side": side}
    if status:
        flt["status"] = status
    if party_id:
        flt["party_id"] = party_id
    return await get_collection(PAYMENT_ALLOCATIONS_COLLECTION).find(flt).to_list(length=5000)


async def _fetch_open_item_docs(
    *, spec: dict, tenant_id: str, app_key: str, accounting_entity_id: str, party_id: str | None,
) -> list[dict]:
    flt = {**_scope(tenant_id, app_key, accounting_entity_id), "status": "posted"}
    if party_id:
        flt[spec["party_field"]] = party_id
    return await get_collection(spec["collection"]).find(flt).to_list(length=5000)


async def _fetch_payment_docs(
    *, spec: dict, tenant_id: str, app_key: str, accounting_entity_id: str, party_id: str | None,
) -> list[dict]:
    flt = {**_scope(tenant_id, app_key, accounting_entity_id),
           "status": "posted", "voucher_type": spec["voucher_type"]}
    if party_id:
        flt["party_id"] = party_id
    return await get_collection(VOUCHERS_COLLECTION).find(flt).to_list(length=5000)


async def list_open_items(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, kind: str,
    party_id: str | None = None, as_of: date | None = None, include_settled: bool = False,
) -> dict:
    spec = _require_side(kind)
    as_of = as_of or date.today()
    items = await _fetch_open_item_docs(
        spec=spec, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, party_id=party_id,
    )
    allocs = await _fetch_allocations(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        side=kind, party_id=party_id,
    )
    views = compute_open_items(
        items, _group_by(allocs, "open_item_id"), spec=spec, as_of=as_of, include_settled=include_settled,
    )
    total_outstanding = sum((_d(v["outstanding"]) for v in views), Decimal("0.00"))
    return {
        "kind": kind, "as_of": as_of.isoformat(), "accounting_entity_id": accounting_entity_id,
        "items": views, "count": len(views), "total_outstanding": str(total_outstanding),
    }


async def list_unallocated_payments(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, kind: str,
    party_id: str | None = None, include_settled: bool = False,
) -> dict:
    spec = _require_side(kind)
    payments = await _fetch_payment_docs(
        spec=spec, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, party_id=party_id,
    )
    allocs = await _fetch_allocations(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        side=kind, party_id=party_id,
    )
    views = compute_unallocated_payments(
        payments, _group_by(allocs, "payment_id"), include_settled=include_settled,
    )
    total = sum((_d(v["unallocated"]) for v in views), Decimal("0.00"))
    return {
        "kind": kind, "accounting_entity_id": accounting_entity_id,
        "items": views, "count": len(views), "total_unallocated": str(total),
    }


async def _payment_with_balance(*, spec, tenant_id, app_key, accounting_entity_id, payment_id) -> tuple[dict, Decimal]:
    payment = await get_collection(VOUCHERS_COLLECTION).find_one({
        **_scope(tenant_id, app_key, accounting_entity_id),
        "voucher_id": payment_id, "voucher_type": spec["voucher_type"],
    })
    if payment is None:
        raise AccountingNotFoundError("Payment voucher not found")
    if payment.get("status") != "posted":
        raise AccountingValidationError("Payment voucher is not posted")
    allocs = await get_collection(PAYMENT_ALLOCATIONS_COLLECTION).find({
        **_scope(tenant_id, app_key, accounting_entity_id),
        "payment_id": payment_id, "status": "active",
    }).to_list(length=5000)
    unallocated = (_d(payment.get("amount")) - sum_allocated(allocs)).quantize(_CENT)
    return payment, unallocated


async def fifo_suggestion(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, kind: str, payment_id: str,
    as_of: date | None = None,
) -> dict:
    spec = _require_side(kind)
    payment, unallocated = await _payment_with_balance(
        spec=spec, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, payment_id=payment_id,
    )
    open_items = (await list_open_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=payment.get("party_id"), as_of=as_of,
    ))["items"]
    suggestion = suggest_fifo(open_items, unallocated)
    return {
        "payment_id": payment_id, "payment_number": payment.get("voucher_number"),
        "party_id": payment.get("party_id"), "unallocated": str(unallocated),
        "allocations": suggestion,
    }


async def allocate_payment(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, created_by: str,
    kind: str, payment_id: str, allocations: list[dict],
) -> dict:
    """Match a posted payment to one or more open items. Validates against the
    current live balances, then writes one allocation doc per line. No GL posting."""
    spec = _require_side(kind)
    payment, unallocated = await _payment_with_balance(
        spec=spec, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, payment_id=payment_id,
    )
    party_id = payment.get("party_id")

    # Current outstanding for the requested items (same party as the payment).
    open_items = (await list_open_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=party_id,
    ))["items"]
    outstanding_by_item = {v["open_item_id"]: _d(v["outstanding"]) for v in open_items}
    number_by_item = {v["open_item_id"]: v["open_item_number"] for v in open_items}

    requested = [(a["open_item_id"], _d(a["allocated_amount"])) for a in allocations]
    validate_allocation(
        payment_unallocated=unallocated, outstanding_by_item=outstanding_by_item, requested=requested,
    )

    now = _now()
    today = date.today().isoformat()
    docs = []
    for item_id, amount in requested:
        docs.append({
            "allocation_id": str(uuid4()),
            **_scope(tenant_id, app_key, accounting_entity_id),
            "side": kind,
            "party_id": party_id,
            "payment_id": payment_id,
            "payment_number": payment.get("voucher_number"),
            "open_item_id": item_id,
            "open_item_number": number_by_item.get(item_id),
            "allocated_amount": str(amount),
            "allocated_date": today,
            "status": "active",
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        })
    await get_collection(PAYMENT_ALLOCATIONS_COLLECTION).insert_many(docs)
    return {
        "payment_id": payment_id,
        "allocations": [{k: v for k, v in d.items() if k != "_id"} for d in docs],
        "count": len(docs),
    }


async def reverse_allocation(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, allocation_id: str, reversed_by: str,
) -> dict:
    coll = get_collection(PAYMENT_ALLOCATIONS_COLLECTION)
    flt = {**_scope(tenant_id, app_key, accounting_entity_id), "allocation_id": allocation_id}
    existing = await coll.find_one(flt)
    if existing is None:
        raise AccountingNotFoundError("Allocation not found")
    if existing.get("status") != "active":
        raise AccountingValidationError("Allocation is already reversed")
    await coll.update_one(flt, {"$set": {
        "status": "reversed", "reversed_by": reversed_by,
        "reversed_at": _now(), "updated_at": _now(),
    }})
    existing.update({"status": "reversed"})
    return {k: v for k, v in existing.items() if k != "_id"}


async def reconciliation(
    session: AsyncSession, *, tenant_id: str, app_key: str, accounting_entity_id: str,
    kind: str, party_id: str | None = None, as_of: date | None = None,
) -> dict:
    """Tie the Mongo allocation metadata back to the immutable ledger."""
    _require_side(kind)
    as_of = as_of or date.today()

    open_items = await list_open_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=party_id, as_of=as_of,
    )
    payments = await list_unallocated_payments(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=party_id,
    )

    if party_id:
        balances = await get_party_outstanding(
            session, tenant_id=tenant_id, party_id=party_id, as_of=as_of,
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        ledger_balance = _d(balances[kind])
        unallocated_bucket = Decimal("0.00")
    else:
        lines, _total = await get_party_wise_balances(
            session, tenant_id=tenant_id, as_of=as_of, kind=kind,
            app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        # Exclude the NULL "Unallocated" bucket (manual entries with no source doc);
        # report it separately so the reconciliation difference stays clean.
        ledger_balance = sum((_d(l["balance"]) for l in lines if l.get("party_id") is not None), Decimal("0.00"))
        unallocated_bucket = sum((_d(l["balance"]) for l in lines if l.get("party_id") is None), Decimal("0.00"))

    result = reconcile(
        open_items_outstanding=_d(open_items["total_outstanding"]),
        unallocated_payments=_d(payments["total_unallocated"]),
        ledger_balance=ledger_balance,
    )
    result.update({
        "kind": kind, "as_of": as_of.isoformat(), "party_id": party_id,
        "ledger_unallocated_bucket": str(unallocated_bucket.quantize(_CENT)),
    })
    return result


async def ar_ap_aging(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, kind: str,
    party_id: str | None = None, as_of: date | None = None,
) -> dict:
    """AR (receivable) or AP (payable) aging report: open-item outstanding bucketed
    by days past due, grouped by party (party names enriched from Mongo)."""
    _require_side(kind)
    as_of = as_of or date.today()
    open_items = await list_open_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=party_id, as_of=as_of,
    )
    summary = aging_summary(open_items["items"])

    parties = await get_collection(PARTIES_COLLECTION).find(
        _scope(tenant_id, app_key, accounting_entity_id)
    ).to_list(length=5000)
    name_by_id = {p.get("party_id"): p.get("party_name") for p in parties}
    for row in summary["by_party"]:
        row["party_name"] = name_by_id.get(row["party_id"])

    summary.update({
        "kind": kind, "as_of": as_of.isoformat(), "accounting_entity_id": accounting_entity_id,
    })
    return summary
