"""MandirMitra role permission routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

@router.get("/role-permissions")
async def mandir_role_permissions(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    default_roles = [
        {"role_key": "president", "display_name": "President", "is_enabled": True},
        {"role_key": "secretary", "display_name": "Secretary", "is_enabled": True},
        {"role_key": "treasurer", "display_name": "Treasurer", "is_enabled": True},
        {"role_key": "counter_clerk", "display_name": "Counter Clerk", "is_enabled": True},
        {"role_key": "accounts_clerk", "display_name": "Accounts Clerk", "is_enabled": True},
        {"role_key": "priest_operator", "display_name": "Priest / Temple Operator", "is_enabled": True},
    ]
    docs = await mandir_router.get_collection("mandir_role_permissions").find({"tenant_id": tenant_id, "app_key": app_key}).to_list(length=200)
    by_role = {str(doc.get("role_key") or ""): doc for doc in docs}
    roles = []
    for base in default_roles:
        current = by_role.get(base["role_key"]) or {}
        roles.append(
            {
                "role_key": base["role_key"],
                "display_name": base["display_name"],
                "is_enabled": bool(current.get("is_enabled", base["is_enabled"])),
                "module_permissions": current.get("module_permissions") or {},
                "action_permissions": current.get("action_permissions") or {},
            }
        )
    return {
        "modules": [],
        "actions": [],
        "roles": roles,
        "policy_notice": "Accounting transactions should be reversed with audit reason instead of hard delete.",
    }


@router.put("/role-permissions/{role_key}", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_role_permissions_update(
    role_key: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "role_key": str(role_key).strip().lower(),
        "display_name": str(payload.get("display_name") or role_key).strip(),
        "is_enabled": bool(payload.get("is_enabled", True)),
        "module_permissions": payload.get("module_permissions") or {},
        "action_permissions": payload.get("action_permissions") or {},
        "updated_at": now,
    }
    await mandir_router.get_collection("mandir_role_permissions").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "role_key": doc["role_key"]},
        {
            "$set": doc,
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )
    return {"role": doc}


@router.get("/role-permissions/assignable")
async def mandir_role_permissions_assignable(_current_user: dict = Depends(get_current_user)):
    return {
        "roles": [
            {"role_key": "treasurer", "display_name": "Treasurer"},
            {"role_key": "counter_clerk", "display_name": "Counter Clerk"},
            {"role_key": "accounts_clerk", "display_name": "Accounts Clerk"},
            {"role_key": "priest_operator", "display_name": "Priest / Temple Operator"},
        ]
    }


