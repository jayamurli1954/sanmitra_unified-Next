"""OfficeMitra Documents package (ADR-016): link Review notes to MitraBooks CA queue."""
from __future__ import annotations

from typing import Any

from app.modules.office_ai.connectors import mitrabooks_connector
from app.modules.office_ai.services import review_store


class DocumentsError(ValueError):
    """Base error for the Documents package."""


class DocumentsNotFoundError(DocumentsError):
    pass


def _book_id(engagement: dict[str, Any] | None, override: str | None = None) -> str:
    if override and str(override).strip():
        return str(override).strip()
    if engagement and engagement.get("accounting_entity_id"):
        return str(engagement.get("accounting_entity_id")).strip()
    return "primary"


async def list_queue(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    accounting_entity_id: str | None = None,
    engagement_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    engagement = None
    if engagement_id:
        engagement = await review_store.get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
        if engagement is None:
            raise DocumentsNotFoundError(f"Engagement not found: {engagement_id}")
    book_id = _book_id(engagement, accounting_entity_id)
    payload = await mitrabooks_connector.list_ca_staff_documents(
        tenant_id=tenant_id,
        tenant=tenant,
        accounting_entity_id=book_id,
        status=status,
        limit=limit,
    )
    linked: set[str] = set()
    if engagement_id:
        notes = await review_store.list_notes(tenant_id=tenant_id, engagement_id=engagement_id)
        linked = {str(note.get("ca_document_id") or "").strip() for note in notes if note.get("ca_document_id")}
        linked.discard("")
    items = []
    for row in payload.get("items") or []:
        document_id = str(row.get("document_id") or "").strip()
        items.append({**row, "linked_to_review_note": document_id in linked})
    return {
        "enabled": bool(payload.get("enabled")),
        "reason": payload.get("reason"),
        "error": payload.get("error"),
        "source": payload.get("source"),
        "accounting_entity_id": book_id,
        "items": items,
        "count": len(items),
        "client_portal": False,
        "companion_writes": False,
        "adr_016": "accepted",
    }


async def link_note(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    user: dict[str, Any],
    note_id: str,
    document_id: str,
) -> dict[str, Any]:
    note = await review_store.get_note(tenant_id=tenant_id, note_id=note_id)
    if note is None:
        raise DocumentsNotFoundError(f"Review note not found: {note_id}")
    engagement = await review_store.get_engagement(
        tenant_id=tenant_id, engagement_id=str(note.get("engagement_id") or "")
    )
    book_id = _book_id(engagement)
    doc_id = str(document_id or "").strip()
    if not doc_id:
        raise DocumentsError("document_id is required")
    document = await mitrabooks_connector.get_ca_staff_document(
        tenant_id=tenant_id,
        tenant=tenant,
        document_id=doc_id,
        accounting_entity_id=book_id,
    )
    if document is None:
        raise DocumentsNotFoundError(f"CA document not found: {doc_id}")
    updated = await review_store.update_note(
        tenant_id=tenant_id,
        note_id=note_id,
        user=user,
        updates={"ca_document_id": doc_id},
    )
    return {"item": updated, "document": document}


async def unlink_note(
    *,
    tenant_id: str,
    user: dict[str, Any],
    note_id: str,
) -> dict[str, Any]:
    note = await review_store.get_note(tenant_id=tenant_id, note_id=note_id)
    if note is None:
        raise DocumentsNotFoundError(f"Review note not found: {note_id}")
    updated = await review_store.update_note(
        tenant_id=tenant_id,
        note_id=note_id,
        user=user,
        updates={"ca_document_id": None},
    )
    return {"item": updated}
