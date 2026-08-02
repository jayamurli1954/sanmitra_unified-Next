"""HTTP routes for LegalMitra Stage 5 — guided agentic workflows."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.modules.legal import workflow_service
from app.modules.legal.practice_service import PracticeNotFoundError
from app.modules.legal.workflow_schemas import (
    ReadyToFileRequest,
    WorkflowArtifactListResponse,
    WorkflowCatalogResponse,
    WorkflowDefinitionListResponse,
    WorkflowRunCreateRequest,
    WorkflowRunListResponse,
    WorkflowRunResponse,
    WorkflowStepRejectRequest,
    WorkflowTimelineListResponse,
)

DEFAULT_APP_KEY = "legalmitra"

workflow_router = APIRouter(tags=["legal-workflows"])


def _resolve_legal_app_key(x_app_key: str | None) -> str:
    return resolve_app_key((x_app_key or DEFAULT_APP_KEY).strip())


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("sub") or "system")


def _http_for_workflow_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (workflow_service.WorkflowNotFoundError, PracticeNotFoundError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, workflow_service.WorkflowValidationError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, workflow_service.WorkflowConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, workflow_service.WorkflowDisabledError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Workflow operation failed")


@workflow_router.get("/workflows/catalog", response_model=WorkflowCatalogResponse)
async def get_catalog(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    resolve_tenant_id(current_user, x_tenant_id)
    _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.get_workflow_catalog()
    except workflow_service.WorkflowDisabledError as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get("/workflows", response_model=WorkflowDefinitionListResponse)
async def get_definitions(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    resolve_tenant_id(current_user, x_tenant_id)
    _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.get_workflow_definitions()
    except workflow_service.WorkflowDisabledError as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post("/workflows/runs", response_model=WorkflowRunResponse)
async def create_run(
    payload: WorkflowRunCreateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.create_workflow_run(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            payload=payload,
            auto_advance=True,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowValidationError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowNotFoundError,
        PracticeNotFoundError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get("/workflows/runs", response_model=WorkflowRunListResponse)
async def list_runs(
    matter_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.list_workflow_runs(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            limit=limit,
        )
    except workflow_service.WorkflowDisabledError as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get("/workflows/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_run(
    run_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.get_workflow_run(
            tenant_id=tenant_id, app_key=app_key, run_id=run_id
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get(
    "/workflows/runs/{run_id}/timeline",
    response_model=WorkflowTimelineListResponse,
)
async def get_run_timeline(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.list_run_timeline(
            tenant_id=tenant_id, app_key=app_key, run_id=run_id, limit=limit
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get(
    "/workflows/runs/{run_id}/artifacts",
    response_model=WorkflowArtifactListResponse,
)
async def get_run_artifacts(
    run_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.list_run_artifacts(
            tenant_id=tenant_id, app_key=app_key, run_id=run_id
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/advance",
    response_model=WorkflowRunResponse,
)
async def advance_run(
    run_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.advance_workflow_run(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
            until_blocked=True,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowValidationError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/steps/{step_id}/approve",
    response_model=WorkflowRunResponse,
)
async def approve_step(
    run_id: str,
    step_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.approve_workflow_step(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
            step_id=step_id,
            auto_advance=True,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowValidationError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/steps/{step_id}/reject",
    response_model=WorkflowRunResponse,
)
async def reject_step(
    run_id: str,
    step_id: str,
    payload: WorkflowStepRejectRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.reject_workflow_step(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
            step_id=step_id,
            payload=payload,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowValidationError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/steps/{step_id}/retry",
    response_model=WorkflowRunResponse,
)
async def retry_step(
    run_id: str,
    step_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.retry_workflow_step(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
            step_id=step_id,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowValidationError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/cancel",
    response_model=WorkflowRunResponse,
)
async def cancel_run(
    run_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.cancel_workflow_run(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.post(
    "/workflows/runs/{run_id}/ready-to-file",
    response_model=WorkflowRunResponse,
)
async def ready_to_file(
    run_id: str,
    payload: ReadyToFileRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.set_ready_to_file(
            tenant_id=tenant_id,
            app_key=app_key,
            actor_id=_actor_id(current_user),
            run_id=run_id,
            payload=payload,
        )
    except (
        workflow_service.WorkflowDisabledError,
        workflow_service.WorkflowNotFoundError,
        workflow_service.WorkflowConflictError,
        workflow_service.WorkflowValidationError,
    ) as exc:
        raise _http_for_workflow_error(exc) from exc


@workflow_router.get("/kg/subgraph")
async def kg_subgraph(
    family: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await workflow_service.get_kg_subgraph(
            tenant_id=tenant_id, app_key=app_key, family=family, limit=limit
        )
    except workflow_service.WorkflowDisabledError as exc:
        raise _http_for_workflow_error(exc) from exc
