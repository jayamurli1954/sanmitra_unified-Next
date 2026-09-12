"""ADR-015 Review routes (kept separate to avoid growing office_ai/router.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.modules.dependencies import require_enabled_module, require_enabled_module_feature
from app.core.modules.registry import (
    is_office_ai_review_enabled,
    is_office_ai_review_notes_enabled,
    is_office_ai_review_working_papers_enabled,
)
from app.modules.office_ai import schemas
from app.modules.office_ai.services import mis_store, review_service, review_store

router = APIRouter(prefix="/officemitra", tags=["officemitra"])


def _tenant_id(ctx: dict) -> str:
    return str((ctx.get("tenant") or {}).get("tenant_id") or (ctx.get("user") or {}).get("tenant_id") or "").strip()


def review_capability_flags(tenant: dict) -> dict[str, bool]:
    enabled_modules = tenant.get("enabled_modules") or []
    office_ai_features = tenant.get("office_ai_features")
    return {
        "review": is_office_ai_review_enabled(
            enabled_modules=enabled_modules,
            office_ai_features=office_ai_features,
        ),
        "working_papers": is_office_ai_review_working_papers_enabled(
            enabled_modules=enabled_modules,
            office_ai_features=office_ai_features,
        ),
        "notes": is_office_ai_review_notes_enabled(
            enabled_modules=enabled_modules,
            office_ai_features=office_ai_features,
        ),
    }


def review_ping_fields(tenant: dict) -> dict:
    flags = review_capability_flags(tenant)
    return {
        "review_enabled": flags["review"],
        "review_capabilities": {
            "working_papers": flags["working_papers"],
            "notes": flags["notes"],
        },
        "adr_015": "accepted",
    }


@router.get("/review/status")
async def review_status(ctx: dict = Depends(require_enabled_module("office_ai"))) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    return {
        "review_enabled": flags["review"],
        "capabilities": {"working_papers": flags["working_papers"], "notes": flags["notes"]},
        "adr_015": "accepted",
        "live_ledger_writes": False,
    }


@router.get("/review/engagements")
async def list_review_engagements(
    limit: int = Query(default=50, ge=1, le=200),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    items = await review_store.list_engagements(tenant_id=_tenant_id(ctx), limit=limit)
    return {"items": items, "count": len(items)}


@router.post("/review/engagements")
async def create_review_engagement(
    payload: schemas.ReviewEngagementCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    try:
        item = await review_service.create_engagement(
            tenant_id=_tenant_id(ctx),
            user=ctx["user"],
            period=payload.period,
            pack_id=payload.pack_id,
            accounting_entity_id=payload.accounting_entity_id,
            jurisdiction=payload.jurisdiction,
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (review_store.ReviewStoreError, review_service.ReviewServiceError, mis_store.MISStoreError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@router.get("/review/engagements/{engagement_id}")
async def get_review_engagement(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    item = await review_store.get_engagement(tenant_id=_tenant_id(ctx), engagement_id=engagement_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return {"item": item}


@router.post("/review/engagements/{engagement_id}/link-pack")
async def link_review_pack(
    engagement_id: str,
    payload: schemas.ReviewLinkPackRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    try:
        item = await review_service.link_pack(
            tenant_id=_tenant_id(ctx),
            engagement_id=engagement_id,
            user=ctx["user"],
            pack_id=payload.pack_id,
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (review_store.ReviewStoreError, review_service.ReviewServiceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@router.post("/review/engagements/{engagement_id}/scan")
async def scan_review_engagement(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    try:
        return await review_service.scan_engagement(
            tenant_id=_tenant_id(ctx),
            engagement_id=engagement_id,
            user=ctx["user"],
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except mis_store.MISPackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (review_store.ReviewStoreError, review_service.ReviewServiceError, mis_store.MISStoreError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/review/engagements/{engagement_id}/issues")
async def list_review_issues(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    try:
        items = await review_store.list_issues(tenant_id=_tenant_id(ctx), engagement_id=engagement_id)
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}


@router.post("/review/engagements/{engagement_id}/working-papers")
async def generate_review_working_papers(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["working_papers"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.working_papers")
    try:
        return await review_service.generate_working_papers(
            tenant_id=_tenant_id(ctx),
            engagement_id=engagement_id,
            user=ctx["user"],
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (review_store.ReviewStoreError, review_service.ReviewServiceError, mis_store.MISStoreError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/review/engagements/{engagement_id}/working-papers")
async def list_review_working_papers(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["working_papers"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.working_papers")
    try:
        items = await review_store.list_papers(tenant_id=_tenant_id(ctx), engagement_id=engagement_id)
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}


@router.post("/review/working-papers/{paper_id}/close")
async def close_review_working_paper(
    paper_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["working_papers"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.working_papers")
    try:
        item = await review_store.close_paper(
            tenant_id=_tenant_id(ctx),
            paper_id=paper_id,
            user=ctx["user"],
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except review_store.ReviewImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except review_store.ReviewStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}


@router.get("/review/working-papers/{paper_id}/download")
async def download_review_working_paper(
    paper_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> Response:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["working_papers"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.working_papers")
    artifact = await review_store.get_paper(
        tenant_id=_tenant_id(ctx),
        paper_id=paper_id,
        include_content=True,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Working paper not found")
    filename = str(artifact.get("filename") or "working-paper.xlsx")
    content_type = str(artifact.get("content_type") or "application/octet-stream")
    content = artifact.get("content") or b""
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/review/engagements/{engagement_id}/notes")
async def list_review_notes(
    engagement_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["notes"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.notes")
    try:
        items = await review_store.list_notes(tenant_id=_tenant_id(ctx), engagement_id=engagement_id)
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items, "count": len(items)}


@router.post("/review/engagements/{engagement_id}/notes")
async def create_review_note(
    engagement_id: str,
    payload: schemas.ReviewNoteCreateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["notes"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.notes")
    try:
        return await review_service.create_note_with_task(
            tenant_id=_tenant_id(ctx),
            engagement_id=engagement_id,
            user=ctx["user"],
            description=payload.description,
            issue_id=payload.issue_id,
            assigned_to=payload.assigned_to,
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except review_store.ReviewStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/review/notes/{note_id}")
async def update_review_note(
    note_id: str,
    payload: schemas.ReviewNoteUpdateRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "review")),
) -> dict:
    flags = review_capability_flags(ctx.get("tenant") or {})
    if not flags["notes"]:
        raise HTTPException(status_code=403, detail="Enable office_ai.review.notes")
    updates = payload.model_dump(exclude_unset=True)
    try:
        item = await review_store.update_note(
            tenant_id=_tenant_id(ctx),
            note_id=note_id,
            user=ctx["user"],
            updates=updates,
        )
    except review_store.ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except review_store.ReviewStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": item}
