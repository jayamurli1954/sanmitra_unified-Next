"""Signed visitor-pass links (SEC-01).

A guest pass link carries a short HMAC token bound to the visitor ID and the pass
expiry. The public pass page only reveals the gate passcode when that token is
present and valid, so knowing a visitor ID alone (from a QR code photo, a log line
or a referrer) is no longer enough to read the passcode.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

_KEY_LABEL = b"sanmitra-visitor-pass-v1"
_TOKEN_HEX_CHARS = 32  # 128-bit tag


def _signing_key() -> bytes:
    settings = get_settings()
    dedicated = str(getattr(settings, "VISITOR_PASS_SIGNING_SECRET", "") or "").strip()
    if dedicated:
        return dedicated.encode("utf-8")
    # Derive a separate key from JWT_SECRET so pass links never share a key with tokens.
    base = str(settings.JWT_SECRET or "").encode("utf-8")
    return hmac.new(base, _KEY_LABEL, hashlib.sha256).digest()


def visitor_pass_token(visitor_id: str, expires_at: str | None) -> str:
    message = f"{visitor_id}|{expires_at or ''}".encode("utf-8")
    return hmac.new(_signing_key(), message, hashlib.sha256).hexdigest()[:_TOKEN_HEX_CHARS]


def verify_visitor_pass_token(visitor_id: str, expires_at: str | None, token: str | None) -> bool:
    if not token:
        return False
    expected = visitor_pass_token(visitor_id, expires_at)
    return hmac.compare_digest(expected, str(token).strip().lower())


def pass_is_usable(doc: dict[str, Any], *, now: datetime | None = None) -> tuple[bool, bool]:
    """Return (is_expired, passcode_may_show) for a visitor pass document."""
    now = now or datetime.now(timezone.utc)
    expires_at = doc.get("expires_at")
    is_expired = bool(expires_at) and now > datetime.fromisoformat(str(expires_at))
    closed = str(doc.get("status") or "").lower() == "rejected" or bool(doc.get("checked_out_at"))
    return is_expired, not (is_expired or closed)
