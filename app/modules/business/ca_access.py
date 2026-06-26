"""
CA Access — invite a Chartered Accountant to read-only access of one tenant's books.

Invite flow:
  1. tenant_admin  POST /business/ca/invite        {email, full_name}
  2. core_users entry is created or refreshed in an inactive invite-pending state.
  3. A single-use invite link email is sent with token expiry.
  4. CA accepts the invite by setting a password on first use.
  5. tenant_admin  DELETE /business/ca/{user_id}/revoke  → is_active=False
"""
from __future__ import annotations

import asyncio
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import uuid4

from app.config import get_settings
from app.core.auth.security import hash_password
from app.core.email_delivery.service import log_email_delivery_attempt
from app.db.mongo import get_collection

_logger = logging.getLogger(__name__)

_CA_INVITES = "business_ca_invitations"


def _as_utc(dt: datetime) -> datetime:
    """Return dt as a timezone-aware UTC datetime. MongoDB returns naive UTC datetimes."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
_USERS = "core_users"
_TOKEN_TTL_DAYS = 7


async def _ensure_indexes() -> None:
    col = get_collection(_CA_INVITES)
    await col.create_index("token", unique=True, sparse=True)
    await col.create_index([("tenant_id", 1), ("status", 1)])
    await col.create_index("email")


async def invite_ca(
    *,
    tenant_id: str,
    app_key: str,
    email: str,
    full_name: str,
    invited_by: str,
) -> dict:
    """Provision or refresh a CA viewer invite and send a token-based acceptance link."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    users = get_collection(_USERS)

    normalized_email = email.strip().lower()
    existing = await col.find_one({"tenant_id": tenant_id, "email": normalized_email})
    now = datetime.now(timezone.utc)
    resolved_name = full_name.strip()

    existing_user = await users.find_one({"email": normalized_email})
    if existing_user and str(existing_user.get("tenant_id") or "") != tenant_id:
        raise ValueError("A user with this email already exists in a different tenant. Contact support.")

    if existing_user:
        user_id = str(existing_user.get("user_id") or uuid4())
        await users.update_one(
            {"_id": existing_user["_id"]},
            {
                "$set": {
                    "user_id": user_id,
                    "email": normalized_email,
                    "full_name": resolved_name,
                    "tenant_id": tenant_id,
                    "app_key": app_key,
                    "role": existing_user.get("role") or "ca_viewer",
                    "auth_provider": existing_user.get("auth_provider"),
                    "provider_subject": existing_user.get("provider_subject"),
                    "is_active": bool(existing_user.get("is_active", False)),
                    "must_change_password": False,
                    "invite_pending": True,
                    "invited_role": "ca_viewer",
                    "subscription_tier": existing_user.get("subscription_tier", "free"),
                    "subscription_status": existing_user.get("subscription_status", "active"),
                    "accepted_terms_at": existing_user.get("accepted_terms_at"),
                    "query_usage_count": existing_user.get("query_usage_count", 0),
                    "updated_at": now,
                }
            },
        )
    else:
        user_id = str(uuid4())
        await users.insert_one({
            "user_id": user_id,
            "email": normalized_email,
            "full_name": resolved_name,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "role": "ca_viewer",
            "auth_provider": "password_setup_pending",
            "provider_subject": f"invite:{normalized_email}",
            "is_active": False,
            "must_change_password": False,
            "invite_pending": True,
            "invited_role": "ca_viewer",
            "subscription_tier": "free",
            "subscription_status": "active",
            "accepted_terms_at": None,
            "query_usage_count": 0,
            "created_at": now,
            "updated_at": now,
        })

    if existing:
        token = str(existing.get("token") or secrets.token_urlsafe(32))
        expires_at = _as_utc(existing.get("expires_at"))
        if not expires_at or expires_at < now:
            expires_at = now + timedelta(days=_TOKEN_TTL_DAYS)
        update_doc = {
            "full_name": resolved_name,
            "token": token,
            "expires_at": expires_at,
            "status": "invited",
            "resent_at": now,
            "resent_by": invited_by,
            "user_id": user_id,
        }
        await col.update_one({"_id": existing["_id"]}, {"$set": update_doc})
        delivery = await _send_invite_email(
            email=normalized_email,
            full_name=resolved_name,
            tenant_id=tenant_id,
            token=token,
            expires_at=expires_at,
        )
        existing.update(update_doc)
        existing["email_delivery"] = delivery
        existing["resent"] = True
        existing.pop("_id", None)
        return existing

    token = secrets.token_urlsafe(32)
    doc = {
        "invite_id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "email": normalized_email,
        "full_name": resolved_name,
        "token": token,
        "status": "invited",
        "invited_by": invited_by,
        "created_at": now,
        "expires_at": now + timedelta(days=_TOKEN_TTL_DAYS),
        "user_id": user_id,
    }
    await col.insert_one(doc)
    delivery = await _send_invite_email(
        email=normalized_email,
        full_name=resolved_name,
        tenant_id=tenant_id,
        token=token,
        expires_at=doc["expires_at"],
    )
    doc["email_delivery"] = delivery
    doc["resent"] = False
    doc.pop("_id", None)
    return doc


async def _send_invite_email(*, email: str, full_name: str, tenant_id: str, token: str, expires_at: datetime) -> dict:
    settings = get_settings()
    mitrabooks_base = (
        str(getattr(settings, "MITRABOOKS_PUBLIC_URL", "") or "").rstrip("/")
        or "https://www.mitrabooks.sanmitratech.in"
    )
    invite_accept_url = f"{mitrabooks_base}/mitrabooks-erp/ca-invite-accept.html?token={token}"
    invite_preview_url = f"{mitrabooks_base}/api/v1/business/ca/invite/{token}/preview"
    expiry_text = _as_utc(expires_at).strftime("%Y-%m-%d %H:%M UTC")

    subject = "You have been invited to access MitraBooks financial data"
    body = (
        f"Hello {full_name},\n\n"
        f"You have been invited as a Chartered Accountant (CA) to review the financial data"
        f" for business tenant '{tenant_id}' on MitraBooks.\n\n"
        f"Accept the invite and set your password using the secure invite link below:\n\n"
        f"  {invite_accept_url}\n\n"
        f"If the invite page is not yet available in your environment, your administrator can"
        f" use this preview/API link to confirm the token details before acceptance:\n"
        f"  {invite_preview_url}\n\n"
        f"Email for acceptance: {email}\n"
        f"Invite expires at: {expiry_text}\n"
        f"This link is single-use and will stop working after acceptance, expiry, or revoke.\n\n"
        f"You will have read-only access to:\n"
        f"  - Financial Statements (Trial Balance, P&L, Balance Sheet, General Ledger)\n"
        f"  - GST Returns (GSTR-1, GSTR-3B, GSTR-2B Reconciliation)\n"
        f"  - TDS/TCS Register\n"
        f"  - Bank Reconciliation\n\n"
        f"-- MitraBooks by SanMitra Tech"
    )

    if not settings.SMTP_HOST:
        await log_email_delivery_attempt(
            module="ca_access", action="ca_invite", to_email=email,
            subject=subject, sent=False, error="SMTP not configured", tenant_id=tenant_id,
        )
        _logger.warning("CA invite email not sent (SMTP not configured)")
        return {"sent": False, "error": "SMTP not configured"}

    from_header = settings.SMTP_FROM_EMAIL
    if settings.SMTP_FROM_NAME:
        from_header = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_header
    msg["To"] = email
    msg.set_content(body)

    def _send() -> None:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
                if settings.SMTP_USERNAME:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
            return
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(msg)

    try:
        await asyncio.to_thread(_send)
        await log_email_delivery_attempt(
            module="ca_access", action="ca_invite", to_email=email,
            subject=subject, sent=True, tenant_id=tenant_id,
        )
        return {"sent": True, "error": None}
    except Exception as exc:
        error = str(exc)
        await log_email_delivery_attempt(
            module="ca_access", action="ca_invite", to_email=email,
            subject=subject, sent=False, error=error, tenant_id=tenant_id,
        )
        _logger.warning("CA invite email delivery failed: %s", exc)
        return {"sent": False, "error": error}


async def preview_ca_invite(*, token: str) -> dict:
    """Return public invite details (email, name) without consuming the token."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    invite = await col.find_one({"token": token})
    if not invite:
        raise ValueError("Invalid or expired invite token")
    if invite["status"] == "accepted":
        raise ValueError("This invite has already been accepted")
    if invite["status"] == "revoked":
        raise ValueError("This invite has been revoked")
    if _as_utc(invite.get("expires_at")) < datetime.now(timezone.utc):
        raise ValueError("This invite link has expired. Ask the business to send a new invite.")
    return {
        "email": invite["email"],
        "full_name": invite.get("full_name", ""),
        "tenant_id": invite["tenant_id"],
    }


async def accept_ca_invite(*, token: str, password: str, full_name: str | None = None) -> dict:
    """Accept a token-based invite and activate CA access by setting the first password."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    invite = await col.find_one({"token": token})
    if not invite:
        raise ValueError("Invalid or expired invite token")
    if invite["status"] == "accepted":
        raise ValueError("This invite has already been accepted")
    if invite["status"] == "revoked":
        raise ValueError("This invite has been revoked")
    if _as_utc(invite.get("expires_at")) < datetime.now(timezone.utc):
        raise ValueError("This invite link has expired. Ask the business to send a new invite.")

    resolved_name = (full_name or "").strip() or invite["full_name"]
    email = invite["email"]
    tenant_id = invite["tenant_id"]
    app_key = invite["app_key"]
    now = datetime.now(timezone.utc)

    users = get_collection(_USERS)
    existing = await users.find_one({"email": email})
    if existing:
        if str(existing.get("tenant_id") or "") != tenant_id:
            raise ValueError("A user with this email already exists in a different tenant. Contact support.")
        user_id = str(existing.get("user_id") or uuid4())
        await users.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "role": "ca_viewer",
                    "is_active": True,
                    "full_name": resolved_name,
                    "hashed_password": hash_password(password),
                    "auth_provider": "password",
                    "provider_subject": f"password:{email}",
                    "must_change_password": False,
                    "invite_pending": False,
                    "invited_role": None,
                    "updated_at": now,
                }
            },
        )
    else:
        user_id = str(uuid4())
        await users.insert_one({
            "user_id": user_id,
            "email": email,
            "full_name": resolved_name,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "role": "ca_viewer",
            "hashed_password": hash_password(password),
            "auth_provider": "password",
            "provider_subject": f"password:{email}",
            "is_active": True,
            "must_change_password": False,
            "invite_pending": False,
            "invited_role": None,
            "subscription_tier": "free",
            "subscription_status": "active",
            "accepted_terms_at": None,
            "query_usage_count": 0,
            "created_at": now,
            "updated_at": now,
        })

    await col.update_one(
        {"_id": invite["_id"]},
        {"$set": {"status": "accepted", "accepted_at": now, "user_id": user_id, "token_consumed_at": now}},
    )
    return {"user_id": user_id, "email": email, "full_name": resolved_name, "role": "ca_viewer"}


async def revoke_ca_access(*, tenant_id: str, user_id: str) -> None:
    """Deactivate a ca_viewer for this tenant."""
    users = get_collection(_USERS)
    result = await users.update_one(
        {"user_id": user_id, "tenant_id": tenant_id, "role": "ca_viewer"},
        {"$set": {"is_active": False, "invite_pending": False, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise ValueError(f"CA user '{user_id}' not found in this tenant")
    col = get_collection(_CA_INVITES)
    await col.update_one(
        {"tenant_id": tenant_id, "user_id": user_id},
        {"$set": {"status": "revoked"}},
    )


async def reinstate_ca_access(*, tenant_id: str, user_id: str) -> None:
    """Re-enable a previously revoked ca_viewer."""
    users = get_collection(_USERS)
    result = await users.update_one(
        {"user_id": user_id, "tenant_id": tenant_id, "role": "ca_viewer"},
        {"$set": {"is_active": True, "invite_pending": False, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise ValueError(f"CA user '{user_id}' not found in this tenant")
    col = get_collection(_CA_INVITES)
    await col.update_one(
        {"tenant_id": tenant_id, "user_id": user_id},
        {"$set": {"status": "invited"}},
    )


async def delete_ca_record(*, tenant_id: str, invite_id: str) -> None:
    """Permanently delete a CA invite record (any status).
    If the invite had an associated user account, deactivates it too."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    invite = await col.find_one({"invite_id": invite_id, "tenant_id": tenant_id})
    if not invite:
        raise ValueError("CA record not found")
    user_id = invite.get("user_id")
    if user_id:
        users = get_collection(_USERS)
        await users.update_one(
            {"user_id": user_id, "tenant_id": tenant_id},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
        )
    await col.delete_one({"invite_id": invite_id, "tenant_id": tenant_id})


async def list_ca_access(*, tenant_id: str) -> dict:
    """List all CA invites (pending + accepted + revoked) for this tenant."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    docs = await col.find({"tenant_id": tenant_id}).sort("created_at", -1).to_list(length=200)
    records = [
        {
            "invite_id": str(d.get("invite_id") or ""),
            "email": str(d.get("email") or ""),
            "full_name": str(d.get("full_name") or ""),
            "status": str(d.get("status") or "pending"),
            "invited_by": str(d.get("invited_by") or ""),
            "invited_at": d.get("created_at"),
            "expires_at": d.get("expires_at"),
            "accepted_at": d.get("accepted_at"),
            "user_id": d.get("user_id"),
        }
        for d in docs
    ]
    return {"ca_users": records, "total": len(records)}
