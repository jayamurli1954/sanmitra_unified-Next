"""Ingest Tier-1 constitutional doctrine/judgment seed JSON into LegalMitra RAG.

Dry-run (no Mongo writes):

  python scripts/ingest_legal_constitutional_seed.py --dry-run

Ingest into Mongo (requires local Mongo for this workspace):

  python scripts/ingest_legal_constitutional_seed.py

These records are curated summaries, not full judgments. They stay tenant-scoped
and advisory. Do not treat ingest as production enablement of a full case-law corpus.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from app.db.mongo import close_mongo, init_mongo
from app.modules.legal_compat.constitutional_seed import (
    iter_ingest_requests,
    validate_seed_package,
)
from app.modules.rag.service import ensure_rag_indexes, ingest_document

TENANT_ID = os.getenv("LEGAL_INGEST_TENANT_ID", "seed-tenant-1").strip() or "seed-tenant-1"
APP_KEY = os.getenv("LEGAL_INGEST_APP_KEY", "legalmitra").strip() or "legalmitra"
CREATED_BY = "constitutional-seed-ingest"


async def _ingest(*, tenant_id: str, app_key: str, dry_run: bool) -> int:
    problems = validate_seed_package()
    if problems:
        print("Seed package validation failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    payloads = list(iter_ingest_requests())
    if dry_run:
        for payload in payloads:
            print(
                f"DRY-RUN {payload.source_type} {payload.external_id}: "
                f"{payload.title} ({len(payload.content)} chars)"
            )
        print(f"OK dry-run: {len(payloads)} records")
        return 0

    await init_mongo()
    try:
        await ensure_rag_indexes()
        ingested = 0
        skipped = 0
        for payload in payloads:
            try:
                result = await ingest_document(
                    tenant_id=tenant_id,
                    app_key=app_key,
                    created_by=CREATED_BY,
                    payload=payload,
                )
            except ValueError as exc:
                if "external_id already exists" in str(exc):
                    print(f"EXISTS {payload.external_id}: {payload.title}")
                    skipped += 1
                    continue
                raise
            print(
                f"OK {payload.external_id}: {result['document_id']} "
                f"({result['chunk_count']} chunks)"
            )
            ingested += 1
        print(f"Done: ingested={ingested} skipped={skipped}")
        return 0
    finally:
        await close_mongo()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest LegalMitra Tier-1 constitutional seed JSON into RAG."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print records without writing to Mongo.",
    )
    parser.add_argument(
        "--tenant-id",
        default=TENANT_ID,
        help="Target tenant_id (default seed-tenant-1 or LEGAL_INGEST_TENANT_ID).",
    )
    parser.add_argument(
        "--app-key",
        default=APP_KEY,
        help="Target app_key (default legalmitra or LEGAL_INGEST_APP_KEY).",
    )
    args = parser.parse_args()
    if args.app_key.strip().lower() != "legalmitra":
        raise SystemExit("constitutional seed ingest is LegalMitra-only (app_key=legalmitra)")
    raise SystemExit(
        asyncio.run(
            _ingest(
                tenant_id=args.tenant_id.strip(),
                app_key="legalmitra",
                dry_run=bool(args.dry_run),
            )
        )
    )


if __name__ == "__main__":
    main()
