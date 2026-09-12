"""OfficeMitra Documents package (ADR-016) — staff CA queue links, no companion writes."""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_documents_enabled,
    require_module_feature,
)
from app.modules.office_ai.models import REVIEW_ENGAGEMENTS_COLLECTION, REVIEW_NOTES_COLLECTION
from app.modules.office_ai.services import documents_service, review_store


class _FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    def find(self, query: dict | None = None):
        query = query or {}
        matched = [dict(doc) for doc in self.docs if all(doc.get(k) == v for k, v in query.items())]
        return _FakeCursor(matched)

    async def find_one(self, query: dict, *args, **kwargs):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def create_index(self, *_args, **_kwargs):
        return True


@pytest.fixture
def fake_review_mongo(monkeypatch):
    store = {
        REVIEW_ENGAGEMENTS_COLLECTION: _FakeCollection(),
        REVIEW_NOTES_COLLECTION: _FakeCollection(),
    }

    def _get(name: str):
        return store.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.modules.office_ai.services.review_store.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.models.get_collection", _get)
    return store
from tests.test_office_ai_review import _FakeCollection, _match


def test_documents_feature_is_opt_in_not_parent_or_review():
    with pytest.raises(ModuleAccessError, match="office_ai.documents"):
        require_module_feature(
            module_key="office_ai",
            feature="documents",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )
    with pytest.raises(ModuleAccessError, match="office_ai.documents"):
        require_module_feature(
            module_key="office_ai",
            feature="documents",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai", "office_ai.review", "office_ai.review.notes"],
            app_key="officemitra",
        )
    require_module_feature(
        module_key="office_ai",
        feature="documents",
        organization_type="PROFESSIONAL",
        enabled_modules=["office_ai", "office_ai.documents"],
        app_key="officemitra",
    )
    assert is_office_ai_documents_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_documents_enabled(enabled_modules=["office_ai", "office_ai.review"]) is False
    assert is_office_ai_documents_enabled(enabled_modules=["office_ai", "office_ai.documents"]) is True


def test_documents_modules_never_touch_ledger_or_ca_collection():
    from app.modules.office_ai import documents_router
    from app.modules.office_ai.services import documents_service as svc

    for mod in (svc, documents_router):
        src = inspect.getsource(mod)
        assert "post_journal" not in src
        assert "app.accounting" not in src
        assert "business_ca_document_metadata" not in src
        assert "CA_DOCUMENTS_COLLECTION" not in src


@pytest.mark.asyncio
async def test_queue_fails_soft_without_business_module(monkeypatch):
    async def fake_list(*, tenant_id, tenant, accounting_entity_id="primary", status=None, limit=100):
        if "business" not in (tenant.get("enabled_modules") or []):
            return {"enabled": False, "items": [], "total": 0, "reason": "business_module_off"}
        return {"enabled": True, "items": [], "total": 0}

    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.list_ca_staff_documents",
        fake_list,
    )
    result = await documents_service.list_queue(
        tenant_id="demo-mfg-mis",
        tenant={"enabled_modules": ["office_ai", "office_ai.documents"]},
    )
    assert result["enabled"] is False
    assert result["reason"] == "business_module_off"
    assert result["items"] == []
    assert result["client_portal"] is False
    assert result["companion_writes"] is False


@pytest.mark.asyncio
async def test_link_note_is_tenant_scoped(fake_review_mongo, monkeypatch):
    user = {"sub": "tester"}
    engagement = await review_store.create_engagement(
        tenant_id="tenant-a",
        user=user,
        period="2026-07",
        accounting_entity_id="primary",
    )
    note = await review_store.create_note(
        tenant_id="tenant-a",
        engagement_id=engagement["id"],
        user=user,
        description="Need bank statement",
    )

    async def fake_get(*, tenant_id, tenant, document_id, accounting_entity_id=None):
        if tenant_id != "tenant-a":
            return None
        return {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "accounting_entity_id": accounting_entity_id or "primary",
            "status": "uploaded",
        }

    monkeypatch.setattr(
        "app.modules.office_ai.connectors.mitrabooks_connector.get_ca_staff_document",
        fake_get,
    )
    linked = await documents_service.link_note(
        tenant_id="tenant-a",
        tenant={"enabled_modules": ["business", "office_ai", "office_ai.documents"]},
        user=user,
        note_id=note["id"],
        document_id="doc-1",
    )
    assert linked["item"]["ca_document_id"] == "doc-1"
    with pytest.raises(documents_service.DocumentsNotFoundError):
        await documents_service.link_note(
            tenant_id="tenant-b",
            tenant={"enabled_modules": ["business"]},
            user=user,
            note_id=note["id"],
            document_id="doc-1",
        )
    other = await review_store.get_note(tenant_id="tenant-b", note_id=note["id"])
    assert other is None


def test_seed_refuses_live_erp_demo_tenant():
    import importlib.util

    path = Path("scripts/seed_documents_demo.py")
    spec = importlib.util.spec_from_file_location("seed_documents_demo", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit, match="demo-mitrabooks-business"):
        mod.assert_allowed_documents_demo_tenant("demo-mitrabooks-business")
    with pytest.raises(SystemExit, match="locked"):
        mod.assert_allowed_documents_demo_tenant("someone-else")


def test_shared_workspace_has_documents_tab_when_flagged() -> None:
    shared = Path("frontend/shared/office-ai-workspace.js").read_text(encoding="utf-8")
    docs_js = Path("frontend/shared/office-ai-documents.js").read_text(encoding="utf-8")
    combined = shared + docs_js
    assert '["documents", "Documents"]' in combined
    assert "/api/v1/officemitra/documents/queue" in combined
    assert "documents_enabled" in combined
    assert 'data-office-ai-action="documents-link"' in combined
    assert "client portal" in combined.lower()
    assert "ca-access" in combined
