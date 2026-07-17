#!/usr/bin/env python3
"""Ensure local Mandir demo tenant actors for guarded Stage 3 E2E.

Creates a second tenant_admin on the configured demo Mandir tenant when missing,
and marks the temple record demo-writable. Local/disposable use only.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.core.users.service import create_user, get_user_by_email
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.mandir_compat.service import ensure_demo_mandir_bootstrap, ensure_temple_numeric_id


LOCAL_MAKER_EMAIL = os.getenv("MANDIRMITRA_E2E_MAKER_EMAIL", "mandir.maker@sanmitra.local").strip()
LOCAL_MAKER_PASSWORD = os.getenv("MANDIRMITRA_E2E_MAKER_PASSWORD", "").strip()


def _require_local() -> None:
    settings = get_settings()
    environment = str(settings.ENVIRONMENT or "").strip().lower()
    if environment in {"production", "prod"}:
        raise SystemExit("Refusing to provision demo actors while ENVIRONMENT is production.")


async def main_async(*, allow_nonlocal: bool) -> int:
    _require_local()
    settings = get_settings()
    tenant_id = str(settings.DEMO_MANDIR_TENANT_ID or "seed-tenant-1").strip()
    if not tenant_id:
        raise SystemExit("DEMO_MANDIR_TENANT_ID is empty.")

    await init_mongo()
    try:
        await ensure_demo_mandir_bootstrap("mandirmitra")
        temple_id = await ensure_temple_numeric_id(tenant_id, app_key="mandirmitra")
        now = datetime.now(timezone.utc)
        await get_collection("mandir_temples").update_one(
            {"tenant_id": tenant_id, "app_key": "mandirmitra"},
            {
                "$set": {
                    "platform_can_write": True,
                    "is_active": True,
                    "id": temple_id,
                    "temple_id": temple_id,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

        if not LOCAL_MAKER_EMAIL or "@" not in LOCAL_MAKER_EMAIL:
            raise SystemExit("Set MANDIRMITRA_E2E_MAKER_EMAIL to a valid maker email.")
        if len(LOCAL_MAKER_PASSWORD) < 8:
            raise SystemExit(
                "Set MANDIRMITRA_E2E_MAKER_PASSWORD (min 8 chars). "
                "Do not commit the password."
            )

        existing = await get_user_by_email(LOCAL_MAKER_EMAIL)
        if not existing:
            await create_user(
                email=LOCAL_MAKER_EMAIL,
                password=LOCAL_MAKER_PASSWORD,
                full_name="Mandir Demo Maker",
                tenant_id=tenant_id,
                role="tenant_admin",
                app_key="mandirmitra",
            )
            print(f"Created maker actor: {LOCAL_MAKER_EMAIL} on tenant {tenant_id}")
        else:
            print(f"Maker actor already exists: {LOCAL_MAKER_EMAIL} on tenant {existing.get('tenant_id')}")
    finally:
        await close_mongo()

    print(f"Demo tenant ready: {tenant_id}")
    print(f"Approver (seed): admin@sanmitra.local")
    print(f"Maker (local): {LOCAL_MAKER_EMAIL}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure local Mandir demo E2E actors.")
    parser.add_argument("--allow-nonlocal", action="store_true", help="Skip local URI guard.")
    args = parser.parse_args()
    os.environ.setdefault("ENVIRONMENT", "development")
    return asyncio.run(main_async(allow_nonlocal=args.allow_nonlocal))


if __name__ == "__main__":
    raise SystemExit(main())
