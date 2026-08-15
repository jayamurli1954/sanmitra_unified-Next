"""Self-service registration and first-login tenant assignment policy."""

from __future__ import annotations

from fastapi import HTTPException

from app.config import Settings, get_settings
from app.core.onboarding.service import get_onboarding_request

PUBLIC_SELF_SERVICE_ROLES = frozenset({"operator", "viewer"})
DEV_OPEN_REGISTRATION_TENANT_ID = "seed-tenant-1"
LEGALMITRA_APP_KEY = "legalmitra"


def open_registration_tenant_id(*, app_key: str | None, settings: Settings) -> str:
    """Dev open-registration tenant depends on product app key.

    MandirMitra keeps the temple seed tenant. LegalMitra must not.
    """
    key = str(app_key or "").strip().lower()
    if key == LEGALMITRA_APP_KEY:
        return (
            str(getattr(settings, "DEMO_LEGAL_TENANT_ID", "") or "demo-legal-firm").strip()
            or "demo-legal-firm"
        )
    return DEV_OPEN_REGISTRATION_TENANT_ID


def assert_open_registration_allowed(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.ALLOW_OPEN_REGISTRATION:
        raise HTTPException(status_code=403, detail="Open registration is disabled")


def normalize_public_self_service_role(role: str | None) -> str:
    normalized = str(role or "operator").strip().lower() or "operator"
    if normalized not in PUBLIC_SELF_SERVICE_ROLES:
        raise HTTPException(status_code=403, detail="Role not allowed for self-service registration")
    return normalized


async def _tenant_id_from_approved_onboarding(
    *,
    onboarding_request_id: str,
    email: str | None = None,
) -> str:
    request_id = str(onboarding_request_id or "").strip()
    if not request_id:
        raise HTTPException(status_code=400, detail="onboarding_request_id is required")

    doc = await get_onboarding_request(request_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Onboarding request not found")

    status = str(doc.get("status") or "").strip().lower()
    if status != "approved":
        raise HTTPException(status_code=403, detail="Onboarding request is not approved")

    approved_tenant_id = str(doc.get("approved_tenant_id") or "").strip()
    if not approved_tenant_id:
        raise HTTPException(status_code=403, detail="Approved onboarding request has no tenant assignment")

    if email:
        admin_email = str(doc.get("admin_email") or "").strip().lower()
        if admin_email and admin_email != email.strip().lower():
            raise HTTPException(status_code=403, detail="Onboarding request does not match this email")

    return approved_tenant_id


async def resolve_self_service_tenant_id(
    *,
    requested_tenant_id: str | None,
    onboarding_request_id: str | None = None,
    email: str | None = None,
    settings: Settings | None = None,
    app_key: str | None = None,
) -> str:
    """Resolve tenant for public signup flows without client-controlled escalation."""
    settings = settings or get_settings()
    approved_tenant = str(onboarding_request_id or "").strip()
    if approved_tenant:
        return await _tenant_id_from_approved_onboarding(
            onboarding_request_id=approved_tenant,
            email=email,
        )

    if not settings.ALLOW_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail="Tenant assignment requires an approved onboarding request",
        )

    requested = str(requested_tenant_id or "").strip()
    open_tenant = open_registration_tenant_id(app_key=app_key, settings=settings)
    key = str(app_key or "").strip().lower()
    if not requested or requested == open_tenant:
        return open_tenant
    # Older LegalMitra shells sent the temple seed tenant. Remap; do not assign
    # LegalMitra signups onto MandirMitra.
    if key == LEGALMITRA_APP_KEY and requested == DEV_OPEN_REGISTRATION_TENANT_ID:
        return open_tenant
    if requested == DEV_OPEN_REGISTRATION_TENANT_ID and key != LEGALMITRA_APP_KEY:
        return DEV_OPEN_REGISTRATION_TENANT_ID

    raise HTTPException(
        status_code=403,
        detail="Tenant assignment requires an approved onboarding request",
    )
