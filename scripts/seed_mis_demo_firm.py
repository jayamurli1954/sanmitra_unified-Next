#!/usr/bin/env python3
"""
LOCAL / DEMO ONLY — seed a dedicated manufacturing firm for OfficeMitra MIS (ADR-014).

Creates:
  Tenant:  demo-mfg-mis  ("SanMitra Demo Manufacturing Pvt Ltd")
  Maker:   admin@demo-mfg-mis.local  (tenant_admin)
  Checker: checker@demo-mfg-mis.local  (tenant_admin, different user for maker-checker)

Enables office_ai + office_ai.mis and nested MIS import/export/pack flags, then
loads a fixed manufacturing MIS fact pack for period 2026-07 (draft, not reconciled).

MIS Excel / synthetic ERP generation stays outside this repository.
This script only seeds a demo tenant + a small inlined fact snapshot for UI testing.

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
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.auth.security import hash_password
from app.core.tenants.context import resolve_app_key
from app.core.tenants.service import TENANTS_COLLECTION, ensure_tenant_exists
from app.core.users.service import (
    USERS_COLLECTION,
    _password_provider_subject,
    ensure_demo_mitrabooks_user,
    ensure_users_indexes,
)
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.office_ai.services import mis_store

DEMO_TENANT_ID = "demo-mfg-mis"
DEMO_DISPLAY_NAME = "SanMitra Demo Manufacturing Pvt Ltd"
DEMO_MAKER_EMAIL = "admin@demo-mfg-mis.local"
DEMO_CHECKER_EMAIL = "checker@demo-mfg-mis.local"
DEMO_PERIOD = "2026-07"
DEMO_PACK_KEY = "manufacturing"
DEMO_COMPANY = "SanMitra Demo Manufacturing Pvt Ltd"

BASE_ENABLED_MODULES = [
    "business",
    "accounting",
    "gst",
    "inventory",
    "audit",
    "office_ai",
    "office_ai.mis",
]

NESTED_MIS_FLAGS = [
    "office_ai.mis.import",
    "office_ai.mis.export",
    "office_ai.mis.pack.manufacturing",
]


def _money(value: Decimal | float | int) -> str:
    return format(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")


def _fact(
    *,
    entity_type: str,
    source_ref: str,
    source_id: str,
    amount: Decimal | float | int | None = None,
    value: Any = None,
    dimensions: dict[str, Any] | None = None,
    period: str = DEMO_PERIOD,
    as_of: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "entity_type": entity_type,
        "period": period,
        "as_of": as_of or f"{DEMO_PERIOD}-28",
        "source_system": "demo_seed",
        "source_id": source_id,
        "source_ref": source_ref,
        "currency": "INR",
        "dimensions": dict(dimensions or {}),
    }
    if amount is not None:
        row["amount_decimal"] = _money(amount)
    if value is not None:
        row["value"] = value
    return row


def build_demo_manufacturing_facts() -> list[dict[str, Any]]:
    """Small fixed MIS snapshot for demo-mfg-mis (not a general data generator)."""
    revenue = Decimal("18500000.00")
    cogs = Decimal("11470000.00")
    gp = revenue - cogs
    opex = Decimal("3330000.00")
    ebit = gp - opex
    tax = (ebit * Decimal("0.25")).quantize(Decimal("0.01"))
    pat = ebit - tax
    cash = Decimal("1480000.00")
    bank = Decimal("2620000.00")
    ar = Decimal("3330000.00")
    inventory = Decimal("2035000.00")
    ap = Decimal("2523400.00")
    equity = cash + bank + ar + inventory - ap + Decimal("4200000.00")

    ar_buckets = {
        "Current": Decimal("1598400.00"),
        "1-30": Decimal("732600.00"),
        "31-60": Decimal("466200.00"),
        "61-90": Decimal("299700.00"),
        "90+": Decimal("233100.00"),
    }
    ap_buckets = {
        "Current": Decimal("1387870.00"),
        "1-30": Decimal("504680.00"),
        "31-60": Decimal("302808.00"),
        "61-90": Decimal("201872.00"),
        "90+": Decimal("126170.00"),
    }

    facts: list[dict[str, Any]] = []
    for line, amount, code in [
        ("Revenue", revenue, "REV"),
        ("COGS", cogs, "COGS"),
        ("Gross Profit", gp, "GP"),
        ("Operating Expenses", opex, "OPEX"),
        ("EBIT", ebit, "EBIT"),
        ("Tax", tax, "TAX"),
        ("PAT", pat, "PAT"),
    ]:
        facts.append(
            _fact(
                entity_type="pnl_line",
                source_ref=f"PnL!{code}",
                source_id=f"pnl-{code.lower()}",
                amount=amount,
                dimensions={"line": line, "company": DEMO_COMPANY, "industry": "manufacturing"},
            )
        )

    for line, amount, code in [
        ("Cash", cash, "CASH"),
        ("Bank", bank, "BANK"),
        ("Accounts Receivable", ar, "AR"),
        ("Inventory", inventory, "INV"),
        ("Accounts Payable", ap, "AP"),
        ("Equity", equity, "EQ"),
    ]:
        facts.append(
            _fact(
                entity_type="bs_line",
                source_ref=f"BS!{code}",
                source_id=f"bs-{code.lower()}",
                amount=amount,
                dimensions={"line": line, "company": DEMO_COMPANY},
            )
        )

    ops = Decimal("4200000.00")
    investing = Decimal("-250000.00")
    financing = Decimal("80000.00")
    for line, amount, code in [
        ("Operating", ops, "CFO"),
        ("Investing", investing, "CFI"),
        ("Financing", financing, "CFF"),
        ("Net Change", ops + investing + financing, "NET"),
    ]:
        facts.append(
            _fact(
                entity_type="cash_summary",
                source_ref=f"CF!{code}",
                source_id=f"cf-{code.lower()}",
                amount=amount,
                dimensions={"line": line, "company": DEMO_COMPANY},
            )
        )

    for bucket, amount in ar_buckets.items():
        facts.append(
            _fact(
                entity_type="aging_bucket",
                source_ref=f"AR!{bucket}",
                source_id=f"ar-{bucket.lower().replace('+', 'plus')}",
                amount=amount,
                dimensions={"side": "AR", "bucket": bucket, "company": DEMO_COMPANY},
            )
        )
    for bucket, amount in ap_buckets.items():
        facts.append(
            _fact(
                entity_type="aging_bucket",
                source_ref=f"AP!{bucket}",
                source_id=f"ap-{bucket.lower().replace('+', 'plus')}",
                amount=amount,
                dimensions={"side": "AP", "bucket": bucket, "company": DEMO_COMPANY},
            )
        )

    dso = round(float((ar / revenue) * Decimal("360")), 1)
    dpo = round(float((ap / cogs) * Decimal("360")), 1)
    gp_pct = round(float((gp / revenue) * Decimal("100")), 1)
    current_ratio = round(float((cash + bank + ar + inventory) / ap), 2)
    cash_runway = round(float((cash + bank) / (opex / Decimal("12"))), 1)
    for name, value, unit in [
        ("DSO", dso, "days"),
        ("DPO", dpo, "days"),
        ("GrossMarginPct", gp_pct, "percent"),
        ("CurrentRatio", current_ratio, "ratio"),
        ("CashRunwayMonths", cash_runway, "months"),
        ("Revenue", float(revenue), "INR"),
        ("PAT", float(pat), "INR"),
        ("CashAndBank", float(cash + bank), "INR"),
    ]:
        facts.append(
            _fact(
                entity_type="kpi",
                source_ref=f"KPI!{name}",
                source_id=f"kpi-{name.lower()}",
                value=value,
                dimensions={"kpi": name, "unit": unit, "company": DEMO_COMPANY},
            )
        )

    # Short trend for dashboard (prior months).
    for month, rev in [("2026-06", "15200000"), ("2026-05", "14850000"), ("2026-04", "14100000")]:
        facts.append(
            _fact(
                entity_type="pnl_line",
                period=month,
                as_of=f"{month}-28",
                source_ref=f"PnLTrend!REV!{month}",
                source_id=f"pnl-trend-rev-{month}",
                amount=Decimal(rev),
                dimensions={"line": "Revenue", "company": DEMO_COMPANY, "trend": True},
            )
        )

    return facts


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


async def _seed_mis_pack(*, tenant_id: str, maker_user_id: str) -> dict[str, Any]:
    facts = build_demo_manufacturing_facts()

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

    from app.modules.office_ai.models import MIS_FACTS_COLLECTION

    await get_collection(MIS_FACTS_COLLECTION).delete_many({"tenant_id": tenant_id, "pack_id": pack_id})
    insert_res = await mis_store.insert_facts(
        tenant_id=tenant_id,
        pack_id=pack_id,
        user={"sub": maker_user_id},
        facts=facts,
    )
    return {
        "pack_id": pack_id,
        "status": "draft",
        "inserted": int(insert_res.get("inserted") or 0),
        "fact_count": len(facts),
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

        await _ensure_password_user(
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
        print("  Next: login as maker -> OfficeMitra AI -> MIS Packs -> reconcile -> checker approves in Proposals.")
    else:
        print("  MIS data:  skipped (--skip-mis-data)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed SanMitra Demo Manufacturing firm for OfficeMitra MIS.")
    p.add_argument("--password", default="", help="Shared password for maker and checker (>=6 chars)")
    p.add_argument("--use-env-password", action="store_true", help="Read DEMO_MIS_MFG_ADMIN_PASSWORD")
    p.add_argument("--skip-mis-data", action="store_true", help="Create firm/users only; do not load MIS facts")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(seed(parse_args()))
