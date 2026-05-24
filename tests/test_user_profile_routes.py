import pytest
from fastapi import HTTPException

from app.core.users import router as users_router


async def fake_get_tenant(tenant_id):
    return {"tenant_id": tenant_id, "organization_type": "PLATFORM", "enabled_modules": ["audit"]}


class FakeUsersCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    @staticmethod
    def _matches(doc, query):
        for key, value in query.items():
            actual = doc.get(key)
            if isinstance(value, dict):
                if "$ne" in value and actual == value["$ne"]:
                    return False
                continue
            if actual != value:
                return False
        return True

    async def find_one(self, query):
        for doc in self.docs:
            if self._matches(doc, query):
                return dict(doc)
        return None

    async def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                return


@pytest.mark.asyncio
async def test_me_returns_db_backed_profile_identity(monkeypatch):
    users = FakeUsersCollection(
        [
            {
                "user_id": "platform-owner-1",
                "email": "contact@sanmitratech.in",
                "full_name": "Platform Owner",
                "role": "super_admin",
                "is_active": True,
            }
        ]
    )
    monkeypatch.setattr(users_router, "get_collection", lambda name: users)
    monkeypatch.setattr(users_router, "get_tenant", fake_get_tenant)

    response = await users_router.me(
        current_user={
            "sub": "platform-owner-1",
            "email": "contact@sanmitratech.in",
            "role": "super_admin",
            "tenant_id": "platform",
        }
    )

    assert response["id"] == "platform-owner-1"
    assert response["user_id"] == "platform-owner-1"
    assert response["is_superuser"] is True
    assert response["is_active"] is True
    assert response["full_name"] == "Platform Owner"


@pytest.mark.asyncio
async def test_update_user_profile_is_self_only_and_persists_allowed_fields(monkeypatch):
    users = FakeUsersCollection(
        [
            {
                "user_id": "platform-owner-1",
                "email": "contact@sanmitratech.in",
                "full_name": "Platform Owner",
                "phone": None,
                "role": "super_admin",
                "is_active": True,
            },
            {
                "user_id": "tenant-user-1",
                "email": "admin@sanmitra.local",
                "full_name": "Tenant Admin",
                "role": "tenant_admin",
            },
        ]
    )
    monkeypatch.setattr(users_router, "get_collection", lambda name: users)

    blocked = None
    try:
        await users_router.update_user_profile(
            "tenant-user-1",
            {"full_name": "Should Not Update"},
            current_user={"sub": "platform-owner-1", "role": "super_admin"},
        )
    except HTTPException as exc:
        blocked = exc
    assert blocked is not None
    assert blocked.status_code == 403

    response = await users_router.update_user_profile(
        "platform-owner-1",
        {
            "full_name": "Muralidhar Rao",
            "email": "contact@sanmitratech.in",
            "phone": "9444019106",
        },
        current_user={"sub": "platform-owner-1", "role": "super_admin"},
    )

    assert response["id"] == "platform-owner-1"
    assert response["full_name"] == "Muralidhar Rao"
    assert response["phone"] == "9444019106"
    assert response["is_superuser"] is True
