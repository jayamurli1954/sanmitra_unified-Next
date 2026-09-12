"""LOCAL-ONLY helper: provision + enable the enterprise add-ons (HR, Cost-Centre,
Manufacturing) for a tenant so you can test them on your machine.

Provisioning is normally a platform-owner (super_admin) action via the
/platform-owner API and the tenant-admin enable toggles; this script just flips
the same flags directly against your local Mongo so you do not have to do the
auth dance while testing. DO NOT use against any shared/deployed database.

Usage:
    python scripts/provision_addons_local.py
    python scripts/provision_addons_local.py --tenant demo-mitrabooks-business --entity primary
"""
import argparse
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from app.db.mongo import init_mongo, close_mongo


async def run(tenant_id: str, app_key: str, entity: str) -> None:
    from app.core.tenants.service import set_addon_available, set_hr_addon_available
    from app.modules.business.service import set_hr_enabled, set_module_enabled

    actor = "local-provision-script"
    await init_mongo()
    try:
        # 1. Platform-owner provisioning (core_tenants.*_addon_available).
        await set_hr_addon_available(tenant_id=tenant_id, available=True, updated_by=actor)
        await set_addon_available(tenant_id=tenant_id, flag="cost_centre_addon_available", available=True, updated_by=actor)
        await set_addon_available(tenant_id=tenant_id, flag="manufacturing_addon_available", available=True, updated_by=actor)

        # 2. Tenant-admin enable toggles (InvoiceSettings.*_enabled).
        await set_hr_enabled(tenant_id=tenant_id, app_key=app_key, accounting_entity_id=entity, enabled=True, updated_by=actor)
        await set_module_enabled(tenant_id=tenant_id, app_key=app_key, accounting_entity_id=entity, flag="cost_centre_enabled", enabled=True, updated_by=actor)
        await set_module_enabled(tenant_id=tenant_id, app_key=app_key, accounting_entity_id=entity, flag="manufacturing_enabled", enabled=True, updated_by=actor)

        print(f"Provisioned + enabled HR, Cost-Centre and Manufacturing for "
              f"tenant={tenant_id} app_key={app_key} entity={entity}.")
        print("Hard-refresh the MitraBooks tab (Ctrl+Shift+R) — HR & Payroll and "
              "Manufacturing should now be active.")
    except KeyError:
        print(f"Tenant '{tenant_id}' not found. Seed it first "
              f"(scripts/seed_mitrabooks_local_demo.py) or pass --tenant.")
    finally:
        await close_mongo()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision + enable enterprise add-ons locally.")
    parser.add_argument("--tenant", default="demo-mitrabooks-business")
    parser.add_argument("--app-key", default="mitrabooks")
    parser.add_argument("--entity", default="primary")
    args = parser.parse_args()
    asyncio.run(run(args.tenant, args.app_key, args.entity))
