"""Behavioral checks that public abuse controls fail with HTTP 429."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.core.rate_limiting import limiter
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_rate_limit_storage():
    """Prevent counters from leaking across behavioral tests or the wider suite."""
    limiter.reset()
    yield
    limiter.reset()


def _assert_threshold(responses, *, allowed: int) -> None:
    assert all(response.status_code != 429 for response in responses[:allowed])
    assert responses[allowed].status_code == 429
    payload = responses[allowed].json()
    assert "rate limit" in str(payload.get("error") or payload.get("detail") or "").lower()


def test_login_returns_429_after_ten_attempts(monkeypatch):
    from app.core.auth import router as auth_router

    async def reject_login(*_args, **_kwargs):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    monkeypatch.setattr(auth_router, "login_user", reject_login)
    with TestClient(app) as client:
        responses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "Wrong123!"},
                headers={"X-App-Key": "mitrabooks"},
            )
            for _ in range(11)
        ]

    _assert_threshold(responses, allowed=10)


def test_forgot_password_returns_429_after_five_attempts(monkeypatch):
    from app.core.auth import router as auth_router

    async def unknown_user(_email):
        return None

    monkeypatch.setattr(auth_router, "get_user_by_email", unknown_user)
    with TestClient(app) as client:
        responses = [
            client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nobody@example.com"},
                headers={"X-App-Key": "mitrabooks"},
            )
            for _ in range(6)
        ]

    assert all(response.status_code == 200 for response in responses[:5])
    _assert_threshold(responses, allowed=5)


def test_mobile_otp_send_returns_429_after_five_attempts(monkeypatch):
    from app.core.auth import router as auth_router

    async def send_stub(_mobile):
        return {
            "status": "sent",
            "expires_in_seconds": 300,
            "resend_after_seconds": 60,
        }

    monkeypatch.setattr(auth_router, "send_mobile_otp", send_stub)
    with TestClient(app) as client:
        responses = [
            client.post("/api/v1/auth/mobile-otp/send", json={"mobile": "+919876543210"})
            for _ in range(6)
        ]

    _assert_threshold(responses, allowed=5)


def test_ca_invite_preview_returns_429_after_twenty_attempts(monkeypatch):
    from app.modules.business import router as business_router

    async def preview_stub(*, token: str):
        return {"masked_email": "c***@example.com"}

    monkeypatch.setattr(business_router.ca_access_module, "preview_ca_invite", preview_stub)
    with TestClient(app) as client:
        responses = [
            client.get("/api/v1/business/ca/invite/random-token/preview")
            for _ in range(21)
        ]

    assert all(response.status_code == 200 for response in responses[:20])
    _assert_threshold(responses, allowed=20)


def test_ca_invite_accept_returns_429_after_ten_attempts(monkeypatch):
    from app.modules.business import router as business_router

    async def reject_accept(**_kwargs):
        raise ValueError("unavailable")

    monkeypatch.setattr(business_router.ca_access_module, "accept_ca_invite", reject_accept)
    with TestClient(app) as client:
        responses = [
            client.post(
                "/api/v1/business/ca/invite/random-token/accept",
                json={"password": "Secret123!", "full_name": "CA Ravi"},
            )
            for _ in range(11)
        ]

    assert all(response.status_code == 400 for response in responses[:10])
    _assert_threshold(responses, allowed=10)


def test_remaining_core_auth_endpoint_types_enforce_their_thresholds(monkeypatch):
    """Cover every other decorated core-auth handler, resetting per endpoint scope."""
    from app.core.auth import router as auth_router

    async def reject(*_args, **_kwargs):
        raise HTTPException(status_code=401, detail="Rejected for rate-limit test")

    async def resolve_tenant(**_kwargs):
        return "public-self-service"

    async def create_user_stub(**_kwargs):
        return {"user_id": "test-user", "role": "user"}

    class EmptyUsers:
        async def find_one(self, *_args, **_kwargs):
            return None

    async def action_token_stub(**_kwargs):
        return "safe-test-action-token"

    async def email_stub(**_kwargs):
        return True, None

    monkeypatch.setattr(auth_router, "login_user", reject)
    monkeypatch.setattr(auth_router, "assert_open_registration_allowed", lambda: None)
    monkeypatch.setattr(auth_router, "resolve_self_service_tenant_id", resolve_tenant)
    monkeypatch.setattr(auth_router, "create_user", create_user_stub)
    monkeypatch.setattr(auth_router, "get_collection", lambda _name: EmptyUsers())
    monkeypatch.setattr(auth_router, "_create_email_action_token", action_token_stub)
    monkeypatch.setattr(auth_router, "_send_auth_email", email_stub)
    monkeypatch.setattr(auth_router, "_load_valid_email_action", reject)
    monkeypatch.setattr(auth_router, "login_google_user", reject)
    monkeypatch.setattr(auth_router, "verify_mobile_otp", reject)
    monkeypatch.setattr(auth_router, "rotate_refresh_token", reject)

    cases = [
        ("/api/v1/auth/local-login", {"email": "nobody@example.com", "password": "Wrong123!"}, 10),
        ("/api/v1/auth/register", {"email": "new@example.com", "password": "Strong123!"}, 5),
        ("/api/v1/auth/register-request", {"email": "new@example.com", "full_name": "New User"}, 5),
        ("/api/v1/auth/activate", {"token": "safe-token", "password": "Strong123!"}, 5),
        ("/api/v1/auth/reset-password", {"token": "safe-token", "new_password": "Strong123!"}, 5),
        ("/api/v1/auth/google", {"id_token": "safe-google-token"}, 10),
        ("/api/v1/auth/mobile-otp/verify", {"mobile": "+919876543210", "otp": "123456"}, 10),
        ("/api/v1/auth/refresh", {"refresh_token": "safe-refresh-token"}, 20),
    ]

    with TestClient(app) as client:
        for path, payload, allowed in cases:
            limiter.reset()
            responses = [
                client.post(path, json=payload, headers={"X-App-Key": "mitrabooks"})
                for _ in range(allowed + 1)
            ]
            _assert_threshold(responses, allowed=allowed)
