from io import BytesIO

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.modules.housing_compat.router import _read_housing_upload_with_size_limit


@pytest.mark.asyncio
async def test_housing_journal_attachment_rejects_oversized_payload() -> None:
    file = UploadFile(filename="attachment.pdf", file=BytesIO(b"a" * (1024 * 1024 + 1)))
    with pytest.raises(HTTPException) as exc:
        await _read_housing_upload_with_size_limit(
            file=file,
            limit_bytes=1024 * 1024,
            feature_name="Journal attachment",
        )
    assert exc.value.status_code == 413
    assert "Journal attachment exceeds the upload limit" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_housing_journal_attachment_accepts_payload_within_limit() -> None:
    payload = b"ok-content"
    file = UploadFile(filename="attachment.pdf", file=BytesIO(payload))
    content = await _read_housing_upload_with_size_limit(
        file=file,
        limit_bytes=1024 * 1024,
        feature_name="Journal attachment",
    )
    assert content == payload
