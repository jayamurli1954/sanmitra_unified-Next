"""OfficeMitra Phase 6 — workflow engine (ADR-009)."""
from __future__ import annotations

import pytest
from bson import ObjectId

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_workflows_enabled,
    require_module_feature,
)
from app.modules.office_ai.actions import EXECUTOR_VERSION, list_registered_actions
from app.modules.office_ai.models import (
    NOTIFICATIONS_COLLECTION,
    TASKS_COLLECTION,
    WORKFLOW_RUNS_COLLECTION,
    WORKFLOW_TEMPLATES_COLLECTION,
)
from app.modules.office_ai.services import workflow_service


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
        NOTIFICATIONS_COLLECTION: _FakeCollection(),
        WORKFLOW_TEMPLATES_COLLECTION: _FakeCollection(),
        WORKFLOW_RUNS_COLLECTION: _FakeCollection(),
        "core_audit_logs": _FakeCollection(),
    }

    def get_collection(name: str):
        if name not in store:
            store[name] = _FakeCollection()
        return store[name]

    for target in (
        "app.modules.office_ai.models.get_collection",
        "app.modules.office_ai.services.task_service.get_collection",
        "app.modules.office_ai.services.notification_service.get_collection",
        "app.modules.office_ai.services.workflow_service.get_collection",
        "app.core.audit.service.get_collection",
    ):
        monkeypatch.setattr(target, get_collection)
    monkeypatch.setattr("app.modules.office_ai.models._indexes_ready", True)
    return store


def test_workflows_feature_is_opt_in_not_parent_default():
    with pytest.raises(ModuleAccessError, match="office_ai.workflows"):
        require_module_feature(
            module_key="office_ai",
            feature="workflows",
            organization_type="BUSINESS",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )
    require_module_feature(
        module_key="office_ai",
        feature="workflows",
        organization_type="BUSINESS",
        enabled_modules=["office_ai", "office_ai.workflows"],
        app_key="officemitra",
    )
    assert is_office_ai_workflows_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_workflows_enabled(enabled_modules=["office_ai", "office_ai.workflows"]) is True


def test_create_notification_action_is_registered():
    assert "create_task" in list_registered_actions()
    assert "create_notification" in list_registered_actions()


@pytest.mark.asyncio
async def test_template_run_separation_and_step_diagnostics(fake_mongo):
    user = {"sub": "u1", "tenant_id": "t1"}
    template = await workflow_service.create_template(
        tenant_id="t1",
        user=user,
        name="Daily follow-up",
        continue_on_failure=False,
        steps=[
            {
                "step_id": "task",
                "action_type": "create_task",
                "payload": {"title": "Follow up client", "notes": "WF"},
            },
            {
                "step_id": "notify",
                "action_type": "create_notification",
                "payload": {"title": "Follow-up created", "kind": "workflow_ready"},
            },
        ],
    )
    assert template["template_key"]
    assert template["version"] == 1
    assert template["created_by"] == "u1"
    assert len(template["steps"]) == 2

    result = await workflow_service.start_run(
        tenant_id="t1",
        user=user,
        template_id=template["id"],
        trigger_source="manual",
        idempotency_key="t1-daily-followup-20260811",
    )
    assert result["idempotent_replay"] is False
    run = result["run"]
    assert run["status"] == "applied"
    assert run["trigger_source"] == "manual"
    assert run["idempotency_key"] == "t1-daily-followup-20260811"
    assert run["template_version"] == 1
    assert len(run["step_results"]) == 2
    for step in run["step_results"]:
        assert step["status"] == "applied"
        assert step["duration_ms"] is not None
        assert step["retry_count"] == 0
        assert step["executor_version"] == EXECUTOR_VERSION
        assert step["error_message"] is None
    assert len(fake_mongo[TASKS_COLLECTION].docs) == 1
    assert len(fake_mongo[NOTIFICATIONS_COLLECTION].docs) == 1


@pytest.mark.asyncio
async def test_idempotency_returns_existing_run(fake_mongo):
    user = {"sub": "u1"}
    template = await workflow_service.create_template(
        tenant_id="t1",
        user=user,
        name="Idempotent demo",
        steps=[{"action_type": "create_task", "payload": {"title": "Once"}}],
    )
    first = await workflow_service.start_run(
        tenant_id="t1",
        user=user,
        template_id=template["id"],
        idempotency_key="same-key",
        trigger_source="api",
    )
    second = await workflow_service.start_run(
        tenant_id="t1",
        user=user,
        template_id=template["id"],
        idempotency_key="same-key",
        trigger_source="api",
    )
    assert second["idempotent_replay"] is True
    assert second["run"]["id"] == first["run"]["id"]
    assert len(fake_mongo[TASKS_COLLECTION].docs) == 1
    assert len(fake_mongo[WORKFLOW_RUNS_COLLECTION].docs) == 1


@pytest.mark.asyncio
async def test_stop_on_failure_skips_remaining_steps(fake_mongo, monkeypatch):
    user = {"sub": "u1"}
    template = await workflow_service.create_template(
        tenant_id="t1",
        user=user,
        name="Fail then stop",
        continue_on_failure=False,
        steps=[
            {"step_id": "a", "action_type": "create_task", "payload": {"title": "A"}},
            {"step_id": "b", "action_type": "create_notification", "payload": {"title": "B"}},
        ],
    )

    async def boom(**_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(
        "app.modules.office_ai.services.workflow_service.execute_action",
        boom,
    )
    result = await workflow_service.start_run(
        tenant_id="t1",
        user=user,
        template_id=template["id"],
        trigger_source="proposal",
    )
    run = result["run"]
    assert run["status"] == "failed"
    assert run["trigger_source"] == "proposal"
    assert run["step_results"][0]["status"] == "failed"
    assert run["step_results"][0]["error_message"]
    assert run["step_results"][0]["executor_version"] == EXECUTOR_VERSION
    assert run["step_results"][1]["status"] == "skipped"


@pytest.mark.asyncio
async def test_tenant_isolation_on_templates(fake_mongo):
    await workflow_service.create_template(
        tenant_id="tenant-a",
        user={"sub": "a"},
        name="A only",
        steps=[{"action_type": "create_task", "payload": {"title": "A"}}],
    )
    items = await workflow_service.list_templates(tenant_id="tenant-b")
    assert items == []
    missing = await workflow_service.get_template(
        tenant_id="tenant-b",
        template_id=str(fake_mongo[WORKFLOW_TEMPLATES_COLLECTION].docs[0]["_id"]),
    )
    assert missing is None


def test_shared_workspace_mentions_workflows():
    from pathlib import Path

    shared = Path("frontend/shared/office-ai-workspace.js").read_text(encoding="utf-8")
    assert "workflowsEnabled" in shared
    assert "refresh-workflows" in shared
    assert "ADR-009" in shared
