"""Read helpers for housing complaints / maintenance tickets."""
from __future__ import annotations

from app.db.mongo import get_collection

COMPLAINTS = "housing_complaints"
_OPEN_COMPLAINT_STATUSES_EXCLUDED = frozenset({"resolved", "closed", "cancelled"})


def _housing_app_key(app_key: str | None = None) -> str:
    return str(app_key or "gruhamitra").strip() or "gruhamitra"


async def list_open_complaints(
    *,
    tenant_id: str,
    app_key: str,
    limit: int = 20,
) -> list[dict]:
    """Society-wide open maintenance/complaint tickets (read-only).

    Mirrors the open-status filter used by the housing dashboard
    (`status` not in resolved/closed/cancelled). Intended for connectors
    and admin summaries — no resident-scoped $or filter.
    """
    scoped_app = _housing_app_key(app_key)
    capped = max(1, min(int(limit or 20), 100))
    query: dict = {
        "tenant_id": tenant_id,
        "app_key": scoped_app,
        "status": {"$nin": list(_OPEN_COMPLAINT_STATUSES_EXCLUDED)},
    }
    rows = (
        await get_collection(COMPLAINTS)
        .find(query)
        .sort("created_at", -1)
        .limit(capped)
        .to_list(length=capped)
    )
    return [
        {
            "id": row.get("id"),
            "title": row.get("title") or "",
            "description": row.get("description") or "",
            "type": row.get("type") or "other",
            "priority": row.get("priority") or "medium",
            "scope": row.get("scope") or "individual",
            "status": row.get("status") or "open",
            "user_name": row.get("user_name") or "Resident",
            "flat_number": row.get("flat_number") or "N/A",
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }
        for row in rows
    ]
