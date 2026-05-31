from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.accounting.models.base import Base
from app.accounting.service import initialize_default_chart_of_accounts
from app.core.users.service import ensure_demo_gruhamitra_user
from app.db.mongo import close_mongo, init_mongo
from app.db.postgres import close_postgres, create_postgres_tables, get_session_factory, init_postgres
from app.modules.housing_compat.service import ensure_housing_compat_indexes


async def seed_demo(args: argparse.Namespace) -> None:
    await init_mongo()
    try:
        admin = await ensure_demo_gruhamitra_user(
            email=args.admin_email,
            password=args.admin_password,
            full_name=args.admin_full_name,
            tenant_id=args.tenant_id,
            role="tenant_admin",
        )
        if admin is None:
            raise SystemExit("admin email must be valid and admin password must be at least 8 characters")

        resident = None
        if args.resident_email and args.resident_password:
            resident = await ensure_demo_gruhamitra_user(
                email=args.resident_email,
                password=args.resident_password,
                full_name=args.resident_full_name,
                tenant_id=args.tenant_id,
                role="operator",
            )
            if resident is None:
                raise SystemExit("resident email must be valid and resident password must be at least 8 characters")

        await ensure_housing_compat_indexes()
    finally:
        await close_mongo()

    if args.skip_coa:
        print(f"Seeded GruhaMitra demo users for tenant {args.tenant_id}; skipped chart of accounts.")
        return

    await init_postgres()
    try:
        await create_postgres_tables(Base.metadata)
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await initialize_default_chart_of_accounts(
                session,
                tenant_id=args.tenant_id,
                app_key="gruhamitra",
                accounting_entity_id="primary",
                organization_type="HOUSING",
            )
    finally:
        await close_postgres()

    users = [args.admin_email]
    if resident:
        users.append(args.resident_email)
    print(
        "Seeded GruhaMitra demo users "
        f"{', '.join(users)} for tenant {args.tenant_id}; "
        f"chart accounts created={result['accounts_created']} "
        f"existing={result['accounts_existing']} total={result['total_accounts']}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a GruhaMitra HOUSING demo tenant and demo login users.")
    parser.add_argument("--tenant-id", default="gruhamitra-demo-society")
    parser.add_argument("--admin-email", default="demo.admin@gruhamitra.sanmitratech.in")
    parser.add_argument("--admin-full-name", default="GruhaMitra Demo Admin")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--resident-email", default="demo.resident@gruhamitra.sanmitratech.in")
    parser.add_argument("--resident-full-name", default="GruhaMitra Demo Resident")
    parser.add_argument("--resident-password", default="")
    parser.add_argument("--skip-coa", action="store_true", help="Only seed Mongo tenant/user data; skip PostgreSQL COA.")
    args = parser.parse_args()
    asyncio.run(seed_demo(args))


if __name__ == "__main__":
    main()
