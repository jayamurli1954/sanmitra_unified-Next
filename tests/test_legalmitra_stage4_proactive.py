"""LegalMitra Stage 4 — Proactive Assistant service tests."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.modules.legal import practice_service as practice
from app.modules.legal import proactive_service as proactive
from app.modules.legal.practice_schemas import (
    ClientCreateRequest,
    MatterCreateRequest,
    MatterDocumentCreateRequest,
    MatterStatus,
)
from app.modules.legal.proactive_schemas import (
    AlertUpdateRequest,
    MorningBriefGenerateRequest,
)


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
                matched = True
                break
        if not matched and upsert:
            new_doc = dict(flt)
            new_doc.update(update.get("$set", {}))
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
    monkeypatch.setattr(practice, "log_audit_event", _noop_audit)
    monkeypatch.setattr(proactive, "log_audit_event", _noop_audit)
    return cols


async def _noop_audit(**_kwargs):
    return "evt"


async def _seed_matter(fake_db, *, deadline=None, hearing=None, status=MatterStatus.ACTIVE, title="SCN reply"):
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
            practice_area="gst",
            status=status,
            next_deadline_date=deadline,
            next_hearing_date=hearing,
            priority="high",
        ),
    )
    return client, matter


@pytest.mark.asyncio
async def test_empty_tenant_morning_brief_is_honest(fake_db):
    brief = await proactive.generate_morning_brief(
        tenant_id="tenant-empty",
        app_key="legalmitra",
        user_id="user-1",
        payload=MorningBriefGenerateRequest(force_refresh=True),
    )
    assert brief["empty_practice"] is True
    assert brief["human_review_required"] is True
    assert brief["practice_health_score"] == 100
    assert "No practice data" in " ".join(brief["sections"]["limitations"])
    assert brief["sections"]["priority_actions"] == []


@pytest.mark.asyncio
async def test_deadline_alert_and_priority_sorted_brief(fake_db):
    today = date.today()
    await _seed_matter(fake_db, deadline=today - timedelta(days=1), title="Overdue GST reply")
    await _seed_matter(fake_db, deadline=today + timedelta(days=5), title="Later GST reply")

    result = await proactive.refresh_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
    )
    assert result["open_alerts"] >= 2

    alerts = await proactive.list_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", status="open"
    )
    assert any(a["alert_type"] == "deadline_approaching" for a in alerts)
    assert alerts[0]["priority_score"] >= alerts[-1]["priority_score"]
    assert alerts[0]["suggested_actions"]
    assert alerts[0]["recommended_action"]

    brief = await proactive.generate_morning_brief(
        tenant_id="tenant-a",
        app_key="legalmitra",
        user_id="user-1",
        payload=MorningBriefGenerateRequest(force_refresh=True),
    )
    assert brief["empty_practice"] is False
    assert 0 <= brief["practice_health_score"] <= 100
    assert brief["practice_health_label"]
    actions = brief["sections"]["priority_actions"]
    assert actions
    assert actions[0]["priority_score"] >= actions[-1]["priority_score"]
    assert "Never invent hearings" in " ".join(brief["sections"]["limitations"])


@pytest.mark.asyncio
async def test_dormant_matter_alert(fake_db):
    client, matter = await _seed_matter(fake_db, title="Silent engagement")
    # Backdate matter + timeline activity beyond dormant threshold.
    matters = fake_db["legal_matters"]
    old = datetime.now(timezone.utc) - timedelta(days=60)
    for doc in matters.docs:
        if doc["matter_id"] == matter["matter_id"]:
            doc["updated_at"] = old
            doc["created_at"] = old
    for doc in fake_db["legal_matter_timeline"].docs:
        if doc.get("matter_id") == matter["matter_id"]:
            doc["occurred_at"] = old
            doc["created_at"] = old

    await proactive.refresh_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
    )
    alerts = await proactive.list_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", status="open"
    )
    assert any(a["alert_type"] == "dormant_matter" for a in alerts)


@pytest.mark.asyncio
async def test_missing_documents_alert(fake_db):
    await _seed_matter(fake_db, title="No docs yet")
    await proactive.refresh_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
    )
    alerts = await proactive.list_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", status="open"
    )
    assert any(a["alert_type"] == "compliance_gap_missing_documents" for a in alerts)

    # Attach a document and refresh — gap should auto-resolve.
    matter_id = alerts[0]["matter_id"]
    # find the matter without docs
    for a in alerts:
        if a["alert_type"] == "compliance_gap_missing_documents":
            matter_id = a["matter_id"]
            break
    await practice.attach_matter_document(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter_id,
        created_by="user-1",
        payload=MatterDocumentCreateRequest(filename="order.pdf", doc_type="order"),
    )
    await proactive.refresh_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
    )
    open_alerts = await proactive.list_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", status="open"
    )
    assert not any(
        a["alert_type"] == "compliance_gap_missing_documents" and a["matter_id"] == matter_id
        for a in open_alerts
    )


@pytest.mark.asyncio
async def test_alert_tenant_isolation_and_dismiss(fake_db):
    await _seed_matter(fake_db, deadline=date.today(), title="Tenant A matter")
    await proactive.refresh_practice_alerts(
        tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
    )
    assert await proactive.list_practice_alerts(tenant_id="tenant-b", app_key="legalmitra") == []

    alerts = await proactive.list_practice_alerts(tenant_id="tenant-a", app_key="legalmitra")
    updated = await proactive.update_practice_alert(
        tenant_id="tenant-a",
        app_key="legalmitra",
        alert_id=alerts[0]["alert_id"],
        actor_id="user-1",
        payload=AlertUpdateRequest(status="dismissed"),
    )
    assert updated["status"] == "dismissed"


@pytest.mark.asyncio
async def test_proactive_disabled_flag(fake_db, monkeypatch):
    class _S:
        LEGALMITRA_PROACTIVE_ENABLED = False
        LEGALMITRA_MORNING_BRIEF_ENABLED = False
        LEGALMITRA_ALERT_LOOKAHEAD_DAYS = 7
        LEGALMITRA_DORMANT_MATTER_DAYS = 45
        LEGALMITRA_STALE_REVIEW_DAYS = 7

    monkeypatch.setattr(proactive, "get_settings", lambda: _S())
    with pytest.raises(proactive.ProactiveDisabledError):
        await proactive.refresh_practice_alerts(
            tenant_id="tenant-a", app_key="legalmitra", actor_id="user-1"
        )
