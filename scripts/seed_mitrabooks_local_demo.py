from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.accounting.models.base import Base
from app.accounting.service import initialize_default_chart_of_accounts
from app.core.users.service import ensure_demo_mitrabooks_user
from app.db.mongo import close_mongo, init_mongo
from app.db.mongo import get_collection
from app.db.postgres import close_postgres, create_postgres_tables, get_session_factory, init_postgres
from app.modules.business import seed as business_seed
from app.modules.business.service import CA_DOCUMENTS_COLLECTION
from app.modules.business.service import ensure_business_indexes


CA_DEMO_FIRMS: tuple[dict[str, Any], ...] = (
    {
        "tenant_id": "demo-ca-practice-alpha",
        "email": "alpha.ca@sanmitra.local",
        "full_name": "Alpha CA Practice Admin",
        "display_name": "Alpha & Co Chartered Accountants",
        "documents": [
            {
                "document_id": "alpha-bank-may-2026",
                "client_name": "Jayam Publications",
                "document_type": "Bank statement",
                "period": "May 2026",
                "status": "under_review",
                "assigned_to": "Staff A",
                "client_owner": "Partner Alpha",
                "priority": "high",
                "due_date": "2026-06-20",
                "compliance_area": "GST",
                "client_access_enabled": True,
                "original_file_name": "jayam-bank-may-2026.pdf",
                "next_action": "Review support and raise query if needed",
                "posting_reference": None,
                "notes": "Demo queue item for bank reconciliation review.",
            },
            {
                "document_id": "alpha-tds-q1-2026",
                "client_name": "Kartik Enterprises",
                "document_type": "TDS file",
                "period": "Q1 2026-27",
                "status": "query_raised",
                "assigned_to": "Staff B",
                "client_owner": "Partner Alpha",
                "priority": "urgent",
                "due_date": "2026-06-25",
                "compliance_area": "TDS",
                "client_access_enabled": True,
                "original_file_name": "kartik-tds-q1.xlsx",
                "next_action": "Await client clarification",
                "posting_reference": None,
                "notes": "Demo query: challan confirmation missing.",
            },
        ],
    },
    {
        "tenant_id": "demo-ca-practice-beta",
        "email": "beta.books@sanmitra.local",
        "full_name": "Beta Bookkeeping Admin",
        "display_name": "Beta Books & Tax Services",
        "documents": [
            {
                "document_id": "beta-sales-may-2026",
                "client_name": "Stellar Logistics",
                "document_type": "Sales invoices",
                "period": "May 2026",
                "status": "reviewed",
                "assigned_to": "Reviewer B",
                "client_owner": "Manager Beta",
                "priority": "normal",
                "due_date": "2026-06-22",
                "compliance_area": "Bookkeeping",
                "client_access_enabled": False,
                "original_file_name": "stellar-sales-may.zip",
                "next_action": "Ready for voucher or return posting",
                "posting_reference": None,
                "notes": "Demo item ready for posting review.",
            },
            {
                "document_id": "beta-gst-may-2026",
                "client_name": "Power & Light Corp",
                "document_type": "GST return",
                "period": "May 2026",
                "status": "uploaded",
                "assigned_to": "Reviewer C",
                "client_owner": "Manager Beta",
                "priority": "high",
                "due_date": "2026-06-18",
                "compliance_area": "GST",
                "client_access_enabled": True,
                "original_file_name": "plc-gstr1-may.json",
                "next_action": "Classify document and assign reviewer",
                "posting_reference": None,
                "notes": "Demo GST return file awaiting classification.",
            },
        ],
    },
    {
        "tenant_id": "demo-ca-practice-gamma",
        "email": "gamma.audit@sanmitra.local",
        "full_name": "Gamma Audit Admin",
        "display_name": "Gamma Audit Associates",
        "documents": [
            {
                "document_id": "gamma-audit-fy-2026",
                "client_name": "South City Foods",
                "document_type": "Supporting document",
                "period": "FY 2026-27",
                "status": "uploaded",
                "assigned_to": "Audit Staff",
                "client_owner": "Partner Gamma",
                "priority": "normal",
                "due_date": "2026-06-30",
                "compliance_area": "Audit",
                "client_access_enabled": False,
                "original_file_name": "south-city-audit-support.zip",
                "next_action": "Classify document and assign reviewer",
                "posting_reference": None,
                "notes": "Demo statutory audit support pack.",
            },
            {
                "document_id": "gamma-roc-forms-2026",
                "client_name": "Nandi Software LLP",
                "document_type": "Supporting document",
                "period": "FY 2026-27",
                "status": "posted",
                "assigned_to": "Audit Staff",
                "client_owner": "Partner Gamma",
                "priority": "low",
                "due_date": "2026-07-10",
                "compliance_area": "ROC",
                "client_access_enabled": True,
                "original_file_name": "nandi-roc-forms.pdf",
                "next_action": "Linked to posted voucher or return reference",
                "posting_reference": "DEMO-ROC-2026",
                "notes": "Demo completed compliance item.",
            },
        ],
    },
)


def _admin_emails(args: argparse.Namespace) -> list[str]:
    emails = [args.email]
    if args.all_admin_aliases:
        from app.config import get_settings

        settings = get_settings()
        emails.extend([settings.DEMO_MITRABOOKS_ADMIN_EMAIL, *settings.DEMO_MITRABOOKS_ADMIN_ALIAS_EMAILS])

    normalized: list[str] = []
    for email in emails:
        value = str(email or "").strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _generate_ca_demo_password(firm: dict[str, Any]) -> str:
    firm_code = str(firm["tenant_id"]).rsplit("-", maxsplit=1)[-1].title()
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(10))
    return f"DemoCA-{firm_code}-{random_part}9!"


def _ca_demo_passwords(*, shared_password: str | None, generate_passwords: bool) -> dict[str, str]:
    if generate_passwords:
        return {firm["tenant_id"]: _generate_ca_demo_password(firm) for firm in CA_DEMO_FIRMS}
    return {firm["tenant_id"]: shared_password or "" for firm in CA_DEMO_FIRMS}


async def _seed_ca_demo_documents(*, tenant_id: str, created_by: str, documents: list[dict[str, Any]]) -> int:
    collection = get_collection(CA_DOCUMENTS_COLLECTION)
    created = 0
    now = datetime.now(timezone.utc)

    for doc in documents:
        record = {
            **doc,
            "tenant_id": tenant_id,
            "app_key": "mitrabooks",
            "accounting_entity_id": "primary",
            "created_by": created_by,
            "updated_by": created_by,
        }
        result = await collection.update_one(
            {"tenant_id": tenant_id, "app_key": "mitrabooks", "document_id": doc["document_id"]},
            {
                "$setOnInsert": {
                    "created_at": now,
                },
                "$set": {
                    **record,
                    "updated_at": now,
                },
            },
            upsert=True,
        )
        created += int(getattr(result, "upserted_id", None) is not None)
    return created


async def seed_demo(args: argparse.Namespace) -> None:
    password = args.password
    if args.use_env_password:
        password = os.getenv("DEMO_MITRABOOKS_ADMIN_PASSWORD", "")
    generated_ca_passwords = bool(args.ca_demo_firms and args.generate_ca_demo_passwords)
    if not password and not generated_ca_passwords:
        print("MitraBooks demo seed failed: DEMO_MITRABOOKS_ADMIN_PASSWORD is not set.")
        raise SystemExit("password is required; pass --password or set DEMO_MITRABOOKS_ADMIN_PASSWORD with --use-env-password")

    emails = _admin_emails(args)
    if not emails:
        raise SystemExit("at least one valid admin email is required")

    await init_mongo()
    try:
        seeded_users = []
        seeded_ca_documents = 0
        ca_passwords = _ca_demo_passwords(shared_password=password, generate_passwords=generated_ca_passwords)
        if args.ca_demo_firms:
            for firm in CA_DEMO_FIRMS:
                user = await ensure_demo_mitrabooks_user(
                    email=firm["email"],
                    password=ca_passwords[firm["tenant_id"]],
                    full_name=firm["full_name"],
                    tenant_id=firm["tenant_id"],
                    display_name=firm["display_name"],
                )
                if user is None:
                    raise SystemExit(f"email {firm['email']} must be valid and password must be at least 6 characters")
                seeded_users.append(user)
                seeded_ca_documents += await _seed_ca_demo_documents(
                    tenant_id=firm["tenant_id"],
                    created_by=firm["email"],
                    documents=firm["documents"],
                )
        else:
            for email in emails:
                user = await ensure_demo_mitrabooks_user(
                    email=email,
                    password=password,
                    full_name=args.full_name,
                    tenant_id=args.tenant_id,
                )
                if user is None:
                    raise SystemExit(f"email {email} must be valid and password must be at least 6 characters")
                seeded_users.append(user)
        await ensure_business_indexes()
    finally:
        await close_mongo()

    if args.skip_coa:
        print(
            "Seeded MitraBooks demo users "
            f"{len(seeded_users)} for "
            f"{'CA demo firms' if args.ca_demo_firms else 'tenant ' + args.tenant_id}; "
            f"CA documents created={seeded_ca_documents}; skipped chart of accounts."
        )
        if args.ca_demo_firms:
            print("Demo CA logins:")
            for firm in CA_DEMO_FIRMS:
                password_label = ca_passwords[firm["tenant_id"]] if generated_ca_passwords else "<password supplied to script>"
                print(f"- {firm['display_name']}: {firm['email']} / {password_label}")
        return

    await init_postgres()
    if args.ca_demo_firms:
        await init_mongo()
    try:
        await create_postgres_tables(Base.metadata)
        session_factory = get_session_factory()
        async with session_factory() as session:
            if args.ca_demo_firms:
                ca_seed_results = []
                for firm in CA_DEMO_FIRMS:
                    ca_seed_results.append(
                        await business_seed.ensure_mitrabooks_e2e_seed(
                            session,
                            tenant_id=firm["tenant_id"],
                            created_by=firm["email"],
                        )
                    )
                result = {
                    "accounts_created": sum(item["chart_of_accounts"]["accounts_created"] for item in ca_seed_results),
                    "accounts_existing": sum(item["chart_of_accounts"]["accounts_existing"] for item in ca_seed_results),
                    "total_accounts": sum(item["chart_of_accounts"]["total_accounts"] for item in ca_seed_results),
                }
            else:
                result = await initialize_default_chart_of_accounts(
                    session,
                    tenant_id=args.tenant_id,
                    app_key="mitrabooks",
                    accounting_entity_id="primary",
                    organization_type="BUSINESS",
                )
    finally:
        if args.ca_demo_firms:
            await close_mongo()
        await close_postgres()

    print(
        "Seeded MitraBooks demo users "
        f"{len(seeded_users)} for "
        f"{'CA demo firms' if args.ca_demo_firms else 'tenant ' + args.tenant_id}; "
        f"CA documents created={seeded_ca_documents}; "
        f"chart accounts created={result['accounts_created']} "
        f"existing={result['accounts_existing']} total={result['total_accounts']}."
    )
    if args.ca_demo_firms:
        print("Demo CA logins:")
        for firm in CA_DEMO_FIRMS:
            password_label = ca_passwords[firm["tenant_id"]] if generated_ca_passwords else "<password supplied to script>"
            print(f"- {firm['display_name']}: {firm['email']} / {password_label}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a local MitraBooks BUSINESS demo tenant and admin user.")
    parser.add_argument("--tenant-id", default="demo-mitrabooks-business")
    parser.add_argument("--email", default="businessadmin@sanmitra.local")
    parser.add_argument("--full-name", default="Demo MitraBooks Admin")
    parser.add_argument("--password")
    parser.add_argument(
        "--use-env-password",
        action="store_true",
        help="Read password from DEMO_MITRABOOKS_ADMIN_PASSWORD instead of a command argument.",
    )
    parser.add_argument(
        "--all-admin-aliases",
        action="store_true",
        help="Seed the primary MitraBooks admin email and configured alias emails.",
    )
    parser.add_argument(
        "--ca-demo-firms",
        action="store_true",
        help="Seed three dummy CA/bookkeeper demo tenants, login users, report-ready books, and CA document queues.",
    )
    parser.add_argument(
        "--generate-ca-demo-passwords",
        action="store_true",
        help="Generate and print a distinct random password for each CA demo firm.",
    )
    parser.add_argument("--skip-coa", action="store_true", help="Only seed Mongo tenant/user data; skip PostgreSQL COA.")
    args = parser.parse_args()
    asyncio.run(seed_demo(args))


if __name__ == "__main__":
    main()
