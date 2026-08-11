"""OfficeMitra Phase 2 — calendar, meeting notes, notifications (fake Motor)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from bson import ObjectId

from app.core.modules.registry import ModuleAccessError, require_module_feature
from app.modules.office_ai.models import (
    BRIEFS_COLLECTION,
    CALENDAR_EVENTS_COLLECTION,
    EMAILS_COLLECTION,
    MEETING_NOTES_COLLECTION,
    NOTIFICATIONS_COLLECTION,
    TASKS_COLLECTION,
    TELEMETRY_COLLECTION,
)
from app.modules.office_ai.services import (
    brief_service,
    calendar_service,
    meeting_notes_service,
    notification_service,
)


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length: int = 100):
        return self._docs[:length]


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    def find(self, query: dict | None = None):
        query = query or {}
        matched = [doc for doc in self.docs if _match(doc, query)]
        return _FakeCursor(matched)

    async def find_one(self, query: dict, *args, **kwargs):
        for doc in self.docs:
            if _match(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def update_many(self, query: dict, update: dict):
        count = 0
        for doc in self.docs:
            if _match(doc, query):
                doc.update(update.get("$set") or {})
                count += 1
        return type("R", (), {"modified_count": count})()

    async def find_one_and_update(self, query: dict, update: dict):
        for doc in self.docs:
            if _match(doc, query):
                before = dict(doc)
                doc.update(update.get("$set") or {})
                return before
        return None

    async def count_documents(self, query: dict):
        return sum(1 for doc in self.docs if _match(doc, query))

    async def delete_many(self, query: dict):
        before = len(self.docs)
        self.docs = [doc for doc in self.docs if not _match(doc, query)]
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def create_index(self, *_args, **_kwargs):
        return True


def _match(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        if key == "_id" and isinstance(expected, dict) and "$in" in expected:
            if doc.get("_id") not in expected["$in"]:
                return False
            continue
        actual = doc.get(key)
        if isinstance(expected, dict):
            if "$lte" in expected and not (actual is not None and actual <= expected["$lte"]):
                return False
            if "$gte" in expected and not (actual is not None and actual >= expected["$gte"]):
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            continue
        if expected is None:
            if actual is not None:
                return False
        elif actual != expected:
            return False
    return True


@pytest.fixture
def fake_mongo(monkeypatch):
    store = {
        TASKS_COLLECTION: _FakeCollection(),
        EMAILS_COLLECTION: _FakeCollection(),
        BRIEFS_COLLECTION: _FakeCollection(),
        TELEMETRY_COLLECTION: _FakeCollection(),
        CALENDAR_EVENTS_COLLECTION: _FakeCollection(),
        MEETING_NOTES_COLLECTION: _FakeCollection(),
        NOTIFICATIONS_COLLECTION: _FakeCollection(),
    }

    def get_collection(name: str):
        return store[name]

    targets = [
        "app.modules.office_ai.models.get_collection",
        "app.modules.office_ai.services.task_service.get_collection",
        "app.modules.office_ai.services.email_service.get_collection",
        "app.modules.office_ai.services.brief_service.get_collection",
        "app.modules.office_ai.services.calendar_service.get_collection",
        "app.modules.office_ai.services.meeting_notes_service.get_collection",
        "app.modules.office_ai.services.notification_service.get_collection",
        "app.modules.office_ai.retention.get_collection",
    ]
    for target in targets:
        monkeypatch.setattr(target, get_collection)
    monkeypatch.setattr("app.modules.office_ai.models._indexes_ready", True)
    return store


def test_phase2_feature_flags_exist():
    definition = require_module_feature(
        module_key="office_ai",
        feature="calendar",
        organization_type="BUSINESS",
        enabled_modules=["office_ai"],
        app_key="mitrabooks",
    )
    assert "calendar" in definition.features
    assert "meeting_notes" in definition.features
    assert "notifications" in definition.features

    with pytest.raises(ModuleAccessError, match="office_ai.calendar"):
        require_module_feature(
            module_key="office_ai",
            feature="calendar",
            organization_type="BUSINESS",
            enabled_modules=["office_ai", "office_ai.tasks", "office_ai.email"],
            app_key="mitrabooks",
        )


def test_parse_calendar_text_agenda_and_ics():
    today = date.today().isoformat()
    agenda = f"{today} 10:00 GST review with Jayam\n14:30 TDS follow-up"
    events = calendar_service.parse_calendar_text(agenda)
    assert len(events) >= 2
    assert "GST review" in events[0]["title"]

    ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Partner huddle
DTSTART:20260805T090000Z
DTEND:20260805T100000Z
LOCATION:Zoom
END:VEVENT
END:VCALENDAR"""
    ics_events = calendar_service.parse_calendar_text(ics)
    assert len(ics_events) == 1
    assert ics_events[0]["title"] == "Partner huddle"
    assert ics_events[0]["location"] == "Zoom"


@pytest.mark.asyncio
async def test_calendar_and_notifications_are_tenant_scoped(fake_mongo):
    user_a = {"sub": "ua"}
    user_b = {"sub": "ub"}
    starts = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    await calendar_service.create_event(
        tenant_id="tenant-a",
        user=user_a,
        title="A event",
        starts_at=starts.isoformat(),
        source="manual",
    )
    await calendar_service.create_event(
        tenant_id="tenant-b",
        user=user_b,
        title="B event",
        starts_at=starts.isoformat(),
        source="manual",
    )
    listed = await calendar_service.list_today_events(tenant_id="tenant-a")
    assert len(listed) == 1
    assert listed[0]["title"] == "A event"

    notifs = await notification_service.list_notifications(tenant_id="tenant-a", user=user_a)
    assert notifs["count"] >= 1
    other = await notification_service.list_notifications(tenant_id="tenant-b", user=user_a)
    assert other["count"] == 0


@pytest.mark.asyncio
async def test_notification_mark_read_is_user_scoped(fake_mongo):
    user_a = {"sub": "ua"}
    user_b = {"sub": "ub"}
    note = await notification_service.create_notification(
        tenant_id="t1",
        user=user_a,
        title="Hello",
        kind="note_processed",
    )
    missing = await notification_service.mark_read(
        tenant_id="t1",
        user=user_b,
        notification_id=note["id"],
    )
    assert missing is None
    updated = await notification_service.mark_read(
        tenant_id="t1",
        user=user_a,
        notification_id=note["id"],
    )
    assert updated is not None
    assert updated["read_at"] is not None


@pytest.mark.asyncio
async def test_meeting_notes_soft_fail_and_persist(fake_mongo, monkeypatch):
    async def fake_summarize(**kwargs):
        return {
            "ai_available": False,
            "summary": "",
            "action_items": [],
            "prompt_version": "summarize_meeting_notes_v1",
            "telemetry_id": str(ObjectId()),
            "provider": "null",
            "model": "none",
            "error_code": "missing_api_key",
            "advisory": "advisory",
        }

    monkeypatch.setattr(
        "app.modules.office_ai.services.meeting_notes_service.orchestrator.summarize_meeting_notes",
        fake_summarize,
    )
    result = await meeting_notes_service.summarize_and_optionally_persist(
        tenant_id="t1",
        user={"sub": "ua"},
        raw_text="Discussed GST filing deadline Friday. Assign staff A.",
        persist=True,
        create_tasks=True,
    )
    assert result["ai_available"] is False
    assert result["meeting_note"] is not None
    assert result["saved_tasks"] == []
    listed = await meeting_notes_service.list_meeting_notes(tenant_id="t1")
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_brief_includes_today_calendar(fake_mongo, monkeypatch):
    async def fake_brief(**kwargs):
        return {
            "ai_available": False,
            "content": "fallback",
            "prompt_version": "daily_brief_v1",
            "telemetry_id": None,
            "model": None,
            "error_code": "missing_api_key",
            "advisory": "advisory",
        }

    async def fake_connectors(**kwargs):
        return {
            "standalone": True,
            "connectors_loaded": [],
            "connectors_skipped": [],
            "sections": {},
            "source_modules": [],
        }

    monkeypatch.setattr("app.modules.office_ai.services.brief_service.orchestrator.build_daily_brief", fake_brief)
    monkeypatch.setattr(
        "app.modules.office_ai.services.brief_service.collect_connector_facts",
        fake_connectors,
    )

    starts = datetime.now(timezone.utc).replace(hour=11, minute=0, second=0, microsecond=0)
    await calendar_service.create_event(
        tenant_id="t1",
        user={"sub": "ua"},
        title="Board call",
        starts_at=starts.isoformat(),
        notify=False,
    )
    result = await brief_service.generate_brief(
        tenant_id="t1",
        app_key="mitrabooks",
        tenant={"enabled_modules": ["office_ai"]},
        user={"sub": "ua"},
        include_calendar=True,
        include_meeting_notes=True,
    )
    sections = (result.get("brief") or {}).get("sections") or {}
    assert any(item.get("title") == "Board call" for item in (sections.get("today_calendar") or []))


def test_office_ai_ui_has_phase2_tabs() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "shared"
        / "office-ai-workspace.js"
    ).read_text(encoding="utf-8")
    assert '["calendar", "Calendar"]' in source
    assert '["notes", "Meeting Notes"]' in source
    assert '["notifications", notifLabel]' in source or "Notifications" in source
    assert "/api/v1/officemitra/calendar/parse" in source
    assert "/api/v1/officemitra/meeting-notes/summarize" in source
    assert "/api/v1/officemitra/notifications/" in source
    assert 'data-office-ai-action="parse-calendar"' in source
    assert 'data-office-ai-action="summarize-notes"' in source
    assert 'data-office-ai-action="mark-notification-read"' in source
    assert "confirm-proposal" in source
