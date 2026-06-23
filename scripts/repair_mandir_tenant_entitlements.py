import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.getcwd())

from app.db.mongo import close_mongo, get_collection, init_mongo


TENANTS_COLLECTION = "core_tenants"
MANDIR_TEMPLES_COLLECTION = "mandir_temples"
MANDIR_TENANT_NAMES = {
    "Kondappadi Shree Ananthapadmanabha Temple",
    "Demo Temple",
    "MandirMitra Temple - Demo",
}
MANDIR_TENANT_PATCH = {
    "organization_type": "TEMPLE",
    "enabled_modules": ["temple", "accounting", "audit"],
    "app_keys": ["mandirmitra"],
}


async def _find_tenant_ids_from_temple_profiles() -> set[str]:
    temples = get_collection(MANDIR_TEMPLES_COLLECTION)
    name_fields = ("name", "temple_name", "trust_name", "display_name")
    name_clauses = [{field: {"$in": sorted(MANDIR_TENANT_NAMES)}} for field in name_fields]
    cursor = temples.find({"app_key": "mandirmitra", "$or": name_clauses})
    rows = await cursor.to_list(length=100)
    return {str(row.get("tenant_id") or "").strip() for row in rows if str(row.get("tenant_id") or "").strip()}


async def repair_mandir_tenants(*, apply: bool) -> None:
    await init_mongo()
    try:
        tenants = get_collection(TENANTS_COLLECTION)
        tenant_ids = await _find_tenant_ids_from_temple_profiles()
        tenant_filter = {
            "$or": [
                {"display_name": {"$in": sorted(MANDIR_TENANT_NAMES)}},
                {"tenant_id": {"$in": sorted(tenant_ids)}},
            ]
        }
        cursor = tenants.find(tenant_filter)
        rows = await cursor.to_list(length=100)
        if not rows:
            print("No matching MandirMitra tenant rows found.")
            return

        for row in rows:
            tenant_id = row.get("tenant_id")
            display_name = row.get("display_name")
            before = {
                "organization_type": row.get("organization_type"),
                "enabled_modules": row.get("enabled_modules"),
                "app_keys": row.get("app_keys"),
            }
            print(f"{display_name} ({tenant_id})")
            print(f"  before: {before}")
            print(f"  after : {MANDIR_TENANT_PATCH}")
            if apply:
                await tenants.update_one(
                    {"tenant_id": tenant_id},
                    {
                        "$set": {
                            **MANDIR_TENANT_PATCH,
                            "updated_at": datetime.now(timezone.utc),
                            "updated_by": "repair_mandir_tenant_entitlements",
                        }
                    },
                )
                print("  updated")
            else:
                print("  dry-run only")
    finally:
        await close_mongo()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair known MandirMitra temple tenants to TEMPLE entitlements.")
    parser.add_argument("--apply", action="store_true", help="Apply updates. Without this flag the script only prints changes.")
    args = parser.parse_args()
    asyncio.run(repair_mandir_tenants(apply=args.apply))


if __name__ == "__main__":
    main()
