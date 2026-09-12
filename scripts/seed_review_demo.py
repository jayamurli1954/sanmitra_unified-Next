#!/usr/bin/env python3
"""
LOCAL / DEMO ONLY — enable OfficeMitra Review on the MIS manufacturing demo tenant.

Hard-locked tenant: demo-mfg-mis
Refuses: demo-mitrabooks-business and every other tenant id.

This script never posts MitraBooks journals. It only:
  - adds office_ai.review* flags on demo-mfg-mis
  - optionally creates an engagement on the existing MIS pack
  - optionally runs scan + working papers + a closable note (OfficeMitra Mongo)

Prereq:
  python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"

Usage:
  python scripts/seed_review_demo.py --flags-only
  python scripts/seed_review_demo.py --run-smoke
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.tenants.service import TENANTS_COLLECTION
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.office_ai.models import ensure_indexes
from app.modules.office_ai.services import mis_store, review_service, review_store

REVIEW_FLAGS = [
    "office_ai.review",
    "office_ai.review.working_papers",
    "office_ai.review.notes",
]
BLOCKED_TENANT_IDS = frozenset({"demo-mitrabooks-business"})
DEMO_PERIOD = "2026-07"


def _load_mis_seed_module():
    path = REPO_ROOT / "scripts" / "seed_mis_demo_firm.py"
    spec = importlib.util.spec_from_file_location("seed_mis_demo_firm", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def allowed_review_demo_tenant_id() -> str:
    mod = _load_mis_seed_module()
    return str(mod.DEMO_TENANT_ID)


def assert_allowed_review_demo_tenant(tenant_id: str) -> str:
    """Refuse ERP / production-looking tenants. Review smoke is demo-mfg-mis only."""
    key = str(tenant_id or "").strip().lower()
    allowed = allowed_review_demo_tenant_id().strip().lower()
    if not key:
        raise SystemExit("tenant_id is required")
    if key in BLOCKED_TENANT_IDS:
        raise SystemExit(
            f"Refusing tenant {key}: Review must not be enabled on the live ERP demo tenant."
        )
    if key != allowed:
        raise SystemExit(
            f"Refusing tenant {key}: Review demo smoke is locked to {allowed} only."
        )
    return key


async def _apply_review_entitlements(tenant_id: str) -> list[str]:
    tenants = get_collection(TENANTS_COLLECTION)
    doc = await tenants.find_one({"tenant_id": tenant_id})
    if not doc:
        raise SystemExit(
            f"Tenant {tenant_id} not found. Run scripts/seed_mis_demo_firm.py first."
        )
    modules = [str(m).strip().lower() for m in (doc.get("enabled_modules") or []) if str(m).strip()]
    if "office_ai" not in modules:
        modules.append("office_ai")
    if "office_ai.mis" not in modules:
        modules.append("office_ai.mis")
    for flag in REVIEW_FLAGS:
        if flag not in modules:
            modules.append(flag)
    await tenants.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "enabled_modules": modules,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": "seed-review-demo",
                "review_demo": True,
            }
        },
    )
    return modules


async def _latest_pack_id(tenant_id: str) -> str:
    packs = await mis_store.list_packs(tenant_id=tenant_id, period=DEMO_PERIOD, limit=20)
    if not packs:
        packs = await mis_store.list_packs(tenant_id=tenant_id, limit=20)
    if not packs:
        raise SystemExit("No MIS pack on demo-mfg-mis. Re-run seed_mis_demo_firm.py without --skip-mis-data.")
    return str(packs[0].get("id") or "")


async def _run_in_process_smoke(*, tenant_id: str) -> dict[str, Any]:
    await ensure_indexes()
    pack_id = await _latest_pack_id(tenant_id)
    user = {"sub": "seed-review-demo"}
    existing = await review_store.list_engagements(tenant_id=tenant_id, limit=20)
    engagement = None
    for item in existing:
        if str(item.get("pack_id") or "") == pack_id and str(item.get("period") or "") == DEMO_PERIOD:
            engagement = item
            break
    if engagement is None:
        engagement = await review_service.create_engagement(
            tenant_id=tenant_id,
            user=user,
            period=DEMO_PERIOD,
            pack_id=pack_id,
        )
    elif str(engagement.get("pack_id") or "") != pack_id:
        engagement = await review_service.link_pack(
            tenant_id=tenant_id,
            engagement_id=str(engagement["id"]),
            user=user,
            pack_id=pack_id,
        )
    scanned = await review_service.scan_engagement(
        tenant_id=tenant_id,
        engagement_id=str(engagement["id"]),
        user=user,
    )
    papers = await review_service.generate_working_papers(
        tenant_id=tenant_id,
        engagement_id=str(engagement["id"]),
        user=user,
    )
    issues = scanned.get("issues") or []
    issue_id = str(issues[0]["id"]) if issues else None
    note_res = await review_service.create_note_with_task(
        tenant_id=tenant_id,
        engagement_id=str(engagement["id"]),
        user=user,
        description="Demo smoke: follow up ageing / findings. Does not post to MitraBooks.",
        issue_id=issue_id,
    )
    closed = await review_store.update_note(
        tenant_id=tenant_id,
        note_id=str(note_res["item"]["id"]),
        user=user,
        updates={"status": "closed"},
    )
    return {
        "pack_id": pack_id,
        "engagement_id": str(engagement["id"]),
        "issue_count": int(scanned.get("issue_count") or 0),
        "engagement_risk_score": scanned.get("engagement_risk_score"),
        "data_quality_score": scanned.get("data_quality_score"),
        "ssdv_cli": scanned.get("ssdv_cli"),
        "paper_count": int(papers.get("count") or 0),
        "note_id": str(closed.get("id") or ""),
        "note_status": closed.get("status"),
        "finding_codes": [str(item.get("finding_code") or "") for item in issues[:12]],
    }


async def seed(args: argparse.Namespace) -> None:
    tenant_id = assert_allowed_review_demo_tenant(allowed_review_demo_tenant_id())
    await init_mongo()
    try:
        modules = await _apply_review_entitlements(tenant_id)
        smoke: dict[str, Any] | None = None
        if args.run_smoke:
            smoke = await _run_in_process_smoke(tenant_id=tenant_id)
    finally:
        await close_mongo()

    print(f"Review demo entitlements on {tenant_id}")
    print(f"  modules: {', '.join(modules)}")
    print("  ledger:  no MitraBooks journals posted")
    if smoke:
        print(f"  pack:    {smoke['pack_id']}")
        print(f"  engagement: {smoke['engagement_id']}")
        print(
            f"  scan:    issues={smoke['issue_count']} "
            f"risk={smoke['engagement_risk_score']} "
            f"data_quality_score={smoke['data_quality_score']} "
            f"ssdv_cli={smoke['ssdv_cli']}"
        )
        print(f"  papers:  {smoke['paper_count']}")
        print(f"  note:    {smoke['note_id']} status={smoke['note_status']}")
        if smoke["finding_codes"]:
            print(f"  codes:   {', '.join(smoke['finding_codes'])}")
        print("  Next: login as admin@demo-mfg-mis.local -> OfficeMitra AI -> Review tab.")
    else:
        print("  smoke:   skipped (--flags-only). UI Review tab appears after login.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enable OfficeMitra Review on demo-mfg-mis only.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--flags-only", action="store_true", help="Enable office_ai.review* only")
    mode.add_argument(
        "--run-smoke",
        action="store_true",
        help="Enable flags and run scan / papers / close-note against MIS facts",
    )
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(seed(parse_args()))
