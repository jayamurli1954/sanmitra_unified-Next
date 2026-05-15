from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.service import get_tenant
from app.core.users.schemas import UserCreateRequest, UserResponse
from app.core.users.service import create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    tenant_id = str(current_user.get("tenant_id") or "").strip()
    tenant = await get_tenant(tenant_id) if tenant_id else None
    return {
        **current_user,
        "tenant": tenant,
        "organization_type": (tenant or {}).get("organization_type"),
        "enabled_modules": (tenant or {}).get("enabled_modules", []),
        "subscription_plan": (tenant or {}).get("subscription_plan", "free"),
    }


@router.get("/me/usage")
async def get_my_usage(current_user: dict = Depends(get_current_user)):
    """Retrieve current usage statistics and tier limits for the logged-in user."""
    from app.db.mongo import get_collection
    from app.core.billing.limits import get_tier_limits
    
    user_id = current_user.get("sub")
    users = get_collection("core_users")
    user = await users.find_one({"user_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    tier = user.get("subscription_tier", "free").lower()
    limits = get_tier_limits(tier)
    
    return {
        "tier": tier,
        "limits": limits,
        "usage": {
            "daily_research": {
                "count": user.get("daily_research_count", 0),
                "limit": limits.get("daily_research_queries"),
                "reset_date": user.get("last_research_date")
            },
            "monthly_templates": {
                "count": user.get("monthly_template_count", 0),
                "limit": limits.get("monthly_templates"),
                "reset_month": user.get("last_template_month")
            },
            "total_research": user.get("total_research_count", 0),
            "total_templates": user.get("total_template_count", 0)
        }
    }


@router.post("", response_model=UserResponse)
async def register_user(payload: UserCreateRequest, current_user: dict = Depends(get_current_user)):
    role = current_user.get("role")
    if role not in {"super_admin", "tenant_admin"}:
        raise HTTPException(status_code=403, detail="Only admins can create users")

    if role == "tenant_admin" and current_user.get("tenant_id") != payload.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant admin cannot create users outside tenant")

    try:
        user = await create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            tenant_id=payload.tenant_id,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return UserResponse(**user)


@router.post("/accept-terms")
async def accept_terms(current_user: dict = Depends(get_current_user)):
    """Record that the user has accepted the Terms & Disclaimer."""
    from app.db.mongo import get_collection
    from datetime import datetime, timezone
    
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")
        
    users = get_collection("core_users")
    await users.update_one(
        {"user_id": user_id},
        {"$set": {"accepted_terms_at": datetime.now(timezone.utc)}}
    )
    return {"status": "success", "accepted_at": datetime.now(timezone.utc)}
