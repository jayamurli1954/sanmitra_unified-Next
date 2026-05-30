from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.core.platform_owner.service import get_platform_owner_dashboard

router = APIRouter(prefix="/platform-owner", tags=["platform-owner"])


@router.get("/dashboard")
async def platform_owner_dashboard(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    if str(current_user.get("role") or "").strip() != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can view platform owner dashboard")

    return await get_platform_owner_dashboard(limit=limit)
