"""CA Access — token-based invite flow, accept, revoke, list. Uses fake Mongo via mongomock."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_invite(status="pending", expired=False):
    now = datetime.now(timezone.utc)
    return {
        "_id": "oid1",
        "invite_id": "inv-1",
        "tenant_id": "t1",
        "app_key": "mitrabooks",
        "email": "ca@example.com",
        "full_name": "CA Ravi",
        "token": "tok123",
        "status": status,
        "invited_by": "admin",
        "created_at": now,
        "expires_at": now - timedelta(hours=1) if expired else now + timedelta(days=7),
        "accepted_at": None,
        "user_id": None,
    }


# ── tests ─────────────────────────────────────────────────────────────────────

def test_accept_route_accepts_text_plain_json(monkeypatch):
    from app.main import app
    from app.modules.business import router as business_router

    async def fake_accept_ca_invite(*, token: str, password: str, full_name: str | None = None):
        assert token == "tok123"
        assert password == "Secret123!"
        assert full_name == "CA Ravi"
        return {
            "user_id": "u-1",
            "role": "ca_viewer",
        }

    monkeypatch.setattr(business_router.ca_access_module, "accept_ca_invite", fake_accept_ca_invite)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/business/ca/invite/tok123/accept",
            data='{"password":"Secret123!","full_name":"CA Ravi"}',
            headers={"Content-Type": "text/plain;charset=UTF-8"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["user_id"] == "u-1"
    assert payload["role"] == "ca_viewer"

@pytest.mark.asyncio
async def test_invite_provisions_inactive_ca_user_and_sends_token_email():
    from app.modules.business import ca_access

    mock_invites = AsyncMock()
    mock_invites.find_one = AsyncMock(return_value=None)
    mock_invites.insert_one = AsyncMock()
    mock_invites.create_index = AsyncMock()
    mock_users = AsyncMock()
    mock_users.find_one = AsyncMock(return_value=None)
    mock_users.insert_one = AsyncMock()
    email_delivery = {"sent": True, "error": None}

    def _col(name):
        if name == "business_ca_invitations":
            return mock_invites
        return mock_users

    with patch("app.modules.business.ca_access.get_collection", side_effect=_col), \
         patch("app.modules.business.ca_access._send_invite_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = email_delivery
        result = await ca_access.invite_ca(
            tenant_id="t1", app_key="mitrabooks",
            email="CA@Example.com", full_name="CA Ravi", invited_by="admin1",
        )

    assert result["email"] == "ca@example.com"
    assert result["status"] == "invited"
    assert "token" in result
    assert result["user_id"]
    assert result["email_delivery"] == email_delivery
    assert result["resent"] is False
    mock_email.assert_awaited_once()
    assert mock_email.call_args.kwargs["email"] == "ca@example.com"
    assert mock_email.call_args.kwargs["token"] == result["token"]
    assert mock_email.call_args.kwargs["expires_at"] == result["expires_at"]
    mock_users.insert_one.assert_awaited_once()
    inserted_user = mock_users.insert_one.call_args[0][0]
    assert inserted_user["role"] == "ca_viewer"
    assert inserted_user["auth_provider"] == "password_setup_pending"
    assert inserted_user["provider_subject"] == "invite:ca@example.com"
    assert inserted_user["is_active"] is False
    assert inserted_user["invite_pending"] is True
    assert "hashed_password" not in inserted_user


@pytest.mark.asyncio
async def test_existing_ca_invite_resends_token_and_keeps_existing_user_in_pending_state():
    from app.modules.business import ca_access

    invite = _make_invite("pending")
    existing_user = {
        "_id": "user-oid",
        "user_id": "u-existing",
        "email": "ca@example.com",
        "tenant_id": "t1",
        "role": "ca_viewer",
        "subscription_tier": "free",
        "subscription_status": "active",
        "query_usage_count": 4,
    }
    mock_invites = AsyncMock()
    mock_invites.find_one = AsyncMock(return_value=invite)
    mock_invites.update_one = AsyncMock()
    mock_invites.create_index = AsyncMock()
    mock_users = AsyncMock()
    mock_users.find_one = AsyncMock(return_value=existing_user)
    mock_users.update_one = AsyncMock()
    email_delivery = {"sent": True, "error": None}

    def _col(name):
        if name == "business_ca_invitations":
            return mock_invites
        return mock_users

    with patch("app.modules.business.ca_access.get_collection", side_effect=_col), \
         patch("app.modules.business.ca_access._send_invite_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = email_delivery
        result = await ca_access.invite_ca(
            tenant_id="t1", app_key="mitrabooks",
            email="ca@example.com", full_name="CA Ravi", invited_by="admin1",
        )

    assert result["invite_id"] == "inv-1"
    assert result["resent"] is True
    assert result["email_delivery"] == email_delivery
    assert result["status"] == "invited"
    assert result["user_id"] == "u-existing"
    mock_invites.update_one.assert_awaited_once()
    mock_users.update_one.assert_awaited_once()
    mock_email.assert_awaited_once()
    assert mock_email.call_args.kwargs["token"] == result["token"]
    user_update = mock_users.update_one.call_args[0][1]["$set"]
    assert user_update["invite_pending"] is True
    assert user_update["role"] == "ca_viewer"
    assert user_update["must_change_password"] is False


@pytest.mark.asyncio
async def test_accept_invite_creates_user():
    from app.modules.business import ca_access

    invite = _make_invite("pending")
    mock_inv_col = AsyncMock()
    mock_inv_col.find_one = AsyncMock(return_value=invite)
    mock_inv_col.update_one = AsyncMock()
    mock_inv_col.create_index = AsyncMock()

    mock_users_col = AsyncMock()
    mock_users_col.find_one = AsyncMock(return_value=None)
    mock_users_col.insert_one = AsyncMock()

    def _col(name):
        if name == "business_ca_invitations":
            return mock_inv_col
        return mock_users_col

    with patch("app.modules.business.ca_access.get_collection", side_effect=_col), \
         patch("app.modules.business.ca_access.hash_password", return_value="hashed"):
        result = await ca_access.accept_ca_invite(token="tok123", password="Secret123!")

    assert result["role"] == "ca_viewer"
    mock_users_col.insert_one.assert_awaited_once()
    inserted = mock_users_col.insert_one.call_args[0][0]
    assert inserted["role"] == "ca_viewer"
    assert inserted["is_active"] is True
    assert inserted["invite_pending"] is False
    assert inserted["must_change_password"] is False
    assert inserted["auth_provider"] == "password"


@pytest.mark.asyncio
async def test_accept_invite_updates_existing_tenant_user_password():
    from app.modules.business import ca_access

    invite = _make_invite("pending")
    existing_user = {
        "_id": "user-oid",
        "user_id": "u-existing",
        "email": "ca@example.com",
        "tenant_id": "t1",
        "role": "viewer",
        "hashed_password": "old-hash",
    }
    mock_inv_col = AsyncMock()
    mock_inv_col.find_one = AsyncMock(return_value=invite)
    mock_inv_col.update_one = AsyncMock()
    mock_inv_col.create_index = AsyncMock()

    mock_users_col = AsyncMock()
    mock_users_col.find_one = AsyncMock(return_value=existing_user)
    mock_users_col.update_one = AsyncMock()

    def _col(name):
        if name == "business_ca_invitations":
            return mock_inv_col
        return mock_users_col

    with patch("app.modules.business.ca_access.get_collection", side_effect=_col), \
         patch("app.modules.business.ca_access.hash_password", return_value="new-hash"):
        result = await ca_access.accept_ca_invite(token="tok123", password="Secret123!")

    assert result["user_id"] == "u-existing"
    update_doc = mock_users_col.update_one.call_args[0][1]["$set"]
    assert update_doc["role"] == "ca_viewer"
    assert update_doc["is_active"] is True
    assert update_doc["hashed_password"] == "new-hash"
    assert update_doc["auth_provider"] == "password"
    assert update_doc["invite_pending"] is False
    assert update_doc["must_change_password"] is False


@pytest.mark.asyncio
async def test_accept_expired_invite_raises():
    from app.modules.business import ca_access

    invite = _make_invite("pending", expired=True)
    mock_inv_col = AsyncMock()
    mock_inv_col.find_one = AsyncMock(return_value=invite)
    mock_inv_col.create_index = AsyncMock()

    with patch("app.modules.business.ca_access.get_collection", return_value=mock_inv_col):
        with pytest.raises(ValueError, match="expired"):
            await ca_access.accept_ca_invite(token="tok123", password="Secret123!")


@pytest.mark.asyncio
async def test_accept_accepted_invite_raises_single_use_error():
    from app.modules.business import ca_access

    invite = _make_invite("accepted", expired=False)
    mock_inv_col = AsyncMock()
    mock_inv_col.find_one = AsyncMock(return_value=invite)
    mock_inv_col.create_index = AsyncMock()

    with patch("app.modules.business.ca_access.get_collection", return_value=mock_inv_col):
        with pytest.raises(ValueError, match="already been accepted"):
            await ca_access.accept_ca_invite(token="tok123", password="Secret123!")


@pytest.mark.asyncio
async def test_revoke_sets_inactive():
    from app.modules.business import ca_access

    mock_users = AsyncMock()
    revoke_result = MagicMock()
    revoke_result.matched_count = 1
    mock_users.update_one = AsyncMock(return_value=revoke_result)

    mock_inv_col = AsyncMock()
    mock_inv_col.update_one = AsyncMock()

    def _col(name):
        if name == "business_ca_invitations":
            return mock_inv_col
        return mock_users

    with patch("app.modules.business.ca_access.get_collection", side_effect=_col):
        await ca_access.revoke_ca_access(tenant_id="t1", user_id="u1")

    mock_users.update_one.assert_awaited_once()
    call_kwargs = mock_users.update_one.call_args
    assert call_kwargs[0][1]["$set"]["is_active"] is False
