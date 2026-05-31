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
from app.core.users.service import ensure_demo_mitrabooks_user
from app.db.mongo import close_mongo, init_mongo
from app.db.postgres import close_postgres, create_postgres_tables, get_session_factory, init_postgres
from app.modules.business.service import ensure_business_indexes


async def seed_demo(args: argparse.Namespace) -> None:
    await init_mongo()
    try:
        user = await ensure_demo_mitrabooks_user(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            tenant_id=args.tenant_id,
        )
        if user is None:
            raise SystemExit("email must be valid and password must be at least 6 characters")
        await ensure_business_indexes()
    finally:
        await close_mongo()

    if args.skip_coa:
        print(f"Seeded MitraBooks demo user {args.email} for tenant {args.tenant_id}; skipped chart of accounts.")
        return

    await init_postgres()
    try:
        await create_postgres_tables(Base.metadata)
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await initialize_default_chart_of_accounts(
                session,
                tenant_id=args.tenant_id,
                app_key="mitrabooks",
                accounting_entity_id="primary",
                organization_type="BUSINESS",
            )
    finally:
        await close_postgres()

    print(
        "Seeded MitraBooks demo user "
        f"{args.email} for tenant {args.tenant_id}; "
        f"chart accounts created={result['accounts_created']} "
        f"existing={result['accounts_existing']} total={result['total_accounts']}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a local MitraBooks BUSINESS demo tenant and admin user.")
    parser.add_argument("--tenant-id", default="demo-mitrabooks-business")
    parser.add_argument("--email", default="businessadmin@sanmitra.local")
    parser.add_argument("--full-name", default="Demo MitraBooks Admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--skip-coa", action="store_true", help="Only seed Mongo tenant/user data; skip PostgreSQL COA.")
    args = parser.parse_args()
    asyncio.run(seed_demo(args))


if __name__ == "__main__":
    main()
