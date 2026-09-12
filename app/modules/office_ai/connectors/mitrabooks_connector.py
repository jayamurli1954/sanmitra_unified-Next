from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.connectors.base import tenant_has_module

_logger = logging.getLogger("officemitra.connectors.mitrabooks")


async def get_todays_revenue(
    *,
    tenant_id: str,
    app_key: str,
    tenant: dict[str, Any],
    session=None,
) -> dict[str, Any]:
    """Read-only: FY income snapshot via accounting dashboard service (not raw SQL)."""
    if not tenant_has_module(tenant, "business") and not tenant_has_module(tenant, "accounting"):
        return {"enabled": False, "income_fytd": None, "as_of": None}
    if session is None:
        return {"enabled": True, "income_fytd": None, "as_of": None, "note": "session_required"}
    try:
        from app.accounting.reports import get_business_dashboard

        dashboard = await get_business_dashboard(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            as_of=date.today(),
        )
        return {
            "enabled": True,
            "income_fytd": dashboard.get("income"),
            "expense_fytd": dashboard.get("expense"),
            "net_fytd": dashboard.get("net"),
            "as_of": str(date.today()),
            "source": "mitrabooks.get_business_dashboard",
        }
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.mitrabooks.failure")
        _logger.warning("get_todays_revenue failed: %s", type(exc).__name__)
        return {"enabled": True, "error": "connector_failed", "income_fytd": None}


async def get_overdue_invoices(
    *,
    tenant_id: str,
    app_key: str,
    tenant: dict[str, Any],
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Read-only: AR aging via allocation service (not raw table access)."""
    if not tenant_has_module(tenant, "business") and not tenant_has_module(tenant, "accounting"):
        return []
    try:
        from app.modules.business import allocation_service

        aging = await allocation_service.ar_ap_aging(
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            kind="receivable",
            as_of=date.today(),
        )
        rows: list[dict[str, Any]] = []
        for row in (aging or {}).get("by_party") or []:
            buckets = row.get("buckets") or {}
            overdue = 0.0
            for bucket in ("31-60", "61-90", "90+"):
                try:
                    overdue += float(buckets.get(bucket) or 0)
                except (TypeError, ValueError):
                    continue
            if overdue <= 0:
                continue
            rows.append(
                {
                    "party_name": row.get("party_name") or row.get("name") or "Party",
                    "overdue": overdue,
                    "outstanding": row.get("total") or row.get("outstanding"),
                }
            )
            if len(rows) >= limit:
                break
        return rows
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.mitrabooks.failure")
        _logger.warning("get_overdue_invoices failed: %s", type(exc).__name__)
        return []


CA_QUEUE_APP_KEY = "mitrabooks"


async def list_ca_staff_documents(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    accounting_entity_id: str = "primary",
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Read-only: MitraBooks CA staff queue via ca_clients (not raw Mongo)."""
    if not tenant_has_module(tenant, "business"):
        return {"enabled": False, "items": [], "total": 0, "reason": "business_module_off"}
    try:
        from app.modules.business.services import ca_clients

        result = await ca_clients.list_ca_document_metadata(
            tenant_id=tenant_id,
            app_key=CA_QUEUE_APP_KEY,
            accounting_entity_id=str(accounting_entity_id or "primary").strip() or "primary",
            status=status,
            limit=limit,
        )
        return {
            "enabled": True,
            "items": result.get("items") or [],
            "total": int(result.get("total") or 0),
            "source": "mitrabooks.list_ca_document_metadata",
        }
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.mitrabooks.failure")
        _logger.warning("list_ca_staff_documents failed: %s", type(exc).__name__)
        return {"enabled": True, "error": "connector_failed", "items": [], "total": 0}


async def get_ca_staff_document(
    *,
    tenant_id: str,
    tenant: dict[str, Any],
    document_id: str,
    accounting_entity_id: str | None = None,
) -> dict[str, Any] | None:
    """Read-only: one CA staff document via ca_clients."""
    if not tenant_has_module(tenant, "business"):
        return None
    try:
        from app.modules.business.services import ca_clients

        return await ca_clients.get_ca_document_metadata(
            tenant_id=tenant_id,
            app_key=CA_QUEUE_APP_KEY,
            document_id=document_id,
            accounting_entity_id=accounting_entity_id,
        )
    except Exception as exc:
        ai_metrics.incr("officemitra.connector.mitrabooks.failure")
        _logger.warning("get_ca_staff_document failed: %s", type(exc).__name__)
        return None
