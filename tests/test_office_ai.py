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
from app.modules.office_ai.connectors import (
    gruhamitra_connector,
    legalmitra_connector,
    mandirmitra_connector,
    mitrabooks_connector,
)


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
async def test_legal_connector_skips_when_module_disabled():
    items = await legalmitra_connector.get_pending_documents(
        tenant_id="t1",
        tenant={"enabled_modules": ["office_ai"]},
    )
    assert items == []


@pytest.mark.asyncio
async def test_legal_connector_maps_pending_matters(monkeypatch):
    async def fake_list_matters(*, tenant_id, app_key, status=None, limit=50, **_kwargs):
        assert tenant_id == "t-legal"
        assert app_key == "legalmitra"
        if status == "pending":
            return [
                {
                    "matter_id": "m1",
                    "title": "Contract review",
                    "matter_number": "LM-1",
                    "status": "pending",
                    "next_deadline_date": "2026-08-10",
                    "client_name": "Acme",
                }
            ]
        if status == "draft":
            return [{"matter_id": "m2", "title": "Draft brief", "status": "draft"}]
        return []

    import app.modules.legal.practice_service as practice_service

    monkeypatch.setattr(practice_service, "list_matters", fake_list_matters)

    items = await legalmitra_connector.get_pending_documents(
        tenant_id="t-legal",
        tenant={"enabled_modules": ["legal", "office_ai"]},
    )
    assert len(items) == 2
    assert items[0]["id"] == "m1"
    assert "Contract review" in items[0]["title"]
    assert items[0]["due"] == "2026-08-10"
    assert items[1]["id"] == "m2"


@pytest.mark.asyncio
async def test_gruhamitra_connector_skips_when_module_disabled():
    items = await gruhamitra_connector.get_open_maintenance_requests(
        tenant_id="t1",
        tenant={"enabled_modules": ["office_ai"]},
    )
    assert items == []


@pytest.mark.asyncio
async def test_gruhamitra_connector_maps_open_complaints(monkeypatch):
    async def fake_list_open_complaints(*, tenant_id, app_key, limit=20):
        assert tenant_id == "t-house"
        assert app_key == "mitrabooks"
        return [
            {
                "id": "c1",
                "title": "Lift outage",
                "status": "open",
                "priority": "high",
                "flat_number": "A-101",
                "type": "maintenance",
            }
        ]

    import app.modules.housing_compat.complaints_service as complaints_service

    monkeypatch.setattr(complaints_service, "list_open_complaints", fake_list_open_complaints)

    items = await gruhamitra_connector.get_open_maintenance_requests(
        tenant_id="t-house",
        tenant={"enabled_modules": ["housing", "office_ai"]},
        app_key="mitrabooks",
    )
    assert len(items) == 1
    assert items[0]["id"] == "c1"
    assert items[0]["title"] == "Lift outage"


@pytest.mark.asyncio
async def test_mandirmitra_connector_skips_without_session():
    items = await mandirmitra_connector.get_upcoming_events_or_donations(
        tenant_id="t1",
        tenant={"enabled_modules": ["temple", "office_ai"]},
        session=None,
    )
    assert items == []


@pytest.mark.asyncio
async def test_mandirmitra_connector_maps_seva_schedule(monkeypatch):
    async def fake_seva_schedule_report(session, *, tenant_id, app_key, days):
        assert tenant_id == "t-temple"
        assert app_key == "mandirmitra"
        assert days == 14
        return {
            "schedule": [
                {
                    "id": "s1",
                    "seva_name": "Abhishekam",
                    "status": "Today",
                    "date": "2026-08-05",
                    "time": "06:00",
                    "devotee_name": "Devotee",
                    "devotee_mobile": "9999999999",
                    "amount": 501.0,
                }
            ]
        }

    import app.modules.mandir_compat.report_helpers as report_helpers

    monkeypatch.setattr(report_helpers, "seva_schedule_report", fake_seva_schedule_report)

    items = await mandirmitra_connector.get_upcoming_events_or_donations(
        tenant_id="t-temple",
        tenant={"enabled_modules": ["temple", "office_ai"]},
        app_key="mandirmitra",
        session=object(),
    )
    assert len(items) == 1
    assert items[0]["id"] == "s1"
    assert items[0]["title"] == "Abhishekam"
    assert "devotee_mobile" not in items[0]


def test_office_ai_source_has_no_direct_sqlalchemy_accounting_imports():
    """Lightweight isolation guard: connector may import services, not raw SQL/Mongo of companions."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "modules" / "office_ai"
    forbidden = (
        "from app.accounting.models",
        "select(Journal",
        "JournalEntry",
        'get_collection("housing_complaints")',
        "get_collection('housing_complaints')",
        'get_collection("mandir_seva_bookings")',
        "LEGAL_MATTERS_COLLECTION",
    )
    offenders: list[str] = []
    for path in root.rglob("*.py"):
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
        repo_root / "frontend" / "shared" / "office-ai-workspace.js"
    ).read_text(encoding="utf-8")
    erp_shim = (
        repo_root / "frontend" / "mitrabooks-erp" / "modules" / "workspaces" / "office-ai.js"
    ).read_text(encoding="utf-8")

    assert 'getAttribute("data-task-id")' in office_ai_source
    assert "taskRecordId(task)" in office_ai_source
    assert 'status: "done"' in office_ai_source
    assert "Task marked done." in office_ai_source
    assert "missing task id" in office_ai_source
    assert "office-ai-workspace.js" in erp_shim
