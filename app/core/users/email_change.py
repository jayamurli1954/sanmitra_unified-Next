"""Mailbox-confirmed email changes (Audit V1, SEC-02 follow-up).

Changing the login email used to take effect immediately, so a stolen session could
redirect every future password-reset email. Now a change needs the current password,
is held as ``pending_email`` and only applies when the link mailed to the *new*
address is confirmed. The *old* address is told about the request. Confirming signs
the user out of other devices by revoking their refresh tokens.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse
from pymongo.errors import DuplicateKeyError

from app.core.auth.security import verify_password
from app.core.users.service import USERS_COLLECTION
from app.db.mongo import get_collection

EMAIL_CHANGE_ACTION = "email_change"
EMAIL_CHANGE_TTL_MINUTES = 30
REFRESH_TOKENS_COLLECTION = "core_auth_refresh_tokens"
CONFIRM_PATH = "/api/v1/users/email-change/confirm"


def _public_api_base(request: Request) -> str:
    proto = str(request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
    return f"{proto}://{host}"


async def request_email_change(
    *,
    request: Request,
    existing: dict[str, Any],
    new_email: str,
    current_password: str,
) -> dict[str, Any]:
    """Validate, store ``pending_email`` and send the confirmation link. Returns the user patch."""
    from app.core.auth import router as auth_router  # late import: auth router is heavy

    if str(existing.get("auth_provider") or "password") != "password":
        raise HTTPException(status_code=400, detail="Email is managed by your sign-in provider and cannot be changed here")
    if not current_password:
        raise HTTPException(status_code=400, detail="Current password is required to change your email")
    hashed = str(existing.get("hashed_password") or "")
    if not hashed or not verify_password(current_password, hashed):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    users = get_collection(USERS_COLLECTION)
    user_id = str(existing.get("user_id") or "")
    taken = await users.find_one({"email": new_email, "user_id": {"$ne": user_id}}, {"user_id": 1})
    if taken is not None:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    old_email = str(existing.get("email") or "")
    token = await auth_router._create_email_action_token(
        action=EMAIL_CHANGE_ACTION,
        email=new_email,
        ttl_minutes=EMAIL_CHANGE_TTL_MINUTES,
        meta={"user_id": user_id, "old_email": old_email, "new_email": new_email},
    )
    link = f"{_public_api_base(request)}{CONFIRM_PATH}?token={token}"
    sent, error = await auth_router._send_auth_email(
        to_email=new_email,
        subject="Confirm your new SanMitra sign-in email",
        body=(
            f"A request was made to change the sign-in email for your SanMitra account "
            f"from {old_email} to {new_email}.\n\n"
            f"Open this link within {EMAIL_CHANGE_TTL_MINUTES} minutes to confirm:\n{link}\n\n"
            "If you did not ask for this, ignore this email and your account stays unchanged."
        ),
        action=EMAIL_CHANGE_ACTION,
        meta={"user_id": user_id},
    )
    if not sent:
        raise HTTPException(status_code=503, detail=f"Could not send the confirmation email: {error}")
    if old_email:
        await auth_router._send_auth_email(
            to_email=old_email,
            subject="Your SanMitra sign-in email change was requested",
            body=(
                f"Someone asked to change the sign-in email of your SanMitra account to {new_email}. "
                "Nothing changes until that address confirms. If this was not you, change your "
                "password now and contact your administrator."
            ),
            action=f"{EMAIL_CHANGE_ACTION}_notice",
            meta={"user_id": user_id},
        )
    return {"pending_email": new_email, "pending_email_requested_at": datetime.now(timezone.utc)}


def _page(title: str, message: str, *, token: str | None = None) -> HTMLResponse:
    form = ""
    if token:
        form = (
            f'<form method="post" action="{CONFIRM_PATH}">'
            f'<input type="hidden" name="token" value="{html.escape(token, quote=True)}">'
            '<button type="submit">Confirm new email</button></form>'
        )
    body = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title></head><body>"
        f"<h1>{html.escape(title)}</h1><p>{html.escape(message)}</p>{form}</body></html>"
    )
    response = HTMLResponse(body)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def confirm_page(token: str) -> HTMLResponse:
    """GET shows a button; link scanners that prefetch the URL do not confirm the change."""
    from app.core.auth import router as auth_router

    try:
        await auth_router._load_valid_email_action(action=EMAIL_CHANGE_ACTION, token=token)
    except HTTPException as exc:
        return _page("Link not valid", str(exc.detail))
    return _page("Confirm your new email", "Press the button to finish changing your sign-in email.", token=token)


async def confirm_email_change(token: str) -> HTMLResponse:
    from app.core.auth import router as auth_router

    try:
        action = await auth_router._load_valid_email_action(action=EMAIL_CHANGE_ACTION, token=token)
    except HTTPException as exc:
        return _page("Link not valid", str(exc.detail))
    meta = action.get("meta") or {}
    user_id = str(meta.get("user_id") or "")
    new_email = str(meta.get("new_email") or "").strip().lower()
    users = get_collection(USERS_COLLECTION)
    user = await users.find_one({"user_id": user_id}, {"pending_email": 1})
    if not user or str(user.get("pending_email") or "").lower() != new_email:
        await auth_router._consume_email_action(action)
        return _page("Link not valid", "This email change was cancelled or replaced by a newer request.")
    try:
        await users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email": new_email,
                    "provider_subject": f"password:{new_email}",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$unset": {"pending_email": "", "pending_email_requested_at": ""},
            },
        )
    except DuplicateKeyError:
        return _page("Email already in use", "Another account now uses this email. Nothing was changed.")
    await auth_router._consume_email_action(action)
    await get_collection(REFRESH_TOKENS_COLLECTION).update_many(
        {"user_id": user_id, "revoked": False},
        {"$set": {"revoked": True, "revoked_reason": "email_changed", "revoked_at": datetime.now(timezone.utc)}},
    )
    return _page("Email changed", f"Your sign-in email is now {new_email}. Please sign in again on your devices.")
