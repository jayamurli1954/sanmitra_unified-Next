import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.append(os.getcwd())

from app.core.auth.security import hash_password
from app.core.auth.security import verify_password
from app.core.tenants.context import resolve_app_key
from app.core.tenants.service import ensure_tenant_exists
from app.core.users.service import ensure_users_indexes
from app.db.mongo import close_mongo, get_collection, init_mongo


USERS_COLLECTION = "core_users"


def _required_env(name: str) -> str:
    value = str(os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _password_provider_subject(email: str) -> str:
    return f"password:{email.strip().lower()}"


async def create_platform_owner() -> None:
    email = _required_env("PLATFORM_OWNER_EMAIL").lower()
    password = _required_env("PLATFORM_OWNER_PASSWORD")
    if "@" not in email:
        raise RuntimeError("PLATFORM_OWNER_EMAIL must be a valid email address")
    if len(password) < 12:
        raise RuntimeError("PLATFORM_OWNER_PASSWORD must be at least 12 characters")

    tenant_id = str(os.getenv("PLATFORM_OWNER_TENANT_ID") or "platform").strip() or "platform"
    full_name = str(os.getenv("PLATFORM_OWNER_FULL_NAME") or "SanMitra Platform Owner").strip()
    app_key = resolve_app_key(os.getenv("PLATFORM_OWNER_APP_KEY") or "mitrabooks")
    reset_password = str(os.getenv("PLATFORM_OWNER_RESET_PASSWORD") or "").strip().lower() in {"1", "true", "yes"}

    await init_mongo()
    try:
        await ensure_tenant_exists(
            tenant_id,
            display_name="SanMitra Platform",
            organization_type="BUSINESS",
            app_keys=["gruhamitra", "mandirmitra", "mitrabooks", "legalmitra"],
            created_by="create_platform_owner",
        )
        await ensure_users_indexes()
        users = get_collection(USERS_COLLECTION)
        now = datetime.now(timezone.utc)
        existing = await users.find_one({"email": email})
        verify_only = str(os.getenv("PLATFORM_OWNER_VERIFY_ONLY") or "").strip().lower() in {"1", "true", "yes"}
        if verify_only:
            if not existing:
                raise RuntimeError(f"Platform owner account not found: {email}")
            if not existing.get("hashed_password"):
                raise RuntimeError(f"Platform owner account has no password hash: {email}")
            if not verify_password(password, str(existing["hashed_password"])):
                raise RuntimeError(f"Password verification failed for: {email}")
            print(f"Password verification passed for: {email}")
            return

        update_fields = {
            "full_name": full_name,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "role": "super_admin",
            "auth_provider": "password",
            "provider_subject": _password_provider_subject(email),
            "is_active": True,
            "updated_at": now,
        }

        if existing:
            if reset_password or not existing.get("hashed_password"):
                update_fields["hashed_password"] = hash_password(password)
            await users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            print(f"Platform owner account updated: {email}")
            return

        doc = {
            "user_id": str(uuid4()),
            "email": email,
            "hashed_password": hash_password(password),
            "created_at": now,
            **update_fields,
        }
        await users.insert_one(doc)
        print(f"Platform owner account created: {email}")
    finally:
        await close_mongo()


if __name__ == "__main__":
    asyncio.run(create_platform_owner())
