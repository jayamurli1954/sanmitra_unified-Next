"""HTTP routes for LegalMitra Stage 3 — clients, matters, documents, timeline, briefs, dashboard.

Mounted under the existing `/legal` router. Legacy `/legal/cases` remains unchanged.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.modules.legal import practice_service
from app.modules.legal import custody_service
from app.modules.legal import extract_service
from app.modules.legal.practice_schemas import (
    CaseCardApplyRequest,
    CaseCardSuggestResponse,
    ClientCreateRequest,
    ClientListResponse,
    ClientResponse,
    ClientUpdateRequest,
    DocCustodySettingsResponse,
    DocCustodySettingsUpdateRequest,
    MatterBriefGenerateRequest,
    MatterBriefResponse,
    MatterChunkListResponse,
    MatterCreateRequest,
    MatterDocumentCreateRequest,
    MatterDocumentListResponse,
    MatterDocumentResponse,
    MatterExtractIngestRequest,
    MatterExtractIngestResponse,
    MatterExtractListResponse,
    MatterExtractResponse,
    MatterListResponse,
    MatterResponse,
    MatterUpdateRequest,
    PracticeDashboardResponse,
    RetentionDryRunResponse,
    TimelineEventCreateRequest,
    TimelineEventResponse,
    TimelineListResponse,
)

DEFAULT_APP_KEY = "legalmitra"
_CUSTODY_MANAGE_ROLES = frozenset({"tenant_admin", "super_admin"})

practice_router = APIRouter(tags=["legal-practice"])


def _resolve_legal_app_key(x_app_key: str | None) -> str:
    return resolve_app_key((x_app_key or DEFAULT_APP_KEY).strip())


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("sub") or "system")


def _can_manage_custody(current_user: dict) -> bool:
    role = str(current_user.get("role") or "").strip()
    return role in _CUSTODY_MANAGE_ROLES


def _http_for_practice_error(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            practice_service.PracticeNotFoundError,
            extract_service.ExtractNotFoundError,
        ),
    ):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, practice_service.PracticeConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(
        exc,
        (
            practice_service.PracticeValidationError,
            custody_service.CustodyValidationError,
            extract_service.ExtractValidationError,
        ),
    ):
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


# ── Matter extracts / chunks (P2) ─────────────────────────────────────────────


@practice_router.post(
    "/matters/{matter_id}/documents/{document_id}/extracts",
    response_model=MatterExtractIngestResponse,
)
async def ingest_matter_extract(
    matter_id: str,
    document_id: str,
    payload: MatterExtractIngestRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        result = await extract_service.ingest_matter_extract(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            document_id=document_id,
            actor_id=_actor_id(current_user),
            extract_text=payload.extract_text,
            approve=payload.approve,
            authorize_external_provider=payload.authorize_external_provider,
        )
    except (
        extract_service.ExtractNotFoundError,
        extract_service.ExtractValidationError,
        practice_service.PracticeNotFoundError,
    ) as exc:
        raise _http_for_practice_error(exc) from exc
    return MatterExtractIngestResponse(
        deduped=bool(result.get("deduped")),
        extract=result["extract"],
        chunks=result.get("chunks") or [],
        suggestions=result.get("suggestions") or {},
    )


@practice_router.get(
    "/matters/{matter_id}/extracts",
    response_model=MatterExtractListResponse,
)
async def list_matter_extracts(
    matter_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    items = await extract_service.list_matter_extracts(
        tenant_id=tenant_id, app_key=app_key, matter_id=matter_id, limit=limit
    )
    return MatterExtractListResponse(items=items, count=len(items))


@practice_router.get(
    "/matters/{matter_id}/chunks",
    response_model=MatterChunkListResponse,
)
async def list_matter_chunks(
    matter_id: str,
    extract_id: str | None = Query(default=None),
    approved_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    items = await extract_service.list_matter_chunks(
        tenant_id=tenant_id,
        app_key=app_key,
        matter_id=matter_id,
        extract_id=extract_id,
        approved_only=approved_only,
        limit=limit,
    )
    return MatterChunkListResponse(items=items, count=len(items))


@practice_router.post(
    "/matters/{matter_id}/extracts/{extract_id}/approve",
    response_model=MatterExtractResponse,
)
async def approve_matter_extract(
    matter_id: str,
    extract_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await extract_service.approve_extract(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            extract_id=extract_id,
            actor_id=_actor_id(current_user),
        )
    except extract_service.ExtractNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.get(
    "/matters/{matter_id}/extracts/{extract_id}/case-card-suggestions",
    response_model=CaseCardSuggestResponse,
)
async def suggest_case_card_from_extract(
    matter_id: str,
    extract_id: str,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await extract_service.suggest_case_card(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            extract_id=extract_id,
        )
    except extract_service.ExtractNotFoundError as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.post(
    "/matters/{matter_id}/extracts/{extract_id}/apply-case-card",
    response_model=MatterResponse,
)
async def apply_case_card_from_extract(
    matter_id: str,
    extract_id: str,
    payload: CaseCardApplyRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        return await extract_service.apply_case_card_suggestions(
            tenant_id=tenant_id,
            app_key=app_key,
            matter_id=matter_id,
            extract_id=extract_id,
            actor_id=_actor_id(current_user),
            fields=payload.fields,
        )
    except (
        extract_service.ExtractNotFoundError,
        extract_service.ExtractValidationError,
        practice_service.PracticeNotFoundError,
        practice_service.PracticeValidationError,
    ) as exc:
        raise _http_for_practice_error(exc) from exc


@practice_router.get(
    "/practice/extracts/retention-dry-run",
    response_model=RetentionDryRunResponse,
)
async def extract_retention_dry_run(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not _can_manage_custody(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only tenant_admin or super_admin can run retention dry-run",
        )
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    return await extract_service.retention_dry_run(tenant_id=tenant_id, app_key=app_key)


@practice_router.post("/practice/cloud-originals/assert-allowed")
async def assert_cloud_original_allowed(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """P2.8 gate probe — Mode B / missing opt-in fail closed. No binary storage yet."""
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        settings = await extract_service.assert_cloud_original_allowed(
            tenant_id=tenant_id, app_key=app_key
        )
    except extract_service.ExtractValidationError as exc:
        raise _http_for_practice_error(exc) from exc
    return {
        "allowed": True,
        "doc_custody_mode": settings.get("doc_custody_mode"),
        "doc_cloud_originals_opt_in": settings.get("doc_cloud_originals_opt_in"),
    }


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


# ── Document custody settings (P0) ────────────────────────────────────────────


@practice_router.get(
    "/practice/custody-settings", response_model=DocCustodySettingsResponse
)
async def get_practice_custody_settings(
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    settings = await custody_service.get_custody_settings(
        tenant_id=tenant_id, app_key=app_key
    )
    return custody_service.to_response(
        settings, can_manage=_can_manage_custody(current_user)
    )


@practice_router.patch(
    "/practice/custody-settings", response_model=DocCustodySettingsResponse
)
async def patch_practice_custody_settings(
    payload: DocCustodySettingsUpdateRequest,
    _module_context: dict = Depends(require_enabled_module("legal")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not _can_manage_custody(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only tenant_admin or super_admin can change document custody settings",
        )
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_legal_app_key(x_app_key)
    try:
        settings = await custody_service.update_custody_settings(
            tenant_id=tenant_id,
            app_key=app_key,
            payload=payload,
            actor_user_id=_actor_id(current_user),
        )
    except custody_service.CustodyValidationError as exc:
        raise _http_for_practice_error(exc) from exc
    return custody_service.to_response(settings, can_manage=True)


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
    dashboard = await practice_service.get_practice_dashboard(
        tenant_id=tenant_id, app_key=app_key, limit=limit
    )
    from app.modules.legal import proactive_service

    return await proactive_service.extend_dashboard_proactive(
        tenant_id=tenant_id, app_key=app_key, base_dashboard=dashboard
    )
