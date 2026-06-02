from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import app.core.users.service as users_service


class FakeUsersCollection:
    def __init__(self):
        self.docs = []

    async def create_index(self, *_args, **_kwargs):
        return None

    async def find_one(self, filters):
        for doc in self.docs:
            matched = True
            for key, value in filters.items():
                if doc.get(key) != value:
                    matched = False
                    break
            if matched:
                return doc
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc.get("_id"))

    async def update_one(self, filters, update):
        for doc in self.docs:
            matched = True
            for key, value in filters.items():
                if doc.get(key) != value:
                    matched = False
                    break
            if matched:
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)


def _settings(**kwargs):
    values = {
        "SUPER_ADMIN_BOOTSTRAP": True,
        "SUPER_ADMIN_EMAIL": "superadmin@sanmitra.local",
        "SUPER_ADMIN_PASSWORD": "superadmin123",
        "SUPER_ADMIN_FULL_NAME": "SanMitra Super Admin",
        "SUPER_ADMIN_TENANT_ID": "seed-tenant-1",
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_ensure_super_admin_user_creates_account(monkeypatch):
    fake_users = FakeUsersCollection()

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)
    monkeypatch.setattr(users_service, "get_settings", lambda: _settings())

    ensured = {}

    async def fake_ensure_tenant_exists(tenant_id: str, **_kwargs):
        ensured["tenant_id"] = tenant_id
        ensured.update(_kwargs)
        return {"tenant_id": tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    await users_service.ensure_super_admin_user()

    created = await fake_users.find_one({"email": "superadmin@sanmitra.local"})
    assert created is not None
    assert created["role"] == "super_admin"
    assert created["tenant_id"] == "seed-tenant-1"
    assert created["is_active"] is True
    assert ensured["tenant_id"] == "seed-tenant-1"
    assert ensured["organization_type"] == "TEMPLE"
    assert ensured["enabled_modules"] == ["temple", "accounting", "audit"]
    assert ensured["app_keys"] == ["mandirmitra"]


@pytest.mark.asyncio
async def test_ensure_super_admin_user_uses_platform_context_for_separate_tenant(monkeypatch):
    fake_users = FakeUsersCollection()

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)
    monkeypatch.setattr(users_service, "get_settings", lambda: _settings(SUPER_ADMIN_TENANT_ID="platform-admin"))

    ensured = {}

    async def fake_ensure_tenant_exists(tenant_id: str, **_kwargs):
        ensured["tenant_id"] = tenant_id
        ensured.update(_kwargs)
        return {"tenant_id": tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    await users_service.ensure_super_admin_user()

    created = await fake_users.find_one({"email": "superadmin@sanmitra.local"})
    assert created is not None
    assert created["role"] == "super_admin"
    assert created["tenant_id"] == "platform-admin"
    assert ensured["tenant_id"] == "platform-admin"
    assert ensured["organization_type"] == "BUSINESS"
    assert ensured["app_keys"] == ["gruhamitra", "mandirmitra", "mitrabooks", "legalmitra", "investmitra"]


@pytest.mark.asyncio
async def test_ensure_super_admin_user_promotes_existing_account(monkeypatch):
    fake_users = FakeUsersCollection()
    fake_users.docs.append(
        {
            "_id": "u-existing",
            "email": "superadmin@sanmitra.local",
            "full_name": "Existing User",
            "tenant_id": "seed-tenant-1",
            "role": "tenant_admin",
            "auth_provider": "password",
            "provider_subject": None,
            "hashed_password": "already-hashed",
            "is_active": False,
            "updated_at": datetime.now(timezone.utc),
        }
    )

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)
    monkeypatch.setattr(users_service, "get_settings", lambda: _settings())

    async def fake_ensure_tenant_exists(_tenant_id: str, **_kwargs):
        return {"tenant_id": _tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    await users_service.ensure_super_admin_user()

    updated = await fake_users.find_one({"email": "superadmin@sanmitra.local"})
    assert updated is not None
    assert updated["role"] == "super_admin"
    assert updated["is_active"] is True
    assert updated["hashed_password"] == "already-hashed"


@pytest.mark.asyncio
async def test_ensure_demo_mitrabooks_user_creates_business_tenant(monkeypatch):
    fake_users = FakeUsersCollection()

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)

    ensured = {}

    async def fake_ensure_tenant_exists(tenant_id: str, **_kwargs):
        ensured["tenant_id"] = tenant_id
        ensured.update(_kwargs)
        return {"tenant_id": tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    result = await users_service.ensure_demo_mitrabooks_user(
        email="businessadmin@sanmitra.local",
        password="businessadmin123",
    )

    assert result is not None
    assert result["email"] == "businessadmin@sanmitra.local"
    assert result["tenant_id"] == "demo-mitrabooks-business"
    assert result["app_key"] == "mitrabooks"
    assert result["role"] == "tenant_admin"
    assert ensured["organization_type"] == "BUSINESS"
    assert ensured["enabled_modules"] == ["business", "accounting", "gst", "inventory", "audit"]
    assert ensured["app_keys"] == ["mitrabooks"]
    assert ensured["subscription_plan"] == "pro"


@pytest.mark.asyncio
async def test_ensure_demo_mitrabooks_user_updates_existing_account(monkeypatch):
    fake_users = FakeUsersCollection()
    fake_users.docs.append(
        {
            "_id": "u-business",
            "user_id": "business-user",
            "email": "businessadmin@sanmitra.local",
            "tenant_id": "old-tenant",
            "role": "operator",
            "auth_provider": "password",
            "provider_subject": None,
            "hashed_password": "old-hash",
            "is_active": False,
        }
    )

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)

    async def fake_ensure_tenant_exists(_tenant_id: str, **_kwargs):
        return {"tenant_id": _tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    await users_service.ensure_demo_mitrabooks_user(
        email="businessadmin@sanmitra.local",
        password="businessadmin123",
    )

    updated = await fake_users.find_one({"email": "businessadmin@sanmitra.local"})
    assert updated["user_id"] == "business-user"
    assert updated["tenant_id"] == "demo-mitrabooks-business"
    assert updated["app_key"] == "mitrabooks"
    assert updated["role"] == "tenant_admin"
    assert updated["is_active"] is True
    assert updated["hashed_password"] != "old-hash"


@pytest.mark.asyncio
async def test_ensure_demo_mitrabooks_user_supports_mitrabooks_admin_alias(monkeypatch):
    fake_users = FakeUsersCollection()

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)

    ensured = {}

    async def fake_ensure_tenant_exists(tenant_id: str, **_kwargs):
        ensured["tenant_id"] = tenant_id
        ensured.update(_kwargs)
        return {"tenant_id": tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    result = await users_service.ensure_demo_mitrabooks_user(
        email="admin@mitrabooks.local",
        password="admin123",
        full_name="MitraBooks Admin",
        tenant_id="demo-mitrabooks-business",
    )

    assert result is not None
    assert result["email"] == "admin@mitrabooks.local"
    assert result["tenant_id"] == "demo-mitrabooks-business"
    assert result["app_key"] == "mitrabooks"
    assert result["role"] == "tenant_admin"
    assert ensured["organization_type"] == "BUSINESS"
    assert ensured["app_keys"] == ["mitrabooks"]


@pytest.mark.asyncio
async def test_demo_mitrabooks_alias_email_defaults_include_legacy_business_admin():
    from app.config import Settings

    settings = Settings()

    assert "business.admin@sanmitra.local" in settings.DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS
    assert "businessadmin@sanmitra.local" in settings.DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS


def test_mitrabooks_seed_script_can_expand_admin_aliases(monkeypatch):
    from types import SimpleNamespace

    from scripts.seed_mitrabooks_local_demo import _admin_emails

    settings = SimpleNamespace(
        DEMO_MITRABOOKS_ADMIN_EMAIL="admin@mitrabooks.local",
        DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS=[
            "business.admin@sanmitra.local",
            "businessadmin@sanmitra.local",
            "businessadmin@sanmitra.local",
        ],
    )

    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    emails = _admin_emails(
        SimpleNamespace(
            email="BUSINESSADMIN@sanmitra.local",
            all_admin_aliases=True,
        )
    )

    assert emails == [
        "businessadmin@sanmitra.local",
        "admin@mitrabooks.local",
        "business.admin@sanmitra.local",
    ]


@pytest.mark.asyncio
async def test_ensure_demo_gruhamitra_user_creates_housing_tenant(monkeypatch):
    fake_users = FakeUsersCollection()

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)

    ensured = {}

    async def fake_ensure_tenant_exists(tenant_id: str, **_kwargs):
        ensured["tenant_id"] = tenant_id
        ensured.update(_kwargs)
        return {"tenant_id": tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    result = await users_service.ensure_demo_gruhamitra_user(
        email="demo.admin@gruhamitra.sanmitratech.in",
        password="GruhaDemo@2026",
    )

    assert result is not None
    assert result["email"] == "demo.admin@gruhamitra.sanmitratech.in"
    assert result["tenant_id"] == "gruhamitra-demo-society"
    assert result["app_key"] == "gruhamitra"
    assert result["role"] == "tenant_admin"
    assert ensured["organization_type"] == "HOUSING"
    assert ensured["enabled_modules"] == ["housing", "accounting", "audit"]
    assert ensured["app_keys"] == ["gruhamitra"]
    assert ensured["subscription_plan"] == "growth"


@pytest.mark.asyncio
async def test_ensure_demo_gruhamitra_user_updates_existing_account(monkeypatch):
    fake_users = FakeUsersCollection()
    fake_users.docs.append(
        {
            "_id": "u-gruha",
            "user_id": "gruhamitra-user",
            "email": "demo.admin@gruhamitra.sanmitratech.in",
            "tenant_id": "old-tenant",
            "role": "operator",
            "auth_provider": "password",
            "provider_subject": None,
            "hashed_password": "old-hash",
            "is_active": False,
        }
    )

    monkeypatch.setattr(users_service, "get_collection", lambda _name: fake_users)

    async def fake_ensure_tenant_exists(_tenant_id: str, **_kwargs):
        return {"tenant_id": _tenant_id, "status": "active"}

    monkeypatch.setattr(users_service, "ensure_tenant_exists", fake_ensure_tenant_exists)

    await users_service.ensure_demo_gruhamitra_user(
        email="demo.admin@gruhamitra.sanmitratech.in",
        password="GruhaDemo@2026",
    )

    updated = await fake_users.find_one({"email": "demo.admin@gruhamitra.sanmitratech.in"})
    assert updated["user_id"] == "gruhamitra-user"
    assert updated["tenant_id"] == "gruhamitra-demo-society"
    assert updated["app_key"] == "gruhamitra"
    assert updated["role"] == "tenant_admin"
    assert updated["is_active"] is True
    assert updated["hashed_password"] != "old-hash"
