from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from scripts.verify_production_security_config import validate_config, workspace_output_path


def valid_environment() -> dict[str, str]:
    return {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "jwt-" + "a1B2c3D4" * 5,
        "OTP_PEPPER": "otp-" + "e5F6g7H8" * 5,
        "MANDIR_ONBOARDING_SECRET": "mandir-" + "i9J0k1L2" * 5,
        "SUPER_ADMIN_BOOTSTRAP": "false",
        "DEMO_MANDIR_BOOTSTRAP": "false",
        "DEMO_MITRABOOKS_BOOTSTRAP": "false",
        "DEMO_MITRABOOKS_E2E_SEED_ENABLED": "false",
        "AUTH_EMAIL_DEBUG_RETURN_LINK": "false",
        "MOBILE_OTP_DEBUG_RETURN_CODE": "false",
        "ALLOW_OPEN_REGISTRATION": "false",
    }


def production_settings() -> Settings:
    settings = Settings()
    settings.ENVIRONMENT = "production"
    settings.JWT_SECRET = "test-jwt-secret"
    settings.OTP_PEPPER = "test-otp-pepper"
    settings.MANDIR_ONBOARDING_SECRET = "test-onboarding-secret"
    settings.AUTH_EMAIL_DEBUG_RETURN_LINK = False
    settings.MOBILE_OTP_DEBUG_RETURN_CODE = False
    settings.ALLOW_OPEN_REGISTRATION = False
    settings.SUPER_ADMIN_BOOTSTRAP = False
    settings.SUPER_ADMIN_PASSWORD = "Test-only-super-admin-password1!"
    settings.DEMO_MANDIR_BOOTSTRAP = False
    settings.DEMO_MANDIR_ADMIN_PASSWORD = "Test-only-mandir-password1!"
    settings.DEMO_MITRABOOKS_BOOTSTRAP = False
    settings.DEMO_MITRABOOKS_ADMIN_PASSWORD = "Test-only-mitrabooks-password1!"
    settings.DEMO_MITRABOOKS_E2E_SEED_ENABLED = False
    return settings


def test_sanitized_verifier_accepts_strong_distinct_secrets_and_disabled_controls() -> None:
    environment = valid_environment()
    errors, evidence = validate_config(environment)

    assert errors == []
    assert evidence["status"] == "passed"
    serialized = repr(evidence)
    for secret_name in ("JWT_SECRET", "OTP_PEPPER", "MANDIR_ONBOARDING_SECRET"):
        assert environment[secret_name] not in serialized


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("JWT_SECRET", "", "JWT_SECRET must be set"),
        ("OTP_PEPPER", "short", "at least 32 characters"),
        ("MANDIR_ONBOARDING_SECRET", "change-me-please-change-me-please-1234", "placeholder"),
    ],
)
def test_sanitized_verifier_rejects_missing_weak_or_placeholder_secrets(
    name: str, value: str, message: str
) -> None:
    environment = valid_environment()
    environment[name] = value

    errors, evidence = validate_config(environment)

    assert any(message in error for error in errors)
    assert evidence["status"] == "blocked"
    if value:
        assert value not in repr(evidence)


@pytest.mark.parametrize("flag", [
    "SUPER_ADMIN_BOOTSTRAP",
    "DEMO_MANDIR_BOOTSTRAP",
    "DEMO_MITRABOOKS_BOOTSTRAP",
    "DEMO_MITRABOOKS_E2E_SEED_ENABLED",
    "AUTH_EMAIL_DEBUG_RETURN_LINK",
    "MOBILE_OTP_DEBUG_RETURN_CODE",
    "ALLOW_OPEN_REGISTRATION",
])
def test_sanitized_verifier_requires_explicit_false_for_dangerous_controls(flag: str) -> None:
    environment = valid_environment()
    environment[flag] = "true"

    errors, evidence = validate_config(environment)

    assert f"{flag} must be explicitly set to false" in errors
    assert evidence["disabled_control_checks"][flag] is False


def test_sanitized_verifier_requires_distinct_secrets() -> None:
    environment = valid_environment()
    environment["OTP_PEPPER"] = environment["JWT_SECRET"]

    errors, evidence = validate_config(environment)

    assert any("must be distinct" in error for error in errors)
    assert evidence["secrets_distinct"] is False


@pytest.mark.parametrize(
    "flag",
    [
        "SUPER_ADMIN_BOOTSTRAP",
        "DEMO_MANDIR_BOOTSTRAP",
        "DEMO_MITRABOOKS_BOOTSTRAP",
        "DEMO_MITRABOOKS_E2E_SEED_ENABLED",
    ],
)
def test_settings_validate_rejects_bootstrap_or_demo_seed_in_production(flag: str) -> None:
    settings = production_settings()
    setattr(settings, flag, True)

    with pytest.raises(ValueError, match="must be disabled"):
        settings.validate()


def test_workspace_output_path_rejects_non_json_and_outside_workspace(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="inside the workspace"):
        workspace_output_path(tmp_path / "evidence.json")
    with pytest.raises(ValueError, match=".json"):
        workspace_output_path(Path("outputs/production-config.txt"))
