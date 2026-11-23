"""Personal access tokens for MCP clients.

A token belongs to one user in one tenant, is read-only, and expires. Only its
SHA-256 hash is stored; the plain value is shown once, at creation. On each MCP
request the token is exchanged for a short-lived ordinary access token built from
the user's *current* record, so deactivating the user, the tenant, or the token
takes effect immediately.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.auth.security import create_access_token
from app.core.users.service import USERS_COLLECTION
from app.db.mongo import get_collection

MCP_TOKENS_COLLECTION = "core_mcp_access_tokens"
MCP_APP_KEY = "mitrabooks"
TOKEN_PREFIX = "mbk_"
ALLOWED_EXPIRY_DAYS = (30, 90, 180, 365)
DEFAULT_EXPIRY_DAYS = 90
MAX_ACTIVE_TOKENS_PER_USER = 10
READ_SCOPE = "read"
# Avoid a write on every tool call; last-used precision of a few minutes is enough.
_LAST_USED_WRITE_INTERVAL = timedelta(minutes=5)

_indexes_ready = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _collection():
    try:
        return get_collection(MCP_TOKENS_COLLECTION)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Token store is unavailable") from exc


async def _ensure_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    tokens = _collection()
    await tokens.create_index("token_hash", unique=True)
    await tokens.create_index([("user_id", 1), ("tenant_id", 1)])
    _indexes_ready = True


def public_view(doc: dict) -> dict:
    """Token metadata safe to return to its owner (never the hash)."""
    return {
        "token_id": doc.get("token_id"),
        "name": doc.get("name"),
        "prefix": doc.get("prefix"),
        "scopes": list(doc.get("scopes") or []),
        "created_at": doc.get("created_at"),
        "expires_at": doc.get("expires_at"),
        "last_used_at": doc.get("last_used_at"),
        "revoked_at": doc.get("revoked_at"),
    }


def _owner(current_user: dict) -> tuple[str, str]:
    user_id = str(current_user.get("sub") or "").strip()
    tenant_id = str(current_user.get("tenant_id") or "").strip()
    if not user_id or not tenant_id:
        raise HTTPException(status_code=403, detail="A tenant user is required to manage AI access tokens")
    if str(current_user.get("app_key") or "") != MCP_APP_KEY:
        raise HTTPException(status_code=403, detail="AI access tokens are available in MitraBooks only")
    return user_id, tenant_id


async def create_token(*, current_user: dict, name: str, expires_in_days: int) -> tuple[str, dict]:
    if expires_in_days not in ALLOWED_EXPIRY_DAYS:
        raise HTTPException(status_code=422, detail=f"expires_in_days must be one of {list(ALLOWED_EXPIRY_DAYS)}")
    clean_name = str(name or "").strip()
    if not clean_name or len(clean_name) > 80:
        raise HTTPException(status_code=422, detail="Token name must be 1-80 characters")
    user_id, tenant_id = _owner(current_user)

    await _ensure_indexes()
    tokens = _collection()
    now = _now()
    active = await tokens.count_documents(
        {"user_id": user_id, "tenant_id": tenant_id, "revoked_at": None, "expires_at": {"$gt": now}}
    )
    if active >= MAX_ACTIVE_TOKENS_PER_USER:
        raise HTTPException(status_code=409, detail="Too many active tokens; revoke one first")

    plain = TOKEN_PREFIX + secrets.token_urlsafe(32)
    doc = {
        "token_id": str(uuid4()),
        "token_hash": hash_token(plain),
        "prefix": plain[: len(TOKEN_PREFIX) + 6],
        "name": clean_name,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "app_key": MCP_APP_KEY,
        "scopes": [READ_SCOPE],
        "created_at": now,
        "expires_at": now + timedelta(days=expires_in_days),
        "last_used_at": None,
        "revoked_at": None,
    }
    await tokens.insert_one(dict(doc))
    return plain, public_view(doc)


async def list_tokens(*, current_user: dict) -> list[dict]:
    user_id, tenant_id = _owner(current_user)
    cursor = _collection().find({"user_id": user_id, "tenant_id": tenant_id}).sort("created_at", -1).limit(100)
    return [public_view(doc) async for doc in cursor]


async def revoke_token(*, current_user: dict, token_id: str) -> dict:
    user_id, tenant_id = _owner(current_user)
    tokens = _collection()
    query = {"token_id": str(token_id or ""), "user_id": user_id, "tenant_id": tenant_id}
    doc = await tokens.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Token not found")
    if doc.get("revoked_at") is None:
        doc["revoked_at"] = _now()
        await tokens.update_one(query, {"$set": {"revoked_at": doc["revoked_at"]}})
    return public_view(doc)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": 'Bearer realm="mitrabooks-mcp"'},
    )


async def exchange_token(plain: str) -> tuple[str, dict]:
    """Validate a personal access token and mint a short-lived access token for it.

    Returns ``(access_token, token_doc)``. Raises 401 for any invalid, expired,
    revoked or orphaned token without saying which, so tokens cannot be probed.
    """
    value = str(plain or "").strip()
    if not value.startswith(TOKEN_PREFIX):
        raise _unauthorized("Invalid or expired token")

    tokens = _collection()
    doc = await tokens.find_one({"token_hash": hash_token(value)})
    now = _now()
    expires_at = _aware(doc.get("expires_at")) if doc else None
    if not doc or doc.get("revoked_at") is not None or not expires_at or expires_at <= now:
        raise _unauthorized("Invalid or expired token")
    if READ_SCOPE not in (doc.get("scopes") or []):
        raise _unauthorized("Invalid or expired token")

    try:
        users = get_collection(USERS_COLLECTION)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="User store is unavailable") from exc
    user = await users.find_one({"user_id": doc.get("user_id")})
    if (
        not user
        or user.get("is_active", True) is False
        or str(user.get("tenant_id") or "") != str(doc.get("tenant_id") or "")
        or user.get("must_change_password")
    ):
        raise _unauthorized("Invalid or expired token")

    # Imported here: the auth service imports widely and this keeps module import cheap.
    from app.core.auth.service import _token_payload_from_user

    payload = await _token_payload_from_user(user, app_key=MCP_APP_KEY)
    payload["via"] = "mcp"
    payload["mcp_token_id"] = doc.get("token_id")
    access_token = create_access_token(payload)

    last_used = _aware(doc.get("last_used_at"))
    if last_used is None or now - last_used >= _LAST_USED_WRITE_INTERVAL:
        await tokens.update_one({"token_id": doc.get("token_id")}, {"$set": {"last_used_at": now}})
    return access_token, doc
