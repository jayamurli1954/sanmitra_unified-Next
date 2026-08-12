"""OfficeMitra Phase 4 — confirmed write-back proposals + action executor."""
from __future__ import annotations

from typing import Any

import pytest
from bson import ObjectId

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_writeback_enabled,
    require_module_feature,
)
from app.modules.office_ai.actions import execute_action, list_registered_actions
from app.modules.office_ai.models import (
    PROPOSALS_COLLECTION,
    TASKS_COLLECTION,
)
from app.modules.office_ai.services import proposal_service, task_service


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

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if _match(doc, query):
                doc.update(update.get("$set") or {})
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def create_index(self, *_args, **_kwargs):
        return True


def _match(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = doc.get(key)
        if actual != expected:
            return False
    return True


@pytest.fixture
def fake_mongo(monkeypatch):
    store = {
        TASKS_COLLECTION: _FakeCollection(),
        PROPOSALS_COLLECTION: _FakeCollection(),
        "core_audit_logs": _FakeCollection(),
    }

    def get_collection(name: str):
        if name not in store:
            store[name] = _FakeCollection()
        return store[name]

    for target in (
        "app.modules.office_ai.models.get_collection",
        "app.modules.office_ai.services.task_service.get_collection",
        "app.modules.office_ai.services.proposal_service.get_collection",
        "app.core.audit.service.get_collection",
        "app.modules.office_ai.services.notification_service.get_collection",
    ):
        monkeypatch.setattr(target, get_collection)
    monkeypatch.setattr("app.modules.office_ai.models._indexes_ready", True)
    return store


def test_writeback_feature_is_opt_in_not_parent_default():
    with pytest.raises(ModuleAccessError, match="office_ai.writeback"):
        require_module_feature(
            module_key="office_ai",
            feature="writeback",
            organization_type="BUSINESS",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )

    require_module_feature(
        module_key="office_ai",
        feature="writeback",
        organization_type="BUSINESS",
        enabled_modules=["office_ai", "office_ai.writeback"],
        app_key="officemitra",
    )
    assert is_office_ai_writeback_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_writeback_enabled(enabled_modules=["office_ai", "office_ai.writeback"]) is True


def test_action_registry_lists_create_task():
    assert "create_task" in list_registered_actions()
    from app.modules.office_ai.actions import get_action, list_action_descriptors

    spec = get_action("create_task")
    assert spec is not None
    assert spec.capabilities.requires_confirmation is True
    assert spec.capabilities.risk_level == "LOW"
    descriptors = list_action_descriptors()
    assert any(item["action_type"] == "create_task" for item in descriptors)
    assert "capabilities" in descriptors[0]


@pytest.mark.asyncio
async def test_generate_with_writeback_creates_proposals_not_tasks(fake_mongo, monkeypatch):
    async def fake_generate(*, tenant_id, text, user_id):
        return {
            "ai_available": True,
            "tasks": [{"title": "Call vendor", "due_date": None}],
            "prompt_version": "v-test",
            "telemetry_id": None,
        }

    monkeypatch.setattr(
        "app.modules.office_ai.services.task_service.orchestrator.generate_tasks",
        fake_generate,
    )
    user = {"sub": "user-1"}
    result = await task_service.generate_and_optionally_persist(
        tenant_id="tenant-a",
        user=user,
        text="please call vendor",
        persist=True,
        writeback_enabled=True,
    )
    assert result["writeback_enabled"] is True
    assert result["saved_tasks"] == []
    assert len(result["proposals"]) == 1
    assert result["proposals"][0]["action_type"] == "create_task"
    assert result["proposals"][0]["target_module"] == "office_ai"
    assert result["proposals"][0]["status"] == "pending"
    assert result["proposals"][0]["requires_confirmation"] is True
    assert fake_mongo[TASKS_COLLECTION].docs == []
    assert len(fake_mongo[PROPOSALS_COLLECTION].docs) == 1


@pytest.mark.asyncio
async def test_generate_soft_fail_creates_proposals_when_ai_unavailable(fake_mongo, monkeypatch):
    async def fake_generate(*, tenant_id, text, user_id):
        return {
            "ai_available": False,
            "tasks": [],
            "prompt_version": "generate_tasks_v1",
            "telemetry_id": None,
            "provider": "null",
            "error_code": "missing_api_key",
        }

    monkeypatch.setattr(
        "app.modules.office_ai.services.task_service.orchestrator.generate_tasks",
        fake_generate,
    )
    user = {"sub": "user-1"}
    result = await task_service.generate_and_optionally_persist(
        tenant_id="tenant-a",
        user=user,
        text="1) Call vendor tomorrow\n2) Send finance reminder",
        persist=True,
        writeback_enabled=True,
    )
    assert result["ai_available"] is False
    assert result["soft_fail_proposals"] is True
    assert result["saved_tasks"] == []
    assert len(result["proposals"]) == 2
    assert result["proposals"][0]["source_feature"] == "tasks.generate.soft_fail"
    assert result["proposals"][0]["prompt_version"] == "soft_fail_v1"
    assert result["proposals"][0]["payload"]["title"] == "Call vendor tomorrow"
    assert result["proposals"][0]["payload"]["source"] == "manual"
    assert result["proposals"][1]["payload"]["title"] == "Send finance reminder"
    assert fake_mongo[TASKS_COLLECTION].docs == []


@pytest.mark.asyncio
async def test_generate_soft_fail_does_not_persist_without_writeback(fake_mongo, monkeypatch):
    async def fake_generate(*, tenant_id, text, user_id):
        return {
            "ai_available": False,
            "tasks": [],
            "prompt_version": "generate_tasks_v1",
            "error_code": "missing_api_key",
        }

    monkeypatch.setattr(
        "app.modules.office_ai.services.task_service.orchestrator.generate_tasks",
        fake_generate,
    )
    result = await task_service.generate_and_optionally_persist(
        tenant_id="tenant-a",
        user={"sub": "user-1"},
        text="Call vendor tomorrow",
        persist=True,
        writeback_enabled=False,
    )
    assert result["soft_fail_proposals"] is False
    assert result["proposals"] == []
    assert result["saved_tasks"] == []
    assert fake_mongo[TASKS_COLLECTION].docs == []
    assert fake_mongo[PROPOSALS_COLLECTION].docs == []


@pytest.mark.asyncio
async def test_confirm_applies_via_executor_and_dismiss_is_noop(fake_mongo):
    user = {"sub": "user-1"}
    proposals = await proposal_service.create_task_proposals(
        tenant_id="tenant-a",
        user=user,
        tasks=[{"title": "Review brief", "confidence": 0.91, "reasoning": "From AI"}],
    )
    proposal_id = proposals[0]["id"]

    confirmed = await proposal_service.confirm_proposal(
        tenant_id="tenant-a",
        user=user,
        proposal_id=proposal_id,
    )
    assert confirmed["proposal"]["status"] == "applied"
    assert confirmed["result"]["entity_type"] == "officemitra_task"
    assert len(fake_mongo[TASKS_COLLECTION].docs) == 1
    assert fake_mongo[TASKS_COLLECTION].docs[0]["source"] == "ai"
    assert fake_mongo[TASKS_COLLECTION].docs[0]["tenant_id"] == "tenant-a"

    other = await proposal_service.create_task_proposals(
        tenant_id="tenant-a",
        user=user,
        tasks=[{"title": "Skip me"}],
    )
    dismissed = await proposal_service.dismiss_proposal(
        tenant_id="tenant-a",
        user=user,
        proposal_id=other[0]["id"],
    )
    assert dismissed["status"] == "dismissed"
    assert len(fake_mongo[TASKS_COLLECTION].docs) == 1


@pytest.mark.asyncio
async def test_confirm_is_tenant_isolated(fake_mongo):
    user = {"sub": "user-1"}
    proposals = await proposal_service.create_task_proposals(
        tenant_id="tenant-a",
        user=user,
        tasks=[{"title": "Secret"}],
    )
    missing = await proposal_service.confirm_proposal(
        tenant_id="tenant-b",
        user=user,
        proposal_id=proposals[0]["id"],
    )
    assert missing is None
    assert fake_mongo[TASKS_COLLECTION].docs == []


@pytest.mark.asyncio
async def test_executor_rejects_unknown_action():
    with pytest.raises(Exception):
        await execute_action(
            action_type="post_journal",
            tenant_id="tenant-a",
            user={"sub": "u1"},
            payload={},
        )


def test_shared_workspace_mentions_proposals_and_officemitra_app_key():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    shared = (root / "frontend" / "shared" / "office-ai-workspace.js").read_text(encoding="utf-8")
    assert "confirm-proposal" in shared
    assert "writebackEnabled" in shared
    assert 'APP_KEY = "officemitra"' in (root / "frontend" / "officemitra" / "app.js").read_text(encoding="utf-8")
