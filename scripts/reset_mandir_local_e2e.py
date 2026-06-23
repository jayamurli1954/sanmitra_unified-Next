#!/usr/bin/env python3
"""Reset local MandirMitra E2E data and recreate minimal demo seed data."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.core.tenants.service import ensure_tenant_exists
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.db.postgres import close_postgres, get_session_factory, init_postgres
from app.modules.mandir_compat.router import _ensure_default_mandir_sql_accounts_safe
from app.modules.mandir_compat.service import ensure_mandir_compat_indexes, ensure_temple_numeric_id


APP_KEY = "mandirmitra"
TENANT_ID = "demo-mandir-tenant"

MANDIR_CLEAR_COLLECTIONS = [
    "mandir_donations",
    "mandir_seva_bookings",
    "mandir_journal_entries",
    "mandir_devotees",
    "mandir_sevas",
    "mandir_reschedule_requests",
    "mandir_upi_payments",
    "mandir_receipts",
]


def _is_local_uri(uri: str) -> bool:
    lowered = uri.lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def _require_local_environment(*, allow_nonlocal: bool) -> None:
    settings = get_settings()
    environment = str(settings.ENVIRONMENT or "").strip().lower()
    if environment in {"production", "prod"}:
        raise SystemExit("Refusing to reset data while ENVIRONMENT is production.")

    if allow_nonlocal:
        return

    if not _is_local_uri(settings.MONGODB_URI):
        raise SystemExit("Refusing to reset non-local MongoDB. Pass --allow-nonlocal only if this is disposable.")
    if not _is_local_uri(settings.POSTGRES_URI):
        raise SystemExit("Refusing to reset non-local PostgreSQL. Pass --allow-nonlocal only if this is disposable.")


def _base_sevas(now: datetime, temple_id: int) -> list[dict]:
    return [
        {
            "id": str(uuid4()),
            "tenant_id": TENANT_ID,
            "app_key": APP_KEY,
            "temple_id": temple_id,
            "name": "Pallaki Seve",
            "name_english": "Pallaki Seve",
            "name_kannada": "ಪಲ್ಲಕಿ ಸೇವೆ",
            "seva_name": "Pallaki Seve",
            "description": (
                "The temple Deity is taken in a decorated in a Silver palanquin around the temple "
                "in a ceremonial way music, veda parayana, bhakt sangeeth, instrumental round etc. "
                "the seva is held in the evening before the evening Mahapooje"
            ),
            "category": "pooja",
            "amount": 5000,
            "availability": "specific_day",
            "specific_day": 6,
            "time_slot": "night 6:30 pm",
            "max_bookings_per_day": 2,
            "advance_booking_days": 30,
            "requires_approval": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid4()),
            "tenant_id": TENANT_ID,
            "app_key": APP_KEY,
            "temple_id": temple_id,
            "name": "Sarva Seva",
            "name_english": "Sarva Seva",
            "name_kannada": "ಸರ್ವ ಸೇವೆ",
            "seva_name": "Sarva Seva",
            "description": "A comprehensive, daily worship service performed on behalf of a devotee.",
            "category": "archana",
            "amount": 1500,
            "availability": "daily",
            "time_slot": "whole_day",
            "advance_booking_days": 30,
            "requires_approval": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": str(uuid4()),
            "tenant_id": TENANT_ID,
            "app_key": APP_KEY,
            "temple_id": temple_id,
            "name": "Mangala Arathi",
            "name_english": "Mangala Arathi",
            "name_kannada": "ಮಂಗಳ ಆರತಿ",
            "seva_name": "Mangala Arathi",
            "description": "Mangala Arathi is done to the Deity as per the devotee's wishes.",
            "category": "pooja",
            "amount": 50,
            "availability": "daily",
            "time_slot": "whole_day",
            "advance_booking_days": 30,
            "requires_approval": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]


async def reset_mongo() -> int:
    await ensure_tenant_exists(
        TENANT_ID,
        display_name="Demo Temple",
        organization_type="TEMPLE",
        enabled_modules=["temple", "accounting", "audit"],
        app_keys=["mandirmitra"],
        created_by="local-e2e-reset",
    )
    await ensure_mandir_compat_indexes()
    now = datetime.now(timezone.utc)

    deleted = 0
    for collection_name in MANDIR_CLEAR_COLLECTIONS:
        result = await get_collection(collection_name).delete_many({"app_key": APP_KEY})
        deleted += result.deleted_count

    temple_id = await ensure_temple_numeric_id(TENANT_ID, app_key=APP_KEY)
    await get_collection("mandir_temples").delete_many({"app_key": APP_KEY, "tenant_id": {"$ne": TENANT_ID}})
    await get_collection("mandir_temples").update_one(
        {"tenant_id": TENANT_ID, "app_key": APP_KEY},
        {
            "$set": {
                "id": temple_id,
                "temple_id": temple_id,
                "tenant_id": TENANT_ID,
                "app_key": APP_KEY,
                "name": "Demo Temple",
                "temple_name": "Demo Temple",
                "trust_name": "Demo Temple",
                "platform_can_write": True,
                "is_active": True,
                "onboarding_status": "local_e2e_seed",
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    await get_collection("mandir_sevas").insert_many(_base_sevas(now, temple_id))
    return deleted


async def reset_postgres() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(text("DELETE FROM journal_lines WHERE app_key = :app_key"), {"app_key": APP_KEY})
        await session.execute(text("DELETE FROM journal_entries WHERE app_key = :app_key"), {"app_key": APP_KEY})
        await session.commit()

    async with session_factory() as session:
        await _ensure_default_mandir_sql_accounts_safe(session, TENANT_ID, raise_on_failure=True)
        await session.commit()


async def main_async() -> int:
    parser = argparse.ArgumentParser(description="Reset local MandirMitra E2E data.")
    parser.add_argument("--confirm-local-reset", action="store_true", help="Required confirmation for destructive local reset.")
    parser.add_argument("--allow-nonlocal", action="store_true", help="Allow non-local DB URIs. Avoid unless disposable.")
    args = parser.parse_args()

    if not args.confirm_local_reset:
        print("Refusing to run without --confirm-local-reset.")
        return 2

    _require_local_environment(allow_nonlocal=args.allow_nonlocal)

    await init_mongo()
    await init_postgres()
    try:
        deleted = await reset_mongo()
        await reset_postgres()
    finally:
        await close_postgres()
        await close_mongo()

    print(f"MandirMitra local E2E reset complete. Mongo business records deleted: {deleted}")
    print(f"Seed tenant: {TENANT_ID}; app_key: {APP_KEY}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("ENVIRONMENT", "development")
    raise SystemExit(asyncio.run(main_async()))
