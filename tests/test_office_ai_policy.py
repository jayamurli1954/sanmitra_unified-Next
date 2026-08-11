"""OfficeMitra ADR-012 policy engine tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.office_ai.actions.registry import (
    ActionCapabilityDescriptor,
    ActionSpec,
    register_action,
)
from app.modules.office_ai.models import PROPOSALS_COLLECTION, TASKS_COLLECTION
from app.modules.office_ai.policy import PolicyContext, evaluate_policy
from app.modules.office_ai.policy.engine import DEFAULT_APPROVAL_EXPIRY_HOURS, compute_approval_expires_at
from app.modules.office_ai.services import proposal_service


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
        if isinstance(expected, dict) and "$in" in expected:
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
    ):
        monkeypatch.setattr(target, get_collection)
    monkeypatch.setattr("app.modules.office_ai.models._indexes_ready", True)
    return store


def test_policy_denies_when_writeback_flag_off():
    decision = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="u1",
            action_type="create_task",
            intent="confirm",
            enabled_modules=["office_ai"],
            required_feature="writeback",
        )
    )
    assert decision.allowed is False
    assert decision.execution_mode == "deny"
    assert decision.decision == "DENY"
    assert decision.rule_id == "POL-002"
    assert "writeback" in decision.reason


def test_policy_requires_confirmation_for_create_task():
    decision = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="u1",
            action_type="create_task",
            intent="propose",
            enabled_modules=["office_ai", "office_ai.writeback"],
        )
    )
    assert decision.allowed is True
    assert decision.execution_mode == "confirmation"
    assert decision.decision == "REQUIRE_CONFIRMATION"
    assert decision.rule_id == "POL-010"
    assert decision.approval_expiry_hours == DEFAULT_APPROVAL_EXPIRY_HOURS


def test_policy_maker_cannot_be_checker():
    decision = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="same-user",
            action_type="create_task",
            intent="approve",
            enabled_modules=["office_ai", "office_ai.writeback"],
            maker_id="same-user",
            allow_self_approval=False,
        )
    )
    # create_task does not require maker-checker → deny with capability rule
    assert decision.allowed is False


def test_policy_maker_checker_enforcement(monkeypatch):
    async def _noop(*_a, **_k):
        return {"entity_type": "x", "entity_id": "1"}

    register_action(
        ActionSpec(
            action_type="high_risk_demo",
            target_module="office_ai",
            description="Demo HIGH risk action",
            handler=_noop,
            capabilities=ActionCapabilityDescriptor(
                requires_confirmation=True,
                requires_maker_checker=True,
                risk_level="HIGH",
            ),
        )
    )
    confirm = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="maker",
            action_type="high_risk_demo",
            intent="confirm",
            enabled_modules=["office_ai", "office_ai.writeback"],
        )
    )
    assert confirm.execution_mode == "maker_checker"
    assert confirm.rule_id == "POL-022"

    deny_self = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="maker",
            action_type="high_risk_demo",
            intent="approve",
            enabled_modules=["office_ai", "office_ai.writeback"],
            maker_id="maker",
        )
    )
    assert deny_self.allowed is False
    assert deny_self.rule_id == "POL-021"

    allow_checker = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="checker",
            action_type="high_risk_demo",
            intent="approve",
            enabled_modules=["office_ai", "office_ai.writeback"],
            maker_id="maker",
        )
    )
    assert allow_checker.allowed is True
    assert allow_checker.rule_id == "POL-023"


def test_policy_approval_expiry():
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    decision = evaluate_policy(
        PolicyContext(
            tenant_id="t1",
            actor_id="u1",
            action_type="create_task",
            intent="confirm",
            enabled_modules=["office_ai", "office_ai.writeback"],
            approval_expires_at=expired,
        )
    )
    assert decision.allowed is False
    assert decision.rule_id == "POL-020"


def test_compute_approval_expires_at():
    start = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
    ends = compute_approval_expires_at(from_time=start, hours=72)
    assert ends == start + timedelta(hours=72)


@pytest.mark.asyncio
async def test_confirm_applies_low_risk_with_policy(fake_mongo):
    proposals = await proposal_service.create_task_proposals(
        tenant_id="t1",
        user={"sub": "u1"},
        tasks=[{"title": "Call client"}],
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    result = await proposal_service.confirm_proposal(
        tenant_id="t1",
        user={"sub": "u1"},
        proposal_id=proposals[0]["id"],
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    assert result["proposal"]["status"] == "applied"
    assert result["policy"]["rule_id"]
    assert len(fake_mongo[TASKS_COLLECTION].docs) == 1


@pytest.mark.asyncio
async def test_maker_checker_flow_and_self_approve_denied(fake_mongo):
    async def _noop(*, tenant_id, user, payload, **_kwargs):
        return {"entity_type": "demo", "entity_id": "x", "payload": payload}

    register_action(
        ActionSpec(
            action_type="high_risk_demo",
            target_module="office_ai",
            description="Demo HIGH risk action",
            handler=_noop,
            capabilities=ActionCapabilityDescriptor(
                requires_confirmation=True,
                requires_maker_checker=True,
                risk_level="HIGH",
            ),
        )
    )
    created = await proposal_service.create_proposals(
        tenant_id="t1",
        user={"sub": "maker"},
        action_type="high_risk_demo",
        items=[{"payload": {"note": "n1"}}],
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    mid = created[0]["id"]
    maker = await proposal_service.confirm_proposal(
        tenant_id="t1",
        user={"sub": "maker"},
        proposal_id=mid,
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    assert maker["proposal"]["status"] == "awaiting_checker"
    assert maker["proposal"]["maker_id"] == "maker"
    assert maker["proposal"]["approval_expires_at"]

    with pytest.raises(Exception) as excinfo:
        await proposal_service.approve_proposal(
            tenant_id="t1",
            user={"sub": "maker"},
            proposal_id=mid,
            enabled_modules=["office_ai", "office_ai.writeback"],
        )
    from app.modules.office_ai.policy import PolicyDeniedError

    assert isinstance(excinfo.value, PolicyDeniedError)
    assert excinfo.value.decision.rule_id == "POL-021"

    approved = await proposal_service.approve_proposal(
        tenant_id="t1",
        user={"sub": "checker"},
        proposal_id=mid,
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    assert approved["proposal"]["status"] == "applied"
    assert approved["proposal"]["checker_id"] == "checker"


@pytest.mark.asyncio
async def test_expired_awaiting_checker_cannot_approve(fake_mongo):
    async def _noop(*, tenant_id, user, payload, **_kwargs):
        return {"entity_type": "demo", "entity_id": "x"}

    register_action(
        ActionSpec(
            action_type="high_risk_demo2",
            target_module="office_ai",
            description="Demo HIGH risk action 2",
            handler=_noop,
            capabilities=ActionCapabilityDescriptor(
                requires_confirmation=True,
                requires_maker_checker=True,
                risk_level="HIGH",
            ),
        )
    )
    created = await proposal_service.create_proposals(
        tenant_id="t1",
        user={"sub": "maker"},
        action_type="high_risk_demo2",
        items=[{"payload": {"note": "n1"}}],
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    mid = created[0]["id"]
    await proposal_service.confirm_proposal(
        tenant_id="t1",
        user={"sub": "maker"},
        proposal_id=mid,
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    # Force expiry in store
    doc = fake_mongo[PROPOSALS_COLLECTION].docs[0]
    doc["approval_expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)

    result = await proposal_service.approve_proposal(
        tenant_id="t1",
        user={"sub": "checker"},
        proposal_id=mid,
        enabled_modules=["office_ai", "office_ai.writeback"],
    )
    assert result["proposal"]["status"] == "expired"


def test_shared_workspace_mentions_policy_and_approve():
    from pathlib import Path

    shared = Path("frontend/shared/office-ai-workspace.js").read_text(encoding="utf-8")
    assert "approve-proposal" in shared
    assert "ADR-008/012" in shared or "ADR-012" in shared
