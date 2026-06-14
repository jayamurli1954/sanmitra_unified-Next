"""Customer / vendor statements of account + dunning (payment reminders).

Phase D of the receivables workflow. Design rules, consistent with the rest
of the business module:

  * The statement is assembled purely from already-posted ledger lines
    (the party sub-ledger) plus the open-item view from payment allocation —
    no new postings, no invented numbers.
  * Dunning is deterministic: reminder levels come from the oldest overdue
    open item; letter text is a fixed template filled with ledger figures.
    Nothing is emailed automatically — the accountant prints/sends and
    records it (maker-checker), building an audit trail in Mongo.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

DUNNING_LOG_COLLECTION = "business_dunning_log"

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Reminder escalation policy, driven by the oldest overdue open item.
# Thresholds are days past due; level 0 means nothing is overdue.
DUNNING_LEVELS = [
    {"level": 1, "min_days_overdue": 1, "label": "Gentle reminder",
     "tone": "polite", "subject": "Payment reminder — outstanding invoices"},
    {"level": 2, "min_days_overdue": 31, "label": "Second reminder",
     "tone": "firm", "subject": "Second reminder — payment overdue"},
    {"level": 3, "min_days_overdue": 61, "label": "Final notice",
     "tone": "final", "subject": "Final notice before further action — overdue account"},
]

_DOC_LABELS = {
    "sales_invoice": "Invoice",
    "purchase_bill": "Bill",
    "credit_note": "Credit Note",
    "debit_note": "Debit Note",
    "receipt": "Receipt",
    "payment": "Payment",
}


def suggest_dunning_level(open_items: list[dict]) -> dict:
    """Pick the reminder level from the oldest overdue open item. Items carry
    `days_overdue` and `outstanding` (from the allocation open-item view)."""
    overdue = [i for i in open_items if int(i.get("days_overdue") or 0) > 0 and _q2(i.get("outstanding") or 0) > 0]
    if not overdue:
        return {"level": 0, "label": "No reminder needed", "max_days_overdue": 0,
                "overdue_count": 0, "overdue_total": "0.00"}
    max_days = max(int(i.get("days_overdue") or 0) for i in overdue)
    chosen = DUNNING_LEVELS[0]
    for rule in DUNNING_LEVELS:
        if max_days >= rule["min_days_overdue"]:
            chosen = rule
    overdue_total = sum((_q2(i.get("outstanding") or 0) for i in overdue), Decimal("0.00"))
    return {
        "level": chosen["level"], "label": chosen["label"], "subject": chosen["subject"],
        "tone": chosen["tone"], "max_days_overdue": max_days,
        "overdue_count": len(overdue), "overdue_total": str(_q2(overdue_total)),
    }


def build_dunning_letter(
    *,
    business_name: str,
    party_name: str,
    as_of: date,
    open_items: list[dict],
    suggestion: dict,
) -> str:
    """Deterministic reminder letter (plain text) for the suggested level.
    All figures come straight from the open-item view."""
    level = int(suggestion.get("level") or 0)
    if level <= 0:
        return ""
    overdue = [i for i in open_items if int(i.get("days_overdue") or 0) > 0 and _q2(i.get("outstanding") or 0) > 0]
    overdue.sort(key=lambda i: -int(i.get("days_overdue") or 0))

    intro = {
        1: "This is a friendly reminder that the following invoices are past their due date. "
           "If payment has already been made, please ignore this letter and share the payment details.",
        2: "Despite our earlier reminder, the invoices below remain unpaid. "
           "We request you to arrange payment at the earliest to keep the account in good standing.",
        3: "Despite repeated reminders, the invoices below remain unpaid. Please treat this as a final "
           "notice; if payment is not received within 7 days we may be compelled to pause further "
           "supplies and pursue recovery of the dues.",
    }[min(level, 3)]

    lines = [
        f"From: {business_name}",
        f"To: {party_name}",
        f"Date: {as_of.isoformat()}",
        "",
        f"Subject: {suggestion.get('subject') or 'Payment reminder'}",
        "",
        f"Dear {party_name},",
        "",
        intro,
        "",
        "Outstanding invoices:",
    ]
    for item in overdue:
        lines.append(
            f"  - {item.get('open_item_number') or item.get('open_item_id')} dated {item.get('item_date') or ''}: "
            f"Rs. {item.get('outstanding')} outstanding ({item.get('days_overdue')} days overdue)"
        )
    lines += [
        "",
        f"Total overdue: Rs. {suggestion.get('overdue_total')}",
        "",
        "Kindly arrange the payment and share the reference details so we can allocate it promptly.",
        "If there is any dispute or query on these invoices, please let us know immediately.",
        "",
        "Thank you,",
        business_name,
    ]
    return "\n".join(lines)


def reconcile_statement_open_items(
    *,
    kind: str,
    closing_balance: Decimal,
    open_items: list[dict],
) -> tuple[list[dict], list[str]]:
    """Suppress stale open-item reminders when allocation metadata lags ledger."""
    closing = _q2(closing_balance)
    open_total = sum((_q2(i.get("outstanding") or 0) for i in open_items), Decimal("0.00"))
    if not open_items or open_total == closing:
        return open_items, []

    if closing <= Decimal("0.00"):
        return [], [
            "Open-item allocation is out of date: the party ledger is settled, so overdue reminders are suppressed.",
        ]

    return open_items, [
        (
            "Open-item allocation does not match the party ledger closing balance; "
            "reminders are suppressed until receipts/payments are allocated."
        ),
    ]


def assemble_party_statement(
    *,
    party: dict,
    kind: str,
    from_date: date,
    to_date: date,
    opening_balance: Decimal,
    transactions: list[dict],
    open_items: list[dict],
    dunning_suggestion: dict,
    dunning_letter: str,
    dunning_log: list[dict],
    business_name: str,
) -> dict:
    """Statement of account: opening balance + dated transactions with a
    running balance + closing balance, plus the open-item/dunning view.

    Sign convention follows the side: receivable statements show what the
    customer owes (their debits increase the balance); payable statements show
    what we owe the vendor (their credits increase the balance)."""
    running = _q2(opening_balance)
    rows: list[dict] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")
    for txn in transactions:
        debit = _q2(txn.get("debit") or 0)
        credit = _q2(txn.get("credit") or 0)
        running = _q2(running + (debit - credit if kind == "receivable" else credit - debit))
        total_debit += debit
        total_credit += credit
        doc_type = str(txn.get("document_type") or "")
        rows.append({
            "entry_date": txn.get("entry_date"),
            "document_type": _DOC_LABELS.get(doc_type, doc_type or "Journal"),
            "reference": txn.get("reference"),
            "description": txn.get("description"),
            "debit": str(debit),
            "credit": str(credit),
            "balance": str(running),
        })

    open_items, allocation_notes = reconcile_statement_open_items(
        kind=kind,
        closing_balance=running,
        open_items=open_items,
    )
    if allocation_notes:
        dunning_suggestion = {
            "level": 0,
            "label": "Allocation required",
            "max_days_overdue": 0,
            "overdue_count": 0,
            "overdue_total": "0.00",
        }
        dunning_letter = ""

    return {
        "party": {
            "party_id": party.get("party_id"),
            "party_name": party.get("party_name"),
            "gstin": party.get("gstin"),
            "email": party.get("email"),
            "billing_address": party.get("billing_address"),
        },
        "business_name": business_name,
        "kind": kind,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "opening_balance": str(_q2(opening_balance)),
        "transactions": rows,
        "total_debit": str(_q2(total_debit)),
        "total_credit": str(_q2(total_credit)),
        "closing_balance": str(running),
        "open_items": open_items,
        "dunning": {
            "suggestion": dunning_suggestion,
            "letter": dunning_letter,
            "log": dunning_log,
        },
        "notes": [
            "Statement lines come from the posted party sub-ledger; the closing balance ties to the party's ledger balance.",
            "Open items and overdue ages come from payment allocation — allocate receipts to invoices to keep them accurate.",
            "Reminder letters are generated from the ledger figures; sending is manual and recorded below (maker-checker).",
            *allocation_notes,
        ],
    }


# --------------------------------------------------------------------------- #
# Async service layer.
# --------------------------------------------------------------------------- #

async def build_party_statement(
    session,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    kind: str = "receivable",
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict:
    from app.accounting.service import (
        AccountingNotFoundError,
        AccountingValidationError,
        _financial_year_start,
        get_party_ledger_lines,
    )
    from app.modules.business import allocation_service
    from app.modules.business.service import get_invoice_settings, get_party

    if kind not in ("receivable", "payable"):
        raise AccountingValidationError("kind must be 'receivable' or 'payable'")
    to_date = to_date or date.today()
    from_date = from_date or _financial_year_start(to_date)
    if from_date > to_date:
        raise AccountingValidationError("from_date cannot be after to_date")

    party = await get_party(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, party_id=party_id,
    )
    if party is None:
        raise AccountingNotFoundError("Party not found")

    opening, transactions = await get_party_ledger_lines(
        session,
        tenant_id=tenant_id, party_id=party_id, kind=kind,
        from_date=from_date, to_date=to_date,
        app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    open_items_payload = await allocation_service.list_open_items(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        kind=kind, party_id=party_id, as_of=to_date,
    )
    open_items = open_items_payload.get("items") or []

    settings = await get_invoice_settings(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    business_name = ((settings.get("branding") or {}).get("business_name") or "").strip() or "Our business"

    suggestion = suggest_dunning_level(open_items)
    letter = build_dunning_letter(
        business_name=business_name,
        party_name=party.get("party_name") or party_id,
        as_of=to_date,
        open_items=open_items,
        suggestion=suggestion,
    ) if kind == "receivable" else ""
    if kind != "receivable":
        suggestion = {"level": 0, "label": "Dunning applies to receivables only",
                      "max_days_overdue": 0, "overdue_count": 0, "overdue_total": "0.00"}

    log = await list_dunning_log(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, party_id=party_id,
    )

    return assemble_party_statement(
        party=party, kind=kind, from_date=from_date, to_date=to_date,
        opening_balance=opening, transactions=transactions,
        open_items=open_items, dunning_suggestion=suggestion,
        dunning_letter=letter, dunning_log=log, business_name=business_name,
    )


async def record_dunning_sent(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    level: int,
    note: str | None,
    overdue_total: str | None,
    created_by: str,
) -> dict:
    """Log that a reminder was actually sent (print/email/WhatsApp — manual)."""
    from app.accounting.service import AccountingValidationError
    from app.db.mongo import get_collection

    if level < 1 or level > 3:
        raise AccountingValidationError("Dunning level must be 1, 2 or 3")
    doc = {
        "dunning_id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_id": party_id,
        "level": level,
        "label": next((r["label"] for r in DUNNING_LEVELS if r["level"] == level), f"Level {level}"),
        "overdue_total": overdue_total,
        "note": (note or "").strip() or None,
        "created_by": created_by,
        "created_at": _now(),
    }
    await get_collection(DUNNING_LOG_COLLECTION).insert_one(doc)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


async def list_dunning_log(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, party_id: str,
) -> list[dict]:
    from app.db.mongo import get_collection

    rows = await get_collection(DUNNING_LOG_COLLECTION).find({
        "tenant_id": tenant_id, "app_key": app_key,
        "accounting_entity_id": accounting_entity_id, "party_id": party_id,
    }).sort("created_at", -1).to_list(length=100)
    for row in rows:
        row.pop("_id", None)
        if isinstance(row.get("created_at"), datetime):
            row["created_at"] = row["created_at"].isoformat()
    return rows
