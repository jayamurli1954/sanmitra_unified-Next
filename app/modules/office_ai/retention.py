"""OfficeMitra retention helpers — purge aged emails/telemetry (ADR-005 / Phase 1 polish).

Tasks and briefs are kept by default (user work product). Email paste bodies and AI
telemetry are purged after the tenant/policy retention window.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings
from app.db.mongo import get_collection
from app.modules.office_ai.models import (
    EMAILS_COLLECTION,
    TELEMETRY_COLLECTION,
    ensure_indexes,
    utcnow,
)


def resolve_retention_days(tenant: dict[str, Any] | None = None) -> int:
    settings = get_settings()
    if tenant is not None:
        raw = tenant.get("office_ai_retention_days")
        if raw is not None:
            try:
                return max(1, int(raw))
            except (TypeError, ValueError):
                pass
    return max(1, int(settings.OFFICEMITRA_RETENTION_DAYS))


def retention_cutoff(days: int, now: datetime | None = None) -> datetime:
    base = now or utcnow()
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base - timedelta(days=max(1, int(days)))


async def cleanup_expired_office_ai_records(
    *,
    tenant_id: str | None = None,
    retention_days: int | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Delete aged email pastes and AI telemetry. Tenant-scoped when tenant_id set."""
    await ensure_indexes()
    days = retention_days if retention_days is not None else get_settings().OFFICEMITRA_RETENTION_DAYS
    cutoff = retention_cutoff(int(days), now)
    query: dict[str, Any] = {"created_at": {"$lte": cutoff}}
    if tenant_id:
        query["tenant_id"] = tenant_id

    emails = await get_collection(EMAILS_COLLECTION).delete_many(query)
    telemetry = await get_collection(TELEMETRY_COLLECTION).delete_many(query)
    return {
        "emails_deleted": int(getattr(emails, "deleted_count", 0) or 0),
        "telemetry_deleted": int(getattr(telemetry, "deleted_count", 0) or 0),
        "retention_days": int(days),
        "cutoff": cutoff.isoformat(),
    }
