"""MandirMitra donation, seva, and fund reporting routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import get_cost_centre_ledger_pl
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.report_helpers import (
    detailed_donation_report,
    detailed_seva_report,
    donation_category_wise_report,
    donation_daily_report,
    donation_monthly_report,
    posted_donations,
    seva_schedule_report,
)
from app.modules.mandir_compat.router import router

@router.get("/reports/donations/category-wise")
async def mandir_report_donations_category_wise(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await donation_category_wise_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date)


@router.get("/reports/donations/detailed")
async def mandir_report_donations_detailed(
    from_date: date = Query(...),
    to_date: date = Query(...),
    category: str | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await detailed_donation_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=from_date,
        to_date=to_date,
        category=category,
        payment_mode=payment_mode,
    )


async def _mandir_donation_designation_report(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    from_date: date,
    to_date: date,
    id_field: str,
    name_field: str,
) -> dict[str, Any]:
    donations = await mandir_router.posted_donations(
        session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date
    )
    grouped: dict[str, dict[str, Any]] = {}
    for donation in donations:
        designation_id = str(donation.get(id_field) or "").strip()
        designation_name = str(donation.get(name_field) or "").strip()
        if not designation_id or not designation_name:
            continue
        bucket = grouped.setdefault(
            designation_id,
            {"id": designation_id, "name": designation_name, "count": 0, "amount": Decimal("0")},
        )
        bucket["count"] += 1
        bucket["amount"] += Decimal(str(donation.get("amount") or "0"))
    items = [
        {**bucket, "amount": float(bucket["amount"])}
        for bucket in sorted(grouped.values(), key=lambda row: (str(row["name"]).lower(), str(row["id"])))
    ]
    return {
        "from_date": from_date.isoformat(), "to_date": to_date.isoformat(), "items": items,
        "total_count": sum(int(item["count"]) for item in items),
        "total_amount": float(sum((Decimal(str(item["amount"])) for item in items), Decimal("0"))),
    }


@router.get("/reports/donations/fund-wise")
async def mandir_report_donations_fund_wise(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund donation reporting"
    )
    return await _mandir_donation_designation_report(
        session, tenant_id=context.tenant_id, app_key=context.app_key, from_date=from_date, to_date=to_date,
        id_field="fund_id", name_field="fund_name",
    )


@router.get("/reports/donations/festival-wise")
async def mandir_report_donations_festival_wise(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="festival donation reporting"
    )
    return await _mandir_donation_designation_report(
        session, tenant_id=context.tenant_id, app_key=context.app_key, from_date=from_date, to_date=to_date,
        id_field="festival_id", name_field="festival_name",
    )


async def _mandir_fund_subledger_data(
    session: AsyncSession, *, tenant_id: str, app_key: str, from_date: date, to_date: date,
) -> dict[str, Any]:
    ledger = await mandir_router.get_cost_centre_ledger_pl(
        session, tenant_id=tenant_id, app_key=app_key,
        accounting_entity_id="primary", from_date=from_date, to_date=to_date,
    )
    prior_to = from_date - timedelta(days=1)
    prior_ledger = {"buckets": {}}
    if from_date > date(1900, 1, 1):
        prior_ledger = await mandir_router.get_cost_centre_ledger_pl(
            session, tenant_id=tenant_id, app_key=app_key,
            accounting_entity_id="primary", from_date=date(1900, 1, 1), to_date=prior_to,
        )
    funds = await mandir_router.get_collection("mandir_funds").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).sort("name", 1).to_list(length=500)
    transfers = await mandir_router.get_collection("mandir_fund_transfers").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=2000)
    openings = await mandir_router.get_collection("mandir_fund_opening_balances").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=1000)
    transfer_buckets: dict[str, dict[str, Decimal]] = {}
    prior_transfer_buckets: dict[str, dict[str, Decimal]] = {}
    opening_buckets: dict[str, Decimal] = {}
    prior_opening_buckets: dict[str, Decimal] = {}

    def transfer_bucket(target: dict[str, dict[str, Decimal]], fund_id: str) -> dict[str, Decimal]:
        return target.setdefault(fund_id, {"transfers_in": Decimal("0"), "transfers_out": Decimal("0")})

    def apply_transfer_event(transfer: dict[str, Any], event_day: date, *, reverse: bool = False) -> None:
        if event_day < date(1900, 1, 1) or event_day > to_date:
            return
        target = prior_transfer_buckets if event_day < from_date else transfer_buckets
        amount = Decimal(str(transfer.get("amount") or "0"))
        from_key = "transfers_in" if reverse else "transfers_out"
        to_key = "transfers_out" if reverse else "transfers_in"
        transfer_bucket(target, str(transfer.get("from_fund_id")))[from_key] += amount
        transfer_bucket(target, str(transfer.get("to_fund_id")))[to_key] += amount

    for transfer in transfers:
        if not transfer.get("journal_entry_id"):
            continue
        apply_transfer_event(transfer, date.fromisoformat(str(transfer.get("transfer_date"))))
        reversed_at = mandir_router._parse_iso_datetime(transfer.get("reversed_at")) if transfer.get("status") == "reversed" else None
        if reversed_at:
            apply_transfer_event(transfer, reversed_at.date(), reverse=True)

    def apply_opening_event(fund_id: str, amount: Decimal, event_day: date) -> None:
        if event_day < date(1900, 1, 1) or event_day > to_date:
            return
        target = prior_opening_buckets if event_day < from_date else opening_buckets
        target[fund_id] = target.get(fund_id, Decimal("0")) + amount

    for opening in openings:
        if not opening.get("journal_entry_id"):
            continue
        fund_id = str(opening.get("fund_id") or "")
        amount = Decimal(str(opening.get("amount") or "0"))
        apply_opening_event(fund_id, amount, date.fromisoformat(str(opening.get("opening_date"))))
        reversed_at = mandir_router._parse_iso_datetime(opening.get("reversed_at")) if opening.get("status") == "reversed" else None
        if reversed_at:
            apply_opening_event(fund_id, -amount, reversed_at.date())

    rows = []
    ledger_buckets = ledger.get("buckets") or {}
    prior_ledger_buckets = prior_ledger.get("buckets") or {}
    for fund in funds:
        fund_id = str(fund.get("id") or "")
        dimension_id = str(fund.get("accounting_dimension_id") or "")
        pnl = ledger_buckets.get(dimension_id) or {}
        prior_pnl = prior_ledger_buckets.get(dimension_id) or {}
        movement = transfer_buckets.get(fund_id) or {}
        prior_movement = prior_transfer_buckets.get(fund_id) or {}
        income = Decimal(str(pnl.get("income") or "0"))
        expense = Decimal(str(pnl.get("expense") or "0"))
        transfers_in = Decimal(str(movement.get("transfers_in") or "0"))
        transfers_out = Decimal(str(movement.get("transfers_out") or "0"))
        opening_entries = opening_buckets.get(fund_id, Decimal("0"))
        opening_balance = (
            prior_opening_buckets.get(fund_id, Decimal("0"))
            + Decimal(str(prior_pnl.get("income") or "0"))
            - Decimal(str(prior_pnl.get("expense") or "0"))
            + Decimal(str(prior_movement.get("transfers_in") or "0"))
            - Decimal(str(prior_movement.get("transfers_out") or "0"))
        )
        net_activity = income - expense + transfers_in - transfers_out
        closing_balance = opening_balance + opening_entries + net_activity
        rows.append({
            "fund_id": fund_id, "fund_name": str(fund.get("name") or ""),
            "fund_type": str(fund.get("fund_type") or ""), "accounting_dimension_id": dimension_id,
            "opening_balance": float(opening_balance), "opening_entries": float(opening_entries),
            "income": float(income), "expense": float(expense),
            "transfers_in": float(transfers_in), "transfers_out": float(transfers_out),
            "net_activity": float(net_activity), "closing_balance": float(closing_balance),
        })
    return {
        "from_date": from_date.isoformat(), "to_date": to_date.isoformat(), "items": rows,
        "totals": {
            key: float(sum((Decimal(str(row[key])) for row in rows), Decimal("0")))
            for key in (
                "opening_balance", "opening_entries", "income", "expense",
                "transfers_in", "transfers_out", "net_activity", "closing_balance",
            )
        },
    }


@router.get("/reports/funds/subledger")
async def mandir_report_fund_subledger(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund subledger reporting",
    )
    return await _mandir_fund_subledger_data(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=from_date, to_date=to_date,
    )


@router.get("/reports/funds/as-of")
async def mandir_report_funds_as_of(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund as-of reporting",
    )
    report = await _mandir_fund_subledger_data(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=date(1900, 1, 1), to_date=as_of,
    )
    return {
        "as_of": as_of.isoformat(),
        "items": [
            {
                "fund_id": row["fund_id"], "fund_name": row["fund_name"],
                "fund_type": row["fund_type"], "accounting_dimension_id": row["accounting_dimension_id"],
                "balance": row["closing_balance"],
            }
            for row in report["items"]
        ],
        "total_balance": report["totals"]["closing_balance"],
    }


@router.get("/reports/sevas/detailed")
async def mandir_report_sevas_detailed(
    from_date: date = Query(...),
    to_date: date = Query(...),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await detailed_seva_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date, status=status)


@router.get("/reports/sevas/schedule")
async def mandir_report_sevas_schedule(
    days: int = Query(default=3, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await seva_schedule_report(session, tenant_id=tenant_id, app_key=app_key, days=days)


@router.get("/donations/report/daily")
async def mandir_donations_daily_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_value: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = mandir_router._resolve_report_date_window(from_date=from_date, to_date=to_date, single_date=date_value)
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await donation_daily_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    category_data = await donation_category_wise_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=start_date,
        to_date=end_date,
    )
    data["total"] = data.get("total_amount", 0.0)
    data["count"] = data.get("total_count", 0)
    data["by_category"] = category_data.get("categories", [])
    return data


@router.get("/donations/report/monthly")
async def mandir_donations_monthly_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=1900, le=3000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = mandir_router._resolve_report_date_window(
        from_date=from_date,
        to_date=to_date,
        month=month,
        year=year,
    )
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await donation_monthly_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    category_data = await donation_category_wise_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=start_date,
        to_date=end_date,
    )
    data["total"] = data.get("total_amount", 0.0)
    data["count"] = data.get("total_count", 0)
    data["by_category"] = category_data.get("categories", [])
    return data


@router.get("/donations/export/excel")
async def mandir_donations_export_excel(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = mandir_router._resolve_export_window(from_date=from_date, to_date=to_date, date_from=date_from, date_to=date_to)
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await detailed_donation_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    return {**data, "export_format": "excel"}


@router.get("/donations/export/pdf")
async def mandir_donations_export_pdf(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = mandir_router._resolve_export_window(from_date=from_date, to_date=to_date, date_from=date_from, date_to=date_to)
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await detailed_donation_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    return {**data, "export_format": "pdf"}

