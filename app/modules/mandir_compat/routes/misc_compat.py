"""MandirMitra compatibility stub routes (assets, backup, bank, HR, etc.).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, File, Header, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)


def _ok(name: str, **extra: Any) -> dict[str, Any]:
    return {"status": "ok", "endpoint": name, **extra}


@router.get("/assets")
async def mandir_assets(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/assets/cwip")
async def mandir_assets_cwip(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/assets/reports/summary")
async def mandir_assets_report_summary(_current_user: dict = Depends(get_current_user)):
    return {"summary": {}}


@router.post("/assets/revaluation", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_assets_revaluation(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("assets/revaluation")


@router.get("/backup-restore/status")
async def mandir_backup_status(_current_user: dict = Depends(get_current_user)):
    return {"backup_enabled": False, "last_backup_at": None, "status": "idle"}


@router.post("/backup-restore/backup", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_backup_now(_current_user: dict = Depends(get_current_user)):
    return _ok("backup-restore/backup")


@router.get("/bank-accounts")
async def mandir_bank_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    docs = await mandir_router.get_collection("mandir_bank_accounts").find({"tenant_id": tenant_id, "app_key": app_key}).sort("updated_at", -1).to_list(length=200)
    return [mandir_router._sanitize_mongo_doc(doc) for doc in docs]


@router.post("/bank-accounts", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
@router.post("/bank-accounts/", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_create_bank_account(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    account_id = str(uuid4())
    doc = {
        "id": account_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        **{k: v for k, v in payload.items() if k not in {"id", "_id", "tenant_id", "app_key"}},
        "created_at": now,
        "updated_at": now,
    }
    await mandir_router.get_collection("mandir_bank_accounts").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Bank reconciliation (accounts / match / reconcile / statements / import / summary / entries)
# ROUTES : GET /bank-reconciliation/accounts  POST .../match|reconcile|statements/import  GET .../statements  GET .../statements/{id}/summary|entries|unmatched-book-entries
# ════════════════════════════════════════════════════════════════════════

@router.get("/bank-reconciliation/accounts")
async def mandir_bank_rec_accounts(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)

    sql_accounts = await mandir_router.list_accounts(session, app_key=app_key, tenant_id=tenant_id)
    bank_accounts = []
    cash_bank_accounts = []

    for account in sql_accounts:
        if not bool(getattr(account, "is_cash_bank", False)):
            continue

        name = str(getattr(account, "name", "") or "").lower()
        code = str(getattr(account, "code", "") or "").strip()
        row = {
            "id": int(account.id),
            "account_id": int(account.id),
            "code": code,
            "name": str(getattr(account, "name", "") or "").strip(),
            "type": str(getattr(account, "type", "") or "").strip(),
            "account_code": code,
            "account_name": str(getattr(account, "name", "") or "").strip(),
            "account_type": str(getattr(account, "type", "") or "").strip(),
            "is_cash_bank": True,
            "cash_bank_nature": "bank" if "bank" in name else "cash",
        }
        cash_bank_accounts.append(row)
        if "bank" in name or code == "12001":
            row["cash_bank_nature"] = "bank"
            bank_accounts.append(row)

    return bank_accounts or cash_bank_accounts


@router.post("/bank-reconciliation/match", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_match(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("bank-reconciliation/match")


@router.post("/bank-reconciliation/reconcile", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_reconcile(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("bank-reconciliation/reconcile")


@router.get("/bank-reconciliation/statements")
async def mandir_bank_rec_statements(_current_user: dict = Depends(get_current_user)):
    return []


@router.post("/bank-reconciliation/statements/import", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_statements_import(
    file: UploadFile | None = File(default=None),
    account_id: str | None = Query(default=None),
    statement_date: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    statement_id = str(uuid4())
    filename = str((file.filename if file else "") or "").strip() or "statement.csv"
    doc = {
        "id": statement_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "account_id": account_id,
        "statement_date": statement_date,
        "filename": filename,
        "status": "imported",
        "entries_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    await mandir_router.get_collection("mandir_bank_statements").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.get("/bank-reconciliation/statements/{statement_id}/summary")
async def mandir_bank_rec_statement_summary(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    statement = await mandir_router.get_collection("mandir_bank_statements").find_one({"id": statement_id, "tenant_id": tenant_id, "app_key": app_key})
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    return {
        "statement_id": statement_id,
        "status": str(statement.get("status") or "imported"),
        "total_entries": int(statement.get("entries_count") or 0),
        "matched_entries": 0,
        "unmatched_entries": int(statement.get("entries_count") or 0),
        "closing_balance": 0.0,
        "book_balance": 0.0,
        "difference": 0.0,
    }


@router.get("/bank-reconciliation/statements/{statement_id}/entries")
async def mandir_bank_rec_statement_entries(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    rows = await mandir_router.get_collection("mandir_bank_statement_entries").find(
        {"statement_id": statement_id, "tenant_id": tenant_id, "app_key": app_key}
    ).sort("entry_date", 1).to_list(length=2000)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.get("/bank-reconciliation/statements/{statement_id}/unmatched-book-entries")
async def mandir_bank_rec_unmatched_book_entries(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    rows = await mandir_router.get_collection("mandir_bank_unmatched_entries").find(
        {"statement_id": statement_id, "tenant_id": tenant_id, "app_key": app_key}
    ).sort("entry_date", 1).to_list(length=2000)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Sacred events, financial closing, auth (forgot / reset), HR, hundi
# ROUTES : GET /dashboard/sacred-events  POST /financial-closing/close-month|close-year  GET .../closing-summary|financial-years|period-closings  POST /forgot-password|reset-password  GET /hr/employees|attendance  GET /hundi/masters|openings
# ════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/sacred-events/nakshatra/{nakshatra}")
async def mandir_nakshatra_dates(nakshatra: str, limit: int = Query(default=8, ge=1, le=30), _current_user: dict = Depends(get_current_user)):
    today = date.today()
    out = []
    for i in range(limit):
        d = today.replace(day=min(28, today.day))
        out.append({"event_date": str(d), "weekday": d.strftime("%A"), "days_away": i, "is_today": i == 0})
    return {"nakshatra": nakshatra, "next_occurrences": out}


@router.post("/financial-closing/close-month", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_close_month(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("financial-closing/close-month")


@router.post("/financial-closing/close-year", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_close_year(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("financial-closing/close-year")


@router.get("/financial-closing/closing-summary")
async def mandir_closing_summary(_current_user: dict = Depends(get_current_user)):
    return {"summary": {}}


@router.get("/financial-closing/financial-years")
async def mandir_financial_years(_current_user: dict = Depends(get_current_user)):
    y = datetime.now(timezone.utc).year
    return [{"financial_year": f"{y}-{y+1}", "is_current": True}]


@router.get("/financial-closing/period-closings")
async def mandir_period_closings(_current_user: dict = Depends(get_current_user)):
    return []


@router.post("/forgot-password")
async def mandir_forgot_password(_payload: dict[str, Any]):
    return _ok("forgot-password")


@router.post("/reset-password")
async def mandir_reset_password(_payload: dict[str, Any]):
    return _ok("reset-password")


@router.get("/hr/employees")
async def mandir_hr_employees(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/hr/attendance/monthly")
async def mandir_hr_attendance_monthly(_current_user: dict = Depends(get_current_user)):
    return []

