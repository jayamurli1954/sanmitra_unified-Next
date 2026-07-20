"""MandirMitra UPI config, intent, and quick-log routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

def _mandir_upi_config_view(doc: dict[str, Any], temple_id: int) -> dict[str, Any]:
    upi_id = str(doc.get("upi_id") or "").strip()
    payee_name = str(doc.get("upi_payee_name") or doc.get("trust_name") or doc.get("temple_name") or doc.get("name") or "Temple").strip()
    currency = str(doc.get("upi_currency") or "INR").strip().upper() or "INR"
    return {
        "temple_id": int(temple_id),
        "upi_public_enabled": bool(doc.get("upi_public_enabled", False)),
        "upi_id": upi_id,
        "upi_payee_name": payee_name,
        "upi_currency": currency,
        "upi_qr_note": str(doc.get("upi_qr_note") or "").strip() or None,
        "qr_code_image_url": str(doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": str(doc.get("admin_whatsapp") or "").strip() or None,
    }
@router.get("/upi-payments/config")
async def mandir_upi_payments_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await mandir_router.ensure_temple_numeric_id(tenant_id, app_key=app_key)
    doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return _mandir_upi_config_view(doc, assigned_temple_id)


@router.put("/upi-payments/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_upi_payments_config_update(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await mandir_router.ensure_temple_numeric_id(tenant_id, app_key=app_key)

    upi_id = str(payload.get("upi_id") or "").strip().lower()
    upi_payee_name = str(payload.get("upi_payee_name") or "").strip()
    upi_qr_note = str(payload.get("upi_qr_note") or "").strip()
    upi_currency = str(payload.get("upi_currency") or "INR").strip().upper() or "INR"

    update = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "id": assigned_temple_id,
        "temple_id": assigned_temple_id,
    }
    if "upi_public_enabled" in payload:
        update["upi_public_enabled"] = bool(payload.get("upi_public_enabled"))
    if "upi_id" in payload:
        update["upi_id"] = upi_id or None
    if "upi_payee_name" in payload:
        update["upi_payee_name"] = upi_payee_name or None
    if "upi_qr_note" in payload:
        update["upi_qr_note"] = upi_qr_note or None
    if "upi_currency" in payload:
        update["upi_currency"] = upi_currency
    if "qr_code_image_url" in payload:
        update["qr_code_image_url"] = str(payload.get("qr_code_image_url") or "").strip() or None
    if "admin_whatsapp" in payload:
        update["admin_whatsapp"] = str(payload.get("admin_whatsapp") or "").strip() or None

    col = mandir_router.get_collection("mandir_temples")
    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": update,
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )
    doc = await col.find_one({"tenant_id": tenant_id}) or {}
    return _mandir_upi_config_view(doc, assigned_temple_id)


@router.get("/public/temples/{temple_id}/upi-intent")
async def mandir_public_upi_intent(
    temple_id: int,
    amount: float | None = Query(default=None, ge=0),
    purpose: str | None = Query(default=None),
    reference: str | None = Query(default=None),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    temples = mandir_router.get_collection("mandir_temples")
    temple_doc = await temples.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not temple_doc:
        temple_doc = await temples.find_one({"tenant_id": tenant_id}) or {}

    if not bool(temple_doc.get("upi_public_enabled", False)):
        raise HTTPException(status_code=404, detail="Public UPI is not enabled for this temple")

    upi_id = str(temple_doc.get("upi_id") or "").strip().lower()
    if not upi_id:
        raise HTTPException(status_code=404, detail="Temple UPI ID is not configured")

    payee_name = str(
        temple_doc.get("upi_payee_name")
        or temple_doc.get("trust_name")
        or temple_doc.get("temple_name")
        or temple_doc.get("name")
        or "Temple"
    ).strip()
    currency = str(temple_doc.get("upi_currency") or "INR").strip().upper() or "INR"
    note_text = str(purpose or temple_doc.get("upi_qr_note") or "Temple Offering").strip()
    reference_text = str(reference or "").strip() or None

    intent_uri = mandir_router._build_upi_intent_uri(
        upi_id=upi_id,
        payee_name=payee_name,
        amount=amount,
        note=note_text,
        reference=reference_text,
        currency=currency,
    )

    return {
        "temple_id": temple_id,
        "upi_id": upi_id,
        "payee_name": payee_name,
        "currency": currency,
        "amount": amount,
        "purpose": note_text,
        "reference": reference_text,
        "intent_uri": intent_uri,
        "qr_payload": intent_uri,
    }
@router.get("/upi-payments")
async def mandir_upi_payments(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    rows = await mandir_router.get_collection("mandir_upi_payments").find({"tenant_id": tenant_id, "app_key": app_key}).sort("payment_datetime", -1).limit(limit).to_list(length=limit)

    filtered: list[dict[str, Any]] = []
    for row in rows:
        parsed = mandir_router._parse_iso_datetime(row.get("payment_datetime") or row.get("created_at"))
        if parsed is not None:
            row_date = parsed.date()
            if from_date and row_date < from_date:
                continue
            if to_date and row_date > to_date:
                continue
        filtered.append(row)

    filtered.sort(key=lambda item: str(item.get("payment_datetime") or item.get("created_at") or ""), reverse=True)
    return [mandir_router._mandir_upi_payment_view(row) for row in filtered]


@router.post("/upi-payments/quick-log", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_upi_quick_log(
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
        operation="UPI quick log",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    amount = mandir_router._safe_float(payload.get("amount"), 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    purpose = str(payload.get("payment_purpose") or "DONATION").strip().upper()
    payment_dt = mandir_router._parse_iso_datetime(payload.get("payment_datetime")) or datetime.now(timezone.utc)
    payment_datetime = payment_dt.isoformat()

    normalized_phone = mandir_router._normalize_phone(payload.get("devotee_phone") or payload.get("sender_phone") or payload.get("phone"))
    devotee_name = str(payload.get("devotee_name") or payload.get("sender_name") or "").strip() or "Walk-in Devotee"
    sender_upi_id = str(payload.get("sender_upi_id") or "").strip() or None
    upi_reference_number = str(payload.get("upi_reference_number") or "").strip() or None
    notes = str(payload.get("notes") or "").strip() or None

    col = mandir_router.get_collection("mandir_upi_payments")
    if upi_reference_number:
        existing = await col.find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "upi_reference_number": upi_reference_number,
            }
        )
        if existing is not None:
            return mandir_router._mandir_upi_payment_view(existing)

    source_record: dict[str, Any]
    source_type: str
    source_id: str | None

    if purpose == "SEVA":
        seva_payload = {
            **payload,
            "amount_paid": amount,
            "payment_mode": "UPI",
            "devotee_name": devotee_name,
            "devotee_names": str(payload.get("devotee_names") or devotee_name),
            "devotee_phone": normalized_phone,
            "devotee_mobile": normalized_phone,
            "booking_date": str(payload.get("booking_date") or payment_dt.date().isoformat()),
            "seva_name": str(payload.get("seva_name") or "Seva Booking"),
        }
        source_record = await mandir_router.create_seva_booking(
            payload=seva_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        source_type = "seva"
        source_id = str(source_record.get("id") or "").strip() or None
    else:
        donation_category_map = {
            "ANNADANA": "Annadanam",
            "ANNADANAM": "Annadanam",
            "SPONSORSHIP": "Sponsorship",
            "OTHER": "General Donation",
            "DONATION": "General Donation",
        }
        donation_payload = {
            **payload,
            "amount": amount,
            "payment_mode": "UPI",
            "category": str(payload.get("category") or donation_category_map.get(purpose, "General Donation")),
            "devotee_name": devotee_name,
            "devotee_phone": normalized_phone,
            "phone": normalized_phone,
        }
        source_record = await mandir_router.create_donation(
            payload=donation_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        source_type = "donation"
        source_id = str(source_record.get("donation_id") or source_record.get("id") or "").strip() or None

    row_id = str(uuid4())
    receipt_number = str(source_record.get("receipt_number") or mandir_router._upi_receipt_number({"id": row_id})).strip()
    now = datetime.now(timezone.utc).isoformat()
    payment_row = {
        "id": row_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": amount,
        "payment_datetime": payment_datetime,
        "payment_mode": "UPI",
        "payment_purpose": purpose,
        "devotee_name": devotee_name,
        "devotee_phone": normalized_phone,
        "sender_phone": normalized_phone,
        "sender_upi_id": sender_upi_id,
        "upi_reference_number": upi_reference_number,
        "notes": notes,
        "source_type": source_type,
        "source_id": source_id,
        "receipt_number": receipt_number,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(payment_row)

    return mandir_router._mandir_upi_payment_view(payment_row)

