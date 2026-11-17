"""Quick security fixes from Security Deep-Dive Audit V1.

- Legacy /api/auth/login and /api/auth/local-login record login activity (SEC-03).
- A deactivated user's access token stops working (SEC-06).
- MandirMitra user list is admin-only; others see only themselves.
- The shadowed, unguarded MandirMitra PUT /users/{id} and GET /users/me are gone (SEC-02).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute

from app.core.auth import dependencies as auth_deps


class _Users:
    def __init__(self, docs):
        self.docs = list(docs)
        self.queries: list[dict] = []

    async def find_one(self, query, projection=None):
        self.queries.append(query)
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None


@pytest.fixture(autouse=True)
def _fresh_cache():
    auth_deps.clear_user_active_cache()
    yield
    auth_deps.clear_user_active_cache()


def _use_users(monkeypatch, docs):
    users = _Users(docs)
    monkeypatch.setattr(auth_deps, "get_collection", lambda name: users)
    return users


@pytest.mark.asyncio
async def test_deactivated_user_is_rejected(monkeypatch):
    _use_users(monkeypatch, [{"user_id": "u-1", "is_active": False}])
    with pytest.raises(HTTPException) as exc:
        await auth_deps.ensure_user_is_active("u-1")
    assert exc.value.status_code == 401
    assert "inactive" in exc.value.detail


@pytest.mark.asyncio
async def test_active_unknown_and_blank_users_pass(monkeypatch):
    _use_users(monkeypatch, [{"user_id": "u-1", "is_active": True}, {"user_id": "u-2"}])
    await auth_deps.ensure_user_is_active("u-1")
    await auth_deps.ensure_user_is_active("u-2")  # no flag means active
    await auth_deps.ensure_user_is_active("service-identity")  # no record
    await auth_deps.ensure_user_is_active(None)


@pytest.mark.asyncio
async def test_status_is_cached_briefly_then_rechecked(monkeypatch):
    users = _use_users(monkeypatch, [{"user_id": "u-1", "is_active": True}])
    await auth_deps.ensure_user_is_active("u-1")
    await auth_deps.ensure_user_is_active("u-1")
    assert len(users.queries) == 1

    users.docs[0]["is_active"] = False
    monkeypatch.setattr(auth_deps, "_USER_ACTIVE_CACHE_TTL_SECONDS", -1.0)
    with pytest.raises(HTTPException):
        await auth_deps.ensure_user_is_active("u-1")


@pytest.mark.asyncio
async def test_missing_mongo_does_not_block(monkeypatch):
    def unavailable(name):
        raise RuntimeError("Mongo not configured")

    monkeypatch.setattr(auth_deps, "get_collection", unavailable)
    await auth_deps.ensure_user_is_active("u-1")


@pytest.mark.asyncio
async def test_get_current_user_enforces_active_status(monkeypatch):
    from fastapi.security import HTTPAuthorizationCredentials

    _use_users(monkeypatch, [{"user_id": "u-1", "is_active": False}])

    async def tenant_ok(_tenant_id):
        return None

    monkeypatch.setattr(auth_deps, "ensure_tenant_is_active", tenant_ok)
    monkeypatch.setattr(
        auth_deps,
        "decode_token",
        lambda token: {"sub": "u-1", "role": "operator", "tenant_id": "t-1", "app_key": "mandirmitra", "type": "access"},
    )
    request = Request({"type": "http", "path": "/", "headers": [], "client": ("127.0.0.1", 1)})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(HTTPException) as exc:
        await auth_deps.get_current_user(request=request, credentials=creds, x_tenant_id=None, x_app_key=None)
    assert exc.value.status_code == 401


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def limit(self, _n):
        return self

    async def to_list(self, length):
        return self.docs[:length]


class _UserList:
    def __init__(self, docs):
        self.docs = docs
        self.last_query: dict | None = None

    def find(self, query):
        self.last_query = query
        return _Cursor([d for d in self.docs if all(d.get(k) == v for k, v in query.items())])


def _tenant_users():
    return _UserList(
        [
            {"user_id": "admin-1", "tenant_id": "t-1", "is_active": True, "email": "admin@t1", "role": "tenant_admin"},
            {"user_id": "op-1", "tenant_id": "t-1", "is_active": True, "email": "op@t1", "role": "operator"},
            {"user_id": "x-1", "tenant_id": "t-2", "is_active": True, "email": "x@t2", "role": "operator"},
        ]
    )


@pytest.mark.asyncio
async def test_mandir_user_list_is_admin_only(monkeypatch):
    from app.modules.mandir_compat import router as mandir_router
    from app.modules.mandir_compat.routes.users import mandir_users

    users = _tenant_users()
    monkeypatch.setattr(mandir_router, "get_collection", lambda name: users)

    admin = await mandir_users(_current_user={"sub": "admin-1", "role": "tenant_admin", "tenant_id": "t-1"}, x_tenant_id=None)
    assert {u["user_id"] for u in admin} == {"admin-1", "op-1"}

    operator = await mandir_users(_current_user={"sub": "op-1", "role": "operator", "tenant_id": "t-1"}, x_tenant_id=None)
    assert [u["user_id"] for u in operator] == ["op-1"]
    assert users.last_query == {"tenant_id": "t-1", "is_active": True, "user_id": "op-1"}


def test_only_the_guarded_core_user_routes_are_mounted():
    import app.main

    def handlers(path, method):
        return [
            r.endpoint.__module__
            for r in app.main.app.routes
            if isinstance(r, APIRoute) and r.path == path and method in r.methods
        ]

    assert handlers("/api/v1/users/{user_id}", "PUT") == ["app.core.users.router"]
    assert handlers("/api/v1/users/me", "GET") == ["app.core.users.router"]


@pytest.mark.asyncio
@pytest.mark.parametrize("route_name", ["legacy_auth_login", "legacy_auth_local_login"])
async def test_legacy_logins_record_login_activity(monkeypatch, route_name):
    from app.api import legacy_alias_router as legacy
    from app.core.auth.schemas import LoginRequest

    calls = []

    async def fake_login_user(email, password, app_key):
        return "access-token", "refresh-token"

    async def fake_log(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(legacy, "login_user", fake_login_user)
    monkeypatch.setattr(legacy, "_log_login_activity", fake_log)
    request = Request({"type": "http", "path": "/api/auth/login", "headers": [], "client": ("127.0.0.1", 1)})
    handler = getattr(legacy, route_name)
    result = await handler.__wrapped__(
        request=request,
        payload=LoginRequest(email="a@b.co", password="secret-Password1!"),
        x_app_key=None,
    )
    assert result.access_token == "access-token"
    assert len(calls) == 1
    assert calls[0]["access_token"] == "access-token"
    assert calls[0]["login_method"].startswith("legacy_")
