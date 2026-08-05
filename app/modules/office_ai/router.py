from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.modules.dependencies import require_enabled_module, require_enabled_module_feature
from app.db.postgres import get_async_session
from app.modules.office_ai import schemas
from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors.manager import list_registered_connectors
from app.modules.office_ai.services import (
    brief_service,
    calendar_service,
    email_service,
    meeting_notes_service,
    notification_service,
    task_service,
)

router = APIRouter(prefix="/officemitra", tags=["officemitra"])


def _tenant_id(ctx: dict) -> str:
    return str((ctx.get("tenant") or {}).get("tenant_id") or (ctx.get("user") or {}).get("tenant_id") or "").strip()


@router.get("/ping")
async def ping(ctx: dict = Depends(require_enabled_module("office_ai"))) -> dict:
    return {
        "ok": True,
        "module": "office_ai",
        "tenant_id": _tenant_id(ctx),
        "app_key": ctx.get("app_key"),
        "features": ["tasks", "email", "brief", "calendar", "meeting_notes", "notifications"],
        "connectors": list_registered_connectors(),
        "metrics": ai_metrics.snapshot(),
    }


@router.get("/tasks")
async def list_tasks(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "tasks")),
) -> dict:
    items = await task_service.list_tasks(tenant_id=_tenant_id(ctx), status=status, limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/tasks")
async def create_task(
    payload: schemas.TaskCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "tasks")),
) -> dict:
    item = await task_service.create_task(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        title=payload.title,
        notes=payload.notes,
        due_date=payload.due_date,
        status=payload.status,
        source="manual",
    )
    return {"item": item}


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: schemas.TaskUpdateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "tasks")),
) -> dict:
    item = await task_service.update_task(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        task_id=task_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"item": item}


@router.post("/tasks/generate")
async def generate_tasks(
    payload: schemas.TaskGenerateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "tasks")),
) -> dict:
    return await task_service.generate_and_optionally_persist(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        text=payload.text,
        persist=payload.persist,
    )


@router.get("/emails")
async def list_emails(
    limit: int = Query(default=50, ge=1, le=100),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "email")),
) -> dict:
    items = await email_service.list_emails(tenant_id=_tenant_id(ctx), limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/emails")
async def create_email(
    payload: schemas.EmailCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "email")),
) -> dict:
    item = await email_service.create_email(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        raw_text=payload.raw_text,
    )
    return {"item": item}


@router.post("/emails/summarize")
async def summarize_email(
    payload: schemas.EmailSummarizeRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "email")),
) -> dict:
    return await email_service.summarize_and_optionally_persist(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        raw_text=payload.raw_text,
        persist=payload.persist,
        create_tasks=payload.create_tasks,
    )


@router.get("/briefs/today")
async def today_brief(ctx: dict = Depends(require_enabled_module_feature("office_ai", "brief"))) -> dict:
    item = await brief_service.get_today_brief(tenant_id=_tenant_id(ctx))
    return {"item": item}


@router.post("/briefs/generate")
async def generate_brief(
    payload: schemas.BriefGenerateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "brief")),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    return await brief_service.generate_brief(
        tenant_id=_tenant_id(ctx),
        app_key=ctx["app_key"],
        tenant=ctx["tenant"],
        user=ctx["user"],
        session=session,
        include_tasks=payload.include_tasks,
        include_emails=payload.include_emails,
        include_calendar=payload.include_calendar,
        include_meeting_notes=payload.include_meeting_notes,
    )


@router.get("/calendar/events")
async def list_calendar_events(
    day: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "calendar")),
) -> dict:
    items = await calendar_service.list_events(tenant_id=_tenant_id(ctx), day=day, limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/calendar/today")
async def calendar_today(
    limit: int = Query(default=50, ge=1, le=100),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "calendar")),
) -> dict:
    items = await calendar_service.list_today_events(tenant_id=_tenant_id(ctx), limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/calendar/events")
async def create_calendar_event(
    payload: schemas.CalendarEventCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "calendar")),
) -> dict:
    try:
        item = await calendar_service.create_event(
            tenant_id=_tenant_id(ctx),
            user=ctx["user"],
            title=payload.title,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            location=payload.location,
            raw_text=payload.raw_text,
            source="manual",
            linked_note_id=payload.linked_note_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@router.patch("/calendar/events/{event_id}")
async def update_calendar_event(
    event_id: str,
    payload: schemas.CalendarEventUpdateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "calendar")),
) -> dict:
    item = await calendar_service.update_event(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        event_id=event_id,
        updates=payload.model_dump(exclude_unset=True),
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return {"item": item}


@router.post("/calendar/parse")
async def parse_calendar(
    payload: schemas.CalendarParseRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "calendar")),
) -> dict:
    return await calendar_service.parse_and_optionally_persist(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        raw_text=payload.raw_text,
        persist=payload.persist,
    )


@router.get("/meeting-notes")
async def list_meeting_notes(
    limit: int = Query(default=50, ge=1, le=100),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "meeting_notes")),
) -> dict:
    items = await meeting_notes_service.list_meeting_notes(tenant_id=_tenant_id(ctx), limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/meeting-notes")
async def create_meeting_note(
    payload: schemas.MeetingNoteCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "meeting_notes")),
) -> dict:
    item = await meeting_notes_service.create_meeting_note(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        raw_text=payload.raw_text,
        linked_event_id=payload.linked_event_id,
    )
    return {"item": item}


@router.post("/meeting-notes/summarize")
async def summarize_meeting_notes(
    payload: schemas.MeetingNoteSummarizeRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "meeting_notes")),
) -> dict:
    return await meeting_notes_service.summarize_and_optionally_persist(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        raw_text=payload.raw_text,
        persist=payload.persist,
        create_tasks=payload.create_tasks,
        linked_event_id=payload.linked_event_id,
    )


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "notifications")),
) -> dict:
    return await notification_service.list_notifications(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        unread_only=unread_only,
        limit=limit,
    )


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "notifications")),
) -> dict:
    item = await notification_service.mark_read(
        tenant_id=_tenant_id(ctx),
        user=ctx["user"],
        notification_id=notification_id,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"item": item}
