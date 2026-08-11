"""OfficeMitra action registry (ADR-008).

Proposals are action-based, not task-specific. Register handlers here so future
OfficeMitra-owned actions (notifications, calendar, etc.) plug in without
changing confirm/dismiss orchestration.

Each action carries an Action Capability Descriptor so confirmation, maker-checker,
risk, idempotency, rollback, and audit depth are declarative (not scattered ifs).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.modules.office_ai.services import mis_export, mis_store, notification_service, task_service

ActionHandler = Callable[..., Awaitable[dict[str, Any]]]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AuditLevel = Literal["BASIC", "STANDARD", "FULL"]


@dataclass(frozen=True)
class ActionCapabilityDescriptor:
    """Declarative policy metadata for a registered action."""

    requires_confirmation: bool = True
    requires_maker_checker: bool = False
    risk_level: RiskLevel = "LOW"
    idempotent: bool = False
    rollback_supported: bool = False
    audit_level: AuditLevel = "STANDARD"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionSpec:
    action_type: str
    target_module: str
    description: str
    handler: ActionHandler
    capabilities: ActionCapabilityDescriptor = ActionCapabilityDescriptor()

    @property
    def requires_confirmation(self) -> bool:
        return bool(self.capabilities.requires_confirmation)


async def _handle_create_task(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    task = await task_service.create_task(
        tenant_id=tenant_id,
        user=user,
        title=str(payload.get("title") or "Untitled"),
        notes=payload.get("notes"),
        due_date=payload.get("due_date"),
        source="ai",
        prompt_version=prompt_version,
        ai_telemetry_id=ai_telemetry_id,
    )
    return {
        "entity_type": "officemitra_task",
        "entity_id": task.get("id"),
        "task": task,
        "proposal_id": proposal_id,
    }


async def _handle_create_notification(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    item = await notification_service.create_notification(
        tenant_id=tenant_id,
        user=user,
        title=str(payload.get("title") or "OfficeMitra notice"),
        body=payload.get("body"),
        kind=str(payload.get("kind") or "workflow_ready"),
        href=payload.get("href"),
        dedupe_key=payload.get("dedupe_key"),
    )
    return {
        "entity_type": "officemitra_notification",
        "entity_id": (item or {}).get("id"),
        "notification": item,
        "proposal_id": proposal_id,
        "prompt_version": prompt_version,
        "ai_telemetry_id": ai_telemetry_id,
    }


async def _handle_reconcile_mis_pack(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    """Lock MIS pack + facts after human review (ADR-014 immutability)."""
    pack_id = str(payload.get("pack_id") or "").strip()
    if not pack_id:
        raise ValueError("pack_id is required for reconcile_mis_pack")

    try:
        item = await mis_store.reconcile_pack(
            tenant_id=tenant_id,
            pack_id=pack_id,
            user=user,
            data_quality_score=payload.get("data_quality_score"),
            data_quality_breakdown=payload.get("data_quality_breakdown"),
        )
    except Exception as exc:
        raise RuntimeError(f"reconcile_mis_pack failed: {type(exc).__name__}: {exc}") from exc

    return {
        "entity_type": "officemitra_mis_pack",
        "entity_id": (item or {}).get("id") if isinstance(item, dict) else pack_id,
        "pack": item,
        "proposal_id": proposal_id,
    }


async def _handle_export_mis(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    export_format: str,
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    """Generate MIS export artifact metadata for a reconciled pack (ADR-014)."""
    pack_id = str(payload.get("pack_id") or "").strip()
    if not pack_id:
        raise ValueError("pack_id is required for MIS export actions")

    try:
        result = await mis_export.export_mis_pack(
            tenant_id=tenant_id,
            pack_id=pack_id,
            user=user,
            export_format=export_format,
        )
    except Exception as exc:
        raise RuntimeError(f"MIS export failed: {type(exc).__name__}: {exc}") from exc

    artifact = result.get("artifact") if isinstance(result, dict) else {}
    pack = result.get("pack") if isinstance(result, dict) else None
    return {
        "entity_type": "officemitra_mis_export",
        "entity_id": pack_id,
        "export_format": export_format,
        "artifact": artifact,
        "pack": pack,
        "proposal_id": proposal_id,
    }


async def _handle_export_mis_excel(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    return await _handle_export_mis(
        tenant_id=tenant_id,
        user=user,
        payload=payload,
        export_format="excel",
        prompt_version=prompt_version,
        ai_telemetry_id=ai_telemetry_id,
        proposal_id=proposal_id,
    )


async def _handle_export_mis_pdf_summary(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    return await _handle_export_mis(
        tenant_id=tenant_id,
        user=user,
        payload=payload,
        export_format="pdf_summary",
        prompt_version=prompt_version,
        ai_telemetry_id=ai_telemetry_id,
        proposal_id=proposal_id,
    )


async def _handle_export_mis_ppt(
    *,
    tenant_id: str,
    user: dict,
    payload: dict[str, Any],
    prompt_version: str | None = None,
    ai_telemetry_id: str | None = None,
    proposal_id: str | None = None,
) -> dict[str, Any]:
    return await _handle_export_mis(
        tenant_id=tenant_id,
        user=user,
        payload=payload,
        export_format="ppt",
        prompt_version=prompt_version,
        ai_telemetry_id=ai_telemetry_id,
        proposal_id=proposal_id,
    )


_ACTION_REGISTRY: dict[str, ActionSpec] = {}


def register_action(spec: ActionSpec) -> None:
    key = str(spec.action_type or "").strip().lower()
    if not key:
        raise ValueError("action_type is required")
    # ADR-008 / Phase 4–6: only office_ai targets until ADR-010 is Accepted.
    if str(spec.target_module or "").strip().lower() != "office_ai":
        raise ValueError("Phase 4–6 actions may only target office_ai (ADR-008/009); companion targets need ADR-010")
    if not isinstance(spec.capabilities, ActionCapabilityDescriptor):
        raise ValueError("capabilities must be an ActionCapabilityDescriptor")
    _ACTION_REGISTRY[key] = spec


def get_action(action_type: str) -> ActionSpec | None:
    return _ACTION_REGISTRY.get(str(action_type or "").strip().lower())


def list_registered_actions() -> list[str]:
    return sorted(_ACTION_REGISTRY.keys())


def list_action_descriptors() -> list[dict[str, Any]]:
    """Return registry metadata (no handlers) for UI / policy / ping."""
    out: list[dict[str, Any]] = []
    for key in list_registered_actions():
        spec = _ACTION_REGISTRY[key]
        out.append(
            {
                "action_type": spec.action_type,
                "target_module": spec.target_module,
                "description": spec.description,
                "capabilities": spec.capabilities.to_dict(),
            }
        )
    return out


def ensure_default_actions_registered() -> None:
    if "create_task" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="create_task",
                target_module="office_ai",
                description="Create an OfficeMitra task from a confirmed proposal",
                handler=_handle_create_task,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=False,
                    risk_level="LOW",
                    idempotent=False,
                    rollback_supported=False,
                    audit_level="STANDARD",
                ),
            )
        )
    if "create_notification" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="create_notification",
                target_module="office_ai",
                description="Create an OfficeMitra in-app notification",
                handler=_handle_create_notification,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=False,
                    risk_level="LOW",
                    idempotent=True,
                    rollback_supported=False,
                    audit_level="BASIC",
                ),
            )
        )

    if "reconcile_mis_pack" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="reconcile_mis_pack",
                target_module="office_ai",
                description="Lock MIS pack + facts after human review (ADR-014).",
                handler=_handle_reconcile_mis_pack,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=True,
                    risk_level="HIGH",
                    idempotent=True,
                    rollback_supported=False,
                    audit_level="FULL",
                ),
            )
        )

    if "export_mis_excel" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="export_mis_excel",
                target_module="office_ai",
                description="Export reconciled MIS pack as CFO Excel workbook (ADR-014).",
                handler=_handle_export_mis_excel,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=False,
                    risk_level="MEDIUM",
                    idempotent=True,
                    rollback_supported=False,
                    audit_level="FULL",
                ),
            )
        )
    if "export_mis_pdf_summary" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="export_mis_pdf_summary",
                target_module="office_ai",
                description="Export reconciled MIS pack as CEO PDF summary (ADR-014).",
                handler=_handle_export_mis_pdf_summary,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=False,
                    risk_level="MEDIUM",
                    idempotent=True,
                    rollback_supported=False,
                    audit_level="FULL",
                ),
            )
        )
    if "export_mis_ppt" not in _ACTION_REGISTRY:
        register_action(
            ActionSpec(
                action_type="export_mis_ppt",
                target_module="office_ai",
                description="Export reconciled MIS pack as board PPT deck (ADR-014).",
                handler=_handle_export_mis_ppt,
                capabilities=ActionCapabilityDescriptor(
                    requires_confirmation=True,
                    requires_maker_checker=True,
                    risk_level="HIGH",
                    idempotent=True,
                    rollback_supported=False,
                    audit_level="FULL",
                ),
            )
        )


ensure_default_actions_registered()
