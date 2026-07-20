"""Business document attachment service (upload / list / download).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Storage path and attachment policy constants remain on service.py so existing
tests that monkeypatch BUSINESS_ATTACHMENT_STORAGE_DIR / get_collection keep
working via runtime lookup on the service module.
"""
from pathlib import Path
from uuid import uuid4

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.modules.business import service as business_service


def _safe_attachment_file_name(file_name: str | None) -> str:
    raw = str(file_name or "attachment").strip().replace("\\", " ").replace("/", " ")
    cleaned = "".join(ch for ch in raw if ch >= " " and ch != "\x7f").strip().strip(".")
    return cleaned[:240] or "attachment"


def _normalize_attachment_content_type(content_type: str | None) -> str:
    return str(content_type or "").split(";")[0].strip().lower()


def _business_attachment_response_doc(doc: dict) -> dict:
    result = business_service._json_safe_doc(doc)
    result.pop("stored_file_path", None)
    return result


async def _get_business_attachment_owner(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
) -> tuple[dict, str]:
    normalized_owner_type = str(owner_type or "").strip().lower()
    owner_filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if normalized_owner_type == "sales_invoice":
        owner = await business_service.get_collection(business_service.SALES_INVOICES_COLLECTION).find_one(
            {**owner_filters, "invoice_id": owner_id}
        )
        if owner is None:
            raise AccountingNotFoundError("Sales invoice not found")
        return owner, "invoice_id"
    if normalized_owner_type == "purchase_bill":
        owner = await business_service.get_collection(business_service.PURCHASE_BILLS_COLLECTION).find_one(
            {**owner_filters, "bill_id": owner_id}
        )
        if owner is None:
            raise AccountingNotFoundError("Purchase bill not found")
        return owner, "bill_id"
    if normalized_owner_type == "ca_document":
        owner = await business_service.get_collection(business_service.CA_DOCUMENTS_COLLECTION).find_one(
            {**owner_filters, "document_id": owner_id}
        )
        if owner is None:
            raise AccountingNotFoundError("CA document metadata not found")
        return owner, "document_id"
    raise AccountingValidationError(f"Unsupported business attachment owner type: {owner_type}")


async def create_business_document_attachment(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    uploaded_by: str,
    file_name: str,
    content_type: str | None,
    payload: bytes,
) -> dict:
    normalized_content_type = _normalize_attachment_content_type(content_type)
    if normalized_content_type not in business_service.ALLOWED_BUSINESS_ATTACHMENT_TYPES:
        raise AccountingValidationError(f"Unsupported attachment type: {normalized_content_type or 'unknown'}")
    if not payload:
        raise AccountingValidationError("Uploaded file is empty")
    if len(payload) > business_service.MAX_BUSINESS_ATTACHMENT_BYTES:
        raise AccountingValidationError("Attachment file exceeds the 10 MB limit")
    safe_name = _safe_attachment_file_name(file_name)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in business_service.ALLOWED_BUSINESS_ATTACHMENT_TYPES[normalized_content_type]:
        raise AccountingValidationError("Attachment filename extension does not match the supplied content type")

    owner, _owner_key = await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )

    attachment_id = str(uuid4())
    now = business_service._now()
    stored_file_path = (
        business_service.BUSINESS_ATTACHMENT_STORAGE_DIR
        / tenant_id
        / app_key
        / accounting_entity_id
        / f"{attachment_id}{suffix}"
    )
    stored_file_path.parent.mkdir(parents=True, exist_ok=True)
    stored_file_path.write_bytes(payload)

    doc = {
        "attachment_id": attachment_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "owner_type": str(owner_type).strip().lower(),
        "owner_id": owner_id,
        "file_name": safe_name,
        "content_type": normalized_content_type,
        "size_bytes": len(payload),
        "stored_file_path": str(stored_file_path),
        "uploaded_by": uploaded_by,
        "uploaded_at": now,
        "created_at": now,
        "updated_at": now,
    }
    await business_service.get_collection(business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION).insert_one(doc)
    if str(owner_type).strip().lower() == "ca_document":
        attachment_count = await business_service.get_collection(
            business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION
        ).count_documents(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "owner_type": "ca_document",
                "owner_id": owner_id,
            }
        )
        await business_service.get_collection(business_service.CA_DOCUMENTS_COLLECTION).update_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "document_id": owner_id,
            },
            {
                "$set": {
                    "attachment_count": attachment_count,
                    "last_attachment_at": now,
                    "updated_at": now,
                }
            },
        )
    result = _business_attachment_response_doc(doc)
    await business_service._audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=uploaded_by,
        action="business_document_attachment_uploaded",
        entity_type="business_document_attachment",
        entity_id=attachment_id,
        new_value=result,
    )
    return result


async def list_business_document_attachments(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    limit: int = 100,
) -> dict:
    await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await business_service.get_collection(business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION)
        .find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": accounting_entity_id,
                "owner_type": str(owner_type).strip().lower(),
                "owner_id": owner_id,
            }
        )
        .sort("uploaded_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_business_attachment_response_doc(row) for row in rows], "total": len(rows)}


async def download_business_document_attachment(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    owner_type: str,
    owner_id: str,
    attachment_id: str,
    downloaded_by: str,
) -> dict:
    await _get_business_attachment_owner(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    doc = await business_service.get_collection(business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "owner_type": str(owner_type).strip().lower(),
            "owner_id": owner_id,
            "attachment_id": attachment_id,
        }
    )
    if doc is None:
        raise AccountingNotFoundError("Business document attachment not found")
    stored_file_path = Path(str(doc.get("stored_file_path") or "")).resolve()
    try:
        payload = stored_file_path.read_bytes()
    except FileNotFoundError as exc:
        raise AccountingNotFoundError("Business document attachment file is missing") from exc
    result = _business_attachment_response_doc(doc)
    await business_service._audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=downloaded_by,
        action="business_document_attachment_downloaded",
        entity_type="business_document_attachment",
        entity_id=attachment_id,
        new_value=result,
    )
    return {**result, "payload": payload}
