from __future__ import annotations

import logging
from typing import Any

from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors.base import tenant_has_module

_logger = logging.getLogger("officemitra.connectors.gruhamitra")


def _housing_app_key(requested: str | None) -> str:
    key = str(requested or "").strip().lower()
    if key in {"gruhamitra", "mitrabooks"}:
        return key
    return "gruhamitra"


async def get_open_maintenance_requests(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    app_key: str | None = None,
    **_kwargs,
) -> list[dict[str, Any]]:
    """Read-only: open housing complaints via housing_compat service (not raw Mongo)."""
    if not tenant_has_module(tenant, "housing"):
        return []
    try:
        from app.modules.housing_compat import complaints_service

        rows = await complaints_service.list_open_complaints(
            tenant_id=tenant_id,
            app_key=_housing_app_key(app_key),
            limit=20,
        )
        return [
            {
                "id": row.get("id"),
                "title": row.get("title") or "Maintenance request",
                "status": row.get("status") or "open",
                "priority": row.get("priority"),
                "flat_number": row.get("flat_number"),
                "type": row.get("type"),
                "created_at": row.get("created_at"),
                "source": "housing_compat.complaints_service.list_open_complaints",
            }
            for row in (rows or [])
        ]
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.gruhamitra.failure")
        _logger.warning("get_open_maintenance_requests failed: %s", type(exc).__name__)
        return []
