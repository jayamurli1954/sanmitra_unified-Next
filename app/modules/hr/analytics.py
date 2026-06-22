"""Payroll analytics (Step 8) — a compliance/cost dashboard built from the
already-aggregated payroll run totals plus current headcount.

Each payroll run stores its period totals (gross/TDS/EPF/ESI/PT/net), so a
trailing-N-month trend is a cheap read over runs — no separate cache layer is
needed at this scale. Employee movement (active vs exited) comes from the
employee status the F&F flow maintains.
"""
from __future__ import annotations

from decimal import Decimal

from app.db.mongo import get_collection
from app.modules.hr.payroll_run import HR_RUNS_COLLECTION
from app.modules.hr.service import HR_EMPLOYEES_COLLECTION


def _d(value) -> float:
    try:
        return float(Decimal(str(value or "0")))
    except Exception:
        return 0.0


async def compile_dashboard(*, tenant_id: str, app_key: str, accounting_entity_id: str, months: int = 6) -> dict:
    months = max(1, min(int(months or 6), 24))
    runs = (
        await get_collection(HR_RUNS_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id})
        .sort("period", -1)
        .limit(months)
        .to_list(length=months)
    )
    runs = list(reversed(runs))  # chronological for the trend

    labels: list[str] = []
    tds_trend: list[float] = []
    epf_trend: list[float] = []
    net_trend: list[float] = []
    headcount_trend: list[int] = []
    for r in runs:
        totals = r.get("totals") or {}
        labels.append(r.get("period"))
        tds_trend.append(_d(totals.get("tds")))
        # EPF dataset shows the full statutory PF (employee + employer) already
        # summed into totals["epf"] by the run.
        epf_trend.append(_d(totals.get("epf")))
        net_trend.append(_d(totals.get("net")))
        headcount_trend.append(int(r.get("employee_count") or 0))

    employees = get_collection(HR_EMPLOYEES_COLLECTION)
    active = await employees.count_documents(
        {"tenant_id": tenant_id, "app_key": app_key, "status": "active"}
    )
    exited = await employees.count_documents(
        {"tenant_id": tenant_id, "app_key": app_key, "status": "exited"}
    )

    latest = runs[-1] if runs else None
    latest_totals = (latest or {}).get("totals") or {}

    return {
        "labels": labels,
        "datasets": {
            "tds_liability": tds_trend,
            "epf_total": epf_trend,
            "net_disbursed": net_trend,
            "headcount": headcount_trend,
        },
        "summary": {
            "active_employees": int(active),
            "exited_employees": int(exited),
            "latest_period": (latest or {}).get("period"),
            "latest_net_payout": _d(latest_totals.get("net")),
            "latest_tds": _d(latest_totals.get("tds")),
        },
    }
