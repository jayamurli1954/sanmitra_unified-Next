from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.config import get_settings
from app.db.mongo import get_collection
from app.core.billing.limits import get_tier_limits

PRIVILEGED_USAGE_ROLES = {"platform_owner", "super_admin", "owner"}


def _has_privileged_usage_role(user: dict | None) -> bool:
    if not user:
        return False
    role = str(user.get("role") or "").strip().lower().replace("-", "_").replace(" ", "_")
    return role in PRIVILEGED_USAGE_ROLES


def _has_privileged_usage_email(user: dict | None) -> bool:
    if not user:
        return False
    email = str(user.get("email") or "").strip().lower()
    if not email:
        return False
    settings = get_settings()
    super_admin_email = str(settings.SUPER_ADMIN_EMAIL or "").strip().lower()
    return bool(super_admin_email and email == super_admin_email)


def _has_privileged_usage_access(user: dict | None) -> bool:
    return _has_privileged_usage_role(user) or _has_privileged_usage_email(user)


async def ensure_terms_accepted(user_id: str | None):
    if not user_id:
        return True

    users_col = get_collection("core_users")
    user = await users_col.find_one({"user_id": user_id})
    if user and not user.get("accepted_terms_at"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Legal Agreement Required: Please review and accept the Terms of Use and Disclaimer to continue."
        )
    return True


async def get_usage_limits_for_user(user_id: str | None, actor: dict | None = None) -> dict:
    tier = str((actor or {}).get("subscription_tier") or "free").lower()

    if user_id:
        users_col = get_collection("core_users")
        user = await users_col.find_one({"user_id": user_id})
        if user:
            tier = str(user.get("subscription_tier") or tier).lower()

    return get_tier_limits(tier)

async def check_and_increment_usage(user_id: str, feature: str, actor: dict | None = None):
    """
    Checks if a user has reached their tier limit for a specific feature and increments the counter.

    Features supported:
    - 'daily_research_queries'
    - 'monthly_templates'
    - 'max_compliance_records'
    """
    if _has_privileged_usage_access(actor):
        return True

    users_col = get_collection("core_users")
    user = await users_col.find_one({"user_id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if _has_privileged_usage_access(user):
        return True

    tier = user.get("subscription_tier", "free").lower()
    limits = get_tier_limits(tier)

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    this_month_str = now.strftime("%Y-%m")

    update_query = {}

    if feature == "daily_research_queries":
        last_date = user.get("last_research_date")
        current_count = user.get("daily_research_count", 0)

        if last_date != today_str:
            current_count = 0

        limit = limits.get("daily_research_queries")
        if limit is not None and current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Daily research limit reached for {tier} tier. Please upgrade for more access."
            )

        if last_date != today_str:
            update_query = {
                "$set": {"last_research_date": today_str, "daily_research_count": 1},
                "$inc": {"total_research_count": 1}
            }
        else:
            update_query = {
                "$set": {"last_research_date": today_str},
                "$inc": {"daily_research_count": 1, "total_research_count": 1}
            }

    elif feature == "monthly_templates":
        last_month = user.get("last_template_month")
        current_count = user.get("monthly_template_count", 0)

        if last_month != this_month_str:
            current_count = 0

        limit = limits.get("monthly_templates")
        if limit is not None and current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Monthly template limit reached for {tier} tier. Please upgrade to unlock more drafts."
            )

        if last_month != this_month_str:
            update_query = {
                "$set": {"last_template_month": this_month_str, "monthly_template_count": 1},
                "$inc": {"total_template_count": 1}
            }
        else:
            update_query = {
                "$set": {"last_template_month": this_month_str},
                "$inc": {"monthly_template_count": 1, "total_template_count": 1}
            }

    elif feature == "max_compliance_records":
        # For this, we check current count in the specific collection
        diary_col = get_collection("legal_diary")
        count = await diary_col.count_documents({"user_id": user_id})

        limit = limits.get("max_compliance_records")
        if limit is not None and count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Compliance record limit reached for {tier} tier. Please upgrade to manage more clients."
            )
        # No increment here as it's a fixed capacity check
        return True

    elif feature == "can_upload_official_forms":
        if not limits.get("can_upload_official_forms", False):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Official form upload is restricted to the Popular/Pro tier (₹899/mo). Please upgrade to continue."
            )
        return True

    if update_query:
        await users_col.update_one({"user_id": user_id}, update_query)

    return True
