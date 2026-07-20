"""MandirMitra refund-request routes and helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Registered on the shared ``router`` from ``app.modules.mandir_compat.router``.
Uses runtime lookup on the router module for get_collection and shared helpers
so existing tests that monkeypatch mandir_router keep working.
"""
from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.audit.service import log_audit_event
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

_logger = logging.getLogger(__name__)


def _mandir_refund_source_spec(source_kind: str) -> tuple[str, str, str, str]:
    normalized = str(source_kind or "").strip().lower()
    if normalized == "donation":
        return "mandir_donations", "donation_id", "don_", "amount"
    if normalized == "seva":
        return "mandir_seva_bookings", "id", "sev_", "amount_paid"
    raise HTTPException(status_code=400, detail="source_kind must be donation or seva")


async def _mandir_refund_source(
    *, tenant_id: str, app_key: str, source_kind: str, source_id: str,
    allow_reversed: bool = False,
) -> tuple[dict[str, Any], str, str, str, str]:
    collection_name, id_field, idempotency_prefix, amount_field = _mandir_refund_source_spec(source_kind)
    source = await mandir_router.get_collection(collection_name).find_one({
        id_field: source_id, "tenant_id": tenant_id, "app_key": app_key,
    })
    if source is None:
        raise HTTPException(status_code=404, detail="Refund source receipt not found")
    if not allow_reversed and str(source.get("status") or "").lower() in {"cancelled", "reversed"}:
        raise HTTPException(status_code=409, detail="Receipt is already reversed")
    if source_kind == "donation":
        if str(source.get("donation_type") or "cash").lower() != "cash":
            raise HTTPException(status_code=409, detail="In-kind donations cannot enter the cash refund workflow")
        if not allow_reversed and str(source.get("status") or "").lower() != "posted":
            raise HTTPException(status_code=409, detail="Only posted cash donations can enter the refund workflow")
    elif str(source.get("payment_status") or "").lower() != "paid":
        raise HTTPException(status_code=409, detail="Only paid seva receipts can enter the refund workflow")
    return source, collection_name, id_field, idempotency_prefix, amount_field


async def _audit_mandir_refund_event(
    *, tenant_id: str, app_key: str, actor: str, action: str,
    request_id: str, old_status: str | None, new_status: str,
) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id, user_id=actor, product=app_key, action=action,
            entity_type="mandir_refund_request", entity_id=request_id,
            old_value={"status": old_status}, new_value={"status": new_status},
        )
    except Exception:
        _logger.warning("Failed to write refund audit event action=%s request=%s", action, request_id, exc_info=True)


@router.get("/refund-requests", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def list_mandir_refund_requests(
    status: str | None = Query(default=None),
    source_kind: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund request listing",
    )
    query: dict[str, Any] = {"tenant_id": context.tenant_id, "app_key": context.app_key}
    if status:
        query["status"] = str(status).strip().lower()
    if source_kind:
        normalized_kind = str(source_kind).strip().lower()
        _mandir_refund_source_spec(normalized_kind)
        query["source_kind"] = normalized_kind
    rows = await mandir_router.get_collection("mandir_refund_requests").find(query).sort("created_at", -1).to_list(
        length=offset + limit
    )
    return [mandir_router._sanitize_mongo_doc(row) for row in rows[offset:offset + limit]]


@router.post("/refund-requests", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_mandir_refund_request(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund request submission",
    )
    source_kind = str(payload.get("source_kind") or "").strip().lower()
    source_id = str(payload.get("source_id") or "").strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id is required")
    source, _collection_name, _id_field, _prefix, amount_field = await _mandir_refund_source(
        tenant_id=context.tenant_id, app_key=context.app_key,
        source_kind=source_kind, source_id=source_id,
    )
    source_amount = Decimal(str(source.get(amount_field) or "0")).quantize(Decimal("0.01"))
    try:
        requested_amount = Decimal(str(payload.get("amount") or source_amount)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid refund amount is required") from exc
    if not requested_amount.is_finite() or requested_amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be greater than zero")
    if requested_amount != source_amount:
        raise HTTPException(status_code=409, detail="Only a full receipt refund is supported")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Refund reason is required")
    collection = mandir_router.get_collection("mandir_refund_requests")
    existing_rows = await collection.find({
        "tenant_id": context.tenant_id, "app_key": context.app_key,
        "source_kind": source_kind, "source_id": source_id,
    }).to_list(length=100)
    active_statuses = {"pending_approval", "approved_pending_settlement", "settled"}
    if any(str(row.get("status") or "") in active_statuses for row in existing_rows):
        raise HTTPException(status_code=409, detail="This receipt already has an active refund request")
    request_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": request_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "source_kind": source_kind, "source_id": source_id,
        "receipt_number": str(source.get("receipt_number") or source.get("booking_number") or ""),
        "amount": str(requested_amount), "currency": str(source.get("currency") or "INR"),
        "reason": reason, "requested_refund_mode": mandir_router._safe_optional_str(payload.get("refund_mode")),
        "reference": f"RFD-{request_id[:8].upper()}", "status": "pending_approval",
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await collection.insert_one(doc)
    await _audit_mandir_refund_event(
        tenant_id=context.tenant_id, app_key=context.app_key, actor=str(doc["created_by"]),
        action="refund_requested", request_id=request_id, old_status=None, new_status="pending_approval",
    )
    return mandir_router._sanitize_mongo_doc(doc)


@router.post("/refund-requests/{request_id}/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_refund_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund request approval",
    )
    collection = mandir_router.get_collection("mandir_refund_requests")
    query = {"id": request_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if existing.get("status") == "approved_pending_settlement":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending refund requests can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Refund maker and approver must be different users")
    await _mandir_refund_source(
        tenant_id=context.tenant_id, app_key=context.app_key,
        source_kind=str(existing["source_kind"]), source_id=str(existing["source_id"]),
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "approved_pending_settlement", "approved_by": actor,
        "approved_at": now, "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    await _audit_mandir_refund_event(
        tenant_id=context.tenant_id, app_key=context.app_key, actor=actor,
        action="refund_approved", request_id=request_id,
        old_status=str(existing.get("status") or ""), new_status=str(patch["status"]),
    )
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/refund-requests/{request_id}/reject", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def reject_mandir_refund_request(
    request_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund request rejection",
    )
    collection = mandir_router.get_collection("mandir_refund_requests")
    query = {"id": request_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if existing.get("status") == "rejected":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending refund requests can be rejected")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Refund maker and reviewer must be different users")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "rejected", "rejected_by": actor, "rejected_at": now,
        "rejection_reason": reason, "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    await _audit_mandir_refund_event(
        tenant_id=context.tenant_id, app_key=context.app_key, actor=actor,
        action="refund_rejected", request_id=request_id,
        old_status=str(existing.get("status") or ""), new_status=str(patch["status"]),
    )
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/refund-requests/{request_id}/settle", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def settle_mandir_refund_request(
    request_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund settlement",
    )
    collection = mandir_router.get_collection("mandir_refund_requests")
    query = {"id": request_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if existing.get("status") == "settled":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "approved_pending_settlement":
        raise HTTPException(status_code=409, detail="Only approved refund requests can be settled")
    refund_mode = str(payload.get("refund_mode") or existing.get("requested_refund_mode") or "").strip()
    refund_reference = str(payload.get("refund_reference") or "").strip()
    if len(refund_mode) < 2:
        raise HTTPException(status_code=400, detail="Refund payment mode is required")
    if len(refund_reference) < 3:
        raise HTTPException(status_code=400, detail="Refund settlement reference is required")
    settlement_date = str(payload.get("settlement_date") or datetime.now(timezone.utc).date().isoformat()).strip()
    try:
        parsed_settlement_date = date.fromisoformat(settlement_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid settlement_date is required") from exc
    if parsed_settlement_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Settlement date cannot be in the future")
    source_kind = str(existing["source_kind"])
    source_id = str(existing["source_id"])
    source, collection_name, id_field, prefix, _amount_field = await _mandir_refund_source(
        tenant_id=context.tenant_id, app_key=context.app_key,
        source_kind=source_kind, source_id=source_id, allow_reversed=True,
    )
    if str(source.get("status") or "").lower() in {"cancelled", "reversed"}:
        if str(source.get("refund_reference") or "") != refund_reference:
            raise HTTPException(status_code=409, detail="Receipt was reversed outside this refund settlement")
    cancelled = await mandir_router._cancel_mandir_receipt_source(
        source_kind=source_kind, source_id=source_id, collection_name=collection_name,
        id_field=id_field, idempotency_prefix=prefix,
        payload={
            "reason": str(existing["reason"]), "refund_mode": refund_mode,
            "refund_reference": refund_reference, "refund_date": settlement_date,
        },
        session=session, current_user=current_user,
        x_tenant_id=x_tenant_id, x_app_key=x_app_key,
    )
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "settled", "settled_by": mandir_router._mandir_actor_id(current_user), "settled_at": now,
        "settlement_date": settlement_date, "refund_mode": refund_mode,
        "refund_reference": refund_reference,
        "reversal_journal_id": cancelled.get("reversal_journal_id"), "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    await _audit_mandir_refund_event(
        tenant_id=context.tenant_id, app_key=context.app_key, actor=str(patch["settled_by"]),
        action="refund_settled", request_id=request_id,
        old_status=str(existing.get("status") or ""), new_status=str(patch["status"]),
    )
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


async def _mandir_refund_report_rows(
    *, tenant_id: str, app_key: str, from_date: date, to_date: date,
) -> list[dict[str, Any]]:
    rows = await mandir_router.get_collection("mandir_refund_requests").find({
        "tenant_id": tenant_id, "app_key": app_key,
    }).to_list(length=5000)
    result = []
    for row in rows:
        created_at = mandir_router._parse_iso_datetime(row.get("created_at"))
        if created_at is None or not (from_date <= created_at.date() <= to_date):
            continue
        result.append(mandir_router._sanitize_mongo_doc(row))
    result.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return result


@router.get("/reports/refunds", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_report_refunds(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund reporting",
    )
    rows = await _mandir_refund_report_rows(
        tenant_id=context.tenant_id, app_key=context.app_key, from_date=from_date, to_date=to_date,
    )
    totals: dict[str, Decimal] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        totals[status] = totals.get(status, Decimal("0")) + Decimal(str(row.get("amount") or "0"))
    return {
        "from_date": from_date.isoformat(), "to_date": to_date.isoformat(), "items": rows,
        "count": len(rows), "amount_by_status": {key: float(value) for key, value in sorted(totals.items())},
    }


@router.get("/reports/refunds/export.csv", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_export_refunds_csv(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="refund report export",
    )
    rows = await _mandir_refund_report_rows(
        tenant_id=context.tenant_id, app_key=context.app_key, from_date=from_date, to_date=to_date,
    )
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "refund_reference", "receipt_number", "source_kind", "amount", "currency", "status",
        "reason", "refund_mode", "settlement_reference", "settlement_date", "reversal_journal_id",
    ])
    for row in rows:
        writer.writerow([
            row.get("reference"), row.get("receipt_number"), row.get("source_kind"), row.get("amount"),
            row.get("currency"), row.get("status"), row.get("reason"), row.get("refund_mode"),
            row.get("refund_reference"), row.get("settlement_date"), row.get("reversal_journal_id"),
        ])
    return Response(
        content=output.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="mandir_refunds_{from_date}_{to_date}.csv"'},
    )
