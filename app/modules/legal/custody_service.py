"""LegalMitra P0 document custody settings (tenant-scoped practice identity).

Enum keys are stable; advocate-facing labels use Personal Practice / Chamber LAN.
Full extract pipeline and SanMitra Chamber Connector remain later phases.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.legal.practice_schemas import (
    DOC_CUSTODY_DISPLAY_NAMES,
    DOC_CUSTODY_MODE_VALUES,
    DocCustodyMode,
    DocCustodySettingsResponse,
    DocCustodySettingsUpdateRequest,
)

LEGAL_PRACTICE_SETTINGS_COLLECTION = "legal_practice_settings"
DEFAULT_APP_KEY = "legalmitra"
DEFAULT_EXTRACT_RETENTION_DAYS = 365

FUTURE_MODE_HINTS = {
    "enterprise_vault": (
        "Enterprise Vault is planned for a later phase and is not available yet. "
        "Use Personal Practice or Chamber LAN."
    ),
}


class CustodyValidationError(Exception):
    """Invalid custody mode or flag combination."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _scope(*, tenant_id: str, app_key: str) -> dict[str, str]:
    return {"tenant_id": tenant_id, "app_key": app_key}


def display_name_for_mode(mode: str) -> str:
    return DOC_CUSTODY_DISPLAY_NAMES.get(mode, mode)


def default_custody_settings(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    mode = DocCustodyMode.CLOUD_MINIMIZED.value
    return {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "doc_custody_mode": mode,
        "display_name": display_name_for_mode(mode),
        "doc_cloud_originals_opt_in": False,
        "chamber_connector_enabled": False,
        "extract_retention_days": DEFAULT_EXTRACT_RETENTION_DAYS,
        "onboarding_answered": False,
        "updated_at": None,
        "updated_by": None,
    }


def _normalize_stored(doc: dict[str, Any] | None, *, tenant_id: str, app_key: str) -> dict[str, Any]:
    base = default_custody_settings(tenant_id=tenant_id, app_key=app_key)
    if not doc:
        return base
    mode = str(doc.get("doc_custody_mode") or base["doc_custody_mode"]).strip().lower()
    if mode not in DOC_CUSTODY_MODE_VALUES:
        mode = DocCustodyMode.CLOUD_MINIMIZED.value
    retention = doc.get("extract_retention_days")
    try:
        retention_days = int(retention) if retention is not None else DEFAULT_EXTRACT_RETENTION_DAYS
    except (TypeError, ValueError):
        retention_days = DEFAULT_EXTRACT_RETENTION_DAYS
    retention_days = max(1, min(retention_days, 3650))
    return {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "doc_custody_mode": mode,
        "display_name": display_name_for_mode(mode),
        "doc_cloud_originals_opt_in": bool(doc.get("doc_cloud_originals_opt_in", False)),
        "chamber_connector_enabled": bool(doc.get("chamber_connector_enabled", False)),
        "extract_retention_days": retention_days,
        "onboarding_answered": bool(doc.get("onboarding_answered", False)),
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
    }


def _validate_update(payload: DocCustodySettingsUpdateRequest, current: dict[str, Any]) -> dict[str, Any]:
    mode = (
        payload.doc_custody_mode.value
        if payload.doc_custody_mode is not None
        else current["doc_custody_mode"]
    )
    raw_mode = str(mode or "").strip().lower()
    if raw_mode in FUTURE_MODE_HINTS:
        raise CustodyValidationError(FUTURE_MODE_HINTS[raw_mode])
    if raw_mode not in DOC_CUSTODY_MODE_VALUES:
        raise CustodyValidationError(
            f"Invalid doc_custody_mode. Allowed: {', '.join(sorted(DOC_CUSTODY_MODE_VALUES))}"
        )

    cloud_opt_in = (
        bool(payload.doc_cloud_originals_opt_in)
        if payload.doc_cloud_originals_opt_in is not None
        else bool(current["doc_cloud_originals_opt_in"])
    )
    connector = (
        bool(payload.chamber_connector_enabled)
        if payload.chamber_connector_enabled is not None
        else bool(current["chamber_connector_enabled"])
    )
    retention = (
        int(payload.extract_retention_days)
        if payload.extract_retention_days is not None
        else int(current["extract_retention_days"])
    )
    onboarding = (
        bool(payload.onboarding_answered)
        if payload.onboarding_answered is not None
        else bool(current["onboarding_answered"])
    )

    if raw_mode == DocCustodyMode.CHAMBER_LAN.value:
        if cloud_opt_in:
            raise CustodyValidationError(
                "Chamber LAN does not allow cloud originals opt-in. Keep full papers on the chamber server."
            )
        # Connector flag may be set as intent; runtime Connector is still later-phase.
    else:
        # Personal Practice: connector must stay off
        if connector:
            raise CustodyValidationError(
                "SanMitra Chamber Connector requires Chamber LAN custody mode."
            )
        cloud_opt_in = bool(cloud_opt_in)

    if raw_mode == DocCustodyMode.CLOUD_MINIMIZED.value:
        connector = False

    return {
        "doc_custody_mode": raw_mode,
        "doc_cloud_originals_opt_in": cloud_opt_in if raw_mode == DocCustodyMode.CLOUD_MINIMIZED.value else False,
        "chamber_connector_enabled": connector if raw_mode == DocCustodyMode.CHAMBER_LAN.value else False,
        "extract_retention_days": max(1, min(retention, 3650)),
        "onboarding_answered": onboarding,
    }


async def ensure_custody_indexes() -> None:
    settings = get_collection(LEGAL_PRACTICE_SETTINGS_COLLECTION)
    await settings.create_index(
        [("tenant_id", 1), ("app_key", 1)],
        unique=True,
    )


async def get_custody_settings(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    await ensure_custody_indexes()
    settings = get_collection(LEGAL_PRACTICE_SETTINGS_COLLECTION)
    doc = await settings.find_one(_scope(tenant_id=tenant_id, app_key=app_key))
    return _normalize_stored(doc, tenant_id=tenant_id, app_key=app_key)


async def update_custody_settings(
    *,
    tenant_id: str,
    app_key: str,
    payload: DocCustodySettingsUpdateRequest,
    actor_user_id: str,
) -> dict[str, Any]:
    if payload.doc_custody_mode is None and all(
        getattr(payload, field) is None
        for field in (
            "doc_cloud_originals_opt_in",
            "chamber_connector_enabled",
            "extract_retention_days",
            "onboarding_answered",
        )
    ):
        raise CustodyValidationError("No custody settings changes provided")

    await ensure_custody_indexes()
    current = await get_custody_settings(tenant_id=tenant_id, app_key=app_key)
    next_values = _validate_update(payload, current)
    now = _now()
    settings = get_collection(LEGAL_PRACTICE_SETTINGS_COLLECTION)
    await settings.update_one(
        _scope(tenant_id=tenant_id, app_key=app_key),
        {
            "$set": {
                **next_values,
                "updated_at": now,
                "updated_by": actor_user_id,
            },
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": now,
            },
        },
        upsert=True,
    )
    updated = await get_custody_settings(tenant_id=tenant_id, app_key=app_key)
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            product=app_key or DEFAULT_APP_KEY,
            action="legal_doc_custody_settings_updated",
            entity_type="legal_practice_settings",
            entity_id=f"{tenant_id}:{app_key}",
            old_value={
                "doc_custody_mode": current.get("doc_custody_mode"),
                "doc_cloud_originals_opt_in": current.get("doc_cloud_originals_opt_in"),
                "chamber_connector_enabled": current.get("chamber_connector_enabled"),
                "extract_retention_days": current.get("extract_retention_days"),
            },
            new_value={
                "doc_custody_mode": updated.get("doc_custody_mode"),
                "doc_cloud_originals_opt_in": updated.get("doc_cloud_originals_opt_in"),
                "chamber_connector_enabled": updated.get("chamber_connector_enabled"),
                "extract_retention_days": updated.get("extract_retention_days"),
                "display_name": updated.get("display_name"),
            },
        )
    except Exception:
        pass
    return updated


def to_response(doc: dict[str, Any], *, can_manage: bool = False) -> DocCustodySettingsResponse:
    return DocCustodySettingsResponse(
        tenant_id=doc["tenant_id"],
        app_key=doc["app_key"],
        doc_custody_mode=doc["doc_custody_mode"],
        display_name=doc["display_name"],
        doc_cloud_originals_opt_in=bool(doc.get("doc_cloud_originals_opt_in")),
        chamber_connector_enabled=bool(doc.get("chamber_connector_enabled")),
        extract_retention_days=int(doc.get("extract_retention_days") or DEFAULT_EXTRACT_RETENTION_DAYS),
        onboarding_answered=bool(doc.get("onboarding_answered")),
        updated_at=doc.get("updated_at"),
        updated_by=doc.get("updated_by"),
        can_manage=can_manage,
        onboarding_question=(
            "Does this chamber use a shared office file server for case papers?"
        ),
        mode_guidance={
            DocCustodyMode.CLOUD_MINIMIZED.value: (
                "Personal Practice — case papers stay on your device or optional private cloud. "
                "LegalMitra prefers case cards and extracts over hot full-file storage."
            ),
            DocCustodyMode.CHAMBER_LAN.value: (
                "Chamber LAN — full papers stay on your chamber server. "
                "LegalMitra holds practice intelligence, metadata, and selective extracts only."
            ),
        },
    )


def dashboard_custody_summary(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_custody_mode": doc.get("doc_custody_mode"),
        "display_name": doc.get("display_name"),
        "doc_cloud_originals_opt_in": bool(doc.get("doc_cloud_originals_opt_in")),
        "chamber_connector_enabled": bool(doc.get("chamber_connector_enabled")),
        "onboarding_answered": bool(doc.get("onboarding_answered")),
    }
