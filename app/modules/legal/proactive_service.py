"""LegalMitra Stage 4 — Proactive Assistant service.

Deterministic alerts + Morning Brief assembled only from tenant practice data.
Never invents hearings, statutes, or court dates.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal.practice_service import (
    LEGAL_CLIENTS_COLLECTION,
    LEGAL_MATTER_DOCUMENTS_COLLECTION,
    LEGAL_MATTER_TIMELINE_COLLECTION,
    LEGAL_MATTERS_COLLECTION,
)
from app.modules.legal.proactive_schemas import (
    AlertUpdateRequest,
    MorningBriefGenerateRequest,
)

LEGAL_PRACTICE_ALERTS_COLLECTION = "legal_practice_alerts"
LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION = "legal_practice_notifications"
LEGAL_MORNING_BRIEFS_COLLECTION = "legal_morning_briefs"

ADVISORY_NOTICE = (
    "This Morning Brief is an advisory working summary generated from your tenant "
    "practice records. It is not final legal advice. A qualified professional must "
    "review before filing, advising a client, or taking any binding action."
)

MATTER_PRIORITY_WEIGHT = {"low": 0, "normal": 5, "high": 15, "urgent": 25}
PRACTICE_AREA_RISK = {
    "litigation": 8,
    "gst": 6,
    "income_tax": 6,
    "secretarial": 4,
    "contract": 3,
    "advisory": 2,
    "compliance": 5,
}


class ProactiveDisabledError(Exception):
    """Raised when Stage 4 proactive features are disabled by flag."""


class ProactiveNotFoundError(Exception):
    """Scoped entity missing."""


class ProactiveValidationError(Exception):
    """Invalid alert state transition or payload."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _audit(**kwargs) -> None:
    try:
        await log_audit_event(**kwargs)
    except Exception:
        pass


def _require_proactive_enabled() -> None:
    settings = get_settings()
    if not getattr(settings, "LEGALMITRA_PROACTIVE_ENABLED", True):
        raise ProactiveDisabledError("LegalMitra proactive assistant is disabled")


def _lookahead_days() -> int:
    return max(1, int(getattr(get_settings(), "LEGALMITRA_ALERT_LOOKAHEAD_DAYS", 7)))


def _dormant_days() -> int:
    return max(1, int(getattr(get_settings(), "LEGALMITRA_DORMANT_MATTER_DAYS", 45)))


def _stale_review_days() -> int:
    return max(1, int(getattr(get_settings(), "LEGALMITRA_STALE_REVIEW_DAYS", 7)))


def _health_label(score: int) -> str:
    if score < 50:
        return "Critical"
    if score < 75:
        return "Needs Attention"
    if score < 90:
        return "Healthy"
    return "Strong"


def _action_href(matter_id: str | None) -> str:
    if matter_id:
        return f"./tracker.html?matter_id={matter_id}#daily-board"
    return "./tracker.html#daily-board"


async def ensure_proactive_indexes() -> None:
    alerts = get_collection(LEGAL_PRACTICE_ALERTS_COLLECTION)
    await alerts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("alert_id", 1)], unique=True
    )
    await alerts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("dedupe_key", 1)], unique=True
    )
    await alerts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("status", 1), ("priority_score", -1)]
    )

    notifications = get_collection(LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION)
    await notifications.create_index(
        [("tenant_id", 1), ("app_key", 1), ("notification_id", 1)], unique=True
    )
    await notifications.create_index(
        [("tenant_id", 1), ("app_key", 1), ("user_id", 1), ("created_at", -1)]
    )

    briefs = get_collection(LEGAL_MORNING_BRIEFS_COLLECTION)
    await briefs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("brief_id", 1)], unique=True
    )
    await briefs.create_index(
        [
            ("tenant_id", 1),
            ("app_key", 1),
            ("user_id", 1),
            ("brief_date", 1),
            ("persona", 1),
            ("window", 1),
        ],
        unique=True,
    )


# ── Scoring helpers ──────────────────────────────────────────────────────────


def compute_matter_health(
    *,
    matter: dict,
    document_count: int,
    days_since_activity: int | None,
    overdue: bool,
) -> int:
    score = 80
    status = matter.get("status")
    if status in {"draft", "pending"}:
        score -= 10
    if status == "on_hold":
        score -= 5
    if document_count <= 0 and status in {"active", "pending"}:
        score -= 25
    if overdue:
        score -= 30
    if days_since_activity is not None and days_since_activity >= _dormant_days():
        score -= 20
    elif days_since_activity is not None and days_since_activity >= 14:
        score -= 8
    return max(0, min(100, score))


def compute_priority_score(
    *,
    alert_type: str,
    severity: str,
    matter: dict,
    days_until: int | None,
    document_count: int = 0,
) -> int:
    score = 10
    if severity == "urgent":
        score += 40
    elif severity == "high":
        score += 25
    elif severity == "normal":
        score += 10
    if days_until is not None:
        if days_until < 0:
            score += 35 + min(20, abs(days_until))
        elif days_until <= 2:
            score += 20
        elif days_until <= 7:
            score += 10
    score += MATTER_PRIORITY_WEIGHT.get(str(matter.get("priority") or "normal"), 5)
    area = str(matter.get("practice_area") or "general").lower()
    score += PRACTICE_AREA_RISK.get(area, 2)
    if alert_type == "compliance_gap_missing_documents" or document_count == 0:
        score += 12
    if alert_type == "dormant_matter":
        score += 15
    return int(score)


def _suggested_actions_for(*, alert_type: str, matter: dict) -> list[str]:
    number = matter.get("matter_number") or matter.get("matter_id")
    actions: list[str] = []
    if alert_type == "hearing_approaching":
        actions = [
            f"Prepare for hearing on matter {number}",
            "Review last order / timeline entry",
            "Confirm client instructions",
            "Generate Matter Intelligence Brief",
        ]
    elif alert_type == "deadline_approaching":
        actions = [
            f"Prepare filing / response for deadline on {number}",
            "Check required documents are attached",
            "Review applicable law with citations before filing",
            "Generate Matter Intelligence Brief",
        ]
    elif alert_type == "compliance_gap_missing_documents":
        actions = [
            "Attach source documents to the matter file",
            "Request missing papers from the client",
            "Update matter timeline after receipt",
        ]
    elif alert_type == "matter_awaiting_review":
        actions = [
            "Move matter forward or update status",
            "Generate or review Matter Intelligence Brief",
            "Record next hearing/deadline if known",
        ]
    elif alert_type == "dormant_matter":
        actions = [
            "Confirm whether the matter is waiting on client, court, or internal work",
            "Add a timeline note with current status",
            "Set next deadline or place on hold if paused",
        ]
    else:
        actions = ["Open matter and review timeline"]
    return actions


def _severity_for_days(days_until: int | None) -> str:
    if days_until is None:
        return "normal"
    if days_until < 0:
        return "urgent"
    if days_until <= 2:
        return "high"
    return "normal"


# ── Alert evaluation ─────────────────────────────────────────────────────────


async def _load_practice_snapshot(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    scope = _scope(tenant_id=tenant_id, app_key=app_key)
    matters = await get_collection(LEGAL_MATTERS_COLLECTION).find(scope).to_list(length=500)
    docs = await get_collection(LEGAL_MATTER_DOCUMENTS_COLLECTION).find(scope).to_list(length=2000)
    timeline = await get_collection(LEGAL_MATTER_TIMELINE_COLLECTION).find(scope).to_list(
        length=5000
    )
    clients = await get_collection(LEGAL_CLIENTS_COLLECTION).find(scope).to_list(length=500)

    docs_by_matter: dict[str, int] = {}
    for d in docs:
        mid = d.get("matter_id")
        if mid:
            docs_by_matter[mid] = docs_by_matter.get(mid, 0) + 1

    latest_activity: dict[str, datetime] = {}
    for event in timeline:
        mid = event.get("matter_id")
        if not mid:
            continue
        occurred = _parse_dt(event.get("occurred_at")) or _parse_dt(event.get("created_at"))
        if not occurred:
            continue
        prev = latest_activity.get(mid)
        if prev is None or occurred > prev:
            latest_activity[mid] = occurred

    return {
        "matters": matters,
        "docs_by_matter": docs_by_matter,
        "latest_activity": latest_activity,
        "clients": clients,
        "documents": docs,
        "timeline": timeline,
    }


def _candidate_alerts(
    *,
    snapshot: dict[str, Any],
    today: date,
) -> list[dict[str, Any]]:
    lookahead = _lookahead_days()
    dormant = _dormant_days()
    stale = _stale_review_days()
    candidates: list[dict[str, Any]] = []

    for matter in snapshot["matters"]:
        status = matter.get("status")
        if status in {"closed", "archived"}:
            continue
        matter_id = matter["matter_id"]
        doc_count = int(snapshot["docs_by_matter"].get(matter_id, 0))
        last_act = snapshot["latest_activity"].get(matter_id) or _parse_dt(
            matter.get("updated_at")
        ) or _parse_dt(matter.get("created_at"))
        days_since = (today - last_act.date()).days if last_act else None

        hearing = _parse_date(matter.get("next_hearing_date"))
        deadline = _parse_date(matter.get("next_deadline_date"))
        overdue = False
        if hearing is not None:
            days = (hearing - today).days
            if days <= lookahead:
                overdue = days < 0 or overdue
                sev = _severity_for_days(days)
                actions = _suggested_actions_for(alert_type="hearing_approaching", matter=matter)
                candidates.append(
                    {
                        "alert_type": "hearing_approaching",
                        "severity": sev,
                        "matter_id": matter_id,
                        "client_id": matter.get("client_id"),
                        "title": f"Hearing {'overdue' if days < 0 else 'upcoming'}: {matter.get('matter_number')}",
                        "summary": f"{matter.get('title')} — hearing on {hearing.isoformat()}",
                        "due_at": hearing.isoformat(),
                        "dedupe_key": f"hearing:{matter_id}:{hearing.isoformat()}",
                        "priority_score": compute_priority_score(
                            alert_type="hearing_approaching",
                            severity=sev,
                            matter=matter,
                            days_until=days,
                            document_count=doc_count,
                        ),
                        "suggested_actions": actions,
                        "recommended_action": actions[0] if actions else None,
                        "recommended_priority": sev,
                        "matter_health": compute_matter_health(
                            matter=matter,
                            document_count=doc_count,
                            days_since_activity=days_since,
                            overdue=days < 0,
                        ),
                        "payload": {
                            "matter_number": matter.get("matter_number"),
                            "court": matter.get("court"),
                            "days_until": days,
                        },
                    }
                )

        if deadline is not None:
            days = (deadline - today).days
            if days <= lookahead:
                overdue = days < 0 or overdue
                sev = _severity_for_days(days)
                actions = _suggested_actions_for(alert_type="deadline_approaching", matter=matter)
                candidates.append(
                    {
                        "alert_type": "deadline_approaching",
                        "severity": sev,
                        "matter_id": matter_id,
                        "client_id": matter.get("client_id"),
                        "title": f"Deadline {'overdue' if days < 0 else 'upcoming'}: {matter.get('matter_number')}",
                        "summary": f"{matter.get('title')} — deadline on {deadline.isoformat()}",
                        "due_at": deadline.isoformat(),
                        "dedupe_key": f"deadline:{matter_id}:{deadline.isoformat()}",
                        "priority_score": compute_priority_score(
                            alert_type="deadline_approaching",
                            severity=sev,
                            matter=matter,
                            days_until=days,
                            document_count=doc_count,
                        ),
                        "suggested_actions": actions,
                        "recommended_action": actions[0] if actions else None,
                        "recommended_priority": sev,
                        "matter_health": compute_matter_health(
                            matter=matter,
                            document_count=doc_count,
                            days_since_activity=days_since,
                            overdue=days < 0,
                        ),
                        "payload": {
                            "matter_number": matter.get("matter_number"),
                            "days_until": days,
                        },
                    }
                )

        if status in {"active", "pending"} and doc_count == 0:
            actions = _suggested_actions_for(
                alert_type="compliance_gap_missing_documents", matter=matter
            )
            candidates.append(
                {
                    "alert_type": "compliance_gap_missing_documents",
                    "severity": "high",
                    "matter_id": matter_id,
                    "client_id": matter.get("client_id"),
                    "title": f"Missing documents: {matter.get('matter_number')}",
                    "summary": f"{matter.get('title')} has no attached documents",
                    "due_at": None,
                    "dedupe_key": f"missing_docs:{matter_id}",
                    "priority_score": compute_priority_score(
                        alert_type="compliance_gap_missing_documents",
                        severity="high",
                        matter=matter,
                        days_until=None,
                        document_count=0,
                    ),
                    "suggested_actions": actions,
                    "recommended_action": actions[0] if actions else None,
                    "recommended_priority": "high",
                    "matter_health": compute_matter_health(
                        matter=matter,
                        document_count=0,
                        days_since_activity=days_since,
                        overdue=overdue,
                    ),
                    "payload": {"matter_number": matter.get("matter_number")},
                }
            )

        created = _parse_dt(matter.get("created_at"))
        age_days = (today - created.date()).days if created else 0
        if status in {"draft", "pending"} and age_days >= stale:
            actions = _suggested_actions_for(alert_type="matter_awaiting_review", matter=matter)
            candidates.append(
                {
                    "alert_type": "matter_awaiting_review",
                    "severity": "normal",
                    "matter_id": matter_id,
                    "client_id": matter.get("client_id"),
                    "title": f"Awaiting review: {matter.get('matter_number')}",
                    "summary": f"{matter.get('title')} has been {status} for {age_days} days",
                    "due_at": None,
                    "dedupe_key": f"awaiting_review:{matter_id}",
                    "priority_score": compute_priority_score(
                        alert_type="matter_awaiting_review",
                        severity="normal",
                        matter=matter,
                        days_until=None,
                        document_count=doc_count,
                    ),
                    "suggested_actions": actions,
                    "recommended_action": actions[0] if actions else None,
                    "recommended_priority": "normal",
                    "matter_health": compute_matter_health(
                        matter=matter,
                        document_count=doc_count,
                        days_since_activity=days_since,
                        overdue=overdue,
                    ),
                    "payload": {"age_days": age_days, "status": status},
                }
            )

        if (
            status in {"active", "pending", "on_hold"}
            and days_since is not None
            and days_since >= dormant
        ):
            actions = _suggested_actions_for(alert_type="dormant_matter", matter=matter)
            candidates.append(
                {
                    "alert_type": "dormant_matter",
                    "severity": "high",
                    "matter_id": matter_id,
                    "client_id": matter.get("client_id"),
                    "title": f"Dormant matter: {matter.get('matter_number')}",
                    "summary": f"No activity for {days_since} days on {matter.get('title')}",
                    "due_at": None,
                    "dedupe_key": f"dormant:{matter_id}",
                    "priority_score": compute_priority_score(
                        alert_type="dormant_matter",
                        severity="high",
                        matter=matter,
                        days_until=None,
                        document_count=doc_count,
                    ),
                    "suggested_actions": actions,
                    "recommended_action": actions[0] if actions else None,
                    "recommended_priority": "high",
                    "matter_health": compute_matter_health(
                        matter=matter,
                        document_count=doc_count,
                        days_since_activity=days_since,
                        overdue=overdue,
                    ),
                    "payload": {"days_since_activity": days_since},
                }
            )

    return candidates


async def refresh_practice_alerts(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
) -> dict:
    _require_proactive_enabled()
    snapshot = await _load_practice_snapshot(tenant_id=tenant_id, app_key=app_key)
    today = _today()
    candidates = _candidate_alerts(snapshot=snapshot, today=today)
    alerts = get_collection(LEGAL_PRACTICE_ALERTS_COLLECTION)
    scope = _scope(tenant_id=tenant_id, app_key=app_key)
    now = _now()

    active_keys = {c["dedupe_key"] for c in candidates}
    upserted = 0
    for cand in candidates:
        existing = await alerts.find_one({**scope, "dedupe_key": cand["dedupe_key"]})
        fields = {
            **cand,
            "updated_at": now,
            "action_href": _action_href(cand.get("matter_id")),
        }
        if existing is None:
            doc = {
                "alert_id": str(uuid4()),
                **scope,
                **fields,
                "status": "open",
                "snoozed_until": None,
                "resolved_at": None,
                "resolved_by": None,
                "created_at": now,
            }
            await alerts.insert_one(doc)
            upserted += 1
            await _create_notification_for_alert(
                tenant_id=tenant_id,
                app_key=app_key,
                user_id=actor_id,
                alert=doc,
            )
        else:
            # Re-open auto-resolved alerts if condition returns; leave user-dismissed alone.
            status = existing.get("status")
            updates = {k: v for k, v in fields.items()}
            if status == "resolved":
                updates["status"] = "open"
                updates["resolved_at"] = None
                updates["resolved_by"] = None
            elif status == "snoozed":
                until = _parse_dt(existing.get("snoozed_until"))
                if until and until <= now:
                    updates["status"] = "open"
                    updates["snoozed_until"] = None
            elif status == "dismissed":
                updates = {"updated_at": now}  # keep dismissed
            await alerts.update_one(
                {**scope, "alert_id": existing["alert_id"]},
                {"$set": updates},
            )
            upserted += 1

    resolved = 0
    open_rows = await alerts.find({**scope, "status": "open"}).to_list(length=1000)
    for row in open_rows:
        if row.get("dedupe_key") not in active_keys:
            await alerts.update_one(
                {**scope, "alert_id": row["alert_id"]},
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_at": now,
                        "resolved_by": "system",
                        "updated_at": now,
                    }
                },
            )
            resolved += 1

    open_count = await alerts.count_documents({**scope, "status": "open"})
    await _audit(
        tenant_id=tenant_id,
        user_id=actor_id,
        product=app_key,
        action="legal_practice_alerts_refreshed",
        entity_type="legal_practice_alerts",
        entity_id=tenant_id,
        new_value={"upserted": upserted, "resolved": resolved, "open_alerts": open_count},
    )
    return {"upserted": upserted, "resolved": resolved, "open_alerts": int(open_count)}


async def list_practice_alerts(
    *,
    tenant_id: str,
    app_key: str,
    status: str | None = "open",
    limit: int = 50,
) -> list[dict]:
    _require_proactive_enabled()
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if status:
        flt["status"] = status
    rows = await (
        get_collection(LEGAL_PRACTICE_ALERTS_COLLECTION)
        .find(flt)
        .sort("priority_score", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    items = []
    for row in rows:
        item = _serialize(row)
        item["due_at"] = _parse_date(item.get("due_at"))
        item["action_href"] = item.get("action_href") or _action_href(item.get("matter_id"))
        items.append(item)
    return items


async def update_practice_alert(
    *,
    tenant_id: str,
    app_key: str,
    alert_id: str,
    actor_id: str,
    payload: AlertUpdateRequest,
) -> dict:
    _require_proactive_enabled()
    alerts = get_collection(LEGAL_PRACTICE_ALERTS_COLLECTION)
    scope = _scope(tenant_id=tenant_id, app_key=app_key)
    existing = await alerts.find_one({**scope, "alert_id": alert_id})
    if existing is None:
        raise ProactiveNotFoundError("Alert not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _serialize(existing)
    now = _now()
    if updates.get("status") in {"resolved", "dismissed"}:
        updates["resolved_at"] = now
        updates["resolved_by"] = actor_id
    if updates.get("status") == "snoozed" and not updates.get("snoozed_until"):
        updates["snoozed_until"] = now + timedelta(days=1)
    updates["updated_at"] = now
    await alerts.update_one({**scope, "alert_id": alert_id}, {"$set": updates})
    await _audit(
        tenant_id=tenant_id,
        user_id=actor_id,
        product=app_key,
        action="legal_practice_alert_updated",
        entity_type="legal_practice_alert",
        entity_id=alert_id,
        old_value={"status": existing.get("status")},
        new_value={k: updates[k] for k in updates if k != "updated_at"},
    )
    refreshed = await alerts.find_one({**scope, "alert_id": alert_id})
    item = _serialize(refreshed or {**existing, **updates})
    item["due_at"] = _parse_date(item.get("due_at"))
    return item


# ── Notifications ────────────────────────────────────────────────────────────


async def _create_notification_for_alert(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    alert: dict,
) -> None:
    notifications = get_collection(LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION)
    now = _now()
    doc = {
        "notification_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "user_id": user_id,
        "source_type": "alert",
        "source_id": alert.get("alert_id"),
        "title": alert.get("title") or "Practice alert",
        "body": alert.get("summary") or "",
        "action_href": alert.get("action_href") or _action_href(alert.get("matter_id")),
        "read_at": None,
        "created_at": now,
    }
    await notifications.insert_one(doc)


async def list_notifications(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    limit: int = 50,
) -> dict:
    _require_proactive_enabled()
    flt = {**_scope(tenant_id=tenant_id, app_key=app_key), "user_id": user_id}
    rows = await (
        get_collection(LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION)
        .find(flt)
        .sort("created_at", -1)
        .limit(limit)
        .to_list(length=limit)
    )
    unread = await get_collection(LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION).count_documents(
        {**flt, "read_at": None}
    )
    return {
        "items": [_serialize(r) for r in rows],
        "count": len(rows),
        "unread_count": int(unread),
    }


async def mark_notification_read(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    notification_id: str,
) -> dict:
    _require_proactive_enabled()
    col = get_collection(LEGAL_PRACTICE_NOTIFICATIONS_COLLECTION)
    flt = {
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "user_id": user_id,
        "notification_id": notification_id,
    }
    existing = await col.find_one(flt)
    if existing is None:
        raise ProactiveNotFoundError("Notification not found")
    await col.update_one(flt, {"$set": {"read_at": _now()}})
    refreshed = await col.find_one(flt)
    return _serialize(refreshed or {**existing, "read_at": _now()})


# ── Morning Brief ────────────────────────────────────────────────────────────


def compute_practice_health_score(*, snapshot: dict, open_alerts: list[dict]) -> tuple[int, str]:
    matters = [
        m
        for m in snapshot["matters"]
        if m.get("status") not in {"closed", "archived"}
    ]
    if not matters and not open_alerts:
        return 100, "Strong"

    score = 100
    urgent = sum(1 for a in open_alerts if a.get("severity") == "urgent")
    high = sum(1 for a in open_alerts if a.get("severity") == "high")
    missing_docs = sum(
        1 for a in open_alerts if a.get("alert_type") == "compliance_gap_missing_documents"
    )
    dormant = sum(1 for a in open_alerts if a.get("alert_type") == "dormant_matter")
    awaiting = sum(1 for a in open_alerts if a.get("alert_type") == "matter_awaiting_review")

    score -= urgent * 12
    score -= high * 6
    score -= missing_docs * 5
    score -= dormant * 4
    score -= awaiting * 3
    score -= max(0, len(open_alerts) - 5) * 2
    score = max(0, min(100, score))
    return score, _health_label(score)


async def generate_morning_brief(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    payload: MorningBriefGenerateRequest | None = None,
) -> dict:
    _require_proactive_enabled()
    settings = get_settings()
    if not getattr(settings, "LEGALMITRA_MORNING_BRIEF_ENABLED", True):
        raise ProactiveDisabledError("Morning Brief is disabled")

    options = payload or MorningBriefGenerateRequest()
    if options.window != "daily":
        # Reserved multi-window shape — Stage 4 exit requires daily only.
        raise ProactiveValidationError(
            f"Brief window '{options.window}' is reserved; use window=daily for Stage 4"
        )

    await refresh_practice_alerts(tenant_id=tenant_id, app_key=app_key, actor_id=user_id)
    snapshot = await _load_practice_snapshot(tenant_id=tenant_id, app_key=app_key)
    open_alerts = await list_practice_alerts(
        tenant_id=tenant_id, app_key=app_key, status="open", limit=100
    )
    health_score, health_label = compute_practice_health_score(
        snapshot=snapshot, open_alerts=open_alerts
    )
    today = _today()
    empty = not snapshot["matters"] and not snapshot["clients"]

    from app.modules.legal.workflow_service import recommend_workflow_for

    matters_by_id = {m.get("matter_id"): m for m in snapshot["matters"]}
    priority_actions = []
    for alert in sorted(open_alerts, key=lambda a: a.get("priority_score") or 0, reverse=True)[
        :15
    ]:
        matter = matters_by_id.get(alert.get("matter_id")) or {}
        recommended_workflow = recommend_workflow_for(
            alert_type=alert.get("alert_type"),
            practice_area=matter.get("practice_area"),
            title=alert.get("title") or matter.get("title"),
        )
        priority_actions.append(
            {
                "alert_id": alert.get("alert_id"),
                "alert_type": alert.get("alert_type"),
                "title": alert.get("title"),
                "summary": alert.get("summary"),
                "severity": alert.get("severity"),
                "priority_score": alert.get("priority_score"),
                "suggested_actions": alert.get("suggested_actions") or [],
                "matter_id": alert.get("matter_id"),
                "action_href": alert.get("action_href") or _action_href(alert.get("matter_id")),
                "matter_health": alert.get("matter_health"),
                "recommended_workflow": recommended_workflow,
            }
        )

    hearings = []
    deadlines = []
    awaiting = []
    gaps = []
    for matter in snapshot["matters"]:
        if matter.get("status") in {"closed", "archived"}:
            continue
        mid = matter["matter_id"]
        doc_count = int(snapshot["docs_by_matter"].get(mid, 0))
        hearing = _parse_date(matter.get("next_hearing_date"))
        deadline = _parse_date(matter.get("next_deadline_date"))
        if hearing and (hearing - today).days <= _lookahead_days():
            hearings.append(
                {
                    "matter_id": mid,
                    "matter_number": matter.get("matter_number"),
                    "title": matter.get("title"),
                    "next_hearing_date": hearing.isoformat(),
                    "court": matter.get("court"),
                    "action_href": _action_href(mid),
                }
            )
        if deadline and (deadline - today).days <= _lookahead_days():
            deadlines.append(
                {
                    "matter_id": mid,
                    "matter_number": matter.get("matter_number"),
                    "title": matter.get("title"),
                    "next_deadline_date": deadline.isoformat(),
                    "action_href": _action_href(mid),
                }
            )
        if matter.get("status") in {"draft", "pending"}:
            awaiting.append(
                {
                    "matter_id": mid,
                    "matter_number": matter.get("matter_number"),
                    "title": matter.get("title"),
                    "status": matter.get("status"),
                    "action_href": _action_href(mid),
                }
            )
        if matter.get("status") in {"active", "pending"} and doc_count == 0:
            gaps.append(
                {
                    "matter_id": mid,
                    "matter_number": matter.get("matter_number"),
                    "title": matter.get("title"),
                    "gap": "missing_documents",
                    "action_href": _action_href(mid),
                }
            )

    recent_activity = []
    for event in sorted(
        snapshot["timeline"],
        key=lambda e: str(e.get("occurred_at") or e.get("created_at") or ""),
        reverse=True,
    )[:10]:
        recent_activity.append(
            {
                "event_id": event.get("event_id"),
                "matter_id": event.get("matter_id"),
                "event_type": event.get("event_type"),
                "summary": event.get("summary"),
                "occurred_at": event.get("occurred_at"),
                "action_href": _action_href(event.get("matter_id")),
            }
        )

    if empty:
        suggested_focus = [
            "Create your first client and matter to activate the Morning Brief.",
            "Add hearing or deadline dates so watches can surface Priority Actions.",
        ]
        limitations = [
            "No practice data found for this tenant.",
            "Never invent hearings, statutes, or court dates.",
        ]
        confidence = 0.2
    else:
        suggested_focus = []
        for action in priority_actions[:5]:
            for tip in action.get("suggested_actions") or []:
                if tip not in suggested_focus:
                    suggested_focus.append(tip)
                if len(suggested_focus) >= 5:
                    break
            if len(suggested_focus) >= 5:
                break
        if not suggested_focus:
            suggested_focus = ["Review open matters and confirm next dates are recorded."]
        limitations = [
            "Summary is grounded only in stored clients, matters, documents, timeline, and alerts.",
            "Never invent hearings, statutes, or court dates.",
            "Suggested actions are deterministic operational prompts, not legal advice.",
        ]
        confidence = 0.55
        if open_alerts:
            confidence += 0.1
        if snapshot["documents"]:
            confidence += 0.05
        confidence = min(confidence, 0.8)

    sections = {
        "date_context": today.isoformat(),
        "persona_context": options.persona,
        "practice_health_score": health_score,
        "practice_health_label": health_label,
        "priority_actions": priority_actions,
        "upcoming_hearings": hearings,
        "upcoming_deadlines": deadlines,
        "matters_awaiting_review": awaiting,
        "compliance_gaps": gaps,
        "recent_activity": recent_activity,
        "suggested_focus": suggested_focus,
        "limitations": limitations,
        "confidence": round(confidence, 2),
        "human_review_required": True,
    }

    sources = [{"source_type": "practice_snapshot", "matters": len(snapshot["matters"])}]
    for alert in open_alerts[:20]:
        sources.append(
            {
                "source_type": "alert",
                "alert_id": alert.get("alert_id"),
                "alert_type": alert.get("alert_type"),
            }
        )

    briefs = get_collection(LEGAL_MORNING_BRIEFS_COLLECTION)
    scope = _scope(tenant_id=tenant_id, app_key=app_key)
    existing = await briefs.find_one(
        {
            **scope,
            "user_id": user_id,
            "brief_date": today.isoformat(),
            "persona": options.persona,
            "window": options.window,
        }
    )
    now = _now()
    if existing and not options.force_refresh:
        out = _serialize(existing)
        out["brief_date"] = _parse_date(out.get("brief_date")) or today
        return out

    brief = {
        "brief_id": str(uuid4()) if not existing else existing["brief_id"],
        **scope,
        "user_id": user_id,
        "brief_date": today.isoformat(),
        "window": options.window,
        "persona": options.persona,
        "practice_health_score": health_score,
        "practice_health_label": health_label,
        "sections": sections,
        "alert_ids": [a.get("alert_id") for a in open_alerts if a.get("alert_id")],
        "matter_ids": [m.get("matter_id") for m in snapshot["matters"] if m.get("matter_id")],
        "sources": sources,
        "advisory_notice": ADVISORY_NOTICE,
        "confidence": sections["confidence"],
        "human_review_required": True,
        "generation_strategy": "grounded_practice_summary",
        "generated_at": now,
        "generated_by": user_id,
        "empty_practice": empty,
    }

    if existing:
        await briefs.update_one(
            {**scope, "brief_id": existing["brief_id"]},
            {"$set": {k: v for k, v in brief.items() if k != "brief_id"}},
        )
        brief["brief_id"] = existing["brief_id"]
    else:
        await briefs.insert_one(brief)

    await _audit(
        tenant_id=tenant_id,
        user_id=user_id,
        product=app_key,
        action="legal_morning_brief_generated",
        entity_type="legal_morning_brief",
        entity_id=brief["brief_id"],
        new_value={
            "practice_health_score": health_score,
            "open_alerts": len(open_alerts),
            "empty_practice": empty,
        },
    )

    out = _serialize(brief)
    out["brief_date"] = today
    return out


async def get_today_morning_brief(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    persona: str = "advocate",
    window: str = "daily",
) -> dict:
    _require_proactive_enabled()
    today = _today()
    existing = await get_collection(LEGAL_MORNING_BRIEFS_COLLECTION).find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "user_id": user_id,
            "brief_date": today.isoformat(),
            "persona": persona,
            "window": window,
        }
    )
    if existing:
        out = _serialize(existing)
        out["brief_date"] = _parse_date(out.get("brief_date")) or today
        return out
    return await generate_morning_brief(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=user_id,
        payload=MorningBriefGenerateRequest(persona=persona, window=window),  # type: ignore[arg-type]
    )


async def extend_dashboard_proactive(
    *,
    tenant_id: str,
    app_key: str,
    base_dashboard: dict,
) -> dict:
    """Non-breaking dashboard enrichment used by Stage 3 dashboard route."""
    try:
        _require_proactive_enabled()
    except ProactiveDisabledError:
        base_dashboard["open_alerts"] = 0
        base_dashboard["practice_health_score"] = None
        base_dashboard["practice_health_label"] = None
        return base_dashboard

    open_alerts = await list_practice_alerts(
        tenant_id=tenant_id, app_key=app_key, status="open", limit=100
    )
    snapshot = await _load_practice_snapshot(tenant_id=tenant_id, app_key=app_key)
    score, label = compute_practice_health_score(snapshot=snapshot, open_alerts=open_alerts)
    base_dashboard["open_alerts"] = len(open_alerts)
    base_dashboard["practice_health_score"] = score
    base_dashboard["practice_health_label"] = label
    base_dashboard["priority_alerts"] = open_alerts[:5]
    return base_dashboard
