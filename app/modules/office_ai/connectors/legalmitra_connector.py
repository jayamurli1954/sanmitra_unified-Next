from __future__ import annotations

from typing import Any

from app.modules.office_ai.connectors.base import tenant_has_module


async def get_pending_documents(*, tenant_id: str, tenant: dict[str, Any]) -> list[dict[str, Any]]:
    # Stub until LegalMitra service surface is wired (Phase 3).
    if not tenant_has_module(tenant, "legal"):
        return []
    return []
