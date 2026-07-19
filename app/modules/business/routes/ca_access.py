"""CA access management routes (invite / accept / list / cancel / revoke).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. The CA-only rate-limit constants moved here.
"""
import json

from fastapi import Depends, Header, HTTPException, Request

from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.rate_limiting import limiter
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business import ca_access as ca_access_module
from app.modules.business.schemas import (
    CaAccessListResponse,
    CaAccessRecord,
    CaInviteAcceptRequest,
    CaInviteRequest,
    CaRevokeResponse,
)
from app.modules.business.router import _created_by, router

CA_INVITE_PREVIEW_RATE_LIMIT = "20/minute"
CA_INVITE_ACCEPT_RATE_LIMIT = "10/minute"


# ── CA Access Management ──────────────────────────────────────────────────────

@router.post("/ca/invite")
async def invite_ca_user(
    payload: CaInviteRequest,
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Send a CA invite email. tenant_admin only."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CA invite",
    )
    try:
        doc = await ca_access_module.invite_ca(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            email=payload.email,
            full_name=payload.full_name,
            invited_by=_created_by(current_user),
        )
        delivery = doc.get("email_delivery") or {}
        return {
            "ok": bool(delivery.get("sent", False)),
            "invite_id": doc["invite_id"],
            "email": doc["email"],
            "expires_at": str(doc["expires_at"]),
            "resent": bool(doc.get("resent")),
            "email_sent": bool(delivery.get("sent", False)),
            "email_error": delivery.get("error"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/ca/invite/{token}/preview")
@limiter.limit(CA_INVITE_PREVIEW_RATE_LIMIT)
async def preview_ca_invite(request: Request, token: str):
    """Return a masked invite hint. No authentication is required."""
    try:
        return await ca_access_module.preview_ca_invite(token=token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invite is invalid, expired, or unavailable") from exc


@router.post("/ca/invite/{token}/accept")
@limiter.limit(CA_INVITE_ACCEPT_RATE_LIMIT)
async def accept_ca_invite(
    request: Request,
    token: str,
):
    """Accept a CA invite — creates the ca_viewer account. No auth required."""
    try:
        content_type = str(request.headers.get("content-type") or "").lower()
        if content_type.startswith("text/plain"):
            raw_body = (await request.body()).decode("utf-8").strip()
            payload = CaInviteAcceptRequest.model_validate(json.loads(raw_body or "{}"))
        else:
            payload = CaInviteAcceptRequest.model_validate(await request.json())
        await ca_access_module.accept_ca_invite(
            token=token,
            password=payload.password,
            full_name=payload.full_name,
        )
        return {"ok": True}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid invite accept payload") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invite is invalid, expired, or unavailable") from exc


@router.get("/ca/users", response_model=CaAccessListResponse)
async def list_ca_users(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """List all CA invites and users for this tenant. tenant_admin only."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CA user listing",
    )
    data = await ca_access_module.list_ca_access(tenant_id=context.tenant_id)
    return CaAccessListResponse(
        ca_users=[CaAccessRecord(**r) for r in data["ca_users"]],
        total=data["total"],
    )


@router.post("/ca/invite/{invite_id}/cancel")
async def cancel_ca_invite(
    invite_id: str,
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Cancel a pending CA invite. tenant_admin only."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CA invite cancel",
    )
    try:
        await ca_access_module.delete_ca_record(tenant_id=context.tenant_id, invite_id=invite_id)
        return {"ok": True, "message": "CA record deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ca/{user_id}/reinstate")
async def reinstate_ca_user(
    user_id: str,
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Reinstate a previously revoked CA user. tenant_admin only."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CA access reinstate",
    )
    try:
        await ca_access_module.reinstate_ca_access(tenant_id=context.tenant_id, user_id=user_id)
        return {"ok": True, "message": f"CA access reinstated for user {user_id}"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ca/{user_id}/revoke", response_model=CaRevokeResponse)
async def revoke_ca_user(
    user_id: str,
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Revoke a CA user account. tenant_admin only."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CA access revoke",
    )
    try:
        await ca_access_module.revoke_ca_access(tenant_id=context.tenant_id, user_id=user_id)
        return CaRevokeResponse(ok=True, message=f"CA access revoked for user {user_id}")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
