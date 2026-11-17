import logging
from time import monotonic

from fastapi import Depends, Header, HTTPException, Request
from fastapi.params import Header as HeaderParam
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth.security import decode_token
from app.core.audit.service import log_audit_event
from app.core.tenants.context import InvalidAppKeyError, get_app_key, resolve_app_key, validate_app_key
from app.core.tenants.service import ensure_tenant_is_active
from app.core.users.service import USERS_COLLECTION
from app.db.mongo import get_collection

bearer_scheme = HTTPBearer(auto_error=False)
_auth_dependency_logger = logging.getLogger(__name__)

# Short cache so deactivation takes effect within seconds without a DB read per request.
_USER_ACTIVE_CACHE_TTL_SECONDS = 10.0
_USER_ACTIVE_CACHE: dict[str, tuple[float, bool]] = {}


def clear_user_active_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _USER_ACTIVE_CACHE.clear()
    else:
        _USER_ACTIVE_CACHE.pop(str(user_id), None)


async def ensure_user_is_active(user_id: str | None) -> None:
    """Reject tokens of users an admin has deactivated (is_active = False).

    Users with no record in core_users (service or seed identities) are left alone, as
    is the case when Mongo is not configured, mirroring ensure_tenant_is_active.
    """
    key = str(user_id or "").strip()
    if not key:
        return
    cached = _USER_ACTIVE_CACHE.get(key)
    if cached and monotonic() - cached[0] <= _USER_ACTIVE_CACHE_TTL_SECONDS:
        active = cached[1]
    else:
        try:
            users = get_collection(USERS_COLLECTION)
        except RuntimeError:
            return
        doc = await users.find_one({"user_id": key}, {"is_active": 1})
        active = doc is None or doc.get("is_active", True) is not False
        _USER_ACTIVE_CACHE[key] = (monotonic(), active)
    if not active:
        raise HTTPException(status_code=401, detail="User account is inactive")


async def _audit_super_admin_override_usage(
    *,
    payload: dict,
    token_app_key: str,
    header_app_key: str | None,
    x_tenant_id: str | None,
    request: Request | None,
) -> None:
    role = str(payload.get("role") or "").strip()
    if role != "super_admin":
        return

    token_tenant_id = str(payload.get("tenant_id") or "").strip()
    requested_tenant_id = str(x_tenant_id or "").strip()
    app_key_override_used = bool(header_app_key and header_app_key != token_app_key)
    tenant_override_used = bool(requested_tenant_id and requested_tenant_id != token_tenant_id)

    if not app_key_override_used and not tenant_override_used:
        return

    try:
        await log_audit_event(
            tenant_id=requested_tenant_id or token_tenant_id or "platform",
            user_id=str(payload.get("sub") or payload.get("user_id") or "unknown"),
            product=header_app_key or token_app_key,
            action="super_admin_context_override_used",
            entity_type="auth_context",
            entity_id=str(payload.get("sub") or payload.get("user_id") or "unknown"),
            old_value={
                "token_tenant_id": token_tenant_id or None,
                "token_app_key": token_app_key,
            },
            new_value={
                "requested_tenant_id": requested_tenant_id or None,
                "requested_app_key": header_app_key or token_app_key,
                "tenant_override_used": tenant_override_used,
                "app_key_override_used": app_key_override_used,
            },
            ip_address=request.client.host if request and request.client else None,
        )
    except Exception as exc:
        _auth_dependency_logger.error("Blocking super-admin override because audit persistence failed")
        raise HTTPException(
            status_code=503,
            detail="Privileged context override is unavailable because its audit event could not be recorded",
        ) from exc


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    payload = decode_token(credentials.credentials)
    token_type = payload.get("type")

    if token_type == "refresh":
        raise HTTPException(status_code=401, detail="Access token required")
    if token_type not in (None, "access"):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    header_value = None if isinstance(x_app_key, HeaderParam) else x_app_key
    tenant_header_value = None if isinstance(x_tenant_id, HeaderParam) else x_tenant_id
    try:
        token_app_key = resolve_app_key(payload.get("app_key") or get_app_key())
    except InvalidAppKeyError as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc
    try:
        header_app_key = validate_app_key(header_value) if header_value else None
    except InvalidAppKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    role = str(payload.get("role") or "").strip()

    if header_app_key and header_app_key != token_app_key and role != "super_admin":
        raise HTTPException(status_code=403, detail="App key override not allowed")

    await _audit_super_admin_override_usage(
        payload=payload,
        token_app_key=token_app_key,
        header_app_key=header_app_key,
        x_tenant_id=tenant_header_value,
        request=request,
    )

    payload["app_key"] = header_app_key if role == "super_admin" and header_app_key else token_app_key

    if role != "super_admin":
        await ensure_tenant_is_active(payload.get("tenant_id"))
    await ensure_user_is_active(payload.get("sub"))

    return payload
