from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import get_collection

TASKS_COLLECTION = "officemitra_tasks"
EMAILS_COLLECTION = "officemitra_emails"
BRIEFS_COLLECTION = "officemitra_briefs"
TELEMETRY_COLLECTION = "officemitra_ai_telemetry"
CALENDAR_EVENTS_COLLECTION = "officemitra_calendar_events"
MEETING_NOTES_COLLECTION = "officemitra_meeting_notes"
NOTIFICATIONS_COLLECTION = "officemitra_notifications"
PROPOSALS_COLLECTION = "officemitra_proposals"
WORKFLOW_TEMPLATES_COLLECTION = "officemitra_workflow_templates"
WORKFLOW_RUNS_COLLECTION = "officemitra_workflow_runs"
MIS_PACKS_COLLECTION = "officemitra_mis_packs"
MIS_FACTS_COLLECTION = "officemitra_mis_facts"
MIS_EXPORTS_COLLECTION = "officemitra_mis_exports"

MIS_PACK_STATUSES = frozenset(
    {"draft", "pending_reconcile", "reconciled", "pending_export", "exported", "failed"}
)
MIS_EDITABLE_PACK_STATUSES = frozenset({"draft", "pending_reconcile", "failed"})
MIS_ENTITY_TYPES = frozenset(
    {
        "pnl_line",
        "bs_line",
        "cash_summary",
        "aging_bucket",
        "kpi",
        "party",
    }
)
MIS_INGESTION_PATHS = frozenset({"excel_import", "mitrabooks", "zoho", "tally", "manual"})

TASK_STATUSES = frozenset({"open", "done", "cancelled"})
TASK_SOURCES = frozenset({"manual", "ai"})
PROPOSAL_STATUSES = frozenset(
    {"draft", "pending", "confirmed", "awaiting_checker", "applied", "failed", "dismissed", "expired"}
)
PROPOSAL_ACTION_TYPES = frozenset({"create_task"})  # kept for docs; runtime source is action registry
WORKFLOW_RUN_STATUSES = frozenset({"pending", "running", "applied", "failed", "skipped", "cancelled"})
WORKFLOW_STEP_STATUSES = frozenset({"pending", "running", "applied", "failed", "skipped", "cancelled"})
WORKFLOW_TRIGGER_SOURCES = frozenset({"proposal", "manual", "scheduled", "api"})
CALENDAR_SOURCES = frozenset({"manual", "paste", "ai"})
NOTIFICATION_KINDS = frozenset(
    {
        "calendar_due",
        "note_processed",
        "task_due",
        "calendar_parsed",
        "brief_ready",
        "proposal_ready",
        "workflow_ready",
    }
)

_indexes_ready = False


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_object_id() -> ObjectId:
    return ObjectId()


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    out = dict(doc)
    for key, value in list(out.items()):
        if isinstance(value, ObjectId):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, list):
            out[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    if "_id" in out:
        out["id"] = out.pop("_id")
    elif out.get("id") is not None:
        out["id"] = str(out["id"])
    return out


async def ensure_indexes() -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        await get_collection(TASKS_COLLECTION).create_index([("tenant_id", 1), ("status", 1), ("updated_at", -1)])
        await get_collection(EMAILS_COLLECTION).create_index([("tenant_id", 1), ("created_at", -1)])
        await get_collection(BRIEFS_COLLECTION).create_index(
            [("tenant_id", 1), ("brief_date", 1), ("generated_at", -1)]
        )
        await get_collection(TELEMETRY_COLLECTION).create_index(
            [("tenant_id", 1), ("feature", 1), ("created_at", -1)]
        )
        await get_collection(CALENDAR_EVENTS_COLLECTION).create_index(
            [("tenant_id", 1), ("starts_at", 1)]
        )
        await get_collection(MEETING_NOTES_COLLECTION).create_index(
            [("tenant_id", 1), ("created_at", -1)]
        )
        await get_collection(NOTIFICATIONS_COLLECTION).create_index(
            [("tenant_id", 1), ("user_id", 1), ("created_at", -1)]
        )
        await get_collection(NOTIFICATIONS_COLLECTION).create_index(
            [("tenant_id", 1), ("dedupe_key", 1)]
        )
        await get_collection(PROPOSALS_COLLECTION).create_index(
            [("tenant_id", 1), ("status", 1), ("created_at", -1)]
        )
        await get_collection(WORKFLOW_TEMPLATES_COLLECTION).create_index(
            [("tenant_id", 1), ("template_key", 1), ("version", -1)]
        )
        await get_collection(WORKFLOW_RUNS_COLLECTION).create_index(
            [("tenant_id", 1), ("created_at", -1)]
        )
        await get_collection(WORKFLOW_RUNS_COLLECTION).create_index(
            [("tenant_id", 1), ("idempotency_key", 1)],
            unique=True,
            partialFilterExpression={"idempotency_key": {"$type": "string"}},
        )
        await get_collection(MIS_PACKS_COLLECTION).create_index(
            [("tenant_id", 1), ("period", 1), ("updated_at", -1)]
        )
        await get_collection(MIS_PACKS_COLLECTION).create_index(
            [("tenant_id", 1), ("status", 1), ("updated_at", -1)]
        )
        await get_collection(MIS_FACTS_COLLECTION).create_index(
            [("tenant_id", 1), ("pack_id", 1), ("entity_type", 1)]
        )
        await get_collection(MIS_FACTS_COLLECTION).create_index(
            [("tenant_id", 1), ("pack_id", 1), ("fact_id", 1)],
            unique=True,
        )
        await get_collection(MIS_EXPORTS_COLLECTION).create_index(
            [("tenant_id", 1), ("pack_id", 1), ("created_at", -1)]
        )
        _indexes_ready = True
    except Exception:
        # Indexes are best-effort; routes still work without them.
        pass
