"""Policy types for ADR-012."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

PolicyIntent = Literal["propose", "confirm", "approve", "execute", "start_workflow"]
ExecutionMode = Literal["deny", "immediate", "confirmation", "maker_checker"]
DecisionLabel = Literal["ALLOW", "DENY", "REQUIRE_CONFIRMATION", "REQUIRE_MAKER_CHECKER"]


@dataclass
class PolicyContext:
    tenant_id: str
    actor_id: str
    action_type: str
    target_module: str = "office_ai"
    intent: PolicyIntent = "execute"
    actor_roles: list[str] = field(default_factory=list)
    enabled_modules: list[str] = field(default_factory=list)
    office_ai_features: list[str] = field(default_factory=list)
    required_feature: str | None = None  # writeback | workflows | companion_writeback
    proposal_id: str | None = None
    workflow_run_id: str | None = None
    # Approval state (from proposal / run document)
    maker_id: str | None = None
    checker_id: str | None = None
    confirmed_at: datetime | str | None = None
    approval_expires_at: datetime | str | None = None
    allow_self_approval: bool = False
    approval_expiry_hours: int = 72

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    execution_mode: ExecutionMode
    decision: DecisionLabel
    rule_id: str
    reason: str
    approval_expiry_hours: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "execution_mode": self.execution_mode,
            "decision": self.decision,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "approval_expiry_hours": self.approval_expiry_hours,
        }
