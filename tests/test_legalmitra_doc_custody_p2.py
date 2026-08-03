"""LegalMitra P2 — matter-paper extracts, chunks, retention, custody gates."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.modules.legal import custody_service
from app.modules.legal import extract_service as svc
from app.modules.legal import practice_service
from app.modules.legal import workflow_adapters
from app.modules.legal.practice_schemas import DocCustodySettingsUpdateRequest


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

    async def create_index(self, *_args, **_kwargs):
        return None

    @staticmethod
    def _match(doc, flt):
        for key, expected in flt.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$lte" in expected:
                    if actual is None or actual > expected["$lte"]:
                        return False
                elif "$type" in expected:
                    continue
                else:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, flt):
        for d in self.docs:
            if self._match(d, flt):
                return dict(d)
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    def find(self, flt):
        return _Cursor([dict(d) for d in self.docs if self._match(d, flt)])

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
        return type("R", (), {"matched_count": 1 if matched or upsert else 0})()

    async def update_many(self, flt, update):
        count = 0
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                count += 1
        return type("R", (), {"matched_count": count})()


@pytest.fixture
def fake_db(monkeypatch):
    cols: dict[str, FakeCollection] = {}

    def _get(name: str):
        return cols.setdefault(name, FakeCollection())

    monkeypatch.setattr(svc, "get_collection", _get)
    monkeypatch.setattr(custody_service, "get_collection", _get)
    monkeypatch.setattr(practice_service, "get_collection", _get)
    return cols


@pytest.fixture
def captured_audit(monkeypatch):
    events: list[dict] = []

    async def _fake_log(**kwargs):
        events.append(kwargs)
        return "evt"

    monkeypatch.setattr(svc, "log_audit_event", _fake_log)
    monkeypatch.setattr(custody_service, "log_audit_event", _fake_log)
    monkeypatch.setattr(practice_service, "log_audit_event", _fake_log)
    return events


def _seed_document(cols, *, tenant_id="tenant-a", matter_id="m-1", document_id="d-1"):
    cols.setdefault(svc.LEGAL_MATTER_DOCUMENTS_COLLECTION, FakeCollection()).docs.append(
        {
            "document_id": document_id,
            "matter_id": matter_id,
            "tenant_id": tenant_id,
            "app_key": "legalmitra",
            "filename": "notice.pdf",
            "doc_type": "notice",
            "extract_status": "pending",
        }
    )
    cols.setdefault(svc.LEGAL_MATTERS_COLLECTION, FakeCollection()).docs.append(
        {
            "matter_id": matter_id,
            "matter_number": "LM-2026-0001",
            "tenant_id": tenant_id,
            "app_key": "legalmitra",
            "client_id": "c-1",
            "client_name": "Acme",
            "title": "Writ petition sample",
            "matter_type": "writ",
            "status": "active",
            "jurisdiction": "Delhi High Court",
            "practice_area": "constitutional",
            "priority": "normal",
            "case_number": None,
            "issues": [],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )


SAMPLE_TEXT = (
    "Case Number: WP 226/2024 filed before Delhi High Court. "
    "Petitioner v. State of NCT. Issues include limitation and jurisdiction. "
    "Section 482 CrPC and GST assessment noted."
)


@pytest.mark.asyncio
async def test_ingest_creates_matter_paper_chunks(fake_db, captured_audit):
    _seed_document(fake_db)
    result = await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    assert result["deduped"] is False
    assert result["extract"]["source_kind"] == "matter_paper"
    assert result["extract"]["approval_status"] == "approved"
    assert result["chunks"]
    assert all(c["source_kind"] == "matter_paper" for c in result["chunks"])
    assert result["suggestions"].get("case_number")
    assert captured_audit[-1]["action"] == "legal_matter_extract_ingested"


@pytest.mark.asyncio
async def test_hash_dedupe_skips_second_ingest(fake_db):
    _seed_document(fake_db)
    first = await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    second = await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    assert first["deduped"] is False
    assert second["deduped"] is True
    extracts = fake_db[svc.LEGAL_MATTER_EXTRACTS_COLLECTION].docs
    assert len(extracts) == 1


@pytest.mark.asyncio
async def test_provider_gate_fail_closed(fake_db):
    with pytest.raises(svc.ExtractValidationError, match="fail-closed"):
        await svc.assert_external_provider_allowed(
            tenant_id="tenant-a",
            app_key="legalmitra",
            authorize_external_provider=False,
        )


@pytest.mark.asyncio
async def test_chamber_lan_rejects_cloud_originals(fake_db, captured_audit):
    await custody_service.update_custody_settings(
        tenant_id="tenant-a",
        app_key="legalmitra",
        payload=DocCustodySettingsUpdateRequest(
            doc_custody_mode="chamber_lan",
            onboarding_answered=True,
        ),
        actor_user_id="admin-1",
    )
    with pytest.raises(svc.ExtractValidationError, match="Chamber LAN"):
        await svc.assert_cloud_original_allowed(tenant_id="tenant-a", app_key="legalmitra")


@pytest.mark.asyncio
async def test_personal_practice_requires_opt_in_for_originals(fake_db):
    with pytest.raises(svc.ExtractValidationError, match="opt-in"):
        await svc.assert_cloud_original_allowed(tenant_id="tenant-a", app_key="legalmitra")

    await custody_service.update_custody_settings(
        tenant_id="tenant-a",
        app_key="legalmitra",
        payload=DocCustodySettingsUpdateRequest(
            doc_custody_mode="cloud_minimized",
            doc_cloud_originals_opt_in=True,
            onboarding_answered=True,
        ),
        actor_user_id="admin-1",
    )
    settings = await svc.assert_cloud_original_allowed(
        tenant_id="tenant-a", app_key="legalmitra"
    )
    assert settings["doc_cloud_originals_opt_in"] is True


@pytest.mark.asyncio
async def test_apply_case_card_is_explicit_only(fake_db, captured_audit):
    _seed_document(fake_db)
    result = await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    extract_id = result["extract"]["extract_id"]
    with pytest.raises(svc.ExtractValidationError, match="No applyable"):
        await svc.apply_case_card_suggestions(
            tenant_id="tenant-a",
            app_key="legalmitra",
            matter_id="m-1",
            extract_id=extract_id,
            actor_id="adv-1",
            fields={},
        )
    updated = await svc.apply_case_card_suggestions(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        extract_id=extract_id,
        actor_id="adv-1",
        fields={"case_number": "WP 226/2024", "issues": ["limitation"]},
    )
    assert updated["case_number"] == "WP 226/2024"
    assert "limitation" in updated["issues"]


@pytest.mark.asyncio
async def test_retention_dry_run_lists_expired(fake_db):
    _seed_document(fake_db)
    await custody_service.update_custody_settings(
        tenant_id="tenant-a",
        app_key="legalmitra",
        payload=DocCustodySettingsUpdateRequest(extract_retention_days=1),
        actor_user_id="admin-1",
    )
    result = await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    # Force expiry into the past for dry-run.
    extract_id = result["extract"]["extract_id"]
    past = datetime.now(timezone.utc) - timedelta(days=2)
    for doc in fake_db[svc.LEGAL_MATTER_EXTRACTS_COLLECTION].docs:
        if doc["extract_id"] == extract_id:
            doc["expires_at"] = past
    for doc in fake_db[svc.LEGAL_MATTER_CHUNKS_COLLECTION].docs:
        if doc["extract_id"] == extract_id:
            doc["expires_at"] = past

    dry = await svc.retention_dry_run(tenant_id="tenant-a", app_key="legalmitra")
    assert dry["dry_run"] is True
    assert dry["expired_extract_count"] == 1
    assert dry["expired_chunk_count"] >= 1


@pytest.mark.asyncio
async def test_tenant_isolation_for_extracts(fake_db):
    _seed_document(fake_db, tenant_id="tenant-a")
    _seed_document(fake_db, tenant_id="tenant-b", matter_id="m-b", document_id="d-b")
    await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )
    other = await svc.list_matter_extracts(
        tenant_id="tenant-b", app_key="legalmitra", matter_id="m-b"
    )
    assert other == []


@pytest.mark.asyncio
async def test_stage5_research_uses_approved_chunks(fake_db, monkeypatch):
    _seed_document(fake_db)
    await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )

    async def _get_matter(**kwargs):
        return fake_db[svc.LEGAL_MATTERS_COLLECTION].docs[0]

    async def _list_docs(**kwargs):
        return fake_db[svc.LEGAL_MATTER_DOCUMENTS_COLLECTION].docs

    monkeypatch.setattr(workflow_adapters, "get_matter", _get_matter)
    monkeypatch.setattr(workflow_adapters, "list_matter_documents", _list_docs)
    monkeypatch.setattr(workflow_adapters, "extract_service", svc)

    result = await workflow_adapters.adapter_legal_research(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        workflow_template="writ_petition",
    )
    assert result["payload"]["matter_paper_chunk_count"] >= 1
    assert any(s.get("source_type") == "matter_paper_chunk" for s in result["sources"])
    assert any("Approved extract" in f for f in result["payload"]["key_facts"])


@pytest.mark.asyncio
async def test_brief_grounds_on_approved_chunks(fake_db, monkeypatch):
    _seed_document(fake_db)
    await svc.ingest_matter_extract(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        document_id="d-1",
        actor_id="adv-1",
        extract_text=SAMPLE_TEXT,
        approve=True,
    )

    async def _get_matter(**kwargs):
        return dict(fake_db[svc.LEGAL_MATTERS_COLLECTION].docs[0])

    async def _list_docs(**kwargs):
        return [dict(d) for d in fake_db[svc.LEGAL_MATTER_DOCUMENTS_COLLECTION].docs]

    async def _list_timeline(**kwargs):
        return []

    monkeypatch.setattr(practice_service, "get_matter", _get_matter)
    monkeypatch.setattr(practice_service, "list_matter_documents", _list_docs)
    monkeypatch.setattr(practice_service, "list_matter_timeline", _list_timeline)

    brief = await practice_service.generate_matter_brief(
        tenant_id="tenant-a",
        app_key="legalmitra",
        matter_id="m-1",
        generated_by="adv-1",
    )
    assert brief["generation_strategy"] == "grounded_matter_summary_with_extracts"
    assert any(s.get("source_type") == "matter_paper_chunk" for s in brief["sources"])
    assert any("Approved extract" in f for f in brief["sections"]["key_facts"])
