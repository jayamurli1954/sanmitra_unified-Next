"""Cross-document approval queue listing (vouchers, invoices, bills, notes).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Uses runtime lookup on the service module for get_collection so existing tests
that monkeypatch business_service.get_collection keep working.
"""
from app.modules.business import service as business_service


def _approval_queue_item(
    *,
    document_type: str,
    document_id: str,
    document_number: str,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_name: str | None,
    document_date,
    amount,
    status: str,
    approval_status: str | None,
    approval_required: bool | None,
    journal_entry_id,
    created_by,
    created_at,
    updated_at,
) -> dict:
    return {
        "document_type": document_type,
        "document_id": document_id,
        "document_number": document_number,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_name": party_name,
        "document_date": document_date,
        "amount": amount,
        "status": status,
        "approval_status": approval_status or "auto_posted",
        "approval_required": bool(approval_required),
        "journal_entry_id": journal_entry_id,
        "created_by": created_by,
        "created_at": created_at,
        "updated_at": updated_at,
    }


async def list_documents_for_approval_queue(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    document_type: str | None = None,
    status: str | None = None,
    approval_status: str | None = None,
    include_reviewed: bool = False,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    safe_limit = max(1, min(int(limit or 100), 500))

    collections = [
        (business_service.VOUCHERS_COLLECTION, "voucher"),
        (business_service.SALES_INVOICES_COLLECTION, "sales_invoice"),
        (business_service.PURCHASE_BILLS_COLLECTION, "purchase_bill"),
        (business_service.CREDIT_NOTES_COLLECTION, "credit_note"),
        (business_service.DEBIT_NOTES_COLLECTION, "debit_note"),
    ]
    if document_type:
        collections = [item for item in collections if item[1] == document_type]
    rows_by_type: dict[str, list[dict]] = {}
    for collection_name, doc_type in collections:
        rows = (
            await business_service.get_collection(collection_name)
            .find(filters)
            .sort("updated_at", -1)
            .limit(safe_limit)
            .to_list(length=safe_limit)
        )
        rows = [
            row for row in rows
            if str(row.get("status") or "").strip().lower() in {"posted", "pending_approval"}
        ]
        rows = [
            row for row in rows
            if bool(row.get("approval_required")) or str(row.get("approval_status") or "").strip().lower() in {"pending_approval", "approved", "rejected"}
        ]
        if status:
            rows = [row for row in rows if str(row.get("status") or "").strip().lower() == status]
        if approval_status:
            rows = [row for row in rows if str(row.get("approval_status") or "auto_posted").strip().lower() == approval_status]
        if not include_reviewed:
            rows = [row for row in rows if str(row.get("approval_status") or "auto_posted") != "approved"]
        rows_by_type[doc_type] = rows

    items: list[dict] = []
    for row in rows_by_type.get("voucher", []):
        items.append(
            _approval_queue_item(
                document_type="voucher",
                document_id=str(row.get("voucher_id") or ""),
                document_number=str(row.get("voucher_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=None,
                document_date=row.get("entry_date"),
                amount=row.get("amount"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("sales_invoice", []):
        items.append(
            _approval_queue_item(
                document_type="sales_invoice",
                document_id=str(row.get("invoice_id") or ""),
                document_number=str(row.get("invoice_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("customer_name"),
                document_date=row.get("invoice_date"),
                amount=row.get("invoice_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("purchase_bill", []):
        items.append(
            _approval_queue_item(
                document_type="purchase_bill",
                document_id=str(row.get("bill_id") or ""),
                document_number=str(row.get("bill_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("vendor_name"),
                document_date=row.get("bill_date"),
                amount=row.get("bill_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("credit_note", []):
        items.append(
            _approval_queue_item(
                document_type="credit_note",
                document_id=str(row.get("credit_note_id") or ""),
                document_number=str(row.get("credit_note_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("customer_name"),
                document_date=row.get("note_date"),
                amount=row.get("note_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )
    for row in rows_by_type.get("debit_note", []):
        items.append(
            _approval_queue_item(
                document_type="debit_note",
                document_id=str(row.get("debit_note_id") or ""),
                document_number=str(row.get("debit_note_number") or ""),
                tenant_id=tenant_id,
                app_key=app_key,
                accounting_entity_id=accounting_entity_id,
                party_name=row.get("vendor_name"),
                document_date=row.get("note_date"),
                amount=row.get("note_total"),
                status=str(row.get("status") or ""),
                approval_status=row.get("approval_status"),
                approval_required=row.get("approval_required"),
                journal_entry_id=row.get("journal_entry_id"),
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
                updated_at=row.get("updated_at"),
            )
        )

    items.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
    items = items[:safe_limit]
    return {"items": items, "total": len(items)}
