"""Tenant-safe export governance for MitraBooks downloads."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.audit.service import log_audit_event


ALLOWED_EXPORT_ROLES = {"owner", "admin", "accountant", "auditor", "viewer", "tenant_admin", "platform_owner"}
DENIED_EXPORT_ROLES = {"cashier"}


def _role_values(current_user: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("business_role", "role"):
        if current_user.get(key):
            values.add(str(current_user[key]).strip().lower())
    raw_roles = current_user.get("roles")
    if isinstance(raw_roles, (list, tuple, set)):
        values.update(str(role).strip().lower() for role in raw_roles if role)
    return {value for value in values if value}


def require_export_permission(current_user: dict[str, Any], *, export_type: str) -> None:
    roles = _role_values(current_user)
    if roles & DENIED_EXPORT_ROLES:
        raise HTTPException(status_code=403, detail=f"{export_type} export is not permitted for cashier users")
    if roles and not (roles & ALLOWED_EXPORT_ROLES):
        raise HTTPException(status_code=403, detail=f"{export_type} export is not permitted for this role")


def validate_export_format(fmt: str, *, allowed: set[str]) -> str:
    normalized = str(fmt or "").strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=400, detail=f"format must be one of: {', '.join(sorted(allowed))}")
    return normalized


async def govern_export_response(
    response,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    current_user: dict[str, Any],
    export_type: str,
    export_format: str,
    report_key: str | None = None,
    entity_id: str | None = None,
    filters: dict[str, Any] | None = None,
):
    require_export_permission(current_user, export_type=export_type)
    actor = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")
    safe_entity_id = entity_id or report_key or export_type
    metadata = {
        "export_type": export_type,
        "format": export_format,
        "report_key": report_key,
        "accounting_entity_id": accounting_entity_id,
        "filters": filters or {},
    }
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=actor,
            product=app_key,
            action="business_export_downloaded",
            entity_type="business_export",
            entity_id=f"{export_type}:{safe_entity_id}:{export_format}",
            new_value=metadata,
        )
    except Exception:
        pass
    response.headers["X-SanMitra-Export-Governed"] = "true"
    response.headers["X-SanMitra-Export-Type"] = export_type
    response.headers["X-SanMitra-Export-Format"] = export_format
    response.headers["X-SanMitra-Accounting-Entity"] = accounting_entity_id
    return response
