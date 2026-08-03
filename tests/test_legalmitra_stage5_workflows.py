"""LegalMitra Stage 5 — Agentic Workflows service tests."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.modules.legal import practice_service as practice
from app.modules.legal import proactive_service as proactive
from app.modules.legal import workflow_service as workflows
from app.modules.legal import extract_service as extracts
from app.modules.legal.practice_schemas import (
    ClientCreateRequest,
    MatterCreateRequest,
    MatterStatus,
)
from app.modules.legal.workflow_schemas import (
    ReadyToFileRequest,
    WorkflowRunCreateRequest,
    WorkflowStepRejectRequest,
)
from app.modules.legal.workflow_adapters import adapter_matter_intake
from bson import encode


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        reverse = direction < 0

        def _key(row):
            value = row.get(field)
            if value is None:
                return (1, 0, "")
            if isinstance(value, (int, float)):
                return (0, float(value), "")
            return (0, 0, str(value))

        self._docs.sort(key=_key, reverse=reverse)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self._docs)
        return list(self._docs[:length])


class FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []
        self.seq = 0

    async def create_index(self, *_a, **_k):
        return None

    @staticmethod
    def _match(doc, flt):
        return all(doc.get(k) == v for k, v in flt.items())

    async def find_one(self, flt):
        for d in self.docs:
            if self._match(d, flt):
                return dict(d)
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if self._match(d, flt))

    async def update_one(self, flt, update, upsert=False):
        matched = False
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                for key, amount in (update.get("$inc") or {}).items():
                    d[key] = int(d.get(key) or 0) + int(amount)
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
            for key, amount in (update.get("$inc") or {}).items():
                new_doc[key] = int(amount)
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        return {**filters, "seq": self.seq}


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(practice, "get_collection", _get)
    monkeypatch.setattr(proactive, "get_collection", _get)
    monkeypatch.setattr(workflows, "get_collection", _get)
    monkeypatch.setattr(extracts, "get_collection", _get)
    monkeypatch.setattr(practice, "log_audit_event", _noop_audit)
    monkeypatch.setattr(proactive, "log_audit_event", _noop_audit)
    monkeypatch.setattr(workflows, "log_audit_event", _noop_audit)
    monkeypatch.setattr(extracts, "log_audit_event", _noop_audit)
    return cols


async def _noop_audit(**_kwargs):
    return "evt"


async def _seed_matter(
    *,
    practice_area="gst",
    jurisdiction="India — CGST",
    title="GST SCN reply",
):
    client = await practice.create_client(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=ClientCreateRequest(display_name="Acme Ltd"),
    )
    matter = await practice.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title=title,
            status=MatterStatus.ACTIVE,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            next_deadline_date=date.today() + timedelta(days=2),
        ),
    )
    return matter


def _latest(steps, key):
    rows = [s for s in steps if s["step_key"] == key]
    return max(rows, key=lambda s: int(s.get("attempt") or 1))


def test_bson_safe_encodes_python_dates():
    payload = workflows._bson_safe(
        {"hearing": date(2026, 5, 23), "nested": {"deadline": date(2026, 4, 15)}}
    )
    encode(payload)
    assert payload["hearing"] == "2026-05-23"
    assert payload["nested"]["deadline"] == "2026-04-15"


def test_as_utc_datetime_accepts_naive_mongo_datetimes():
    from datetime import datetime, timezone

    finished = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    started = datetime(2026, 8, 3, 11, 0)  # naive, as Motor often returns
    normalized = workflows._as_utc_datetime(started)
    assert normalized is not None
    assert (finished - normalized).total_seconds() == 3600


@pytest.mark.asyncio
async def test_intake_artifact_payload_is_bson_encodable(fake_db):
    matter = await _seed_matter()
    result = await adapter_matter_intake(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        workflow_template="general",
    )
    encode({"payload": result["payload"], "sources": result["sources"]})
    assert isinstance(result["payload"].get("next_deadline_date"), (str, type(None)))


@pytest.mark.asyncio
async def test_catalog_and_recommend_mapping(fake_db):
    catalog = await workflows.get_workflow_catalog()
    assert catalog["count"] >= 1
    assert any(i["workflow_key"] == "prepare_matter_response" for i in catalog["items"])
    rec = workflows.recommend_workflow_for(
        alert_type="deadline_approaching", practice_area="gst", title="GST appeal"
    )
    assert rec["workflow_key"] == "prepare_matter_response"
    assert rec["workflow_template"] == "gst_notice"


@pytest.mark.asyncio
async def test_prepare_matter_response_e2e_with_human_gates(fake_db):
    matter = await _seed_matter()
    run = await workflows.create_workflow_run(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=WorkflowRunCreateRequest(
            matter_id=matter["matter_id"],
            recommended_from="morning_brief",
            workflow_template="general",
        ),
        auto_advance=True,
    )
    assert run["status"] == "awaiting_human"
    assert run["workflow_template"] == "gst_notice"  # practice_area hint
    research = _latest(run["steps"], "RESEARCH")
    assert research["status"] == "awaiting_human"
    assert research["confidence"] is not None
    assert research["estimated_minutes"] == 6

    arts = await workflows.list_run_artifacts(
        tenant_id="tenant-a", app_key="legalmitra", run_id=run["run_id"]
    )
    research_art = next(
        a for a in arts["items"] if a["artifact_type"] == "research_response"
    )
    assert research_art["payload"].get("citations") == []
    limitations = " ".join(research_art["payload"].get("limitations") or []).lower()
    assert "fabricated" in limitations or "invent" in limitations

    run = await workflows.approve_workflow_step(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        step_id=research["step_id"],
        auto_advance=True,
    )
    draft = _latest(run["steps"], "DRAFT")
    assert draft["status"] == "awaiting_human"
    assert draft["human_review_required"] is True

    run = await workflows.approve_workflow_step(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        step_id=draft["step_id"],
        auto_advance=True,
    )
    human = _latest(run["steps"], "HUMAN_REVIEW")
    assert human["status"] == "awaiting_human"

    run = await workflows.approve_workflow_step(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        step_id=human["step_id"],
        auto_advance=True,
    )
    assert run["status"] == "completed"
    assert run["ready_to_file"] is False
    assert run["approval_count"] >= 3
    assert run["total_duration_ms"] is not None

    timeline = await workflows.list_run_timeline(
        tenant_id="tenant-a", app_key="legalmitra", run_id=run["run_id"]
    )
    types = {e["event_type"] for e in timeline["items"]}
    assert "run_completed" in types
    assert "human_approved" in types

    run = await workflows.set_ready_to_file(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        payload=ReadyToFileRequest(ready_to_file=True, confirm=True),
    )
    assert run["ready_to_file"] is True


@pytest.mark.asyncio
async def test_research_refuses_without_jurisdiction(fake_db):
    matter = await _seed_matter(jurisdiction=None, practice_area="general", title="Advisory")
    run = await workflows.create_workflow_run(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=WorkflowRunCreateRequest(matter_id=matter["matter_id"]),
        auto_advance=True,
    )
    research = _latest(run["steps"], "RESEARCH")
    assert research["status"] == "awaiting_human"
    assert research["failure_class"] == "requires_human"
    arts = await workflows.list_run_artifacts(
        tenant_id="tenant-a", app_key="legalmitra", run_id=run["run_id"]
    )
    payload = next(a["payload"] for a in arts["items"] if a["artifact_type"] == "research_response")
    assert payload.get("citations") == []
    assert payload.get("strategy") == "insufficient_sources"


@pytest.mark.asyncio
async def test_reject_and_retry_creates_new_attempt(fake_db):
    matter = await _seed_matter()
    run = await workflows.create_workflow_run(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=WorkflowRunCreateRequest(matter_id=matter["matter_id"]),
    )
    research = _latest(run["steps"], "RESEARCH")
    run = await workflows.reject_workflow_step(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        step_id=research["step_id"],
        payload=WorkflowStepRejectRequest(reason="Need stronger authorities"),
    )
    rejected = _latest(run["steps"], "RESEARCH")
    # After reject, latest attempt is rejected; retry adds attempt 2.
    assert rejected["status"] == "rejected"
    run = await workflows.retry_workflow_step(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        run_id=run["run_id"],
        step_id=research["step_id"],
    )
    research2 = _latest(run["steps"], "RESEARCH")
    assert research2["attempt"] == 2
    assert research2["status"] == "awaiting_human"
    assert run["retry_count"] >= 1


@pytest.mark.asyncio
async def test_tenant_isolation_on_runs(fake_db):
    matter = await _seed_matter()
    run = await workflows.create_workflow_run(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=WorkflowRunCreateRequest(matter_id=matter["matter_id"]),
    )
    with pytest.raises(workflows.WorkflowNotFoundError):
        await workflows.get_workflow_run(
            tenant_id="tenant-b",
            app_key="legalmitra",
            run_id=run["run_id"],
        )


@pytest.mark.asyncio
async def test_morning_brief_includes_recommended_workflow(fake_db):
    await _seed_matter()
    brief = await proactive.generate_morning_brief(
        tenant_id="tenant-a",
        app_key="legalmitra",
        user_id="user-1",
    )
    actions = brief["sections"]["priority_actions"]
    assert actions
    assert actions[0].get("recommended_workflow", {}).get("workflow_key") == (
        "prepare_matter_response"
    )


@pytest.mark.asyncio
async def test_no_file_send_on_complete_artifact(fake_db):
    matter = await _seed_matter()
    run = await workflows.create_workflow_run(
        tenant_id="tenant-a",
        app_key="legalmitra",
        actor_id="user-1",
        payload=WorkflowRunCreateRequest(matter_id=matter["matter_id"]),
    )
    for key in ("RESEARCH", "DRAFT", "HUMAN_REVIEW"):
        step = _latest(run["steps"], key)
        if step["status"] != "awaiting_human":
            # advance if somehow not blocked
            run = await workflows.advance_workflow_run(
                tenant_id="tenant-a",
                app_key="legalmitra",
                actor_id="user-1",
                run_id=run["run_id"],
                until_blocked=True,
            )
            step = _latest(run["steps"], key)
        run = await workflows.approve_workflow_step(
            tenant_id="tenant-a",
            app_key="legalmitra",
            actor_id="user-1",
            run_id=run["run_id"],
            step_id=step["step_id"],
        )
    assert run["status"] == "completed"
    arts = await workflows.list_run_artifacts(
        tenant_id="tenant-a", app_key="legalmitra", run_id=run["run_id"]
    )
    complete = next(
        a for a in arts["items"] if (a.get("payload") or {}).get("completed") is True
    )
    assert complete["payload"].get("filed") is False
    assert complete["payload"].get("sent") is False
    assert complete["payload"].get("ready_to_file") is False


@pytest.mark.asyncio
async def test_feature_flag_disables_workflows(fake_db, monkeypatch):
    class _Settings:
        LEGALMITRA_AGENTIC_ENABLED = False

    monkeypatch.setattr(workflows, "get_settings", lambda: _Settings())
    with pytest.raises(workflows.WorkflowDisabledError):
        await workflows.get_workflow_catalog()
