"""OfficeMitra Policy Engine (ADR-012).

Single evaluation API for proposals, executor, workflows, and future connectors.
Policy is evaluated before execution — never after.
"""

from app.modules.office_ai.policy.engine import (
    DEFAULT_APPROVAL_EXPIRY_HOURS,
    PolicyDeniedError,
    evaluate_policy,
    log_policy_decision,
)
from app.modules.office_ai.policy.types import (
    ExecutionMode,
    PolicyContext,
    PolicyDecision,
    PolicyIntent,
)

__all__ = [
    "DEFAULT_APPROVAL_EXPIRY_HOURS",
    "ExecutionMode",
    "PolicyContext",
    "PolicyDecision",
    "PolicyDeniedError",
    "PolicyIntent",
    "evaluate_policy",
    "log_policy_decision",
]
