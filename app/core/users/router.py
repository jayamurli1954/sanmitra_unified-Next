from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.security import hash_password, verify_password
from app.core.tenants.service import get_tenant
from app.core.users.schemas import UserCreateRequest, UserResponse
from app.core.users.service import create_user
from app.db.mongo import get_collection

router = APIRouter(prefix="/users", tags=["users"])

_ME_PROFILE_FIELDS = frozenset({
    "user_id",
    "email",
    "full_name",
    "role",
    "system_role",
    "tenant_id",
    "app_key",
    "auth_provider",
    "is_active",
    "mobile",
    "phone",
    "avatar_url",
    "permissions",
    "accounting_entity_ids",
    "created_at",
    "updated_at",
    "last_login_at",
    "provider_subject",
    "accepted_terms_at",
})


def _public_user_profile(current_user: dict, user_doc: dict | None) -> dict:
    merged = {**current_user, **(user_doc or {})}
    profile = {key: merged[key] for key in _ME_PROFILE_FIELDS if key in merged}
    resolved_user_id = str(profile.get("user_id") or merged.get("sub") or "").strip()
    if resolved_user_id:
        profile["user_id"] = resolved_user_id
        profile["id"] = resolved_user_id
    role = str(profile.get("role") or merged.get("role") or "").strip()
    if role:
        profile["role"] = role
        profile.setdefault("system_role", role)
    profile["is_superuser"] = bool(merged.get("is_superuser")) or role == "super_admin"
    profile["is_active"] = bool(merged.get("is_active", True))
    return profile


def _validate_profile_email(email: str) -> None:
    if (
        not email
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
        or any(ch.isspace() for ch in email)
    ):
        raise HTTPException(status_code=400, detail="Valid email is required")


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    tenant_id = str(current_user.get("tenant_id") or "").strip()
    tenant = await get_tenant(tenant_id) if tenant_id else None
    user_id = str(current_user.get("sub") or current_user.get("user_id") or "").strip()
    email = str(current_user.get("email") or "").strip().lower()
    user_doc = None
    try:
        users = get_collection("core_users")
        if user_id:
            user_doc = await users.find_one({"user_id": user_id})
        if user_doc is None and email:
            user_doc = await users.find_one({"email": email})
    except RuntimeError as exc:
        if "MongoDB is not initialized" not in str(exc):
            raise
    merged_user = _public_user_profile(current_user, user_doc)
    resolved_user_id = str(merged_user.get("user_id") or user_id or "").strip()
    return {
        **merged_user,
        "_id": None,
        "id": resolved_user_id,
        "user_id": resolved_user_id,
        "tenant": tenant,
        "organization_type": (tenant or {}).get("organization_type"),
        "enabled_modules": (tenant or {}).get("enabled_modules", []),
        "subscription_plan": (tenant or {}).get("subscription_plan", "free"),
    }


@router.put("/{user_id}")
async def update_user_profile(
    user_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    actor_user_id = str(current_user.get("sub") or current_user.get("user_id") or "").strip()
    requested_user_id = str(user_id or "").strip()
    if not requested_user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    if requested_user_id != actor_user_id:
        raise HTTPException(status_code=403, detail="Users can update only their own profile")

    users = get_collection("core_users")
    existing = await users.find_one({"user_id": requested_user_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found")

    patch: dict = {"updated_at": datetime.now(timezone.utc)}
    if "full_name" in payload:
        full_name = str(payload.get("full_name") or "").strip()
        if len(full_name) < 2:
            raise HTTPException(status_code=400, detail="Full name must be at least 2 characters")
        patch["full_name"] = full_name
    if "email" in payload:
        email = str(payload.get("email") or "").strip().lower()
        _validate_profile_email(email)
        duplicate = await users.find_one({"email": email, "user_id": {"$ne": requested_user_id}})
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="User with this email already exists")
        patch["email"] = email
        patch["provider_subject"] = f"password:{email}"
    if "phone" in payload:
        phone = str(payload.get("phone") or "").strip()
        patch["phone"] = phone or None
    if "password" in payload:
        new_password = str(payload.get("password") or "")
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        current_password = str(payload.get("current_password") or "")
        if not current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not existing.get("hashed_password") or not verify_password(current_password, str(existing["hashed_password"])):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        patch["hashed_password"] = hash_password(new_password)
        patch["must_change_password"] = False

    await users.update_one({"user_id": requested_user_id}, {"$set": patch})
    doc = await users.find_one({"user_id": requested_user_id}) or {**existing, **patch}
    return {
        "id": str(doc.get("user_id") or requested_user_id),
        "user_id": str(doc.get("user_id") or requested_user_id),
        "email": str(doc.get("email") or ""),
        "full_name": str(doc.get("full_name") or ""),
        "phone": doc.get("phone"),
        "role": doc.get("role"),
        "system_role": doc.get("system_role") or doc.get("role"),
        "role_key": doc.get("role_key"),
        "role_label": doc.get("role_label"),
        "module_permissions": doc.get("module_permissions") or {},
        "action_permissions": doc.get("action_permissions") or {},
        "is_superuser": bool(doc.get("is_superuser")) or str(doc.get("role") or "").strip() == "super_admin",
        "is_active": bool(doc.get("is_active", True)),
        "must_change_password": bool(doc.get("must_change_password", False)),
    }


@router.get("/me/usage")
async def get_my_usage(current_user: dict = Depends(get_current_user)):
    """Retrieve current usage statistics and tier limits for the logged-in user."""
    from app.db.mongo import get_collection
    from app.core.billing.limits import get_tier_limits
    from app.core.billing.usage import _has_privileged_usage_access
    
    user_id = current_user.get("sub")
    users = get_collection("core_users")
    user = await users.find_one({"user_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    tier = user.get("subscription_tier", "free").lower()
    privileged_usage_access = _has_privileged_usage_access(current_user) or _has_privileged_usage_access(user)
    effective_tier = "pro" if privileged_usage_access else tier
    limits = get_tier_limits(effective_tier)
    
    return {
        "tier": tier,
        "effective_tier": effective_tier,
        "role": user.get("role") or current_user.get("role"),
        "privileged_usage_access": privileged_usage_access,
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
            accounting_entity_ids=payload.accounting_entity_ids,
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
