#!/usr/bin/env python3
"""Validate production security controls without printing secret values."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
SECRET_MIN_LENGTHS = {
    "JWT_SECRET": 32,
    "OTP_PEPPER": 32,
    "MANDIR_ONBOARDING_SECRET": 32,
}
REQUIRED_FALSE_FLAGS = (
    "SUPER_ADMIN_BOOTSTRAP",
    "DEMO_MANDIR_BOOTSTRAP",
    "DEMO_MITRABOOKS_BOOTSTRAP",
    "DEMO_MITRABOOKS_E2E_SEED_ENABLED",
    "AUTH_EMAIL_DEBUG_RETURN_LINK",
    "MOBILE_OTP_DEBUG_RETURN_CODE",
    "ALLOW_OPEN_REGISTRATION",
)
FALSE_VALUES = {"0", "false", "no", "off"}
PLACEHOLDER_MARKERS = (
    "change-me",
    "changeme",
    "example",
    "placeholder",
    "replace-me",
    "secret-key",
    "your-secret",
    "your-super-secret",
)


def _validate_secret(name: str, value: str, minimum_length: int) -> list[str]:
    errors: list[str] = []
    normalized = value.strip()
    if not normalized:
        return [f"{name} must be set"]
    if len(normalized) < minimum_length:
        errors.append(f"{name} must contain at least {minimum_length} characters")
    lowered = normalized.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        errors.append(f"{name} must not use a placeholder value")
    if len(set(normalized)) < 8:
        errors.append(f"{name} does not have sufficient character diversity")
    return errors


def validate_config(environment: Mapping[str, str]) -> tuple[list[str], dict[str, object]]:
    """Return sanitized validation errors and evidence; never include secret values."""
    errors: list[str] = []
    environment_name = str(environment.get("ENVIRONMENT", "")).strip().lower()
    if environment_name not in {"production", "prod"}:
        errors.append("ENVIRONMENT must be explicitly set to production or prod")

    secret_values: dict[str, str] = {}
    secret_checks: dict[str, bool] = {}
    for name, minimum_length in SECRET_MIN_LENGTHS.items():
        value = str(environment.get(name, ""))
        secret_values[name] = value.strip()
        secret_errors = _validate_secret(name, value, minimum_length)
        errors.extend(secret_errors)
        secret_checks[name] = not secret_errors

    populated_secrets = [value for value in secret_values.values() if value]
    all_secrets_present = len(populated_secrets) == len(SECRET_MIN_LENGTHS)
    secrets_are_distinct = all_secrets_present and len(populated_secrets) == len(set(populated_secrets))
    if all_secrets_present and not secrets_are_distinct:
        errors.append("JWT_SECRET, OTP_PEPPER, and MANDIR_ONBOARDING_SECRET must be distinct")

    disabled_checks: dict[str, bool] = {}
    for name in REQUIRED_FALSE_FLAGS:
        raw_value = environment.get(name)
        is_explicitly_false = raw_value is not None and str(raw_value).strip().lower() in FALSE_VALUES
        disabled_checks[name] = is_explicitly_false
        if not is_explicitly_false:
            errors.append(f"{name} must be explicitly set to false")

    evidence: dict[str, object] = {
        "status": "passed" if not errors else "blocked",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "environment": "production" if environment_name in {"production", "prod"} else "invalid",
        "secret_policy_checks": secret_checks,
        "secrets_distinct": secrets_are_distinct,
        "disabled_control_checks": disabled_checks,
    }
    return errors, evidence


def workspace_output_path(path: Path) -> Path:
    resolved = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("evidence output must remain inside the workspace") from exc
    if resolved.suffix.lower() != ".json":
        raise ValueError("evidence output must use a .json file")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed production secret/bootstrap/debug configuration verification."
    )
    parser.add_argument(
        "--evidence-output",
        type=Path,
        help="Optional workspace-local path for sanitized JSON evidence.",
    )
    args = parser.parse_args()

    errors, evidence = validate_config(os.environ)
    rendered = json.dumps(evidence, indent=2, sort_keys=True)
    if args.evidence_output:
        try:
            output_path = workspace_output_path(args.evidence_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered + "\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            print(f"BLOCKED: unable to write sanitized evidence: {exc}", file=sys.stderr)
            return 1
    print(rendered)
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}", file=sys.stderr)
        return 1
    print("PRODUCTION SECURITY CONFIG: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
