from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.db.mongo import get_collection

LEGAL_CHAT_HISTORY_COLLECTION = "legal_chat_history"
LEGAL_UPLOAD_RECORDS_COLLECTION = "legal_upload_records"
OFFICIAL_FORM_BANK_COLLECTION = "official_form_bank"

_REVIEW_UPLOAD_DIR = Path(__file__).resolve().parent / "data" / "uploads" / "review_documents"


def retention_expiry(days: int, now: datetime | None = None) -> datetime:
    base = now or datetime.now(timezone.utc)
    return base + timedelta(days=max(1, int(days)))


async def ensure_legal_retention_indexes() -> None:
    chat = get_collection(LEGAL_CHAT_HISTORY_COLLECTION)
    uploads = get_collection(LEGAL_UPLOAD_RECORDS_COLLECTION)
    official_forms = get_collection(OFFICIAL_FORM_BANK_COLLECTION)

    await chat.create_index([("tenant_id", 1), ("app_key", 1), ("user_id", 1), ("created_at", -1)])
    await chat.create_index("expires_at", expireAfterSeconds=0)

    await uploads.create_index([("tenant_id", 1), ("app_key", 1), ("user_id", 1), ("created_at", -1)])
    await uploads.create_index("expires_at", expireAfterSeconds=0)

    await official_forms.create_index([("tenant_id", 1), ("app_key", 1), ("created_at", -1)])
    await official_forms.create_index("expires_at", expireAfterSeconds=0)


async def save_legal_chat_history(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    query: str,
    query_type: str,
    response: dict[str, Any],
    retention_days: int,
) -> str:
    now = datetime.now(timezone.utc)
    record_id = str(uuid4())
    doc = {
        "record_id": record_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "user_id": user_id,
        "query": query,
        "query_type": query_type,
        "response": response.get("response") or response.get("answer") or "",
        "provider": response.get("provider"),
        "strategy": response.get("strategy"),
        "citations": response.get("citations") or [],
        "retention_days": int(retention_days),
        "created_at": now,
        "expires_at": retention_expiry(retention_days, now),
    }
    await get_collection(LEGAL_CHAT_HISTORY_COLLECTION).insert_one(doc)
    return record_id


async def save_review_upload_record(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    file_name: str,
    content_type: str | None,
    payload: bytes,
    retention_days: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    upload_id = str(uuid4())
    suffix = Path(file_name or "uploaded-document").suffix[:12] or ".bin"
    _REVIEW_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_file_path = _REVIEW_UPLOAD_DIR / f"{upload_id}{suffix}"
    stored_file_path.write_bytes(payload)

    doc = {
        "upload_id": upload_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "user_id": user_id,
        "source_filename": file_name or "uploaded-document",
        "content_type": content_type or "",
        "file_size_bytes": len(payload),
        "file_sha256": sha256(payload).hexdigest(),
        "stored_file_path": str(stored_file_path),
        "retention_days": int(retention_days),
        "created_at": now,
        "expires_at": retention_expiry(retention_days, now),
    }
    await get_collection(LEGAL_UPLOAD_RECORDS_COLLECTION).insert_one(doc)
    return doc


async def list_legal_chat_history(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    cursor = (
        get_collection(LEGAL_CHAT_HISTORY_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "user_id": user_id, "expires_at": {"$gt": now}})
        .sort("created_at", -1)
        .limit(max(1, min(limit, 100)))
    )
    rows = await cursor.to_list(length=max(1, min(limit, 100)))
    for row in rows:
        row.pop("_id", None)
    return rows


async def list_legal_upload_records(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    query = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "user_id": user_id,
        "expires_at": {"$gt": now},
    }
    cursor = get_collection(LEGAL_UPLOAD_RECORDS_COLLECTION).find(query).sort("created_at", -1).limit(max(1, min(limit, 100)))
    rows = await cursor.to_list(length=max(1, min(limit, 100)))
    for row in rows:
        row.pop("_id", None)
        row.pop("stored_file_path", None)
    return rows


async def cleanup_expired_legal_retention_records(now: datetime | None = None) -> dict[str, int]:
    cutoff = now or datetime.now(timezone.utc)
    stats = {"chat_history_deleted": 0, "upload_records_deleted": 0, "official_form_records_deleted": 0, "files_deleted": 0}

    chat_result = await get_collection(LEGAL_CHAT_HISTORY_COLLECTION).delete_many({"expires_at": {"$lte": cutoff}})
    stats["chat_history_deleted"] = int(getattr(chat_result, "deleted_count", 0) or 0)

    uploads_col = get_collection(LEGAL_UPLOAD_RECORDS_COLLECTION)
    expired_uploads = await uploads_col.find({"expires_at": {"$lte": cutoff}}).to_list(length=1000)
    for doc in expired_uploads:
        if _delete_stored_file(doc.get("stored_file_path")):
            stats["files_deleted"] += 1
    uploads_result = await uploads_col.delete_many({"expires_at": {"$lte": cutoff}})
    stats["upload_records_deleted"] = int(getattr(uploads_result, "deleted_count", 0) or 0)

    official_col = get_collection(OFFICIAL_FORM_BANK_COLLECTION)
    expired_forms = await official_col.find({"expires_at": {"$lte": cutoff}}).to_list(length=1000)
    for doc in expired_forms:
        if _delete_stored_file(doc.get("stored_file_path")):
            stats["files_deleted"] += 1
    official_result = await official_col.delete_many({"expires_at": {"$lte": cutoff}})
    stats["official_form_records_deleted"] = int(getattr(official_result, "deleted_count", 0) or 0)

    return stats


def _delete_stored_file(path_value: Any) -> bool:
    path_text = str(path_value or "").strip()
    if not path_text:
        return False
    try:
        path = Path(path_text).resolve()
        allowed_roots = [
            _REVIEW_UPLOAD_DIR.resolve(),
            (Path(__file__).resolve().parent / "data" / "official_forms" / "uploaded").resolve(),
        ]
        if not any(path.is_relative_to(root) for root in allowed_roots):
            return False
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        return False
    return False
