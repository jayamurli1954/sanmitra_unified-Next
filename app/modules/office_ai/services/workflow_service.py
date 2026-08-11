"""OfficeMitra workflow engine (ADR-009).

Templates are reusable definitions; runs are executable instances.
Every step goes through the Action Executor (no parallel executor).
Companion targets remain forbidden until ADR-010 is Accepted.
"""
from __future__ import annotations

import time
from typing import Any, Iterable

from bson import ObjectId

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.office_ai.actions import ActionExecutionError, execute_action, get_action
from app.modules.office_ai.actions.executor import EXECUTOR_VERSION
from app.modules.office_ai.actions.registry import ensure_default_actions_registered
from app.modules.office_ai.models import (
    WORKFLOW_RUN_STATUSES,
    WORKFLOW_RUNS_COLLECTION,
    WORKFLOW_STEP_STATUSES,
    WORKFLOW_TEMPLATES_COLLECTION,
    WORKFLOW_TRIGGER_SOURCES,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)
from app.modules.office_ai.policy import PolicyContext, PolicyDeniedError, evaluate_policy, log_policy_decision


def _user_id(user: dict) -> str:
    return str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or "unknown"


def _user_roles(user: dict) -> list[str]:
    roles: list[str] = []
    raw = user.get("roles")
    if isinstance(raw, (list, tuple, set)):
        roles.extend(str(r).strip().lower() for r in raw if str(r).strip())
    single = str(user.get("role") or "").strip().lower()
    if single and single not in roles:
        roles.append(single)
    return roles


def _normalize_steps(steps: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    ensure_default_actions_registered()
    out: list[dict[str, Any]] = []
    for idx, raw in enumerate(steps or []):
        if not isinstance(raw, dict):
            continue
        action_type = str(raw.get("action_type") or "").strip().lower()
        if not action_type:
            raise ValueError(f"steps[{idx}].action_type is required")
        spec = get_action(action_type)
        if spec is None:
            raise ValueError(f"Unknown action_type: {action_type}")
        if str(spec.target_module).strip().lower() != "office_ai":
            raise ValueError("Workflow steps may only target office_ai under ADR-009")
        step_id = str(raw.get("step_id") or f"step-{idx + 1}").strip()[:80] or f"step-{idx + 1}"
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        out.append(
            {
                "step_id": step_id,
                "action_type": spec.action_type,
                "payload": payload,
            }
        )
    if not out:
        raise ValueError("At least one workflow step is required")
    return out


async def create_template(
    *,
    tenant_id: str,
    user: dict,
    name: str,
    steps: list[dict[str, Any]],
    description: str | None = None,
    template_key: str | None = None,
    continue_on_failure: bool = False,
    version: int | None = None,
) -> dict:
    await ensure_indexes()
    uid = _user_id(user)
    now = utcnow()
    normalized_steps = _normalize_steps(steps)
    key = (str(template_key or name).strip().lower().replace(" ", "-")[:120]) or "workflow"
    next_version = version
    if next_version is None:
        existing = (
            await get_collection(WORKFLOW_TEMPLATES_COLLECTION)
            .find({"tenant_id": tenant_id, "template_key": key})
            .sort("version", -1)
            .limit(1)
            .to_list(length=1)
        )
        next_version = int((existing[0].get("version") if existing else 0) or 0) + 1
    doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "template_key": key,
        "name": str(name or "").strip()[:200] or key,
        "description": (str(description or "").strip()[:2000] or None),
        "version": int(next_version),
        "continue_on_failure": bool(continue_on_failure),
        "steps": normalized_steps,
        "created_by": uid,
        "updated_by": uid,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(WORKFLOW_TEMPLATES_COLLECTION).insert_one(doc)
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=uid,
        product="officemitra",
        action="workflow.template.create",
        entity_type="officemitra_workflow_template",
        entity_id=str(doc["_id"]),
        new_value={"template_key": key, "version": doc["version"], "step_count": len(normalized_steps)},
    )
    return serialize_doc(doc)


async def list_templates(*, tenant_id: str, limit: int = 50) -> list[dict]:
    await ensure_indexes()
    cursor = (
        get_collection(WORKFLOW_TEMPLATES_COLLECTION)
        .find({"tenant_id": tenant_id})
        .sort([("template_key", 1), ("version", -1)])
        .limit(min(limit, 100))
    )
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 100))]


async def get_template(*, tenant_id: str, template_id: str) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(template_id):
        return None
    doc = await get_collection(WORKFLOW_TEMPLATES_COLLECTION).find_one(
        {"_id": ObjectId(template_id), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def list_runs(*, tenant_id: str, limit: int = 50) -> list[dict]:
    await ensure_indexes()
    cursor = (
        get_collection(WORKFLOW_RUNS_COLLECTION)
        .find({"tenant_id": tenant_id})
        .sort("created_at", -1)
        .limit(min(limit, 100))
    )
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 100))]


async def get_run(*, tenant_id: str, run_id: str) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(run_id):
        return None
    doc = await get_collection(WORKFLOW_RUNS_COLLECTION).find_one(
        {"_id": ObjectId(run_id), "tenant_id": tenant_id}
    )
    return serialize_doc(doc)


async def start_run(
    *,
    tenant_id: str,
    user: dict,
    template_id: str,
    trigger_source: str = "manual",
    idempotency_key: str | None = None,
    proposal_id: str | None = None,
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
) -> dict:
    """Start (or return existing idempotent) workflow run and execute steps synchronously."""
    await ensure_indexes()
    uid = _user_id(user)
    source = str(trigger_source or "manual").strip().lower()
    if source not in WORKFLOW_TRIGGER_SOURCES:
        raise ValueError(f"Invalid trigger_source: {trigger_source}")

    modules = list(enabled_modules or ["office_ai", "office_ai.workflows"])
    features = list(office_ai_features or [])

    key = (str(idempotency_key or "").strip()[:200] or None)
    if key:
        existing = await get_collection(WORKFLOW_RUNS_COLLECTION).find_one(
            {"tenant_id": tenant_id, "idempotency_key": key}
        )
        if existing:
            return {"run": serialize_doc(existing), "idempotent_replay": True}

    template = await get_template(tenant_id=tenant_id, template_id=template_id)
    if template is None:
        raise ValueError("Workflow template not found")

    steps = list(template.get("steps") or [])
    # Preflight policy on every step before creating a run (ADR-012).
    now = utcnow()
    for step in steps:
        action_type = str(step.get("action_type") or "")
        ctx = PolicyContext(
            tenant_id=tenant_id,
            actor_id=uid,
            actor_roles=_user_roles(user),
            action_type=action_type,
            target_module="office_ai",
            intent="start_workflow",
            enabled_modules=modules,
            office_ai_features=features,
            required_feature="workflows",
            maker_id=uid,
            confirmed_at=now,
        )
        decision = evaluate_policy(ctx)
        await log_policy_decision(ctx=ctx, decision=decision)
        if not decision.allowed:
            raise PolicyDeniedError(decision)

    step_results = [
        {
            "step_id": step.get("step_id"),
            "action_type": step.get("action_type"),
            "status": "pending",
            "started_at": None,
            "finished_at": None,
            "duration_ms": None,
            "retry_count": 0,
            "executor_version": None,
            "error_message": None,
            "result": None,
        }
        for step in steps
    ]
    run_doc = {
        "_id": new_object_id(),
        "tenant_id": tenant_id,
        "template_id": template.get("id"),
        "template_key": template.get("template_key"),
        "template_version": template.get("version"),
        "proposal_id": (str(proposal_id).strip()[:64] if proposal_id else None),
        "trigger_source": source,
        "idempotency_key": key,
        "actor": uid,
        "status": "pending",
        "continue_on_failure": bool(template.get("continue_on_failure")),
        "step_results": step_results,
        "started_at": None,
        "finished_at": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await get_collection(WORKFLOW_RUNS_COLLECTION).insert_one(run_doc)
    except Exception as exc:
        # Race on unique idempotency_key — return the winner.
        if key and "duplicate" in str(exc).lower():
            existing = await get_collection(WORKFLOW_RUNS_COLLECTION).find_one(
                {"tenant_id": tenant_id, "idempotency_key": key}
            )
            if existing:
                return {"run": serialize_doc(existing), "idempotent_replay": True}
        raise

    executed = await _execute_run(
        tenant_id=tenant_id,
        user=user,
        run_doc=run_doc,
        template_steps=steps,
        enabled_modules=modules,
        office_ai_features=features,
    )
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=uid,
        product="officemitra",
        action="workflow.run.start",
        entity_type="officemitra_workflow_run",
        entity_id=str(run_doc["_id"]),
        new_value={
            "template_id": template.get("id"),
            "template_version": template.get("version"),
            "trigger_source": source,
            "status": executed.get("status"),
        },
    )
    return {"run": executed, "idempotent_replay": False}


async def _execute_run(
    *,
    tenant_id: str,
    user: dict,
    run_doc: dict,
    template_steps: list[dict],
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
) -> dict:
    col = get_collection(WORKFLOW_RUNS_COLLECTION)
    run_id = run_doc["_id"]
    started = utcnow()
    step_results = list(run_doc.get("step_results") or [])
    continue_on_failure = bool(run_doc.get("continue_on_failure"))
    overall_status = "running"
    overall_error: str | None = None
    modules = list(enabled_modules or ["office_ai", "office_ai.workflows"])
    features = list(office_ai_features or [])
    uid = _user_id(user)

    await col.update_one(
        {"_id": run_id, "tenant_id": tenant_id},
        {"$set": {"status": "running", "started_at": started, "updated_at": started}},
    )

    for idx, step in enumerate(template_steps):
        step_started = utcnow()
        t0 = time.perf_counter()
        step_results[idx]["status"] = "running"
        step_results[idx]["started_at"] = step_started.isoformat()
        step_results[idx]["executor_version"] = EXECUTOR_VERSION
        await col.update_one(
            {"_id": run_id, "tenant_id": tenant_id},
            {"$set": {"step_results": step_results, "updated_at": utcnow()}},
        )
        try:
            step_ctx = PolicyContext(
                tenant_id=tenant_id,
                actor_id=uid,
                actor_roles=_user_roles(user),
                action_type=str(step.get("action_type") or ""),
                target_module="office_ai",
                intent="execute",
                enabled_modules=modules,
                office_ai_features=features,
                required_feature="workflows",
                workflow_run_id=str(run_id),
                maker_id=uid,
                confirmed_at=started,
            )
            step_decision = evaluate_policy(step_ctx)
            if not step_decision.allowed:
                raise PolicyDeniedError(step_decision)

            result = await execute_action(
                action_type=str(step.get("action_type")),
                tenant_id=tenant_id,
                user=user,
                payload=step.get("payload") if isinstance(step.get("payload"), dict) else {},
                proposal_id=run_doc.get("proposal_id"),
            )
            finished = utcnow()
            duration_ms = int((time.perf_counter() - t0) * 1000)
            step_results[idx].update(
                {
                    "status": "applied",
                    "finished_at": finished.isoformat(),
                    "duration_ms": duration_ms,
                    "retry_count": 0,
                    "executor_version": (result or {}).get("executor_version") or EXECUTOR_VERSION,
                    "error_message": None,
                    "result": result,
                    "policy": step_decision.to_dict(),
                }
            )
        except (PolicyDeniedError, ActionExecutionError, ValueError, Exception) as exc:
            finished = utcnow()
            duration_ms = int((time.perf_counter() - t0) * 1000)
            err = str(exc)[:2000]
            if isinstance(exc, PolicyDeniedError):
                err = f"{exc.decision.rule_id}: {exc.decision.reason}"
            step_results[idx].update(
                {
                    "status": "failed",
                    "finished_at": finished.isoformat(),
                    "duration_ms": duration_ms,
                    "retry_count": 0,
                    "executor_version": EXECUTOR_VERSION,
                    "error_message": err,
                    "result": None,
                }
            )
            overall_error = err
            if not continue_on_failure:
                # Mark remaining steps skipped (stop-on-failure).
                for j in range(idx + 1, len(step_results)):
                    if step_results[j].get("status") == "pending":
                        step_results[j]["status"] = "skipped"
                overall_status = "failed"
                break
            overall_status = "failed"

    if overall_status == "running":
        overall_status = "failed" if overall_error else "applied"
    # If continue_on_failure and any failed, status is failed even if later steps applied.
    if any(s.get("status") == "failed" for s in step_results):
        overall_status = "failed"
    elif all(s.get("status") == "applied" for s in step_results):
        overall_status = "applied"

    if overall_status not in WORKFLOW_RUN_STATUSES:
        overall_status = "failed"
    for s in step_results:
        if s.get("status") not in WORKFLOW_STEP_STATUSES:
            s["status"] = "failed"

    finished_at = utcnow()
    await col.update_one(
        {"_id": run_id, "tenant_id": tenant_id},
        {
            "$set": {
                "status": overall_status,
                "step_results": step_results,
                "finished_at": finished_at,
                "error_message": overall_error,
                "updated_at": finished_at,
            }
        },
    )
    updated = await col.find_one({"_id": run_id, "tenant_id": tenant_id})
    return serialize_doc(updated)
