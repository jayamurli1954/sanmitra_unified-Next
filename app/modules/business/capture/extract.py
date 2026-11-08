"""Extraction orchestrator: pick a backend and normalize its result.

The pipeline downstream (validators, scoring, routing) is engine-agnostic — it
only reads ``fields`` / ``field_confidences`` / ``extracted`` from the dict below,
so swapping or adding an OCR engine never touches it.
"""
from __future__ import annotations

from typing import Any

# Re-exported for scoring.py (kept stable for imports).
from app.modules.business.capture.backends.base import PageImage, REQUIRED_FIELDS  # noqa: F401
from app.modules.business.capture.backends.registry import select_backend


async def extract_document(
    *,
    tenant_id: str,
    pages: list[PageImage],
    user_id: str | None = None,
) -> dict[str, Any]:
    backend = select_backend()
    result = await backend.extract(tenant_id=tenant_id, pages=pages, user_id=user_id)
    result.setdefault(
        "advisory", "AI/OCR-extracted fields are drafts for human review, never auto-filed."
    )
    return result
