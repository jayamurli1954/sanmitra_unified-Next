from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from scripts import verify_mandirmitra_stage3_signoff as gate


def timestamp(*, days_ago: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def browser_evidence() -> dict[str, object]:
    return {
        "gate": "mandirmitra_stage3_browser_smoke",
        "status": "passed",
        "generated_at": timestamp(),
        "tenant_id": "demo-mandir-tenant",
        "organization_type": "TEMPLE",
        "app_key": "mandirmitra",
        "enabled_modules": ["temple", "accounting", "audit"],
        "frontend_url": "https://demo.example.org/mitrabooks-erp/",
        "api_base": "https://demo-api.example.org/api/v1",
    }


def destructive_evidence() -> dict[str, object]:
    return {
        "gate": "mandirmitra_stage3_destructive_demo",
        "status": "passed",
        "exit_code": 0,
        "completed_at": timestamp(),
        "tenant_id": "demo-mandir-tenant",
        "organization_type_expected": "TEMPLE",
        "app_key": "mandirmitra",
        "distinct_actor_check": True,
        "demo_write_marker_check": True,
        "trace_and_video_disabled": True,
        "frontend_origin": "https://demo.example.org",
        "api_origin": "https://demo-api.example.org",
    }


def backup(service_name: str) -> dict[str, object]:
    return {
        "provider": "managed-provider",
        "service_name": service_name,
        "backup_mode": "provider_managed_snapshot",
        "provider_backup_enabled": True,
        "schedule": "daily",
        "retention_days": 14,
        "last_successful_backup_at": timestamp(),
        "last_restore_test_at": timestamp(days_ago=30),
        "last_restore_test_status": "passed",
        "last_restore_test_target": "isolated_nonproduction",
        "restore_owner": "operations-role",
        "restore_location": "production-vault",
    }


def operations_evidence() -> dict[str, object]:
    return {
        "status": "confirmed",
        "confirmed_at": timestamp(),
        "confirmed_by_role": "release-operator-role",
        "production_frontend_origin": "https://erp.example.org",
        "production_api_origin": "https://api.example.org",
        "deployed_release_tag": "backend-v1.3.0",
        "deployed_commit_sha": "a" * 40,
        "mongodb_backup": backup("mongodb-production"),
        "postgresql_backup": backup("postgresql-production"),
        "cross_store_restore_strategy_confirmed": True,
        "demo_bootstrap_disabled": True,
        "super_admin_bootstrap_disabled": True,
        "production_health_verified": True,
        "production_frontend_verified": True,
        "cors_verified": True,
        "financial_rollback_policy": "reversal_or_adjustment_only",
    }


def test_valid_evidence_contracts_bind_the_same_demo_context() -> None:
    browser = gate.validate_browser(browser_evidence(), 7)
    destructive = gate.validate_destructive(destructive_evidence(), 7)
    operations = gate.validate_operations(operations_evidence(), 7)

    assert browser == destructive
    assert operations == {
        "production_frontend_origin": "https://erp.example.org",
        "production_api_origin": "https://api.example.org",
        "deployed_release_tag": "backend-v1.3.0",
        "deployed_commit_sha": "a" * 40,
    }


def test_browser_evidence_rejects_stale_or_incomplete_context() -> None:
    stale = browser_evidence()
    stale["generated_at"] = timestamp(days_ago=8)
    with pytest.raises(ValueError, match="older than 7 days"):
        gate.validate_browser(stale, 7)

    missing_module = browser_evidence()
    missing_module["enabled_modules"] = ["temple", "audit"]
    with pytest.raises(ValueError, match="missing required MandirMitra modules"):
        gate.validate_browser(missing_module, 7)


def test_destructive_evidence_rejects_real_tenant_and_missing_safety_marker() -> None:
    real_tenant = destructive_evidence()
    real_tenant["tenant_id"] = "parlathya-prathishtana"
    with pytest.raises(ValueError, match="visibly marked demo/test/seed"):
        gate.validate_destructive(real_tenant, 7)

    unsafe = destructive_evidence()
    unsafe["trace_and_video_disabled"] = False
    with pytest.raises(ValueError, match="trace_and_video_disabled=true"):
        gate.validate_destructive(unsafe, 7)


def test_operations_evidence_requires_recent_backup_restore_and_https() -> None:
    stale_restore = operations_evidence()
    stale_restore["mongodb_backup"]["last_restore_test_at"] = timestamp(days_ago=91)  # type: ignore[index]
    with pytest.raises(ValueError, match="restore test is older than 90 days"):
        gate.validate_operations(stale_restore, 7)

    http_target = operations_evidence()
    http_target["production_api_origin"] = "http://api.example.org"
    with pytest.raises(ValueError, match="production API origin must use HTTPS"):
        gate.validate_operations(http_target, 7)


def test_operations_evidence_binds_exact_release_and_restore_result() -> None:
    wrong_release = operations_evidence()
    with pytest.raises(ValueError, match="must attest deployed release backend-v1.4.0"):
        gate.validate_operations(wrong_release, 7, expected_tag="backend-v1.4.0")

    failed_restore = operations_evidence()
    failed_restore["postgresql_backup"]["last_restore_test_status"] = "failed"  # type: ignore[index]
    with pytest.raises(ValueError, match="last restore test status must be passed"):
        gate.validate_operations(failed_restore, 7)


def test_operations_evidence_allows_operator_managed_logical_exports() -> None:
    payload = operations_evidence()
    payload["mongodb_backup"].update({  # type: ignore[union-attr]
        "provider": "MongoDB tools",
        "backup_mode": "operator_managed_logical_export",
        "provider_backup_enabled": False,
        "schedule": "daily mongodump",
        "restore_location": "encrypted-offsite-backup-vault / Cluster0-restore-drill",
    })

    gate.validate_operations(payload, 7)


def test_operations_evidence_rejects_unknown_backup_mode() -> None:
    payload = operations_evidence()
    payload["mongodb_backup"]["backup_mode"] = "manual_note_only"  # type: ignore[index]

    with pytest.raises(ValueError, match="backup_mode must be"):
        gate.validate_operations(payload, 7)


def test_operations_evidence_rejects_disabled_provider_snapshot() -> None:
    payload = operations_evidence()
    payload["mongodb_backup"]["provider_backup_enabled"] = False  # type: ignore[index]

    with pytest.raises(ValueError, match="provider backup must be confirmed enabled"):
        gate.validate_operations(payload, 7)


def test_malformed_numeric_evidence_fails_closed() -> None:
    malformed_exit = destructive_evidence()
    malformed_exit["exit_code"] = "not-a-number"
    with pytest.raises(ValueError, match="exit_code must be an integer"):
        gate.validate_destructive(malformed_exit, 7)

    fractional_exit = destructive_evidence()
    fractional_exit["exit_code"] = 0.1
    with pytest.raises(ValueError, match="exit_code must be an integer"):
        gate.validate_destructive(fractional_exit, 7)

    malformed_retention = operations_evidence()
    malformed_retention["mongodb_backup"]["retention_days"] = "unknown"  # type: ignore[index]
    with pytest.raises(ValueError, match="retention_days must be an integer"):
        gate.validate_operations(malformed_retention, 7)


def test_evidence_rejects_sensitive_fields_at_any_depth() -> None:
    payload = operations_evidence()
    payload["mongodb_backup"]["access_token"] = "must-not-be-stored"  # type: ignore[index]
    with pytest.raises(ValueError, match="forbidden sensitive field"):
        gate.reject_sensitive_keys(payload, "operations evidence")


def test_release_tags_are_strictly_versioned_and_distinct(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="must match"):
        gate.validate_release_chain("v1.3.0", "backend-v1.2.0")
    with pytest.raises(ValueError, match="must be distinct"):
        gate.validate_release_chain("backend-v1.3.0", "backend-v1.3.0")

    calls: list[tuple[str, ...]] = []

    def fake_git_capture(*args: str) -> str:
        calls.append(args)
        values = {
            ("tag", "--list"): "backend-v1.2.0\nbackend-v1.3.0",
            ("rev-parse", "HEAD"): "release-commit",
            ("rev-list", "-n", "1", "backend-v1.3.0"): "release-commit",
        }
        return values[args]

    class Result:
        returncode = 0

    monkeypatch.setattr(gate, "git_capture", fake_git_capture)
    monkeypatch.setattr(gate.subprocess, "run", lambda *args, **kwargs: Result())
    gate.validate_release_chain(
        "backend-v1.3.0", "backend-v1.2.0", deployed_commit="release-commit",
    )
    assert ("rev-parse", "HEAD") in calls


def test_workspace_evidence_paths_cannot_escape_repository() -> None:
    inside = gate.workspace_evidence_path(gate.ROOT / "tmp" / "evidence.json", "evidence")
    assert inside == (gate.ROOT / "tmp" / "evidence.json").resolve()
    with pytest.raises(ValueError, match="inside the workspace"):
        gate.workspace_evidence_path(gate.ROOT.parent / "evidence.json", "evidence")
    with pytest.raises(ValueError, match="must use a .json file"):
        gate.workspace_evidence_path(gate.ROOT / "tmp" / "evidence.txt", "evidence")


def test_documented_operations_example_matches_required_release_and_restore_contract() -> None:
    contract = (
        gate.ROOT / "docs" / "operations" / "MANDIRMITRA_PRODUCTION_EVIDENCE_SCHEMA.md"
    ).read_text(encoding="utf-8")

    assert '"deployed_release_tag"' in contract
    assert '"deployed_commit_sha"' in contract
    assert contract.count('"last_restore_test_status": "passed"') == 2
    assert contract.count('"last_restore_test_target": "isolated_nonproduction"') == 2
