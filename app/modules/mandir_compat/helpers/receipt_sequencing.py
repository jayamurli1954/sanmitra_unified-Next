"""MandirMitra receipt and journal entry sequence helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Important for tests:
- Constants and get_collection are resolved via `mandir_router.<name>` so
  monkeypatching `app.modules.mandir_compat.router.<name>` continues to work.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.modules.mandir_compat import router as mandir_router

def _format_mandir_receipt_number(prefix: str, sequence: int) -> str:
    normalized_prefix = str(prefix or "").strip().upper()
    if normalized_prefix not in {"DON", "SEV"}:
        raise ValueError(f"Unsupported MandirMitra receipt prefix: {prefix!r}")
    if int(sequence) < 1:
        raise ValueError("Receipt sequence must be positive")
    return f"{normalized_prefix}-{int(sequence):0{mandir_router._MANDIR_RECEIPT_WIDTH}d}"


def _format_mandir_sequence_number(prefix: str, sequence: int) -> str:
    normalized_prefix = str(prefix or "").strip().upper()
    if not normalized_prefix:
        raise ValueError("Sequence prefix is required")
    if int(sequence) < 1:
        raise ValueError("Sequence must be positive")
    return f"{normalized_prefix}-{int(sequence):0{mandir_router._MANDIR_RECEIPT_WIDTH}d}"


async def _next_receipt_number(
    *,
    tenant_id: str,
    app_key: str,
    receipt_kind: str,
    receipt_date: Any = None,
) -> str:
    prefix = mandir_router._MANDIR_RECEIPT_PREFIX_BY_KIND.get(str(receipt_kind or "").strip().lower())
    if not prefix:
        raise ValueError(f"Unsupported MandirMitra receipt kind: {receipt_kind!r}")

    now = datetime.now(timezone.utc).isoformat()
    counter_id = f"{app_key}:{tenant_id}:receipt:{prefix}"
    counters = mandir_router.get_collection(mandir_router._MANDIR_COUNTERS_COLLECTION)
    result = await counters.find_one_and_update(
        {"_id": counter_id},
        {
            "$inc": {"seq": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "app_key": app_key,
                "tenant_id": tenant_id,
                "prefix": prefix,
                "kind": receipt_kind,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    sequence = int((result or {}).get("seq") or 1)
    return _format_mandir_receipt_number(prefix, sequence)


async def _next_journal_entry_number(*, tenant_id: str, app_key: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    counter_id = f"{app_key}:{tenant_id}:journal-entry:{mandir_router._MANDIR_JOURNAL_ENTRY_PREFIX}"
    counters = mandir_router.get_collection(mandir_router._MANDIR_COUNTERS_COLLECTION)
    result = await counters.find_one_and_update(
        {"_id": counter_id},
        {
            "$inc": {"seq": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "app_key": app_key,
                "tenant_id": tenant_id,
                "prefix": mandir_router._MANDIR_JOURNAL_ENTRY_PREFIX,
                "kind": "journal_entry",
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    sequence = int((result or {}).get("seq") or 1)
    return _format_mandir_sequence_number(mandir_router._MANDIR_JOURNAL_ENTRY_PREFIX, sequence)




