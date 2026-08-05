from __future__ import annotations

import logging
from typing import Any

from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors.base import tenant_has_module

_logger = logging.getLogger("officemitra.connectors.mandirmitra")


def _temple_app_key(requested: str | None) -> str:
    key = str(requested or "").strip().lower()
    if key in {"mandirmitra", "mitrabooks"}:
        return key
    return "mandirmitra"


async def get_upcoming_events_or_donations(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    app_key: str | None = None,
    session=None,
    days: int = 14,
    **_kwargs,
) -> list[dict[str, Any]]:
    """Read-only: upcoming posted sevas via mandir_compat report helpers.

    Donations are posted receipts (not due items). Upcoming seva schedule is
    the closest existing service-layer "upcoming events" surface.
    """
    if not tenant_has_module(tenant, "temple"):
        return []
    if session is None:
        return []
    try:
        from app.modules.mandir_compat.report_helpers import seva_schedule_report

        report = await seva_schedule_report(
            session,
            tenant_id=tenant_id,
            app_key=_temple_app_key(app_key),
            days=max(1, min(int(days or 14), 60)),
        )
        rows: list[dict[str, Any]] = []
        for item in (report or {}).get("schedule") or []:
            rows.append(
                {
                    "id": item.get("id"),
                    "title": item.get("seva_name") or "Seva",
                    "status": item.get("status") or "Upcoming",
                    "due": item.get("date"),
                    "time": item.get("time") or "",
                    # Omit devotee_mobile — PII not needed in Daily Brief.
                    "devotee_name": item.get("devotee_name"),
                    "amount": item.get("amount"),
                    "source": "mandir_compat.report_helpers.seva_schedule_report",
                }
            )
            if len(rows) >= 20:
                break
        return rows
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.mandirmitra.failure")
        _logger.warning("get_upcoming_events_or_donations failed: %s", type(exc).__name__)
        return []
