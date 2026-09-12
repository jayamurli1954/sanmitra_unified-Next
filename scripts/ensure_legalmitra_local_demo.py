"""Ensure a local LegalMitra demo tenant + password user for API smoke tests.

Does NOT print the password. Requires:

  $env:LEGALMITRA_DEMO_PASSWORD = "<choose-a-local-only-password>"

Then:

  python scripts/ensure_legalmitra_local_demo.py

Login test:

  $env:LEGALMITRA_API_BASE = "http://127.0.0.1:8000"
  # login with email legal.demo@sanmitra.local and the password you set
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.auth.security import hash_password
from app.core.tenants.service import ensure_tenant_exists
from app.core.users.service import USERS_COLLECTION, ensure_users_indexes, get_user_by_email
from app.db.mongo import close_mongo, get_collection, init_mongo

DEMO_TENANT = "demo-legalmitra"
DEMO_EMAIL = "legal.demo@sanmitra.local"
DEMO_NAME = "LegalMitra Local Demo Admin"
APP_KEY = "legalmitra"


async def main() -> int:
    password = (os.environ.get("LEGALMITRA_DEMO_PASSWORD") or "").strip()
    if len(password) < 8:
        print(
            "FAIL: set LEGALMITRA_DEMO_PASSWORD to a local-only password "
            "(min 8 chars). It will not be printed."
        )
        return 1

    await init_mongo()
    try:
        await ensure_users_indexes()
        await ensure_tenant_exists(
            DEMO_TENANT,
            display_name="LegalMitra Local Demo",
            organization_type="LEGAL",
            enabled_modules=["legal", "rag", "compliance", "audit"],
            app_keys=[APP_KEY],
            subscription_plan="pro",
            created_by="ensure_legalmitra_local_demo",
        )

        users = get_collection(USERS_COLLECTION)
        existing = await get_user_by_email(DEMO_EMAIL)
        if existing:
            await users.update_one(
                {"email": DEMO_EMAIL},
                {
                    "$set": {
                        "hashed_password": hash_password(password),
                        "tenant_id": DEMO_TENANT,
                        "app_key": APP_KEY,
                        "role": "tenant_admin",
                        "auth_provider": "password",
                        "is_active": True,
                        "full_name": DEMO_NAME,
                    }
                },
            )
            action = "updated"
        else:
            from app.core.users.service import create_user

            await create_user(
                email=DEMO_EMAIL,
                password=password,
                full_name=DEMO_NAME,
                tenant_id=DEMO_TENANT,
                role="tenant_admin",
                app_key=APP_KEY,
            )
            action = "created"

        print("OK")
        print(f"action={action}")
        print(f"tenant_id={DEMO_TENANT}")
        print(f"app_key={APP_KEY}")
        print(f"email={DEMO_EMAIL}")
        print("password=SET_FROM_ENV (not printed)")
        print()
        print("Next:")
        print('  $env:LEGALMITRA_API_BASE = "http://127.0.0.1:8000"')
        print("  # login with the email above + LEGALMITRA_DEMO_PASSWORD")
        print("  python scripts/run_legalmitra_crosswalk_smoke.py --api")
        return 0
    finally:
        await close_mongo()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
