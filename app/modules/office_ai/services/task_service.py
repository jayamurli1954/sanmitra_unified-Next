from __future__ import annotations

import re
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection
from app.modules.office_ai.ai import orchestrator
from app.modules.office_ai.models import (
    TASK_STATUSES,
    TASKS_COLLECTION,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)

_SOFT_FAIL_LINE = re.compile(r"^(?:[\d]+[.)]\s*|[-*•]\s*)")


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


def deterministic_task_drafts_from_text(text: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Build reviewable task drafts when the AI provider is unavailable.

    Used only for writeback soft-fail proposals so confirm/dismiss remains
    testable and useful without inventing ERP/legal facts.
    """
    raw = str(text or "").strip()
    if not raw:
        return []
    drafts: list[dict[str, Any]] = []
    for line in raw.splitlines():
        cleaned = _SOFT_FAIL_LINE.sub("", line.strip()).strip()
        if not cleaned:
            continue
        drafts.append({"title": cleaned[:500], "due_date": None, "source": "manual"})
        if len(drafts) >= max(1, min(limit, 10)):
            break
    if not drafts:
        drafts.append({"title": raw[:500], "due_date": None, "source": "manual"})
    return drafts


async def list_tasks(*, tenant_id: str, status: str | None = None, limit: int = 100) -> list[dict]:
    await ensure_indexes()
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if status:
        query["status"] = status
    cursor = get_collection(TASKS_COLLECTION).find(query).sort("updated_at", -1).limit(min(limit, 200))
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 200))]


async def create_task(
    *,
    tenant_id: str,
    user: dict,
    title: str,
    notes: str | None = None,
    due_date: str | None = None,
    status: str = "open",
    source: str = "manual",
    linked_email_id: str | None = None,
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
) -> dict:
    await ensure_indexes()
    now = utcnow()
    uid = _user_id(user)
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "title": title.strip()[:500],
        "notes": (notes or "").strip()[:4000] or None,
        "due_date": due_date,
        "status": status if status in TASK_STATUSES else "open",
        "source": source if source in {"manual", "ai"} else "manual",
        "linked_email_id": ObjectId(linked_email_id) if linked_email_id and ObjectId.is_valid(linked_email_id) else None,
        "prompt_version": prompt_version,
        "ai_telemetry_id": ObjectId(ai_telemetry_id) if ai_telemetry_id and ObjectId.is_valid(ai_telemetry_id) else None,
        "created_at": now,
        "updated_at": now,
        "created_by": uid,
        "updated_by": uid,
        "change_reason": None,
    }
    await get_collection(TASKS_COLLECTION).insert_one(doc)
    item = serialize_doc(doc)
    if due_date:
        from datetime import date

        from app.modules.office_ai.services import notification_service

        today = date.today().isoformat()
        if str(due_date).strip()[:10] == today:
            await notification_service.create_notification(
                tenant_id=tenant_id,
                user=user,
                title=f"Task due today: {doc['title'][:120]}",
                body="Open OfficeMitra AI → Tasks to review.",
                kind="task_due",
                href="/business/office-ai",
                dedupe_key=f"task_due:{item['id']}",
            )
    return item


async def update_task(
    *,
    tenant_id: str,
    user: dict,
    task_id: str,
    updates: dict[str, Any],
) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(task_id):
        return None
    allowed: dict[str, Any] = {}
    if "title" in updates and updates["title"] is not None:
        allowed["title"] = str(updates["title"]).strip()[:500]
    if "notes" in updates:
        notes = updates["notes"]
        allowed["notes"] = (str(notes).strip()[:4000] if notes is not None else None)
    if "due_date" in updates:
        allowed["due_date"] = updates["due_date"]
    if "status" in updates and updates["status"] in TASK_STATUSES:
        allowed["status"] = updates["status"]
    if "change_reason" in updates:
        allowed["change_reason"] = (str(updates["change_reason"] or "").strip()[:500] or None)
    if not allowed:
        existing = await get_collection(TASKS_COLLECTION).find_one({"_id": ObjectId(task_id), "tenant_id": tenant_id})
        return serialize_doc(existing)
    allowed["updated_at"] = utcnow()
    allowed["updated_by"] = _user_id(user)
    result = await get_collection(TASKS_COLLECTION).find_one_and_update(
        {"_id": ObjectId(task_id), "tenant_id": tenant_id},
        {"$set": allowed},
    )
    if result is None:
        return None
    # Motor returns the pre-image by default; re-read for post-update document.
    updated = await get_collection(TASKS_COLLECTION).find_one({"_id": ObjectId(task_id), "tenant_id": tenant_id})
    return serialize_doc(updated)


async def generate_and_optionally_persist(
    *,
    tenant_id: str,
    user: dict,
    text: str,
    persist: bool = False,
    writeback_enabled: bool = False,
    enabled_modules: list | None = None,
    office_ai_features: list | None = None,
) -> dict:
    ai_result = await orchestrator.generate_tasks(tenant_id=tenant_id, text=text, user_id=_user_id(user))
    saved: list[dict] = []
    proposals: list[dict] = []
    soft_fail_proposals = False
    tasks = list(ai_result.get("tasks") or [])

    # Soft-fail writeback path: when AI is down, still open confirmable proposals from
    # the user's pasted text so Phase 4 / ops smoke is not blocked by missing API keys.
    if (
        persist
        and writeback_enabled
        and not ai_result.get("ai_available")
        and not tasks
        and str(text or "").strip()
    ):
        tasks = deterministic_task_drafts_from_text(text)
        soft_fail_proposals = bool(tasks)

    if persist and tasks and (ai_result.get("ai_available") or soft_fail_proposals):
        if writeback_enabled:
            from app.modules.office_ai.services import proposal_service

            proposals = await proposal_service.create_task_proposals(
                tenant_id=tenant_id,
                user=user,
                tasks=tasks,
                source_feature=(
                    "tasks.generate.soft_fail" if soft_fail_proposals else "tasks.generate"
                ),
                prompt_version=(
                    "soft_fail_v1" if soft_fail_proposals else ai_result.get("prompt_version")
                ),
                ai_telemetry_id=None if soft_fail_proposals else ai_result.get("telemetry_id"),
                enabled_modules=enabled_modules or ["office_ai", "office_ai.writeback"],
                office_ai_features=office_ai_features,
            )
        elif ai_result.get("ai_available"):
            for item in tasks:
                saved.append(
                    await create_task(
                        tenant_id=tenant_id,
                        user=user,
                        title=item["title"],
                        due_date=item.get("due_date"),
                        source="ai",
                        prompt_version=ai_result.get("prompt_version"),
                        ai_telemetry_id=ai_result.get("telemetry_id"),
                    )
                )
    return {
        **ai_result,
        "tasks": tasks if soft_fail_proposals else ai_result.get("tasks") or [],
        "saved_tasks": saved,
        "proposals": proposals,
        "writeback_enabled": writeback_enabled,
        "soft_fail_proposals": soft_fail_proposals,
    }
