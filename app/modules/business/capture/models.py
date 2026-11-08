"""CaptureItem model helpers, collection name and status machine."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

COLLECTION = "business_capture_items"

# Status machine:
#   captured -> extracted -> validated -> (drafted | needs_review | duplicate)
#                                                           -> rejected
# "drafted" = high-confidence + all validations passed (one-click-approve ready).
# "needs_review" = low confidence or a failed deterministic check.
STATUS_CAPTURED = "captured"
STATUS_EXTRACTED = "extracted"
STATUS_DRAFTED = "drafted"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_NEEDS_CLIENT = "needs_client"  # client/entity could not be bound — a human must assign
STATUS_DUPLICATE = "duplicate"
STATUS_REJECTED = "rejected"

OPEN_STATUSES = {STATUS_DRAFTED, STATUS_NEEDS_REVIEW, STATUS_NEEDS_CLIENT}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


def content_fingerprint(raw: bytes, *, source_ref: str | None = None) -> str:
    """Idempotent dedupe key: hash of the document bytes plus an optional
    source reference (filename / message id)."""
    h = hashlib.sha256()
    h.update(raw)
    if source_ref:
        h.update(b"\x00")
        h.update(source_ref.encode("utf-8", "ignore"))
    return h.hexdigest()


def serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out
