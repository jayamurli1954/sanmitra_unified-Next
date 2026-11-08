"""LLM-vision extraction backend (optional booster).

Uses a vision-capable model through the OfficeMitra provider. The key is the
tenant's own (BYOK) or a local model — never developer-funded. Unavailable
provider → empty result, so the item falls back to human review.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from app.modules.business.capture.backends.base import PageImage, empty_result
from app.modules.office_ai.ai import get_ai_provider
from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.ai.provider_base import VisionImage
from app.modules.office_ai.ai.telemetry import record_telemetry

_PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "extract_invoice_v1.txt"
PROMPT_VERSION = "extract_invoice_v1"


def _extract_json(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


class LlmVisionBackend:
    name = "llm_vision"

    async def extract(
        self,
        *,
        tenant_id: str,
        pages: list[PageImage],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        system = _PROMPT.read_text(encoding="utf-8").strip()
        images = [
            VisionImage(media_type=p.media_type, data_b64=base64.b64encode(p.data).decode("ascii"))
            for p in pages
        ]
        provider = get_ai_provider()
        result = await provider.complete_vision(
            system=system,
            user="Extract the fields from this document as strict JSON per the schema.",
            images=images,
        )
        ai_metrics.observe_latency("capture.extract.latency", result.latency_ms)
        ai_metrics.incr(f"capture.extract.{'success' if result.success else 'failure'}")
        telemetry_id = await record_telemetry(
            tenant_id=tenant_id,
            feature="capture_extract",
            prompt_version=PROMPT_VERSION,
            result=result,
            user_id=user_id,
        )
        if not result.success:
            out = empty_result(engine=self.name, error_code=result.error_code)
            out["telemetry_id"] = telemetry_id
            out["provider"] = result.provider
            out["model"] = result.model
            return out

        parsed = _extract_json(result.text)
        fields: dict[str, Any] = {}
        confidences: dict[str, float] = {}
        document_type = "unknown"
        if isinstance(parsed, dict):
            document_type = str(parsed.get("document_type") or "unknown")
            if isinstance(parsed.get("fields"), dict):
                fields = parsed["fields"]
            if isinstance(parsed.get("field_confidences"), dict):
                for key, value in parsed["field_confidences"].items():
                    try:
                        confidences[str(key)] = max(0.0, min(1.0, float(value)))
                    except (TypeError, ValueError):
                        continue
        return {
            "extracted": bool(fields),
            "document_type": document_type,
            "fields": fields,
            "field_confidences": confidences,
            "engine": self.name,
            "provider": result.provider,
            "model": result.model,
            "error_code": None if fields else "empty_extraction",
            "telemetry_id": telemetry_id,
        }
