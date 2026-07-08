from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.auth import router as auth_router
from app.main import app


def test_mitrabooks_forgot_password_uses_mitrabooks_reset_link(monkeypatch) -> None:
    sent_email: dict = {}

    async def fake_get_user_by_email(_email: str):
        return {
            "user_id": "user-mb-1",
            "email": "owner@example.com",
            "auth_provider": "password",
            "hashed_password": "hashed",
        }

    async def fake_create_email_action_token(**_kwargs):
        return "reset-token-123"

    async def fake_send_auth_email(**kwargs):
        sent_email.update(kwargs)
        return True, None

    monkeypatch.setattr(auth_router, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_router, "_create_email_action_token", fake_create_email_action_token)
    monkeypatch.setattr(auth_router, "_send_auth_email", fake_send_auth_email)
    monkeypatch.setattr(
        auth_router,
        "get_settings",
        lambda: SimpleNamespace(
            AUTH_RESET_TOKEN_TTL_MINUTES=30,
            AUTH_EMAIL_DEBUG_RETURN_LINK=True,
            AUTH_PUBLIC_BASE_URL="",
        ),
    )

    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "owner@example.com"},
        headers={
            "Origin": "https://erp.example",
            "X-App-Key": "mitrabooks",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reset_link_debug"] == (
        "https://erp.example/mitrabooks-erp/index.html?action=reset&token=reset-token-123"
    )
    assert sent_email["subject"] == "Reset your MitraBooks password"
    assert "reset your MitraBooks password" in sent_email["body"]
