"""MitraBooks Data Health Score.

Read-only checks for operational data quality. The score is intentionally
deterministic and source-backed: it reads tenant-scoped business documents,
bank-reconciliation metadata, and open-item aging, then returns rule evidence.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from app.modules.business import allocation_service
from app.modules.business.bank_recon import BANK_RECON_MATCHES_COLLECTION, BANK_STATEMENT_LINES_COLLECTION
from app.modules.business.service import (
    CREDIT_NOTES_COLLECTION,
    DEBIT_NOTES_COLLECTION,
    PARTIES_COLLECTION,
    PURCHASE_BILLS_COLLECTION,
    SALES_INVOICES_COLLECTION,
    VOUCHERS_COLLECTION,
)
from app.db.mongo import get_collection

_CENT = Decimal("0.01")

_DRAFT_STATUSES = {"draft", "pending_approval", "submitted", "not_submitted"}
_FINAL_STATUSES = {"posted", "cancelled", "reversed", "voided", "rejected", "paid", "partially_paid"}


def _scope(tenant_id: str, app_key: str, accounting_entity_id: str) -> dict:
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


def _d(value) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(_CENT)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _parse_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _rule(key: str, label: str, *, count: int, severity: str, impact: int, detail: str, action: str, evidence=None) -> dict:
    status = "pass" if count == 0 or impact == 0 else "fail"
    return {
        "key": key,
        "label": label,
        "status": status,
        "severity": "info" if status == "pass" else severity,
        "count": count,
        "score_impact": 0 if status == "pass" else impact,
        "detail": detail,
        "action": action,
        "evidence": evidence or [],
    }


_DOCUMENT_WORKSPACES = {
    "sales_invoice": ("sales", "business_sales_invoice", "Open Sales"),
    "purchase_bill": ("bills", "business_purchase_bill", "Open Bills"),
    "voucher": ("vouchers", "business_voucher", "Open Vouchers"),
    "credit_note": ("credit-notes", "business_credit_note", "Open Credit Notes"),
    "debit_note": ("debit-notes", "business_debit_note", "Open Debit Notes"),
}


def _issue_token(value) -> str:
    text = str(value or "unknown").strip().lower()
    return "".join(ch if ch.isalnum() else "-" for ch in text).strip("-") or "unknown"


def _issue_for_evidence(rule: dict, evidence: dict, index: int) -> dict:
    rule_key = str(rule.get("key") or "data_health")
    workspace = "overview"
    entity_type = "data_health_issue"
    entity_id = f"{rule_key}-{index + 1}"
    entity_label = str(rule.get("label") or rule_key)
    action_label = "Review Issue"

    if rule_key == "missing_gstin":
        workspace = "parties"
        entity_type = "business_party"
        entity_id = evidence.get("party_id") or entity_id
        entity_label = evidence.get("party_name") or entity_id
        action_label = "Open Parties"
    elif rule_key == "unposted_drafts":
        workspace, entity_type, action_label = _DOCUMENT_WORKSPACES.get(
            str(evidence.get("document_type") or ""),
            ("vouchers", "business_document", "Open Documents"),
        )
        entity_id = evidence.get("document_id") or evidence.get("number") or entity_id
        entity_label = evidence.get("number") or entity_id
    elif rule_key == "duplicate_invoices":
        workspace = "sales"
        entity_type = "business_sales_invoice"
        entity_id = evidence.get("invoice_number") or entity_id
        entity_label = f"Invoice {entity_id}"
        action_label = "Open Sales"
    elif rule_key == "stale_reconciliation":
        workspace = "bank-recon"
        entity_type = "bank_statement_line"
        entity_id = evidence.get("statement_line_id") or entity_id
        entity_label = evidence.get("description") or entity_id
        action_label = "Open Bank Reconciliation"
    elif rule_key == "overdue_exposure":
        workspace = "financial-health"
        entity_type = "receivables_aging"
        entity_id = "receivables-aging"
        entity_label = f"Overdue {evidence.get('overdue') or '0.00'}"
        action_label = "Open Financial Health"

    return {
        "issue_id": f"data-health:{rule_key}:{entity_type}:{_issue_token(entity_id)}",
        "rule_key": rule_key,
        "severity": rule.get("severity") or "warning",
        "title": rule.get("label") or rule_key.replace("_", " ").title(),
        "description": rule.get("detail") or "",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_label": entity_label,
        "workspace": workspace,
        "action_label": action_label,
        "action": rule.get("action") or "Review the affected record.",
        "status": "open",
        "evidence": evidence,
    }


def _build_issues(rules: list[dict]) -> list[dict]:
    issues = []
    for rule in rules:
        if rule.get("status") == "pass":
            continue
        evidence_rows = rule.get("evidence") or [{}]
        for index, evidence in enumerate(evidence_rows[:10]):
            issues.append(_issue_for_evidence(rule, evidence if isinstance(evidence, dict) else {}, index))
    return issues


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _rule_missing_gstin(parties: list[dict]) -> dict:
    rows = [
        {
            "party_id": p.get("party_id"),
            "party_name": p.get("party_name"),
            "party_type": p.get("party_type"),
        }
        for p in parties
        if p.get("is_active", True) and str(p.get("party_type") or "").lower() in {"customer", "vendor"}
        and not str(p.get("gstin") or "").strip()
    ]
    return _rule(
        "missing_gstin",
        "Missing GSTIN",
        count=len(rows),
        severity="warning",
        impact=min(20, len(rows) * 4),
        detail="Active customers/vendors should carry GSTIN where the party is registered.",
        action="Open Parties and complete GSTIN/PAN details before filing or e-invoice work.",
        evidence=rows[:10],
    )


def _rule_unposted_drafts(collection_rows: dict[str, list[dict]]) -> dict:
    rows = []
    for document_type, docs in collection_rows.items():
        for doc in docs:
            status = str(doc.get("status") or "").strip().lower()
            if status in _DRAFT_STATUSES or (status and status not in _FINAL_STATUSES):
                rows.append({
                    "document_type": document_type,
                    "document_id": doc.get("invoice_id") or doc.get("bill_id") or doc.get("voucher_id")
                                   or doc.get("credit_note_id") or doc.get("debit_note_id"),
                    "number": doc.get("invoice_number") or doc.get("bill_number") or doc.get("voucher_number")
                              or doc.get("credit_note_number") or doc.get("debit_note_number"),
                    "status": status or "unknown",
                })
    return _rule(
        "unposted_drafts",
        "Unposted drafts",
        count=len(rows),
        severity="warning",
        impact=min(20, len(rows) * 3),
        detail="Draft or approval-pending financial documents do not affect reports until posted.",
        action="Review draft and pending documents; post, reject, or cancel them before period review.",
        evidence=rows[:10],
    )


def _rule_duplicate_invoices(invoices: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = {}
    for invoice in invoices:
        if str(invoice.get("status") or "").lower() in {"cancelled", "voided", "reversed"}:
            continue
        number = str(invoice.get("invoice_number") or "").strip().upper()
        if number:
            buckets.setdefault(number, []).append(invoice)
    duplicates = [
        {
            "invoice_number": number,
            "count": len(rows),
            "invoice_ids": [row.get("invoice_id") for row in rows[:5]],
        }
        for number, rows in buckets.items()
        if len(rows) > 1
    ]
    return _rule(
        "duplicate_invoices",
        "Duplicate invoice numbers",
        count=sum(item["count"] - 1 for item in duplicates),
        severity="danger",
        impact=min(25, len(duplicates) * 10),
        detail="Invoice numbers must be unique inside the active tenant book.",
        action="Investigate duplicate invoice numbers and correct with cancellation/reversal where needed.",
        evidence=duplicates[:10],
    )


def _rule_stale_reconciliation(statement_lines: list[dict], matches: list[dict], *, as_of: date) -> dict:
    matched = {str(row.get("statement_line_id")) for row in matches if row.get("status", "active") == "active"}
    rows = []
    for line in statement_lines:
        line_id = str(line.get("statement_line_id") or "")
        txn_date = _parse_date(line.get("txn_date") or line.get("uploaded_at"))
        if not line_id or line_id in matched or txn_date is None:
            continue
        age = (as_of - txn_date).days
        if age > 30:
            rows.append({
                "statement_line_id": line_id,
                "txn_date": txn_date.isoformat(),
                "age_days": age,
                "description": line.get("description"),
            })
    return _rule(
        "stale_reconciliation",
        "Stale bank reconciliation",
        count=len(rows),
        severity="warning",
        impact=min(20, len(rows) * 4),
        detail="Bank statement lines older than 30 days should be matched or posted as bank-only vouchers.",
        action="Open Bank Reconciliation and resolve stale unmatched statement lines.",
        evidence=rows[:10],
    )


def _rule_overdue_exposure(ar_aging: dict) -> dict:
    totals = ar_aging.get("totals") or {}
    overdue = _d(totals.get("31-60")) + _d(totals.get("61-90")) + _d(totals.get("90+"))
    over_90 = _d(totals.get("90+"))
    count = sum(1 for row in ar_aging.get("by_party") or [] if _d((row.get("buckets") or {}).get("31-60")) + _d((row.get("buckets") or {}).get("61-90")) + _d((row.get("buckets") or {}).get("90+")) > 0)
    severity = "danger" if over_90 > 0 else "warning"
    impact = 0 if overdue <= 0 else (25 if over_90 > 0 else 15)
    return _rule(
        "overdue_exposure",
        "Overdue receivables exposure",
        count=count,
        severity=severity,
        impact=impact,
        detail=f"Receivables overdue total is {overdue}; over-90-days exposure is {over_90}.",
        action="Open receivables aging and follow up overdue customers before closing review.",
        evidence=[{
            "overdue": str(overdue),
            "over_90": str(over_90),
            "grand_total": str(_d(ar_aging.get("grand_total"))),
        }],
    )


def assemble_data_health_score(*, parties: list[dict], documents: dict[str, list[dict]], statement_lines: list[dict], recon_matches: list[dict], ar_aging: dict, as_of: date) -> dict:
    rules = [
        _rule_missing_gstin(parties),
        _rule_unposted_drafts(documents),
        _rule_duplicate_invoices(documents.get("sales_invoice", [])),
        _rule_stale_reconciliation(statement_lines, recon_matches, as_of=as_of),
        _rule_overdue_exposure(ar_aging),
    ]
    score = max(0, 100 - sum(int(rule["score_impact"]) for rule in rules))
    failing = [rule for rule in rules if rule["status"] != "pass"]
    issues = _build_issues(rules)
    return {
        "as_of": as_of.isoformat(),
        "score": score,
        "grade": _grade(score),
        "status": "ready" if not failing else "needs_attention",
        "summary": "Data health checks passed." if not failing else f"{len(failing)} data-health rule(s) need attention.",
        "rules": rules,
        "issues": issues,
        "issue_count": len(issues),
        "source": {
            "parties": PARTIES_COLLECTION,
            "documents": [SALES_INVOICES_COLLECTION, PURCHASE_BILLS_COLLECTION, VOUCHERS_COLLECTION, CREDIT_NOTES_COLLECTION, DEBIT_NOTES_COLLECTION],
            "bank_reconciliation": [BANK_STATEMENT_LINES_COLLECTION, BANK_RECON_MATCHES_COLLECTION],
            "overdue_exposure": "receivables_open_item_aging",
        },
    }


async def _load_collection(name: str, scope: dict, *, limit: int = 5000) -> list[dict]:
    return await get_collection(name).find(scope).to_list(length=limit)


async def build_data_health_score(*, tenant_id: str, app_key: str, accounting_entity_id: str = "primary", as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    scope = _scope(tenant_id, app_key, accounting_entity_id)
    parties = await _load_collection(PARTIES_COLLECTION, scope)
    invoices = await _load_collection(SALES_INVOICES_COLLECTION, scope)
    bills = await _load_collection(PURCHASE_BILLS_COLLECTION, scope)
    vouchers = await _load_collection(VOUCHERS_COLLECTION, scope)
    credit_notes = await _load_collection(CREDIT_NOTES_COLLECTION, scope)
    debit_notes = await _load_collection(DEBIT_NOTES_COLLECTION, scope)
    statement_lines = await _load_collection(BANK_STATEMENT_LINES_COLLECTION, scope)
    recon_matches = await _load_collection(BANK_RECON_MATCHES_COLLECTION, scope)
    ar_aging = await allocation_service.ar_ap_aging(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, kind="receivable", as_of=as_of,
    )
    return assemble_data_health_score(
        parties=parties,
        documents={
            "sales_invoice": invoices,
            "purchase_bill": bills,
            "voucher": vouchers,
            "credit_note": credit_notes,
            "debit_note": debit_notes,
        },
        statement_lines=statement_lines,
        recon_matches=recon_matches,
        ar_aging=ar_aging,
        as_of=as_of,
    )
