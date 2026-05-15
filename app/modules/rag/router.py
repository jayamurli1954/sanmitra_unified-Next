from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.context import inject_app_key, resolve_tenant_id
from app.modules.rag.schemas import (
    RagDocumentListResponse,
    RagDocumentResponse,
    RagIngestRequest,
    RagQueryRequest,
    RagQueryResponse,
)
from app.modules.rag.service import ingest_document, list_documents, query_knowledge


class IngestedActInfo(BaseModel):
    """Public information about ingested legal acts (no auth required)"""
    name: str
    year: int | str


class IngestedActsListResponse(BaseModel):
    """Public list of ingested acts"""
    acts: list[IngestedActInfo]
    count: int

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/documents", response_model=RagDocumentResponse)
async def ingest_rag_document(
    payload: RagIngestRequest,
    current_user: dict = Depends(
        require_roles([Role.super_admin, Role.tenant_admin, Role.operator])
    ),
    app_key: str = Depends(inject_app_key),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)

    try:
        result = await ingest_document(
            tenant_id=tenant_id,
            app_key=app_key,
            created_by=current_user.get("sub", "system"),
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RagDocumentResponse(**result)


@router.get("/acts", response_model=IngestedActsListResponse)
async def get_ingested_acts_public(
    app_key: str = Depends(inject_app_key),
):
    """
    PUBLIC endpoint: Get list of ingested legal acts (no authentication required).
    Perfect for carousel badges and public-facing act lists.
    Returns only act name and year for each ingested document.
    """
    # For public endpoints, use the default tenant for the app_key
    # LegalMitra uses tenant_id "seed-tenant-1"
    tenant_id = "seed-tenant-1"
    items = await list_documents(tenant_id=tenant_id, app_key=app_key, limit=200)

    # Extract unique acts from documents
    acts_dict = {}
    for item in items:
        legal_meta = item.get("legal_metadata") or {}
        act_name = legal_meta.get("act_name") or item.get("title", "Unknown Act")

        if act_name not in acts_dict:
            # Get year from doc_date or current year
            doc_date = legal_meta.get("doc_date")
            if doc_date:
                try:
                    from datetime import datetime
                    if isinstance(doc_date, str):
                        year = int(doc_date.split("-")[0])
                    else:
                        year = doc_date.year
                except (ValueError, AttributeError, IndexError):
                    year = "2023"
            else:
                year = "2023"

            acts_dict[act_name] = year

    acts = [IngestedActInfo(name=name, year=year) for name, year in sorted(acts_dict.items())]
    return IngestedActsListResponse(acts=acts, count=len(acts))


@router.get("/documents", response_model=RagDocumentListResponse)
async def get_rag_documents(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin, Role.operator, Role.viewer])),
    app_key: str = Depends(inject_app_key),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    items = await list_documents(tenant_id=tenant_id, app_key=app_key, limit=limit)
    return RagDocumentListResponse(items=[RagDocumentResponse(**item) for item in items], count=len(items))


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    payload: RagQueryRequest,
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin, Role.operator, Role.viewer])),
    app_key: str = Depends(inject_app_key),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    try:
        user_id = current_user.get("sub") or current_user.get("user_id")
        result = await query_knowledge(
            tenant_id=tenant_id,
            app_key=app_key,
            payload=payload,
            user_id=user_id,
            actor=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return RagQueryResponse(**result)
