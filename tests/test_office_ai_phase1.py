"""OfficeMitra Phase 1 — Mongo CRUD + tenant isolation (fake Motor collections)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from bson import ObjectId

from app.modules.office_ai.models import (
    BRIEFS_COLLECTION,
    EMAILS_COLLECTION,
    TASKS_COLLECTION,
    TELEMETRY_COLLECTION,
)
from app.modules.office_ai.services import brief_service, email_service, task_service


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
        self.docs: list[dict[str, Any]] = []

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def find_one(self, query: dict, sort=None):
        matches = [d for d in self.docs if _match(d, query)]
        if not matches:
            return None
        if sort:
            # sort is list of (field, direction)
            field, direction = sort[0]
            matches.sort(key=lambda d: d.get(field) or datetime.min.replace(tzinfo=timezone.utc), reverse=direction < 0)
        return dict(matches[0])

    def find(self, query: dict):
        return _FakeCursor([dict(d) for d in self.docs if _match(d, query)])

    async def find_one_and_update(self, query: dict, update: dict):
        for idx, doc in enumerate(self.docs):
            if _match(doc, query):
                for key, value in (update.get("$set") or {}).items():
                    doc[key] = value
                self.docs[idx] = doc
                return dict(doc)
        return None

    async def update_many(self, query: dict, update: dict):
        count = 0
        for doc in self.docs:
            if _match(doc, query):
                for key, value in (update.get("$set") or {}).items():
                    doc[key] = value
                count += 1
        return type("R", (), {"modified_count": count})()

    async def delete_many(self, query: dict):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _match(d, query)]
        return type("R", (), {"deleted_count": before - len(self.docs)})()

    async def create_index(self, *_args, **_kwargs):
        return "ok"


def _match(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = doc.get(key)
        if key == "_id" and isinstance(expected, dict) and "$in" in expected:
            if actual not in expected["$in"]:
                return False
            continue
        if isinstance(expected, dict):
            if "$lte" in expected:
                if actual is None or actual > expected["$lte"]:
                    return False
                continue
            if "$in" in expected:
                if actual not in expected["$in"]:
                    return False
                continue
        if actual != expected:
            return False
    return True


@pytest.fixture
def fake_mongo(monkeypatch):
    store = {
        TASKS_COLLECTION: _FakeCollection(),
        EMAILS_COLLECTION: _FakeCollection(),
        BRIEFS_COLLECTION: _FakeCollection(),
        TELEMETRY_COLLECTION: _FakeCollection(),
    }

    def get_collection(name: str):
        return store[name]

    monkeypatch.setattr("app.modules.office_ai.models.get_collection", get_collection)
    monkeypatch.setattr("app.modules.office_ai.services.task_service.get_collection", get_collection)
    monkeypatch.setattr("app.modules.office_ai.services.email_service.get_collection", get_collection)
    monkeypatch.setattr("app.modules.office_ai.services.brief_service.get_collection", get_collection)
    monkeypatch.setattr("app.modules.office_ai.retention.get_collection", get_collection)
    monkeypatch.setattr("app.modules.office_ai.models._indexes_ready", True)
    return store


@pytest.mark.asyncio
async def test_task_crud_is_tenant_scoped(fake_mongo):
    user_a = {"sub": "ua"}
    user_b = {"sub": "ub"}
    t1 = await task_service.create_task(tenant_id="tenant-a", user=user_a, title="A task")
    await task_service.create_task(tenant_id="tenant-b", user=user_b, title="B task")

    listed = await task_service.list_tasks(tenant_id="tenant-a")
    assert len(listed) == 1
    assert listed[0]["title"] == "A task"
    assert listed[0]["source"] == "manual"

    updated = await task_service.update_task(
        tenant_id="tenant-a",
        user=user_a,
        task_id=t1["id"],
        updates={"status": "done", "change_reason": "finished"},
    )
    assert updated["status"] == "done"
    assert updated["change_reason"] == "finished"
    assert updated["updated_by"] == "ua"

    # Cross-tenant update must not touch the other tenant's row
    missing = await task_service.update_task(
        tenant_id="tenant-b",
        user=user_b,
        task_id=t1["id"],
        updates={"status": "cancelled"},
    )
    assert missing is None


@pytest.mark.asyncio
async def test_email_summarize_persists_and_links_tasks(fake_mongo, monkeypatch):
    async def fake_summarize(**kwargs):
        return {
            "ai_available": True,
            "summary": "Follow up on PO",
            "action_items": ["Send signed PO", "Confirm delivery"],
            "prompt_version": "summarize_email_v1",
            "telemetry_id": str(ObjectId()),
            "provider": "fake",
            "model": "fake",
            "error_code": None,
            "advisory": "advisory",
        }

    monkeypatch.setattr("app.modules.office_ai.services.email_service.orchestrator.summarize_email", fake_summarize)

    result = await email_service.summarize_and_optionally_persist(
        tenant_id="tenant-a",
        user={"sub": "ua"},
        raw_text="Please send the PO by Friday.",
        persist=True,
        create_tasks=True,
    )
    assert result["email"]["summary"] == "Follow up on PO"
    assert len(result["saved_tasks"]) == 2
    assert all(t["source"] == "ai" for t in result["saved_tasks"])
    assert all(t["tenant_id"] == "tenant-a" for t in result["saved_tasks"])

    other = await email_service.list_emails(tenant_id="tenant-b")
    assert other == []


@pytest.mark.asyncio
async def test_brief_standalone_without_connectors(fake_mongo, monkeypatch):
    async def fake_brief(**kwargs):
        return {
            "ai_available": False,
            "content": "Daily brief fallback\n## open_tasks\n[]\nAdvisory: review.",
            "prompt_version": "daily_brief_v1",
            "telemetry_id": str(ObjectId()),
            "provider": "null",
            "model": "none",
            "error_code": "missing_api_key",
            "advisory": "advisory",
        }

    monkeypatch.setattr("app.modules.office_ai.services.brief_service.orchestrator.build_daily_brief", fake_brief)

    result = await brief_service.generate_brief(
        tenant_id="tenant-standalone",
        app_key="officemitra",
        tenant={"enabled_modules": ["office_ai", "audit"]},
        user={"sub": "ua"},
        session=None,
    )
    assert result["deployment_mode"] == "standalone"
    assert result["connectors_loaded"] == []
    assert result["brief"]["brief_date"]
    assert result["brief"]["generation_id"]

    today = await brief_service.get_today_brief(tenant_id="tenant-standalone")
    assert today["generation_id"] == result["brief"]["generation_id"]
    assert await brief_service.get_today_brief(tenant_id="other") is None


@pytest.mark.asyncio
async def test_retention_purges_old_emails_and_telemetry(fake_mongo):
    from app.modules.office_ai import retention as retention_mod

    old = datetime.now(timezone.utc) - timedelta(days=120)
    new = datetime.now(timezone.utc)
    fake_mongo[EMAILS_COLLECTION].docs = [
        {"_id": ObjectId(), "tenant_id": "t1", "created_at": old, "raw_text": "old"},
        {"_id": ObjectId(), "tenant_id": "t1", "created_at": new, "raw_text": "new"},
        {"_id": ObjectId(), "tenant_id": "t2", "created_at": old, "raw_text": "other"},
    ]
    fake_mongo[TELEMETRY_COLLECTION].docs = [
        {"_id": ObjectId(), "tenant_id": "t1", "created_at": old, "feature": "tasks"},
        {"_id": ObjectId(), "tenant_id": "t1", "created_at": new, "feature": "email"},
    ]

    result = await retention_mod.cleanup_expired_office_ai_records(tenant_id="t1", retention_days=90)
    assert result["emails_deleted"] == 1
    assert result["telemetry_deleted"] == 1
    assert len(fake_mongo[EMAILS_COLLECTION].docs) == 2  # t1 new + t2 old
    assert len(fake_mongo[TELEMETRY_COLLECTION].docs) == 1
