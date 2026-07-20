"""MandirMitra devotee CRUD and mobile lookup routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Uses runtime lookup on the router module for get_collection and shared helpers.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

_logger = logging.getLogger(__name__)


@router.get("/devotees")
@router.get("/devotees/")
async def list_devotees(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = mandir_router._to_positive_int(x_temple_id)

    try:
        col = mandir_router.get_collection("mandir_devotees")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
        if temple_id is not None:
            query["temple_id"] = temple_id
        rows = await (
            col.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return [mandir_router._sanitize_mongo_doc(row) for row in rows]
    except Exception as exc:
        _logger.error("Failed to list devotees for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []


@router.post("/devotees", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/devotees/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_devotee(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee create",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = mandir_router._to_positive_int(x_temple_id)

    devotee = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "temple_id": temple_id,
        "name": str(payload.get("name") or payload.get("first_name") or "Unnamed Devotee"),
        "first_name": str(payload.get("first_name") or ""),
        "last_name": str(payload.get("last_name") or ""),
        "phone": mandir_router._normalize_phone(payload.get("phone") or payload.get("mobile") or payload.get("devotee_phone")),
        "email": str(payload.get("email") or "") or None,
        "address": str(payload.get("address") or "") or None,
        "city": str(payload.get("city") or "") or None,
        "state": str(payload.get("state") or "") or None,
        "pincode": str(payload.get("pincode") or "") or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col = mandir_router.get_collection("mandir_devotees")
        await col.insert_one(devotee)
    except Exception as exc:
        _logger.error("Failed to insert devotee for tenant=%s: %s", tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save devotee") from exc

    return mandir_router._sanitize_mongo_doc(devotee)


@router.get("/devotees/search/by-mobile/{phone}")
async def search_devotee_by_mobile(
    phone: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee mobile search",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = mandir_router._to_positive_int(x_temple_id)
    normalized = mandir_router._normalize_phone(phone)

    if not normalized:
        return []

    try:
        col = mandir_router.get_collection("mandir_devotees")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized}
        if temple_id is not None:
            query["temple_id"] = temple_id
        docs = await col.find(query).limit(5).to_list(length=5)
        if docs:
            return [mandir_router._sanitize_mongo_doc(doc) for doc in docs]
        fallback = await mandir_router._find_devotee_by_phone(tenant_id, app_key, normalized, temple_id=temple_id)
        return [fallback] if fallback else []
    except Exception as exc:
        _logger.error("Failed to search devotees by mobile for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []


@router.get("/devotees/autofill/by-mobile/{phone}")
async def autofill_devotee_by_mobile(
    phone: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee mobile autofill",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = mandir_router._to_positive_int(x_temple_id)
    normalized = mandir_router._normalize_phone(phone)
    if not normalized:
        return {"found": False, "phone": normalized, "devotee": None}

    try:
        devotee = await mandir_router._find_devotee_by_phone(tenant_id, app_key, normalized, temple_id=temple_id)
        if devotee is None:
            return {"found": False, "phone": normalized, "devotee": None}
        return {"found": True, "phone": normalized, "devotee": devotee}
    except Exception as exc:
        _logger.error("Failed to autofill devotee by mobile for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return {"found": False, "phone": normalized, "devotee": None}
