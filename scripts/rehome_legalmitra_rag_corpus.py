"""Duplicate LegalMitra RAG rows from the temple seed tenant onto the LEGAL demo tenant.

This is not copy-in-place: source rows are left unchanged until ``--purge-source``.
New document_id / chunk_id values are issued for the destination tenant.

  python scripts/rehome_legalmitra_rag_corpus.py --dry-run
  python scripts/rehome_legalmitra_rag_corpus.py
  python scripts/rehome_legalmitra_rag_corpus.py --purge-source --confirm-purge-source

Do not convert seed-tenant-1 to LEGAL. MandirMitra temple data is not touched.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from uuid import uuid4

sys.path.append(os.getcwd())

from app.core.tenants.service import ensure_tenant_exists, get_tenant
from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.legal_compat.tenancy import (
    LEGALMITRA_APP_KEY,
    TEMPLE_SEED_TENANT_ID,
    legalmitra_corpus_tenant_id,
    require_legalmitra_ingest_tenant,
)
from app.modules.rag.service import RAG_CHUNKS_COLLECTION, RAG_DOCUMENTS_COLLECTION

LEGAL_STATUTE_SECTIONS_COLLECTION = "legal_statute_sections"


def _strip_id(doc: dict) -> dict:
    payload = dict(doc)
    payload.pop("_id", None)
    return payload


async def _count(collection, tenant_id: str) -> int:
    return await collection.count_documents(
        {"tenant_id": tenant_id, "app_key": LEGALMITRA_APP_KEY}
    )


async def _rehome_documents(*, source: str, dest: str, dry_run: bool) -> tuple[int, int]:
    documents = get_collection(RAG_DOCUMENTS_COLLECTION)
    chunks = get_collection(RAG_CHUNKS_COLLECTION)
    copied = 0
    skipped = 0
    cursor = documents.find({"tenant_id": source, "app_key": LEGALMITRA_APP_KEY})
    async for doc in cursor:
        external_id = str(doc.get("external_id") or "").strip()
        if external_id:
            existing = await documents.find_one(
                {
                    "tenant_id": dest,
                    "app_key": LEGALMITRA_APP_KEY,
                    "external_id": external_id,
                }
            )
            if existing:
                skipped += 1
                continue
        if dry_run:
            copied += 1
            continue
        old_document_id = str(doc.get("document_id") or "").strip()
        new_document_id = str(uuid4())
        payload = _strip_id(doc)
        payload["tenant_id"] = dest
        payload["document_id"] = new_document_id
        await documents.insert_one(payload)
        if old_document_id:
            chunk_cursor = chunks.find(
                {
                    "tenant_id": source,
                    "app_key": LEGALMITRA_APP_KEY,
                    "document_id": old_document_id,
                }
            )
            batch: list[dict] = []
            async for chunk in chunk_cursor:
                item = _strip_id(chunk)
                item["tenant_id"] = dest
                item["document_id"] = new_document_id
                item["chunk_id"] = str(uuid4())
                batch.append(item)
            if batch:
                await chunks.insert_many(batch)
        copied += 1
    return copied, skipped


async def _rehome_statute_sections(*, source: str, dest: str, dry_run: bool) -> tuple[int, int]:
    sections = get_collection(LEGAL_STATUTE_SECTIONS_COLLECTION)
    copied = 0
    skipped = 0
    cursor = sections.find({"tenant_id": source, "app_key": LEGALMITRA_APP_KEY})
    async def _exists(doc: dict) -> bool:
        act_key = str(doc.get("act_key") or "").strip()
        section = str(doc.get("section") or "").strip()
        if act_key and section:
            found = await sections.find_one(
                {
                    "tenant_id": dest,
                    "app_key": LEGALMITRA_APP_KEY,
                    "act_key": act_key,
                    "section": section,
                }
            )
            return found is not None
        external_id = str(doc.get("external_id") or "").strip()
        if not external_id:
            return False
        found = await sections.find_one(
            {
                "tenant_id": dest,
                "app_key": LEGALMITRA_APP_KEY,
                "external_id": external_id,
            }
        )
        return found is not None

    async for doc in cursor:
        if await _exists(doc):
            skipped += 1
            continue
        if dry_run:
            copied += 1
            continue
        payload = _strip_id(doc)
        payload["tenant_id"] = dest
        await sections.insert_one(payload)
        copied += 1
    return copied, skipped


async def _purge_source(source: str) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for name in (RAG_DOCUMENTS_COLLECTION, RAG_CHUNKS_COLLECTION, LEGAL_STATUTE_SECTIONS_COLLECTION):
        collection = get_collection(name)
        result = await collection.delete_many(
            {"tenant_id": source, "app_key": LEGALMITRA_APP_KEY}
        )
        deleted[name] = int(result.deleted_count or 0)
    return deleted


async def _run(*, source: str, dest: str, dry_run: bool, purge_source: bool) -> int:
    dest = require_legalmitra_ingest_tenant(dest)
    if source != TEMPLE_SEED_TENANT_ID:
        raise SystemExit(f"source must be {TEMPLE_SEED_TENANT_ID} (temple seed holding stray LegalMitra RAG)")
    if dest == source:
        raise SystemExit("destination tenant must differ from the temple seed")

    await init_mongo()
    try:
        existing = await get_tenant(dest)
        if existing is None:
            await ensure_tenant_exists(
                dest,
                display_name="Demo Legal Firm",
                organization_type="LEGAL",
                enabled_modules=["legal", "rag", "compliance", "audit"],
                app_keys=[LEGALMITRA_APP_KEY],
                subscription_plan="pro",
                created_by="rehome-legalmitra-rag",
            )
        elif str(existing.get("organization_type") or "").strip().upper() != "LEGAL":
            raise SystemExit(
                f"destination tenant {dest} is {existing.get('organization_type')}, not LEGAL"
            )
        documents = get_collection(RAG_DOCUMENTS_COLLECTION)
        chunks = get_collection(RAG_CHUNKS_COLLECTION)
        sections = get_collection(LEGAL_STATUTE_SECTIONS_COLLECTION)
        print(
            "source docs/chunks/sections",
            await _count(documents, source),
            await _count(chunks, source),
            await _count(sections, source),
        )
        print(
            "dest docs/chunks/sections",
            await _count(documents, dest),
            await _count(chunks, dest),
            await _count(sections, dest),
        )
        docs_copied, docs_skipped = await _rehome_documents(
            source=source, dest=dest, dry_run=dry_run
        )
        sections_copied, sections_skipped = await _rehome_statute_sections(
            source=source, dest=dest, dry_run=dry_run
        )
        action = "DRY-RUN" if dry_run else "COPIED"
        print(
            f"{action} documents={docs_copied} skipped={docs_skipped} "
            f"statute_sections={sections_copied} skipped_sections={sections_skipped}"
        )
        if purge_source:
            if dry_run:
                print("DRY-RUN skip purge")
            else:
                deleted = await _purge_source(source)
                print("purged source legalmitra RAG", deleted)
        print(
            "after dest docs/chunks/sections",
            await _count(documents, dest),
            await _count(chunks, dest),
            await _count(sections, dest),
        )
        return 0
    finally:
        await close_mongo()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Duplicate LegalMitra RAG from the temple seed onto DEMO_LEGAL_TENANT_ID."
    )
    parser.add_argument("--source-tenant", default=TEMPLE_SEED_TENANT_ID)
    parser.add_argument(
        "--dest-tenant",
        default="",
        help="Destination LEGAL tenant (default DEMO_LEGAL_TENANT_ID / LEGAL_INGEST_TENANT_ID).",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--purge-source",
        action="store_true",
        help="After copy, delete app_key=legalmitra RAG rows from the temple seed only.",
    )
    parser.add_argument(
        "--confirm-purge-source",
        action="store_true",
        help="Required together with --purge-source.",
    )
    args = parser.parse_args()
    dest = str(args.dest_tenant or "").strip() or legalmitra_corpus_tenant_id()
    if args.purge_source and not args.confirm_purge_source:
        raise SystemExit("--purge-source requires --confirm-purge-source")
    raise SystemExit(
        asyncio.run(
            _run(
                source=str(args.source_tenant or "").strip(),
                dest=dest,
                dry_run=bool(args.dry_run),
                purge_source=bool(args.purge_source),
            )
        )
    )


if __name__ == "__main__":
    main()
