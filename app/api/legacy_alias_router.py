from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.core.auth.service import login_user, logout_refresh_token, rotate_refresh_token
from app.core.users.service import create_user
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.mongo import get_collection
from app.db.postgres import get_async_session

router = APIRouter(prefix="/api", tags=["legacy-api-compat"])


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _bill_is_reversed(row: dict[str, Any]) -> bool:
    return str(row.get("status") or "").strip().lower() == "reversed" or bool(row.get("is_reversed"))


def _bill_paid_amount(row: dict[str, Any]) -> float:
    status = str(row.get("payment_status") or row.get("status") or "").strip().lower()
    if status in {"paid", "collected", "settled"}:
        return _safe_float(row.get("amount"))
    return _safe_float(row.get("paid_amount") or row.get("amount_paid") or row.get("collected_amount"))


async def _society_cash_bank_balance(session: AsyncSession, *, tenant_id: str, app_key: str) -> float:
    rows = (
        await session.execute(
            select(
                Account.code,
                Account.name,
                Account.is_cash_bank,
                func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
            )
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == "primary",
                    Account.type == "asset",
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.app_key == app_key,
                    JournalEntry.accounting_entity_id == "primary",
                    or_(
                        Account.is_cash_bank.is_(True),
                        Account.code.in_(["1000", "1010"]),
                    ),
                )
            )
            .group_by(Account.code, Account.name, Account.is_cash_bank)
        )
    ).all()
    return round(
        sum(_safe_float(row.debit_total) - _safe_float(row.credit_total) for row in rows),
        2,
    )


async def _account_code_balance(session: AsyncSession, *, tenant_id: str, app_key: str, account_code: str) -> float:
    rows = (
        await session.execute(
            select(
                Account.code,
                func.coalesce(func.sum(JournalLine.debit), 0).label("debit_total"),
                func.coalesce(func.sum(JournalLine.credit), 0).label("credit_total"),
            )
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == "primary",
                    Account.code == account_code,
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.app_key == app_key,
                    JournalEntry.accounting_entity_id == "primary",
                )
            )
            .group_by(Account.code)
        )
    ).all()
    return round(
        sum(_safe_float(row.debit_total) - _safe_float(row.credit_total) for row in rows),
        2,
    )


async def _recent_member_due_receipts(session: AsyncSession, *, tenant_id: str, app_key: str) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                JournalEntry.id,
                JournalEntry.entry_date,
                JournalEntry.reference,
                JournalEntry.description,
                JournalEntry.created_at,
                JournalLine.credit.label("amount"),
            )
            .join(JournalLine, JournalLine.journal_id == JournalEntry.id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(
                and_(
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == "primary",
                    Account.code == "1100",
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.app_key == app_key,
                    JournalEntry.accounting_entity_id == "primary",
                    JournalLine.credit > 0,
                )
            )
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .limit(5)
        )
    ).all()
    activities: list[dict[str, Any]] = []
    for row in rows:
        reference = str(row.reference or "").strip()
        description = str(row.description or "").strip()
        amount = _safe_float(row.amount)
        activities.append(
            {
                "id": f"receipt-{row.id}",
                "title": f"Maintenance receipt {reference}".strip(),
                "description": f"{row.entry_date.isoformat()} - Rs. {amount:,.2f}"
                if amount
                else row.entry_date.isoformat(),
                "icon": "receipt",
                "sort_key": str(row.created_at or row.entry_date),
                "detail": description,
            }
        )
    return activities


async def _gruhamitra_dashboard_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
) -> dict[str, Any]:
    bills = await get_collection("housing_maintenance_bills").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=5000)
    active_bills = [row for row in bills if not _bill_is_reversed(row)]
    latest_period = max(
        (
            (_safe_float(row.get("year")), _safe_float(row.get("month")))
            for row in active_bills
            if _safe_float(row.get("year")) and _safe_float(row.get("month"))
        ),
        default=None,
    )
    if latest_period:
        latest_year, latest_month = latest_period
        period_bills = [
            row
            for row in active_bills
            if _safe_float(row.get("year")) == latest_year and _safe_float(row.get("month")) == latest_month
        ]
    else:
        period_bills = []

    monthly_billing = round(sum(_safe_float(row.get("amount")) for row in period_bills), 2)
    society_balance = await _society_cash_bank_balance(session, tenant_id=tenant_id, app_key=app_key)
    dues_pending = max(
        await _account_code_balance(session, tenant_id=tenant_id, app_key=app_key, account_code="1100"),
        0.0,
    )
    complaints_open = await get_collection("housing_complaints").count_documents(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "status": {"$nin": ["resolved", "closed", "cancelled"]},
        }
    )
    bill_activities = [
        {
            "id": str(row.get("id") or row.get("_id") or f"bill-{idx}"),
            "title": f"Maintenance bill {row.get('flat_number') or ''}".strip(),
            "description": f"{row.get('month')}/{row.get('year')} - {row.get('status') or 'generated'}",
            "icon": "bill",
            "sort_key": str(row.get("updated_at") or row.get("created_at") or ""),
        }
        for idx, row in enumerate(
            sorted(
                active_bills,
                key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                reverse=True,
            )[:5]
        )
    ]
    receipt_activities = await _recent_member_due_receipts(session, tenant_id=tenant_id, app_key=app_key)
    recent_activities = sorted(
        [*receipt_activities, *bill_activities],
        key=lambda item: str(item.get("sort_key") or ""),
        reverse=True,
    )[:5]
    for activity in recent_activities:
        activity.pop("sort_key", None)

    return {
        "admin_stats": {
            "society_balance": society_balance,
            "monthly_billing": monthly_billing,
            "dues_pending": dues_pending,
            "complaints_open": int(complaints_open or 0),
            "billing_period": {
                "month": int(latest_period[1]) if latest_period else None,
                "year": int(latest_period[0]) if latest_period else None,
            },
            "collection_trend": [],
        },
        "recent_activities": recent_activities,
    }


@router.post("/auth/login", response_model=TokenResponse)
@router.post("/auth/legacy-login", response_model=TokenResponse)
async def legacy_auth_login(
    payload: LoginRequest,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "").strip())
    access_token, refresh_token = await login_user(payload.email, payload.password, app_key=app_key)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)



@router.post("/auth/register")
async def legacy_auth_register(payload: dict):
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    full_name = str(payload.get("full_name") or payload.get("name") or "User").strip()
    tenant_id = str(payload.get("tenant_id") or "seed-tenant-1").strip()
    role = str(payload.get("role") or "operator").strip()

    user = await create_user(email=email, password=password, full_name=full_name, tenant_id=tenant_id, role=role)
    return {"status": "created", "user": user}
@router.post("/auth/local-login", response_model=TokenResponse)
async def legacy_auth_local_login(
    payload: LoginRequest,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "").strip())
    access_token, refresh_token = await login_user(payload.email, payload.password, app_key=app_key)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/refresh", response_model=TokenResponse)
async def legacy_auth_refresh(
    payload: RefreshRequest,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "").strip())
    access_token, refresh_token = await rotate_refresh_token(payload.refresh_token, app_key=app_key)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/auth/logout")
async def legacy_auth_logout(payload: LogoutRequest):
    await logout_refresh_token(payload.refresh_token)
    return {"status": "ok"}


@router.get("/auth/me")
async def legacy_auth_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/dashboard/summary")
@router.get("/v1/dashboard/summary")
async def legacy_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    session: AsyncSession = Depends(get_async_session),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "").strip())
    if app_key == "gruhamitra":
        summary = await _gruhamitra_dashboard_summary(session, tenant_id=tenant_id, app_key=app_key)
        return {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "status": "ok",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **summary,
        }
    return {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "widgets": {
            "pending_tasks": 0,
            "notifications": 0,
            "summary_text": "Dashboard summary compatibility response.",
        },
    }


@router.get("/alerts")
async def legacy_invest_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "").strip())

    try:
        col = get_collection("investment_alerts")
        rows = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).limit(limit).to_list(length=limit)
    except Exception:
        rows = []

    alerts = [
        {
            "id": str(row.get("alert_id") or row.get("_id") or ""),
            "title": str(row.get("title") or "Alert"),
            "message": str(row.get("message") or ""),
            "severity": str(row.get("severity") or "info"),
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]

    return {"alerts": alerts, "count": len(alerts)}


