"""OfficeMitra write-back actions package (ADR-008)."""

from app.modules.office_ai.actions.executor import EXECUTOR_VERSION, ActionExecutionError, execute_action
from app.modules.office_ai.actions.registry import (
    ActionCapabilityDescriptor,
    ActionSpec,
    ensure_default_actions_registered,
    get_action,
    list_action_descriptors,
    list_registered_actions,
    register_action,
)

__all__ = [
    "ActionCapabilityDescriptor",
    "ActionExecutionError",
    "ActionSpec",
    "EXECUTOR_VERSION",
    "ensure_default_actions_registered",
    "execute_action",
    "get_action",
    "list_action_descriptors",
    "list_registered_actions",
    "register_action",
]
