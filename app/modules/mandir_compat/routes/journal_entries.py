"""MandirMitra journal entry routes and financial report endpoints.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.service import AccountingValidationError, get_journal_drilldown
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.report_helpers import (
    accounts_payable_report,
    accounts_receivable_report,
    balance_sheet_report,
    bank_book_report,
    cash_book_report,
    category_income_report,
    day_book_report,
    ledger_report,
    profit_loss_report,
    receipts_payments_report,
    top_donors_report,
    trial_balance_report,
)
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

def _parse_journal_entry_date(value: Any) -> date:
    if isinstance(value, date):
        return value

    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).date()

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            return datetime.now(timezone.utc).date()


async def _resolve_sql_account_for_journal_line(
    session: AsyncSession,
    *,
    tenant_id: str,
    raw_account_id: Any,
) -> Account | None:
    raw_value = str(raw_account_id or "").strip()
    if not raw_value:
        return None

    maybe_id = mandir_router._safe_optional_int(raw_value)
    if maybe_id is not None:
        by_id_stmt = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.id == maybe_id,
        )
        by_id = (await session.execute(by_id_stmt)).scalar_one_or_none()
        if by_id is not None:
            return by_id

    code_candidate = raw_value.split(" - ", 1)[0].strip()
    normalized_code = mandir_router._normalize_mandir_account_code(code_candidate)
    if normalized_code:
        by_code_stmt = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.code == normalized_code,
        )
        by_code = (await session.execute(by_code_stmt)).scalar_one_or_none()
        if by_code is not None:
            return by_code

    return None


async def _normalize_mandir_journal_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    raw_lines: Any,
) -> tuple[list[dict[str, Any]], Decimal, Decimal]:
    if not isinstance(raw_lines, list) or len(raw_lines) < 2:
        raise HTTPException(status_code=400, detail="At least two journal lines are required")

    normalized_lines: list[dict[str, Any]] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for index, line in enumerate(raw_lines, start=1):
        if not isinstance(line, dict):
            raise HTTPException(status_code=400, detail=f"Journal line #{index} is invalid")

        account_ref = line.get("account_id")
        account = await mandir_router._resolve_sql_account_for_journal_line(
            session,
            tenant_id=tenant_id,
            raw_account_id=account_ref,
        )
        if account is None:
            raise HTTPException(status_code=400, detail=f"Invalid account on journal line #{index}")

        try:
            debit_amount = Decimal(str(line.get("debit_amount") or 0)).quantize(Decimal("0.01"))
            credit_amount = Decimal(str(line.get("credit_amount") or 0)).quantize(Decimal("0.01"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid amount on journal line #{index}") from exc

        if debit_amount < 0 or credit_amount < 0:
            raise HTTPException(status_code=400, detail=f"Amounts cannot be negative on line #{index}")
        if debit_amount == 0 and credit_amount == 0:
            raise HTTPException(status_code=400, detail=f"Either debit or credit is required on line #{index}")
        if debit_amount > 0 and credit_amount > 0:
            raise HTTPException(status_code=400, detail=f"Line #{index} cannot have both debit and credit")

        total_debit += debit_amount
        total_credit += credit_amount

        reference_account_id = mandir_router._safe_optional_int(account_ref)
        if reference_account_id is None:
            reference_account_id = mandir_router._safe_optional_int(str(account.code or "").strip()) or int(account.id)

        normalized_lines.append(
            {
                "account_id": reference_account_id,
                "account_code": str(account.code or "").strip(),
                "account_name": str(account.name or "").strip(),
                "ledger_account_id": int(account.id),
                "debit_amount": float(debit_amount),
                "credit_amount": float(credit_amount),
                "description": str(line.get("description") or "").strip(),
            }
        )

    if total_debit <= 0 or total_credit <= 0:
        raise HTTPException(status_code=400, detail="Total debit and credit must be greater than zero")
    if total_debit != total_credit:
        raise HTTPException(status_code=400, detail="Total debit and credit must be equal")

    return normalized_lines, total_debit, total_credit


async def _validate_mandir_journal_cash_balance(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    normalized_lines: list[dict[str, Any]],
) -> None:
    accounting_lines: list[tuple[int, Decimal, Decimal]] = []
    for line in normalized_lines:
        ledger_account_id = mandir_router._safe_optional_int(line.get("ledger_account_id"))
        if ledger_account_id is None:
            continue
        accounting_lines.append(
            (
                ledger_account_id,
                Decimal(str(line.get("debit_amount") or 0)).quantize(Decimal("0.01")),
                Decimal(str(line.get("credit_amount") or 0)).quantize(Decimal("0.01")),
            )
        )

    try:
        await mandir_router.validate_cash_balance_for_journal_lines(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            normalized_lines=accounting_lines,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _mandir_journal_entry_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = mandir_router._sanitize_mongo_doc(doc)
    row["entry_number"] = str(row.get("entry_number") or f"JE-{str(row.get('id') or '')[:8].upper()}")
    row["entry_date"] = str(row.get("entry_date") or datetime.now(timezone.utc).date().isoformat())[:10]
    row["narration"] = str(row.get("narration") or row.get("description") or "").strip()
    row["reference_type"] = str(row.get("reference_type") or "").strip().lower() or None
    row["reference_id"] = mandir_router._safe_optional_int(row.get("reference_id"))
    row["status"] = str(row.get("status") or "draft").strip().lower() or "draft"
    row["total_debit"] = mandir_router._safe_float(row.get("total_debit"), 0.0)
    row["total_credit"] = mandir_router._safe_float(row.get("total_credit"), 0.0)
    row["total_amount"] = mandir_router._safe_float(
        row.get("total_amount"),
        mandir_router._safe_float(row.get("total_debit"), 0.0),
    )

    journal_lines: list[dict[str, Any]] = []
    for line in row.get("journal_lines") or []:
        if not isinstance(line, dict):
            continue
        journal_lines.append(
            {
                "account_id": mandir_router._safe_optional_int(line.get("account_id")),
                "account_code": str(line.get("account_code") or "").strip(),
                "account_name": str(line.get("account_name") or "").strip(),
                "debit_amount": mandir_router._safe_float(line.get("debit_amount"), 0.0),
                "credit_amount": mandir_router._safe_float(line.get("credit_amount"), 0.0),
                "description": str(line.get("description") or "").strip(),
            }
        )
    row["journal_lines"] = journal_lines
    return row



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Journal entries (GET / POST / drilldown / financial reports / day-book / cash-book / bank-book)
# ROUTES : GET /journal-entries  POST .../journal-entries  GET .../reports/drilldown|balance-sheet|accounts-receivable|payable|ledger|category-income|top-donors|day-book|cash-book|bank-book
# ════════════════════════════════════════════════════════════════════════

@router.get("/journal-entries")
@router.get("/journal-entries/")
async def mandir_journal_entries(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if reference_type:
        query["reference_type"] = str(reference_type).strip().lower()

    try:
        docs = await mandir_router.get_collection("mandir_journal_entries").find(query).sort("updated_at", -1).limit(limit).to_list(length=limit)
    except Exception:
        docs = []

    rows: list[dict[str, Any]] = []
    for doc in docs:
        view = mandir_router._mandir_journal_entry_view(doc)
        entry_date = mandir_router._parse_journal_entry_date(view.get("entry_date"))
        if from_date and entry_date < from_date:
            continue
        if to_date and entry_date > to_date:
            continue
        rows.append(view)

    if rows:
        return rows

    # Backward-compatible fallback: expose posted SQL journals in the same list shape.
    report = await mandir_router.journal_entries_report(session, tenant_id=tenant_id, limit=limit)
    fallback_rows: list[dict[str, Any]] = []
    for item in report.get("items", []):
        entry_date = mandir_router._parse_journal_entry_date(item.get("entry_date"))
        if from_date and entry_date < from_date:
            continue
        if to_date and entry_date > to_date:
            continue
        fallback_reference_type = str(item.get("reference") or "").split("-", 1)[0].lower() or None
        if reference_type and fallback_reference_type != str(reference_type).strip().lower():
            continue

        fallback_rows.append(
            {
                "id": int(item.get("id")),
                "entry_number": f"JE-{item.get('id')}",
                "entry_date": entry_date.isoformat(),
                "narration": str(item.get("description") or "").strip(),
                "reference_type": fallback_reference_type,
                "reference_id": None,
                "status": "posted",
                "total_amount": mandir_router._safe_float(item.get("total_debit"), 0.0),
                "total_debit": mandir_router._safe_float(item.get("total_debit"), 0.0),
                "total_credit": mandir_router._safe_float(item.get("total_credit"), 0.0),
                "journal_lines": [],
            }
        )

    return fallback_rows


@router.post("/journal-entries", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/journal-entries/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_create_journal_entry(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry creation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    normalized_lines, total_debit, total_credit = await mandir_router._normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=payload.get("journal_lines"),
    )
    await mandir_router._validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    entry_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    entry_date = mandir_router._parse_journal_entry_date(payload.get("entry_date"))
    entry_number = await mandir_router._next_journal_entry_number(tenant_id=tenant_id, app_key=app_key)

    entry_doc = {
        "id": entry_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "entry_number": entry_number,
        "entry_date": entry_date.isoformat(),
        "narration": str(payload.get("narration") or "").strip(),
        "reference_type": str(payload.get("reference_type") or "expense").strip().lower(),
        "reference_id": mandir_router._safe_optional_int(payload.get("reference_id")),
        "status": "draft",
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "idempotency_key": f"man_je_{entry_id}",
        "created_by": str(current_user.get("sub") or current_user.get("email") or "system"),
        "created_at": now,
        "updated_at": now,
    }

    await mandir_router.get_collection("mandir_journal_entries").insert_one(entry_doc)
    return mandir_router._mandir_journal_entry_view(entry_doc)


@router.put("/journal-entries/{entry_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_update_journal_entry(
    entry_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry update",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    collection = mandir_router.get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if str(existing.get("status") or "").lower() != "draft":
        raise HTTPException(status_code=400, detail="Only draft entries can be edited")

    normalized_lines, total_debit, total_credit = await mandir_router._normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=payload.get("journal_lines"),
    )
    await mandir_router._validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    patch = {
        "entry_date": mandir_router._parse_journal_entry_date(payload.get("entry_date") or existing.get("entry_date")).isoformat(),
        "narration": str(payload.get("narration") or "").strip(),
        "reference_type": str(payload.get("reference_type") or existing.get("reference_type") or "expense").strip().lower(),
        "reference_id": mandir_router._safe_optional_int(payload.get("reference_id")),
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    updated = {**existing, **patch}
    return mandir_router._mandir_journal_entry_view(updated)


@router.post("/journal-entries/{entry_id}/post", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_post_journal_entry(
    entry_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry posting",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    collection = mandir_router.get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if str(existing.get("status") or "").lower() == "posted":
        return mandir_router._mandir_journal_entry_view(existing)

    if str(existing.get("status") or "").lower() in {"cancelled", "reversed"}:
        raise HTTPException(status_code=400, detail="Cancelled/reversed entries cannot be posted")

    normalized_lines, total_debit, total_credit = await mandir_router._normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=existing.get("journal_lines"),
    )
    await mandir_router._validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    post_lines: list[JournalLineIn] = []
    for line in normalized_lines:
        ledger_account_id = mandir_router._safe_optional_int(line.get("ledger_account_id"))
        if not ledger_account_id:
            account = await mandir_router._resolve_sql_account_for_journal_line(
                session,
                tenant_id=tenant_id,
                raw_account_id=line.get("account_id"),
            )
            if account is None:
                raise HTTPException(status_code=400, detail="Unable to resolve account while posting")
            ledger_account_id = int(account.id)

        post_lines.append(
            JournalLineIn(
                account_id=ledger_account_id,
                debit=Decimal(str(line.get("debit_amount") or 0)),
                credit=Decimal(str(line.get("credit_amount") or 0)),
            )
        )

    journal_payload = JournalPostRequest(
        entry_date=mandir_router._parse_journal_entry_date(existing.get("entry_date")),
        description=str(existing.get("narration") or "").strip(),
        reference=f"{str(existing.get('reference_type') or 'expense').upper()}-{str(existing.get('entry_number') or '')}",
        lines=post_lines,
    )

    try:
        posted_entry, _created = await mandir_router.post_journal_entry(
            session=session,
            tenant_id=tenant_id,
            created_by=str(current_user.get("sub") or current_user.get("email") or "system"),
            payload=journal_payload,
            idempotency_key=str(existing.get("idempotency_key") or f"man_je_{entry_id}"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to post journal entry: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "posted_journal_id": int(posted_entry.id),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    return mandir_router._mandir_journal_entry_view({**existing, **patch})


@router.post("/journal-entries/{entry_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_cancel_journal_entry(
    entry_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva booking",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    collection = mandir_router.get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    current_status = str(existing.get("status") or "").lower()
    if current_status in {"cancelled", "reversed"}:
        return mandir_router._mandir_journal_entry_view(existing)

    cancellation_reason = str((payload or {}).get("cancellation_reason") or "").strip() or "Reversal entry"

    if current_status == "draft":
        patch = {
            "status": "cancelled",
            "cancellation_reason": cancellation_reason,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await collection.update_one(
            {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
            {"$set": patch},
            upsert=False,
        )
        return mandir_router._mandir_journal_entry_view({**existing, **patch})

    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)
    normalized_lines, _total_debit, _total_credit = await mandir_router._normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=existing.get("journal_lines"),
    )

    reversal_lines: list[JournalLineIn] = []
    for line in normalized_lines:
        ledger_account_id = mandir_router._safe_optional_int(line.get("ledger_account_id"))
        if not ledger_account_id:
            account = await mandir_router._resolve_sql_account_for_journal_line(
                session,
                tenant_id=tenant_id,
                raw_account_id=line.get("account_id"),
            )
            if account is None:
                raise HTTPException(status_code=400, detail="Unable to resolve account while reversing")
            ledger_account_id = int(account.id)

        reversal_lines.append(
            JournalLineIn(
                account_id=ledger_account_id,
                debit=Decimal(str(line.get("credit_amount") or 0)),
                credit=Decimal(str(line.get("debit_amount") or 0)),
            )
        )

    reversal_payload = JournalPostRequest(
        entry_date=datetime.now(timezone.utc).date(),
        description=f"Reversal of {existing.get('entry_number')}: {cancellation_reason}",
        reference=f"REV-{existing.get('entry_number')}",
        lines=reversal_lines,
    )

    try:
        reversal_entry, _created = await mandir_router.post_journal_entry(
            session=session,
            tenant_id=tenant_id,
            created_by=str(current_user.get("sub") or current_user.get("email") or "system"),
            payload=reversal_payload,
            idempotency_key=f"{str(existing.get('idempotency_key') or f'man_je_{entry_id}')}_rev",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reverse journal entry: {exc}") from exc

    patch = {
        "status": "reversed",
        "cancellation_reason": cancellation_reason,
        "reversed_at": datetime.now(timezone.utc).isoformat(),
        "reversal_journal_id": int(reversal_entry.id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    return mandir_router._mandir_journal_entry_view({**existing, **patch})


@router.get("/journal-entries/reports/trial-balance")
async def mandir_journal_trial_balance(
    as_of: date,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    try:
        return await trial_balance_report(session, tenant_id=tenant_id, as_of=as_of)
    except (ConnectionRefusedError, OSError, SQLAlchemyError) as exc:
        mandir_router.logger.exception("Trial balance query failed", extra={"tenant_id": tenant_id, "as_of": as_of.isoformat()})
        raise HTTPException(status_code=503, detail="Accounting database unavailable. Please retry shortly.") from exc


@router.get("/journal-entries/reports/profit-loss")
async def mandir_journal_profit_loss(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await profit_loss_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/income-expenditure")
async def mandir_journal_income_expenditure(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await profit_loss_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/receipts-payments")
async def mandir_journal_receipts_payments(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await receipts_payments_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/drilldown")
async def mandir_journal_drilldown(
    from_date: date = Query(...),
    to_date: date = Query(...),
    level: str = Query(default="month", pattern="^(month|week|day|voucher)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    week_start: date | None = Query(default=None),
    day: date | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await get_journal_drilldown(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id="primary",
        from_date=from_date,
        to_date=to_date,
        level=level,
        month=month,
        week_start=week_start,
        day=day,
        limit=limit,
    )


@router.get("/journal-entries/reports/balance-sheet")
async def mandir_journal_balance_sheet(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await balance_sheet_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/accounts-receivable")
async def mandir_journal_accounts_receivable(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await accounts_receivable_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/accounts-payable")
async def mandir_journal_accounts_payable(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await accounts_payable_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/ledger/{account_id}")
async def mandir_journal_ledger(
    account_id: int,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await ledger_report(session, tenant_id=tenant_id, account_id=account_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/category-income")
async def mandir_journal_category_income(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await category_income_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/top-donors")
async def mandir_journal_top_donors(
    from_date: date = Query(...),
    to_date: date = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await top_donors_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date, limit=limit)


@router.get("/journal-entries/reports/day-book")
async def mandir_journal_day_book(
    date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await day_book_report(session, tenant_id=tenant_id, date_value=date)


@router.get("/journal-entries/reports/cash-book")
async def mandir_journal_cash_book(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await cash_book_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/bank-book/{account_id}")
async def mandir_journal_bank_book(
    account_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await bank_book_report(session, tenant_id=tenant_id, account_id=account_id, from_date=from_date, to_date=to_date)

