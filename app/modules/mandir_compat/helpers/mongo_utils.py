"""MandirMitra MongoDB document sanitization helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

def _sanitize_mongo_doc(doc: dict[str, Any]) -> dict[str, Any]:
    row = dict(doc or {})
    # ObjectId is not JSON serializable; hide Mongo internals from API clients.
    row.pop("_id", None)
    return row

