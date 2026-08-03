"""LegalMitra Stage 5 — guided agentic workflow orchestrator.

Deterministic declared step graph only. No autonomous agent loops, no file/send.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal import workflow_adapters as adapters
from app.modules.legal.practice_service import PracticeNotFoundError, get_matter
from app.modules.legal.workflow_definitions import (
    get_definition,
    list_catalog,
    list_enabled_definitions,
    resolve_template,
)
from app.modules.legal.workflow_schemas import (
    ReadyToFileRequest,
    WorkflowRunCreateRequest,
    WorkflowStepRejectRequest,
)

LEGAL_WORKFLOW_RUNS = "legal_workflow_runs"
LEGAL_WORKFLOW_STEPS = "legal_workflow_steps"
LEGAL_WORKFLOW_ARTIFACTS = "legal_workflow_artifacts"
LEGAL_WORKFLOW_TIMELINE = "legal_workflow_timeline"
LEGAL_KG_NODES = "legal_kg_nodes"
LEGAL_KG_EDGES = "legal_kg_edges"

DEFAULT_APP_KEY = "legalmitra"

ADAPTER_MAP = {
    "matter_intake": adapters.adapter_matter_intake,
    "legal_research": adapters.adapter_legal_research,
    "document_evidence": adapters.adapter_document_evidence,
    "drafting": adapters.adapter_drafting,
    "human_review_gate": adapters.adapter_human_review_gate,
    "complete": adapters.adapter_complete,
}


class WorkflowDisabledError(Exception):
    """Feature flag off."""


class WorkflowNotFoundError(Exception):
    """Scoped run/step missing."""


class WorkflowValidationError(Exception):
    """Invalid state or payload."""


class WorkflowConflictError(Exception):
    """Illegal transition."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_datetime(value: Any) -> datetime | None:
    """Normalize Mongo/naive/aware datetimes for safe arithmetic."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _bson_safe(value: Any) -> Any:
    """Convert values Mongo/BSON cannot encode (e.g. datetime.date) before insert."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _bson_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_bson_safe(v) for v in value]
    return value


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


def _require_enabled() -> None:
    if not getattr(get_settings(), "LEGALMITRA_AGENTIC_ENABLED", True):
        raise WorkflowDisabledError("LegalMitra agentic workflows are disabled")


async def _audit(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            product=app_key or DEFAULT_APP_KEY,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        pass


async def ensure_workflow_indexes() -> None:
    runs = get_collection(LEGAL_WORKFLOW_RUNS)
    await runs.create_index([("tenant_id", 1), ("app_key", 1), ("run_id", 1)], unique=True)
    await runs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("matter_id", 1), ("created_at", -1)]
    )
    await runs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("status", 1), ("updated_at", -1)]
    )

    steps = get_collection(LEGAL_WORKFLOW_STEPS)
    await steps.create_index([("tenant_id", 1), ("app_key", 1), ("step_id", 1)], unique=True)
    await steps.create_index(
        [("tenant_id", 1), ("app_key", 1), ("run_id", 1), ("step_key", 1), ("attempt", 1)]
    )

    artifacts = get_collection(LEGAL_WORKFLOW_ARTIFACTS)
    await artifacts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("artifact_id", 1)], unique=True
    )
    await artifacts.create_index(
        [("tenant_id", 1), ("app_key", 1), ("run_id", 1), ("created_at", -1)]
    )

    timeline = get_collection(LEGAL_WORKFLOW_TIMELINE)
    await timeline.create_index(
        [("tenant_id", 1), ("app_key", 1), ("event_id", 1)], unique=True
    )
    await timeline.create_index(
        [("tenant_id", 1), ("app_key", 1), ("run_id", 1), ("occurred_at", -1)]
    )

    nodes = get_collection(LEGAL_KG_NODES)
    await nodes.create_index([("tenant_id", 1), ("app_key", 1), ("node_id", 1)], unique=True)
    edges = get_collection(LEGAL_KG_EDGES)
    await edges.create_index([("tenant_id", 1), ("app_key", 1), ("edge_id", 1)], unique=True)


def recommend_workflow_for(
    *,
    alert_type: str | None = None,
    practice_area: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Map Stage 4 alert/matter hints → Stage 5 recommended workflow CTA."""
    hay = " ".join(
        str(x or "").lower() for x in (alert_type, practice_area, title)
    )
    template = "general"
    if "gst" in hay:
        template = "gst_notice"
    elif "income" in hay or "it_notice" in hay or practice_area == "income_tax":
        template = "income_tax_notice"
    return {
        "workflow_key": "prepare_matter_response",
        "workflow_template": template,
        "display_name": "Prepare Matter Response",
        "catalog_status": "mvp",
    }


async def get_workflow_catalog() -> dict[str, Any]:
    _require_enabled()
    items = list_catalog()
    return {"items": items, "count": len(items)}


async def get_workflow_definitions() -> dict[str, Any]:
    _require_enabled()
    items = list_enabled_definitions()
    return {"items": items, "count": len(items)}


async def _append_run_timeline(
    *,
    tenant_id: str,
    app_key: str,
    run_id: str,
    matter_id: str | None,
    actor_id: str,
    event_type: str,
    summary: str,
    payload: dict | None = None,
) -> dict:
    event = {
        "event_id": str(uuid4()),
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "run_id": run_id,
        "matter_id": matter_id,
        "event_type": event_type,
        "summary": summary,
        "actor_id": actor_id,
        "occurred_at": _now(),
        "payload": payload or {},
    }
    await get_collection(LEGAL_WORKFLOW_TIMELINE).insert_one(event)
    return _serialize(event)


async def _load_run(*, tenant_id: str, app_key: str, run_id: str) -> dict:
    doc = await get_collection(LEGAL_WORKFLOW_RUNS).find_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id}
    )
    if not doc:
        raise WorkflowNotFoundError(f"Workflow run not found: {run_id}")
    return doc


async def _load_steps(*, tenant_id: str, app_key: str, run_id: str) -> list[dict]:
    cursor = get_collection(LEGAL_WORKFLOW_STEPS).find(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id}
    )
    rows = await cursor.to_list(length=200)
    # Stable order by definition sequence then attempt.
    order = {
        s["step_key"]: i
        for i, s in enumerate(
            (get_definition("prepare_matter_response") or {}).get("steps") or []
        )
    }
    rows.sort(
        key=lambda r: (order.get(r.get("step_key"), 99), int(r.get("attempt") or 1))
    )
    return [_serialize(r) for r in rows]


async def _load_artifacts(*, tenant_id: str, app_key: str, run_id: str) -> list[dict]:
    cursor = get_collection(LEGAL_WORKFLOW_ARTIFACTS).find(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id}
    )
    rows = await cursor.to_list(length=200)
    rows.sort(key=lambda r: str(r.get("created_at") or ""))
    return [_serialize(r) for r in rows]


async def _serialize_run(*, tenant_id: str, app_key: str, run: dict) -> dict:
    out = _serialize(run)
    out["steps"] = await _load_steps(
        tenant_id=tenant_id, app_key=app_key, run_id=run["run_id"]
    )
    return out


async def create_workflow_run(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    payload: WorkflowRunCreateRequest,
    auto_advance: bool = True,
) -> dict:
    _require_enabled()
    definition = get_definition(payload.workflow_key)
    if not definition or not definition.get("enabled"):
        raise WorkflowValidationError(
            f"Workflow '{payload.workflow_key}' is not available"
        )
    if definition.get("catalog_status") != "mvp":
        raise WorkflowValidationError(
            f"Workflow '{payload.workflow_key}' is planned, not yet runnable"
        )

    matter = await get_matter(
        tenant_id=tenant_id, app_key=app_key, matter_id=payload.matter_id
    )
    template = resolve_template(payload.workflow_template)
    # Prefer practice-area hint when caller left general.
    if template == "general" and matter.get("practice_area"):
        hinted = recommend_workflow_for(practice_area=matter.get("practice_area"))
        template = hinted["workflow_template"]

    now = _now()
    run_id = str(uuid4())
    run = {
        "run_id": run_id,
        **_scope(tenant_id=tenant_id, app_key=app_key),
        "workflow_key": definition["workflow_key"],
        "workflow_version": int(definition["version"]),
        "workflow_template": template,
        "matter_id": matter["matter_id"],
        "client_id": matter.get("client_id"),
        "alert_id": payload.alert_id,
        "recommended_from": payload.recommended_from,
        "status": "draft",
        "persona": payload.persona or "advocate",
        "ready_to_file": False,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "total_duration_ms": None,
        "approval_count": 0,
        "rejection_count": 0,
        "revision_count": 0,
        "retry_count": 0,
    }
    await get_collection(LEGAL_WORKFLOW_RUNS).insert_one(run)

    steps_col = get_collection(LEGAL_WORKFLOW_STEPS)
    for step_def in definition["steps"]:
        step = {
            "step_id": str(uuid4()),
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "run_id": run_id,
            "step_key": step_def["step_key"],
            "adapter": step_def["adapter"],
            "attempt": 1,
            "status": "pending",
            "failure_class": None,
            "confidence": None,
            "estimated_minutes": int(step_def.get("estimated_minutes") or 5),
            "human_review_required": bool(step_def.get("requires_human_gate")),
            "approved_by": None,
            "approved_at": None,
            "rejection_reason": None,
            "error": None,
            "input_ref": None,
            "output_ref": None,
            "started_at": None,
            "finished_at": None,
            "requires_human_gate": bool(step_def.get("requires_human_gate")),
        }
        await steps_col.insert_one(step)

    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=matter["matter_id"],
        actor_id=actor_id,
        event_type="run_created",
        summary=f"Workflow {definition['workflow_key']} created for {matter.get('matter_number')}",
        payload={
            "workflow_template": template,
            "recommended_from": payload.recommended_from,
        },
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_run_created",
        entity_type="legal_workflow_run",
        entity_id=run_id,
        new_value={
            "matter_id": matter["matter_id"],
            "workflow_key": definition["workflow_key"],
            "workflow_template": template,
        },
    )

    if auto_advance:
        return await advance_workflow_run(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=actor_id,
            run_id=run_id,
            until_blocked=True,
        )
    return await _serialize_run(tenant_id=tenant_id, app_key=app_key, run=run)


async def get_workflow_run(
    *, tenant_id: str, app_key: str, run_id: str
) -> dict:
    _require_enabled()
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    return await _serialize_run(tenant_id=tenant_id, app_key=app_key, run=run)


async def list_workflow_runs(
    *,
    tenant_id: str,
    app_key: str,
    matter_id: str | None = None,
    limit: int = 50,
) -> dict:
    _require_enabled()
    flt: dict[str, Any] = {**_scope(tenant_id=tenant_id, app_key=app_key)}
    if matter_id:
        flt["matter_id"] = matter_id
    cursor = get_collection(LEGAL_WORKFLOW_RUNS).find(flt)
    rows = await cursor.to_list(length=limit)
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    items = []
    for run in rows[:limit]:
        items.append(
            await _serialize_run(tenant_id=tenant_id, app_key=app_key, run=run)
        )
    return {"items": items, "count": len(items)}


async def list_run_timeline(
    *, tenant_id: str, app_key: str, run_id: str, limit: int = 100
) -> dict:
    _require_enabled()
    await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    cursor = get_collection(LEGAL_WORKFLOW_TIMELINE).find(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id}
    )
    rows = await cursor.to_list(length=limit)
    rows.sort(key=lambda r: str(r.get("occurred_at") or ""))
    return {"items": [_serialize(r) for r in rows[:limit]], "count": len(rows[:limit])}


async def list_run_artifacts(
    *, tenant_id: str, app_key: str, run_id: str
) -> dict:
    _require_enabled()
    await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    items = await _load_artifacts(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    return {"items": items, "count": len(items)}


def _latest_attempts(steps: list[dict]) -> list[dict]:
    """One row per step_key — highest attempt."""
    best: dict[str, dict] = {}
    for step in steps:
        key = step["step_key"]
        prev = best.get(key)
        if not prev or int(step.get("attempt") or 1) >= int(prev.get("attempt") or 1):
            best[key] = step
    order = {
        s["step_key"]: i
        for i, s in enumerate(
            (get_definition("prepare_matter_response") or {}).get("steps") or []
        )
    }
    return sorted(best.values(), key=lambda s: order.get(s["step_key"], 99))


async def _execute_step(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run: dict,
    step: dict,
) -> dict:
    adapter_name = step.get("adapter")
    fn = ADAPTER_MAP.get(adapter_name)
    if not fn:
        raise WorkflowValidationError(f"Unknown adapter: {adapter_name}")

    now = _now()
    steps_col = get_collection(LEGAL_WORKFLOW_STEPS)
    await steps_col.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "step_id": step["step_id"]},
        {"$set": {"status": "running", "started_at": now, "error": None}},
    )
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run["run_id"]},
        {
            "$set": {
                "status": "running",
                "updated_at": now,
                "started_at": run.get("started_at") or now,
            }
        },
    )

    prior = await _load_artifacts(
        tenant_id=tenant_id, app_key=app_key, run_id=run["run_id"]
    )
    kwargs: dict[str, Any] = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "matter_id": run["matter_id"],
    }
    if adapter_name in {"matter_intake", "legal_research", "document_evidence", "drafting"}:
        kwargs["workflow_template"] = run.get("workflow_template") or "general"
    if adapter_name in {"drafting", "human_review_gate"}:
        kwargs["prior_artifacts"] = prior

    try:
        result = await fn(**kwargs)
    except PracticeNotFoundError as exc:
        result = {
            "artifact_type": "note",
            "payload": {"error": str(exc)},
            "sources": [],
            "confidence": 0.0,
            "human_review_required": True,
            "failure_class": "permanent",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 — map to retryable step failure
        result = {
            "artifact_type": "note",
            "payload": {"error": "Step execution failed"},
            "sources": [],
            "confidence": 0.0,
            "human_review_required": True,
            "failure_class": "retryable",
            "error": str(exc)[:500],
        }

    finished = _now()
    failure_class = result.get("failure_class")
    error = result.get("error")
    force_human = bool(result.get("force_awaiting_human"))
    human_gate = bool(step.get("requires_human_gate")) or (
        bool(result.get("human_review_required"))
        and step.get("step_key") in {"RESEARCH", "DRAFT", "HUMAN_REVIEW"}
    )

    artifact_id = None
    if result.get("artifact_type"):
        artifact = {
            "artifact_id": str(uuid4()),
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "run_id": run["run_id"],
            "step_id": step["step_id"],
            "artifact_type": result["artifact_type"],
            "payload": _bson_safe(result.get("payload") or {}),
            "sources": _bson_safe(result.get("sources") or []),
            "human_review_required": bool(result.get("human_review_required", True)),
            "created_at": finished,
        }
        await get_collection(LEGAL_WORKFLOW_ARTIFACTS).insert_one(artifact)
        artifact_id = artifact["artifact_id"]

    if failure_class in {"retryable", "requires_human", "permanent"} and error:
        step_status = "failed" if failure_class == "permanent" else (
            "awaiting_human" if failure_class == "requires_human" or force_human else "failed"
        )
        if failure_class == "requires_human" or force_human:
            step_status = "awaiting_human"
        await steps_col.update_one(
            {
                **_scope(tenant_id=tenant_id, app_key=app_key),
                "step_id": step["step_id"],
            },
            {
                "$set": {
                    "status": step_status,
                    "failure_class": failure_class,
                    "confidence": result.get("confidence"),
                    "error": error,
                    "output_ref": artifact_id,
                    "finished_at": finished,
                    "human_review_required": True,
                }
            },
        )
        run_status = (
            "failed"
            if failure_class == "permanent"
            else ("awaiting_human" if step_status == "awaiting_human" else "failed")
        )
        await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run["run_id"]},
            {"$set": {"status": run_status, "updated_at": finished}},
        )
        await _append_run_timeline(
            tenant_id=tenant_id,
            app_key=app_key,
            run_id=run["run_id"],
            matter_id=run.get("matter_id"),
            actor_id=actor_id,
            event_type="step_failed" if run_status == "failed" else "step_blocked",
            summary=f"{step['step_key']} blocked ({failure_class})",
            payload={"step_key": step["step_key"], "failure_class": failure_class},
        )
        return await get_workflow_run(
            tenant_id=tenant_id, app_key=app_key, run_id=run["run_id"]
        )

    # Success path
    if human_gate or force_human:
        step_status = "awaiting_human"
        run_status = "awaiting_human"
        event_type = f"{step['step_key'].lower()}_awaiting_human"
    else:
        step_status = "succeeded"
        run_status = "running"
        event_type = f"{step['step_key'].lower()}_finished"

    await steps_col.update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "step_id": step["step_id"]},
        {
            "$set": {
                "status": step_status,
                "failure_class": None,
                "confidence": result.get("confidence"),
                "error": None,
                "output_ref": artifact_id,
                "finished_at": finished,
                "human_review_required": bool(
                    result.get("human_review_required") or human_gate
                ),
            }
        },
    )

    # COMPLETE success → mark run completed + analytics snapshot
    if step["step_key"] == "COMPLETE" and step_status == "succeeded":
        started = _as_utc_datetime(run.get("started_at")) or finished
        duration_ms = None
        try:
            duration_ms = int((finished - started).total_seconds() * 1000)
        except TypeError:
            duration_ms = None
        await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run["run_id"]},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": finished,
                    "updated_at": finished,
                    "total_duration_ms": duration_ms,
                }
            },
        )
        await _append_run_timeline(
            tenant_id=tenant_id,
            app_key=app_key,
            run_id=run["run_id"],
            matter_id=run.get("matter_id"),
            actor_id=actor_id,
            event_type="run_completed",
            summary="Workflow completed (ready-to-file still requires explicit human marker)",
            payload={"total_duration_ms": duration_ms, "ready_to_file": False},
        )
    else:
        await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
            {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run["run_id"]},
            {"$set": {"status": run_status, "updated_at": finished}},
        )
        await _append_run_timeline(
            tenant_id=tenant_id,
            app_key=app_key,
            run_id=run["run_id"],
            matter_id=run.get("matter_id"),
            actor_id=actor_id,
            event_type=event_type,
            summary=f"{step['step_key']} → {step_status}",
            payload={
                "step_key": step["step_key"],
                "confidence": result.get("confidence"),
                "artifact_id": artifact_id,
            },
        )

    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_step_advanced",
        entity_type="legal_workflow_step",
        entity_id=step["step_id"],
        new_value={"status": step_status, "step_key": step["step_key"]},
    )
    return await get_workflow_run(
        tenant_id=tenant_id, app_key=app_key, run_id=run["run_id"]
    )


async def advance_workflow_run(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run_id: str,
    until_blocked: bool = False,
) -> dict:
    _require_enabled()
    max_loops = 12 if until_blocked else 1
    last = None
    for _ in range(max_loops):
        run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
        if run.get("status") in {"completed", "cancelled", "failed"}:
            return await _serialize_run(tenant_id=tenant_id, app_key=app_key, run=run)
        if run.get("status") == "awaiting_human" and last is not None:
            return last

        steps = _latest_attempts(
            await _load_steps(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
        )
        # Block if any latest attempt awaits human and is not yet approved.
        blocked = next(
            (s for s in steps if s.get("status") == "awaiting_human"),
            None,
        )
        if blocked:
            return await _serialize_run(tenant_id=tenant_id, app_key=app_key, run=run)

        next_step = next((s for s in steps if s.get("status") == "pending"), None)
        if not next_step:
            # Resume a step left "running" after a prior worker crash/timeout.
            next_step = next((s for s in steps if s.get("status") == "running"), None)
        if not next_step:
            # All done without COMPLETE? treat as conflict.
            raise WorkflowConflictError("No pending step to advance")

        last = await _execute_step(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=actor_id,
            run=run,
            step=next_step,
        )
        if last.get("status") in {"awaiting_human", "completed", "failed", "cancelled"}:
            return last
        if not until_blocked:
            return last
    return last or await get_workflow_run(
        tenant_id=tenant_id, app_key=app_key, run_id=run_id
    )


async def approve_workflow_step(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run_id: str,
    step_id: str,
    auto_advance: bool = True,
) -> dict:
    _require_enabled()
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    step = await get_collection(LEGAL_WORKFLOW_STEPS).find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "run_id": run_id,
            "step_id": step_id,
        }
    )
    if not step:
        raise WorkflowNotFoundError(f"Step not found: {step_id}")
    if step.get("status") != "awaiting_human":
        raise WorkflowConflictError(
            f"Step {step.get('step_key')} cannot be approved from status {step.get('status')}"
        )

    now = _now()
    await get_collection(LEGAL_WORKFLOW_STEPS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "step_id": step_id},
        {
            "$set": {
                "status": "approved",
                "approved_by": actor_id,
                "approved_at": now,
                "finished_at": step.get("finished_at") or now,
            }
        },
    )
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id},
        {
            "$set": {"status": "running", "updated_at": now},
            "$inc": {"approval_count": 1},
        },
    )
    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=run.get("matter_id"),
        actor_id=actor_id,
        event_type="human_approved",
        summary=f"{step.get('step_key')} approved",
        payload={"step_id": step_id, "step_key": step.get("step_key")},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_step_approved",
        entity_type="legal_workflow_step",
        entity_id=step_id,
        new_value={"step_key": step.get("step_key")},
    )
    if auto_advance:
        return await advance_workflow_run(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=actor_id,
            run_id=run_id,
            until_blocked=True,
        )
    return await get_workflow_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)


async def reject_workflow_step(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run_id: str,
    step_id: str,
    payload: WorkflowStepRejectRequest,
) -> dict:
    _require_enabled()
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    step = await get_collection(LEGAL_WORKFLOW_STEPS).find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "run_id": run_id,
            "step_id": step_id,
        }
    )
    if not step:
        raise WorkflowNotFoundError(f"Step not found: {step_id}")
    if step.get("status") != "awaiting_human":
        raise WorkflowConflictError("Only awaiting_human steps can be rejected")

    now = _now()
    await get_collection(LEGAL_WORKFLOW_STEPS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "step_id": step_id},
        {
            "$set": {
                "status": "rejected",
                "rejection_reason": payload.reason,
                "failure_class": "requires_human",
                "finished_at": now,
            }
        },
    )
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id},
        {
            "$set": {"status": "awaiting_human", "updated_at": now},
            "$inc": {"rejection_count": 1},
        },
    )
    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=run.get("matter_id"),
        actor_id=actor_id,
        event_type="human_rejected",
        summary=f"{step.get('step_key')} rejected",
        payload={"step_id": step_id, "reason": payload.reason},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_step_rejected",
        entity_type="legal_workflow_step",
        entity_id=step_id,
        new_value={"reason": payload.reason},
    )
    return await get_workflow_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)


async def retry_workflow_step(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run_id: str,
    step_id: str,
) -> dict:
    _require_enabled()
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    step = await get_collection(LEGAL_WORKFLOW_STEPS).find_one(
        {
            **_scope(tenant_id=tenant_id, app_key=app_key),
            "run_id": run_id,
            "step_id": step_id,
        }
    )
    if not step:
        raise WorkflowNotFoundError(f"Step not found: {step_id}")
    if step.get("failure_class") not in {"retryable", "requires_human"} and step.get(
        "status"
    ) not in {"failed", "rejected", "awaiting_human"}:
        raise WorkflowConflictError("Step is not eligible for retry")
    if step.get("failure_class") == "permanent":
        raise WorkflowConflictError("Permanent failures cannot be retried")

    # New attempt row; prior remains auditable.
    new_step = {
        **{k: v for k, v in step.items() if k != "_id"},
        "step_id": str(uuid4()),
        "attempt": int(step.get("attempt") or 1) + 1,
        "status": "pending",
        "failure_class": None,
        "confidence": None,
        "approved_by": None,
        "approved_at": None,
        "rejection_reason": None,
        "error": None,
        "input_ref": None,
        "output_ref": None,
        "started_at": None,
        "finished_at": None,
    }
    await get_collection(LEGAL_WORKFLOW_STEPS).insert_one(new_step)
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id},
        {
            "$set": {"status": "running", "updated_at": _now()},
            "$inc": {"retry_count": 1, "revision_count": 1},
        },
    )
    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=run.get("matter_id"),
        actor_id=actor_id,
        event_type="step_retried",
        summary=f"{step.get('step_key')} retry attempt {new_step['attempt']}",
        payload={"step_key": step.get("step_key"), "attempt": new_step["attempt"]},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_step_retried",
        entity_type="legal_workflow_step",
        entity_id=new_step["step_id"],
        new_value={"attempt": new_step["attempt"]},
    )
    return await advance_workflow_run(
        tenant_id=tenant_id,
        app_key=app_key,
        actor_id=actor_id,
        run_id=run_id,
        until_blocked=True,
    )


async def cancel_workflow_run(
    *, tenant_id: str, app_key: str, actor_id: str, run_id: str
) -> dict:
    _require_enabled()
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    if run.get("status") in {"completed", "cancelled"}:
        raise WorkflowConflictError(f"Run already {run.get('status')}")
    now = _now()
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=run.get("matter_id"),
        actor_id=actor_id,
        event_type="run_cancelled",
        summary="Workflow soft-cancelled",
        payload={},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_run_cancelled",
        entity_type="legal_workflow_run",
        entity_id=run_id,
    )
    return await get_workflow_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)


async def set_ready_to_file(
    *,
    tenant_id: str,
    app_key: str,
    actor_id: str,
    run_id: str,
    payload: ReadyToFileRequest,
) -> dict:
    """Human readiness marker only — never files or sends."""
    _require_enabled()
    if not payload.confirm:
        raise WorkflowValidationError("confirm=true is required")
    run = await _load_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)
    if run.get("status") != "completed":
        raise WorkflowConflictError("ready_to_file only after workflow completion")
    now = _now()
    await get_collection(LEGAL_WORKFLOW_RUNS).update_one(
        {**_scope(tenant_id=tenant_id, app_key=app_key), "run_id": run_id},
        {"$set": {"ready_to_file": bool(payload.ready_to_file), "updated_at": now}},
    )
    await _append_run_timeline(
        tenant_id=tenant_id,
        app_key=app_key,
        run_id=run_id,
        matter_id=run.get("matter_id"),
        actor_id=actor_id,
        event_type="ready_to_file_marked",
        summary=(
            "Human marked ready to file (no filing or send occurred)"
            if payload.ready_to_file
            else "Ready-to-file marker cleared"
        ),
        payload={"ready_to_file": payload.ready_to_file, "filed": False, "sent": False},
    )
    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=actor_id,
        action="legal_workflow_ready_to_file",
        entity_type="legal_workflow_run",
        entity_id=run_id,
        new_value={"ready_to_file": payload.ready_to_file, "filed": False, "sent": False},
    )
    return await get_workflow_run(tenant_id=tenant_id, app_key=app_key, run_id=run_id)


async def get_kg_subgraph(
    *,
    tenant_id: str,
    app_key: str,
    family: str | None = None,
    limit: int = 50,
) -> dict:
    """Read-only KG MVP slice. Empty is a valid miss → Stage 2 path unchanged."""
    _require_enabled()
    scope = _scope(tenant_id=tenant_id, app_key=app_key)
    node_flt = dict(scope)
    if family:
        node_flt["family"] = family
    nodes = await get_collection(LEGAL_KG_NODES).find(node_flt).to_list(length=limit)
    edges = await get_collection(LEGAL_KG_EDGES).find(scope).to_list(length=limit)
    return {
        "nodes": [_serialize(n) for n in nodes],
        "edges": [_serialize(e) for e in edges],
        "count_nodes": len(nodes),
        "count_edges": len(edges),
        "enrichment_only": True,
        "note": (
            "Knowledge graph is optional research enrichment only. "
            "Graph miss degrades to Stage 2 hybrid research; never invent edges."
        ),
    }
