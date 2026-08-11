"""Action executor — runs confirmed OfficeMitra proposals via the action registry."""
from __future__ import annotations

from typing import Any

from app.modules.office_ai.actions.registry import ensure_default_actions_registered, get_action

# Bump when executor contract / diagnostics semantics change (ADR-009).
EXECUTOR_VERSION = "officemitra-executor-v1"


class ActionExecutionError(RuntimeError):
    def __init__(self, message: str, *, code: str = "action_failed"):
        super().__init__(message)
        self.code = code


async def execute_action(
    *,
    action_type: str,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any] | None,
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    ensure_default_actions_registered()
    spec = get_action(action_type)
    if spec is None:
        raise ActionExecutionError(f"Unknown action_type: {action_type}", code="unknown_action")
    if str(spec.target_module).strip().lower() != "office_ai":
        raise ActionExecutionError(
            f"Action target {spec.target_module} is not allowed under ADR-008/009",
            code="forbidden_target",
        )
    try:
        result = await spec.handler(
            tenant_id=tenant_id,
            user=user,
            payload=payload or {},
            prompt_version=prompt_version,
            ai_telemetry_id=ai_telemetry_id,
            proposal_id=proposal_id,
        )
    except ActionExecutionError:
        raise
    except Exception as exc:
        # Ensure any handler exception is surfaced in the same ActionExecutionError contract.
        raise ActionExecutionError(str(exc), code="action_handler_failed") from exc
    if isinstance(result, dict):
        return {**result, "executor_version": EXECUTOR_VERSION}
    return {"result": result, "executor_version": EXECUTOR_VERSION}
