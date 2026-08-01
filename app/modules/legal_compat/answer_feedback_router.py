"""LegalMitra answer-feedback routes (Stage 2 quality instrumentation)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.context import resolve_tenant_id
from app.modules.legal_compat.retention import save_answer_feedback, summarize_answer_feedback

router = APIRouter(tags=["legal-compat"])

_DEFAULT_APP_KEY = "legalmitra"
_any_authenticated = require_roles(
    [Role.viewer, Role.operator, Role.accountant, Role.tenant_admin, Role.super_admin]
)


def _resolve_compat_app_key(x_app_key: str | None) -> str:
    value = (x_app_key or "").strip().lower()
    return value or _DEFAULT_APP_KEY


class AnswerFeedbackRequest(BaseModel):
    answer_id: str = Field(min_length=1, max_length=200)
    feedback_type: str = Field(min_length=1, max_length=40)
    value: Any = None
    query: str | None = Field(default=None, max_length=2000)
    provider: str | None = Field(default=None, max_length=80)
    strategy: str | None = Field(default=None, max_length=120)
    confidence: str | None = Field(default=None, max_length=40)
    history_record_id: str | None = Field(default=None, max_length=80)


@router.post("/legalmitra/answer-feedback")
async def legalmitra_answer_feedback(
    payload: AnswerFeedbackRequest,
    current_user: dict = Depends(_any_authenticated),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_compat_app_key(x_app_key)
    user_id = str(current_user.get("sub") or current_user.get("user_id") or "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User context missing")

    saved = await save_answer_feedback(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=user_id,
        answer_id=payload.answer_id,
        feedback_type=payload.feedback_type,
        value=payload.value,
        query=payload.query,
        provider=payload.provider,
        strategy=payload.strategy,
        confidence=payload.confidence,
        history_record_id=payload.history_record_id,
    )
    return {"ok": True, **saved}


@router.get("/legalmitra/answer-feedback/summary")
async def legalmitra_answer_feedback_summary(
    limit: int = Query(default=200, ge=1, le=500),
    current_user: dict = Depends(require_roles([Role.tenant_admin, Role.super_admin, Role.operator])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = _resolve_compat_app_key(x_app_key)
    return await summarize_answer_feedback(tenant_id=tenant_id, app_key=app_key, limit=limit)
