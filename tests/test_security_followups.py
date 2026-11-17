"""Audit V1 follow-ups: verify-pass roles, rate-limit keys, GruhaMitra users on
core_users, and mailbox-confirmed email changes."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException, Request

from app.core.auth.security import hash_password

# --------------------------------------------------------------------------- fakes


def _matches(doc: dict, query: dict) -> bool:
    for key, want in query.items():
        have = doc.get(key)
        if isinstance(want, dict) and "$ne" in want:
            if have == want["$ne"]:
                return False
        elif have != want:
            return False
    return True


class _Result:
    def __init__(self, matched: int):
        self.matched_count = matched
        self.modified_count = matched


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *_args):
        return self

    async def to_list(self, length):
        return self.docs[:length]


class _Collection:
    def __init__(self, docs=None):
        self.docs = [copy.deepcopy(d) for d in (docs or [])]

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if _matches(doc, query):
                return doc
        return None

    def find(self, query, projection=None):
        rows = [d for d in self.docs if _matches(d, query)]
        if projection:
            hidden = {k for k, v in projection.items() if not v}
            rows = [{k: v for k, v in d.items() if k not in hidden} for d in rows]
        return _Cursor(rows)

    async def update_one(self, query, update, upsert=False):
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                for key in update.get("$unset", {}):
                    doc.pop(key, None)
                return _Result(1)
        return _Result(0)

    async def update_many(self, query, update):
        count = 0
        for doc in self.docs:
            if _matches(doc, query):
                doc.update(update.get("$set", {}))
                count += 1
        return _Result(count)

    async def insert_one(self, doc):
        self.docs.append(copy.deepcopy(doc))


def _request(path="/", headers=None):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "path": path, "headers": raw, "client": ("10.0.0.9", 1), "scheme": "https", "server": ("api.test", 443)})


# ------------------------------------------------------------------ verify-pass


@pytest.mark.asyncio
async def test_resident_cannot_verify_guest_passes(monkeypatch):
    from app.modules.housing_compat import router as housing_router

    def tenant(**_kwargs):
        class Ctx:
            tenant_id = "society-1"
            app_key = "gruhamitra"

        return Ctx()

    monkeypatch.setattr(housing_router, "resolve_gruha_tenant", tenant)
    with pytest.raises(HTTPException) as exc:
        await housing_router.visitors_verify_pass(
            request=_request("/visitors/verify-pass"),
            payload={"code": "123456"},
            current_user={"sub": "r-1", "role": "resident", "tenant_id": "society-1"},
            x_tenant_id=None,
            x_app_key=None,
        )
    assert exc.value.status_code == 403


# ------------------------------------------------------------------ rate-limit key


def test_rate_limit_key_uses_proxy_appended_address(monkeypatch):
    from app.core.rate_limiting import client_rate_limit_key, rate_limit_storage_uri

    # A client cannot pick its own bucket by sending a fake leading X-Forwarded-For entry.
    spoofed = _request(headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"})
    assert client_rate_limit_key(spoofed) == "203.0.113.7"
    monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXY_HOPS", "2")
    assert client_rate_limit_key(spoofed) == "1.2.3.4"
    assert client_rate_limit_key(_request()) == "10.0.0.9"

    monkeypatch.delenv("RATE_LIMIT_STORAGE_URI", raising=False)
    assert rate_limit_storage_uri() == "memory://"
    monkeypatch.setenv("RATE_LIMIT_STORAGE_URI", "redis://cache:6379/0")
    assert rate_limit_storage_uri() == "redis://cache:6379/0"


# ------------------------------------------------------- GruhaMitra users on core_users


def _society_users():
    return _Collection(
        [
            {"user_id": "adm", "tenant_id": "s-1", "app_key": "gruhamitra", "role": "tenant_admin", "full_name": "Asha", "email": "asha@s1", "hashed_password": "x"},
            {"user_id": "sec", "tenant_id": "s-1", "app_key": "gruhamitra", "role": "secretary", "full_name": "Sunil", "email": "sunil@s1"},
            {"user_id": "res", "tenant_id": "s-1", "app_key": "gruhamitra", "role": "resident", "full_name": "Ravi", "email": "ravi@s1"},
            {"user_id": "boss", "tenant_id": "s-1", "app_key": "gruhamitra", "role": "super_admin", "full_name": "Ops", "email": "ops@x"},
            {"user_id": "other", "tenant_id": "s-2", "app_key": "gruhamitra", "role": "resident", "full_name": "Other", "email": "o@s2"},
        ]
    )


@pytest.fixture
def gruha(monkeypatch):
    from app.api import gruhamitra_compat_router as gruha_router

    users = _society_users()
    monkeypatch.setattr(gruha_router, "get_collection", lambda name: users if name == "core_users" else _Collection())
    return gruha_router, users


ADMIN = {"sub": "adm", "role": "tenant_admin", "tenant_id": "s-1", "app_key": "gruhamitra"}
SECRETARY = {"sub": "sec", "role": "secretary", "tenant_id": "s-1", "app_key": "gruhamitra"}


@pytest.mark.asyncio
async def test_user_list_reads_core_users_for_own_society_without_secrets(gruha):
    gruha_router, _ = gruha
    rows = await gruha_router.users_list_compat_endpoint(current_user=ADMIN)
    assert {r["id"] for r in rows} == {"adm", "sec", "res", "boss"}
    assert all("hashed_password" not in r for r in rows)


@pytest.mark.asyncio
async def test_role_change_writes_core_users(gruha):
    gruha_router, users = gruha
    out = await gruha_router.user_role_update_compat_endpoint(user_id="res", payload={"role": "Treasurer"}, current_user=ADMIN)
    assert out["role"] == "treasurer"
    assert (await users.find_one({"user_id": "res"}))["role"] == "treasurer"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actor", "target", "role", "status"),
    [
        (ADMIN, "res", "super_admin", 422),
        (ADMIN, "res", "wizard", 422),
        (SECRETARY, "res", "tenant_admin", 403),
        (SECRETARY, "res", "admin", 403),
        (ADMIN, "adm", "resident", 403),
        (ADMIN, "boss", "resident", 403),
        (ADMIN, "other", "resident", 404),
        ({"sub": "res", "role": "resident", "tenant_id": "s-1", "app_key": "gruhamitra"}, "sec", "resident", 403),
    ],
    ids=["super-admin", "unknown-role", "secretary-grants-tenant-admin", "secretary-grants-admin", "self", "platform-admin", "other-society", "resident-actor"],
)
async def test_role_change_guards(gruha, actor, target, role, status):
    gruha_router, users = gruha
    before = copy.deepcopy(users.docs)
    with pytest.raises(HTTPException) as exc:
        await gruha_router.user_role_update_compat_endpoint(user_id=target, payload={"role": role}, current_user=actor)
    assert exc.value.status_code == status
    assert users.docs == before


@pytest.mark.asyncio
async def test_secretary_can_assign_non_admin_roles(gruha):
    gruha_router, _ = gruha
    out = await gruha_router.user_role_update_compat_endpoint(user_id="res", payload={"role": "auditor"}, current_user=SECRETARY)
    assert out["role"] == "auditor"


@pytest.mark.asyncio
async def test_profile_update_writes_own_core_users_record(gruha):
    gruha_router, users = gruha
    out = await gruha_router.update_auth_me_compat_endpoint(
        payload={"name": "Ravi Kumar", "mobile": "9876500000", "flat_number": "B-202", "role": "tenant_admin"},
        current_user={"sub": "res", "role": "resident", "tenant_id": "s-1", "app_key": "gruhamitra"},
    )
    doc = await users.find_one({"user_id": "res"})
    assert doc["full_name"] == "Ravi Kumar" and doc["mobile"] == "9876500000" and doc["flat_number"] == "B-202"
    assert doc["role"] == "resident"  # role is not editable here
    assert out["name"] == "Ravi Kumar"


# ------------------------------------------------------------ email change by mailbox


@pytest.fixture
def mail(monkeypatch):
    from app.core.auth import router as auth_router
    from app.core.users import email_change
    from app.core.users import router as users_router

    users = _Collection(
        [
            {"user_id": "u-1", "email": "old@x.in", "auth_provider": "password", "hashed_password": hash_password("Right-Pass-123!"), "full_name": "Old Name", "role": "operator", "provider_subject": "password:old@x.in"},
            {"user_id": "u-2", "email": "taken@x.in", "auth_provider": "password", "hashed_password": "x", "full_name": "Other"},
            {"user_id": "g-1", "email": "g@x.in", "auth_provider": "google", "full_name": "G"},
        ]
    )
    actions = _Collection()
    refresh = _Collection([{"user_id": "u-1", "jti": "a", "revoked": False}, {"user_id": "u-2", "jti": "b", "revoked": False}])
    sent: list[dict] = []

    def collection(name):
        return {"core_users": users, "core_auth_refresh_tokens": refresh}.get(name, actions)

    async def fake_send(**kwargs):
        sent.append(kwargs)
        return True, None

    tokens: list[str] = []

    async def fake_create(*, action, email, ttl_minutes, meta=None):
        token = f"tok-{len(tokens)}"
        tokens.append(token)
        actions.docs.append({"_id": token, "action": action, "token": token, "email": email, "meta": meta, "consumed": False,
                             "expires_at": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)})
        return token

    async def fake_load(*, action, token):
        doc = next((d for d in actions.docs if d["token"] == token and d["action"] == action and not d["consumed"]), None)
        if doc is None:
            raise HTTPException(status_code=400, detail="Invalid or already-used link")
        return doc

    async def fake_consume(doc):
        doc["consumed"] = True

    for mod in (users_router, email_change):
        monkeypatch.setattr(mod, "get_collection", collection)
    monkeypatch.setattr(auth_router, "_send_auth_email", fake_send)
    monkeypatch.setattr(auth_router, "_create_email_action_token", fake_create)
    monkeypatch.setattr(auth_router, "_load_valid_email_action", fake_load)
    monkeypatch.setattr(auth_router, "_consume_email_action", fake_consume)
    return users_router, email_change, users, refresh, sent, tokens


ME = {"sub": "u-1", "role": "operator"}


@pytest.mark.asyncio
async def test_email_change_needs_password_and_is_pending_until_confirmed(mail):
    users_router, email_change, users, refresh, sent, tokens = mail
    req = _request("/api/v1/users/u-1", {"host": "api.test", "x-forwarded-proto": "https"})

    with pytest.raises(HTTPException) as exc:
        await users_router.update_user_profile(user_id="u-1", payload={"email": "new@x.in"}, request=req, current_user=ME)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        await users_router.update_user_profile(user_id="u-1", payload={"email": "new@x.in", "current_password": "nope"}, request=req, current_user=ME)
    assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:
        await users_router.update_user_profile(user_id="u-1", payload={"email": "taken@x.in", "current_password": "Right-Pass-123!"}, request=req, current_user=ME)
    assert exc.value.status_code == 409
    assert sent == []

    out = await users_router.update_user_profile(
        user_id="u-1", payload={"email": "New@X.in", "current_password": "Right-Pass-123!", "full_name": "New Name"}, request=req, current_user=ME
    )
    assert out["email"] == "old@x.in"  # unchanged until confirmed
    assert out["pending_email_change"] is True and out["pending_email"] == "new@x.in"
    assert out["full_name"] == "New Name"  # other fields still save immediately
    assert [m["to_email"] for m in sent] == ["new@x.in", "old@x.in"]
    assert "https://api.test/api/v1/users/email-change/confirm?token=tok-0" in sent[0]["body"]

    # Opening the link only shows a confirm button (mail scanners do not confirm).
    page = await email_change.confirm_page("tok-0")
    assert b"Confirm new email" in page.body
    assert (await users.find_one({"user_id": "u-1"}))["email"] == "old@x.in"

    done = await email_change.confirm_email_change("tok-0")
    assert b"Email changed" in done.body
    doc = await users.find_one({"user_id": "u-1"})
    assert doc["email"] == "new@x.in" and doc["provider_subject"] == "password:new@x.in"
    assert "pending_email" not in doc
    assert refresh.docs[0]["revoked"] is True and refresh.docs[1]["revoked"] is False

    again = await email_change.confirm_email_change("tok-0")
    assert b"Link not valid" in again.body


@pytest.mark.asyncio
async def test_unchanged_email_and_google_accounts(mail):
    users_router, _, _, _, sent, _ = mail
    req = _request("/api/v1/users/u-1")
    out = await users_router.update_user_profile(user_id="u-1", payload={"email": "OLD@x.in", "full_name": "Same"}, request=req, current_user=ME)
    assert out["pending_email_change"] is False and sent == []

    with pytest.raises(HTTPException) as exc:
        await users_router.update_user_profile(user_id="g-1", payload={"email": "new@g.in", "current_password": "x"}, request=req, current_user={"sub": "g-1"})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_superseded_request_cannot_be_confirmed(mail):
    users_router, email_change, users, _, _, _ = mail
    req = _request("/api/v1/users/u-1")
    for address in ("first@x.in", "second@x.in"):
        await users_router.update_user_profile(user_id="u-1", payload={"email": address, "current_password": "Right-Pass-123!"}, request=req, current_user=ME)
    stale = await email_change.confirm_email_change("tok-0")
    assert b"Link not valid" in stale.body
    assert (await users.find_one({"user_id": "u-1"}))["email"] == "old@x.in"
    await email_change.confirm_email_change("tok-1")
    assert (await users.find_one({"user_id": "u-1"}))["email"] == "second@x.in"


def test_unreachable_shared_storage_falls_back_instead_of_failing():
    from app.core.rate_limiting import limiter

    # A wrong RATE_LIMIT_STORAGE_URI or Redis outage must not turn logins into 500s.
    assert limiter._in_memory_fallback_enabled is True
    assert limiter._swallow_errors is True
