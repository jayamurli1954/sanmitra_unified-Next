from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.db.mongo import get_collection
from app.modules.office_ai.ai import orchestrator
from app.modules.office_ai.connectors.manager import collect_connector_facts
from app.modules.office_ai.models import BRIEFS_COLLECTION, ensure_indexes, new_object_id, serialize_doc, utcnow
from app.modules.office_ai.services import calendar_service, email_service, meeting_notes_service, notification_service, task_service


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


async def get_today_brief(*, tenant_id: str) -> dict | None:
    await ensure_indexes()
    today = date.today().isoformat()
    doc = await get_collection(BRIEFS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "brief_date": today},
        sort=[("generated_at", -1)],
    )
    return serialize_doc(doc)


async def generate_brief(
    *,
    tenant_id: str,
    app_key: str,
    tenant: dict,
    user: dict,
    session=None,
    include_tasks: bool = True,
    include_emails: bool = True,
    include_calendar: bool = True,
    include_meeting_notes: bool = True,
) -> dict:
    await ensure_indexes()

    open_tasks = await task_service.list_tasks(tenant_id=tenant_id, status="open", limit=20) if include_tasks else []
    recent_emails = await email_service.list_emails(tenant_id=tenant_id, limit=5) if include_emails else []
    today_events = await calendar_service.list_today_events(tenant_id=tenant_id, limit=20) if include_calendar else []
    recent_notes = (
        await meeting_notes_service.list_meeting_notes(tenant_id=tenant_id, limit=5) if include_meeting_notes else []
    )

    connector_facts = await collect_connector_facts(
        tenant_id=tenant_id,
        app_key=app_key,
        tenant=tenant,
        session=session,
    )
    connector_sections = dict(connector_facts.get("sections") or {})
    # Normalize MitraBooks bundle into brief-friendly keys when present.
    mitra = connector_sections.pop("mitrabooks", None)
    if isinstance(mitra, dict):
        connector_sections["mitrabooks_revenue"] = mitra.get("revenue") or {"enabled": False}
        connector_sections["mitrabooks_overdue"] = mitra.get("overdue") or []

    sections: dict[str, Any] = {
        **connector_sections,
        "open_tasks": [{"title": t.get("title"), "due_date": t.get("due_date")} for t in open_tasks],
        "recent_email_summaries": [
            {"summary": e.get("summary"), "created_at": e.get("created_at")} for e in recent_emails if e.get("summary")
        ],
        "today_calendar": [
            {
                "title": e.get("title"),
                "starts_at": e.get("starts_at"),
                "ends_at": e.get("ends_at"),
                "location": e.get("location"),
            }
            for e in today_events
        ],
        "recent_meeting_notes": [
            {"summary": n.get("summary"), "created_at": n.get("created_at")} for n in recent_notes if n.get("summary")
        ],
    }
    facts: dict[str, Any] = {
        "brief_date": date.today().isoformat(),
        "deployment_mode": "standalone" if connector_facts.get("standalone") else "integrated",
        "connectors_loaded": connector_facts.get("connectors_loaded") or [],
        "connectors_skipped": connector_facts.get("connectors_skipped") or [],
        "sections": sections,
        "source_modules": connector_facts.get("source_modules") or [],
    }
    ai_result = await orchestrator.build_daily_brief(
        tenant_id=tenant_id,
        facts=facts,
        user_id=_user_id(user),
    )
    now = utcnow()
    uid = _user_id(user)
    generation_id = str(uuid.uuid4())
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "brief_date": date.today().isoformat(),
        "generation_id": generation_id,
        "generated_at": now,
        "content": ai_result.get("content"),
        "sections": sections,
        "connector_snapshot": {
            "connectors_loaded": connector_facts.get("connectors_loaded") or [],
            "connectors_skipped": connector_facts.get("connectors_skipped") or [],
            "standalone": bool(connector_facts.get("standalone")),
        },
        "source_modules": connector_facts.get("source_modules") or [],
        "deployment_mode": facts["deployment_mode"],
        "model": ai_result.get("model"),
        "prompt_version": ai_result.get("prompt_version"),
        "ai_telemetry_id": ai_result.get("telemetry_id"),
        "ai_available": ai_result.get("ai_available"),
        "created_at": now,
        "updated_at": now,
        "created_by": uid,
        "updated_by": uid,
    }
    await get_collection(BRIEFS_COLLECTION).insert_one(doc)
    brief = serialize_doc(doc)
    await notification_service.create_notification(
        tenant_id=tenant_id,
        user=user,
        title="Today's brief ready",
        body="Open OfficeMitra AI → Today Brief to review.",
        kind="brief_ready",
        href="/business/office-ai",
        dedupe_key=f"brief_ready:{date.today().isoformat()}:{uid}",
    )
    return {
        "brief": brief,
        "ai_available": ai_result.get("ai_available"),
        "advisory": ai_result.get("advisory"),
        "error_code": ai_result.get("error_code"),
        "deployment_mode": facts["deployment_mode"],
        "connectors_loaded": connector_facts.get("connectors_loaded") or [],
    }
