"""LegalMitra Stage 3 — practice dashboard aggregates."""
from __future__ import annotations

from app.modules.legal import practice_service as practice_svc
from app.modules.legal.practice_schemas import MatterStatus

_TERMINAL = {MatterStatus.CLOSED.value, MatterStatus.ARCHIVED.value}


async def get_practice_dashboard(
    *,
    tenant_id: str,
    app_key: str,
    limit: int = 5,
) -> dict:
    matters = practice_svc.get_collection(practice_svc.LEGAL_MATTERS_COLLECTION)
    clients = practice_svc.get_collection(practice_svc.LEGAL_CLIENTS_COLLECTION)
    documents = practice_svc.get_collection(
        practice_svc.LEGAL_MATTER_DOCUMENTS_COLLECTION
    )
    briefs = practice_svc.get_collection(practice_svc.LEGAL_MATTER_BRIEFS_COLLECTION)
    scope = practice_svc._scope(tenant_id=tenant_id, app_key=app_key)

    active_matters = await matters.count_documents(
        {**scope, "status": MatterStatus.ACTIVE.value}
    )
    pending_matters = await matters.count_documents(
        {**scope, "status": MatterStatus.PENDING.value}
    )
    draft_matters = await matters.count_documents(
        {**scope, "status": MatterStatus.DRAFT.value}
    )
    awaiting_review = int(pending_matters) + int(draft_matters)

    upcoming_hearings: list[dict] = []
    upcoming_deadlines: list[dict] = []
    recent_clients: list[dict] = []
    recent_briefs: list[dict] = []
    recent_documents: list[dict] = []

    hearing_rows = await matters.find(scope).sort("next_hearing_date", 1).limit(
        limit * 3
    ).to_list(length=limit * 3)
    for doc in hearing_rows:
        hearing = doc.get("next_hearing_date")
        if not hearing or doc.get("status") in _TERMINAL:
            continue
        upcoming_hearings.append(
            {
                "matter_id": doc["matter_id"],
                "matter_number": doc.get("matter_number"),
                "title": doc.get("title"),
                "next_hearing_date": hearing,
                "court": doc.get("court"),
                "status": doc.get("status"),
                "practice_area": doc.get("practice_area"),
            }
        )
        if len(upcoming_hearings) >= limit:
            break

    deadline_rows = await matters.find(scope).sort("next_deadline_date", 1).limit(
        limit * 3
    ).to_list(length=limit * 3)
    for doc in deadline_rows:
        deadline = doc.get("next_deadline_date")
        if not deadline or doc.get("status") in _TERMINAL:
            continue
        upcoming_deadlines.append(
            {
                "matter_id": doc["matter_id"],
                "matter_number": doc.get("matter_number"),
                "title": doc.get("title"),
                "next_deadline_date": deadline,
                "status": doc.get("status"),
                "practice_area": doc.get("practice_area"),
            }
        )
        if len(upcoming_deadlines) >= limit:
            break

    client_rows = await clients.find(scope).sort("created_at", -1).limit(limit).to_list(
        length=limit
    )
    for doc in client_rows:
        recent_clients.append(
            {
                "client_id": doc["client_id"],
                "display_name": doc.get("display_name"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
            }
        )

    brief_rows = await briefs.find(scope).sort("generated_at", -1).limit(limit).to_list(
        length=limit
    )
    for doc in brief_rows:
        sections = doc.get("sections") or {}
        recent_briefs.append(
            {
                "brief_id": doc["brief_id"],
                "matter_id": doc.get("matter_id"),
                "matter_number": doc.get("matter_number"),
                "practice_area": doc.get("practice_area"),
                "generated_at": doc.get("generated_at"),
                "confidence": sections.get("confidence"),
                "human_review_required": sections.get("human_review_required", True),
            }
        )

    doc_rows = await documents.find(scope).sort("created_at", -1).limit(limit).to_list(
        length=limit
    )
    for doc in doc_rows:
        recent_documents.append(
            {
                "document_id": doc["document_id"],
                "matter_id": doc.get("matter_id"),
                "filename": doc.get("filename"),
                "created_at": doc.get("created_at"),
            }
        )

    fees_outstanding = "—"
    try:
        from app.config import get_settings
        from app.modules.legal import billing_service

        if getattr(get_settings(), "LEGALMITRA_BILLING_ENABLED", True):
            summary = await billing_service.get_fee_summary(
                tenant_id=tenant_id, app_key=app_key
            )
            fees_outstanding = summary.get("fees_outstanding_display") or "₹0.00"
    except Exception:
        fees_outstanding = "—"

    doc_custody = None
    try:
        from app.modules.legal import custody_service

        custody = await custody_service.get_custody_settings(
            tenant_id=tenant_id, app_key=app_key
        )
        doc_custody = custody_service.dashboard_custody_summary(custody)
    except Exception:
        doc_custody = None

    return {
        "active_matters": int(active_matters),
        "pending_matters": int(pending_matters),
        "awaiting_review": awaiting_review,
        "upcoming_hearings": upcoming_hearings,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_clients": recent_clients,
        "recent_briefs": recent_briefs,
        "recent_documents": recent_documents,
        "fees_outstanding": fees_outstanding,
        "data_source": "live",
        "doc_custody": doc_custody,
    }
