"""LegalMitra RAG auto-sync queue helpers (kept out of service.py for file-size ratchet)."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.db.mongo import get_collection

RAG_SYNC_QUEUE_COLLECTION = "rag_sync_queue"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def _query_hash(query: str) -> str:
    return hashlib.sha256(_normalize_query(query).encode("utf-8")).hexdigest()


async def ensure_legal_compat_indexes() -> None:
    queue = get_collection(RAG_SYNC_QUEUE_COLLECTION)
    await queue.create_index([("tenant_id", 1), ("app_key", 1), ("status", 1), ("created_at", -1)])
    await queue.create_index([("status", 1), ("updated_at", 1)])
    await queue.create_index(
        [("tenant_id", 1), ("app_key", 1), ("query_hash", 1), ("status", 1)],
        unique=True,
        partialFilterExpression={"status": "pending"},
    )


async def enqueue_auto_sync_query(*, tenant_id: str, app_key: str, query: str, reason: str) -> None:
    settings = get_settings()
    if not settings.RAG_AUTO_SYNC_ENABLED:
        return

    normalized_query = _normalize_query(query)
    if not normalized_query:
        return

    queue = get_collection(RAG_SYNC_QUEUE_COLLECTION)
    now = _now_utc()
    doc = {
        "job_id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "query": query.strip(),
        "normalized_query": normalized_query,
        "query_hash": _query_hash(query),
        "reason": reason,
        "status": "pending",
        "attempt_count": 0,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }

    await queue.update_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "query_hash": doc["query_hash"],
            "status": "pending",
        },
        {
            "$setOnInsert": doc,
            "$set": {"last_seen_at": now},
        },
        upsert=True,
    )


async def list_sync_queue(
    *, tenant_id: str, app_key: str, status: str = "pending", limit: int = 50
) -> list[dict[str, Any]]:
    queue = get_collection(RAG_SYNC_QUEUE_COLLECTION)
    status_value = (status or "pending").strip().lower()
    cursor = (
        queue.find({"tenant_id": tenant_id, "app_key": app_key, "status": status_value})
        .sort("updated_at", -1)
        .limit(limit)
    )

    items: list[dict[str, Any]] = []
    async for doc in cursor:
        items.append(
            {
                "job_id": str(doc.get("job_id") or ""),
                "query": str(doc.get("query") or ""),
                "reason": str(doc.get("reason") or ""),
                "status": str(doc.get("status") or "pending"),
                "attempt_count": int(doc.get("attempt_count") or 0),
                "last_error": doc.get("last_error"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }
        )

    return items
