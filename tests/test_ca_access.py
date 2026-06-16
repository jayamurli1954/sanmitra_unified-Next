"""CA Access — invite flow, accept, revoke, list. Uses fake Mongo via mongomock."""
from __future__ import annotations

import pytest
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

@pytest.mark.asyncio
async def test_invite_creates_record_and_sends_email():
    from app.modules.business import ca_access

    mock_col = AsyncMock()
    mock_col.find_one = AsyncMock(return_value=None)
    mock_col.insert_one = AsyncMock()
    mock_col.create_index = AsyncMock()

    with patch("app.modules.business.ca_access.get_collection", return_value=mock_col), \
         patch("app.modules.business.ca_access._send_invite_email", new_callable=AsyncMock) as mock_email:
        result = await ca_access.invite_ca(
            tenant_id="t1", app_key="mitrabooks",
            email="CA@Example.com", full_name="CA Ravi", invited_by="admin1",
        )

    assert result["email"] == "ca@example.com"
    assert result["status"] == "pending"
    assert "token" in result
    mock_email.assert_awaited_once()
    assert mock_email.call_args.kwargs["email"] == "ca@example.com"


@pytest.mark.asyncio
async def test_duplicate_pending_invite_raises():
    from app.modules.business import ca_access

    mock_col = AsyncMock()
    mock_col.find_one = AsyncMock(return_value=_make_invite("pending"))
    mock_col.create_index = AsyncMock()

    with patch("app.modules.business.ca_access.get_collection", return_value=mock_col):
        with pytest.raises(ValueError, match="pending invite already exists"):
            await ca_access.invite_ca(
                tenant_id="t1", app_key="mitrabooks",
                email="ca@example.com", full_name="CA Ravi", invited_by="admin1",
            )


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
    assert result["email"] == "ca@example.com"
    mock_users_col.insert_one.assert_awaited_once()
    inserted = mock_users_col.insert_one.call_args[0][0]
    assert inserted["role"] == "ca_viewer"
    assert inserted["is_active"] is True


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
