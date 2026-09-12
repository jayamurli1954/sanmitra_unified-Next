"""OfficeMitra Review workspaces (ADR-015) — flags, isolation, no live ledger writes."""
from __future__ import annotations

import inspect
from typing import Any

import pytest

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_review_enabled,
    is_office_ai_review_notes_enabled,
    is_office_ai_review_working_papers_enabled,
    require_module_feature,
)
from app.modules.office_ai.models import (
    MIS_FACTS_COLLECTION,
    MIS_PACKS_COLLECTION,
    NOTIFICATIONS_COLLECTION,
    REVIEW_ENGAGEMENTS_COLLECTION,
    REVIEW_ISSUES_COLLECTION,
    REVIEW_NOTES_COLLECTION,
    REVIEW_PAPERS_COLLECTION,
    TASKS_COLLECTION,
)
from app.modules.office_ai.services import mis_store, review_scan, review_service, review_store


def test_review_feature_is_opt_in_not_parent_default():
    with pytest.raises(ModuleAccessError, match="office_ai.review"):
        require_module_feature(
            module_key="office_ai",
            feature="review",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )
    with pytest.raises(ModuleAccessError, match="office_ai.review"):
        require_module_feature(
            module_key="office_ai",
            feature="review",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai", "office_ai.mis"],
            app_key="officemitra",
        )
    require_module_feature(
        module_key="office_ai",
        feature="review",
        organization_type="PROFESSIONAL",
        enabled_modules=["office_ai", "office_ai.review"],
        app_key="officemitra",
    )
    assert is_office_ai_review_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_review_enabled(enabled_modules=["office_ai", "office_ai.mis"]) is False
    assert is_office_ai_review_enabled(enabled_modules=["office_ai", "office_ai.review"]) is True


def test_review_sub_capabilities_require_parent_review():
    full = [
        "office_ai",
        "office_ai.review",
        "office_ai.review.working_papers",
        "office_ai.review.notes",
    ]
    assert is_office_ai_review_working_papers_enabled(enabled_modules=full) is True
    assert is_office_ai_review_notes_enabled(enabled_modules=full) is True
    assert (
        is_office_ai_review_working_papers_enabled(
            enabled_modules=["office_ai", "office_ai.review.working_papers"]
        )
        is False
    )
    assert is_office_ai_review_working_papers_enabled(enabled_modules=["office_ai", "office_ai.review"]) is False


def test_review_modules_never_import_accounting():
    from app.modules.office_ai.services import review_papers as papers_mod
    from app.modules.office_ai.services import review_scan as scan_mod
    from app.modules.office_ai.services import review_service as svc
    from app.modules.office_ai.services import review_store as store

    for mod in (scan_mod, store, papers_mod, svc):
        src = inspect.getsource(mod)
        assert "post_journal" not in src
        assert "app.accounting" not in src


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

    async def to_list(self, length: int):
        return self._docs[:length]


class _FakeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    def find(self, query: dict | None = None):
        query = query or {}
        matched = [dict(doc) for doc in self.docs if _match(doc, query)]
        return _FakeCursor(matched)

    async def find_one(self, query: dict, *args, **kwargs):
        for doc in self.docs:
            if _match(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return type("R", (), {"inserted_id": doc.get("_id")})()

    async def insert_many(self, docs: list[dict]):
        for item in docs:
            self.docs.append(dict(item))
        return type("R", (), {"inserted_ids": [item.get("_id") for item in docs]})()

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def delete_many(self, query: dict):
        kept = [doc for doc in self.docs if not _match(doc, query)]
        deleted = len(self.docs) - len(kept)
        self.docs = kept
        return type("R", (), {"deleted_count": deleted})()

    async def count_documents(self, query: dict):
        return sum(1 for doc in self.docs if _match(doc, query))

    async def create_index(self, *_args, **_kwargs):
        return True


def _match(doc: dict, query: dict) -> bool:
    for key, expected in query.items():
        actual = doc.get(key)
        if isinstance(expected, dict) and "$type" in expected:
            continue
        if actual != expected:
            return False
    return True


@pytest.fixture
def fake_review_mongo(monkeypatch):
    store = {
        MIS_PACKS_COLLECTION: _FakeCollection(),
        MIS_FACTS_COLLECTION: _FakeCollection(),
        REVIEW_ENGAGEMENTS_COLLECTION: _FakeCollection(),
        REVIEW_ISSUES_COLLECTION: _FakeCollection(),
        REVIEW_PAPERS_COLLECTION: _FakeCollection(),
        REVIEW_NOTES_COLLECTION: _FakeCollection(),
        TASKS_COLLECTION: _FakeCollection(),
        NOTIFICATIONS_COLLECTION: _FakeCollection(),
    }

    def _get(name: str):
        return store.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.modules.office_ai.services.mis_store.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.services.review_store.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.services.task_service.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.services.notification_service.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.models.get_collection", _get)
    return store


def _facts() -> list[dict[str, Any]]:
    return [
        {
            "entity_type": "cash_summary",
            "amount_decimal": "-1500.00",
            "currency": "INR",
            "fact_id": "cash-close",
            "dimensions": {"line": "Closing"},
        },
        {
            "entity_type": "bs_line",
            "amount_decimal": "25000.00",
            "currency": "INR",
            "fact_id": "suspense-1",
            "dimensions": {"account": "Suspense A/c"},
        },
        {
            "entity_type": "aging_bucket",
            "amount_decimal": "80000.00",
            "currency": "INR",
            "fact_id": "ar-90",
            "dimensions": {"side": "AR", "bucket": "90+"},
        },
        {
            "entity_type": "aging_bucket",
            "amount_decimal": "10000.00",
            "currency": "INR",
            "fact_id": "ap-current",
            "dimensions": {"side": "AP", "bucket": "0-30"},
        },
        {
            "entity_type": "party",
            "amount_decimal": "90000.00",
            "currency": "INR",
            "fact_id": "cust-a",
            "dimensions": {"type": "customer", "name": "Customer A"},
        },
        {
            "entity_type": "party",
            "amount_decimal": "10000.00",
            "currency": "INR",
            "fact_id": "cust-b",
            "dimensions": {"type": "customer", "name": "Customer B"},
        },
    ]


def test_scan_facts_risk_score_distinct_from_quality():
    issues, score = review_scan.scan_facts(_facts())
    codes = {item["finding_code"] for item in issues}
    assert "NEGATIVE_CASH" in codes
    assert "SUSPENSE_BALANCE" in codes
    assert "AR_AGING_90" in codes
    assert "AR_CONCENTRATION" in codes
    assert "MISSING_AP_AGING" not in codes
    assert 0 < score <= 100
    assert all(item["ai_generated"] is False for item in issues)
    assert all(item["rule_version"] == "review_rules@1.0.0" for item in issues)


@pytest.mark.asyncio
async def test_scan_and_papers_are_tenant_scoped(fake_review_mongo):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
        ingestion_path="excel_import",
    )
    await mis_store.insert_facts(
        tenant_id="tenant-a",
        pack_id=pack["id"],
        user=user,
        facts=_facts(),
    )
    other_pack = await mis_store.create_pack_draft(
        tenant_id="tenant-b",
        user=user,
        pack_key="sme_general",
        period="2026-07",
        ingestion_path="excel_import",
    )
    engagement = await review_service.create_engagement(
        tenant_id="tenant-a",
        user=user,
        period="2026-07",
        pack_id=pack["id"],
    )
    scanned = await review_service.scan_engagement(
        tenant_id="tenant-a",
        engagement_id=engagement["id"],
        user=user,
    )
    assert scanned["ssdv_cli"] is False
    assert scanned["data_quality_score"] is None
    assert scanned["engagement"]["engagement_risk_score"] is not None
    issues = await review_store.list_issues(tenant_id="tenant-a", engagement_id=engagement["id"])
    assert issues
    foreign = await review_store.list_engagements(tenant_id="tenant-b")
    assert foreign == []

    with pytest.raises(review_service.ReviewServiceError, match="this tenant"):
        await review_service.link_pack(
            tenant_id="tenant-a",
            engagement_id=engagement["id"],
            user=user,
            pack_id=other_pack["id"],
        )

    papers = await review_service.generate_working_papers(
        tenant_id="tenant-a",
        engagement_id=engagement["id"],
        user=user,
    )
    assert papers["count"] == 5
    paper_id = papers["items"][0]["id"]
    closed = await review_store.close_paper(tenant_id="tenant-a", paper_id=paper_id, user=user)
    assert closed["immutable"] is True
    with pytest.raises(review_store.ReviewImmutableError):
        await review_store.close_paper(tenant_id="tenant-a", paper_id=paper_id, user=user)

    note_res = await review_service.create_note_with_task(
        tenant_id="tenant-a",
        engagement_id=engagement["id"],
        user=user,
        description="Clear suspense.",
        issue_id=issues[0]["id"],
        assigned_to="staff-2",
    )
    assert note_res["task"]["id"]
    assert note_res["item"]["task_id"] == note_res["task"]["id"]
    closed_note = await review_store.update_note(
        tenant_id="tenant-a",
        note_id=note_res["item"]["id"],
        user=user,
        updates={"status": "closed"},
    )
    assert closed_note["status"] == "closed"
    with pytest.raises(review_store.ReviewNotFoundError):
        await review_store.list_notes(tenant_id="tenant-b", engagement_id=engagement["id"])


def test_shared_workspace_has_review_tab_when_flagged() -> None:
    from pathlib import Path

    shared = Path("frontend/shared/office-ai-workspace.js").read_text(encoding="utf-8")
    review_js = Path("frontend/shared/office-ai-review.js").read_text(encoding="utf-8")
    combined = shared + review_js
    assert '["review", "Review"]' in combined
    assert "/api/v1/officemitra/review/engagements" in combined
    assert "review_enabled" in combined
    assert 'data-office-ai-action="review-scan"' in combined
    assert 'data-office-ai-action="review-generate-papers"' in combined
    assert 'data-office-ai-action="review-create-note"' in combined
    assert 'data-office-ai-action="review-close-note"' in combined
    assert "/api/v1/officemitra/review/notes/" in combined


def test_aging_90_plus_does_not_match_61_90_bucket():
    issues, _score = review_scan.scan_facts(
        [
            {
                "entity_type": "aging_bucket",
                "amount_decimal": "100.00",
                "fact_id": "ar-mid",
                "dimensions": {"side": "AR", "bucket": "61-90"},
            },
            {
                "entity_type": "aging_bucket",
                "amount_decimal": "50.00",
                "fact_id": "ar-plus",
                "dimensions": {"side": "AR", "bucket": "90+"},
            },
            {
                "entity_type": "aging_bucket",
                "amount_decimal": "25.00",
                "fact_id": "ap-mid",
                "dimensions": {"side": "AP", "bucket": "61-90"},
            },
        ]
    )
    codes = {item["finding_code"] for item in issues}
    assert "AR_AGING_90" in codes
    assert "AP_AGING_90" not in codes
    ar90 = [item for item in issues if item["finding_code"] == "AR_AGING_90"]
    assert len(ar90) == 1
    assert ar90[0]["fact_ids"] == ["ar-plus"]


def test_manufacturing_demo_facts_produce_review_findings() -> None:
    import importlib.util
    from pathlib import Path

    path = Path("scripts/seed_mis_demo_firm.py")
    spec = importlib.util.spec_from_file_location("seed_mis_demo_firm_for_review", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    issues, score = review_scan.scan_facts(mod.build_demo_manufacturing_facts())
    codes = {item["finding_code"] for item in issues}
    assert "AR_AGING_90" in codes
    assert "AP_AGING_90" in codes
    assert "MISSING_CASH" not in codes
    assert 0 < score <= 100


def test_review_demo_seed_refuses_erp_demo_tenant() -> None:
    import importlib.util
    from pathlib import Path

    from app.core.modules.registry import (
        is_office_ai_review_enabled,
        is_office_ai_review_notes_enabled,
        is_office_ai_review_working_papers_enabled,
    )

    path = Path("scripts/seed_review_demo.py")
    spec = importlib.util.spec_from_file_location("seed_review_demo", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    assert mod.allowed_review_demo_tenant_id() == "demo-mfg-mis"
    assert "demo-mitrabooks-business" in mod.BLOCKED_TENANT_IDS
    with pytest.raises(SystemExit, match="live ERP demo"):
        mod.assert_allowed_review_demo_tenant("demo-mitrabooks-business")
    with pytest.raises(SystemExit, match="locked to demo-mfg-mis"):
        mod.assert_allowed_review_demo_tenant("some-production-tenant")
    assert mod.assert_allowed_review_demo_tenant("demo-mfg-mis") == "demo-mfg-mis"

    full = ["office_ai", "office_ai.mis", *mod.REVIEW_FLAGS]
    assert is_office_ai_review_enabled(enabled_modules=full) is True
    assert is_office_ai_review_working_papers_enabled(enabled_modules=full) is True
    assert is_office_ai_review_notes_enabled(enabled_modules=full) is True

    src = path.read_text(encoding="utf-8")
    assert "app.accounting" not in src
    assert "post_journal" not in src

