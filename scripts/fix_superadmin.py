import asyncio
import os
import sys
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.db.mongo import init_mongo, get_collection, close_mongo
from app.core.auth.security import hash_password

EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "superadmin@sanmitra.local").strip().lower()
PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "").strip()
TENANT_ID = os.getenv("SUPER_ADMIN_TENANT_ID", "seed-tenant-1").strip()


async def check_and_fix_admin():
    if not PASSWORD:
        raise SystemExit(
            "SUPER_ADMIN_PASSWORD must be set in the environment before running fix_superadmin.py"
        )

    await init_mongo()
    users = get_collection("core_users")

    user = await users.find_one({"email": EMAIL})

    hashed_pw = hash_password(PASSWORD)

    if not user:
        print(f"User {EMAIL} not found. Creating new superadmin...")
        new_user = {
            "user_id": "superadmin-001",
            "email": EMAIL,
            "hashed_password": hashed_pw,
            "full_name": os.getenv("SUPER_ADMIN_FULL_NAME", "System Super Admin").strip() or "System Super Admin",
            "tenant_id": TENANT_ID,
            "role": "super_admin",
            "roles": ["super_admin"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "subscription_tier": "pro",
            "accepted_terms_at": datetime.now(timezone.utc),
        }
        await users.insert_one(new_user)
        print("Superadmin created successfully!")
    else:
        print(f"User {EMAIL} found. Resetting password and ensuring super_admin role...")
        await users.update_one(
            {"email": EMAIL},
            {
                "$set": {
                    "hashed_password": hashed_pw,
                    "tenant_id": TENANT_ID,
                    "role": "super_admin",
                    "roles": ["super_admin"],
                    "is_active": True,
                }
            },
        )
        print("Superadmin updated successfully!")

    await close_mongo()


if __name__ == "__main__":
    asyncio.run(check_and_fix_admin())
