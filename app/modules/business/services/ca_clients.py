"""CA client and CA document-metadata service functions.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Imported via the service.py facade (which re-exports the public functions).
"""
from uuid import uuid4

from app.accounting.service import AccountingValidationError
from app.db.mongo import get_collection
from app.modules.business.schemas import (
    CaClientCreateRequest,
    CaClientUpdateRequest,
    CaDocumentCreateRequest,
    CaDocumentUpdateRequest,
)
from app.modules.business.service import (
    CA_CLIENTS_COLLECTION,
    CA_DOCUMENT_DEFAULT_NEXT_ACTION,
    CA_DOCUMENTS_COLLECTION,
    _audit_business_event,
    _json_safe_doc,
    _now,
)


async def _get_ca_client_in_scope(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    client_id: str,
) -> dict:
    client = await get_collection(CA_CLIENTS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "client_id": client_id,
            "active": True,
        }
    )
    if client is None:
        raise AccountingValidationError("CA client is not active in this tenant book")
    return client


def _ca_document_response_doc(doc: dict) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("book_id", result.get("accounting_entity_id"))
    result.setdefault("client_id", None)
    result.setdefault("next_action", CA_DOCUMENT_DEFAULT_NEXT_ACTION.get(str(result.get("status") or "uploaded"), "Review document metadata"))
    result.setdefault("client_owner", None)
    result.setdefault("priority", "normal")
    result.setdefault("due_date", None)
    result.setdefault("compliance_area", None)
    result.setdefault("client_access_enabled", False)
    result.setdefault("attachment_count", 0)
    result.setdefault("review_started_at", None)
    result.setdefault("review_started_by", None)
    result.setdefault("query_raised_at", None)
    result.setdefault("query_raised_by", None)
    result.setdefault("reviewed_at", None)
    result.setdefault("reviewed_by", None)
    result.setdefault("posted_at", None)
    result.setdefault("posted_by", None)
    return result


def _ca_client_response_doc(doc: dict) -> dict:
    result = _json_safe_doc(doc)
    result.setdefault("gstin", None)
    result.setdefault("pan", None)
    result.setdefault("contact_person", None)
    result.setdefault("contact_email", None)
    result.setdefault("contact_phone", None)
    result.setdefault("engagement_type", None)
    result.setdefault("assigned_to", None)
    result.setdefault("client_owner", None)
    result.setdefault("access_level", "view_only")
    result.setdefault("compliance_tracks", [])
    result.setdefault("notes", None)
    result.setdefault("active", True)
    return result


async def create_ca_client(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    payload: CaClientCreateRequest,
) -> dict:
    client_id = str(uuid4())
    now = _now()
    doc = {
        "client_id": client_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "client_name": payload.client_name.strip(),
        "gstin": payload.gstin.strip() if payload.gstin else None,
        "pan": payload.pan.strip() if payload.pan else None,
        "contact_person": payload.contact_person.strip() if payload.contact_person else None,
        "contact_email": payload.contact_email.strip() if payload.contact_email else None,
        "contact_phone": payload.contact_phone.strip() if payload.contact_phone else None,
        "engagement_type": payload.engagement_type.strip() if payload.engagement_type else None,
        "assigned_to": payload.assigned_to.strip() if payload.assigned_to else None,
        "client_owner": payload.client_owner.strip() if payload.client_owner else None,
        "access_level": payload.access_level,
        "compliance_tracks": [str(item).strip() for item in payload.compliance_tracks if str(item).strip()],
        "notes": payload.notes.strip() if payload.notes else None,
        "active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(CA_CLIENTS_COLLECTION).insert_one(doc)
    result = _ca_client_response_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_ca_client_created",
        entity_type="business_ca_client",
        entity_id=client_id,
        new_value=result,
    )
    return result


async def list_ca_clients(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    q: str | None = None,
    active_only: bool = True,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if active_only:
        filters["active"] = True
    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(CA_CLIENTS_COLLECTION)
        .find(filters)
        .sort("client_name", 1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    if q:
        needle = q.strip().lower()
        rows = [
            row for row in rows
            if needle in str(row.get("client_name") or "").lower()
            or needle in str(row.get("gstin") or "").lower()
            or needle in str(row.get("contact_person") or "").lower()
        ]
    return {"items": [_ca_client_response_doc(row) for row in rows], "total": len(rows)}


async def update_ca_client(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    client_id: str,
    updated_by: str,
    payload: CaClientUpdateRequest,
) -> dict | None:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "client_id": client_id,
    }
    collection = get_collection(CA_CLIENTS_COLLECTION)
    existing = await collection.find_one(filters)
    if existing is None:
        return None
    patch = payload.model_dump(exclude_unset=True)
    patch.pop("accounting_entity_id", None)
    if "compliance_tracks" in patch and patch["compliance_tracks"] is not None:
        patch["compliance_tracks"] = [str(item).strip() for item in patch["compliance_tracks"] if str(item).strip()]
    for key in ("client_name", "gstin", "pan", "contact_person", "contact_email", "contact_phone", "engagement_type", "assigned_to", "client_owner", "notes"):
        if key in patch and patch[key] is not None:
            patch[key] = str(patch[key]).strip() or None
    patch["updated_by"] = updated_by
    patch["updated_at"] = _now()
    await collection.update_one(filters, {"$set": patch})
    updated = await collection.find_one(filters)
    result = _ca_client_response_doc(updated)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_ca_client_updated",
        entity_type="business_ca_client",
        entity_id=client_id,
        old_value=_ca_client_response_doc(existing),
        new_value=result,
    )
    return result


async def create_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    payload: CaDocumentCreateRequest,
) -> dict:
    document_id = str(uuid4())
    now = _now()
    client = None
    client_id = str(payload.client_id or "").strip() or None
    if client_id:
        client = await _get_ca_client_in_scope(
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            client_id=client_id,
        )
    client_name = str((client or {}).get("client_name") or payload.client_name).strip()
    doc = {
        "document_id": document_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "book_id": accounting_entity_id,
        "client_id": client_id,
        "client_name": client_name,
        "document_type": payload.document_type.strip(),
        "period": payload.period.strip(),
        "status": "uploaded",
        "assigned_to": payload.assigned_to.strip() if payload.assigned_to else ((client or {}).get("assigned_to") or None),
        "client_owner": payload.client_owner.strip() if payload.client_owner else ((client or {}).get("client_owner") or None),
        "priority": payload.priority,
        "due_date": payload.due_date.strip() if payload.due_date else None,
        "compliance_area": payload.compliance_area.strip() if payload.compliance_area else None,
        "client_access_enabled": bool(payload.client_access_enabled),
        "original_file_name": payload.original_file_name.strip() if payload.original_file_name else None,
        "attachment_count": 0,
        "last_attachment_at": None,
        "next_action": CA_DOCUMENT_DEFAULT_NEXT_ACTION["uploaded"],
        "posting_reference": None,
        "notes": payload.notes.strip() if payload.notes else None,
        "review_started_at": None,
        "review_started_by": None,
        "query_raised_at": None,
        "query_raised_by": None,
        "reviewed_at": None,
        "reviewed_by": None,
        "posted_at": None,
        "posted_by": None,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(CA_DOCUMENTS_COLLECTION).insert_one(doc)
    result = _ca_document_response_doc(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_ca_document_metadata_created",
        entity_type="business_ca_document_metadata",
        entity_id=document_id,
        new_value=result,
    )
    return result


async def list_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    status: str | None = None,
    client_name: str | None = None,
    assigned_to: str | None = None,
    priority: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if status:
        filters["status"] = status
    if assigned_to:
        filters["assigned_to"] = assigned_to
    if priority:
        filters["priority"] = priority

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(CA_DOCUMENTS_COLLECTION)
        .find(filters)
        .sort("updated_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    if client_name:
        normalized_client = client_name.strip().lower()
        rows = [
            row
            for row in rows
            if normalized_client in str(row.get("client_name") or "").lower()
        ]
    return {"items": [_ca_document_response_doc(row) for row in rows], "total": len(rows)}


async def update_ca_document_metadata(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    document_id: str,
    updated_by: str,
    payload: CaDocumentUpdateRequest,
) -> dict | None:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "document_id": document_id,
    }
    collection = get_collection(CA_DOCUMENTS_COLLECTION)
    existing = await collection.find_one(filters)
    if existing is None:
        return None

    patch = payload.model_dump(exclude_unset=True)
    patch.pop("accounting_entity_id", None)
    patch.pop("client_id", None)
    patch = {key: value for key, value in patch.items() if value is not None}
    status = patch.get("status")
    now = _now()
    if status and not patch.get("next_action"):
        patch["next_action"] = CA_DOCUMENT_DEFAULT_NEXT_ACTION.get(str(status), "Review document metadata")
    if status == "under_review" and existing.get("review_started_at") is None:
        patch["review_started_at"] = now
        patch["review_started_by"] = updated_by
    if status == "query_raised":
        patch["query_raised_at"] = now
        patch["query_raised_by"] = updated_by
    if status == "reviewed":
        patch["reviewed_at"] = now
        patch["reviewed_by"] = updated_by
    if status == "posted":
        patch["posted_at"] = now
        patch["posted_by"] = updated_by
        if existing.get("reviewed_at") is None:
            patch["reviewed_at"] = now
            patch["reviewed_by"] = updated_by
    patch["updated_by"] = updated_by
    patch["updated_at"] = now

    await collection.update_one(filters, {"$set": patch})
    updated = await collection.find_one(filters)
    result = _ca_document_response_doc(updated)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_ca_document_metadata_updated",
        entity_type="business_ca_document_metadata",
        entity_id=document_id,
        old_value=_ca_document_response_doc(existing),
        new_value=result,
    )
    return result
