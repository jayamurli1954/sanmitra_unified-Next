from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors import (
    gruhamitra_connector,
    legalmitra_connector,
    mandirmitra_connector,
    mitrabooks_connector,
)
from app.modules.office_ai.connectors.base import tenant_has_module

_logger = logging.getLogger("officemitra.connectors.manager")

CollectFn = Callable[..., Awaitable[Any]]


def _module_any(tenant: dict[str, Any], *keys: str) -> bool:
    return any(tenant_has_module(tenant, key) for key in keys)


async def _collect_mitrabooks(*, tenant_id: str, app_key: str, tenant: dict, session=None) -> dict[str, Any]:
    revenue = await mitrabooks_connector.get_todays_revenue(
        tenant_id=tenant_id, app_key=app_key, tenant=tenant, session=session
    )
    overdue = await mitrabooks_connector.get_overdue_invoices(
        tenant_id=tenant_id, app_key=app_key, tenant=tenant
    )
    return {"revenue": revenue, "overdue": overdue}


async def _collect_legal(*, tenant_id: str, tenant: dict, app_key: str = "", **_kwargs) -> list:
    return await legalmitra_connector.get_pending_documents(
        tenant_id=tenant_id, tenant=tenant, app_key=app_key
    )


async def _collect_housing(*, tenant_id: str, tenant: dict, app_key: str = "", **_kwargs) -> list:
    return await gruhamitra_connector.get_open_maintenance_requests(
        tenant_id=tenant_id, tenant=tenant, app_key=app_key
    )


async def _collect_temple(*, tenant_id: str, tenant: dict, app_key: str = "", session=None, **_kwargs) -> list:
    return await mandirmitra_connector.get_upcoming_events_or_donations(
        tenant_id=tenant_id, tenant=tenant, app_key=app_key, session=session
    )


# kind: internal = unified-backend module service interface; external = separate product contract
CONNECTOR_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "key": "mitrabooks",
        "kind": "internal",
        "section": "mitrabooks",
        "requires_modules": ("business", "accounting"),
        "collect": _collect_mitrabooks,
    },
    {
        "key": "legalmitra",
        "kind": "external",
        "section": "legal_pending_documents",
        "requires_modules": ("legal",),
        "collect": _collect_legal,
    },
    {
        "key": "gruhamitra",
        "kind": "internal",
        "section": "gruhamitra_maintenance",
        "requires_modules": ("housing",),
        "collect": _collect_housing,
    },
    {
        "key": "mandirmitra",
        "kind": "internal",
        "section": "mandirmitra_upcoming",
        "requires_modules": ("temple",),
        "collect": _collect_temple,
    },
)


def list_registered_connectors() -> list[dict[str, Any]]:
    return [
        {
            "key": item["key"],
            "kind": item["kind"],
            "section": item["section"],
            "requires_modules": list(item["requires_modules"]),
        }
        for item in CONNECTOR_REGISTRY
    ]


async def collect_connector_facts(
    *,
    tenant_id: str,
    app_key: str,
    tenant: dict[str, Any],
    session=None,
) -> dict[str, Any]:
    """Discover and invoke available connectors. Never raises for missing modules."""
    loaded: list[str] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    sections: dict[str, Any] = {}
    source_modules: list[str] = []

    for spec in CONNECTOR_REGISTRY:
        requires = tuple(spec["requires_modules"])
        if not _module_any(tenant, *requires):
            skipped.append({"key": spec["key"], "reason": "module_not_enabled"})
            continue
        try:
            payload = await spec["collect"](
                tenant_id=tenant_id,
                app_key=app_key,
                tenant=tenant,
                session=session,
            )
            sections[spec["section"]] = payload
            loaded.append(spec["key"])
            # Prefer the first required module name as the source tag.
            source_modules.append(requires[0])
        except Exception as exc:
            ai_metrics.incr(f"officemitra.connector.{spec['key']}.failure")
            _logger.warning("connector %s failed: %s", spec["key"], type(exc).__name__)
            failed.append({"key": spec["key"], "reason": "connector_exception"})
            sections[spec["section"]] = [] if spec["key"] != "mitrabooks" else {"enabled": False, "error": "connector_failed"}

    return {
        "connectors_loaded": loaded,
        "connectors_skipped": skipped,
        "connectors_failed": failed,
        "source_modules": source_modules,
        "sections": sections,
        "standalone": len(loaded) == 0,
    }
