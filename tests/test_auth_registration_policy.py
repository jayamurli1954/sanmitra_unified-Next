from fastapi import HTTPException
import pytest

from app.config import Settings
from app.core.auth import registration_policy as policy


def test_normalize_public_self_service_role_rejects_elevated_role() -> None:
    with pytest.raises(HTTPException) as exc:
        policy.normalize_public_self_service_role("tenant_admin")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_self_service_tenant_id_allows_seed_tenant_when_open_registration_enabled(monkeypatch) -> None:
    class FakeSettings:
        ALLOW_OPEN_REGISTRATION = True

    monkeypatch.setattr(policy, "get_settings", lambda: FakeSettings())

    tenant_id = await policy.resolve_self_service_tenant_id(requested_tenant_id=None)
    assert tenant_id == policy.DEV_OPEN_REGISTRATION_TENANT_ID


@pytest.mark.asyncio
async def test_resolve_self_service_tenant_id_blocks_arbitrary_tenant(monkeypatch) -> None:
    class FakeSettings:
        ALLOW_OPEN_REGISTRATION = True

    monkeypatch.setattr(policy, "get_settings", lambda: FakeSettings())

    with pytest.raises(HTTPException) as exc:
        await policy.resolve_self_service_tenant_id(requested_tenant_id="tenant-attacker")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_self_service_tenant_id_uses_approved_onboarding(monkeypatch) -> None:
    class FakeSettings:
        ALLOW_OPEN_REGISTRATION = False

    async def fake_get_onboarding_request(_request_id: str):
        return {
            "status": "approved",
            "approved_tenant_id": "tenant-approved",
            "admin_email": "admin@example.com",
        }

    monkeypatch.setattr(policy, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(policy, "get_onboarding_request", fake_get_onboarding_request)

    tenant_id = await policy.resolve_self_service_tenant_id(
        requested_tenant_id="tenant-attacker",
        onboarding_request_id="req-1",
        email="admin@example.com",
    )
    assert tenant_id == "tenant-approved"


def _production_settings_without_bootstrap() -> Settings:
    settings = Settings()
    settings.ENVIRONMENT = "production"
    settings.JWT_SECRET = "test-jwt-secret"
    settings.AUTH_EMAIL_DEBUG_RETURN_LINK = False
    settings.MOBILE_OTP_DEBUG_RETURN_CODE = False
    settings.SUPER_ADMIN_BOOTSTRAP = False
    settings.DEMO_MANDIR_BOOTSTRAP = False
    settings.DEMO_MITRABOOKS_BOOTSTRAP = False
    return settings


def test_settings_validate_requires_mandir_onboarding_secret_in_production() -> None:
    settings = _production_settings_without_bootstrap()
    settings.MANDIR_ONBOARDING_SECRET = ""
    settings.ALLOW_OPEN_REGISTRATION = False

    with pytest.raises(ValueError, match="MANDIR_ONBOARDING_SECRET"):
        settings.validate()


def test_settings_validate_blocks_open_registration_in_production() -> None:
    settings = _production_settings_without_bootstrap()
    settings.MANDIR_ONBOARDING_SECRET = "onboarding-secret"
    settings.ALLOW_OPEN_REGISTRATION = True

    with pytest.raises(ValueError, match="ALLOW_OPEN_REGISTRATION"):
        settings.validate()
