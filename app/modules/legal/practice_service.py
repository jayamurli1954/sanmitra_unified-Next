"""LegalMitra Stage 3 practice data: clients, matters, documents, timeline, briefs, dashboard.

All collections are tenant-scoped (tenant_id + app_key). Mutations write to core audit logs.
Matter briefs are grounded summaries with advisory limitations — not final legal advice.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo import ReturnDocument

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal.practice_schemas import (
    ALLOWED_STATUS_TRANSITIONS,
    MATTER_STATUS_VALUES,
    PRACTICE_AREA_PREFIXES,
    ClientCreateRequest,
    ClientUpdateRequest,
    MatterBriefGenerateRequest,
    MatterCreateRequest,
    MatterDocumentCreateRequest,
    MatterStatus,
    MatterUpdateRequest,
    TimelineEventCreateRequest,
)

LEGAL_CLIENTS_COLLECTION = "legal_clients"
LEGAL_MATTERS_COLLECTION = "legal_matters"
LEGAL_MATTER_DOCUMENTS_COLLECTION = "legal_matter_documents"
LEGAL_MATTER_TIMELINE_COLLECTION = "legal_matter_timeline"
LEGAL_MATTER_BRIEFS_COLLECTION = "legal_matter_briefs"
LEGAL_PRACTICE_COUNTERS_COLLECTION = "legal_practice_counters"

DEFAULT_APP_KEY = "legalmitra"

ADVISORY_NOTICE = (
    "This Matter Intelligence Brief is an advisory working summary generated from "
    "tenant practice records. It is not final legal advice. A qualified professional "
    "must review before filing, advising a client, or taking any binding action."
)


class PracticeConflictError(Exception):
    """Raised on uniqueness or conflict failures."""


class PracticeNotFoundError(Exception):
    """Raised when a scoped entity is missing."""


class PracticeValidationError(Exception):
    """Raised for invalid lifecycle or payload rules."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


def _parse_optional_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value)
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def _date_to_iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


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
            product=app_key or "legalmitra",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        # Best-effort: domain write already succeeded.
        pass


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


async def ensure_practice_indexes() -> None:
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    await clients.create_index(
        [("tenant_id", 1), ("app_key", 1), ("client_id", 1)], unique=True
    )
    await clients.create_index(
        [("tenant_id", 1), ("app_key", 1), ("status", 1), ("created_at", -1)]
    )
    await clients.create_index(
        [("tenant_id", 1), ("app_key", 1), ("display_name", 1)]
    )

    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1)], unique=True
    )
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_number", 1)], unique=True
    )
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("client_id", 1), ("created_at", -1)]
    )
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("status", 1), ("updated_at", -1)]
    )
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("next_hearing_date", 1)]
    )
    await matters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("next_deadline_date", 1)]
    )

    documents = get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION)
    await documents.create_index(
        [("tenant_id", 1), ("app_key", 1), ("document_id", 1)], unique=True
    )
    await documents.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("created_at", -1)]
    )

    timeline = get_collection(LEGAL_MATTER_TIMELINE_COLLECTION)
    await timeline.create_index(
        [("tenant_id", 1), ("app_key", 1), ("event_id", 1)], unique=True
    )
    await timeline.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("occurred_at", -1)]
    )

    briefs = get_collection(LEGAL_MATTER_BRIEFS_COLLECTION)
    await briefs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("brief_id", 1)], unique=True
    )
    await briefs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("generated_at", -1)]
    )

    counters = get_collection(LEGAL_PRACTICE_COUNTERS_COLLECTION)
    await counters.create_index(
        [("tenant_id", 1), ("app_key", 1), ("key", 1)], unique=True
    )


async def _next_matter_number(
    *,
    tenant_id: str,
    app_key: str,
    practice_area: str | None,
) -> str:
    """Atomic per-tenant sequence → e.g. LM-2026-000001 or GST-2026-000034."""
    year = _now().year
    area_key = (practice_area or "general").strip().lower().replace(" ", "_")
    prefix = PRACTICE_AREA_PREFIXES.get(area_key, "LM")
    counter_key = f"matter_number:{prefix}:{year}"

    counters = get_collection(LEGAL_PRACTICE_COUNTERS_COLLECTION)
    doc = await counters.find_one_and_update(
        {"tenant_id": tenant_id, "app_key": app_key, "key": counter_key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(doc["seq"])
    return f"{prefix}-{year}-{seq:06d}"


def _validate_status_transition(*, current: str, new: str) -> None:
    if current == new:
        return
    if new not in MATTER_STATUS_VALUES:
        raise PracticeValidationError(f"Invalid matter status: {new}")
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise PracticeValidationError(
            f"Matter status transition not allowed: {current} → {new}"
        )


def _matter_response(doc: dict, *, client_name: str | None = None) -> dict:
    return {
        "matter_id": doc["matter_id"],
        "matter_number": doc["matter_number"],
        "tenant_id": doc["tenant_id"],
        "app_key": doc["app_key"],
        "client_id": doc["client_id"],
        "client_name": client_name if client_name is not None else doc.get("client_name"),
        "title": doc["title"],
        "matter_type": doc.get("matter_type", "engagement"),
        "status": doc["status"],
        "jurisdiction": doc.get("jurisdiction"),
        "description": doc.get("description"),
        "assigned_users": list(doc.get("assigned_users") or []),
        "tags": list(doc.get("tags") or []),
        "priority": doc.get("priority") or "normal",
        "practice_area": doc.get("practice_area"),
        "court": doc.get("court"),
        "opposite_party": doc.get("opposite_party"),
        "billing_reference": doc.get("billing_reference"),
        "next_hearing_date": _parse_optional_date(doc.get("next_hearing_date")),
        "next_deadline_date": _parse_optional_date(doc.get("next_deadline_date")),
        "created_by": doc.get("created_by", "system"),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
        "archived_at": doc.get("archived_at"),
    }


# ── Clients ──────────────────────────────────────────────────────────────────


async def create_client(
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: ClientCreateRequest,
) -> dict:
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    client_id = str(uuid4())
    now = _now()
    doc = {
        "client_id": client_id,
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "display_name": payload.display_name.strip(),
        "client_type": payload.client_type,
        "email": (payload.email or "").strip() or None,
        "phone": (payload.phone or "").strip() or None,
        "pan": payload.pan,
        "gstin": payload.gstin,
        "address": (payload.address or "").strip() or None,
        "notes": (payload.notes or "").strip() or None,
        "status": payload.status,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await clients.insert_one(doc)
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="legal_client_created",
        entity_type="legal_client",
        entity_id=client_id,
        new_value={"display_name": doc["display_name"], "status": doc["status"]},
    )
    return _serialize(doc)


async def list_clients(
    *,
    tenant_id: str,
    app_key: str,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if status:
        flt["status"] = status
    rows = await clients.find(flt).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [_serialize(doc) for doc in rows]


async def get_client(
    *,
    tenant_id: str,
    app_key: str,
    client_id: str,
) -> dict:
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    doc = await clients.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "client_id": client_id}
    )
    if doc is None:
        raise PracticeNotFoundError("Client not found")
    return _serialize(doc)


async def update_client(
    *,
    tenant_id: str,
    app_key: str,
    client_id: str,
    updated_by: str,
    payload: ClientUpdateRequest,
) -> dict:
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    existing = await clients.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "client_id": client_id}
    )
    if existing is None:
        raise PracticeNotFoundError("Client not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _serialize(existing)

    for key in ("display_name", "email", "phone", "address", "notes"):
        if key in updates and isinstance(updates[key], str):
            updates[key] = updates[key].strip() or None

    updates["updated_at"] = _now()
    await clients.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "client_id": client_id},
        {"$set": updates},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="legal_client_updated",
        entity_type="legal_client",
        entity_id=client_id,
        old_value={"display_name": existing.get("display_name"), "status": existing.get("status")},
        new_value={k: updates[k] for k in updates if k != "updated_at"},
    )
    refreshed = await clients.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "client_id": client_id}
    )
    return _serialize(refreshed or {**existing, **updates})


# ── Timeline helpers ─────────────────────────────────────────────────────────


async def _append_timeline_event(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    actor_id: str,
    event_type: str,
    summary: str,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
) -> dict:
    timeline = get_collection(LEGAL_MATTER_TIMELINE_COLLECTION)
    now = _now()
    event = {
        "event_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter_id,
        "event_type": event_type,
        "summary": summary,
        "actor_id": actor_id,
        "occurred_at": occurred_at or now,
        "payload": payload or {},
        "created_at": now,
    }
    await timeline.insert_one(event)
    return _serialize(event)


# ── Matters ──────────────────────────────────────────────────────────────────


async def create_matter(
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: MatterCreateRequest,
) -> dict:
    client = await get_client(
        tenant_id=tenant_id, app_key=app_key, client_id=payload.client_id
    )
    status = payload.status.value if isinstance(payload.status, MatterStatus) else str(payload.status)
    if status not in MATTER_STATUS_VALUES:
        raise PracticeValidationError(f"Invalid matter status: {status}")

    matter_id = str(uuid4())
    matter_number = await _next_matter_number(
        tenant_id=tenant_id,
        app_key=app_key,
        practice_area=payload.practice_area,
    )
    now = _now()
    doc = {
        "matter_id": matter_id,
        "matter_number": matter_number,
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "client_id": payload.client_id,
        "client_name": client.get("display_name"),
        "title": payload.title.strip(),
        "matter_type": payload.matter_type.strip(),
        "status": status,
        "jurisdiction": (payload.jurisdiction or "").strip() or None,
        "description": (payload.description or "").strip() or None,
        "assigned_users": list(payload.assigned_users or []),
        "tags": list(payload.tags or []),
        "priority": payload.priority,
        "practice_area": (payload.practice_area or "").strip() or None,
        "court": (payload.court or "").strip() or None,
        "opposite_party": (payload.opposite_party or "").strip() or None,
        "billing_reference": (payload.billing_reference or "").strip() or None,
        "next_hearing_date": _date_to_iso(payload.next_hearing_date),
        "next_deadline_date": _date_to_iso(payload.next_deadline_date),
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "archived_at": now if status == MatterStatus.ARCHIVED.value else None,
    }
    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    await matters.insert_one(doc)

    await _append_timeline_event(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        actor_id=created_by,
        event_type="matter_created",
        summary=f"Matter {matter_number} created: {doc['title']}",
        payload={"status": status, "client_id": payload.client_id},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="legal_matter_created",
        entity_type="legal_matter",
        entity_id=matter_id,
        new_value={
            "matter_number": matter_number,
            "title": doc["title"],
            "status": status,
            "client_id": payload.client_id,
        },
    )
    return _matter_response(doc)


async def list_matters(
    *,
    tenant_id: str,
    app_key: str,
    client_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if client_id:
        flt["client_id"] = client_id
    if status:
        flt["status"] = status
    rows = await matters.find(flt).sort("updated_at", -1).limit(limit).to_list(length=limit)
    return [_matter_response(doc) for doc in rows]


async def get_matter(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
) -> dict:
    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    doc = await matters.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
    )
    if doc is None:
        raise PracticeNotFoundError("Matter not found")
    return _matter_response(doc)


async def update_matter(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    updated_by: str,
    payload: MatterUpdateRequest,
) -> dict:
    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    existing = await matters.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
    )
    if existing is None:
        raise PracticeNotFoundError("Matter not found")

    if existing.get("status") == MatterStatus.ARCHIVED.value:
        # Allow only reopen to active via explicit status change; otherwise read-only.
        updates_preview = payload.model_dump(exclude_unset=True)
        new_status = updates_preview.get("status")
        if new_status is not None:
            new_status = new_status.value if isinstance(new_status, MatterStatus) else str(new_status)
        if new_status != MatterStatus.ACTIVE.value:
            raise PracticeValidationError("Archived matters are read-only")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _matter_response(existing)

    if "status" in updates:
        new_status = updates["status"]
        if isinstance(new_status, MatterStatus):
            new_status = new_status.value
        _validate_status_transition(current=existing["status"], new=new_status)
        updates["status"] = new_status
        if new_status == MatterStatus.ARCHIVED.value:
            updates["archived_at"] = _now()
        elif existing.get("status") == MatterStatus.ARCHIVED.value:
            updates["archived_at"] = None

    for key in (
        "title",
        "matter_type",
        "jurisdiction",
        "description",
        "practice_area",
        "court",
        "opposite_party",
        "billing_reference",
    ):
        if key in updates and isinstance(updates[key], str):
            updates[key] = updates[key].strip() or None

    if "next_hearing_date" in updates:
        updates["next_hearing_date"] = _date_to_iso(updates["next_hearing_date"])
    if "next_deadline_date" in updates:
        updates["next_deadline_date"] = _date_to_iso(updates["next_deadline_date"])

    updates["updated_at"] = _now()
    await matters.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id},
        {"$set": updates},
    )

    if "status" in updates and updates["status"] != existing.get("status"):
        await _append_timeline_event(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            actor_id=updated_by,
            event_type="status_changed",
            summary=f"Status changed from {existing.get('status')} to {updates['status']}",
            payload={"from": existing.get("status"), "to": updates["status"]},
        )
        if updates["status"] == MatterStatus.CLOSED.value:
            await _append_timeline_event(
                tenant_id=tenant_id,
                app_key=app_key,
                matter_id=matter_id,
                actor_id=updated_by,
                event_type="matter_closed",
                summary=f"Matter {existing.get('matter_number')} closed",
            )
    else:
        await _append_timeline_event(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            actor_id=updated_by,
            event_type="matter_updated",
            summary="Matter details updated",
            payload={"fields": [k for k in updates if k != "updated_at"]},
        )

    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="legal_matter_updated",
        entity_type="legal_matter",
        entity_id=matter_id,
        old_value={"status": existing.get("status"), "title": existing.get("title")},
        new_value={k: updates[k] for k in updates if k != "updated_at"},
    )
    refreshed = await matters.find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
    )
    return _matter_response(refreshed or {**existing, **updates})


# ── Documents ────────────────────────────────────────────────────────────────


async def attach_matter_document(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    created_by: str,
    payload: MatterDocumentCreateRequest,
) -> dict:
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    documents = get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION)
    now = _now()
    doc = {
        "document_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter_id,
        "filename": payload.filename.strip(),
        "doc_type": payload.doc_type.strip(),
        "notes": (payload.notes or "").strip() or None,
        "storage_ref": (payload.storage_ref or "").strip() or None,
        "ai_generated": bool(payload.ai_generated),
        "human_review_required": bool(payload.human_review_required),
        "created_by": created_by,
        "created_at": now,
    }
    await documents.insert_one(doc)
    await _append_timeline_event(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        actor_id=created_by,
        event_type="document_uploaded",
        summary=f"Document uploaded: {doc['filename']}",
        payload={"document_id": doc["document_id"], "doc_type": doc["doc_type"]},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="legal_matter_document_attached",
        entity_type="legal_matter_document",
        entity_id=doc["document_id"],
        new_value={"matter_id": matter_id, "filename": doc["filename"]},
    )
    return _serialize(doc)


async def list_matter_documents(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    limit: int = 50,
) -> list[dict]:
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    documents = get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION)
    rows = await (
        documents.find(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
        )
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    return [_serialize(doc) for doc in rows]


# ── Timeline ─────────────────────────────────────────────────────────────────


async def list_matter_timeline(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    limit: int = 100,
) -> list[dict]:
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    timeline = get_collection(LEGAL_MATTER_TIMELINE_COLLECTION)
    rows = await (
        timeline.find(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
        )
        .sort("occurred_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    return [_serialize(doc) for doc in rows]


async def add_matter_timeline_event(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    actor_id: str,
    payload: TimelineEventCreateRequest,
) -> dict:
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    event = await _append_timeline_event(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        actor_id=actor_id,
        event_type=payload.event_type.strip(),
        summary=payload.summary.strip(),
        occurred_at=payload.occurred_at,
        payload=payload.payload or {},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_matter_timeline_added",
        entity_type="legal_matter_timeline",
        entity_id=event["event_id"],
        new_value={"matter_id": matter_id, "event_type": event["event_type"]},
    )
    return event


# ── Matter briefs ────────────────────────────────────────────────────────────


def _build_grounded_brief_sections(
    *,
    matter: dict,
    documents: list[dict],
    timeline: list[dict],
    notes_for_brief: str | None,
) -> dict:
    key_facts: list[str] = [
        f"Matter number: {matter.get('matter_number')}",
        f"Title: {matter.get('title')}",
        f"Client: {matter.get('client_name') or matter.get('client_id')}",
        f"Type: {matter.get('matter_type')}",
    ]
    if matter.get("practice_area"):
        key_facts.append(f"Practice area: {matter['practice_area']}")
    if matter.get("court"):
        key_facts.append(f"Court / forum: {matter['court']}")
    if matter.get("opposite_party"):
        key_facts.append(f"Opposite party: {matter['opposite_party']}")
    if matter.get("jurisdiction"):
        key_facts.append(f"Jurisdiction: {matter['jurisdiction']}")
    if matter.get("description"):
        key_facts.append(f"Description: {matter['description']}")
    if notes_for_brief:
        key_facts.append(f"Briefing notes: {notes_for_brief.strip()}")

    important_dates: list[str] = []
    if matter.get("next_hearing_date"):
        important_dates.append(f"Next hearing: {matter['next_hearing_date']}")
    if matter.get("next_deadline_date"):
        important_dates.append(f"Next deadline: {matter['next_deadline_date']}")
    for event in timeline[:10]:
        if event.get("event_type") in {"court_hearing", "client_meeting"} or "deadline" in str(
            event.get("event_type") or ""
        ):
            important_dates.append(
                f"{event.get('occurred_at')}: {event.get('summary')}"
            )

    docs_reviewed = [
        f"{d.get('filename')} ({d.get('doc_type')})" for d in documents[:20]
    ]

    risks: list[str] = []
    if matter.get("status") == MatterStatus.PENDING.value:
        risks.append("Matter is pending external action — follow up may be overdue.")
    if matter.get("priority") in {"high", "urgent"}:
        risks.append(f"Priority is marked {matter.get('priority')}.")
    if not documents:
        risks.append("No documents attached yet — evidence file may be incomplete.")
    if not important_dates:
        risks.append("No hearing or deadline dates recorded on the matter.")

    next_actions: list[str] = [
        "Confirm facts and dates against source documents.",
        "Verify applicable law and citations before advising or filing.",
    ]
    if matter.get("status") == MatterStatus.DRAFT.value:
        next_actions.insert(0, "Move matter to Active once intake is complete.")
    if matter.get("next_deadline_date"):
        next_actions.insert(0, f"Prepare for deadline on {matter['next_deadline_date']}.")
    if matter.get("next_hearing_date"):
        next_actions.insert(0, f"Prepare for hearing on {matter['next_hearing_date']}.")

    limitations = [
        "Summary is grounded only in stored matter, client, document, and timeline records.",
        "Statutory and case-law positions are not independently verified in this Stage 3 brief.",
        "Do not treat suggested next actions as legal advice or filing instructions.",
    ]

    confidence = 0.55
    if documents:
        confidence += 0.1
    if timeline:
        confidence += 0.05
    if matter.get("jurisdiction") and matter.get("practice_area"):
        confidence += 0.05
    confidence = min(confidence, 0.75)

    overview_bits = [
        f"{matter.get('matter_number')} — {matter.get('title')}",
        f"Status: {matter.get('status')}",
    ]
    if matter.get("client_name"):
        overview_bits.append(f"Client: {matter['client_name']}")

    return {
        "matter_overview": ". ".join(overview_bits) + ".",
        "key_facts": key_facts,
        "applicable_law": [
            "Not automatically retrieved in Stage 3 grounded brief. "
            "Use LegalMitra research with citations for applicable law."
        ],
        "important_dates": important_dates or ["No important dates recorded."],
        "documents_reviewed": docs_reviewed or ["No documents attached."],
        "current_status": str(matter.get("status") or "unknown"),
        "risks": risks or ["No elevated risks flagged from stored records."],
        "suggested_next_actions": next_actions,
        "limitations": limitations,
        "confidence": round(confidence, 2),
        "human_review_required": True,
    }


async def generate_matter_brief(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
    generated_by: str,
    payload: MatterBriefGenerateRequest | None = None,
) -> dict:
    options = payload or MatterBriefGenerateRequest()
    matter = await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    documents: list[dict] = []
    timeline: list[dict] = []
    if options.include_documents:
        documents = await list_matter_documents(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=50
        )
    if options.include_timeline:
        timeline = await list_matter_timeline(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=50
        )

    sections = _build_grounded_brief_sections(
        matter=matter,
        documents=documents,
        timeline=timeline,
        notes_for_brief=options.notes_for_brief,
    )
    sources: list[dict[str, Any]] = [
        {
            "source_type": "matter_record",
            "matter_id": matter_id,
            "matter_number": matter.get("matter_number"),
        }
    ]
    for doc in documents:
        sources.append(
            {
                "source_type": "matter_document",
                "document_id": doc.get("document_id"),
                "filename": doc.get("filename"),
            }
        )
    for event in timeline[:10]:
        sources.append(
            {
                "source_type": "timeline_event",
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
            }
        )

    now = _now()
    brief = {
        "brief_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "matter_id": matter_id,
        "sections": sections,
        "sources": sources,
        "advisory_notice": ADVISORY_NOTICE,
        "generated_by": generated_by,
        "generated_at": now,
        "generation_strategy": "grounded_matter_summary",
    }
    briefs = get_collection(LEGAL_MATTER_BRIEFS_COLLECTION)
    await briefs.insert_one(brief)

    await _append_timeline_event(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        actor_id=generated_by,
        event_type="brief_generated",
        summary="Matter Intelligence Brief generated (grounded summary)",
        payload={"brief_id": brief["brief_id"]},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=generated_by,
        action="legal_matter_brief_generated",
        entity_type="legal_matter_brief",
        entity_id=brief["brief_id"],
        new_value={
            "matter_id": matter_id,
            "confidence": sections["confidence"],
            "human_review_required": True,
        },
    )
    return _serialize(brief)


async def get_latest_matter_brief(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str,
) -> dict:
    await get_matter(tenant_id=tenant_id, app_key=app_key, matter_id=matter_id)
    briefs = get_collection(LEGAL_MATTER_BRIEFS_COLLECTION)
    rows = await (
        briefs.find(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "matter_id": matter_id}
        )
        .sort("generated_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if not rows:
        raise PracticeNotFoundError("No matter brief found")
    return _serialize(rows[0])


# ── Dashboard ────────────────────────────────────────────────────────────────


async def get_practice_dashboard(
    *,
    tenant_id: str,
    app_key: str,
    limit: int = 5,
) -> dict:
    matters = get_collection(LEGAL_MATTERS_COLLECTION)
    clients = get_collection(LEGAL_CLIENTS_COLLECTION)
    documents = get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION)
    briefs = get_collection(LEGAL_MATTER_BRIEFS_COLLECTION)
    scope = _scope(tenant_id=tenant_id, app_key=app_key)

    active_matters = await matters.count_documents({**scope, "status": MatterStatus.ACTIVE.value})
    pending_matters = await matters.count_documents({**scope, "status": MatterStatus.PENDING.value})
    draft_matters = await matters.count_documents({**scope, "status": MatterStatus.DRAFT.value})
    awaiting_review = int(pending_matters) + int(draft_matters)

    upcoming_hearings: list[dict] = []
    upcoming_deadlines: list[dict] = []
    recent_clients: list[dict] = []
    recent_briefs: list[dict] = []
    recent_documents: list[dict] = []

    # Prefer date-sorted queries; FakeCollection sorts by field name.
    hearing_rows = await matters.find(scope).sort("next_hearing_date", 1).limit(limit * 3).to_list(
        length=limit * 3
    )
    for doc in hearing_rows:
        hearing = doc.get("next_hearing_date")
        if not hearing:
            continue
        if doc.get("status") in {
            MatterStatus.CLOSED.value,
            MatterStatus.ARCHIVED.value,
        }:
            continue
        upcoming_hearings.append(
            {
                "matter_id": doc["matter_id"],
                "matter_number": doc.get("matter_number"),
                "title": doc.get("title"),
                "next_hearing_date": hearing,
                "court": doc.get("court"),
                "status": doc.get("status"),
            }
        )
        if len(upcoming_hearings) >= limit:
            break

    deadline_rows = await matters.find(scope).sort("next_deadline_date", 1).limit(limit * 3).to_list(
        length=limit * 3
    )
    for doc in deadline_rows:
        deadline = doc.get("next_deadline_date")
        if not deadline:
            continue
        if doc.get("status") in {
            MatterStatus.CLOSED.value,
            MatterStatus.ARCHIVED.value,
        }:
            continue
        upcoming_deadlines.append(
            {
                "matter_id": doc["matter_id"],
                "matter_number": doc.get("matter_number"),
                "title": doc.get("title"),
                "next_deadline_date": deadline,
                "status": doc.get("status"),
            }
        )
        if len(upcoming_deadlines) >= limit:
            break

    client_rows = await clients.find(scope).sort("created_at", -1).limit(limit).to_list(length=limit)
    for doc in client_rows:
        recent_clients.append(
            {
                "client_id": doc["client_id"],
                "display_name": doc.get("display_name"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at"),
            }
        )

    brief_rows = await briefs.find(scope).sort("generated_at", -1).limit(limit).to_list(length=limit)
    for doc in brief_rows:
        recent_briefs.append(
            {
                "brief_id": doc["brief_id"],
                "matter_id": doc.get("matter_id"),
                "generated_at": doc.get("generated_at"),
                "confidence": (doc.get("sections") or {}).get("confidence"),
                "human_review_required": (doc.get("sections") or {}).get(
                    "human_review_required", True
                ),
            }
        )

    doc_rows = await documents.find(scope).sort("created_at", -1).limit(limit).to_list(length=limit)
    for doc in doc_rows:
        recent_documents.append(
            {
                "document_id": doc["document_id"],
                "matter_id": doc.get("matter_id"),
                "filename": doc.get("filename"),
                "created_at": doc.get("created_at"),
            }
        )

    return {
        "active_matters": int(active_matters),
        "pending_matters": int(pending_matters),
        "awaiting_review": int(awaiting_review),
        "upcoming_hearings": upcoming_hearings,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_clients": recent_clients,
        "recent_briefs": recent_briefs,
        "recent_documents": recent_documents,
        "fees_outstanding": "—",
        "data_source": "live",
    }
