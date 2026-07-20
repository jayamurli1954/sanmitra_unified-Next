"""MandirMitra fund master, transfers, and opening balance routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

logger = logging.getLogger(__name__)

@router.get("/funds")
async def list_mandir_funds(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund listing"
    )
    rows = await mandir_router.get_collection("mandir_funds").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("name", 1).to_list(length=500)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.post("/funds", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def create_mandir_fund(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund creation"
    )
    name = str(payload.get("name") or "").strip()
    fund_type = str(payload.get("fund_type") or "restricted").strip().lower()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Fund name is required")
    if fund_type not in {"general", "restricted", "corpus"}:
        raise HTTPException(status_code=400, detail="fund_type must be general, restricted, or corpus")
    now = datetime.now(timezone.utc).isoformat()
    fund_id = str(uuid4())
    actor = mandir_router._mandir_actor_id(current_user)
    try:
        dimension = await mandir_router.create_dimension(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id="primary",
            payload={
                "dimension_type": "cost_centre",
                "code": f"MF-{fund_id[:8].upper()}",
                "name": f"Mandir fund - {name}",
            },
            created_by=actor,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to provision fund accounting dimension") from exc
    doc = {
        "id": fund_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "name": name, "fund_type": fund_type, "active": True,
        "accounting_dimension_id": str(dimension["dimension_id"]),
        "created_by": actor, "created_at": now, "updated_at": now,
    }
    try:
        await mandir_router.get_collection("mandir_funds").insert_one(doc)
    except Exception as exc:
        try:
            await mandir_router.deactivate_dimension(
                tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
                dimension_id=str(dimension["dimension_id"]), updated_by=actor,
            )
        except Exception:
            logger.exception("Failed to deactivate orphaned Mandir fund dimension tenant=%s", context.tenant_id)
        raise HTTPException(status_code=500, detail="Failed to save fund master") from exc
    return mandir_router._sanitize_mongo_doc(doc)


@router.get("/fund-transfers")
async def list_mandir_fund_transfers(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund transfer listing"
    )
    rows = await mandir_router.get_collection("mandir_fund_transfers").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("created_at", -1).to_list(length=500)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.get("/fund-opening-balances")
async def list_mandir_fund_opening_balances(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund opening balance listing",
    )
    rows = await mandir_router.get_collection("mandir_fund_opening_balances").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("opening_date", -1).to_list(length=500)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.post("/fund-opening-balances", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_mandir_fund_opening_balance(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund opening balance submission",
    )
    fund_id = str(payload.get("fund_id") or "").strip()
    fund = await mandir_router.get_collection("mandir_funds").find_one({
        "id": fund_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "active": True,
    })
    if fund is None or not fund.get("accounting_dimension_id"):
        raise HTTPException(status_code=404, detail="Active accounting-enabled fund not found")
    try:
        amount = Decimal(str(payload.get("amount") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid opening balance amount is required") from exc
    if not amount.is_finite() or amount <= 0:
        raise HTTPException(status_code=400, detail="Opening balance amount must be greater than zero")
    opening_date = str(payload.get("opening_date") or "").strip()
    try:
        parsed_opening_date = date.fromisoformat(opening_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid opening_date is required") from exc
    if parsed_opening_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Opening balance date cannot be in the future")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Opening balance reason is required")
    existing_rows = await mandir_router.get_collection("mandir_fund_opening_balances").find({
        "tenant_id": context.tenant_id, "app_key": context.app_key, "fund_id": fund_id,
    }).to_list(length=100)
    if any(str(row.get("status") or "") in {"pending_approval", "posted"} for row in existing_rows):
        raise HTTPException(status_code=409, detail="This fund already has an active opening balance")
    opening_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "fund_id": fund_id, "fund_name": fund.get("name"),
        "fund_dimension_id": str(fund["accounting_dimension_id"]),
        "amount": str(amount), "opening_date": opening_date, "reason": reason,
        "reference": f"FOB-{opening_id[:8].upper()}", "status": "pending_approval",
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_fund_opening_balances").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.post("/fund-opening-balances/{opening_id}/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_fund_opening_balance(
    opening_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund opening balance approval",
    )
    collection = mandir_router.get_collection("mandir_fund_opening_balances")
    query = {"id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Fund opening balance not found")
    if existing.get("status") == "posted":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending opening balances can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Opening balance maker and approver must be different users")
    fund = await mandir_router.get_collection("mandir_funds").find_one({
        "id": str(existing.get("fund_id") or ""), "tenant_id": context.tenant_id,
        "app_key": context.app_key, "active": True,
    })
    if fund is None or str(fund.get("accounting_dimension_id") or "") != str(existing.get("fund_dimension_id") or ""):
        raise HTTPException(status_code=409, detail="Fund accounting dimension is no longer active")
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    opening_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code="33001", name="Opening Balance",
        account_type="equity", classification="real",
    )
    reserve_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code="32001", name="General Reserve",
        account_type="equity", classification="real",
    )
    amount = Decimal(str(existing["amount"]))
    journal, _created = await mandir_router.post_journal_entry(
        session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
        payload=JournalPostRequest(
            entry_date=date.fromisoformat(str(existing["opening_date"])),
            description=f"Fund opening balance: {existing.get('fund_name')}",
            reference=str(existing["reference"]), source_module="mandirmitra",
            source_document_type="fund_opening_balance", source_document_id=opening_id,
            lines=[
                JournalLineIn(account_id=opening_account_id, debit=amount, credit=Decimal("0")),
                JournalLineIn(
                    account_id=reserve_account_id, debit=Decimal("0"), credit=amount,
                    cost_center_id=str(existing["fund_dimension_id"]),
                ),
            ],
        ),
        idempotency_key=f"fund_opening_balance_{opening_id}",
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "posted", "approved_by": actor, "approved_at": now,
        "journal_entry_id": int(journal.id), "updated_at": now,
    }
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
    except Exception as exc:
        await mandir_router.reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id="primary", journal_id=int(journal.id), created_by=actor,
            reason="Compensate failed fund opening balance persistence",
            idempotency_key=f"fund_opening_balance_{opening_id}_approval_compensation",
        )
        raise HTTPException(status_code=500, detail="Opening balance persistence failed; accounting was reversed") from exc
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/fund-opening-balances/{opening_id}/cancel", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cancel_mandir_fund_opening_balance(
    opening_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="fund opening balance reversal",
    )
    collection = mandir_router.get_collection("mandir_fund_opening_balances")
    query = {"id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Fund opening balance not found")
    if existing.get("status") == "reversed":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "posted":
        raise HTTPException(status_code=409, detail="Only posted opening balances can be reversed")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reversal reason is required")
    reversal, _created = await mandir_router._reverse_mandir_source_journal(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        source_key=f"fund_opening_balance_{opening_id}", reason=reason, current_user=current_user,
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "reversed", "reversal_journal_id": int(reversal.id), "reversal_reason": reason,
        "reversed_by": mandir_router._mandir_actor_id(current_user), "reversed_at": now, "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/fund-transfers", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_mandir_fund_transfer(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund transfer submission"
    )
    from_fund_id = str(payload.get("from_fund_id") or "").strip()
    to_fund_id = str(payload.get("to_fund_id") or "").strip()
    if not from_fund_id or not to_fund_id or from_fund_id == to_fund_id:
        raise HTTPException(status_code=400, detail="Distinct source and destination funds are required")
    fund_collection = mandir_router.get_collection("mandir_funds")
    scope = {"tenant_id": context.tenant_id, "app_key": context.app_key, "active": True}
    from_fund = await fund_collection.find_one({**scope, "id": from_fund_id})
    to_fund = await fund_collection.find_one({**scope, "id": to_fund_id})
    if from_fund is None or to_fund is None:
        raise HTTPException(status_code=404, detail="Active source or destination fund not found")
    if not from_fund.get("accounting_dimension_id") or not to_fund.get("accounting_dimension_id"):
        raise HTTPException(status_code=409, detail="Both funds must have accounting dimensions before transfer")
    try:
        amount = Decimal(str(payload.get("amount") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid transfer amount is required") from exc
    if not amount.is_finite() or amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero")
    transfer_date = str(payload.get("transfer_date") or datetime.now(timezone.utc).date().isoformat()).strip()
    try:
        date.fromisoformat(transfer_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid transfer_date is required") from exc
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Transfer reason is required")
    transfer_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": transfer_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "from_fund_id": from_fund_id, "from_fund_name": from_fund.get("name"),
        "from_dimension_id": from_fund.get("accounting_dimension_id"),
        "to_fund_id": to_fund_id, "to_fund_name": to_fund.get("name"),
        "to_dimension_id": to_fund.get("accounting_dimension_id"),
        "amount": str(amount), "transfer_date": transfer_date, "reason": reason,
        "reference": f"FTR-{transfer_id[:8].upper()}", "status": "pending_approval",
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_fund_transfers").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.post("/fund-transfers/{transfer_id}/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_fund_transfer(
    transfer_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund transfer approval"
    )
    collection = mandir_router.get_collection("mandir_fund_transfers")
    query = {"id": transfer_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Fund transfer not found")
    if existing.get("status") == "posted":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending fund transfers can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Maker and approver must be different users")
    transfer_day = date.fromisoformat(str(existing["transfer_date"]))
    balance_report = await mandir_router._mandir_fund_subledger_data(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=date(1900, 1, 1), to_date=transfer_day,
    )
    source_row = next(
        (row for row in balance_report["items"] if row["fund_id"] == str(existing.get("from_fund_id") or "")),
        None,
    )
    available = Decimal(str(source_row.get("closing_balance") if source_row else "0"))
    amount = Decimal(str(existing["amount"]))
    if available < amount:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient source fund balance; available amount is {available.quantize(Decimal('0.01'))}",
        )
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    control_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code="32001", name="General Reserve", account_type="equity", classification="real"
    )
    journal, _created = await mandir_router.post_journal_entry(
        session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
        payload=JournalPostRequest(
            entry_date=date.fromisoformat(str(existing["transfer_date"])),
            description=f"Fund transfer: {existing.get('from_fund_name')} to {existing.get('to_fund_name')}",
            reference=str(existing["reference"]), source_module="mandirmitra",
            source_document_type="fund_transfer", source_document_id=transfer_id,
            lines=[
                JournalLineIn(
                    account_id=control_account_id, debit=amount, credit=Decimal("0"),
                    cost_center_id=str(existing["from_dimension_id"]),
                ),
                JournalLineIn(
                    account_id=control_account_id, debit=Decimal("0"), credit=amount,
                    cost_center_id=str(existing["to_dimension_id"]),
                ),
            ],
        ),
        idempotency_key=f"fund_transfer_{transfer_id}",
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "posted", "approved_by": actor, "approved_at": now,
        "journal_entry_id": int(journal.id), "updated_at": now,
    }
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
    except Exception as exc:
        await mandir_router.reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
            journal_id=int(journal.id), created_by=actor, reason="Compensate failed fund transfer persistence",
            idempotency_key=f"fund_transfer_{transfer_id}_approval_compensation",
        )
        raise HTTPException(status_code=500, detail="Fund transfer persistence failed; accounting was reversed") from exc
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/fund-transfers/{transfer_id}/cancel", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cancel_mandir_fund_transfer(
    transfer_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="fund transfer reversal"
    )
    collection = mandir_router.get_collection("mandir_fund_transfers")
    query = {"id": transfer_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Fund transfer not found")
    if existing.get("status") == "reversed":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "posted":
        raise HTTPException(status_code=409, detail="Only posted fund transfers can be reversed")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reversal reason is required")
    reversal, _created = await mandir_router._reverse_mandir_source_journal(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        source_key=f"fund_transfer_{transfer_id}", reason=reason, current_user=current_user,
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "reversed", "reversal_journal_id": int(reversal.id), "reversal_reason": reason,
        "reversed_by": mandir_router._mandir_actor_id(current_user), "reversed_at": now, "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


