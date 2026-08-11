"""Policy evaluation engine (ADR-012)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.audit.service import log_audit_event
from app.core.modules.registry import (
    is_office_ai_workflows_enabled,
    is_office_ai_writeback_enabled,
    is_office_ai_mis_enabled,
    is_office_ai_mis_export_enabled,
    is_office_ai_mis_import_enabled,
    is_office_ai_mis_live_mitrabooks_enabled,
    registry_module_keys,
)
from app.modules.office_ai.actions.registry import ensure_default_actions_registered, get_action
from app.modules.office_ai.policy import rules as R
from app.modules.office_ai.policy.types import PolicyContext, PolicyDecision

DEFAULT_APPROVAL_EXPIRY_HOURS = 72


class PolicyDeniedError(PermissionError):
    def __init__(self, decision: PolicyDecision):
        super().__init__(decision.reason)
        self.decision = decision


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _feature_enabled(ctx: PolicyContext, feature: str | None) -> bool:
    if not feature:
        return True
    key = str(feature).strip().lower()
    if key == "writeback":
        return is_office_ai_writeback_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "workflows":
        return is_office_ai_workflows_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "mis":
        return is_office_ai_mis_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "mis.import":
        return is_office_ai_mis_import_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "mis.live_mitrabooks":
        return is_office_ai_mis_live_mitrabooks_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "mis.export":
        return is_office_ai_mis_export_enabled(
            enabled_modules=ctx.enabled_modules,
            office_ai_features=ctx.office_ai_features,
        )
    if key == "companion_writeback":
        # ADR-010 not Accepted — always false until implemented.
        normalized = {str(item or "").strip().lower() for item in (ctx.enabled_modules or [])}
        explicit = {str(item or "").strip().lower() for item in (ctx.office_ai_features or [])}
        return "office_ai.companion_writeback" in normalized or "companion_writeback" in explicit
    return False


def _infer_required_feature(ctx: PolicyContext) -> str | None:
    if ctx.required_feature:
        return str(ctx.required_feature).strip().lower()
    if ctx.intent == "start_workflow":
        return "workflows"
    target = str(ctx.target_module or "office_ai").strip().lower()
    if target != "office_ai":
        return "companion_writeback"
    if ctx.intent in {"propose", "confirm", "approve", "execute"}:
        action = str(ctx.action_type or "").strip().lower()
        if action == "reconcile_mis_pack":
            return "mis"
        if action in {"export_mis_excel", "export_mis_pdf_summary", "export_mis_ppt"}:
            return "mis.export"
        return "writeback"
    return None


def evaluate_policy(ctx: PolicyContext) -> PolicyDecision:
    """Evaluate OfficeMitra action policy in the ADR-012 formal order."""
    expiry_hours = int(ctx.approval_expiry_hours or DEFAULT_APPROVAL_EXPIRY_HOURS)
    if expiry_hours < 1:
        expiry_hours = DEFAULT_APPROVAL_EXPIRY_HOURS

    # 1. Module enabled?
    if "office_ai" not in set(registry_module_keys(ctx.enabled_modules)):
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_MODULE_DISABLED,
            reason="office_ai module is not enabled for this tenant",
        )

    # 2. Feature flag enabled?
    required = _infer_required_feature(ctx)
    if not _feature_enabled(ctx, required):
        flag = f"office_ai.{required}" if required else "required feature"
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_FEATURE_DISABLED,
            reason=f"{flag} disabled",
        )

    # 3. Action registered?
    ensure_default_actions_registered()
    action_type = str(ctx.action_type or "").strip().lower()
    spec = get_action(action_type) if action_type else None
    if spec is None:
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_ACTION_UNREGISTERED,
            reason=f"Unknown or unregistered action_type: {ctx.action_type}",
        )

    # 4. Actor authorized?
    actor = str(ctx.actor_id or "").strip()
    if not actor or actor == "unknown":
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_ACTOR_UNAUTHORIZED,
            reason="Authenticated actor is required",
        )
    # Role denylist reserved for future; empty roles still allow authenticated users.

    caps = spec.capabilities
    target = str(ctx.target_module or spec.target_module or "office_ai").strip().lower()
    if target != "office_ai" and required != "companion_writeback":
        # Defense in depth before ADR-010.
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_FEATURE_DISABLED,
            reason="Companion write-back requires office_ai.companion_writeback (ADR-010)",
        )

    # 5–7. Capability + approval state → final decision (by intent)
    needs_mc = bool(caps.requires_maker_checker) or str(caps.risk_level).upper() in {"HIGH", "CRITICAL"}
    needs_confirm = bool(caps.requires_confirmation) or needs_mc

    expires_at = _parse_dt(ctx.approval_expires_at)
    now = datetime.now(timezone.utc)
    if expires_at is not None and now > expires_at:
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="DENY",
            rule_id=R.POL_APPROVAL_EXPIRED,
            reason="Approval expired; restart the proposal/workflow confirmation",
            approval_expiry_hours=expiry_hours,
        )

    intent = ctx.intent

    if intent == "propose":
        if needs_mc:
            return PolicyDecision(
                allowed=True,
                execution_mode="maker_checker",
                decision="REQUIRE_MAKER_CHECKER",
                rule_id=R.POL_CAPABILITY_MAKER_CHECKER,
                reason="Action requires maker-checker before execution",
                approval_expiry_hours=expiry_hours,
            )
        if needs_confirm:
            return PolicyDecision(
                allowed=True,
                execution_mode="confirmation",
                decision="REQUIRE_CONFIRMATION",
                rule_id=R.POL_CAPABILITY_CONFIRMATION,
                reason="Action requires human confirmation before execution",
                approval_expiry_hours=expiry_hours,
            )
        return PolicyDecision(
            allowed=True,
            execution_mode="immediate",
            decision="ALLOW",
            rule_id=R.POL_CAPABILITY_ALLOW,
            reason="Action may proceed without confirmation",
        )

    if intent == "confirm":
        if needs_mc:
            # Maker confirmation recorded; do not execute yet.
            return PolicyDecision(
                allowed=True,
                execution_mode="maker_checker",
                decision="REQUIRE_MAKER_CHECKER",
                rule_id=R.POL_AWAITING_CHECKER,
                reason="Maker confirmation accepted; checker approval required",
                approval_expiry_hours=expiry_hours,
            )
        if needs_confirm:
            return PolicyDecision(
                allowed=True,
                execution_mode="confirmation",
                decision="REQUIRE_CONFIRMATION",
                rule_id=R.POL_CONFIRMATION_READY,
                reason="Confirmation satisfies policy; execution allowed",
                approval_expiry_hours=expiry_hours,
            )
        return PolicyDecision(
            allowed=True,
            execution_mode="immediate",
            decision="ALLOW",
            rule_id=R.POL_CAPABILITY_ALLOW,
            reason="No confirmation required; execution allowed",
        )

    if intent == "approve":
        if not needs_mc:
            return PolicyDecision(
                allowed=False,
                execution_mode="deny",
                decision="DENY",
                rule_id=R.POL_CAPABILITY_CONFIRMATION,
                reason="Maker-checker is not required for this action",
                approval_expiry_hours=expiry_hours,
            )
        maker = str(ctx.maker_id or "").strip()
        if not maker:
            return PolicyDecision(
                allowed=False,
                execution_mode="deny",
                decision="DENY",
                rule_id=R.POL_AWAITING_CHECKER,
                reason="Maker confirmation is required before checker approval",
                approval_expiry_hours=expiry_hours,
            )
        if maker == actor and not ctx.allow_self_approval:
            return PolicyDecision(
                allowed=False,
                execution_mode="deny",
                decision="DENY",
                rule_id=R.POL_MAKER_EQUALS_CHECKER,
                reason="Maker cannot be checker (self-approval disabled)",
                approval_expiry_hours=expiry_hours,
            )
        return PolicyDecision(
            allowed=True,
            execution_mode="maker_checker",
            decision="ALLOW",
            rule_id=R.POL_CHECKER_READY,
            reason="Checker approval satisfies maker-checker policy; execution allowed",
            approval_expiry_hours=expiry_hours,
        )

    # execute / start_workflow
    if needs_mc:
        maker = str(ctx.maker_id or "").strip()
        checker = str(ctx.checker_id or "").strip()
        if not maker or not checker:
            return PolicyDecision(
                allowed=False,
                execution_mode="deny",
                decision="REQUIRE_MAKER_CHECKER",
                rule_id=R.POL_AWAITING_CHECKER,
                reason="Maker and checker approvals are required before execution",
                approval_expiry_hours=expiry_hours,
            )
        if maker == checker and not ctx.allow_self_approval:
            return PolicyDecision(
                allowed=False,
                execution_mode="deny",
                decision="DENY",
                rule_id=R.POL_MAKER_EQUALS_CHECKER,
                reason="Maker cannot be checker (self-approval disabled)",
                approval_expiry_hours=expiry_hours,
            )
        return PolicyDecision(
            allowed=True,
            execution_mode="maker_checker",
            decision="ALLOW",
            rule_id=R.POL_CHECKER_READY,
            reason="Maker-checker complete; execution allowed",
            approval_expiry_hours=expiry_hours,
        )

    if needs_confirm and intent == "execute" and not ctx.maker_id and not ctx.confirmed_at:
        # execute without prior confirmation is denied when confirmation required
        return PolicyDecision(
            allowed=False,
            execution_mode="deny",
            decision="REQUIRE_CONFIRMATION",
            rule_id=R.POL_CAPABILITY_CONFIRMATION,
            reason="Human confirmation is required before execution",
            approval_expiry_hours=expiry_hours,
        )

    if needs_confirm:
        return PolicyDecision(
            allowed=True,
            execution_mode="confirmation",
            decision="ALLOW",
            rule_id=R.POL_CONFIRMATION_READY,
            reason="Confirmation present; execution allowed",
            approval_expiry_hours=expiry_hours,
        )

    return PolicyDecision(
        allowed=True,
        execution_mode="immediate",
        decision="ALLOW",
        rule_id=R.POL_CAPABILITY_ALLOW,
        reason="Policy allows immediate execution",
    )


def compute_approval_expires_at(
    *,
    from_time: datetime | None = None,
    hours: int = DEFAULT_APPROVAL_EXPIRY_HOURS,
) -> datetime:
    base = from_time or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(hours=max(1, int(hours or DEFAULT_APPROVAL_EXPIRY_HOURS)))


async def log_policy_decision(
    *,
    ctx: PolicyContext,
    decision: PolicyDecision,
) -> None:
    await log_audit_event(
        tenant_id=ctx.tenant_id,
        user_id=ctx.actor_id,
        product="officemitra",
        action="policy.evaluate",
        entity_type="officemitra_policy",
        entity_id=ctx.proposal_id or ctx.workflow_run_id or ctx.action_type,
        new_value={
            "action_type": ctx.action_type,
            "target_module": ctx.target_module,
            "intent": ctx.intent,
            "decision": decision.to_dict(),
        },
    )
