"""
CA Access — invite a Chartered Accountant to read-only access of one tenant's books.

Invite flow:
  1. tenant_admin  POST /business/ca/invite        {email, full_name}
  2. Token stored in business_ca_invitations; invite email sent.
  3. CA clicks link → lands on ?ca_invite=TOKEN in the MitraBooks FE.
  4. CA         POST /business/ca/invite/{token}/accept  {password}
  5. core_users entry created with role=ca_viewer.
  6. tenant_admin  DELETE /business/ca/{user_id}/revoke  → is_active=False
"""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote
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
    """Create a pending invite and send the invite email. Returns the invite record."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)

    normalized_email = email.strip().lower()
    existing = await col.find_one({"tenant_id": tenant_id, "email": normalized_email, "status": "pending"})
    if existing:
        raise ValueError(f"A pending invite already exists for {normalized_email}")

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    doc = {
        "invite_id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "email": normalized_email,
        "full_name": full_name.strip(),
        "token": token,
        "status": "pending",
        "invited_by": invited_by,
        "created_at": now,
        "expires_at": now + timedelta(days=_TOKEN_TTL_DAYS),
        "accepted_at": None,
        "user_id": None,
    }
    await col.insert_one(doc)
    await _send_invite_email(email=normalized_email, full_name=full_name.strip(), token=token, tenant_id=tenant_id)
    doc.pop("_id", None)
    return doc


async def _send_invite_email(*, email: str, full_name: str, token: str, tenant_id: str) -> None:
    settings = get_settings()
    # Use MITRABOOKS_PUBLIC_URL env var when set (required on Render since the
    # frontend is hosted separately at www.mitrabooks.sanmitratech.in, not on the
    # API server). Falls back to the production frontend URL.
    # Link to login.html (not index.html) — login.html is a dedicated static file
    # that handles the CA invite flow without being intercepted by the marketing site.
    mitrabooks_base = (
        str(getattr(settings, "MITRABOOKS_PUBLIC_URL", "") or "").rstrip("/")
        or "https://www.mitrabooks.sanmitratech.in"
    )
    # Embed email and name so login.html can pre-fill without a cross-origin API call.
    accept_url = (
        f"{mitrabooks_base}/mitrabooks-erp/login.html"
        f"?ca_invite={token}"
        f"&email={quote(email, safe='')}"
        f"&name={quote(full_name, safe='')}"
    )

    subject = "You have been invited to access MitraBooks financial data"
    body = (
        f"Hello {full_name},\n\n"
        f"You have been invited as a Chartered Accountant (CA) to review the financial data"
        f" for business tenant '{tenant_id}' on MitraBooks.\n\n"
        f"Click the link below to set your password and activate read-only access:\n\n"
        f"  {accept_url}\n\n"
        f"This link is valid for {_TOKEN_TTL_DAYS} days.\n\n"
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
        _logger.warning("CA invite email not sent (SMTP not configured). Accept URL: %s", accept_url)
        return

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
    except Exception as exc:
        await log_email_delivery_attempt(
            module="ca_access", action="ca_invite", to_email=email,
            subject=subject, sent=False, error=str(exc), tenant_id=tenant_id,
        )
        _logger.warning("CA invite email delivery failed: %s", exc)


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
    if invite["expires_at"] < datetime.now(timezone.utc):
        raise ValueError("This invite link has expired. Ask the business to send a new invite.")
    return {
        "email": invite["email"],
        "full_name": invite.get("full_name", ""),
        "tenant_id": invite["tenant_id"],
    }


async def accept_ca_invite(*, token: str, password: str, full_name: str | None = None) -> dict:
    """Accept an invite: create the ca_viewer user account. Returns basic user info."""
    await _ensure_indexes()
    col = get_collection(_CA_INVITES)
    invite = await col.find_one({"token": token})
    if not invite:
        raise ValueError("Invalid or expired invite token")
    if invite["status"] == "accepted":
        raise ValueError("This invite has already been accepted")
    if invite["status"] == "revoked":
        raise ValueError("This invite has been revoked")
    if invite["expires_at"] < datetime.now(timezone.utc):
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
            {"$set": {"role": "ca_viewer", "is_active": True, "full_name": resolved_name, "updated_at": now}},
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
            "subscription_tier": "free",
            "subscription_status": "active",
            "accepted_terms_at": None,
            "query_usage_count": 0,
            "created_at": now,
            "updated_at": now,
        })

    await col.update_one(
        {"_id": invite["_id"]},
        {"$set": {"status": "accepted", "accepted_at": now, "user_id": user_id}},
    )
    return {"user_id": user_id, "email": email, "full_name": resolved_name, "role": "ca_viewer"}


async def revoke_ca_access(*, tenant_id: str, user_id: str) -> None:
    """Deactivate a ca_viewer for this tenant."""
    users = get_collection(_USERS)
    result = await users.update_one(
        {"user_id": user_id, "tenant_id": tenant_id, "role": "ca_viewer"},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
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
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise ValueError(f"CA user '{user_id}' not found in this tenant")
    col = get_collection(_CA_INVITES)
    await col.update_one(
        {"tenant_id": tenant_id, "user_id": user_id},
        {"$set": {"status": "accepted"}},
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
