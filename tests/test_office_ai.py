"""OfficeMitra AI unit tests — tenancy, feature flags, soft-fail AI, connector isolation."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import app.core.modules.dependencies as module_deps
from app.core.modules.registry import ModuleAccessError, require_module_access, require_module_feature
from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.ai.factory import get_ai_provider
from app.modules.office_ai.ai.orchestrator import generate_tasks, load_prompt
from app.modules.office_ai.ai.providers.null_provider import NullProvider
from app.modules.office_ai.connectors import legalmitra_connector, mitrabooks_connector


def test_office_ai_module_registered_and_gated():
    with pytest.raises(ModuleAccessError, match="not enabled"):
        require_module_access(
            module_key="office_ai",
            organization_type="BUSINESS",
            enabled_modules=["business", "accounting", "audit"],
            app_key="mitrabooks",
        )

    definition = require_module_access(
        module_key="office_ai",
        organization_type="BUSINESS",
        enabled_modules=["business", "accounting", "audit", "office_ai"],
        app_key="mitrabooks",
    )
    assert definition.module_key == "office_ai"
    assert "tasks" in definition.features


def test_office_ai_feature_flag_can_disable_email_only():
    require_module_feature(
        module_key="office_ai",
        feature="tasks",
        organization_type="BUSINESS",
        enabled_modules=["office_ai", "office_ai.tasks", "office_ai.brief"],
        app_key="mitrabooks",
    )
    with pytest.raises(ModuleAccessError, match="office_ai.email"):
        require_module_feature(
            module_key="office_ai",
            feature="email",
            organization_type="BUSINESS",
            enabled_modules=["office_ai", "office_ai.tasks", "office_ai.brief"],
            app_key="mitrabooks",
        )


def test_office_ai_allows_officemitra_and_host_app_keys():
    for app_key in ("officemitra", "mitrabooks", "legalmitra", "gruhamitra", "mandirmitra"):
        org = {
            "officemitra": "BUSINESS",
            "mitrabooks": "BUSINESS",
            "legalmitra": "LEGAL",
            "gruhamitra": "HOUSING",
            "mandirmitra": "TEMPLE",
        }[app_key]
        definition = require_module_access(
            module_key="office_ai",
            organization_type=org,
            enabled_modules=["office_ai"],
            app_key=app_key,
        )
        assert definition.module_key == "office_ai"


def test_office_ai_blocks_unknown_app_key():
    with pytest.raises(ModuleAccessError, match="app_key"):
        require_module_access(
            module_key="office_ai",
            organization_type="BUSINESS",
            enabled_modules=["office_ai"],
            app_key="investmitra",
        )


@pytest.mark.asyncio
async def test_require_enabled_module_office_ai(monkeypatch):
    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": "BUSINESS",
            "enabled_modules": ["business", "accounting", "office_ai", "office_ai.tasks"],
        }

    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    dependency = module_deps.require_enabled_module_feature("office_ai", "tasks")
    result = await dependency(
        current_user={"sub": "u1", "tenant_id": "t1", "app_key": "mitrabooks", "role": "tenant_admin"}
    )
    assert result["feature"] == "tasks"

    with pytest.raises(HTTPException) as exc:
        await module_deps.require_enabled_module_feature("office_ai", "email")(
            current_user={"sub": "u1", "tenant_id": "t1", "app_key": "mitrabooks", "role": "tenant_admin"}
        )
    assert exc.value.status_code == 403


def test_prompt_files_are_versioned():
    text = load_prompt("generate_tasks_v1")
    assert "generate_tasks_v1" in text


def test_null_provider_when_disabled(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "OFFICEMITRA_AI_ENABLED", False)
    provider = get_ai_provider()
    assert isinstance(provider, NullProvider)


@pytest.mark.asyncio
async def test_generate_tasks_soft_fails_without_provider(monkeypatch):
    ai_metrics.reset_for_tests()

    class FakeNull(NullProvider):
        pass

    monkeypatch.setattr(
        "app.modules.office_ai.ai.orchestrator.get_ai_provider",
        lambda: FakeNull(reason="missing_api_key"),
    )

    async def fake_telemetry(**kwargs):
        return "telemetry-1"

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.record_telemetry", fake_telemetry)
    result = await generate_tasks(tenant_id="t1", text="Follow up with ACME on invoice")
    assert result["ai_available"] is False
    assert result["tasks"] == []
    assert result["prompt_version"] == "generate_tasks_v1"
    assert result["error_code"] == "missing_api_key"


@pytest.mark.asyncio
async def test_mitrabooks_connector_skips_when_module_disabled():
    tenant = {"enabled_modules": ["office_ai"]}
    revenue = await mitrabooks_connector.get_todays_revenue(
        tenant_id="t1", app_key="mitrabooks", tenant=tenant, session=None
    )
    assert revenue["enabled"] is False
    overdue = await mitrabooks_connector.get_overdue_invoices(
        tenant_id="t1", app_key="mitrabooks", tenant=tenant
    )
    assert overdue == []


@pytest.mark.asyncio
async def test_connector_manager_standalone_when_no_companion_modules():
    from app.modules.office_ai.connectors.manager import collect_connector_facts

    facts = await collect_connector_facts(
        tenant_id="t-standalone",
        app_key="officemitra",
        tenant={"enabled_modules": ["office_ai", "audit"]},
        session=None,
    )
    assert facts["standalone"] is True
    assert facts["connectors_loaded"] == []
    assert facts["sections"] == {}
    assert any(item["reason"] == "module_not_enabled" for item in facts["connectors_skipped"])


@pytest.mark.asyncio
async def test_legal_connector_stub_empty():
    items = await legalmitra_connector.get_pending_documents(
        tenant_id="t1",
        tenant={"enabled_modules": ["legal", "office_ai"]},
    )
    assert items == []


def test_office_ai_source_has_no_direct_sqlalchemy_accounting_imports():
    """Lightweight isolation guard: connector may import services, services must not raw-SQL."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "modules" / "office_ai"
    forbidden = ("from app.accounting.models", "select(Journal", "JournalEntry")
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if "connectors" in path.parts and path.name == "mitrabooks_connector.py":
            continue  # connector may call services only
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                offenders.append(f"{path.name}:{needle}")
    assert offenders == []


def test_platform_owner_entitlements_include_office_ai_for_mitrabooks_org_types() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    experience_source = (
        repo_root / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "experience-config.js"
    ).read_text(encoding="utf-8")

    for org_type in ("BUSINESS", "PROFESSIONAL", "HOUSING", "TEMPLE"):
        marker = f"{org_type}: ["
        start = experience_source.index(marker)
        end = experience_source.index("]", start)
        block = experience_source[start:end]
        assert '"office_ai"' in block or "'office_ai'" in block, f"{org_type} entitlements must include office_ai"


def test_office_ai_tasks_done_action_uses_task_id_attribute() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    office_ai_source = (
        repo_root / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "office-ai.js"
    ).read_text(encoding="utf-8")

    assert 'getAttribute("data-task-id")' in office_ai_source
    assert "taskRecordId(task)" in office_ai_source
    assert 'status: "done"' in office_ai_source
    assert "Task marked done." in office_ai_source
    assert "missing task id" in office_ai_source
