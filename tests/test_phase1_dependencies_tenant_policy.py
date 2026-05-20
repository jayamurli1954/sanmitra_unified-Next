import pytest
from fastapi import HTTPException

from app.core import phase1_dependencies


def _user(role: str = "tenant_admin", tenant_id: str | None = "tenant-a") -> dict:
    return {
        "user_id": "user-1",
        "sub": "user-1",
        "role": role,
        "tenant_id": tenant_id,
        "app_key": "mandirmitra",
    }


@pytest.mark.asyncio
async def test_phase1_resolve_tenant_blocks_regular_header_override():
    with pytest.raises(HTTPException) as exc_info:
        await phase1_dependencies.resolve_tenant_id(_user(), "tenant-b")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Tenant override not allowed"


@pytest.mark.asyncio
async def test_phase1_resolve_tenant_allows_superadmin_header_override():
    tenant_id = await phase1_dependencies.resolve_tenant_id(_user(role="super_admin"), "tenant-b")

    assert tenant_id == "tenant-b"


@pytest.mark.asyncio
async def test_phase1_current_tenant_requires_token_tenant():
    with pytest.raises(HTTPException) as exc_info:
        await phase1_dependencies.get_current_tenant_id(_user(tenant_id=None))

    assert exc_info.value.status_code == 401
