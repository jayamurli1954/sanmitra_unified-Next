"""LegalMitra Citation Checker API — verify authorities in pasted or uploaded text."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.billing.usage import get_usage_limits_for_user
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.context import resolve_tenant_id
from app.modules.legal_compat import citation_checker as cc

router = APIRouter(tags=["legal-compat"])
_logger = logging.getLogger(__name__)

_DEFAULT_APP_KEY = "legalmitra"
_LIBRARY_LOOKUP_TIMEOUT_S = 4.0
_any_authenticated = require_roles(
    [Role.viewer, Role.operator, Role.accountant, Role.tenant_admin, Role.super_admin]
)


def _resolve_compat_app_key(x_app_key: str | None) -> str:
    value = (x_app_key or "").strip().lower()
    return value or _DEFAULT_APP_KEY


class CitationCheckRequest(BaseModel):
    text: str = Field(min_length=3, max_length=cc.MAX_TEXT_CHARS)
    search_library: bool = True


def _library_lookup_for(tenant_id: str, app_key: str) -> cc.LibraryLookup:
    async def _lookup(query: str) -> list[dict[str, Any]]:
        from app.modules.rag.schemas import RagQueryRequest
        from app.modules.rag.service import query_knowledge

        result = await asyncio.wait_for(
            query_knowledge(
                tenant_id=tenant_id,
                app_key=app_key,
                payload=RagQueryRequest(query=query[:2000], top_k=5),
            ),
            timeout=_LIBRARY_LOOKUP_TIMEOUT_S,
        )
        return list((result or {}).get("citations") or [])

    return _lookup


async def _run_check(*, text: str, tenant_id: str, app_key: str, search_library: bool) -> dict[str, Any]:
    lookup = _library_lookup_for(tenant_id, app_key) if search_library else None
    result = await cc.check_citations(text, library_lookup=lookup)
    _logger.info(
        "citation_check tenant=%s app=%s items=%d errors=%d warnings=%d",
        tenant_id,
        app_key,
        result["summary"]["total"],
        result["summary"]["error"],
        result["summary"]["warning"],
    )
    return {"ok": True, **result}


@router.post("/legalmitra/citation-check")
async def legalmitra_citation_check(
    payload: CitationCheckRequest,
    current_user: dict = Depends(_any_authenticated),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Check every case citation and criminal-code section in pasted text.

    Deterministic — no AI generation. The submitted text is not stored.
    """
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_compat_app_key(x_app_key)
    return await _run_check(
        text=payload.text, tenant_id=tenant_id, app_key=app_key, search_library=payload.search_library
    )


@router.post("/legalmitra/citation-check/upload")
async def legalmitra_citation_check_upload(
    file: UploadFile = File(...),
    current_user: dict = Depends(_any_authenticated),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Check authorities in an uploaded PDF / DOCX / TXT (text layer only, no OCR).

    The file is read in memory and not stored.
    """
    from app.modules.legal_compat.router import _read_upload_with_size_limit

    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_compat_app_key(x_app_key)
    user_id = str(current_user.get("sub") or current_user.get("user_id") or "")
    limits = await get_usage_limits_for_user(user_id, actor=current_user)
    content = await _read_upload_with_size_limit(
        file=file,
        limit_bytes=int(limits.get("max_document_upload_bytes") or 0),
        feature_name="Citation check upload",
    )
    try:
        text = cc.extract_document_text(file.filename or "", content)
    except cc.UnsupportedDocumentError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception as exc:  # malformed PDF/DOCX
        raise HTTPException(status_code=422, detail="Could not read text from this file.") from exc

    if len(text.strip()) < 3:
        raise HTTPException(
            status_code=422,
            detail="No readable text found. Scanned PDFs need OCR, which is not supported yet — paste the text instead.",
        )
    result = await _run_check(text=text, tenant_id=tenant_id, app_key=app_key, search_library=True)
    result["file_name"] = file.filename
    return result
