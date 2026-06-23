"""Presentation/report assembly for the Cost-Centre Accounting add-on.

Thin layer over the scoped ledger aggregations in ``app.accounting.service`` and
the cost-centre masters/budgets in ``app.modules.business``. Resolves cost-centre
names and shapes rows for the UI and for CSV/Excel export. All reads are scoped by
tenant + app + accounting entity by the underlying queries — this layer never
widens that scope.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def _q2(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


async def build_cost_centre_pl(
    *, session, tenant_id: str, app_key: str, accounting_entity_id: str,
    from_date: date, to_date: date,
) -> dict:
    """Cost-centre P&L with names resolved from this entity's masters. Income/
    expense/net per cost centre, plus the untagged bucket; rows sorted by net."""
    from app.accounting.service import get_cost_centre_ledger_pl
    from app.modules.business.dimensions import list_dimensions

    raw = await get_cost_centre_ledger_pl(
        session, tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        from_date=from_date, to_date=to_date,
    )
    # include_inactive so historical tags on deactivated cost centres still resolve.
    masters = await list_dimensions(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        include_inactive=True,
    )
    names = {c["dimension_id"]: c for c in masters["cost_centres"]}

    rows: list[dict] = []
    untagged = {"income": "0.00", "expense": "0.00", "net": "0.00"}
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")

    for key, sums in raw["buckets"].items():
        income = _q2(sums["income"])
        expense = _q2(sums["expense"])
        net = _q2(income - expense)
        total_income += income
        total_expense += expense
        if key == "__untagged__":
            untagged = {"income": str(income), "expense": str(expense), "net": str(net)}
            continue
        meta = names.get(key, {})
        rows.append({
            "cost_centre_id": key,
            "code": meta.get("code") or key,
            "name": meta.get("name") or "(deleted cost centre)",
            "income": str(income),
            "expense": str(expense),
            "net": str(net),
        })

    rows.sort(key=lambda r: -Decimal(r["net"]))
    return {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "rows": rows,
        "untagged": untagged,
        "totals": {
            "income": str(_q2(total_income)),
            "expense": str(_q2(total_expense)),
            "net": str(_q2(total_income - total_expense)),
        },
    }


async def build_cost_centre_tree(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, include_inactive: bool = False,
) -> dict:
    """Cost-centre masters rolled into a parent/child forest for this entity."""
    from app.modules.business.dimensions import build_cost_centre_tree as _tree, list_dimensions

    masters = await list_dimensions(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        include_inactive=include_inactive,
    )
    return {"roots": _tree(masters["cost_centres"])}


def cost_centre_pl_export_spec(report: dict) -> dict:
    """Map a cost-centre P&L into a report_export.export_report spec."""
    columns = [
        {"key": "code", "label": "Cost Centre"},
        {"key": "name", "label": "Name"},
        {"key": "income", "label": "Income", "numeric": True},
        {"key": "expense", "label": "Expense", "numeric": True},
        {"key": "net", "label": "Net", "numeric": True},
    ]
    rows = list(report["rows"])
    rows.append({"code": "", "name": "Untagged", **report["untagged"]})
    footer = {"code": "", "name": "Total", **report["totals"]}
    return {
        "title": f"Cost-Centre P&L ({report['from_date']} to {report['to_date']})",
        "columns": columns,
        "rows": rows,
        "footer": footer,
    }
