"""MandirMitra current-temple profile routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

@router.get("/temples/current")
async def get_current_temple(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    col = mandir_router.get_collection("mandir_temples")
    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key})
    if doc:
        return mandir_router._sanitize_mongo_doc(doc)

    now = datetime.now(timezone.utc).isoformat()
    transient_temple_id = temple_id if temple_id and temple_id > 0 else None
    fallback = {
        "id": transient_temple_id,
        "temple_id": transient_temple_id,
        "tenant_id": tenant_id,
        "name": "Temple",
        "trust_name": "Temple Trust",
        "city": "Bengaluru",
        "state": "Karnataka",
        "platform_can_write": False,
        "is_placeholder": True,
        "is_active": True,
        "updated_at": now,
        "created_at": now,
    }
    return fallback


@router.put("/temples/current", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def update_current_temple(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await mandir_router.ensure_temple_numeric_id(tenant_id, app_key=app_key)
    col = mandir_router.get_collection("mandir_temples")
    now = datetime.now(timezone.utc).isoformat()
    update = {k: v for k, v in payload.items() if k not in {"id", "_id", "tenant_id", "temple_id"}}
    if "donation_categories" in payload:
        update["donation_categories"] = mandir_router._normalize_public_donation_categories(
            payload.get("donation_categories"),
            fallback_to_default=False,
        )
    update["updated_at"] = now

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": {**update, "id": assigned_temple_id, "temple_id": assigned_temple_id},
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return await col.find_one({"tenant_id": tenant_id})

