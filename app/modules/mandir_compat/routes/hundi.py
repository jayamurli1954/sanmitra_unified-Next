"""MandirMitra hundi master and opening workflow routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

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

@router.get("/hundi/masters")
async def mandir_hundi_masters(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi master listing"
    )
    return await mandir_router.get_collection("mandir_hundi_masters").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key, "active": True}
    ).sort("name", 1).to_list(length=500)


@router.post("/hundi/masters", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def create_mandir_hundi_master(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi master creation"
    )
    name = str(payload.get("name") or "").strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Hundi name is required")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid4()), "tenant_id": context.tenant_id, "app_key": context.app_key,
        "name": name, "location": mandir_router._safe_optional_str(payload.get("location")), "active": True,
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_hundi_masters").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.get("/hundi/openings")
async def mandir_hundi_openings(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi opening listing"
    )
    rows = await mandir_router.get_collection("mandir_hundi_openings").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("created_at", -1).to_list(length=500)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.post("/hundi/openings", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_mandir_hundi_opening(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi counting submission"
    )
    hundi_id = str(payload.get("hundi_id") or "").strip()
    master = await mandir_router.get_collection("mandir_hundi_masters").find_one(
        {"id": hundi_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "active": True}
    )
    if master is None:
        raise HTTPException(status_code=404, detail="Active hundi master not found")
    try:
        amount = Decimal(str(payload.get("amount") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid hundi amount is required") from exc
    if not amount.is_finite() or amount <= 0:
        raise HTTPException(status_code=400, detail="Hundi amount must be greater than zero")
    witness = str(payload.get("witness") or "").strip()
    if len(witness) < 2:
        raise HTTPException(status_code=400, detail="Counting witness is required")
    counted_on = str(payload.get("counted_on") or datetime.now(timezone.utc).date().isoformat()).strip()
    try:
        date.fromisoformat(counted_on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid hundi counting date is required") from exc
    opening_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "hundi_id": hundi_id, "hundi_name": master.get("name"), "amount": str(amount),
        "counted_on": counted_on, "witness": witness,
        "fund": mandir_router._safe_optional_str(payload.get("fund")), "festival": mandir_router._safe_optional_str(payload.get("festival")),
        "reference": f"HUN-{opening_id[:8].upper()}", "status": "pending_approval",
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_hundi_openings").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.post("/hundi/openings/{opening_id}/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_hundi_opening(
    opening_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi counting approval"
    )
    collection = mandir_router.get_collection("mandir_hundi_openings")
    query = {"id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Hundi opening not found")
    if existing.get("status") == "posted":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending hundi openings can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Maker and approver must be different users")
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    cash_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code="11002", name="Cash in Hand - Hundi", account_type="asset", classification="real"
    )
    income_account_id = await mandir_router._resolve_mandir_income_account(session, context.tenant_id, "Hundi Collections")
    amount = Decimal(str(existing["amount"]))
    journal, _created = await mandir_router.post_journal_entry(
        session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
        payload=JournalPostRequest(
            entry_date=date.fromisoformat(str(existing.get("counted_on"))),
            description=f"Hundi collection - {existing.get('hundi_name')}", reference=str(existing.get("reference")),
            lines=[
                JournalLineIn(account_id=cash_account_id, debit=amount, credit=Decimal("0")),
                JournalLineIn(account_id=income_account_id, debit=Decimal("0"), credit=amount),
            ],
        ),
        idempotency_key=f"hundi_{opening_id}",
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {"status": "posted", "approved_by": actor, "approved_at": now, "journal_entry_id": int(journal.id), "updated_at": now}
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
    except Exception as exc:
        await mandir_router.reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
            journal_id=int(journal.id), created_by=actor, reason="Compensate failed hundi approval persistence",
            idempotency_key=f"hundi_{opening_id}_approval_compensation",
        )
        raise HTTPException(status_code=500, detail="Hundi approval persistence failed; accounting was reversed") from exc
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/hundi/openings/{opening_id}/cancel", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cancel_mandir_hundi_opening(
    opening_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="hundi posting reversal"
    )
    collection = mandir_router.get_collection("mandir_hundi_openings")
    query = {"id": opening_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Hundi opening not found")
    if existing.get("status") == "reversed":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "posted":
        raise HTTPException(status_code=409, detail="Only posted hundi openings can be reversed")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reversal reason is required")
    reversal, _created = await mandir_router._reverse_mandir_source_journal(
        session, tenant_id=context.tenant_id, app_key=context.app_key, source_key=f"hundi_{opening_id}",
        reason=reason, current_user=current_user,
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {"status": "reversed", "reversal_journal_id": int(reversal.id), "reversal_reason": reason,
             "reversed_by": mandir_router._mandir_actor_id(current_user), "reversed_at": now, "updated_at": now}
    await collection.update_one(query, {"$set": patch}, upsert=False)
    return mandir_router._sanitize_mongo_doc({**existing, **patch})

