"""MandirMitra festival master routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

@router.get("/festivals")
async def list_mandir_festivals(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="festival listing"
    )
    rows = await mandir_router.get_collection("mandir_festivals").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("start_date", -1).to_list(length=500)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.post("/festivals", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def create_mandir_festival(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="festival creation"
    )
    name = str(payload.get("name") or "").strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Festival name is required")
    start_date = str(payload.get("start_date") or "").strip()
    end_date = str(payload.get("end_date") or start_date).strip()
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid festival start_date and end_date are required") from exc
    if start > end:
        raise HTTPException(status_code=400, detail="Festival start_date cannot be after end_date")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid4()), "tenant_id": context.tenant_id, "app_key": context.app_key,
        "name": name, "start_date": start.isoformat(), "end_date": end.isoformat(), "active": True,
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_festivals").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)

