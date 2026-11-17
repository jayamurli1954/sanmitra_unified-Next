"""MandirMitra user list and profile routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Header

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

_USER_LIST_ADMIN_ROLES = {"super_admin", "tenant_admin"}


@router.get("/users")
async def mandir_users(_current_user: dict = Depends(get_current_user), x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")):
    """Tenant user list for administrators. Other roles get only their own record, so
    pickers that expect a list keep working without exposing colleagues' emails."""
    tenant_id = mandir_router.resolve_tenant_id(_current_user, x_tenant_id)
    users = mandir_router.get_collection("core_users")
    query: dict[str, Any] = {"tenant_id": tenant_id, "is_active": True}
    if str(_current_user.get("role") or "").strip() not in _USER_LIST_ADMIN_ROLES:
        query["user_id"] = str(_current_user.get("sub") or "")
    docs = await users.find(query).limit(200).to_list(length=200)
    return [{"user_id": d.get("user_id"), "email": d.get("email"), "full_name": d.get("full_name"), "role": d.get("role")} for d in docs]


# PUT /users/{user_id} and GET /users/me are served by app.core.users.router
# (registered first). The unguarded Mandir copies were removed so a router reorder
# can never re-expose them.
