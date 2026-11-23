"""Complimentary (trial) plans granted by the platform owner.

The platform owner enters someone's email, picks a product, a tier and a
number of days. If no account exists for that email, one is created (its own
tenant, a tenant_admin user, a temporary password that must be changed on
first login). The user's plan is then set with an expiry date; after that date
``effective_subscription_tier`` treats them as ``free`` automatically.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.billing.usage import effective_subscription_tier
from app.core.modules.registry import derive_enabled_modules, normalize_organization_type
from app.core.onboarding.service import (
    _allocate_tenant_id,
    _resolve_app_display_name,
    _send_onboarding_email,
)
from app.core.tenants.service import ensure_tenant_exists
from app.core.users.service import create_user
from app.db.mongo import get_collection

USERS_COLLECTION = "core_users"
BILLING_COLLECTION = "core_billing_transactions"

GRANTABLE_APP_KEYS = ("legalmitra", "mitrabooks", "mandirmitra", "gruhamitra")
GRANTABLE_TIERS = ("basic", "growth", "pro")
MIN_DAYS = 1
MAX_DAYS = 366

# Where a new user signs in, per product (used in the welcome email).
APP_LOGIN_URLS = {
    "legalmitra": "https://legalmitra.sanmitratech.in/legalmitra/login.html",
}


def _generate_policy_password(length: int = 14) -> str:
    """Random password that always satisfies the platform password policy."""
    specials = "@#$%&*!"
    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(specials),
    ]
    alphabet = string.ascii_letters + string.digits + specials
    rest = [secrets.choice(alphabet) for _ in range(max(length, 10) - len(required))]
    chars = required + rest
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def _build_welcome_email(
    *,
    app_key: str,
    full_name: str,
    email: str,
    tier: str,
    days: int,
    expires_at: datetime,
    temporary_password: str | None,
) -> tuple[str, str]:
    app_name = _resolve_app_display_name(app_key)
    login_url = APP_LOGIN_URLS.get(app_key)
    subject = f"{app_name}: your complimentary {days}-day access"
    lines = [
        f"Dear {full_name or 'Sir/Madam'},",
        "",
        f"You have been given complimentary access to {app_name} ({tier.title()} plan, all features) "
        f"for {days} days, valid until {expires_at.strftime('%d %b %Y')}.",
        "",
    ]
    if temporary_password:
        lines += [
            f"Login ID: {email}",
            f"Temporary password: {temporary_password}",
            "",
            "You will be asked to set your own password when you first log in.",
        ]
    else:
        lines.append(f"Sign in with your existing account ({email}).")
    if login_url:
        lines += ["", f"Sign in here: {login_url}"]
    lines += ["", "Regards,", "SanMitra Team"]
    return subject, "\n".join(lines)


def _compact_grant(user: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    tier = str(user.get("subscription_tier") or "free").lower()
    effective = effective_subscription_tier(user, now=now)
    return {
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "tenant_id": user.get("tenant_id"),
        "app_key": user.get("billing_app_key") or user.get("app_key"),
        "tier": tier,
        "effective_tier": effective,
        "active": effective != "free",
        "subscription_started_at": _iso(user.get("subscription_started_at")),
        "subscription_expires_at": _iso(user.get("subscription_expires_at")),
        "granted_by": user.get("complimentary_granted_by"),
        "note": user.get("complimentary_note"),
    }


async def grant_complimentary_plan(
    *,
    email: str,
    full_name: str | None,
    organization_name: str | None,
    app_key: str,
    tier: str,
    days: int,
    note: str | None,
    granted_by: str,
    send_email: bool = True,
) -> dict[str, Any]:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("A valid email is required")
    app_key = str(app_key or "").strip().lower()
    if app_key not in GRANTABLE_APP_KEYS:
        raise ValueError(f"Unknown product: {app_key}")
    tier = str(tier or "").strip().lower()
    if tier not in GRANTABLE_TIERS:
        raise ValueError(f"Plan must be one of: {', '.join(GRANTABLE_TIERS)}")
    days = int(days)
    if days < MIN_DAYS or days > MAX_DAYS:
        raise ValueError(f"Days must be between {MIN_DAYS} and {MAX_DAYS}")

    users = get_collection(USERS_COLLECTION)
    user = await users.find_one({"email": normalized_email})
    display_name = str(full_name or "").strip()
    temporary_password: str | None = None
    account_created = False

    if user:
        existing_app = str(user.get("app_key") or "").strip().lower()
        if existing_app and existing_app != app_key:
            raise ValueError(
                f"{normalized_email} already has a {_resolve_app_display_name(existing_app)} account; "
                f"it cannot be given a {_resolve_app_display_name(app_key)} plan"
            )
        display_name = display_name or str(user.get("full_name") or "")
    else:
        if not display_name:
            raise ValueError("Full name is required to create a new account")
        tenant_name = str(organization_name or "").strip() or display_name
        organization_type = normalize_organization_type(None, app_key=app_key)
        tenant_id = await _allocate_tenant_id(tenant_name)
        await ensure_tenant_exists(
            tenant_id,
            display_name=tenant_name,
            organization_type=organization_type,
            enabled_modules=derive_enabled_modules(organization_type=organization_type),
            app_keys=[app_key],
            created_by=granted_by,
        )
        temporary_password = _generate_policy_password()
        user = await create_user(
            email=normalized_email,
            password=temporary_password,
            full_name=display_name,
            tenant_id=tenant_id,
            role="tenant_admin",
            app_key=app_key,
        )
        account_created = True

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=days)
    patch: dict[str, Any] = {
        "subscription_tier": tier,
        "subscription_status": "active",
        "billing_app_key": app_key,
        "billing_plan": tier,
        "billing_cycle": "complimentary",
        "subscription_started_at": now,
        "subscription_expires_at": expires_at,
        "complimentary_plan": True,
        "complimentary_granted_by": granted_by,
        "complimentary_note": (note or "").strip() or None,
        "updated_at": now,
    }
    if account_created:
        patch["must_change_password"] = True
    await users.update_one({"user_id": user["user_id"]}, {"$set": patch})

    await get_collection(BILLING_COLLECTION).insert_one(
        {
            "transaction_id": str(uuid4()),
            "email": normalized_email,
            "customer_name": display_name,
            "amount": 0,
            "amount_paise": 0,
            "currency": "INR",
            "app_key": app_key,
            "plan": tier,
            "tier": tier,
            "billing_cycle": "complimentary",
            "subscription_status": "active",
            "subscription_started_at": now,
            "subscription_expires_at": expires_at,
            "tenant_id": user.get("tenant_id"),
            "complimentary": True,
            "granted_by": granted_by,
            "note": patch["complimentary_note"],
            "event": "complimentary.granted",
            "created_at": now,
        }
    )

    email_sent, email_error = False, None
    if send_email:
        subject, body = _build_welcome_email(
            app_key=app_key,
            full_name=display_name,
            email=normalized_email,
            tier=tier,
            days=days,
            expires_at=expires_at,
            temporary_password=temporary_password,
        )
        email_sent, email_error = await _send_onboarding_email(
            to_email=normalized_email,
            subject=subject,
            body=body,
            tenant_id=user.get("tenant_id"),
            request_id=f"complimentary:{user['user_id']}",
            app_key=app_key,
        )

    return {
        "email": normalized_email,
        "full_name": display_name,
        "user_id": user["user_id"],
        "tenant_id": user.get("tenant_id"),
        "app_key": app_key,
        "tier": tier,
        "days": days,
        "subscription_expires_at": expires_at.isoformat(),
        "account_created": account_created,
        # Shown once so the owner can pass it on if the email did not go out.
        "temporary_password": temporary_password,
        "email_sent": email_sent,
        "email_error": email_error,
    }


async def revoke_complimentary_plan(*, email: str, revoked_by: str) -> dict[str, Any]:
    normalized_email = str(email or "").strip().lower()
    users = get_collection(USERS_COLLECTION)
    user = await users.find_one({"email": normalized_email})
    if not user:
        raise KeyError("User not found")
    if not user.get("complimentary_plan"):
        raise ValueError("This user does not have a complimentary plan")
    now = datetime.now(timezone.utc)
    await users.update_one(
        {"user_id": user["user_id"]},
        {
            "$set": {
                "subscription_tier": "free",
                "subscription_expires_at": now,
                "complimentary_plan": False,
                "complimentary_revoked_by": revoked_by,
                "complimentary_revoked_at": now,
                "updated_at": now,
            }
        },
    )
    return {"email": normalized_email, "tier": "free", "revoked": True}


async def list_complimentary_plans(*, limit: int = 200) -> list[dict[str, Any]]:
    users = get_collection(USERS_COLLECTION)
    safe_limit = max(1, min(int(limit or 200), 500))
    cursor = users.find({"complimentary_plan": True}).sort("subscription_expires_at", 1).limit(safe_limit)
    docs = await cursor.to_list(length=safe_limit)
    now = datetime.now(timezone.utc)
    return [_compact_grant(doc, now=now) for doc in docs]
