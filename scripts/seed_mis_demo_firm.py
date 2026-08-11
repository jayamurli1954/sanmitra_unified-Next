#!/usr/bin/env python3
"""
LOCAL / DEMO ONLY — seed a dedicated manufacturing firm for OfficeMitra MIS (ADR-014).

Creates:
  Tenant:  demo-mfg-mis  ("SanMitra Demo Manufacturing Pvt Ltd")
  Maker:   admin@demo-mfg-mis.local  (tenant_admin)
  Checker: checker@demo-mfg-mis.local  (tenant_admin, different user for maker-checker)

Enables office_ai + office_ai.mis and nested MIS import/export/pack flags, then
loads a generated MIS_FACTS pack for period 2026-07 (draft, not reconciled).

Does NOT write into customer tenants. Safe to re-run (upsert).

Usage:
  python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
  python scripts/seed_mis_demo_firm.py --use-env-password
  python scripts/seed_mis_demo_firm.py --password "ChangeMe123!" --skip-mis-data

Env (with --use-env-password):
  DEMO_MIS_MFG_ADMIN_PASSWORD
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.auth.security import hash_password
from app.core.tenants.service import TENANTS_COLLECTION, ensure_tenant_exists
from app.core.users.service import (
    USERS_COLLECTION,
    _password_provider_subject,
    ensure_demo_mitrabooks_user,
    ensure_users_indexes,
)
from app.core.tenants.context import resolve_app_key
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.office_ai.services import mis_store

DEMO_TENANT_ID = "demo-mfg-mis"
DEMO_DISPLAY_NAME = "SanMitra Demo Manufacturing Pvt Ltd"
DEMO_MAKER_EMAIL = "admin@demo-mfg-mis.local"
DEMO_CHECKER_EMAIL = "checker@demo-mfg-mis.local"
DEMO_PERIOD = "2026-07"
DEMO_PACK_KEY = "manufacturing"

# Validated via ensure_tenant_exists (single-dot feature flags only).
BASE_ENABLED_MODULES = [
    "business",
    "accounting",
    "gst",
    "inventory",
    "audit",
    "office_ai",
    "office_ai.mis",
]

# Nested MIS capabilities accepted at runtime but rejected by entitlement validator —
# appended with a direct Mongo $set after ensure_tenant_exists.
NESTED_MIS_FLAGS = [
    "office_ai.mis.import",
    "office_ai.mis.export",
    "office_ai.mis.pack.manufacturing",
]


def _load_generator():
    gen_path = REPO_ROOT / "tools" / "sanmitra-demo-data-generator" / "generate_mis_pack.py"
    spec = importlib.util.spec_from_file_location("generate_mis_pack", gen_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load MIS generator at {gen_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def _ensure_password_user(
    *,
    email: str,
    password: str,
    full_name: str,
    tenant_id: str,
) -> dict[str, Any]:
    await ensure_users_indexes()
    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)
    normalized_email = email.strip().lower()
    existing = await users.find_one({"email": normalized_email})
    user_id = str(existing.get("user_id") or uuid4()) if existing else str(uuid4())
    fields = {
        "user_id": user_id,
        "email": normalized_email,
        "full_name": full_name,
        "tenant_id": tenant_id,
        "app_key": resolve_app_key("mitrabooks"),
        "role": "tenant_admin",
        "hashed_password": hash_password(password),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(normalized_email),
        "is_active": True,
        "subscription_tier": "pro",
        "subscription_status": "active",
        "updated_at": now,
    }
    if existing:
        await users.update_one({"_id": existing["_id"]}, {"$set": fields})
    else:
        await users.insert_one({**fields, "created_at": now})
    return {"user_id": user_id, "email": normalized_email, "tenant_id": tenant_id, "role": "tenant_admin"}


async def _apply_mis_entitlements(tenant_id: str) -> list[str]:
    tenants = get_collection(TENANTS_COLLECTION)
    doc = await tenants.find_one({"tenant_id": tenant_id})
    if not doc:
        raise RuntimeError(f"Tenant not found after create: {tenant_id}")
    modules = [str(m).strip().lower() for m in (doc.get("enabled_modules") or []) if str(m).strip()]
    for flag in NESTED_MIS_FLAGS:
        if flag not in modules:
            modules.append(flag)
    # Keep parent flags present.
    for required in BASE_ENABLED_MODULES:
        if required not in modules:
            modules.append(required)
    await tenants.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "enabled_modules": modules,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": "seed-mis-demo-firm",
                "demo_profile": "mis_manufacturing_v1",
            }
        },
    )
    return modules


async def _seed_mis_pack(*, tenant_id: str, maker_user_id: str, size: str, seed: int) -> dict[str, Any]:
    gen = _load_generator()
    facts, meta = gen.build_mis_facts(
        industry="manufacturing",
        period=DEMO_PERIOD,
        size=size,
        seed=seed,
    )

    # Prefer one draft pack per period for this demo tenant.
    existing = await mis_store.list_packs(tenant_id=tenant_id, period=DEMO_PERIOD, limit=20)
    pack = None
    for item in existing:
        if str(item.get("pack_key") or "") == DEMO_PACK_KEY and str(item.get("status") or "") == "draft":
            pack = item
            break
    if pack is None:
        pack = await mis_store.create_pack_draft(
            tenant_id=tenant_id,
            user={"sub": maker_user_id},
            pack_key=DEMO_PACK_KEY,
            period=DEMO_PERIOD,
            ingestion_path="excel_import",
        )

    pack_id = str(pack.get("id") or "")
    if not pack_id:
        raise RuntimeError("MIS pack id missing after create")

    if pack.get("immutable"):
        return {"pack_id": pack_id, "status": pack.get("status"), "inserted": 0, "skipped": "immutable"}

    # Replace facts on draft packs so re-seed is deterministic.
    from app.modules.office_ai.models import MIS_FACTS_COLLECTION

    await get_collection(MIS_FACTS_COLLECTION).delete_many({"tenant_id": tenant_id, "pack_id": pack_id})
    insert_res = await mis_store.insert_facts(
        tenant_id=tenant_id,
        pack_id=pack_id,
        user={"sub": maker_user_id},
        facts=facts,
    )

    out_dir = REPO_ROOT / "tools" / "sanmitra-demo-data-generator" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = out_dir / f"mis_manufacturing_{DEMO_PERIOD}_{size}.xlsx"
    gen.write_xlsx(facts, xlsx_path)

    return {
        "pack_id": pack_id,
        "status": "draft",
        "inserted": int(insert_res.get("inserted") or 0),
        "fact_count": meta["fact_count"],
        "xlsx": str(xlsx_path),
        "kpis": meta.get("kpis") or {},
    }


async def seed(args: argparse.Namespace) -> None:
    password = args.password
    if args.use_env_password:
        password = os.getenv("DEMO_MIS_MFG_ADMIN_PASSWORD", "")
    if not password or len(str(password).strip()) < 6:
        raise SystemExit(
            "password is required (min 6 chars); pass --password or set "
            "DEMO_MIS_MFG_ADMIN_PASSWORD with --use-env-password"
        )
    password = str(password).strip()

    await init_mongo()
    try:
        maker = await ensure_demo_mitrabooks_user(
            email=DEMO_MAKER_EMAIL,
            password=password,
            full_name="Demo MFG MIS Admin",
            tenant_id=DEMO_TENANT_ID,
            display_name=DEMO_DISPLAY_NAME,
        )
        if maker is None:
            raise SystemExit("Failed to create maker admin user")

        # Re-apply full module set (ensure_demo_mitrabooks_user only sets business core).
        await ensure_tenant_exists(
            DEMO_TENANT_ID,
            display_name=DEMO_DISPLAY_NAME,
            organization_type="BUSINESS",
            enabled_modules=list(BASE_ENABLED_MODULES),
            app_keys=["mitrabooks"],
            subscription_plan="pro",
            created_by="seed-mis-demo-firm",
        )
        modules = await _apply_mis_entitlements(DEMO_TENANT_ID)

        checker = await _ensure_password_user(
            email=DEMO_CHECKER_EMAIL,
            password=password,
            full_name="Demo MFG MIS Checker",
            tenant_id=DEMO_TENANT_ID,
        )

        mis_result: dict[str, Any] | None = None
        if not args.skip_mis_data:
            mis_result = await _seed_mis_pack(
                tenant_id=DEMO_TENANT_ID,
                maker_user_id=str(maker["user_id"]),
                size=args.size,
                seed=args.seed,
            )
    finally:
        await close_mongo()

    print(f"Seeded MIS demo firm: {DEMO_DISPLAY_NAME}")
    print(f"  tenant_id: {DEMO_TENANT_ID}")
    print(f"  maker:     {DEMO_MAKER_EMAIL} / <password supplied>")
    print(f"  checker:   {DEMO_CHECKER_EMAIL} / <same password>")
    print(f"  modules:   {', '.join(modules)}")
    if mis_result:
        print(
            f"  MIS pack:  {mis_result['pack_id']} status={mis_result['status']} "
            f"facts={mis_result.get('inserted') or mis_result.get('fact_count')}"
        )
        if mis_result.get("xlsx"):
            print(f"  Excel:     {mis_result['xlsx']}")
        print("  Next: login as maker -> OfficeMitra AI -> MIS Packs -> reconcile -> checker approves in Proposals.")
    else:
        print("  MIS data:  skipped (--skip-mis-data)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed SanMitra Demo Manufacturing firm for OfficeMitra MIS.")
    p.add_argument("--password", default="", help="Shared password for maker and checker (≥6 chars)")
    p.add_argument("--use-env-password", action="store_true", help="Read DEMO_MIS_MFG_ADMIN_PASSWORD")
    p.add_argument("--size", default="medium", choices=("small", "medium", "large"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--skip-mis-data", action="store_true", help="Create firm/users only; do not load MIS facts")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(seed(parse_args()))
