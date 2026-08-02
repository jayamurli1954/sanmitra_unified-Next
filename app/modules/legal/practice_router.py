"""HTTP routes for LegalMitra Stage 3 — clients, matters, documents, timeline, briefs, dashboard.

Mounted under the existing `/legal` router. Legacy `/legal/cases` remains unchanged.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.modules.legal import practice_service
from app.modules.legal.practice_schemas import (
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    MatterBriefGenerateRequest,
    MatterBriefResponse,
    MatterCreateRequest,
    MatterDocumentCreateRequest,
    MatterDocumentListResponse,
    MatterDocumentResponse,
    MatterListResponse,
    MatterResponse,
    MatterUpdateRequest,
    PracticeDashboardResponse,
    TimelineEventCreateRequest,
    TimelineEventResponse,
    TimelineListResponse,
)

DEFAULT_APP_KEY = "legalmitra"

practice_router = APIRouter(tags=["legal-practice"])


def _resolve_legal_app_key(x_app_key: str | None) -> str:
    return resolve_app_key((x_app_key or DEFAULT_APP_KEY).strip())


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("sub") or "system")


def _http_for_practice_error(exc: Exception) -> HTTPException:
    if isinstance(exc, practice_service.PracticeNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, practice_service.PracticeConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, practice_service.PracticeValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Practice operation failed")


# ── Clients ──────────────────────────────────────────────────────────────────


@practice_router.post("/clients", response_model=ClientResponse)
async def create_client(
    payload: ClientCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.create_client(
            tenant_id=tenant_id,
            app_key=app_key,
            created_by=_actor_id(current_user),
            payload=payload,
        )
    except Exception as exc:
        if isinstance(
            exc,
            (
                practice_service.PracticeNotFoundError,
                practice_service.PracticeConflictError,
                practice_service.PracticeValidationError,
            ),
        ):
            raise _http_for_practice_error(exc) from exc
        raise


@practice_router.get("/clients", response_model=ClientListResponse)
async def list_clients(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    items = await practice_service.list_clients(
        tenant_id=tenant_id, app_key=app_key, status=status, limit=limit
    )
    return ClientListResponse(items=items, count=len(items))


@practice_router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.get_client(
            tenant_id=tenant_id, app_key=app_key, client_id=client_id
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.patch("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    payload: ClientUpdateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.update_client(
            tenant_id=tenant_id,
            app_key=app_key,
            client_id=client_id,
            updated_by=_actor_id(current_user),
            payload=payload,
        )
    except (
        practice_service.PracticeNotFoundError,
        practice_service.PracticeValidationError,
    ) as exc:
        raise _http_for_practice_error(exc) from exc


# ── Matters ──────────────────────────────────────────────────────────────────


@practice_router.post("/matters", response_model=MatterResponse)
async def create_matter(
    payload: MatterCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.create_matter(
            tenant_id=tenant_id,
            app_key=app_key,
            created_by=_actor_id(current_user),
            payload=payload,
        )
    except (
        practice_service.PracticeNotFoundError,
        practice_service.PracticeValidationError,
        practice_service.PracticeConflictError,
    ) as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.get("/matters", response_model=MatterListResponse)
async def list_matters(
    client_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    items = await practice_service.list_matters(
        tenant_id=tenant_id,
        app_key=app_key,
        client_id=client_id,
        status=status,
        limit=limit,
    )
    return MatterListResponse(items=items, count=len(items))


@practice_router.get("/matters/{matter_id}", response_model=MatterResponse)
async def get_matter(
    matter_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.get_matter(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.patch("/matters/{matter_id}", response_model=MatterResponse)
async def update_matter(
    matter_id: str,
    payload: MatterUpdateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.update_matter(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            updated_by=_actor_id(current_user),
            payload=payload,
        )
    except (
        practice_service.PracticeNotFoundError,
        practice_service.PracticeValidationError,
    ) as exc:
        raise _http_for_practice_error(exc) from exc


# ── Documents ────────────────────────────────────────────────────────────────


@practice_router.post(
    "/matters/{matter_id}/documents", response_model=MatterDocumentResponse
)
async def attach_matter_document(
    matter_id: str,
    payload: MatterDocumentCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.attach_matter_document(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            created_by=_actor_id(current_user),
            payload=payload,
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.get(
    "/matters/{matter_id}/documents", response_model=MatterDocumentListResponse
)
async def list_matter_documents(
    matter_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        items = await practice_service.list_matter_documents(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=limit
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc
    return MatterDocumentListResponse(items=items, count=len(items))


# ── Timeline ─────────────────────────────────────────────────────────────────


@practice_router.get(
    "/matters/{matter_id}/timeline", response_model=TimelineListResponse
)
async def list_matter_timeline(
    matter_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        items = await practice_service.list_matter_timeline(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=limit
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc
    return TimelineListResponse(items=items, count=len(items))


@practice_router.post(
    "/matters/{matter_id}/timeline", response_model=TimelineEventResponse
)
async def add_matter_timeline_event(
    matter_id: str,
    payload: TimelineEventCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.add_matter_timeline_event(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            actor_id=_actor_id(current_user),
            payload=payload,
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


# ── Briefs ───────────────────────────────────────────────────────────────────


@practice_router.post(
    "/matters/{matter_id}/brief", response_model=MatterBriefResponse
)
async def generate_matter_brief(
    matter_id: str,
    payload: MatterBriefGenerateRequest | None = None,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.generate_matter_brief(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            generated_by=_actor_id(current_user),
            payload=payload,
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.get(
    "/matters/{matter_id}/brief", response_model=MatterBriefResponse
)
async def get_latest_matter_brief(
    matter_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await practice_service.get_latest_matter_brief(
            tenant_id=tenant_id, app_key=app_key, matter_id=matter_id
        )
    except practice_service.PracticeNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


# ── Dashboard ────────────────────────────────────────────────────────────────


@practice_router.get("/practice/dashboard", response_model=PracticeDashboardResponse)
async def practice_dashboard(
    limit: int = Query(default=5, ge=1, le=20),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    return await practice_service.get_practice_dashboard(
        tenant_id=tenant_id, app_key=app_key, limit=limit
    )
