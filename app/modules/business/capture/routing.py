"""Client (accounting entity) binding for a captured document.

The hard rule: a document is bound to exactly ONE client before it can draft or
post, and the client is resolved deterministically — never by an AI guess.

Resolution order:
  1. channel     — the upload/alias/number already selected a client (strongest).
  2. gstin       — the client's OWN GSTIN on the document maps to exactly one
                   client in the firm's master (used by auto-channels later).
  3. needs_client — anything else: a human must assign it; nothing proceeds.

Pure and injectable: the GSTIN lookup is passed in, so this module never reaches
into the client master directly and stays testable.
"""
from __future__ import annotations

from typing import Any, Callable

UNASSIGNED = "unassigned"


def _gstin_candidates(
    fields: dict[str, Any], lookup: Callable[[str], str | None]
) -> list[str]:
    seen: list[str] = []
    for key in ("buyer_gstin", "client_gstin", "vendor_gstin"):
        gstin = fields.get(key)
        if not gstin:
            continue
        entity = lookup(str(gstin).strip().upper())
        if entity and entity not in seen:
            seen.append(entity)
    return seen


def resolve_client_binding(
    *,
    provided_entity: str | None,
    fields: dict[str, Any] | None = None,
    client_gstin_lookup: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    entity = (provided_entity or "").strip()
    if entity and entity.lower() != UNASSIGNED:
        return {"accounting_entity_id": entity, "method": "channel", "candidates": []}

    if client_gstin_lookup is not None and fields:
        candidates = _gstin_candidates(fields, client_gstin_lookup)
        if len(candidates) == 1:
            return {"accounting_entity_id": candidates[0], "method": "gstin", "candidates": candidates}
        # Zero or multiple matches → do not guess.
        return {"accounting_entity_id": None, "method": "needs_client", "candidates": candidates}

    return {"accounting_entity_id": None, "method": "needs_client", "candidates": []}
