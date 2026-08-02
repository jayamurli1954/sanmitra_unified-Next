"""LegalMitra Stage 6 — practice fee billing (Mongo) + optional MitraBooks posting."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pymongo import ReturnDocument

from app.config import get_settings
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal import billing_accounting
from app.modules.legal.billing_schemas import (
    FeeCollectionCreateRequest,
    FeeGlMapUpsertRequest,
    FeeInvoiceCreateRequest,
    FeeInvoiceUpdateRequest,
    FeeInvoiceVoidRequest,
    FeeLineIn,
    TimeEntryCreateRequest,
    _q,
)
from app.modules.legal.practice_service import (
    PracticeNotFoundError,
    get_client,
    get_matter,
)

LEGAL_FEE_INVOICES = "legal_fee_invoices"
LEGAL_FEE_COLLECTIONS = "legal_fee_collections"
LEGAL_TIME_ENTRIES = "legal_time_entries"
LEGAL_FEE_GL_MAP = "legal_fee_gl_map"
LEGAL_PRACTICE_COUNTERS = "legal_practice_counters"

DEFAULT_APP_KEY = "legalmitra"


class BillingDisabledError(Exception):
    pass


class BillingNotFoundError(Exception):
    pass


class BillingValidationError(Exception):
    pass


class BillingConflictError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(doc: dict) -> dict:
    out = {k: v for k, v in doc.items() if k != "_id"}
    for key in (
        "subtotal",
        "tax_total",
        "grand_total",
        "amount_collected",
        "amount_outstanding",
        "amount",
        "hourly_rate",
        "quantity",
        "unit_rate",
        "tax_rate_percent",
        "line_subtotal",
        "line_tax",
        "line_total",
        "total_billed",
        "total_collected",
        "fees_outstanding",
    ):
        if key in out and out[key] is not None and not isinstance(out[key], Decimal):
            try:
                out[key] = _q(out[key])
            except Exception:
                pass
    if "lines" in out and isinstance(out["lines"], list):
        normalized = []
        for line in out["lines"]:
            row = dict(line)
            for key in (
                "quantity",
                "unit_rate",
                "tax_rate_percent",
                "line_subtotal",
                "line_tax",
                "line_total",
            ):
                if key in row and row[key] is not None:
                    row[key] = _q(row[key])
            normalized.append(row)
        out["lines"] = normalized
    if isinstance(out.get("collected_on"), str):
        out["collected_on"] = date.fromisoformat(out["collected_on"])
    if isinstance(out.get("work_date"), str):
        out["work_date"] = date.fromisoformat(out["work_date"])
    return out


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


def _require_billing() -> None:
    if not getattr(get_settings(), "LEGALMITRA_BILLING_ENABLED", True):
        raise BillingDisabledError("LegalMitra billing is disabled")


async def _audit(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            product=app_key or DEFAULT_APP_KEY,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        pass


async def ensure_billing_indexes() -> None:
    invoices = get_collection(LEGAL_FEE_INVOICES)
    await invoices.create_index(
        [("tenant_id", 1), ("app_key", 1), ("invoice_id", 1)], unique=True
    )
    await invoices.create_index(
        [("tenant_id", 1), ("app_key", 1), ("invoice_number", 1)], unique=True
    )
    await invoices.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("created_at", -1)]
    )
    await invoices.create_index(
        [("tenant_id", 1), ("app_key", 1), ("status", 1), ("updated_at", -1)]
    )

    collections = get_collection(LEGAL_FEE_COLLECTIONS)
    await collections.create_index(
        [("tenant_id", 1), ("app_key", 1), ("collection_id", 1)], unique=True
    )
    await collections.create_index(
        [("tenant_id", 1), ("app_key", 1), ("idempotency_key", 1)], unique=True
    )
    await collections.create_index(
        [("tenant_id", 1), ("app_key", 1), ("invoice_id", 1), ("created_at", -1)]
    )

    time_entries = get_collection(LEGAL_TIME_ENTRIES)
    await time_entries.create_index(
        [("tenant_id", 1), ("app_key", 1), ("entry_id", 1)], unique=True
    )
    await time_entries.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("work_date", -1)]
    )

    gl_map = get_collection(LEGAL_FEE_GL_MAP)
    await gl_map.create_index(
        [("tenant_id", 1), ("app_key", 1)], unique=True
    )


def _compute_lines(lines: list[FeeLineIn] | list[dict]) -> tuple[list[dict], Decimal, Decimal, Decimal]:
    out_lines: list[dict] = []
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    for raw in lines:
        if isinstance(raw, FeeLineIn):
            description = raw.description.strip()
            qty = _q(raw.quantity)
            rate = _q(raw.unit_rate)
            tax_rate = _q(raw.tax_rate_percent)
        else:
            description = str(raw.get("description") or "").strip()
            qty = _q(raw.get("quantity") or 0)
            rate = _q(raw.get("unit_rate") or 0)
            tax_rate = _q(raw.get("tax_rate_percent") or 0)
        line_sub = _q(qty * rate)
        line_tax = _q(line_sub * tax_rate / Decimal("100"))
        line_total = _q(line_sub + line_tax)
        out_lines.append(
            {
                "description": description,
                "quantity": str(qty),
                "unit_rate": str(rate),
                "tax_rate_percent": str(tax_rate),
                "line_subtotal": str(line_sub),
                "line_tax": str(line_tax),
                "line_total": str(line_total),
            }
        )
        subtotal = _q(subtotal + line_sub)
        tax_total = _q(tax_total + line_tax)
    grand = _q(subtotal + tax_total)
    return out_lines, subtotal, tax_total, grand


async def _next_invoice_number(*, tenant_id: str, app_key: str) -> str:
    year = _now().year
    key = f"fee_invoice:{year}"
    counters = get_collection(LEGAL_PRACTICE_COUNTERS)
    doc = await counters.find_one_and_update(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "key": key},
        {"$inc": {"seq": 1}, "$setOnInsert": {"created_at": _now()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(doc.get("seq") or 1)
    return f"FEE-{year}-{seq:06d}"


def _invoice_status_after_payment(*, grand_total: Decimal, collected: Decimal, current: str) -> str:
    if current == "void":
        return "void"
    if collected <= 0:
        return "issued" if current != "draft" else "draft"
    if collected >= grand_total:
        return "paid"
    return "partially_paid"


async def create_fee_invoice(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    payload: FeeInvoiceCreateRequest,
) -> dict:
    _require_billing()
    matter = await get_matter(
        tenant_id=tenant_id, app_key=app_key, matter_id=payload.matter_id
    )
    client_id = payload.client_id or matter.get("client_id")
    if client_id:
        await get_client(tenant_id=tenant_id, app_key=app_key, client_id=client_id)

    lines, subtotal, tax_total, grand = _compute_lines(payload.lines)
    if grand <= 0:
        raise BillingValidationError("Invoice grand total must be positive")

    now = _now()
    invoice_id = str(uuid4())
    invoice_number = await _next_invoice_number(tenant_id=tenant_id, app_key=app_key)
    doc = {
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter["matter_id"],
        "client_id": client_id,
        "status": "draft",
        "currency": (payload.currency or "INR").upper(),
        "lines": lines,
        "subtotal": str(subtotal),
        "tax_total": str(tax_total),
        "grand_total": str(grand),
        "amount_collected": str(Decimal("0.00")),
        "amount_outstanding": str(grand),
        "notes": (payload.notes or "").strip() or None,
        "gstin": (payload.gstin or "").strip() or None,
        "place_of_supply": (payload.place_of_supply or "").strip() or None,
        "issued_at": None,
        "issued_by": None,
        "voided_at": None,
        "void_reason": None,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(LEGAL_FEE_INVOICES).insert_one(doc)
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_invoice_created",
        entity_type="legal_fee_invoice",
        entity_id=invoice_id,
        new_value={"invoice_number": invoice_number, "grand_total": str(grand)},
    )
    return _serialize(doc)


async def list_fee_invoices(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> dict:
    _require_billing()
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if matter_id:
        flt["matter_id"] = matter_id
    if status:
        flt["status"] = status
    rows = await get_collection(LEGAL_FEE_INVOICES).find(flt).to_list(length=limit)
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    items = [_serialize(r) for r in rows[:limit]]
    return {"items": items, "count": len(items)}


async def get_fee_invoice(
    *, tenant_id: str, app_key: str, invoice_id: str
) -> dict:
    _require_billing()
    doc = await get_collection(LEGAL_FEE_INVOICES).find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id}
    )
    if not doc:
        raise BillingNotFoundError(f"Invoice not found: {invoice_id}")
    return _serialize(doc)


async def update_fee_invoice(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    invoice_id: str,
    payload: FeeInvoiceUpdateRequest,
) -> dict:
    _require_billing()
    invoices = get_collection(LEGAL_FEE_INVOICES)
    doc = await invoices.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id}
    )
    if not doc:
        raise BillingNotFoundError(f"Invoice not found: {invoice_id}")
    if doc.get("status") != "draft":
        raise BillingConflictError("Only draft invoices can be updated")

    updates: dict[str, Any] = {"updated_at": _now()}
    if payload.lines is not None:
        lines, subtotal, tax_total, grand = _compute_lines(payload.lines)
        if grand <= 0:
            raise BillingValidationError("Invoice grand total must be positive")
        updates.update(
            {
                "lines": lines,
                "subtotal": str(subtotal),
                "tax_total": str(tax_total),
                "grand_total": str(grand),
                "amount_outstanding": str(grand),
            }
        )
    if payload.notes is not None:
        updates["notes"] = payload.notes.strip() or None
    if payload.gstin is not None:
        updates["gstin"] = payload.gstin.strip() or None
    if payload.place_of_supply is not None:
        updates["place_of_supply"] = payload.place_of_supply.strip() or None

    await invoices.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id},
        {"$set": updates},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_invoice_updated",
        entity_type="legal_fee_invoice",
        entity_id=invoice_id,
        new_value={k: updates[k] for k in updates if k != "updated_at"},
    )
    return await get_fee_invoice(
        tenant_id=tenant_id, app_key=app_key, invoice_id=invoice_id
    )


async def issue_fee_invoice(
    *, tenant_id: str, app_key: str, actor_id: str, invoice_id: str
) -> dict:
    _require_billing()
    invoices = get_collection(LEGAL_FEE_INVOICES)
    doc = await invoices.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id}
    )
    if not doc:
        raise BillingNotFoundError(f"Invoice not found: {invoice_id}")
    if doc.get("status") != "draft":
        raise BillingConflictError(f"Cannot issue invoice in status {doc.get('status')}")

    now = _now()
    await invoices.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id},
        {
            "$set": {
                "status": "issued",
                "issued_at": now,
                "issued_by": actor_id,
                "updated_at": now,
            }
        },
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_invoice_issued",
        entity_type="legal_fee_invoice",
        entity_id=invoice_id,
        new_value={"status": "issued"},
    )
    return await get_fee_invoice(
        tenant_id=tenant_id, app_key=app_key, invoice_id=invoice_id
    )


async def void_fee_invoice(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    invoice_id: str,
    payload: FeeInvoiceVoidRequest,
    session=None,
) -> dict:
    _require_billing()
    if not payload.confirm:
        raise BillingValidationError("confirm=true is required to void")
    invoices = get_collection(LEGAL_FEE_INVOICES)
    doc = await invoices.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id}
    )
    if not doc:
        raise BillingNotFoundError(f"Invoice not found: {invoice_id}")
    if doc.get("status") == "void":
        raise BillingConflictError("Invoice already void")
    if doc.get("status") == "draft":
        # Soft-void drafts without collections.
        pass
    else:
        collected = _q(doc.get("amount_collected") or 0)
        if collected > 0:
            raise BillingConflictError(
                "Cannot void an invoice with collections; reverse collections first"
            )

    now = _now()
    await invoices.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "invoice_id": invoice_id},
        {
            "$set": {
                "status": "void",
                "voided_at": now,
                "void_reason": payload.reason,
                "amount_outstanding": str(Decimal("0.00")),
                "updated_at": now,
            }
        },
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_invoice_voided",
        entity_type="legal_fee_invoice",
        entity_id=invoice_id,
        new_value={"reason": payload.reason},
    )
    return await get_fee_invoice(
        tenant_id=tenant_id, app_key=app_key, invoice_id=invoice_id
    )


async def record_fee_collection(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    invoice_id: str,
    payload: FeeCollectionCreateRequest,
    session=None,
) -> dict:
    _require_billing()
    invoices = get_collection(LEGAL_FEE_INVOICES)
    collections = get_collection(LEGAL_FEE_COLLECTIONS)
    scope = _scope(tenant_id=tenant_id, app_key=app_key)

    existing = await collections.find_one({**scope, "idempotency_key": payload.idempotency_key})
    if existing:
        return _serialize(existing)

    invoice = await invoices.find_one({**scope, "invoice_id": invoice_id})
    if not invoice:
        raise BillingNotFoundError(f"Invoice not found: {invoice_id}")
    if invoice.get("status") in {"draft", "void"}:
        raise BillingConflictError(
            f"Cannot collect against invoice in status {invoice.get('status')}"
        )

    amount = _q(payload.amount)
    outstanding = _q(invoice.get("amount_outstanding") or 0)
    if amount > outstanding:
        raise BillingValidationError(
            f"Collection {amount} exceeds outstanding {outstanding}"
        )

    want_post = bool(payload.post_to_mitrabooks)
    if want_post:
        if not payload.confirm_post_to_mitrabooks:
            raise BillingValidationError(
                "confirm_post_to_mitrabooks=true is required to post to MitraBooks"
            )
        if not billing_accounting.posting_enabled():
            raise BillingValidationError("MitraBooks posting is disabled")
        if session is None:
            raise BillingValidationError(
                "Database session required for MitraBooks posting"
            )

    collection_id = str(uuid4())
    collected_on = payload.collected_on or date.today()
    posting_ref = None
    journal_id = None
    accounting_status = "not_posted"
    accounting_error = None

    if want_post:
        gl_map = await get_fee_gl_map(tenant_id=tenant_id, app_key=app_key)
        if not gl_map.get("configured"):
            raise BillingValidationError("Configure fee GL map before posting to MitraBooks")
        try:
            posted = await billing_accounting.post_fee_collection_to_books(
                session,
                legal_tenant_id=tenant_id,
                actor_id=actor_id,
                collection_id=collection_id,
                invoice_number=invoice.get("invoice_number") or invoice_id,
                amount=amount,
                collected_on=collected_on,
                gl_map=gl_map,
            )
            journal_id = posted["journal_id"]
            posting_ref = posted["idempotency_key"]
            accounting_status = "posted"
        except Exception as exc:  # noqa: BLE001 — fail closed for books claim
            raise BillingValidationError(f"MitraBooks posting failed: {exc}") from exc

    now = _now()
    collection = {
        "collection_id": collection_id,
        **scope,
        "invoice_id": invoice_id,
        "amount": str(amount),
        "mode": payload.mode,
        "collected_on": collected_on.isoformat(),
        "reference": (payload.reference or "").strip() or None,
        "notes": (payload.notes or "").strip() or None,
        "idempotency_key": payload.idempotency_key,
        "accounting_status": accounting_status,
        "accounting_posting_ref": posting_ref,
        "accounting_journal_id": journal_id,
        "accounting_error": accounting_error,
        "created_by": actor_id,
        "created_at": now,
    }
    try:
        await collections.insert_one(collection)
    except Exception as exc:
        # Compensate journal if Mongo write fails after successful post.
        if journal_id is not None and session is not None:
            gl_map = await get_fee_gl_map(tenant_id=tenant_id, app_key=app_key)
            try:
                await billing_accounting.reverse_fee_collection_posting(
                    session,
                    actor_id=actor_id,
                    journal_id=int(journal_id),
                    gl_map=gl_map,
                    reason="Compensate Mongo insert failure after fee collection post",
                )
            except Exception:
                pass
        raise BillingConflictError(f"Failed to persist collection: {exc}") from exc

    new_collected = _q(_q(invoice.get("amount_collected") or 0) + amount)
    grand = _q(invoice.get("grand_total") or 0)
    new_outstanding = _q(grand - new_collected)
    new_status = _invoice_status_after_payment(
        grand_total=grand, collected=new_collected, current=str(invoice.get("status"))
    )
    await invoices.update_one(
        {**scope, "invoice_id": invoice_id},
        {
            "$set": {
                "amount_collected": str(new_collected),
                "amount_outstanding": str(new_outstanding),
                "status": new_status,
                "updated_at": now,
            }
        },
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_collection_recorded",
        entity_type="legal_fee_collection",
        entity_id=collection_id,
        new_value={
            "invoice_id": invoice_id,
            "amount": str(amount),
            "accounting_status": accounting_status,
            "accounting_journal_id": journal_id,
        },
    )
    return _serialize(collection)


async def list_fee_collections(
    *,
    tenant_id: str,
    app_key: str,
    invoice_id: str,
    limit: int = 100,
) -> dict:
    _require_billing()
    await get_fee_invoice(tenant_id=tenant_id, app_key=app_key, invoice_id=invoice_id)
    rows = await get_collection(LEGAL_FEE_COLLECTIONS).find(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "invoice_id": invoice_id,
        }
    ).to_list(length=limit)
    rows.sort(key=lambda r: str(r.get("created_at") or ""))
    items = [_serialize(r) for r in rows[:limit]]
    return {"items": items, "count": len(items)}


async def get_fee_summary(*, tenant_id: str, app_key: str) -> dict:
    _require_billing()
    rows = await get_collection(LEGAL_FEE_INVOICES).find(
        {**_scope(tenant_id=tenant_id, app_key=app_key)}
    ).to_list(length=5000)

    total_billed = Decimal("0.00")
    total_collected = Decimal("0.00")
    outstanding = Decimal("0.00")
    issued = paid = partial = draft = 0
    for doc in rows:
        status = doc.get("status")
        if status == "void":
            continue
        if status == "draft":
            draft += 1
            continue
        grand = _q(doc.get("grand_total") or 0)
        collected = _q(doc.get("amount_collected") or 0)
        due = _q(doc.get("amount_outstanding") or 0)
        total_billed = _q(total_billed + grand)
        total_collected = _q(total_collected + collected)
        outstanding = _q(outstanding + due)
        if status == "paid":
            paid += 1
        elif status == "partially_paid":
            partial += 1
            issued += 1
        elif status == "issued":
            issued += 1

    display = f"₹{outstanding:,.2f}"
    return {
        "currency": "INR",
        "invoices_issued": issued,
        "invoices_paid": paid,
        "invoices_partial": partial,
        "invoices_draft": draft,
        "total_billed": total_billed,
        "total_collected": total_collected,
        "fees_outstanding": outstanding,
        "fees_outstanding_display": display,
        "data_source": "live",
    }


async def create_time_entry(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    payload: TimeEntryCreateRequest,
) -> dict:
    _require_billing()
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=payload.matter_id)
    minutes = int(payload.minutes)
    rate = _q(payload.hourly_rate)
    amount = _q(Decimal(minutes) / Decimal("60") * rate)
    now = _now()
    work_date = payload.work_date or date.today()
    doc = {
        "entry_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": payload.matter_id,
        "minutes": minutes,
        "hourly_rate": str(rate),
        "amount": str(amount),
        "description": payload.description.strip(),
        "work_date": work_date.isoformat(),
        "billable": bool(payload.billable),
        "created_by": actor_id,
        "created_at": now,
    }
    await get_collection(LEGAL_TIME_ENTRIES).insert_one(doc)
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_time_entry_created",
        entity_type="legal_time_entry",
        entity_id=doc["entry_id"],
        new_value={"matter_id": payload.matter_id, "minutes": minutes},
    )
    return _serialize(doc)


async def list_time_entries(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str | None = None,
    limit: int = 100,
) -> dict:
    _require_billing()
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if matter_id:
        flt["matter_id"] = matter_id
    rows = await get_collection(LEGAL_TIME_ENTRIES).find(flt).to_list(length=limit)
    rows.sort(key=lambda r: str(r.get("work_date") or ""), reverse=True)
    return {"items": [_serialize(r) for r in rows[:limit]], "count": len(rows[:limit])}


async def get_fee_gl_map(*, tenant_id: str, app_key: str) -> dict:
    _require_billing()
    doc = await get_collection(LEGAL_FEE_GL_MAP).find_one(
        _scope(tenant_id=tenant_id, app_key=app_key)
    )
    if not doc:
        return {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "bank_account_id": None,
            "income_account_id": None,
            "bank_account_code": None,
            "income_account_code": None,
            "accounting_app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "notes": None,
            "configured": False,
            "updated_at": None,
            "books_tenant_id": tenant_id,
            "payload": {},
        }
    out = _serialize(doc)
    out["configured"] = bool(out.get("bank_account_id") and out.get("income_account_id"))
    out.setdefault("books_tenant_id", tenant_id)
    return out


async def upsert_fee_gl_map(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    payload: FeeGlMapUpsertRequest,
) -> dict:
    _require_billing()
    now = _now()
    doc = {
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "bank_account_id": int(payload.bank_account_id),
        "income_account_id": int(payload.income_account_id),
        "bank_account_code": payload.bank_account_code,
        "income_account_code": payload.income_account_code,
        "accounting_app_key": payload.accounting_app_key or "mitrabooks",
        "accounting_entity_id": payload.accounting_entity_id or "primary",
        "books_tenant_id": tenant_id,
        "notes": (payload.notes or "").strip() or None,
        "updated_at": now,
        "updated_by": actor_id,
    }
    await get_collection(LEGAL_FEE_GL_MAP).update_one(
        _scope(tenant_id=tenant_id, app_key=app_key),
        {"$set": doc},
        upsert=True,
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_fee_gl_map_upserted",
        entity_type="legal_fee_gl_map",
        entity_id=tenant_id,
        new_value={
            "bank_account_id": doc["bank_account_id"],
            "income_account_id": doc["income_account_id"],
        },
    )
    return await get_fee_gl_map(tenant_id=tenant_id, app_key=app_key)
