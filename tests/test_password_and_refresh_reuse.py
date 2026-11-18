"""SEC-04: one password policy everywhere. Refresh-token reuse ends the whole login."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.core.auth import service as auth_service
from app.core.auth.security import hash_password

STRONG = "Str0ng-Passw0rd!"
WEAK = "password1"  # 9 chars, no capital, no symbol


# ------------------------------------------------------------------ password policy


class _Users:
    def __init__(self, docs):
        self.docs = [copy.deepcopy(d) for d in docs]

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                return d
        return None

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if doc:
            doc.update(update.get("$set", {}))


@pytest.mark.asyncio
async def test_profile_password_change_uses_the_full_policy(monkeypatch):
    from app.core.users import router as users_router

    users = _Users([{"user_id": "u-1", "email": "a@b.in", "hashed_password": hash_password("Old-Passw0rd!"), "full_name": "A"}])
    monkeypatch.setattr(users_router, "get_collection", lambda name: users)
    with pytest.raises(HTTPException) as exc:
        await users_router.update_user_profile(
            user_id="u-1", payload={"password": WEAK, "current_password": "Old-Passw0rd!"}, request=None, current_user={"sub": "u-1"}
        )
    assert exc.value.status_code == 400
    await users_router.update_user_profile(
        user_id="u-1", payload={"password": STRONG, "current_password": "Old-Passw0rd!"}, request=None, current_user={"sub": "u-1"}
    )


@pytest.mark.asyncio
async def test_admin_created_users_need_a_policy_password(monkeypatch):
    from app.core.users import router as users_router
    from app.core.users.schemas import UserCreateRequest

    created = []

    async def fake_create_user(**kwargs):
        created.append(kwargs)
        raise ValueError("stop here")

    monkeypatch.setattr(users_router, "create_user", fake_create_user)
    admin = {"sub": "adm", "role": "tenant_admin", "tenant_id": "t-1"}
    weak = UserCreateRequest(email="n@b.in", password="abc123", full_name="New", tenant_id="t-1")
    with pytest.raises(HTTPException) as exc:
        await users_router.register_user(payload=weak, current_user=admin)
    assert exc.value.status_code == 400 and created == []

    ok = UserCreateRequest(email="n@b.in", password=STRONG, full_name="New", tenant_id="t-1")
    with pytest.raises(HTTPException) as exc:
        await users_router.register_user(payload=ok, current_user=admin)
    assert exc.value.status_code == 409 and len(created) == 1  # reached create_user


@pytest.mark.asyncio
async def test_resident_registration_needs_a_policy_password(monkeypatch):
    from app.modules.housing_compat import service as housing_service
    from app.modules.housing_compat.schemas import CompleteResidentRegistrationRequest

    def boom(_name):
        raise AssertionError("should be rejected before any database access")

    monkeypatch.setattr(housing_service, "get_collection", boom)
    with pytest.raises(HTTPException) as exc:
        await housing_service.complete_resident_registration(
            payload=CompleteResidentRegistrationRequest(email="r@b.in", password="abc123")
        )
    assert exc.value.status_code == 400


# ------------------------------------------------------------------ refresh reuse


class _Result:
    def __init__(self, n):
        self.modified_count = n
        self.matched_count = n


class _Tokens:
    def __init__(self):
        self.docs: list[dict] = []

    async def create_index(self, *args, **kwargs):
        return None

    def _match(self, doc, query):
        for key, want in query.items():
            if isinstance(want, dict) and "$in" in want:
                if doc.get(key) not in want["$in"]:
                    return False
            elif doc.get(key) != want:
                return False
        return True

    async def insert_one(self, doc):
        self.docs.append(dict(doc, _id=len(self.docs) + 1))

    async def find_one(self, query, projection=None):
        return next((d for d in self.docs if self._match(d, query)), None)

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc:
            doc.update(update.get("$set", {}))
        return _Result(1 if doc else 0)

    async def update_many(self, query, update):
        hits = [d for d in self.docs if self._match(d, query)]
        for d in hits:
            d.update(update.get("$set", {}))
        return _Result(len(hits))


@pytest.fixture
def tokens(monkeypatch):
    store = _Tokens()
    monkeypatch.setattr(auth_service, "_refresh_collection", lambda: store)

    async def tenant_ok(_tenant_id):
        return None

    monkeypatch.setattr(auth_service, "ensure_tenant_is_active", tenant_ok)
    monkeypatch.setattr(auth_service, "_REFRESH_INDEXES_READY", True)
    return store


USER = {"sub": "u-1", "email": "a@b.in", "role": "operator", "tenant_id": "t-1", "app_key": "mitrabooks", "accounting_entity_ids": ["primary"]}


async def _login(store):
    refresh = auth_service.create_refresh_token(dict(USER))
    await auth_service._store_refresh_token(refresh, auth_service.decode_token(refresh))
    return refresh


def _age_revocations(store, seconds):
    for d in store.docs:
        if isinstance(d.get("revoked_at"), datetime):
            d["revoked_at"] = d["revoked_at"] - timedelta(seconds=seconds)


@pytest.mark.asyncio
async def test_rotation_keeps_one_family(tokens):
    first = await _login(tokens)
    _, second = await auth_service.rotate_refresh_token(first, app_key="mitrabooks")
    _, third = await auth_service.rotate_refresh_token(second, app_key="mitrabooks")
    families = {d["family_id"] for d in tokens.docs}
    assert len(families) == 1 and len(tokens.docs) == 3
    assert [d["revoked"] for d in tokens.docs] == [True, True, False]
    assert third


@pytest.mark.asyncio
async def test_reusing_an_old_token_signs_out_the_whole_login(tokens):
    stolen = await _login(tokens)
    _, current = await auth_service.rotate_refresh_token(stolen, app_key="mitrabooks")
    other_login = await _login(tokens)  # a separate device must survive
    _age_revocations(tokens, auth_service.REFRESH_REUSE_GRACE_SECONDS + 5)

    with pytest.raises(HTTPException) as exc:
        await auth_service.rotate_refresh_token(stolen, app_key="mitrabooks")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException):
        await auth_service.rotate_refresh_token(current, app_key="mitrabooks")
    reused_family = tokens.docs[0]["family_id"]
    assert all(d["revoked"] for d in tokens.docs if d["family_id"] == reused_family)
    assert any(d.get("revoked_reason") == "refresh_token_reuse" for d in tokens.docs)
    # The independent login still refreshes.
    await auth_service.rotate_refresh_token(other_login, app_key="mitrabooks")


@pytest.mark.asyncio
async def test_parallel_refresh_within_grace_does_not_sign_out(tokens):
    first = await _login(tokens)
    _, current = await auth_service.rotate_refresh_token(first, app_key="mitrabooks")
    with pytest.raises(HTTPException):
        await auth_service.rotate_refresh_token(first, app_key="mitrabooks")  # second tab, same instant
    await auth_service.rotate_refresh_token(current, app_key="mitrabooks")


@pytest.mark.asyncio
async def test_logged_out_token_reuse_is_just_rejected(tokens):
    first = await _login(tokens)
    await auth_service.logout_refresh_token(first)
    _age_revocations(tokens, 300)
    with pytest.raises(HTTPException):
        await auth_service.rotate_refresh_token(first, app_key="mitrabooks")
    assert not any(d.get("revoked_reason") == "refresh_token_reuse" for d in tokens.docs)


@pytest.mark.asyncio
async def test_tokens_from_before_families_follow_the_rotation_chain(tokens):
    first = await _login(tokens)
    _, second = await auth_service.rotate_refresh_token(first, app_key="mitrabooks")
    for d in tokens.docs:  # simulate records written before family_id existed
        d.pop("family_id", None)
    _age_revocations(tokens, 300)
    with pytest.raises(HTTPException):
        await auth_service.rotate_refresh_token(first, app_key="mitrabooks")
    assert tokens.docs[1]["revoked"] is True
    assert tokens.docs[1]["revoked_reason"] == "refresh_token_reuse"
    assert datetime.now(timezone.utc)  # keep import used
