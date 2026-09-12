"""OfficeMitra Documents package (ADR-016/017): CA queue links + staff missing-doc requests."""
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


EXPECTED_REVIEW_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("bank_statement", "Bank statement"),
    ("gst_returns", "GST returns working"),
    ("tds_challans", "TDS challans"),
    ("trial_balance", "Trial balance"),
    ("receivable_ageing", "AR ageing"),
)


def expected_document_label(document_type: str) -> str:
    key = str(document_type or "").strip().lower()
    for code, label in EXPECTED_REVIEW_DOCUMENTS:
        if code == key:
            return label
    return key.replace("_", " ").strip() or "document"


async def gap_report(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    accounting_entity_id: str | None = None,
    engagement_id: str | None = None,
) -> dict[str, Any]:
    queue = await list_queue(
        tenant_id=tenant_id,
        tenant=tenant,
        accounting_entity_id=accounting_entity_id,
        engagement_id=engagement_id,
        limit=500,
    )
    period = ""
    if engagement_id:
        engagement = await review_store.get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
        period = str((engagement or {}).get("period") or "").strip()
    rows = list(queue.get("items") or [])
    if period:
        rows = [row for row in rows if str(row.get("period") or "").strip() == period]
    present = {
        str(row.get("document_type") or "").strip().lower()
        for row in rows
        if str(row.get("document_type") or "").strip()
    }
    items = []
    for code, label in EXPECTED_REVIEW_DOCUMENTS:
        items.append(
            {
                "document_type": code,
                "label": label,
                "present": code in present,
            }
        )
    missing = [row for row in items if not row["present"]]
    return {
        **{k: queue.get(k) for k in ("enabled", "reason", "error", "source", "accounting_entity_id")},
        "period": period or None,
        "items": items,
        "missing": missing,
        "missing_count": len(missing),
        "client_portal": False,
        "client_email": False,
        "adr_017": "accepted",
    }


async def create_staff_request(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    user: dict[str, Any],
    document_type: str,
    engagement_id: str | None = None,
    accounting_entity_id: str | None = None,
) -> dict[str, Any]:
    from app.modules.office_ai.services import notification_service, task_service

    code = str(document_type or "").strip().lower()
    allowed = {item[0] for item in EXPECTED_REVIEW_DOCUMENTS}
    if code not in allowed:
        raise DocumentsError(f"Unknown expected document type: {code}")
    gaps = await gap_report(
        tenant_id=tenant_id,
        tenant=tenant,
        accounting_entity_id=accounting_entity_id,
        engagement_id=engagement_id,
    )
    if any(row["document_type"] == code and row["present"] for row in gaps.get("items") or []):
        raise DocumentsError(f"{expected_document_label(code)} is already on the CA queue")
    existing = await task_service.find_open_missing_document_task(
        tenant_id=tenant_id,
        document_type=code,
        engagement_id=engagement_id,
    )
    if existing:
        return {"item": existing, "created": False, "note": None, "client_email": False}
    period = ""
    if engagement_id:
        engagement = await review_store.get_engagement(tenant_id=tenant_id, engagement_id=engagement_id)
        if engagement is None:
            raise DocumentsNotFoundError(f"Engagement not found: {engagement_id}")
        period = str(engagement.get("period") or "")
    label = expected_document_label(code)
    title = f"Missing document: {label}" + (f" ({period})" if period else "")
    if gaps.get("enabled") is False:
        body = (
            f"Staff request for {label}. MitraBooks CA Practice is not active "
            f"({gaps.get('reason') or 'business_module_off'}). This is an internal reminder only. "
            "Do not email the client from OfficeMitra."
        )
    else:
        body = (
            f"Staff request for {label}. Upload it in MitraBooks CA Practice (ca-access). "
            "Do not email the client from OfficeMitra."
        )
    task = await task_service.create_task(
        tenant_id=tenant_id,
        user=user,
        title=title[:500],
        notes=body,
        source="manual",
        kind="missing_document",
        document_type=code,
        engagement_id=engagement_id,
    )
    note = None
    from app.core.modules.registry import is_office_ai_review_notes_enabled

    if engagement_id and is_office_ai_review_notes_enabled(
        enabled_modules=tenant.get("enabled_modules") or [],
        office_ai_features=tenant.get("office_ai_features"),
    ):
        note = await review_store.create_note(
            tenant_id=tenant_id,
            engagement_id=engagement_id,
            user=user,
            description=body,
            task_id=str(task.get("id") or ""),
        )
    await notification_service.create_notification(
        tenant_id=tenant_id,
        user=user,
        title=title[:200],
        body=body[:400],
        kind="missing_document_request",
        href="/business/office-ai",
        dedupe_key=f"missing_doc:{tenant_id}:{engagement_id or 'none'}:{code}",
    )
    return {"item": task, "created": True, "note": note, "client_email": False}

