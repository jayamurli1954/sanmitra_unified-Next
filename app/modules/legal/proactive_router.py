"""HTTP routes for LegalMitra Stage 4 — Morning Brief, alerts, notifications."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.modules.legal import proactive_service
from app.modules.legal.proactive_schemas import (
    AlertRefreshResponse,
    AlertUpdateRequest,
    MorningBriefGenerateRequest,
    MorningBriefResponse,
    NotificationListResponse,
    NotificationResponse,
    PracticeAlertListResponse,
    PracticeAlertResponse,
)

DEFAULT_APP_KEY = "legalmitra"

proactive_router = APIRouter(tags=["legal-proactive"])


def _resolve_legal_app_key(x_app_key: str | None) -> str:
    return resolve_app_key((x_app_key or DEFAULT_APP_KEY).strip())


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("sub") or "system")


def _http_for_proactive_error(exc: Exception) -> HTTPException:
    if isinstance(exc, proactive_service.ProactiveNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, proactive_service.ProactiveValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, proactive_service.ProactiveDisabledError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Proactive operation failed")


@proactive_router.get("/practice/morning-brief", response_model=MorningBriefResponse)
async def get_morning_brief(
    persona: str = Query(default="advocate"),
    window: str = Query(default="daily"),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await proactive_service.get_today_morning_brief(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=_actor_id(current_user),
            persona=persona,
            window=window,
        )
    except (
        proactive_service.ProactiveDisabledError,
        proactive_service.ProactiveValidationError,
    ) as exc:
        raise _http_for_proactive_error(exc) from exc


@proactive_router.post("/practice/morning-brief", response_model=MorningBriefResponse)
async def regenerate_morning_brief(
    payload: MorningBriefGenerateRequest | None = None,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    options = payload or MorningBriefGenerateRequest(force_refresh=True)
    if not options.force_refresh:
        options = options.model_copy(update={"force_refresh": True})
    try:
        return await proactive_service.generate_morning_brief(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=_actor_id(current_user),
            payload=options,
        )
    except (
        proactive_service.ProactiveDisabledError,
        proactive_service.ProactiveValidationError,
    ) as exc:
        raise _http_for_proactive_error(exc) from exc


@proactive_router.get("/practice/alerts", response_model=PracticeAlertListResponse)
async def list_alerts(
    status: str | None = Query(default="open"),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        items = await proactive_service.list_practice_alerts(
            tenant_id=tenant_id, app_key=app_key, status=status, limit=limit
        )
    except proactive_service.ProactiveDisabledError as exc:
        raise _http_for_proactive_error(exc) from exc
    return PracticeAlertListResponse(items=items, count=len(items))


@proactive_router.post("/practice/alerts/refresh", response_model=AlertRefreshResponse)
async def refresh_alerts(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await proactive_service.refresh_practice_alerts(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
        )
    except proactive_service.ProactiveDisabledError as exc:
        raise _http_for_proactive_error(exc) from exc


@proactive_router.patch(
    "/practice/alerts/{alert_id}", response_model=PracticeAlertResponse
)
async def update_alert(
    alert_id: str,
    payload: AlertUpdateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await proactive_service.update_practice_alert(
            tenant_id=tenant_id,
            app_key=app_key,
            alert_id=alert_id,
            actor_id=_actor_id(current_user),
            payload=payload,
        )
    except (
        proactive_service.ProactiveNotFoundError,
        proactive_service.ProactiveDisabledError,
        proactive_service.ProactiveValidationError,
    ) as exc:
        raise _http_for_proactive_error(exc) from exc


@proactive_router.get(
    "/practice/notifications", response_model=NotificationListResponse
)
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await proactive_service.list_notifications(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=_actor_id(current_user),
            limit=limit,
        )
    except proactive_service.ProactiveDisabledError as exc:
        raise _http_for_proactive_error(exc) from exc


@proactive_router.patch(
    "/practice/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
async def mark_notification_read(
    notification_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await proactive_service.mark_notification_read(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=_actor_id(current_user),
            notification_id=notification_id,
        )
    except (
        proactive_service.ProactiveNotFoundError,
        proactive_service.ProactiveDisabledError,
    ) as exc:
        raise _http_for_proactive_error(exc) from exc
