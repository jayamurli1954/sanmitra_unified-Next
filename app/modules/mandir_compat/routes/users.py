"""MandirMitra user list and profile routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

@router.get("/users")
async def mandir_users(_current_user: dict = Depends(get_current_user), x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, x_tenant_id)
    users = mandir_router.get_collection("core_users")
    docs = await users.find({"tenant_id": tenant_id, "is_active": True}).limit(200).to_list(length=200)
    return [{"user_id": d.get("user_id"), "email": d.get("email"), "full_name": d.get("full_name"), "role": d.get("role")} for d in docs]



@router.put("/users/{user_id}")
async def mandir_update_user_profile(
    user_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    users = mandir_router.get_collection("core_users")
    query = {
        "tenant_id": tenant_id,
        "$or": [
            {"user_id": user_id},
            {"id": user_id},
        ],
    }

    patch: dict[str, Any] = {}
    if "full_name" in payload:
        patch["full_name"] = str(payload.get("full_name") or "").strip()
    if "email" in payload:
        patch["email"] = str(payload.get("email") or "").strip().lower()
    if "phone" in payload:
        phone = str(payload.get("phone") or "").strip()
        patch["phone"] = phone or None
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    await users.update_one(query, {"$set": patch}, upsert=False)
    doc = await users.find_one(query)
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found")

    resolved_id = str(doc.get("user_id") or doc.get("id") or user_id)
    return {
        "id": resolved_id,
        "email": str(doc.get("email") or ""),
        "full_name": str(doc.get("full_name") or ""),
        "phone": doc.get("phone"),
        "role": doc.get("role"),
        "system_role": doc.get("system_role") or doc.get("role"),
        "role_key": doc.get("role_key"),
        "role_label": doc.get("role_label"),
        "module_permissions": doc.get("module_permissions") or {},
        "action_permissions": doc.get("action_permissions") or {},
        "is_superuser": bool(doc.get("is_superuser", False)),
        "must_change_password": bool(doc.get("must_change_password", False)),
    }

