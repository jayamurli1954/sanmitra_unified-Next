"""MitraBooks MCP server: tokens, tool catalogue, protocol handling, auth forwarding."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import app.core.auth.dependencies as auth_deps
import app.core.modules.dependencies as module_deps
from app.core.auth.security import decode_token
from app.main import app
from app.modules.mcp import server as mcp_server
from app.modules.mcp import tokens as token_service
from app.modules.mcp.tools import TOOLS, TOOLS_BY_NAME, ToolArgumentError, build_request

MCP_URL = "/api/v1/mcp"


# --------------------------------------------------------------------------- fakes


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key, direction):
        self._docs.sort(key=lambda d: d.get(key), reverse=direction < 0)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        async def gen():
            for doc in self._docs:
                yield doc

        return gen()


def _matches(doc: dict, query: dict) -> bool:
    for key, cond in query.items():
        value = doc.get(key)
        if isinstance(cond, dict):
            if "$gt" in cond and not (value is not None and value > cond["$gt"]):
                return False
        elif value != cond:
            return False
    return True


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def create_index(self, *args, **kwargs):
        return "ok"

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query, projection=None):
        return next((dict(d) for d in self.docs if _matches(d, query)), None)

    async def update_one(self, query, update):
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                return

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _matches(d, query))

    def find(self, query):
        return _Cursor([dict(d) for d in self.docs if _matches(d, query)])


USER = {
    "user_id": "user-1",
    "email": "owner@example.com",
    "role": "tenant_admin",
    "tenant_id": "tenant-a",
    "app_key": "mitrabooks",
    "is_active": True,
}
SESSION = {"sub": "user-1", "tenant_id": "tenant-a", "app_key": "mitrabooks", "role": "tenant_admin"}


@pytest.fixture()
def stores(monkeypatch):
    collections = {
        token_service.MCP_TOKENS_COLLECTION: FakeCollection(),
        token_service.USERS_COLLECTION: FakeCollection([dict(USER)]),
    }
    monkeypatch.setattr(token_service, "get_collection", lambda name: collections[name])
    monkeypatch.setattr(token_service, "_indexes_ready", False)
    return collections


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------- tokens


def test_token_roundtrip_mints_user_scoped_access_token(stores):
    plain, meta = _run(token_service.create_token(current_user=SESSION, name="Claude", expires_in_days=90))
    assert plain.startswith("mbk_") and meta["prefix"] == plain[:10]
    stored = stores[token_service.MCP_TOKENS_COLLECTION].docs[0]
    assert plain not in str(stored) and stored["token_hash"] == token_service.hash_token(plain)

    access, _doc = _run(token_service.exchange_token(plain))
    claims = decode_token(access)
    assert claims["sub"] == "user-1"
    assert claims["tenant_id"] == "tenant-a"
    assert claims["app_key"] == "mitrabooks"
    assert claims["via"] == "mcp"
    assert claims["type"] == "access"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda tok, user: tok.update(revoked_at=datetime.now(timezone.utc)),
        lambda tok, user: tok.update(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
        lambda tok, user: user.update(is_active=False),
        lambda tok, user: user.update(tenant_id="tenant-b"),
        lambda tok, user: user.update(must_change_password=True),
        lambda tok, user: tok.update(scopes=[]),
    ],
    ids=["revoked", "expired", "user-inactive", "user-moved-tenant", "must-change-password", "no-read-scope"],
)
def test_token_rejected_when_no_longer_valid(stores, mutate):
    plain, _ = _run(token_service.create_token(current_user=SESSION, name="x", expires_in_days=30))
    mutate(stores[token_service.MCP_TOKENS_COLLECTION].docs[0], stores[token_service.USERS_COLLECTION].docs[0])
    with pytest.raises(HTTPException) as exc:
        _run(token_service.exchange_token(plain))
    assert exc.value.status_code == 401


def test_unknown_or_malformed_token_rejected(stores):
    for value in ("", "not-a-token", "mbk_doesnotexist"):
        with pytest.raises(HTTPException) as exc:
            _run(token_service.exchange_token(value))
        assert exc.value.status_code == 401


def test_token_creation_rules(stores):
    with pytest.raises(HTTPException) as exc:
        _run(token_service.create_token(current_user={**SESSION, "app_key": "mandirmitra"}, name="x", expires_in_days=30))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        _run(token_service.create_token(current_user=SESSION, name="x", expires_in_days=7))
    assert exc.value.status_code == 422
    for i in range(token_service.MAX_ACTIVE_TOKENS_PER_USER):
        _run(token_service.create_token(current_user=SESSION, name=f"t{i}", expires_in_days=30))
    with pytest.raises(HTTPException) as exc:
        _run(token_service.create_token(current_user=SESSION, name="one-too-many", expires_in_days=30))
    assert exc.value.status_code == 409


def test_revoke_is_owner_scoped(stores):
    _plain, meta = _run(token_service.create_token(current_user=SESSION, name="x", expires_in_days=30))
    other = {**SESSION, "sub": "user-2"}
    with pytest.raises(HTTPException) as exc:
        _run(token_service.revoke_token(current_user=other, token_id=meta["token_id"]))
    assert exc.value.status_code == 404
    revoked = _run(token_service.revoke_token(current_user=SESSION, token_id=meta["token_id"]))
    assert revoked["revoked_at"] is not None
    listed = _run(token_service.list_tokens(current_user=SESSION))
    assert "token_hash" not in listed[0]


# --------------------------------------------------------------------------- tool catalogue


def test_every_tool_targets_an_existing_get_route():
    get_routes = {r.path for r in app.routes if isinstance(r, APIRoute) and "GET" in r.methods}
    for tool in TOOLS:
        assert tool.path in get_routes, tool.name
        descriptor = tool.descriptor()
        assert descriptor["annotations"]["readOnlyHint"] is True
        assert descriptor["inputSchema"]["additionalProperties"] is False


def test_build_request_rejects_unsafe_arguments():
    ledger = TOOLS_BY_NAME["get_account_ledger"]
    statement = TOOLS_BY_NAME["get_party_statement"]
    with pytest.raises(ToolArgumentError):
        build_request(ledger, {})
    with pytest.raises(ToolArgumentError):
        build_request(ledger, {"account_id": "1/../../users"})
    with pytest.raises(ToolArgumentError):
        build_request(ledger, {"account_id": True})
    with pytest.raises(ToolArgumentError):
        build_request(statement, {"party_id": "../parties"})
    with pytest.raises(ToolArgumentError):
        build_request(TOOLS_BY_NAME["get_trial_balance"], {"as_of": "2026-03-31", "tenant_id": "other"})

    path, query = build_request(ledger, {"account_id": 42})
    assert path == "/api/v1/accounting/ledger/42" and query == {}
    path, query = build_request(TOOLS_BY_NAME["get_financial_health"], {"as_of": "2026-03-31"})
    assert query == {"as_of": "2026-03-31", "narrate": "false"}


# --------------------------------------------------------------------------- HTTP / protocol


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def authed(monkeypatch):
    """Skip the token store: any 'mbk_' token maps to a real minted access token."""
    from app.core.auth.security import create_access_token

    async def fake_exchange(plain):
        if plain != "mbk_valid":
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return create_access_token({**SESSION, "via": "mcp"}), {"token_id": "t1"}

    monkeypatch.setattr(token_service, "exchange_token", fake_exchange)
    return {"Authorization": "Bearer mbk_valid"}


def _rpc(method, params=None, msg_id=1):
    body = {"jsonrpc": "2.0", "method": method, "id": msg_id}
    if params is not None:
        body["params"] = params
    return body


def test_mcp_requires_bearer_token(client, authed):
    r = client.post(MCP_URL, json=_rpc("tools/list"))
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Bearer")
    r = client.post(MCP_URL, json=_rpc("tools/list"), headers={"Authorization": "Bearer mbk_wrong"})
    assert r.status_code == 401


def test_initialize_list_and_notifications(client, authed):
    r = client.post(MCP_URL, json=_rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}), headers=authed)
    result = r.json()["result"]
    assert result["protocolVersion"] == "2025-03-26"
    assert result["serverInfo"]["name"] == "mitrabooks"
    assert "tools" in result["capabilities"]

    r = client.post(MCP_URL, json=_rpc("initialize", {"protocolVersion": "1999-01-01"}), headers=authed)
    assert r.json()["result"]["protocolVersion"] == mcp_server.LATEST_PROTOCOL_VERSION

    r = client.post(MCP_URL, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=authed)
    assert r.status_code == 202

    r = client.post(MCP_URL, json=_rpc("tools/list"), headers=authed)
    names = {t["name"] for t in r.json()["result"]["tools"]}
    assert names == set(TOOLS_BY_NAME)

    r = client.post(MCP_URL, json=_rpc("nope/nothing"), headers=authed)
    assert r.json()["error"]["code"] == mcp_server.METHOD_NOT_FOUND

    r = client.post(MCP_URL, content=b"{not json", headers={**authed, "Content-Type": "application/json"})
    assert r.json()["error"]["code"] == mcp_server.PARSE_ERROR

    assert client.get(MCP_URL, headers=authed).status_code == 405


def test_tool_call_forwards_as_the_token_user(client, authed, monkeypatch):
    seen = {}

    async def fake_get(self, path, query, entity_id):
        seen.update(path=path, query=query, entity=entity_id, claims=decode_token(self._access_token))
        return httpx.Response(200, json={"total_debit": "100.00", "balanced": True})

    monkeypatch.setattr(mcp_server.McpCaller, "get", fake_get)
    r = client.post(
        MCP_URL,
        json=_rpc("tools/call", {"name": "get_trial_balance", "arguments": {"as_of": "2026-03-31", "accounting_entity_id": "branch-2"}}),
        headers=authed,
    )
    result = r.json()["result"]
    assert result["isError"] is False
    assert '"balanced": true' in result["content"][0]["text"]
    assert seen["path"] == "/api/v1/accounting/reports/trial-balance"
    # Business routes read the entity from the query, accounting routes from the header.
    assert seen["query"] == {"as_of": "2026-03-31", "accounting_entity_id": "branch-2"}
    assert seen["entity"] == "branch-2"
    assert seen["claims"]["tenant_id"] == "tenant-a" and seen["claims"]["via"] == "mcp"

    r = client.post(MCP_URL, json=_rpc("tools/call", {"name": "delete_everything", "arguments": {}}), headers=authed)
    assert r.json()["error"]["code"] == mcp_server.INVALID_PARAMS


def test_tool_call_end_to_end_runs_route_auth_and_validation(client, authed, monkeypatch):
    """No mocks between MCP and the route: the forwarded token passes get_current_user
    and the route's own validation error comes back as a tool error."""

    async def active(*_args, **_kwargs):
        return None

    async def fake_get_tenant(tenant_id):
        return {"tenant_id": tenant_id, "status": "active", "organization_type": "BUSINESS", "enabled_modules": ["business"]}

    monkeypatch.setattr(auth_deps, "ensure_tenant_is_active", active)
    monkeypatch.setattr(auth_deps, "ensure_user_is_active", active)
    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)

    r = client.post(MCP_URL, json=_rpc("tools/call", {"name": "get_gstr1", "arguments": {"period": "2026-13"}}), headers=authed)
    result = r.json()["result"]
    assert result["isError"] is True
    assert result["content"][0]["text"].startswith("Invalid arguments")


def test_token_management_blocks_mcp_sessions(client):
    app.dependency_overrides[auth_deps.get_current_user] = lambda: {**SESSION, "via": "mcp"}
    try:
        assert client.get(f"{MCP_URL}/tokens").status_code == 403
        assert client.post(f"{MCP_URL}/tokens", json={"name": "x"}).status_code == 403
    finally:
        app.dependency_overrides.pop(auth_deps.get_current_user, None)
