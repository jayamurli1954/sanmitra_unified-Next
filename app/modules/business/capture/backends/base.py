"""Extraction backend contract shared by every engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class PageImage:
    """One rendered page of the uploaded document, as raw image bytes.

    Both the OCR backends (via PIL) and the LLM-vision backend (via base64)
    consume these, so the service rasterizes once and every engine reuses it.
    """

    media_type: str  # image/png | image/jpeg | image/webp
    data: bytes


# The fields a draft needs before it can be auto-routed; also what scoring floors on.
REQUIRED_FIELDS = ("vendor_name", "total_amount", "invoice_date")


def empty_result(*, engine: str, error_code: str | None) -> dict[str, Any]:
    """Uniform 'nothing extracted' result → the item routes to human review."""
    return {
        "extracted": False,
        "document_type": "unknown",
        "fields": {},
        "field_confidences": {},
        "engine": engine,
        "provider": engine,
        "model": engine,
        "error_code": error_code,
        "telemetry_id": None,
    }


class ExtractionBackend(Protocol):
    name: str

    async def extract(
        self,
        *,
        tenant_id: str,
        pages: list[PageImage],
        user_id: str | None = None,
    ) -> dict[str, Any]: ...
