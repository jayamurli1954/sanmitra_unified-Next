"""OfficeMitra CA Analysis Pack (ADR-014) — module gates and MIS fact store."""
from __future__ import annotations

from typing import Any

import pytest
from bson import ObjectId

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_mis_enabled,
    is_office_ai_mis_export_enabled,
    is_office_ai_mis_import_enabled,
    is_office_ai_mis_live_mitrabooks_enabled,
    is_office_ai_mis_pack_enabled,
    require_module_feature,
)
from app.modules.office_ai.models import MIS_FACTS_COLLECTION, MIS_PACKS_COLLECTION
from app.modules.office_ai.services import mis_service, mis_store


def test_mis_feature_is_opt_in_not_parent_default():
    with pytest.raises(ModuleAccessError, match="office_ai.mis"):
        require_module_feature(
            module_key="office_ai",
            feature="mis",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )

    require_module_feature(
        module_key="office_ai",
        feature="mis",
        organization_type="PROFESSIONAL",
        enabled_modules=["office_ai", "office_ai.mis"],
        app_key="officemitra",
    )

    assert is_office_ai_mis_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_mis_enabled(enabled_modules=["office_ai", "office_ai.mis"]) is True


def test_mis_sub_capabilities_require_parent_mis():
    modules = [
        "office_ai",
        "office_ai.mis",
        "office_ai.mis.import",
        "office_ai.mis.export",
        "office_ai.mis.live_mitrabooks",
    ]
    assert is_office_ai_mis_import_enabled(enabled_modules=modules) is True
    assert is_office_ai_mis_export_enabled(enabled_modules=modules) is True
    assert is_office_ai_mis_live_mitrabooks_enabled(enabled_modules=modules) is True

    assert is_office_ai_mis_import_enabled(enabled_modules=["office_ai", "office_ai.mis.import"]) is False
    assert is_office_ai_mis_import_enabled(enabled_modules=["office_ai", "office_ai.mis"]) is False


def test_mis_pack_flag_requires_parent_mis():
    modules = ["office_ai", "office_ai.mis", "office_ai.mis.pack.sme_general"]
    assert is_office_ai_mis_pack_enabled("sme_general", enabled_modules=modules) is True
    assert is_office_ai_mis_pack_enabled("ca_practice", enabled_modules=modules) is False
    assert is_office_ai_mis_pack_enabled("sme_general", enabled_modules=["office_ai"]) is False


def test_mis_pack_catalog_lists_adr014_starter_packs():
    catalog = mis_service.list_pack_catalog()
    keys = {item["pack_key"] for item in catalog}
    assert "sme_general" in keys
    assert "ca_practice" in keys
    assert all("pack_version" in item for item in catalog)


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
        for doc in docs:
            self.docs.append(dict(doc))
        return type("R", (), {"inserted_ids": [doc.get("_id") for doc in docs]})()

    async def update_one(self, query: dict, update: dict):
        for doc in self.docs:
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                return type("R", (), {"modified_count": 1})()
        return type("R", (), {"modified_count": 0})()

    async def update_many(self, query: dict, update: dict):
        count = 0
        for doc in self.docs:
            if _match(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                count += 1
        return type("R", (), {"modified_count": count})()

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
def fake_mis_mongo(monkeypatch):
    store = {
        MIS_PACKS_COLLECTION: _FakeCollection(),
        MIS_FACTS_COLLECTION: _FakeCollection(),
    }

    def _get(name: str):
        return store.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.modules.office_ai.services.mis_store.get_collection", _get)
    monkeypatch.setattr("app.modules.office_ai.models.get_collection", _get)
    return store


@pytest.mark.asyncio
async def test_create_pack_and_insert_facts(fake_mis_mongo):
    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
        ingestion_path="excel_import",
    )
    pack_id = pack["id"]
    assert pack["status"] == "draft"
    assert pack["pack_version"] == "1.0.0"
    assert pack["immutable"] is False

    result = await mis_store.insert_facts(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        facts=[
            {
                "entity_type": "pnl_line",
                "amount_decimal": "125000.50",
                "currency": "INR",
                "source_system": "excel_import",
                "source_ref": "PnL!B12",
            }
        ],
    )
    assert result["inserted"] == 1

    facts = await mis_store.list_facts(tenant_id="tenant-a", pack_id=pack_id)
    assert len(facts) == 1
    assert facts[0]["amount_decimal"] == "125000.50"
    assert facts[0]["immutable"] is False


@pytest.mark.asyncio
async def test_reconcile_locks_pack_and_facts(fake_mis_mongo):
    user = {"sub": "reviewer-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="ca_practice",
        period="2026-07",
    )
    pack_id = pack["id"]
    await mis_store.insert_facts(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        facts=[{"entity_type": "kpi", "value": 42, "source_system": "manual"}],
    )

    reconciled = await mis_store.reconcile_pack(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        data_quality_score=92,
        data_quality_breakdown={"mapped_rows_pct": 100},
    )
    assert reconciled["status"] == "reconciled"
    assert reconciled["immutable"] is True
    assert reconciled["data_quality_score"] == 92

    facts = await mis_store.list_facts(tenant_id="tenant-a", pack_id=pack_id)
    assert facts[0]["immutable"] is True
    assert facts[0]["reconciled"] is True

    with pytest.raises(mis_store.MISImmutableError):
        await mis_store.insert_facts(
            tenant_id="tenant-a",
            pack_id=pack_id,
            user=user,
            facts=[{"entity_type": "kpi", "value": 99}],
        )


@pytest.mark.asyncio
async def test_tenant_isolation_on_pack_read(fake_mis_mongo):
    user = {"sub": "u1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    assert await mis_store.get_pack(tenant_id="tenant-b", pack_id=pack["id"]) is None


@pytest.mark.asyncio
async def test_pack_is_editable_helper():
    assert mis_store.pack_is_editable({"status": "draft", "immutable": False}) is True
    assert mis_store.pack_is_editable({"status": "reconciled", "immutable": True}) is False


def test_mis_export_actions_registered_with_adr014_risk_tiers():
    from app.modules.office_ai.actions.registry import ensure_default_actions_registered, get_action

    ensure_default_actions_registered()
    excel = get_action("export_mis_excel")
    pdf = get_action("export_mis_pdf_summary")
    ppt = get_action("export_mis_ppt")
    assert excel is not None
    assert pdf is not None
    assert ppt is not None
    assert excel.capabilities.risk_level == "MEDIUM"
    assert pdf.capabilities.risk_level == "MEDIUM"
    assert ppt.capabilities.risk_level == "HIGH"
    assert ppt.capabilities.requires_maker_checker is True
    assert excel.capabilities.requires_maker_checker is False


@pytest.mark.asyncio
async def test_export_rejects_unreconciled_pack(fake_mis_mongo):
    from app.modules.office_ai.services import mis_export

    user = {"sub": "acct-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    with pytest.raises(mis_export.MISExportNotReconciledError):
        await mis_export.export_mis_pack(
            tenant_id="tenant-a",
            pack_id=pack["id"],
            user=user,
            export_format="excel",
        )


@pytest.mark.asyncio
async def test_export_blocks_ppt_when_data_quality_low(fake_mis_mongo):
    from app.modules.office_ai.services import mis_export

    user = {"sub": "reviewer-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    pack_id = pack["id"]
    await mis_store.reconcile_pack(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        data_quality_score=65,
    )
    with pytest.raises(mis_export.MISExportQualityBlockedError):
        await mis_export.export_mis_pack(
            tenant_id="tenant-a",
            pack_id=pack_id,
            user=user,
            export_format="ppt",
        )


@pytest.mark.asyncio
async def test_export_excel_marks_pack_exported(fake_mis_mongo):
    from app.modules.office_ai.services import mis_export

    user = {"sub": "reviewer-1"}
    pack = await mis_store.create_pack_draft(
        tenant_id="tenant-a",
        user=user,
        pack_key="sme_general",
        period="2026-07",
    )
    pack_id = pack["id"]
    await mis_store.reconcile_pack(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        data_quality_score=88,
    )

    result = await mis_export.export_mis_pack(
        tenant_id="tenant-a",
        pack_id=pack_id,
        user=user,
        export_format="excel",
    )
    assert result["artifact"]["format"] == "excel"
    assert result["pack"]["status"] == "exported"


def test_shared_workspace_has_mis_tab_and_actions() -> None:
    from pathlib import Path

    shared = Path("frontend/shared/office-ai-workspace.js").read_text(encoding="utf-8")
    assert '["mis", "MIS Packs"]' in shared
    assert 'data-office-ai-action="mis-create-pack"' in shared
    assert 'data-office-ai-action="mis-import-excel"' in shared
    assert 'data-office-ai-action="mis-reconcile"' in shared
    assert 'data-office-ai-action="mis-export-ppt"' in shared
    assert "/api/v1/officemitra/mis/packs" in shared
    assert "reconcile_mis_pack" in shared
    assert "export_mis_" in shared
    assert "Pack dashboard" in shared
    assert "buildMisDashboard" in shared


def test_mis_demo_firm_seed_facts_cover_dashboard_entities() -> None:
    """Inlined demo snapshot must cover ADR-014 entities used by the MIS dashboard."""
    import importlib.util
    from pathlib import Path

    path = Path("scripts/seed_mis_demo_firm.py")
    spec = importlib.util.spec_from_file_location("seed_mis_demo_firm", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    facts = mod.build_demo_manufacturing_facts()
    assert len(facts) >= 20
    entity_types = {f["entity_type"] for f in facts}
    assert {"pnl_line", "bs_line", "cash_summary", "aging_bucket", "kpi"} <= entity_types
    assert any(f.get("dimensions", {}).get("kpi") == "DSO" for f in facts)
    assert any(f.get("dimensions", {}).get("side") == "AR" for f in facts)


def test_mis_demo_firm_seed_script_entitlements_match_gates() -> None:
    """Demo firm base modules must validate; nested MIS flags must unlock import/export."""
    import importlib.util
    from pathlib import Path

    from app.core.modules.registry import (
        is_office_ai_mis_enabled,
        is_office_ai_mis_export_enabled,
        is_office_ai_mis_import_enabled,
        is_office_ai_mis_pack_enabled,
    )
    from app.core.tenants.service import _validate_enabled_modules

    path = Path("scripts/seed_mis_demo_firm.py")
    spec = importlib.util.spec_from_file_location("seed_mis_demo_firm", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    assert mod.DEMO_TENANT_ID == "demo-mfg-mis"
    assert "SanMitra Demo Manufacturing" in mod.DEMO_DISPLAY_NAME
    _validate_enabled_modules(
        organization_type="BUSINESS",
        app_keys=["mitrabooks"],
        enabled_modules=list(mod.BASE_ENABLED_MODULES),
    )
    full = list(mod.BASE_ENABLED_MODULES) + list(mod.NESTED_MIS_FLAGS)
    assert is_office_ai_mis_enabled(enabled_modules=full) is True
    assert is_office_ai_mis_import_enabled(enabled_modules=full) is True
    assert is_office_ai_mis_export_enabled(enabled_modules=full) is True
    assert is_office_ai_mis_pack_enabled("manufacturing", enabled_modules=full) is True
