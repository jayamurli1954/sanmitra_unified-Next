from __future__ import annotations

import logging
from typing import Any

from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors.base import tenant_has_module

_logger = logging.getLogger("officemitra.connectors.legalmitra")

# Practice matters are always scoped to the LegalMitra product app key.
_LEGAL_APP_KEY = "legalmitra"
_AWAITING_REVIEW_STATUSES = ("pending", "draft")


async def get_pending_documents(*, tenant_id: str, tenant: dict[str, Any], **_kwargs) -> list[dict[str, Any]]:
    """Read-only: matters awaiting review via LegalMitra practice service.

    There is no tenant-wide pending-documents list; pending/draft matters are
    the established awaiting-review queue (practice dashboard semantics).
    """
    if not tenant_has_module(tenant, "legal"):
        return []
    try:
        from app.modules.legal import practice_service

        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for status in _AWAITING_REVIEW_STATUSES:
            matters = await practice_service.list_matters(
                tenant_id=tenant_id,
                app_key=_LEGAL_APP_KEY,
                status=status,
                limit=20,
            )
            for matter in matters or []:
                matter_id = str(matter.get("matter_id") or matter.get("id") or "").strip()
                if not matter_id or matter_id in seen:
                    continue
                seen.add(matter_id)
                title = str(matter.get("title") or "Matter").strip() or "Matter"
                number = str(matter.get("matter_number") or "").strip()
                if number and number not in title:
                    title = f"{title} ({number})"
                rows.append(
                    {
                        "id": matter_id,
                        "title": title,
                        "status": matter.get("status") or status,
                        "due": matter.get("next_deadline_date") or matter.get("next_hearing_date"),
                        "priority": matter.get("priority"),
                        "client_name": matter.get("client_name"),
                        "source": "legal.practice_service.list_matters",
                    }
                )
                if len(rows) >= 20:
                    return rows
        return rows
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.legalmitra.failure")
        _logger.warning("get_pending_documents failed: %s", type(exc).__name__)
        return []
