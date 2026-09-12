"""ADR-016 Documents routes (kept separate to avoid growing office_ai/router.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.modules.dependencies import require_enabled_module, require_enabled_module_feature
from app.core.modules.registry import (
    is_office_ai_documents_enabled,
    is_office_ai_review_notes_enabled,
)
from app.modules.office_ai import schemas
from app.modules.office_ai.services import documents_service

router = APIRouter(prefix="/officemitra", tags=["officemitra"])


def _tenant_id(ctx: dict) -> str:
    return str((ctx.get("tenant") or {}).get("tenant_id") or (ctx.get("user") or {}).get("tenant_id") or "").strip()


def documents_ping_fields(tenant: dict) -> dict:
    enabled = is_office_ai_documents_enabled(
        enabled_modules=tenant.get("enabled_modules") or [],
        office_ai_features=tenant.get("office_ai_features"),
    )
    return {
        "documents_enabled": enabled,
        "documents_capabilities": {
            "client_portal": False,
            "companion_writes": False,
        },
        "adr_016": "accepted",
    }


@router.get("/documents/status")
async def documents_status(ctx: dict = Depends(require_enabled_module("office_ai"))) -> dict:
    fields = documents_ping_fields(ctx.get("tenant") or {})
    return {
        **fields,
        "live_ledger_writes": False,
    }


@router.get("/documents/queue")
async def list_documents_queue(
    accounting_entity_id: str | None = Query(default=None, max_length=80),
    engagement_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "documents")),
) -> dict:
    try:
        return await documents_service.list_queue(
            tenant_id=_tenant_id(ctx),
            tenant=ctx.get("tenant") or {},
            accounting_entity_id=accounting_entity_id,
            engagement_id=engagement_id,
            status=status,
            limit=limit,
        )
    except documents_service.DocumentsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents/notes/{note_id}/link")
async def link_document_to_note(
    note_id: str,
    payload: schemas.DocumentsLinkNoteRequest,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "documents")),
) -> dict:
    tenant = ctx.get("tenant") or {}
    if not is_office_ai_review_notes_enabled(
        enabled_modules=tenant.get("enabled_modules") or [],
        office_ai_features=tenant.get("office_ai_features"),
    ):
        raise HTTPException(status_code=403, detail="Enable office_ai.review.notes to link documents")
    try:
        return await documents_service.link_note(
            tenant_id=_tenant_id(ctx),
            tenant=tenant,
            user=ctx["user"],
            note_id=note_id,
            document_id=payload.document_id,
        )
    except documents_service.DocumentsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except documents_service.DocumentsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/documents/notes/{note_id}/unlink")
async def unlink_document_from_note(
    note_id: str,
    ctx: dict = Depends(require_enabled_module_feature("office_ai", "documents")),
) -> dict:
    tenant = ctx.get("tenant") or {}
    if not is_office_ai_review_notes_enabled(
        enabled_modules=tenant.get("enabled_modules") or [],
        office_ai_features=tenant.get("office_ai_features"),
    ):
        raise HTTPException(status_code=403, detail="Enable office_ai.review.notes to unlink documents")
    try:
        return await documents_service.unlink_note(
            tenant_id=_tenant_id(ctx),
            user=ctx["user"],
            note_id=note_id,
        )
    except documents_service.DocumentsNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except documents_service.DocumentsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
