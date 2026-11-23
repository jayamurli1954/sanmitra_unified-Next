"""Complimentary (trial) plans: grant, auto-expiry, revoke, and platform-owner-only access."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.core.platform_owner.complimentary as comp
import app.core.platform_owner.router as platform_owner_router
from app.core.auth.dependencies import get_current_user
from app.core.auth.password_policy import validate_password_policy
from app.core.billing.usage import effective_subscription_tier
from app.main import app


# ── in-memory Mongo stand-in ───────────────────────────────────────────────
class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, key, direction):
        self._docs.sort(key=lambda d: (d.get(key) is None, d.get(key)), reverse=direction < 0)
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return list(self._docs)


def _matches(doc, query):
    return all(doc.get(k) == v for k, v in query.items())


class _Collection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query):
        return next((d for d in self.docs if _matches(d, query)), None)

    def find(self, query):
        return _Cursor([d for d in self.docs if _matches(d, query)])

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc is not None:
            doc.update(update.get("$set", {}))

    async def insert_one(self, doc):
        self.docs.append(dict(doc))


@pytest.fixture
def store(monkeypatch):
    collections = {"core_users": _Collection(), "core_billing_transactions": _Collection()}
    monkeypatch.setattr(comp, "get_collection", lambda name: collections[name])

    created_tenants = []

    async def fake_allocate(hint):
        return "adv-sharma"

    async def fake_ensure_tenant(tenant_id, **kwargs):
        created_tenants.append((tenant_id, kwargs))
        return {"tenant_id": tenant_id}

    async def fake_create_user(*, email, password, full_name, tenant_id, role, app_key):
        validate_password_policy(password)  # generated password must pass the real policy
        doc = {
            "user_id": f"u-{len(collections['core_users'].docs) + 1}",
            "email": email,
            "full_name": full_name,
            "tenant_id": tenant_id,
            "role": role,
            "app_key": app_key,
            "subscription_tier": "free",
        }
        collections["core_users"].docs.append(doc)
        return doc

    sent = []

    async def fake_send(**kwargs):
        sent.append(kwargs)
        return True, None

    monkeypatch.setattr(comp, "_allocate_tenant_id", fake_allocate)
    monkeypatch.setattr(comp, "ensure_tenant_exists", fake_ensure_tenant)
    monkeypatch.setattr(comp, "create_user", fake_create_user)
    monkeypatch.setattr(comp, "_send_onboarding_email", fake_send)
    return {"collections": collections, "tenants": created_tenants, "sent": sent}


# ── effective tier / expiry ────────────────────────────────────────────────
def test_expired_plan_is_treated_as_free():
    now = datetime(2027, 3, 1, tzinfo=timezone.utc)
    user = {"subscription_tier": "pro", "subscription_expires_at": now - timedelta(seconds=1)}
    assert effective_subscription_tier(user, now=now) == "free"


def test_active_plan_keeps_its_tier_and_handles_naive_and_iso_dates():
    now = datetime(2027, 3, 1, tzinfo=timezone.utc)
    assert effective_subscription_tier({"subscription_tier": "pro", "subscription_expires_at": datetime(2027, 4, 1)}, now=now) == "pro"
    assert effective_subscription_tier({"subscription_tier": "growth", "subscription_expires_at": "2027-04-01T00:00:00Z"}, now=now) == "growth"


def test_plan_without_expiry_is_unchanged():
    assert effective_subscription_tier({"subscription_tier": "pro"}) == "pro"
    assert effective_subscription_tier(None) == "free"


def test_generated_password_always_meets_policy():
    for _ in range(200):
        validate_password_policy(comp._generate_policy_password())


# ── grant / revoke ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_grant_creates_account_and_sets_expiring_pro_plan(store):
    result = await comp.grant_complimentary_plan(
        email="Advocate@Example.com",
        full_name="R. Sharma",
        organization_name="Sharma Chambers",
        app_key="legalmitra",
        tier="pro",
        days=90,
        note="feedback trial",
        granted_by="owner@sanmitratech.in",
    )
    assert result["account_created"] is True
    assert result["temporary_password"]
    assert result["email_sent"] is True

    user = store["collections"]["core_users"].docs[0]
    assert user["email"] == "advocate@example.com"
    assert user["role"] == "tenant_admin"
    assert user["subscription_tier"] == "pro"
    assert user["complimentary_plan"] is True
    assert user["must_change_password"] is True
    days_left = (user["subscription_expires_at"] - datetime.now(timezone.utc)).days
    assert 89 <= days_left <= 90
    assert effective_subscription_tier(user) == "pro"

    tenant_id, tenant_kwargs = store["tenants"][0]
    assert tenant_kwargs["app_keys"] == ["legalmitra"]
    assert tenant_kwargs["display_name"] == "Sharma Chambers"

    audit = store["collections"]["core_billing_transactions"].docs[0]
    assert audit["amount"] == 0 and audit["complimentary"] is True and audit["plan"] == "pro"

    email = store["sent"][0]
    assert result["temporary_password"] in email["body"]
    assert "legalmitra.sanmitratech.in" in email["body"]


@pytest.mark.asyncio
async def test_grant_to_existing_user_extends_plan_without_new_password(store):
    store["collections"]["core_users"].docs.append(
        {"user_id": "u-9", "email": "adv@example.com", "full_name": "Existing", "app_key": "legalmitra", "tenant_id": "t9", "subscription_tier": "free"}
    )
    result = await comp.grant_complimentary_plan(
        email="adv@example.com", full_name=None, organization_name=None, app_key="legalmitra",
        tier="pro", days=30, note=None, granted_by="owner", send_email=False,
    )
    assert result["account_created"] is False
    assert result["temporary_password"] is None
    assert store["tenants"] == []
    assert store["sent"] == []
    assert store["collections"]["core_users"].docs[0]["subscription_tier"] == "pro"


@pytest.mark.asyncio
async def test_grant_rejects_other_product_account_and_missing_name(store):
    store["collections"]["core_users"].docs.append(
        {"user_id": "u-1", "email": "books@example.com", "app_key": "mitrabooks", "subscription_tier": "free"}
    )
    with pytest.raises(ValueError, match="MitraBooks account"):
        await comp.grant_complimentary_plan(
            email="books@example.com", full_name="X", organization_name=None, app_key="legalmitra",
            tier="pro", days=30, note=None, granted_by="owner",
        )
    with pytest.raises(ValueError, match="Full name is required"):
        await comp.grant_complimentary_plan(
            email="new@example.com", full_name="", organization_name=None, app_key="legalmitra",
            tier="pro", days=30, note=None, granted_by="owner",
        )
    with pytest.raises(ValueError, match="Days must be between"):
        await comp.grant_complimentary_plan(
            email="new@example.com", full_name="New", organization_name=None, app_key="legalmitra",
            tier="pro", days=0, note=None, granted_by="owner",
        )


@pytest.mark.asyncio
async def test_revoke_drops_user_to_free_and_list_shows_status(store):
    await comp.grant_complimentary_plan(
        email="adv@example.com", full_name="Adv", organization_name=None, app_key="legalmitra",
        tier="pro", days=60, note=None, granted_by="owner", send_email=False,
    )
    listed = await comp.list_complimentary_plans()
    assert listed[0]["active"] is True and listed[0]["tier"] == "pro"

    await comp.revoke_complimentary_plan(email="adv@example.com", revoked_by="owner")
    user = store["collections"]["core_users"].docs[0]
    assert user["subscription_tier"] == "free"
    assert user["complimentary_plan"] is False
    assert await comp.list_complimentary_plans() == []


# ── API access control ─────────────────────────────────────────────────────
def test_non_super_admin_cannot_grant():
    app.dependency_overrides[get_current_user] = lambda: {"sub": "u1", "role": "tenant_admin"}
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/platform-owner/complimentary-plans",
            json={"email": "a@example.com", "full_name": "A", "days": 30},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_super_admin_grant_endpoint_returns_result(monkeypatch):
    captured = {}

    async def fake_grant(**kwargs):
        captured.update(kwargs)
        return {"email": kwargs["email"], "tier": kwargs["tier"], "days": kwargs["days"], "account_created": True}

    monkeypatch.setattr(platform_owner_router, "grant_complimentary_plan", fake_grant)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "owner", "email": "owner@sanmitratech.in", "role": "super_admin"}
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/platform-owner/complimentary-plans",
            json={"email": "adv@example.com", "full_name": "Adv", "days": 60},
        )
        assert response.status_code == 200, response.text
        assert response.json()["days"] == 60
        assert captured["app_key"] == "legalmitra" and captured["tier"] == "pro"
        assert captured["granted_by"] == "owner@sanmitratech.in"

        bad = client.post("/api/v1/platform-owner/complimentary-plans", json={"email": "adv@example.com", "days": 999})
        assert bad.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
