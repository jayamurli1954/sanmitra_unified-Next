from __future__ import annotations

from typing import Any

from app.modules.office_ai.connectors.base import tenant_has_module


async def get_open_maintenance_requests(*, tenant_id: str, tenant: dict[str, Any]) -> list[dict[str, Any]]:
    if not tenant_has_module(tenant, "housing"):
        return []
    return []
