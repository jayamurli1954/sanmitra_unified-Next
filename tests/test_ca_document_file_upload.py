"""CA document file upload/download/remove — storage service + upload validation.

Files are stored as bytes in MongoDB (collection ``business_ca_document_files``)
so they survive Render's ephemeral disk. These tests cover the storage service
roundtrip with mocked collections and the router's upload guardrails.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException


# ── upload validation (router._read_ca_upload) ────────────────────────────────


class _FakeUpload:
    def __init__(self, content_type, chunks, filename="doc.pdf"):
        self.content_type = content_type
        self.filename = filename
        self._chunks = list(chunks)

    async def read(self, size=-1):
        return self._chunks.pop(0) if self._chunks else b""


@pytest.mark.asyncio
async def test_read_ca_upload_accepts_allowed_type():
    from app.modules.business.router import _read_ca_upload

    data = await _read_ca_upload(_FakeUpload("application/pdf", [b"%PDF-1.4 data"]))
    assert data == b"%PDF-1.4 data"


@pytest.mark.asyncio
async def test_read_ca_upload_rejects_disallowed_type():
    from app.modules.business.router import _read_ca_upload

    with pytest.raises(HTTPException) as exc:
        await _read_ca_upload(_FakeUpload("application/x-msdownload", [b"MZ..."]))
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_read_ca_upload_rejects_empty_file():
    from app.modules.business.router import _read_ca_upload

    with pytest.raises(HTTPException) as exc:
        await _read_ca_upload(_FakeUpload("application/pdf", []))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_read_ca_upload_rejects_oversized_file(monkeypatch):
    import app.modules.business.router as business_router

    monkeypatch.setattr(business_router, "CA_DOCUMENT_MAX_FILE_BYTES", 8)
    with pytest.raises(HTTPException) as exc:
        await _read_helper(business_router, "text/csv", [b"1234", b"5678", b"9"])
    assert exc.value.status_code == 413


async def _read_helper(business_router, content_type, chunks):
    return await business_router._read_ca_upload(_FakeUpload(content_type, chunks))


@pytest.mark.asyncio
async def test_read_ca_upload_allows_missing_content_type():
    """A client that omits Content-Type should not be blocked by the allowlist."""
    from app.modules.business.router import _read_ca_upload

    data = await _read_ca_upload(_FakeUpload("", [b"plain bytes"]))
    assert data == b"plain bytes"


# ── storage service (service.store/get/delete_ca_document_file) ───────────────


def _route_collections(*, metadata, files):
    from app.modules.business import service

    def _col(name):
        if name == service.CA_DOCUMENT_FILES_COLLECTION:
            return files
        return metadata
    return _col


@pytest.mark.asyncio
async def test_store_returns_none_when_document_missing(monkeypatch):
    from app.modules.business import service

    metadata = AsyncMock()
    metadata.find_one = AsyncMock(return_value=None)
    files = AsyncMock()
    monkeypatch.setattr(service, "get_collection", _route_collections(metadata=metadata, files=files))

    result = await service.store_ca_document_file(
        tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
        document_id="missing", file_name="x.pdf", content_type="application/pdf",
        payload=b"data", uploaded_by="u1",
    )
    assert result is None
    files.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_store_persists_bytes_and_sets_metadata(monkeypatch):
    from app.modules.business import service

    existing = {
        "document_id": "d1", "tenant_id": "t1", "app_key": "mitrabooks",
        "accounting_entity_id": "primary", "client_name": "Acme", "document_type": "invoice",
        "period": "2026-06", "status": "uploaded", "next_action": "x",
        "created_by": "u1", "created_at": service._now(), "updated_at": service._now(),
    }
    updated = {**existing, "has_file": True, "file_content_type": "application/pdf",
               "file_size": 4, "original_file_name": "x.pdf"}

    metadata = AsyncMock()
    metadata.find_one = AsyncMock(side_effect=[existing, updated])
    metadata.update_one = AsyncMock()
    files = AsyncMock()
    files.update_one = AsyncMock()
    monkeypatch.setattr(service, "get_collection", _route_collections(metadata=metadata, files=files))

    result = await service.store_ca_document_file(
        tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
        document_id="d1", file_name="x.pdf", content_type="application/pdf",
        payload=b"data", uploaded_by="u2",
    )

    assert result is not None
    assert result["has_file"] is True
    assert result["file_size"] == 4
    # file bytes go to the files collection via upsert
    files.update_one.assert_awaited_once()
    upsert_kwargs = files.update_one.call_args.kwargs
    assert upsert_kwargs.get("upsert") is True
    stored = files.update_one.call_args.args[1]["$set"]
    assert stored["data"] == b"data"
    assert stored["content_type"] == "application/pdf"
    # metadata collection is flagged has_file
    meta_set = metadata.update_one.call_args.args[1]["$set"]
    assert meta_set["has_file"] is True
    assert meta_set["original_file_name"] == "x.pdf"


@pytest.mark.asyncio
async def test_get_file_returns_none_when_no_file(monkeypatch):
    from app.modules.business import service

    metadata = AsyncMock()
    metadata.find_one = AsyncMock(return_value={"_id": "x"})  # document exists
    files = AsyncMock()
    files.find_one = AsyncMock(return_value=None)  # but no file
    monkeypatch.setattr(service, "get_collection", _route_collections(metadata=metadata, files=files))

    result = await service.get_ca_document_file(
        tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary", document_id="d1",
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_file_returns_bytes(monkeypatch):
    from app.modules.business import service

    metadata = AsyncMock()
    metadata.find_one = AsyncMock(return_value={"_id": "x"})
    files = AsyncMock()
    files.find_one = AsyncMock(return_value={
        "file_name": "bank.csv", "content_type": "text/csv", "data": b"a,b,c",
    })
    monkeypatch.setattr(service, "get_collection", _route_collections(metadata=metadata, files=files))

    result = await service.get_ca_document_file(
        tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary", document_id="d1",
    )
    assert result == {"file_name": "bank.csv", "content_type": "text/csv", "data": b"a,b,c"}


@pytest.mark.asyncio
async def test_delete_clears_file_metadata(monkeypatch):
    from app.modules.business import service

    existing = {"document_id": "d1", "tenant_id": "t1", "app_key": "mitrabooks",
                "accounting_entity_id": "primary", "status": "uploaded", "next_action": "x",
                "created_by": "u1", "created_at": service._now(), "updated_at": service._now(),
                "has_file": True}
    cleared = {**existing, "has_file": False, "file_content_type": None, "file_size": None}

    metadata = AsyncMock()
    metadata.find_one = AsyncMock(side_effect=[existing, cleared])
    metadata.update_one = AsyncMock()
    files = AsyncMock()
    files.delete_one = AsyncMock()
    monkeypatch.setattr(service, "get_collection", _route_collections(metadata=metadata, files=files))

    result = await service.delete_ca_document_file(
        tenant_id="t1", app_key="mitrabooks", accounting_entity_id="primary",
        document_id="d1", deleted_by="u2",
    )
    assert result is not None
    assert result["has_file"] is False
    files.delete_one.assert_awaited_once()
    meta_set = metadata.update_one.call_args.args[1]["$set"]
    assert meta_set["has_file"] is False
    assert meta_set["file_size"] is None
