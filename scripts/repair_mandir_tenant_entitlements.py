"""One-off MandirMitra tenant repairs (product profile + approved display-name exceptions).

Platform Owner Entitlements intentionally does NOT rename tenants. Approved
display-name corrections go through this script only.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.getcwd())

from app.db.mongo import close_mongo, get_collection, init_mongo


TENANTS_COLLECTION = "core_tenants"
MANDIR_TEMPLES_COLLECTION = "mandir_temples"

# One-time approved rename exceptions only. Do not use Entitlements UI for renames.
DISPLAY_NAME_RENAMES = {
    "Kondappadi Shree Ananthapadmanabha Temple": "Parlathaya Prathishtana",
}

MANDIR_TENANT_NAMES = set(DISPLAY_NAME_RENAMES) | {
    "Parlathaya Prathishtana",
    "Demo Temple",
    "MandirMitra Temple - Demo",
}

MANDIR_TENANT_PATCH = {
    "organization_type": "TEMPLE",
    "enabled_modules": ["temple", "accounting", "audit"],
    "app_keys": ["mandirmitra"],
}

TEMPLE_NAME_FIELDS = ("name", "temple_name", "trust_name", "display_name")


async def _find_tenant_ids_from_temple_profiles() -> set[str]:
    temples = get_collection(MANDIR_TEMPLES_COLLECTION)
    lookup_names = sorted(set(MANDIR_TENANT_NAMES) | set(DISPLAY_NAME_RENAMES))
    name_clauses = [{field: {"$in": lookup_names}} for field in TEMPLE_NAME_FIELDS]
    cursor = temples.find({"app_key": "mandirmitra", "$or": name_clauses})
    rows = await cursor.to_list(length=100)
    return {str(row.get("tenant_id") or "").strip() for row in rows if str(row.get("tenant_id") or "").strip()}


async def _rename_temple_profiles(*, tenant_id: str, old_name: str, new_name: str, apply: bool) -> int:
    temples = get_collection(MANDIR_TEMPLES_COLLECTION)
    matched = 0
    for field in TEMPLE_NAME_FIELDS:
        query = {"tenant_id": tenant_id, "app_key": "mandirmitra", field: old_name}
        count = await temples.count_documents(query)
        if count == 0:
            continue
        matched += count
        print(f"  temple profile field {field}: {old_name!r} -> {new_name!r} ({count})")
        if apply:
            await temples.update_many(
                query,
                {
                    "$set": {
                        field: new_name,
                        "updated_at": datetime.now(timezone.utc),
                        "updated_by": "repair_mandir_tenant_entitlements",
                    }
                },
            )
    return matched


async def repair_mandir_tenants(*, apply: bool) -> None:
    await init_mongo()
    try:
        tenants = get_collection(TENANTS_COLLECTION)
        tenant_ids = await _find_tenant_ids_from_temple_profiles()
        lookup_names = sorted(set(MANDIR_TENANT_NAMES) | set(DISPLAY_NAME_RENAMES))
        tenant_filter = {
            "$or": [
                {"display_name": {"$in": lookup_names}},
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
            display_name = str(row.get("display_name") or "").strip()
            renamed_to = DISPLAY_NAME_RENAMES.get(display_name)
            before = {
                "display_name": display_name,
                "organization_type": row.get("organization_type"),
                "enabled_modules": row.get("enabled_modules"),
                "app_keys": row.get("app_keys"),
            }
            after = {
                "display_name": renamed_to or display_name,
                **MANDIR_TENANT_PATCH,
            }
            print(f"{display_name} ({tenant_id})")
            print(f"  before: {before}")
            print(f"  after : {after}")
            if renamed_to:
                print("  note  : one-time approved display-name rename")
                await _rename_temple_profiles(
                    tenant_id=str(tenant_id),
                    old_name=display_name,
                    new_name=renamed_to,
                    apply=apply,
                )
            if apply:
                patch = {
                    **MANDIR_TENANT_PATCH,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": "repair_mandir_tenant_entitlements",
                }
                if renamed_to:
                    patch["display_name"] = renamed_to
                await tenants.update_one({"tenant_id": tenant_id}, {"$set": patch})
                print("  updated")
            else:
                print("  dry-run only")
    finally:
        await close_mongo()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Repair known MandirMitra temple tenants to TEMPLE entitlements, "
            "including approved one-time display-name renames."
        )
    )
    parser.add_argument("--apply", action="store_true", help="Apply updates. Without this flag the script only prints changes.")
    args = parser.parse_args()
    asyncio.run(repair_mandir_tenants(apply=args.apply))


if __name__ == "__main__":
    main()
