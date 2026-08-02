"""LegalMitra Stage 3 — Matter & Client Intelligence service tests.

Uses in-memory FakeCollection so no real Mongo is required.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.modules.legal import practice_service as svc
from app.modules.legal.practice_schemas import (
    ClientCreateRequest,
    ClientUpdateRequest,
    MatterBriefGenerateRequest,
    MatterCreateRequest,
    MatterDocumentCreateRequest,
    MatterStatus,
    MatterUpdateRequest,
    TimelineEventCreateRequest,
)


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        reverse = direction < 0
        self._docs.sort(key=lambda row: row.get(field) or "", reverse=reverse)
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

    async def create_index(self, *_args, **_kwargs):
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
            new_doc.update(update.get("$setOnInsert", {}))
            self.docs.append(new_doc)

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        return {**filters, "seq": self.seq}


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(svc, "get_collection", _get)
    return cols


@pytest.fixture
def captured_audit(monkeypatch):
    events: list[dict] = []

    async def _fake_log(**kwargs):
        events.append(kwargs)
        return "evt"

    monkeypatch.setattr(svc, "log_audit_event", _fake_log)
    return events


def _client_payload(**over):
    base = dict(
        display_name="Acme Traders Pvt Ltd",
        client_type="organization",
        email="accounts@acme.example",
        pan="ABCDE1234F",
        gstin="27ABCDE1234F1Z5",
    )
    base.update(over)
    return ClientCreateRequest(**base)


async def _seed_client(fake_db, captured_audit, **over):
    return await svc.create_client(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=_client_payload(**over),
    )


# ── Clients ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_client_crud_roundtrip(fake_db, captured_audit):
    created = await _seed_client(fake_db, captured_audit)
    assert created["client_id"]
    assert created["display_name"] == "Acme Traders Pvt Ltd"
    assert created["pan"] == "ABCDE1234F"

    listed = await svc.list_clients(tenant_id="tenant-a", app_key="legalmitra")
    assert len(listed) == 1

    got = await svc.get_client(
        tenant_id="tenant-a", app_key="legalmitra", client_id=created["client_id"]
    )
    assert got["email"] == "accounts@acme.example"

    updated = await svc.update_client(
        tenant_id="tenant-a",
        app_key="legalmitra",
        client_id=created["client_id"],
        updated_by="user-1",
        payload=ClientUpdateRequest(notes="Key GST client"),
    )
    assert updated["notes"] == "Key GST client"
    assert any(e["action"] == "legal_client_created" for e in captured_audit)
    assert any(e["action"] == "legal_client_updated" for e in captured_audit)


@pytest.mark.asyncio
async def test_client_tenant_isolation(fake_db, captured_audit):
    await _seed_client(fake_db, captured_audit)
    other = await svc.list_clients(tenant_id="tenant-b", app_key="legalmitra")
    assert other == []


# ── Matters ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_matter_create_assigns_number_and_timeline(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    matter = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="GST SCN reply — FY 2024-25",
            practice_area="gst",
            status=MatterStatus.DRAFT,
            court="GST Dept, Mumbai",
            next_deadline_date=date(2026, 8, 20),
        ),
    )
    assert matter["matter_number"].startswith("GST-2026-")
    assert matter["client_name"] == "Acme Traders Pvt Ltd"
    assert matter["status"] == "draft"
    assert matter["priority"] == "normal"

    timeline = await svc.list_matter_timeline(
        tenant_id="tenant-a", app_key="legalmitra", matter_id=matter["matter_id"]
    )
    assert any(e["event_type"] == "matter_created" for e in timeline)


@pytest.mark.asyncio
async def test_matter_status_lifecycle_and_reject_invalid(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    matter = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Income Tax notice response",
            practice_area="income_tax",
        ),
    )
    active = await svc.update_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        updated_by="user-1",
        payload=MatterUpdateRequest(status=MatterStatus.ACTIVE),
    )
    assert active["status"] == "active"

    with pytest.raises(svc.PracticeValidationError):
        await svc.update_matter(
            tenant_id="tenant-a",
            app_key="legalmitra",
            matter_id=matter["matter_id"],
            updated_by="user-1",
            payload=MatterUpdateRequest(status=MatterStatus.DRAFT),
        )


@pytest.mark.asyncio
async def test_one_client_multiple_engagements(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    lit = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Civil suit — recovery",
            practice_area="litigation",
            matter_type="litigation",
        ),
    )
    gst = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="GST advisory retainer",
            practice_area="gst",
            matter_type="advisory",
        ),
    )
    assert lit["matter_number"].startswith("LIT-")
    assert gst["matter_number"].startswith("GST-")
    items = await svc.list_matters(
        tenant_id="tenant-a", app_key="legalmitra", client_id=client["client_id"]
    )
    assert len(items) == 2


@pytest.mark.asyncio
async def test_matter_tenant_isolation(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Secretarial annual compliance",
            practice_area="secretarial",
        ),
    )
    assert await svc.list_matters(tenant_id="tenant-b", app_key="legalmitra") == []


# ── Documents / timeline / briefs / dashboard ────────────────────────────────


@pytest.mark.asyncio
async def test_document_attach_timeline_and_brief(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    matter = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Contract review — SaaS MSA",
            practice_area="contract",
            status=MatterStatus.ACTIVE,
            jurisdiction="India",
            next_hearing_date=date(2026, 9, 1),
        ),
    )
    doc = await svc.attach_matter_document(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        created_by="user-1",
        payload=MatterDocumentCreateRequest(
            filename="msa-draft-v1.pdf",
            doc_type="contract",
            notes="Client draft for review",
        ),
    )
    assert doc["document_id"]

    await svc.add_matter_timeline_event(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        actor_id="user-1",
        payload=TimelineEventCreateRequest(
            event_type="client_meeting",
            summary="Kickoff call with client counsel",
        ),
    )

    brief = await svc.generate_matter_brief(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        generated_by="user-1",
        payload=MatterBriefGenerateRequest(notes_for_brief="Focus on indemnity caps"),
    )
    sections = brief["sections"]
    assert sections["human_review_required"] is True
    assert sections["confidence"] > 0
    assert "Matter Overview".lower().replace(" ", "_") or True
    assert "matter_overview" in sections
    assert "key_facts" in sections
    assert "limitations" in sections
    assert any("msa-draft-v1.pdf" in d for d in sections["documents_reviewed"])
    assert brief["advisory_notice"]
    assert brief["generation_strategy"] == "grounded_matter_summary"

    latest = await svc.get_latest_matter_brief(
        tenant_id="tenant-a", app_key="legalmitra", matter_id=matter["matter_id"]
    )
    assert latest["brief_id"] == brief["brief_id"]

    timeline = await svc.list_matter_timeline(
        tenant_id="tenant-a", app_key="legalmitra", matter_id=matter["matter_id"]
    )
    types = {e["event_type"] for e in timeline}
    assert "document_uploaded" in types
    assert "brief_generated" in types
    assert "client_meeting" in types


@pytest.mark.asyncio
async def test_practice_dashboard_live_widgets(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    matter = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Pending GST reply",
            practice_area="gst",
            status=MatterStatus.PENDING,
            next_hearing_date=date(2026, 8, 15),
            next_deadline_date=date(2026, 8, 10),
        ),
    )
    await svc.attach_matter_document(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        created_by="user-1",
        payload=MatterDocumentCreateRequest(filename="scn.pdf", doc_type="notice"),
    )
    await svc.generate_matter_brief(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        generated_by="user-1",
    )

    dash = await svc.get_practice_dashboard(tenant_id="tenant-a", app_key="legalmitra")
    assert dash["data_source"] == "live"
    assert dash["pending_matters"] == 1
    assert dash["awaiting_review"] >= 1
    assert dash["recent_clients"]
    assert dash["upcoming_hearings"]
    assert dash["upcoming_deadlines"]
    assert dash["recent_documents"]
    assert dash["recent_briefs"]
    assert dash["fees_outstanding"] == "—"


@pytest.mark.asyncio
async def test_archived_matter_is_read_only_except_reopen(fake_db, captured_audit):
    client = await _seed_client(fake_db, captured_audit)
    matter = await svc.create_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        created_by="user-1",
        payload=MatterCreateRequest(
            client_id=client["client_id"],
            title="Closed legacy matter",
            status=MatterStatus.ACTIVE,
        ),
    )
    closed = await svc.update_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        updated_by="user-1",
        payload=MatterUpdateRequest(status=MatterStatus.CLOSED),
    )
    assert closed["status"] == "closed"
    archived = await svc.update_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        updated_by="user-1",
        payload=MatterUpdateRequest(status=MatterStatus.ARCHIVED),
    )
    assert archived["status"] == "archived"

    with pytest.raises(svc.PracticeValidationError):
        await svc.update_matter(
            tenant_id="tenant-a",
            app_key="legalmitra",
            matter_id=matter["matter_id"],
            updated_by="user-1",
            payload=MatterUpdateRequest(title="Should fail"),
        )

    reopened = await svc.update_matter(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id=matter["matter_id"],
        updated_by="user-1",
        payload=MatterUpdateRequest(status=MatterStatus.ACTIVE),
    )
    assert reopened["status"] == "active"
