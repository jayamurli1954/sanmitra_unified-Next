from __future__ import annotations

import logging
from typing import Any

from app.modules.office_ai.ai.provider_base import ProviderResult
from app.modules.office_ai.models import TELEMETRY_COLLECTION, ensure_indexes, new_object_id, utcnow
from app.db.mongo import get_collection

_logger = logging.getLogger("officemitra.ai.telemetry")


async def record_telemetry(
    *,
    tenant_id: str,
    feature: str,
    prompt_version: str,
    result: ProviderResult,
    user_id: str | None = None,
) -> str:
    await ensure_indexes()
    doc_id = new_object_id()
    doc: dict[str, Any] = {
        "_id": doc_id,
        "tenant_id": tenant_id,
        "feature": feature,
        "provider": result.provider,
        "model": result.model,
        "prompt_version": prompt_version,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "latency_ms": result.latency_ms,
        "estimated_cost": result.estimated_cost,
        "success": bool(result.success),
        "error_code": result.error_code,
        "created_at": utcnow(),
        "created_by": user_id,
    }
    try:
        await get_collection(TELEMETRY_COLLECTION).insert_one(doc)
    except Exception as exc:
        _logger.warning("telemetry_write_failed tenant=%s feature=%s err=%s", tenant_id, feature, type(exc).__name__)
    return str(doc_id)
