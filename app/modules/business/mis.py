"""MitraBooks MIS KPI contracts.

This module does not post, mutate, or infer financial facts. It reshapes the
trusted ledger dashboard and AR/AP aging outputs into a stable MIS response for
the ERP shell.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import get_business_dashboard
from app.modules.business import allocation_service, financial_health

_CENT = Decimal("0.01")


def _d(value) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(_CENT)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _money(value) -> str:
    return str(_d(value))


def _float(value) -> float:
    return float(_d(value))


def _overdue_total(aging: dict) -> Decimal:
    totals = (aging or {}).get("totals") or {}
    return sum((_d(totals.get(bucket)) for bucket in ("31-60", "61-90", "90+")), Decimal("0.00"))


def _aging_summary(aging: dict) -> dict:
    aging = aging or {}
    return {
        "total": _money(aging.get("grand_total")),
        "current": _money((aging.get("totals") or {}).get("0-30")),
        "overdue": _money(_overdue_total(aging)),
        "over_90": _money((aging.get("totals") or {}).get("90+")),
        "buckets_order": aging.get("buckets_order") or ["0-30", "31-60", "61-90", "90+"],
        "totals": {key: _money(value) for key, value in ((aging.get("totals") or {}).items())},
    }


def _top_parties(aging: dict, *, limit: int = 5) -> list[dict]:
    rows = []
    for row in (aging or {}).get("by_party") or []:
        buckets = row.get("buckets") or {}
        overdue = sum((_d(buckets.get(bucket)) for bucket in ("31-60", "61-90", "90+")), Decimal("0.00"))
        rows.append({
            "party_id": row.get("party_id"),
            "party_name": row.get("party_name") or "Unallocated",
            "outstanding": _money(row.get("total")),
            "overdue": _money(overdue),
            "over_90": _money(buckets.get("90+")),
        })
    rows.sort(key=lambda item: (_d(item["outstanding"]), _d(item["overdue"])), reverse=True)
    return [{**row, "rank": index + 1} for index, row in enumerate(rows[:limit])]


def _monthly_sales_purchase_trend(dashboard: dict) -> list[dict]:
    trend = dashboard.get("monthly_trend") or []
    rows = []
    for row in trend:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        month, sales_lakhs, purchase_lakhs = row[0], row[1], row[2]
        sales = _d(Decimal(str(sales_lakhs or 0)) * Decimal("100000"))
        purchases = _d(Decimal(str(purchase_lakhs or 0)) * Decimal("100000"))
        rows.append({
            "month": str(month),
            "sales_lakhs": _float(sales_lakhs),
            "purchases_lakhs": _float(purchase_lakhs),
            "sales": _money(sales),
            "purchases": _money(purchases),
            "net": _money(sales - purchases),
        })
    return rows


def assemble_mis_kpis(*, dashboard: dict, ar_aging: dict, ap_aging: dict, as_of: date) -> dict:
    health = financial_health.assemble_financial_health(
        dashboard=dashboard, ar_aging=ar_aging, ap_aging=ap_aging, as_of=as_of,
    )
    cash = _d(dashboard.get("cash_and_bank"))
    receivables = _d(dashboard.get("receivables"))
    payables = _d(dashboard.get("payables"))
    gst_payable = max(_d((dashboard.get("gst") or {}).get("payable")), Decimal("0.00"))
    current_assets = cash + receivables
    current_liabilities = payables + gst_payable
    ratio = float((current_assets / current_liabilities).quantize(_CENT)) if current_liabilities > 0 else None

    return {
        "as_of": as_of.isoformat(),
        "financial_year_start": dashboard.get("financial_year_start"),
        "accounting_entity_id": ar_aging.get("accounting_entity_id") or ap_aging.get("accounting_entity_id"),
        "source": {
            "sales_purchase_trend": "posted_ledger",
            "working_capital": "posted_ledger",
            "top_parties": "open_item_aging",
            "overdue_dashboards": "open_item_aging",
            "financial_health": "deterministic_financial_health",
        },
        "monthly_sales_purchase_trend": _monthly_sales_purchase_trend(dashboard),
        "top_customers": _top_parties(ar_aging),
        "top_vendors": _top_parties(ap_aging),
        "working_capital": {
            "cash_and_bank": _money(cash),
            "receivables": _money(receivables),
            "payables": _money(payables),
            "gst_payable": _money(gst_payable),
            "current_assets": _money(current_assets),
            "current_liabilities": _money(current_liabilities),
            "net_working_capital": _money(current_assets - current_liabilities),
            "current_ratio": ratio,
        },
        "overdue": {
            "receivables": _aging_summary(ar_aging),
            "payables": _aging_summary(ap_aging),
        },
        "financial_health": {
            "summary": health.get("summary"),
            "kpis": health.get("kpis") or [],
            "alerts": health.get("alerts") or [],
            "charts": health.get("charts") or [],
        },
    }


async def build_mis_kpis(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    as_of: date | None = None,
) -> dict:
    as_of = as_of or date.today()
    dashboard = await get_business_dashboard(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )
    ar_aging = await allocation_service.ar_ap_aging(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, kind="receivable", as_of=as_of,
    )
    ap_aging = await allocation_service.ar_ap_aging(
        tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id=accounting_entity_id, kind="payable", as_of=as_of,
    )
    return assemble_mis_kpis(dashboard=dashboard, ar_aging=ar_aging, ap_aging=ap_aging, as_of=as_of)
