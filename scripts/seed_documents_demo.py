#!/usr/bin/env python3
"""
LOCAL / DEMO ONLY — enable OfficeMitra Documents on the MIS manufacturing demo tenant.

Hard-locked tenant: demo-mfg-mis
Refuses: demo-mitrabooks-business and every other tenant id.

This script never posts MitraBooks journals and never mutates CA document status
from OfficeMitra. It only:
  - adds office_ai.documents and office_ai.documents.requests on demo-mfg-mis
  - creates one staff CA document via the MitraBooks ca_clients service
  - optionally links an existing Review note (OfficeMitra Mongo)
  - raises one staff missing-document task for a type not on the queue (ADR-017)

Prereq:
  python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
  python scripts/seed_review_demo.py --run-smoke   (needed for --run-smoke link)

Usage:
  python scripts/seed_documents_demo.py --flags-only
  python scripts/seed_documents_demo.py --run-smoke
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
from app.modules.office_ai.connectors.mitrabooks_connector import CA_QUEUE_APP_KEY
from app.modules.office_ai.models import ensure_indexes
from app.modules.office_ai.services import documents_service, review_store

DOCUMENTS_FLAG = "office_ai.documents"
REQUESTS_FLAG = "office_ai.documents.requests"
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


def allowed_documents_demo_tenant_id() -> str:
    mod = _load_mis_seed_module()
    return str(mod.DEMO_TENANT_ID)


def assert_allowed_documents_demo_tenant(tenant_id: str) -> str:
    key = str(tenant_id or "").strip().lower()
    allowed = allowed_documents_demo_tenant_id().strip().lower()
    if not key:
        raise SystemExit("tenant_id is required")
    if key in BLOCKED_TENANT_IDS:
        raise SystemExit(
            f"Refusing tenant {key}: Documents must not be enabled on the live ERP demo tenant."
        )
    if key != allowed:
        raise SystemExit(
            f"Refusing tenant {key}: Documents demo smoke is locked to {allowed} only."
        )
    return key


async def _apply_documents_entitlements(tenant_id: str) -> list[str]:
    tenants = get_collection(TENANTS_COLLECTION)
    doc = await tenants.find_one({"tenant_id": tenant_id})
    if not doc:
        raise SystemExit(
            f"Tenant {tenant_id} not found. Run scripts/seed_mis_demo_firm.py first."
        )
    modules = [str(m).strip().lower() for m in (doc.get("enabled_modules") or []) if str(m).strip()]
    if "office_ai" not in modules:
        modules.append("office_ai")
    if "business" not in modules:
        modules.append("business")
    if DOCUMENTS_FLAG not in modules:
        modules.append(DOCUMENTS_FLAG)
    if REQUESTS_FLAG not in modules:
        modules.append(REQUESTS_FLAG)
    await tenants.update_one(
        {"tenant_id": tenant_id},
        {
            "$set": {
                "enabled_modules": modules,
                "updated_at": datetime.now(timezone.utc),
                "updated_by": "seed-documents-demo",
                "documents_demo": True,
            }
        },
    )
    return modules


async def _ensure_demo_ca_document(*, tenant_id: str) -> dict[str, Any]:
    # Import business.service first to avoid ca_clients ↔ service circular import under scripts.
    import app.modules.business.service  # noqa: F401
    from app.modules.business.schemas import CaDocumentCreateRequest
    from app.modules.business.services import ca_clients

    existing = await ca_clients.list_ca_document_metadata(
        tenant_id=tenant_id,
        app_key=CA_QUEUE_APP_KEY,
        accounting_entity_id="primary",
        limit=20,
    )
    for row in existing.get("items") or []:
        if str(row.get("period") or "") == DEMO_PERIOD and str(row.get("document_type") or "") == "bank_statement":
            return row
    payload = CaDocumentCreateRequest(
        client_name="Demo MFG MIS",
        document_type="bank_statement",
        period=DEMO_PERIOD,
        notes="Seeded for OfficeMitra Documents package smoke (ADR-016).",
        accounting_entity_id="primary",
        client_access_enabled=False,
    )
    return await ca_clients.create_ca_document_metadata(
        tenant_id=tenant_id,
        app_key=CA_QUEUE_APP_KEY,
        accounting_entity_id="primary",
        created_by="seed-documents-demo",
        payload=payload,
    )


async def _run_in_process_smoke(*, tenant_id: str) -> dict[str, Any]:
    await ensure_indexes()
    document = await _ensure_demo_ca_document(tenant_id=tenant_id)
    engagements = await review_store.list_engagements(tenant_id=tenant_id, limit=20)
    if not engagements:
        raise SystemExit("No Review engagement. Run scripts/seed_review_demo.py --run-smoke first.")
    engagement = engagements[0]
    notes = await review_store.list_notes(tenant_id=tenant_id, engagement_id=str(engagement["id"]))
    if not notes:
        raise SystemExit("No Review notes. Run scripts/seed_review_demo.py --run-smoke first.")
    tenant = await get_collection(TENANTS_COLLECTION).find_one({"tenant_id": tenant_id})
    linked = await documents_service.link_note(
        tenant_id=tenant_id,
        tenant=tenant or {},
        user={"sub": "seed-documents-demo"},
        note_id=str(notes[0]["id"]),
        document_id=str(document["document_id"]),
    )
    queue = await documents_service.list_queue(
        tenant_id=tenant_id,
        tenant=tenant or {},
        engagement_id=str(engagement["id"]),
    )
    gaps = await documents_service.gap_report(
        tenant_id=tenant_id,
        tenant=tenant or {},
        engagement_id=str(engagement["id"]),
    )
    request = await documents_service.create_staff_request(
        tenant_id=tenant_id,
        tenant=tenant or {},
        user={"sub": "seed-documents-demo"},
        document_type="gst_returns",
        engagement_id=str(engagement["id"]),
    )
    return {
        "document_id": document.get("document_id"),
        "note_id": notes[0]["id"],
        "linked": linked["item"].get("ca_document_id"),
        "queue_count": queue.get("count"),
        "queue_enabled": queue.get("enabled"),
        "missing_count": gaps.get("missing_count"),
        "request_created": request.get("created"),
        "request_task_id": (request.get("item") or {}).get("id"),
        "client_email": request.get("client_email"),
    }


async def _async_main(args: argparse.Namespace) -> int:
    tenant_id = assert_allowed_documents_demo_tenant(args.tenant_id or allowed_documents_demo_tenant_id())
    await init_mongo()
    try:
        modules = await _apply_documents_entitlements(tenant_id)
        print(f"Documents flags on {tenant_id}: {DOCUMENTS_FLAG in modules}, requests={REQUESTS_FLAG in modules}")
        if args.flags_only:
            return 0
        result = await _run_in_process_smoke(tenant_id=tenant_id)
        print("Documents smoke:", result)
        return 0
    finally:
        await close_mongo()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed OfficeMitra Documents on demo-mfg-mis only.")
    parser.add_argument("--tenant-id", default="", help="Must be demo-mfg-mis if set.")
    parser.add_argument("--flags-only", action="store_true")
    parser.add_argument("--run-smoke", action="store_true")
    args = parser.parse_args()
    if not args.flags_only and not args.run_smoke:
        parser.error("pass --flags-only or --run-smoke")
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
