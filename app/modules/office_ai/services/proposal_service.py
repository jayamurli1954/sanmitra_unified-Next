"""OfficeMitra confirmed write-back proposals (ADR-008) + policy gate (ADR-012).

Lifecycle:
  draft → pending → confirmed → applied | failed
                 ↘ awaiting_checker → (checker approve) → applied | failed
                 ↘ dismissed | expired

AI creates pending proposals. Human confirm (and optional checker) runs
the Action Executor only after Policy Engine allows execution.
Nothing mutates companion products — only registered office_ai actions.
"""
from __future__ import annotations

from typing import Any, Iterable

from bson import ObjectId

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.office_ai.actions import ActionExecutionError, execute_action, get_action
from app.modules.office_ai.actions.registry import ensure_default_actions_registered
from app.modules.office_ai.models import (
    PROPOSAL_STATUSES,
    PROPOSALS_COLLECTION,
    ensure_indexes,
    new_object_id,
    serialize_doc,
    utcnow,
)
from app.modules.office_ai.policy import (
    DEFAULT_APPROVAL_EXPIRY_HOURS,
    PolicyContext,
    PolicyDeniedError,
    evaluate_policy,
    log_policy_decision,
)
from app.modules.office_ai.policy.engine import compute_approval_expires_at


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


def _clamp_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return None
    if conf < 0:
        return 0.0
    if conf > 1:
        return 1.0
    return conf


def _policy_ctx(
    *,
    tenant_id: str,
    user: dict,
    action_type: str,
    target_module: str,
    intent: str,
    enabled_modules: Iterable[str] | None,
    office_ai_features: Iterable[str] | None,
    proposal_id: str | None = None,
    maker_id: str | None = None,
    checker_id: str | None = None,
    confirmed_at: Any = None,
    approval_expires_at: Any = None,
    allow_self_approval: bool = False,
    approval_expiry_hours: int = DEFAULT_APPROVAL_EXPIRY_HOURS,
    required_feature: str | None = None,
) -> PolicyContext:
    return PolicyContext(
        tenant_id=tenant_id,
        actor_id=_user_id(user),
        actor_roles=_user_roles(user),
        action_type=action_type,
        target_module=target_module or "office_ai",
        intent=intent,  # type: ignore[arg-type]
        enabled_modules=list(enabled_modules or []),
        office_ai_features=list(office_ai_features or []),
        required_feature=required_feature,
        proposal_id=proposal_id,
        maker_id=maker_id,
        checker_id=checker_id,
        confirmed_at=confirmed_at,
        approval_expires_at=approval_expires_at,
        allow_self_approval=allow_self_approval,
        approval_expiry_hours=approval_expiry_hours,
    )


async def list_proposals(
    *,
    tenant_id: str,
    status: str | None = "pending",
    limit: int = 50,
) -> list[dict]:
    await ensure_indexes()
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if status:
        normalized = str(status).strip().lower()
        if normalized == "open":
            query["status"] = {"$in": ["pending", "awaiting_checker"]}
        elif normalized in PROPOSAL_STATUSES:
            query["status"] = normalized
    cursor = (
        get_collection(PROPOSALS_COLLECTION)
        .find(query)
        .sort("created_at", -1)
        .limit(min(limit, 100))
    )
    return [serialize_doc(doc) for doc in await cursor.to_list(length=min(limit, 100))]


async def create_proposals(
    *,
    tenant_id: str,
    user: dict,
    action_type: str,
    items: list[dict[str, Any]],
    source_feature: str = "tasks.generate",
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    target_module: str = "office_ai",
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
) -> list[dict]:
    """Create pending action proposals (generic; not task-hardcoded)."""
    ensure_default_actions_registered()
    spec = get_action(action_type)
    if spec is None:
        raise ValueError(f"Unknown action_type: {action_type}")
    if str(target_module or spec.target_module).strip().lower() != "office_ai":
        raise ValueError("Proposals may only target office_ai under ADR-008")

    ctx = _policy_ctx(
        tenant_id=tenant_id,
        user=user,
        action_type=spec.action_type,
        target_module="office_ai",
        intent="propose",
        enabled_modules=enabled_modules if enabled_modules is not None else ["office_ai", "office_ai.writeback"],
        office_ai_features=office_ai_features,
    )
    decision = evaluate_policy(ctx)
    await log_policy_decision(ctx=ctx, decision=decision)
    if not decision.allowed:
        raise PolicyDeniedError(decision)

    await ensure_indexes()
    now = utcnow()
    uid = _user_id(user)
    caps = spec.capabilities
    expiry_hours = decision.approval_expiry_hours or DEFAULT_APPROVAL_EXPIRY_HOURS
    saved: list[dict] = []
    for item in items:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else item
        if action_type == "create_task":
            title = str(payload.get("title") or "").strip()
            if not title:
                continue
            payload = {
                "title": title[:500],
                "notes": (str(payload.get("notes") or "").strip()[:4000] or None),
                "due_date": payload.get("due_date"),
            }
        doc = {
            "_id": new_object_id(),
            "tenant_id": tenant_id,
            "action_type": spec.action_type,
            "target_module": "office_ai",
            "status": "pending",
            "payload": payload,
            "confidence": _clamp_confidence(item.get("confidence")),
            "reasoning": (str(item.get("reasoning") or "").strip()[:2000] or None),
            "requires_confirmation": bool(caps.requires_confirmation or caps.requires_maker_checker),
            "requires_maker_checker": bool(caps.requires_maker_checker),
            "risk_level": caps.risk_level,
            "approval_expiry_hours": expiry_hours,
            "policy_decision": decision.to_dict(),
            "source_feature": str(source_feature or "")[:120],
            "prompt_version": prompt_version,
            "ai_telemetry_id": (
                ObjectId(ai_telemetry_id) if ai_telemetry_id and ObjectId.is_valid(ai_telemetry_id) else None
            ),
            "result": None,
            "error_message": None,
            "maker_id": None,
            "checker_id": None,
            "approval_expires_at": None,
            "created_at": now,
            "updated_at": now,
            "created_by": uid,
            "updated_by": uid,
            "confirmed_at": None,
            "resolved_at": None,
            "resolved_by": None,
        }
        await get_collection(PROPOSALS_COLLECTION).insert_one(doc)
        saved.append(serialize_doc(doc))
    return saved


async def create_task_proposals(
    *,
    tenant_id: str,
    user: dict,
    tasks: list[dict[str, Any]],
    source_feature: str = "tasks.generate",
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
) -> list[dict]:
    """Compatibility wrapper used by task generate when writeback is on."""
    return await create_proposals(
        tenant_id=tenant_id,
        user=user,
        action_type="create_task",
        items=list(tasks or []),
        source_feature=source_feature,
        prompt_version=prompt_version,
        ai_telemetry_id=ai_telemetry_id,
        enabled_modules=enabled_modules,
        office_ai_features=office_ai_features,
    )


async def _mark_expired_if_needed(col, doc: dict, proposal_id: str, tenant_id: str) -> dict | None:
    from app.modules.office_ai.policy.engine import _parse_dt

    expires = _parse_dt(doc.get("approval_expires_at"))
    if expires is None:
        return None
    now = utcnow()
    if now <= expires:
        return None
    await col.update_one(
        {"_id": ObjectId(proposal_id), "tenant_id": tenant_id},
        {
            "$set": {
                "status": "expired",
                "updated_at": now,
                "error_message": "Approval expired; restart the proposal confirmation",
            }
        },
    )
    updated = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
    return serialize_doc(updated)


async def confirm_proposal(
    *,
    tenant_id: str,
    user: dict,
    proposal_id: str,
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
    allow_self_approval: bool = False,
) -> dict | None:
    """Confirm as maker; execute when policy allows, else await checker."""
    await ensure_indexes()
    if not ObjectId.is_valid(proposal_id):
        return None
    col = get_collection(PROPOSALS_COLLECTION)
    doc = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
    if not doc:
        return None
    if doc.get("status") in {"applied", "failed", "dismissed", "expired"}:
        return {"proposal": serialize_doc(doc), "result": doc.get("result")}
    if doc.get("status") == "awaiting_checker":
        return {
            "proposal": serialize_doc(doc),
            "result": None,
            "policy": {"decision": "REQUIRE_MAKER_CHECKER", "reason": "Awaiting checker approval"},
        }
    if doc.get("status") != "pending":
        return {"proposal": serialize_doc(doc), "result": doc.get("result")}

    expired = await _mark_expired_if_needed(col, doc, proposal_id, tenant_id)
    if expired:
        return {"proposal": expired, "result": None, "error": "Approval expired"}

    modules = list(enabled_modules or ["office_ai", "office_ai.writeback"])
    uid = _user_id(user)
    action = str(doc.get("action_type") or "")
    expiry_hours = int(doc.get("approval_expiry_hours") or DEFAULT_APPROVAL_EXPIRY_HOURS)

    ctx = _policy_ctx(
        tenant_id=tenant_id,
        user=user,
        action_type=action,
        target_module=str(doc.get("target_module") or "office_ai"),
        intent="confirm",
        enabled_modules=modules,
        office_ai_features=office_ai_features,
        proposal_id=proposal_id,
        allow_self_approval=allow_self_approval,
        approval_expiry_hours=expiry_hours,
    )
    decision = evaluate_policy(ctx)
    await log_policy_decision(ctx=ctx, decision=decision)
    if not decision.allowed:
        raise PolicyDeniedError(decision)

    now = utcnow()
    expires_at = compute_approval_expires_at(from_time=now, hours=expiry_hours)

    if decision.execution_mode == "maker_checker":
        await col.update_one(
            {"_id": ObjectId(proposal_id), "tenant_id": tenant_id, "status": "pending"},
            {
                "$set": {
                    "status": "awaiting_checker",
                    "maker_id": uid,
                    "confirmed_at": now,
                    "approval_expires_at": expires_at,
                    "updated_at": now,
                    "updated_by": uid,
                    "policy_decision": decision.to_dict(),
                }
            },
        )
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=uid,
            product="officemitra",
            action="proposal.maker_confirm",
            entity_type="officemitra_proposal",
            entity_id=proposal_id,
            old_value={"status": "pending"},
            new_value={"status": "awaiting_checker", "rule_id": decision.rule_id},
        )
        updated = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
        return {"proposal": serialize_doc(updated), "result": None, "policy": decision.to_dict()}

    # confirmation / immediate → execute
    await col.update_one(
        {"_id": ObjectId(proposal_id), "tenant_id": tenant_id, "status": "pending"},
        {
            "$set": {
                "status": "confirmed",
                "maker_id": uid,
                "confirmed_at": now,
                "approval_expires_at": expires_at,
                "updated_at": now,
                "updated_by": uid,
                "policy_decision": decision.to_dict(),
            }
        },
    )
    return await _execute_confirmed(
        col=col,
        doc=doc,
        tenant_id=tenant_id,
        user=user,
        proposal_id=proposal_id,
        maker_id=uid,
        checker_id=None,
        enabled_modules=modules,
        office_ai_features=office_ai_features,
        allow_self_approval=allow_self_approval,
    )


async def approve_proposal(
    *,
    tenant_id: str,
    user: dict,
    proposal_id: str,
    enabled_modules: Iterable[str] | None = None,
    office_ai_features: Iterable[str] | None = None,
    allow_self_approval: bool = False,
) -> dict | None:
    """Checker approval for maker-checker proposals (ADR-012)."""
    await ensure_indexes()
    if not ObjectId.is_valid(proposal_id):
        return None
    col = get_collection(PROPOSALS_COLLECTION)
    doc = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
    if not doc:
        return None
    if doc.get("status") != "awaiting_checker":
        return {"proposal": serialize_doc(doc), "result": doc.get("result")}

    expired = await _mark_expired_if_needed(col, doc, proposal_id, tenant_id)
    if expired:
        return {"proposal": expired, "result": None, "error": "Approval expired"}

    modules = list(enabled_modules or ["office_ai", "office_ai.writeback"])
    uid = _user_id(user)
    action = str(doc.get("action_type") or "")
    expiry_hours = int(doc.get("approval_expiry_hours") or DEFAULT_APPROVAL_EXPIRY_HOURS)

    ctx = _policy_ctx(
        tenant_id=tenant_id,
        user=user,
        action_type=action,
        target_module=str(doc.get("target_module") or "office_ai"),
        intent="approve",
        enabled_modules=modules,
        office_ai_features=office_ai_features,
        proposal_id=proposal_id,
        maker_id=doc.get("maker_id"),
        confirmed_at=doc.get("confirmed_at"),
        approval_expires_at=doc.get("approval_expires_at"),
        allow_self_approval=allow_self_approval,
        approval_expiry_hours=expiry_hours,
    )
    decision = evaluate_policy(ctx)
    await log_policy_decision(ctx=ctx, decision=decision)
    if not decision.allowed:
        raise PolicyDeniedError(decision)

    now = utcnow()
    await col.update_one(
        {"_id": ObjectId(proposal_id), "tenant_id": tenant_id, "status": "awaiting_checker"},
        {
            "$set": {
                "status": "confirmed",
                "checker_id": uid,
                "updated_at": now,
                "updated_by": uid,
                "policy_decision": decision.to_dict(),
            }
        },
    )
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=uid,
        product="officemitra",
        action="proposal.checker_approve",
        entity_type="officemitra_proposal",
        entity_id=proposal_id,
        old_value={"status": "awaiting_checker"},
        new_value={"status": "confirmed", "rule_id": decision.rule_id},
    )
    return await _execute_confirmed(
        col=col,
        doc=doc,
        tenant_id=tenant_id,
        user=user,
        proposal_id=proposal_id,
        maker_id=str(doc.get("maker_id") or ""),
        checker_id=uid,
        enabled_modules=modules,
        office_ai_features=office_ai_features,
        allow_self_approval=allow_self_approval,
    )


async def _execute_confirmed(
    *,
    col,
    doc: dict,
    tenant_id: str,
    user: dict,
    proposal_id: str,
    maker_id: str,
    checker_id: str | None,
    enabled_modules: Iterable[str] | None,
    office_ai_features: Iterable[str] | None,
    allow_self_approval: bool,
) -> dict:
    uid = _user_id(user)
    action = str(doc.get("action_type") or "")
    expiry_hours = int(doc.get("approval_expiry_hours") or DEFAULT_APPROVAL_EXPIRY_HOURS)

    exec_ctx = _policy_ctx(
        tenant_id=tenant_id,
        user=user,
        action_type=action,
        target_module=str(doc.get("target_module") or "office_ai"),
        intent="execute",
        enabled_modules=enabled_modules,
        office_ai_features=office_ai_features,
        proposal_id=proposal_id,
        maker_id=maker_id,
        checker_id=checker_id,
        confirmed_at=doc.get("confirmed_at") or utcnow(),
        approval_expires_at=doc.get("approval_expires_at"),
        allow_self_approval=allow_self_approval,
        approval_expiry_hours=expiry_hours,
    )
    exec_decision = evaluate_policy(exec_ctx)
    await log_policy_decision(ctx=exec_ctx, decision=exec_decision)
    if not exec_decision.allowed:
        raise PolicyDeniedError(exec_decision)

    try:
        result = await execute_action(
            action_type=action,
            tenant_id=tenant_id,
            user=user,
            payload=doc.get("payload") if isinstance(doc.get("payload"), dict) else {},
            prompt_version=doc.get("prompt_version"),
            ai_telemetry_id=str(doc.get("ai_telemetry_id") or "") or None,
            proposal_id=proposal_id,
        )
        applied_at = utcnow()
        await col.update_one(
            {"_id": ObjectId(proposal_id), "tenant_id": tenant_id},
            {
                "$set": {
                    "status": "applied",
                    "result": result,
                    "error_message": None,
                    "updated_at": applied_at,
                    "updated_by": uid,
                    "resolved_at": applied_at,
                    "resolved_by": uid,
                    "policy_decision": exec_decision.to_dict(),
                }
            },
        )
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=uid,
            product="officemitra",
            action="proposal.apply",
            entity_type="officemitra_proposal",
            entity_id=proposal_id,
            old_value={"status": "confirmed"},
            new_value={
                "status": "applied",
                "action_type": action,
                "target_module": doc.get("target_module") or "office_ai",
                "result_entity_id": (result or {}).get("entity_id"),
                "rule_id": exec_decision.rule_id,
            },
        )
        updated = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
        return {"proposal": serialize_doc(updated), "result": result, "policy": exec_decision.to_dict()}
    except ActionExecutionError as exc:
        failed_at = utcnow()
        await col.update_one(
            {"_id": ObjectId(proposal_id), "tenant_id": tenant_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc)[:1000],
                    "updated_at": failed_at,
                    "updated_by": uid,
                    "resolved_at": failed_at,
                    "resolved_by": uid,
                }
            },
        )
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=uid,
            product="officemitra",
            action="proposal.fail",
            entity_type="officemitra_proposal",
            entity_id=proposal_id,
            old_value={"status": "confirmed"},
            new_value={"status": "failed", "action_type": action, "error": str(exc)[:500]},
        )
        updated = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
        return {"proposal": serialize_doc(updated), "result": None, "error": str(exc)}


async def dismiss_proposal(*, tenant_id: str, user: dict, proposal_id: str) -> dict | None:
    await ensure_indexes()
    if not ObjectId.is_valid(proposal_id):
        return None
    col = get_collection(PROPOSALS_COLLECTION)
    doc = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
    if not doc:
        return None
    if doc.get("status") not in {"pending", "awaiting_checker"}:
        return serialize_doc(doc)

    now = utcnow()
    uid = _user_id(user)
    old_status = doc.get("status")
    await col.update_one(
        {"_id": ObjectId(proposal_id), "tenant_id": tenant_id, "status": old_status},
        {
            "$set": {
                "status": "dismissed",
                "updated_at": now,
                "updated_by": uid,
                "resolved_at": now,
                "resolved_by": uid,
            }
        },
    )
    await log_audit_event(
        tenant_id=tenant_id,
        user_id=uid,
        product="officemitra",
        action="proposal.dismiss",
        entity_type="officemitra_proposal",
        entity_id=proposal_id,
        old_value={"status": old_status},
        new_value={"status": "dismissed", "action_type": doc.get("action_type")},
    )
    updated = await col.find_one({"_id": ObjectId(proposal_id), "tenant_id": tenant_id})
    return serialize_doc(updated)
