"""Select the extraction backend.

Default is ``ocr_rules`` (open-source, local, no key). A tenant/deployment can opt
into ``llm_vision`` via the ``CAPTURE_EXTRACTION_ENGINE`` setting. Read with a
getattr fallback so no config change is required for the default to work.
"""
from __future__ import annotations

from app.config import get_settings
from app.modules.business.capture.backends.base import ExtractionBackend
from app.modules.business.capture.backends.llm_vision import LlmVisionBackend
from app.modules.business.capture.backends.ocr_rules import OcrRulesBackend


def select_backend() -> ExtractionBackend:
    settings = get_settings()
    engine = str(getattr(settings, "CAPTURE_EXTRACTION_ENGINE", "ocr_rules") or "ocr_rules").strip().lower()
    if engine in {"llm", "llm_vision", "vision"}:
        return LlmVisionBackend()
    return OcrRulesBackend()
