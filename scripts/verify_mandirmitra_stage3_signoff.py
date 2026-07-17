#!/usr/bin/env python3
"""Fail-closed MandirMitra Stage 3 production signoff verifier."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
TAG_RE = re.compile(r"^backend-v\d+\.\d+\.\d+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SENSITIVE_KEYS = {
    "password", "access_token", "refresh_token", "authorization", "jwt_secret",
    "api_key", "donor_pan", "email", "payment_reference", "upi_id",
}


def utc_timestamp(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def url_origin(value: Any, label: str, *, require_https: bool = False) -> str:
    parsed = urlsplit(str(value or "").strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute URL")
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"{label} must use HTTP or HTTPS")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    if require_https and scheme != "https":
        raise ValueError(f"{label} must use HTTPS")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"{label} must include a hostname")
    host = f"[{hostname.lower()}]" if ":" in hostname else hostname.lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} contains an invalid port") from exc
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    authority = host if port is None or default_port else f"{host}:{port}"
    return f"{scheme}://{authority}"


def integer(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+", value.strip()):
        raise ValueError(f"{label} must be an integer")
    return int(value.strip())


def positive_int(value: Any, label: str) -> int:
    parsed = integer(value, label)
    if parsed < 1:
        raise ValueError(f"{label} must be at least 1")
    return parsed


def load_evidence(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} file is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    reject_sensitive_keys(payload, label)
    return payload


def workspace_evidence_path(path: Path, label: str) -> Path:
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} path must remain inside the workspace") from exc
    if resolved.suffix.lower() != ".json":
        raise ValueError(f"{label} path must use a .json file")
    return resolved


def reject_sensitive_keys(value: Any, label: str, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in SENSITIVE_KEYS or normalized.endswith("_password") or normalized.endswith("_token"):
                raise ValueError(f"{label} contains forbidden sensitive field at {path}.{key}")
            reject_sensitive_keys(child, label, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_keys(child, label, f"{path}[{index}]")


def require_fresh(timestamp: datetime, *, max_age_days: int, label: str) -> None:
    now = datetime.now(timezone.utc)
    if timestamp > now + timedelta(minutes=5):
        raise ValueError(f"{label} timestamp is in the future")
    if timestamp < now - timedelta(days=max_age_days):
        raise ValueError(f"{label} is older than {max_age_days} days")


def validate_browser(payload: dict[str, Any], max_age_days: int) -> dict[str, str]:
    if payload.get("gate") != "mandirmitra_stage3_browser_smoke":
        raise ValueError("browser evidence has an invalid gate identifier")
    if payload.get("status") != "passed":
        raise ValueError("browser evidence status must be passed")
    generated = utc_timestamp(payload.get("generated_at"), "browser generated_at")
    require_fresh(generated, max_age_days=max_age_days, label="browser evidence")
    if payload.get("organization_type") != "TEMPLE" or payload.get("app_key") != "mandirmitra":
        raise ValueError("browser evidence must use TEMPLE/mandirmitra context")
    required_modules = {"temple", "accounting", "audit"}
    if not required_modules.issubset(set(payload.get("enabled_modules") or [])):
        raise ValueError("browser evidence is missing required MandirMitra modules")
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not tenant_id:
        raise ValueError("browser evidence is missing tenant_id")
    return {
        "tenant_id": tenant_id,
        "frontend_origin": url_origin(payload.get("frontend_url"), "browser frontend_url"),
        "api_origin": url_origin(payload.get("api_base"), "browser api_base"),
    }


def validate_destructive(payload: dict[str, Any], max_age_days: int) -> dict[str, str]:
    if payload.get("gate") != "mandirmitra_stage3_destructive_demo":
        raise ValueError("destructive evidence has an invalid gate identifier")
    exit_code = integer(payload.get("exit_code", 1), "destructive evidence exit_code")
    if payload.get("status") != "passed" or exit_code != 0:
        raise ValueError("destructive evidence must be passed with exit_code=0")
    completed = utc_timestamp(payload.get("completed_at"), "destructive completed_at")
    require_fresh(completed, max_age_days=max_age_days, label="destructive evidence")
    if payload.get("organization_type_expected") != "TEMPLE" or payload.get("app_key") != "mandirmitra":
        raise ValueError("destructive evidence must use TEMPLE/mandirmitra context")
    for key in ("distinct_actor_check", "demo_write_marker_check", "trace_and_video_disabled"):
        if payload.get(key) is not True:
            raise ValueError(f"destructive evidence requires {key}=true")
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not tenant_id or not any(marker in tenant_id.lower() for marker in ("demo", "test", "seed")):
        raise ValueError("destructive evidence tenant must be visibly marked demo/test/seed")
    return {
        "tenant_id": tenant_id,
        "frontend_origin": url_origin(payload.get("frontend_origin"), "destructive frontend_origin"),
        "api_origin": url_origin(payload.get("api_origin"), "destructive api_origin"),
    }


def validate_backup_store(payload: Any, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} backup confirmation is required")
    for field in ("provider", "service_name", "schedule", "restore_owner", "restore_location"):
        if not str(payload.get(field) or "").strip():
            raise ValueError(f"{label} backup is missing {field}")
    if positive_int(payload.get("retention_days"), f"{label} backup retention_days") < 7:
        raise ValueError(f"{label} backup retention must be at least 7 days")
    if payload.get("provider_backup_enabled") is not True:
        raise ValueError(f"{label} provider backup must be confirmed enabled")
    last_backup = utc_timestamp(payload.get("last_successful_backup_at"), f"{label} last_successful_backup_at")
    require_fresh(last_backup, max_age_days=2, label=f"{label} successful backup")
    last_restore_test = utc_timestamp(payload.get("last_restore_test_at"), f"{label} last_restore_test_at")
    require_fresh(last_restore_test, max_age_days=90, label=f"{label} restore test")
    if payload.get("last_restore_test_status") != "passed":
        raise ValueError(f"{label} last restore test status must be passed")
    if payload.get("last_restore_test_target") != "isolated_nonproduction":
        raise ValueError(f"{label} restore test target must be isolated_nonproduction")


def validate_operations(
    payload: dict[str, Any], max_age_days: int, *, expected_tag: str | None = None,
) -> dict[str, str]:
    if payload.get("status") != "confirmed":
        raise ValueError("operations evidence status must be confirmed")
    confirmed = utc_timestamp(payload.get("confirmed_at"), "operations confirmed_at")
    require_fresh(confirmed, max_age_days=max_age_days, label="operations evidence")
    if not str(payload.get("confirmed_by_role") or "").strip():
        raise ValueError("operations evidence is missing confirmed_by_role")
    validate_backup_store(payload.get("mongodb_backup"), "MongoDB")
    validate_backup_store(payload.get("postgresql_backup"), "PostgreSQL")
    required_true = (
        "cross_store_restore_strategy_confirmed", "demo_bootstrap_disabled",
        "super_admin_bootstrap_disabled", "production_health_verified",
        "production_frontend_verified", "cors_verified",
    )
    for key in required_true:
        if payload.get(key) is not True:
            raise ValueError(f"operations evidence requires {key}=true")
    if payload.get("financial_rollback_policy") != "reversal_or_adjustment_only":
        raise ValueError("financial rollback policy must be reversal_or_adjustment_only")
    deployed_tag = str(payload.get("deployed_release_tag") or "").strip()
    if not TAG_RE.fullmatch(deployed_tag):
        raise ValueError("operations evidence deployed_release_tag must match backend-vMAJOR.MINOR.PATCH")
    if expected_tag is not None and deployed_tag != expected_tag:
        raise ValueError(f"operations evidence must attest deployed release {expected_tag}")
    deployed_commit = str(payload.get("deployed_commit_sha") or "").strip().lower()
    if not COMMIT_RE.fullmatch(deployed_commit):
        raise ValueError("operations evidence deployed_commit_sha must be a full 40-character commit SHA")
    return {
        "production_frontend_origin": url_origin(
            payload.get("production_frontend_origin"), "production frontend origin", require_https=True,
        ),
        "production_api_origin": url_origin(
            payload.get("production_api_origin"), "production API origin", require_https=True,
        ),
        "deployed_release_tag": deployed_tag,
        "deployed_commit_sha": deployed_commit,
    }


def git_capture(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed")
    return result.stdout.strip()


def validate_release_chain(expected_tag: str, rollback_tag: str, *, deployed_commit: str | None = None) -> None:
    if not TAG_RE.fullmatch(expected_tag) or not TAG_RE.fullmatch(rollback_tag):
        raise ValueError("release and rollback tags must match backend-vMAJOR.MINOR.PATCH")
    if expected_tag == rollback_tag:
        raise ValueError("release and rollback tags must be distinct")
    tags = set(git_capture("tag", "--list").splitlines())
    if expected_tag not in tags:
        raise ValueError(f"missing release tag {expected_tag}")
    if rollback_tag not in tags:
        raise ValueError(f"missing rollback tag {rollback_tag}")
    head = git_capture("rev-parse", "HEAD")
    release_commit = git_capture("rev-list", "-n", "1", expected_tag)
    if release_commit != head:
        raise ValueError(f"{expected_tag} must point at current HEAD")
    if deployed_commit is not None and release_commit.lower() != deployed_commit.lower():
        raise ValueError("operations evidence deployed commit does not match the release tag")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", rollback_tag, expected_tag],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError(f"rollback tag {rollback_tag} must be an ancestor of {expected_tag}")


def validate_clean_worktree() -> None:
    if git_capture("status", "--short"):
        raise ValueError("production signoff requires a clean worktree")


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise ValueError(f"command failed: {' '.join(command)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MandirMitra Stage 3 production signoff evidence.")
    parser.add_argument("--browser-evidence", required=True, type=Path)
    parser.add_argument("--destructive-evidence", required=True, type=Path)
    parser.add_argument("--operations-evidence", required=True, type=Path)
    parser.add_argument("--rollback-tag", required=True)
    parser.add_argument("--max-evidence-age-days", type=int, default=7)
    args = parser.parse_args()

    if args.max_evidence_age_days < 1:
        print("BLOCKED: max evidence age must be at least one day", file=sys.stderr)
        return 1
    try:
        evidence_paths = {
            "browser evidence": workspace_evidence_path(args.browser_evidence, "browser evidence"),
            "destructive evidence": workspace_evidence_path(args.destructive_evidence, "destructive evidence"),
            "operations evidence": workspace_evidence_path(args.operations_evidence, "operations evidence"),
        }
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    try:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        print("BLOCKED: VERSION file is missing or unreadable", file=sys.stderr)
        return 1
    if not VERSION_RE.fullmatch(version):
        print("BLOCKED: VERSION must use MAJOR.MINOR.PATCH", file=sys.stderr)
        return 1
    expected_tag = f"backend-v{version}"
    blockers: list[str] = []
    browser: dict[str, str] = {}
    destructive: dict[str, str] = {}
    operations: dict[str, str] = {}
    try:
        browser = validate_browser(
            load_evidence(evidence_paths["browser evidence"], "browser evidence"),
            args.max_evidence_age_days,
        )
    except ValueError as exc:
        blockers.append(str(exc))
    try:
        destructive = validate_destructive(
            load_evidence(evidence_paths["destructive evidence"], "destructive evidence"),
            args.max_evidence_age_days,
        )
    except ValueError as exc:
        blockers.append(str(exc))
    try:
        operations = validate_operations(
            load_evidence(evidence_paths["operations evidence"], "operations evidence"),
            args.max_evidence_age_days,
            expected_tag=expected_tag,
        )
    except ValueError as exc:
        blockers.append(str(exc))
    if browser and destructive:
        for key in ("tenant_id", "frontend_origin", "api_origin"):
            if browser[key] != destructive[key]:
                blockers.append(f"browser/destructive {key} mismatch")
    try:
        validate_clean_worktree()
    except ValueError as exc:
        blockers.append(str(exc))
    try:
        validate_release_chain(
            expected_tag,
            args.rollback_tag,
            deployed_commit=operations.get("deployed_commit_sha") if operations else None,
        )
    except ValueError as exc:
        blockers.append(str(exc))
    if blockers:
        print("MANDIRMITRA STAGE 3 SIGNOFF: BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        return 1

    try:
        run([sys.executable, "scripts/preflight.py", "--all"])
        run([
            sys.executable, "scripts/release_preflight.py", "--target", "production",
            "--expected-tag", expected_tag, "--require-current-tag",
        ])
    except ValueError as exc:
        print(f"MANDIRMITRA STAGE 3 SIGNOFF: BLOCKED\n- {exc}")
        return 1
    print(f"MANDIRMITRA STAGE 3 SIGNOFF: PASSED ({expected_tag}, rollback {args.rollback_tag})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
