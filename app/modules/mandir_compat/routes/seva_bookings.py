"""MandirMitra seva booking routes (create, list, receipt PDF, cancel, reschedule).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

@router.post("/sevas/bookings", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/sevas/bookings/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_seva_booking(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = mandir_router.resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva booking",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    booking_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    amount = mandir_router._safe_float(payload.get("amount_paid") or payload.get("amount"), 0.0)
    payment_mode = str(payload.get("payment_mode") or payload.get("payment_method") or "Cash")
    seva_id = payload.get("seva_id")
    seva_name = str(payload.get("seva_name") or "Seva Booking")
    col_sevas = mandir_router.get_collection("mandir_sevas")
    seva_doc: dict[str, Any] | None = None
    if seva_id:
        seva_doc = await col_sevas.find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
        if not seva_doc:
            seva_doc = await col_sevas.find_one({"id": str(seva_id), "tenant_id": tenant_id})
        if seva_doc and seva_doc.get("name"):
            seva_name = str(seva_doc["name"])
        if seva_doc and seva_doc.get("name_kannada"):
            payload["seva_name_local"] = str(seva_doc.get("name_kannada") or "").strip()

    booking_date = mandir_router._parse_booking_date(payload.get("booking_date"))
    if booking_date is None:
        raise HTTPException(status_code=400, detail="Please enter a valid booking date.")
    mandir_router._validate_seva_booking_date(seva_doc, booking_date)
    await mandir_router._validate_seva_booking_capacity(
        seva_doc,
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=str(seva_id),
        booking_date=booking_date,
    )

    # Compute expiry_date from seva's duration_days (for annual/subscription sevas)
    seva_expiry_date: str | None = None
    if seva_doc:
        duration_days = seva_doc.get("duration_days")
        if duration_days and int(duration_days) > 0:
            booking_date_raw = str(payload.get("booking_date") or "").strip()
            try:
                base_dt = datetime.fromisoformat(booking_date_raw)
            except Exception:
                base_dt = datetime.now(timezone.utc)
            seva_expiry_date = (base_dt + timedelta(days=int(duration_days))).date().isoformat()

    devotee_doc: dict[str, Any] | None = None
    devotee_id = str(payload.get("devotee_id") or "").strip()
    if devotee_id:
        devotee_doc = await mandir_router.get_collection("mandir_devotees").find_one(
            {"id": devotee_id, "tenant_id": tenant_id, "app_key": app_key}
        )
        if not devotee_doc:
            devotee_doc = await mandir_router.get_collection("mandir_devotees").find_one(
                {"id": devotee_id, "tenant_id": tenant_id}
            )

    devotee_phone = mandir_router._normalize_phone(
        payload.get("devotee_phone") or payload.get("devotee_mobile") or payload.get("phone")
    )
    if devotee_doc is None and devotee_phone:
        devotee_doc = await mandir_router._find_devotee_by_phone(tenant_id, app_key, devotee_phone)

    devotee_snapshot = mandir_router._sanitize_mongo_doc(devotee_doc) if isinstance(devotee_doc, dict) else {}
    devotee_name = str(
        payload.get("devotee_names")
        or payload.get("devotee_name")
        or devotee_snapshot.get("name")
        or "Devotee"
    ).strip() or "Devotee"
    devotee_address = str(
        payload.get("devotee_address")
        or payload.get("address")
        or devotee_snapshot.get("address")
        or ""
    ).strip() or None
    devotee_phone = devotee_phone or mandir_router._normalize_phone(devotee_snapshot.get("phone"))

    booking = {
        "id": booking_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        **{k: v for k, v in payload.items() if k not in ("id", "_id", "tenant_id", "app_key")},
        "payment_mode": payment_mode,
        "created_at": now,
        "updated_at": now,
        "status": "confirmed",
    }
    booking["seva_name"] = seva_name
    if payload.get("seva_name_local"):
        booking["seva_name_local"] = str(payload.get("seva_name_local") or "").strip()
    booking["devotee_id"] = devotee_id or str(booking.get("devotee_id") or devotee_snapshot.get("id") or "").strip() or None
    booking["devotee_name"] = devotee_name
    booking["devotee_names"] = devotee_name
    booking["devotee_phone"] = devotee_phone or None
    if devotee_address:
        booking["devotee_address"] = devotee_address
        booking["address"] = devotee_address
    if devotee_snapshot:
        booking["devotee"] = {
            "id": devotee_snapshot.get("id"),
            "name": devotee_name,
            "phone": devotee_phone or devotee_snapshot.get("phone"),
            "address": devotee_address or devotee_snapshot.get("address"),
            "city": devotee_snapshot.get("city"),
            "state": devotee_snapshot.get("state"),
            "pincode": devotee_snapshot.get("pincode"),
        }
    booking["receipt_number"] = await mandir_router._next_receipt_number(
        tenant_id=tenant_id,
        app_key=app_key,
        receipt_kind="seva",
        receipt_date=booking.get("booking_date") or now,
    )
    booking["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id}/receipt/pdf"
    if seva_expiry_date:
        booking["expiry_date"] = seva_expiry_date
        booking["reminder_count"] = 0
        booking["reminder_sent_at"] = None

    col = mandir_router.get_collection("mandir_seva_bookings")
    try:
        await col.insert_one(booking)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save seva booking: {exc}") from exc

    if amount > 0:
        raw_account_id = payload.get("bank_account_id") or payload.get("payment_account_id")
        resolved_account_id = await mandir_router._resolve_mandir_payment_account_id(
            session,
            tenant_id,
            raw_account_id,
            payment_mode,
        )
        if not resolved_account_id:
            await col.delete_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=400, detail="No valid cash/bank account is configured for seva posting")

        try:
            income_acc_id = await mandir_router._resolve_mandir_income_account(session, tenant_id, "Seva Income - General")
            devotee_names = str(booking.get("devotee_names") or booking.get("devotee_name") or "Devotee")
            journal_payload = JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"Seva Booking ({seva_name}) - {devotee_names}",
                reference=booking["receipt_number"],
                lines=[
                    JournalLineIn(account_id=resolved_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount))),
                ],
            )
            await mandir_router.post_journal_entry(
                session=session,
                app_key=app_key,
                tenant_id=tenant_id,
                created_by="mandir_compat_system",
                payload=journal_payload,
                idempotency_key=f"sev_{booking_id}",
            )
        except Exception as exc:
            await col.delete_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=500, detail=f"Failed to post seva journal: {exc}") from exc

    return mandir_router._mandir_seva_booking_view(booking)

@router.post("/sevas/bookings/quick-ticket", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_quick_ticket(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    ticket_type = str(payload.get("ticket_type") or payload.get("purpose") or payload.get("payment_purpose") or "seva").strip().lower()
    normalized_phone = mandir_router._normalize_phone(payload.get("devotee_phone") or payload.get("phone") or payload.get("mobile"))

    devotee = None
    if normalized_phone:
        try:
            devotee = await mandir_router._find_devotee_by_phone(tenant_id, app_key, normalized_phone)
        except Exception:
            devotee = None

    devotee_name = str(
        payload.get("devotee_name")
        or payload.get("devotee_names")
        or (devotee or {}).get("name")
        or "Walk-in Devotee"
    ).strip() or "Walk-in Devotee"

    if ticket_type in {"donation", "annadanam", "annadana", "sponsorship", "other"}:
        category_map = {
            "annadanam": "Annadanam",
            "annadana": "Annadanam",
            "sponsorship": "Sponsorship",
            "other": "General Donation",
            "donation": "General Donation",
        }
        donation_payload = {
            **payload,
            "amount": mandir_router._safe_float(payload.get("amount") or payload.get("amount_paid"), 0.0),
            "devotee_name": devotee_name,
            "devotee_phone": normalized_phone,
            "phone": normalized_phone,
            "category": str(payload.get("category") or category_map.get(ticket_type, "General Donation")),
            "payment_mode": str(payload.get("payment_mode") or payload.get("payment_method") or "Cash"),
        }
        donation = await mandir_router.create_donation(
            payload=donation_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        return {
            "ticket_type": "donation",
            "autofill_found": bool(devotee),
            "devotee": devotee,
            "receipt_number": donation.get("receipt_number"),
            "receipt_pdf_url": donation.get("receipt_pdf_url"),
            "record": donation,
        }

    seva_payload = {
        **payload,
        "amount_paid": mandir_router._safe_float(payload.get("amount_paid") or payload.get("amount"), 0.0),
        "devotee_name": devotee_name,
        "devotee_names": str(payload.get("devotee_names") or devotee_name),
        "devotee_phone": normalized_phone,
        "devotee_mobile": normalized_phone,
        "payment_mode": str(payload.get("payment_mode") or payload.get("payment_method") or "Cash"),
        "booking_date": str(payload.get("booking_date") or datetime.now(timezone.utc).date().isoformat()),
    }
    booking = await mandir_router.create_seva_booking(
        payload=seva_payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )
    return {
        "ticket_type": "seva",
        "autofill_found": bool(devotee),
        "devotee": devotee,
        "receipt_number": booking.get("receipt_number"),
        "receipt_pdf_url": booking.get("receipt_pdf_url"),
        "record": booking,
    }


@router.get("/sevas/bookings")
async def mandir_seva_bookings(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = mandir_router.get_collection("mandir_seva_bookings")
    fetch_limit = 500 if any([q, from_date, to_date, status]) else min(limit + offset, 500)
    docs = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("booking_date", -1).limit(fetch_limit).to_list(length=fetch_limit)
    viewed = [mandir_router._mandir_seva_booking_view(doc) for doc in docs]
    if status:
        normalized_status = str(status).strip().lower()
        viewed = [row for row in viewed if str(row.get("status") or "").strip().lower() == normalized_status]
    filtered = mandir_router._mandir_filter_rows(
        viewed,
        q=q,
        from_date=from_date,
        to_date=to_date,
        date_fields=("booking_date", "created_at"),
        search_fields=("receipt_number", "devotee_name", "devotee_names", "seva_name", "seva", "upi_reference_number"),
    )
    return filtered[offset:offset + limit]


@router.get("/sevas/bookings/{booking_id}/receipt/pdf")
async def get_seva_receipt_pdf(
    booking_id: str,
    lang: str | None = Query(default=None, description="Override receipt language (kannada/hindi/tamil/telugu/malayalam)"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    col = mandir_router.get_collection("mandir_seva_bookings")
    booking = await col.find_one({"id": str(booking_id), "tenant_id": tenant_id, "app_key": app_key})
    if booking is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")

    booking_id_text = str(booking.get("id") or booking_id).strip()
    booking["id"] = booking_id_text

    resolved_seva_name = str(booking.get("seva_name") or "").strip()
    seva_id = booking.get("seva_id")
    seva_doc: dict[str, Any] | None = None
    if seva_id:
        seva_doc = await mandir_router.get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
        if not seva_doc:
            seva_doc = await mandir_router.get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id})
    if seva_doc:
        if (not resolved_seva_name or resolved_seva_name.lower() in {"seva booking", "seva"}) and seva_doc.get("name"):
            booking["seva_name"] = str(seva_doc.get("name")).strip()
        if seva_doc.get("name_kannada"):
            booking["seva_name_local"] = str(seva_doc.get("name_kannada") or "").strip()

    devotee_snapshot = booking.get("devotee") if isinstance(booking.get("devotee"), dict) else {}
    if not devotee_snapshot or not any([
        booking.get("devotee_name"),
        booking.get("devotee_names"),
        booking.get("devotee_address"),
        booking.get("address"),
    ]):
        devotee_doc: dict[str, Any] | None = None
        booking_devotee_id = str(booking.get("devotee_id") or "").strip()
        if booking_devotee_id:
            devotee_doc = await mandir_router.get_collection("mandir_devotees").find_one(
                {"id": booking_devotee_id, "tenant_id": tenant_id, "app_key": app_key}
            )
            if not devotee_doc:
                devotee_doc = await mandir_router.get_collection("mandir_devotees").find_one(
                    {"id": booking_devotee_id, "tenant_id": tenant_id}
                )

        if devotee_doc is None:
            booking_phone = mandir_router._normalize_phone(
                booking.get("devotee_phone") or booking.get("devotee_mobile") or (devotee_snapshot or {}).get("phone")
            )
            if booking_phone:
                devotee_doc = await mandir_router._find_devotee_by_phone(tenant_id, app_key, booking_phone)

        if devotee_doc:
            devotee_snapshot = mandir_router._sanitize_mongo_doc(devotee_doc)

    if devotee_snapshot:
        resolved_devotee_name = str(
            booking.get("devotee_names")
            or booking.get("devotee_name")
            or devotee_snapshot.get("name")
            or "Devotee"
        ).strip() or "Devotee"
        resolved_devotee_address = str(
            booking.get("devotee_address")
            or booking.get("address")
            or devotee_snapshot.get("address")
            or ""
        ).strip() or None
        resolved_devotee_phone = mandir_router._normalize_phone(
            booking.get("devotee_phone") or booking.get("devotee_mobile") or devotee_snapshot.get("phone")
        )
        booking["devotee_id"] = str(booking.get("devotee_id") or devotee_snapshot.get("id") or "").strip() or None
        booking["devotee_name"] = resolved_devotee_name
        booking["devotee_names"] = resolved_devotee_name
        booking["devotee_phone"] = resolved_devotee_phone or None
        if resolved_devotee_address:
            booking["devotee_address"] = resolved_devotee_address
            booking["address"] = resolved_devotee_address
        booking["devotee"] = {
            "id": devotee_snapshot.get("id"),
            "name": resolved_devotee_name,
            "phone": resolved_devotee_phone or devotee_snapshot.get("phone"),
            "address": resolved_devotee_address or devotee_snapshot.get("address"),
            "city": devotee_snapshot.get("city"),
            "state": devotee_snapshot.get("state"),
            "pincode": devotee_snapshot.get("pincode"),
        }
    receipt_number = mandir_router._receipt_number_for_seva(booking)
    booking["receipt_number"] = receipt_number
    booking["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id_text}/receipt/pdf"

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": booking_id_text},
        {
            "$set": {
                "receipt_number": receipt_number,
                "receipt_pdf_url": booking["receipt_pdf_url"],
                "seva_name": booking.get("seva_name"),
                "seva_name_local": booking.get("seva_name_local"),
                "devotee_id": booking.get("devotee_id"),
                "devotee_name": booking.get("devotee_name"),
                "devotee_names": booking.get("devotee_names"),
                "devotee_phone": booking.get("devotee_phone"),
                "devotee_address": booking.get("devotee_address"),
                "address": booking.get("address"),
                "devotee": booking.get("devotee"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=False,
    )

    temple_profile = await mandir_router._resolve_temple_receipt_profile(tenant_id=tenant_id, app_key=app_key, lang=lang)

    try:
        pdf_bytes = mandir_router._generate_seva_receipt_pdf_bytes(
            booking,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    safe_receipt = "".join(ch for ch in str(receipt_number) if ch.isalnum() or ch in ("-", "_")) or booking_id_text[:8]
    filename = f"seva_receipt_{safe_receipt}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/sevas/bookings/{booking_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def cancel_seva_receipt(
    booking_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    return await mandir_router._cancel_mandir_receipt_source(
        source_kind="seva",
        source_id=booking_id,
        collection_name="mandir_seva_bookings",
        id_field="id",
        idempotency_prefix="sev_",
        payload=payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )




@router.put("/sevas/bookings/{booking_id}/reschedule", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_request_seva_reschedule(
    booking_id: str,
    new_date: str = Query(...),
    reason: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    col = mandir_router.get_collection("mandir_seva_bookings")
    await col.update_one(
        {"id": booking_id, "tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": {
                "reschedule_pending": True,
                "status": "reschedule_pending",
                "reschedule_requested_date": new_date,
                "reschedule_reason": str(reason or "").strip() or None,
                "reschedule_requested_at": now,
                "updated_at": now,
            }
        },
        upsert=False,
    )
    doc = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    if doc is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")
    return mandir_router._mandir_seva_booking_view(doc)


@router.post("/sevas/bookings/{booking_id}/approve-reschedule", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_approve_seva_reschedule(
    booking_id: str,
    approve: bool = Query(default=True),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    col = mandir_router.get_collection("mandir_seva_bookings")
    booking = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    if booking is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")

    requested_date = str(booking.get("reschedule_requested_date") or "").strip()
    patch: dict[str, Any] = {
        "reschedule_pending": False,
        "reschedule_approved": bool(approve),
        "reschedule_decided_at": now,
        "updated_at": now,
    }
    if approve and requested_date:
        patch["booking_date"] = requested_date
        patch["status"] = "confirmed"
    else:
        patch["status"] = "confirmed"

    await col.update_one(
        {"id": booking_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    updated = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    return mandir_router._mandir_seva_booking_view(updated or booking)

@router.get("/sevas/reschedule/pending")
async def mandir_seva_reschedule_pending(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = mandir_router.get_collection("mandir_seva_bookings")
    q = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "$or": [{"reschedule_pending": True}, {"status": "reschedule_pending"}],
    }
    docs = await col.find(q).sort("updated_at", -1).limit(limit).to_list(length=limit)
    return [mandir_router._sanitize_mongo_doc(doc) for doc in docs]

