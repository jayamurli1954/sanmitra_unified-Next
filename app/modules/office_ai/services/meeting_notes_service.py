from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection
from app.modules.office_ai.ai import orchestrator
from app.modules.office_ai.models import (
    MEETING_NOTES_COLLECTION,
    TASKS_COLLECTION,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)
from app.modules.office_ai.services import notification_service, task_service


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


async def list_meeting_notes(*, tenant_id: str, limit: int = 50) -> list[dict]:
    await ensure_indexes()
    cursor = (
        get_collection(MEETING_NOTES_COLLECTION)
        .find({"tenant_id": tenant_id})
        .sort("created_at", -1)
        .limit(min(limit, 100))
    )
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 100))]


async def create_meeting_note(
    *,
    tenant_id: str,
    user: dict,
    raw_text: str,
    summary: str | None = None,
    suggested_task_ids: list[str] | None = None,
    linked_event_id: str | None = None,
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
) -> dict:
    await ensure_indexes()
    now = utcnow()
    uid = _user_id(user)
    task_oids = [ObjectId(item) for item in (suggested_task_ids or []) if ObjectId.is_valid(item)]
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "raw_text": raw_text.strip()[:50000],
        "summary": (summary or "").strip() or None,
        "suggested_task_ids": task_oids,
        "linked_event_id": ObjectId(linked_event_id)
        if linked_event_id and ObjectId.is_valid(linked_event_id)
        else None,
        "prompt_version": prompt_version,
        "ai_telemetry_id": ObjectId(ai_telemetry_id)
        if ai_telemetry_id and ObjectId.is_valid(ai_telemetry_id)
        else None,
        "created_at": now,
        "updated_at": now,
        "created_by": uid,
        "updated_by": uid,
    }
    await get_collection(MEETING_NOTES_COLLECTION).insert_one(doc)
    return serialize_doc(doc)


async def summarize_and_optionally_persist(
    *,
    tenant_id: str,
    user: dict,
    raw_text: str,
    persist: bool = True,
    create_tasks: bool = True,
    linked_event_id: str | None = None,
) -> dict[str, Any]:
    ai_result = await orchestrator.summarize_meeting_notes(
        tenant_id=tenant_id,
        text=raw_text,
        user_id=_user_id(user),
    )
    saved_tasks: list[dict] = []
    note_doc = None
    if create_tasks and ai_result.get("ai_available"):
        for title in ai_result.get("action_items") or []:
            saved_tasks.append(
                await task_service.create_task(
                    tenant_id=tenant_id,
                    user=user,
                    title=title,
                    source="ai",
                    prompt_version=ai_result.get("prompt_version"),
                    ai_telemetry_id=ai_result.get("telemetry_id"),
                )
            )
    if persist:
        note_doc = await create_meeting_note(
            tenant_id=tenant_id,
            user=user,
            raw_text=raw_text,
            summary=ai_result.get("summary"),
            suggested_task_ids=[item["id"] for item in saved_tasks if item.get("id")],
            linked_event_id=linked_event_id,
            prompt_version=ai_result.get("prompt_version"),
            ai_telemetry_id=ai_result.get("telemetry_id"),
        )
        if note_doc and saved_tasks:
            await get_collection(TASKS_COLLECTION).update_many(
                {
                    "tenant_id": tenant_id,
                    "_id": {"$in": [ObjectId(t["id"]) for t in saved_tasks if ObjectId.is_valid(t["id"])]},
                },
                {"$set": {"linked_note_id": ObjectId(note_doc["id"]), "updated_at": utcnow()}},
            )
        await notification_service.create_notification(
            tenant_id=tenant_id,
            user=user,
            title="Meeting notes processed",
            body=(ai_result.get("summary") or "Notes saved (AI unavailable).")[:500],
            kind="note_processed",
            href="/business/office-ai",
            dedupe_key=f"note_processed:{note_doc['id']}" if note_doc else None,
        )
    return {
        **ai_result,
        "meeting_note": note_doc,
        "saved_tasks": saved_tasks,
    }
