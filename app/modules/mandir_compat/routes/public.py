"""MandirMitra public portal and public payment management routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.rate_limiting import limiter
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_WRITE_ROUTE_DEPS, router

# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Version + public UPI intent
# ROUTES : GET /mandir/version  GET /public/temples/{temple_id}/upi-intent
# ════════════════════════════════════════════════════════════════════════

@router.get("/mandir/version")
async def mandir_get_version():
    """Get MandirMitra version info. No authentication required."""
    from app.config import get_settings
    from datetime import datetime
    settings = get_settings()
    return {
        "app": "MandirMitra",
        "version": settings.APP_VERSION,
        "released_at": "2026-04-14T00:00:00Z",  # Release date of v1.2.0
        "features": [
            "Quick Ticket Counter mode",
            "Seva renewal reminders (Email + SMS)",
            "Public payment idempotency & audit logging",
            "Rate limiting on public endpoints",
            "Multilingual support (en/kn/hi) for public portal",
            "Indic font rendering for PDFs"
        ]
    }


# ---------------------------------------------------------------------------
# PUBLIC SEVA PAYMENT ENDPOINTS  (no authentication required)
# ---------------------------------------------------------------------------

def _normalize_public_donation_categories(raw: Any, *, fallback_to_default: bool = True) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return [dict(item) for item in mandir_router._DEFAULT_PUBLIC_DONATION_CATEGORIES] if fallback_to_default else []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        category_id = str(item.get("id") or "").strip().lower()
        if not category_id:
            category_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or f"category_{index + 1}"
        base_id = category_id
        suffix = 2
        while category_id in seen:
            category_id = f"{base_id}_{suffix}"
            suffix += 1
        seen.add(category_id)
        normalized.append(
            {
                "id": category_id[:80],
                "name": name[:120],
                "description": str(item.get("description") or "").strip()[:300],
            }
        )

    if normalized or not fallback_to_default:
        return normalized
    return [dict(item) for item in mandir_router._DEFAULT_PUBLIC_DONATION_CATEGORIES]



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public endpoints (temples list / info / sevas / autofill / pincode / donation-categories)
# ROUTES : GET /public/temples  GET .../info  GET .../sevas  GET .../devotee/autofill  GET .../donation-categories  GET /public/location/pincode
# ════════════════════════════════════════════════════════════════════════

@router.get("/public/temples")
async def mandir_public_list_temples(
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """List temples that have public payments enabled (for temple selector on public page)."""
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    col = mandir_router.get_collection("mandir_temples")
    visibility_query: dict[str, Any] = {
        "$or": [
            {"upi_public_enabled": True},
            {"upi_id": {"$exists": True, "$ne": None, "$ne": ""}},
        ]
    }
    if app_key == "mandirmitra":
        visibility_query["$and"] = [
            {
                "$or": [
                    {"app_key": app_key},
                    {"app_key": {"$exists": False}},
                    {"app_key": None},
                    {"app_key": ""},
                ]
            }
        ]
    else:
        visibility_query["app_key"] = app_key
    docs = await col.find(visibility_query).to_list(length=100)
    result = []
    for doc in docs:
        temple_id = doc.get("temple_id") or doc.get("id")
        if not temple_id:
            continue
        if app_key == "mandirmitra" and not str(doc.get("app_key") or "").strip():
            await col.update_one({"_id": doc.get("_id")}, {"$set": {"app_key": app_key}}, upsert=False)
        result.append({
            "temple_id": int(temple_id),
            "temple_name": str(doc.get("temple_name") or doc.get("name") or ""),
            "trust_name": str(doc.get("trust_name") or ""),
            "city": str(doc.get("city") or ""),
            "state": str(doc.get("state") or ""),
        })
    return result


@router.get("/public/temples/{temple_id}/info")
async def mandir_public_temple_info(
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not doc:
        raise HTTPException(status_code=404, detail="Temple not found")

    return {
        "temple_id": temple_id,
        "temple_name": str(doc.get("temple_name") or doc.get("name") or ""),
        "trust_name": str(doc.get("trust_name") or ""),
        "address": str(doc.get("address") or ""),
        "city": str(doc.get("city") or ""),
        "state": str(doc.get("state") or ""),
        "upi_id": str(doc.get("upi_id") or "").strip() or None,
        "upi_payee_name": str(doc.get("upi_payee_name") or doc.get("trust_name") or doc.get("temple_name") or ""),
        "qr_code_image_url": str(doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": str(doc.get("admin_whatsapp") or "").strip() or None,
        "upi_public_enabled": bool(doc.get("upi_public_enabled", False)),
    }


@router.get("/public/temples/{temple_id}/sevas")
@limiter.limit("30/minute")
async def mandir_public_temple_sevas(
    request: Request,
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    col = mandir_router.get_collection("mandir_sevas")
    docs = await col.find({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "is_active": {"$ne": False},
    }).sort("seva_name", 1).to_list(length=200)

    return [
        {
            "seva_id": str(doc.get("_id") or doc.get("id") or ""),
            "seva_name": str(doc.get("seva_name") or doc.get("name") or ""),
            "description": str(doc.get("description") or ""),
            "amount": doc.get("amount"),
            "frequency": str(doc.get("frequency") or "one_time"),
            "duration_days": doc.get("duration_days"),
        }
        for doc in docs
        if doc.get("seva_name") or doc.get("name")
    ]


@router.get("/public/temples/{temple_id}/devotee/autofill/{phone}")
@limiter.limit("20/minute")
async def mandir_public_devotee_autofill(
    request: Request,
    temple_id: int,
    phone: str,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    normalized = mandir_router._normalize_phone(phone)
    if not normalized:
        return {"found": False, "devotee": None}

    # Scoped by tenant_id + app_key - mobile linked to THIS temple only
    col = mandir_router.get_collection("mandir_devotees")
    docs = await col.find({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "phone": normalized,
    }).limit(1).to_list(length=1)

    if not docs:
        return {"found": False, "devotee": None}

    doc = docs[0]
    return {
        "found": True,
        "devotee": {
            "name": str(doc.get("name") or ""),
            "city": str(doc.get("city") or ""),
            "state": str(doc.get("state") or ""),
            "pincode": str(doc.get("pincode") or ""),
            "gothra": str(doc.get("gothra") or ""),
            "nakshtra": str(doc.get("nakshtra") or ""),
            "rashi": str(doc.get("rashi") or ""),
        },
    }


@router.get("/public/location/pincode/{pincode}")
async def mandir_public_pincode_lookup(pincode: str):
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode. Must be 6 digits.")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.postalpincode.in/pincode/{pincode}")
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0].get("Status") == "Success":
                post_offices = data[0].get("PostOffice") or []
                if post_offices:
                    po = post_offices[0]
                    return {
                        "found": True,
                        "pincode": pincode,
                        "city": str(po.get("District") or po.get("Name") or ""),
                        "state": str(po.get("State") or ""),
                        "district": str(po.get("District") or ""),
                    }
    except Exception:
        pass

    return {"found": False, "pincode": pincode, "city": "", "state": "", "district": ""}


@router.get("/public/temples/{temple_id}/donation-categories")
async def mandir_public_donation_categories(
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return _normalize_public_donation_categories(temple_doc.get("donation_categories"))



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public seva payments (create / status)
# ROUTES : POST /public/temples/{temple_id}/seva-payments  GET /public/payments/{payment_id}/status
# ════════════════════════════════════════════════════════════════════════

@router.post("/public/temples/{temple_id}/seva-payments")
@limiter.limit("10/minute")
async def mandir_public_create_seva_payment(
    temple_id: int,
    payload: dict[str, Any],
    request: Request,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    # Idempotency: if client sends idempotency_key and a matching pending record
    # exists (submitted in the last 10 minutes), return it without creating a duplicate.
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if idempotency_key:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        existing = await mandir_router.get_collection("mandir_public_payments").find_one({
            "tenant_id": tenant_id,
            "app_key": app_key,
            "idempotency_key": idempotency_key,
            "created_at": {"$gte": cutoff},
        })
        if existing:
            temple_doc_i = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
            return {
                "payment_id": existing["id"][:8].upper(),
                "full_payment_id": existing["id"],
                "status": existing.get("status", "pending"),
                "payment_type": existing.get("payment_type", "seva"),
                "seva_name": existing.get("seva_name", ""),
                "amount": existing.get("amount"),
                "upi_id": str(temple_doc_i.get("upi_id") or "").strip() or None,
                "upi_payee_name": str(temple_doc_i.get("upi_payee_name") or temple_doc_i.get("trust_name") or "").strip() or None,
                "qr_code_image_url": str(temple_doc_i.get("qr_code_image_url") or "").strip() or None,
                "admin_whatsapp": str(temple_doc_i.get("admin_whatsapp") or "").strip() or None,
                "whatsapp_link": existing.get("whatsapp_link"),
                "whatsapp_message_template": existing.get("whatsapp_message_template"),
                "message": "Payment already submitted. Please complete UPI payment and send WhatsApp confirmation.",
                "_idempotent": True,
            }

    payment_type = str(payload.get("payment_type") or "seva").strip().lower()
    if payment_type not in ("seva", "donation"):
        payment_type = "seva"

    # Validate required fields
    phone_raw = str(payload.get("phone") or payload.get("mobile") or "").strip()
    normalized_phone = mandir_router._normalize_phone(phone_raw)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Valid mobile number is required")

    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if payment_type == "donation":
        category_id = str(payload.get("category_id") or "").strip()
        category_name = str(payload.get("category_name") or "").strip()
        if not category_name:
            raise HTTPException(status_code=400, detail="Donation category is required")
        seva_id = None
        seva_name = category_name
    else:
        seva_id = str(payload.get("seva_id") or "").strip()
        seva_name = str(payload.get("seva_name") or "").strip()
        if not seva_name:
            raise HTTPException(status_code=400, detail="Seva selection is required")

    now = datetime.now(timezone.utc).isoformat()

    # Upsert devotee record - scoped to this temple's tenant_id
    devotee_col = mandir_router.get_collection("mandir_devotees")
    devotee_update = {
        "name": name,
        "phone": normalized_phone,
        "email": str(payload.get("email") or "").strip() or None,
        "address": str(payload.get("address") or "").strip() or None,
        "city": str(payload.get("city") or "").strip() or None,
        "state": str(payload.get("state") or "").strip() or None,
        "pincode": str(payload.get("pincode") or "").strip() or None,
        "gothra": str(payload.get("gothra") or "").strip() or None,
        "nakshtra": str(payload.get("nakshtra") or "").strip() or None,
        "rashi": str(payload.get("rashi") or "").strip() or None,
        "updated_at": now,
    }
    devotee_update_clean = {k: v for k, v in devotee_update.items() if v is not None}

    await devotee_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized_phone},
        {
            "$set": devotee_update_clean,
            "$setOnInsert": {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": now,
                "verified": False,
            },
        },
        upsert=True,
    )

    # Create payment record with pending status
    payment_id = str(uuid4())
    payment_doc = {
        "id": payment_id,
        "temple_id": temple_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "payment_type": payment_type,
        "seva_id": seva_id or None,
        "seva_name": seva_name,
        "amount": float(payload.get("amount") or 0) or None,
        "devotee_name": name,
        "devotee_phone": normalized_phone,
        "devotee_email": str(payload.get("email") or "").strip() or None,
        "gothra": str(payload.get("gothra") or "").strip() or None if payment_type == "seva" else None,
        "nakshtra": str(payload.get("nakshtra") or "").strip() or None if payment_type == "seva" else None,
        "rashi": str(payload.get("rashi") or "").strip() or None if payment_type == "seva" else None,
        "status": "pending",
        "utr_reference": None,
        "verified_at": None,
        "verified_by": None,
        "created_at": now,
        "source_ip": str(request.client.host if request.client else ""),
        "idempotency_key": idempotency_key or None,
    }

    await mandir_router.get_collection("mandir_public_payments").insert_one(payment_doc)

    # Formal audit log for every public payment submission
    from app.core.audit.service import log_audit_event
    try:
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=f"public:{normalized_phone}",
            product="mandirmitra",
            action="public_payment_submitted",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            new_value={
                "payment_type": payment_type,
                "seva_name": seva_name,
                "amount": payload.get("amount"),
                "devotee_phone": normalized_phone,
            },
            ip_address=str(request.client.host if request.client else ""),
        )
    except Exception:
        pass  # Audit is best-effort; never block the payment flow

    # Build WhatsApp message template
    temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    admin_whatsapp = str(temple_doc.get("admin_whatsapp") or "").strip()
    upi_id = str(temple_doc.get("upi_id") or "").strip()
    amount_str = f"Rs.{payload.get('amount')}" if payload.get("amount") else ""
    payment_label = "Donation" if payment_type == "donation" else "Seva payment"
    whatsapp_message = (
        f"Namaste, I have made the {seva_name} {payment_label} {amount_str}.\n"
        f"UTR/Reference: [PASTE UTR HERE]\n"
        f"Name: {name}\n"
        f"Mobile: {normalized_phone}\n"
        f"Payment ID: {payment_id[:8].upper()}"
    )
    whatsapp_link = None
    if admin_whatsapp:
        from urllib.parse import quote
        whatsapp_link = f"https://wa.me/{admin_whatsapp.replace('+', '').replace(' ', '')}?text={quote(whatsapp_message)}"

    # Store whatsapp details on payment doc for idempotency replay
    await mandir_router.get_collection("mandir_public_payments").update_one(
        {"id": payment_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"whatsapp_link": whatsapp_link, "whatsapp_message_template": whatsapp_message}},
    )

    return {
        "payment_id": payment_id[:8].upper(),
        "full_payment_id": payment_id,
        "status": "pending",
        "payment_type": payment_type,
        "seva_name": seva_name,
        "amount": payload.get("amount"),
        "upi_id": upi_id or None,
        "upi_payee_name": str(temple_doc.get("upi_payee_name") or temple_doc.get("trust_name") or temple_doc.get("temple_name") or "").strip() or None,
        "qr_code_image_url": str(temple_doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": admin_whatsapp or None,
        "whatsapp_link": whatsapp_link,
        "whatsapp_message_template": whatsapp_message,
        "message": "Devotee details saved. Please complete payment via UPI and send WhatsApp confirmation to the temple admin.",
    }


@router.get("/public/payments/{payment_id}/status")
async def mandir_public_payment_status(
    payment_id: str,
    temple_id: int = Query(..., ge=1),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    normalized_payment_id = str(payment_id or "").strip()
    if not normalized_payment_id:
        raise HTTPException(status_code=400, detail="Payment ID is required")

    col = mandir_router.get_collection("mandir_public_payments")
    doc = await col.find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "id": normalized_payment_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "payment_id": str(doc.get("id") or "")[:8].upper(),
        "seva_name": doc.get("seva_name"),
        "amount": doc.get("amount"),
        "status": doc.get("status", "pending"),
        "verified_at": doc.get("verified_at"),
    }



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public payments management (list / exceptions / reject / correct / verify)
# ROUTES : GET /public-payments  GET .../exceptions  PATCH .../reject|correction|verify
# ════════════════════════════════════════════════════════════════════════

@router.get("/public-payments")
async def mandir_list_public_payments(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    payment_type: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    normalized_status = str(status or "").strip().lower()
    if normalized_status and normalized_status != "all":
        query["status"] = normalized_status

    col = mandir_router.get_collection("mandir_public_payments")
    normalized_q = str(q or "").strip().lower()
    normalized_type = str(payment_type or "").strip().lower()
    needs_in_memory_filter = any([normalized_q, normalized_type])
    fetch_limit = 500 if needs_in_memory_filter else min(limit + offset, 500)
    docs = await col.find(query).sort("created_at", -1).limit(fetch_limit).to_list(length=fetch_limit)
    filtered: list[dict[str, Any]] = []
    for doc in docs:
        doc_type = str(doc.get("payment_type") or doc.get("payment_purpose") or "").strip().lower()
        if normalized_type and doc_type != normalized_type:
            continue
        if normalized_q:
            haystack = " ".join(
                str(doc.get(key) or "")
                for key in (
                    "id",
                    "payment_id",
                    "devotee_name",
                    "name",
                    "devotee_phone",
                    "phone",
                    "seva_name",
                    "payment_type",
                    "payment_purpose",
                    "status",
                    "utr_reference",
                )
            ).lower()
            if normalized_q not in haystack:
                continue
        filtered.append(mandir_router._sanitize_mongo_doc(doc))
    return filtered[offset:offset + limit]


@router.get("/public-payments/exceptions")
async def mandir_public_payment_exceptions(
    older_than_hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    reason: str | None = Query(default=None),
    status: str | None = Query(default=None),
    payment_type: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=older_than_hours)
    docs = await mandir_router.get_collection("mandir_public_payments").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).sort("created_at", -1).limit(500).to_list(length=500)

    rows: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    normalized_q = str(q or "").strip().lower()
    normalized_reason = str(reason or "").strip().lower()
    normalized_status = str(status or "").strip().lower()
    normalized_type = str(payment_type or "").strip().lower()
    for doc in docs:
        doc_status = str(doc.get("status") or "pending").strip().lower()
        amount = mandir_router._safe_float(doc.get("amount"), 0.0)
        created_at = mandir_router._parse_iso_datetime(doc.get("created_at"))
        reasons: list[str] = []

        if doc_status in {"failed", "error", "rejected"}:
            reasons.append(doc_status)
        if doc_status == "pending" and created_at and created_at < stale_cutoff:
            reasons.append("stale_pending")
        if amount <= 0:
            reasons.append("invalid_amount")
        if not mandir_router._normalize_phone(doc.get("devotee_phone")):
            reasons.append("missing_phone")
        doc_payment_type = str(doc.get("payment_type") or "").strip().lower()
        if doc_payment_type not in {"donation", "seva"}:
            reasons.append("invalid_payment_type")
        if doc_payment_type == "seva" and not str(doc.get("seva_name") or "").strip():
            reasons.append("missing_seva")
        if doc_payment_type == "donation" and not str(doc.get("seva_name") or doc.get("category") or "").strip():
            reasons.append("missing_donation_category")

        if not reasons:
            continue
        if normalized_reason and normalized_reason not in reasons:
            continue
        if normalized_status and normalized_status != "all" and doc_status != normalized_status:
            continue
        if normalized_type and doc_payment_type != normalized_type:
            continue
        if normalized_q:
            haystack = " ".join(
                str(doc.get(key) or "")
                for key in (
                    "id",
                    "payment_id",
                    "devotee_name",
                    "name",
                    "devotee_phone",
                    "phone",
                    "seva_name",
                    "payment_type",
                    "payment_purpose",
                    "status",
                    "utr_reference",
                )
            ).lower()
            if normalized_q not in haystack:
                continue

        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        row = mandir_router._sanitize_mongo_doc(doc)
        row["exception_reasons"] = reasons
        row["age_hours"] = round(((now - created_at).total_seconds() / 3600), 2) if created_at else None
        rows.append(row)

    return {
        "summary": {
            "total": len(rows),
            "by_reason": reason_counts,
            "older_than_hours": older_than_hours,
        },
        "items": rows[offset:offset + limit],
    }


@router.patch("/public-payments/{payment_id}/reject", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_reject_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    reason = " ".join(str(payload.get("reason") or "").strip().split())
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    col = mandir_router.get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    if str(doc.get("status") or "").strip().lower() == "verified":
        raise HTTPException(status_code=400, detail="Verified payment cannot be rejected")

    now = datetime.now(timezone.utc).isoformat()
    rejected_by = str(current_user.get("email") or current_user.get("sub") or current_user.get("id") or "admin")
    update = {
        "status": "rejected",
        "rejection_reason": reason,
        "rejected_at": now,
        "rejected_by": rejected_by,
        "updated_at": now,
    }
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": update})

    try:
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=rejected_by,
            product="mandirmitra",
            action="public_payment_rejected",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={"status": doc.get("status")},
            new_value={"status": "rejected", "reason": reason},
        )
    except Exception:
        pass

    return {
        "status": "rejected",
        "payment_id": payment_id[:8].upper(),
        "reason": reason,
        "rejected_at": now,
    }


@router.patch("/public-payments/{payment_id}/correction", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_correct_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = mandir_router.get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    if str(doc.get("status") or "").strip().lower() == "verified":
        raise HTTPException(status_code=400, detail="Verified payment cannot be corrected")

    patch: dict[str, Any] = {}
    if "amount" in payload:
        amount = mandir_router._safe_float(payload.get("amount"), 0.0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")
        patch["amount"] = amount
    if "devotee_phone" in payload:
        phone = mandir_router._normalize_phone(payload.get("devotee_phone"))
        if not phone:
            raise HTTPException(status_code=400, detail="Valid mobile number is required")
        patch["devotee_phone"] = phone
    if "payment_type" in payload:
        payment_type = str(payload.get("payment_type") or "").strip().lower()
        if payment_type not in {"donation", "seva"}:
            raise HTTPException(status_code=400, detail="payment_type must be donation or seva")
        patch["payment_type"] = payment_type
    if "seva_name" in payload:
        purpose = " ".join(str(payload.get("seva_name") or "").strip().split())
        if not purpose:
            raise HTTPException(status_code=400, detail="Donation/seva purpose is required")
        patch["seva_name"] = purpose

    if not patch:
        raise HTTPException(status_code=400, detail="No correction fields provided")

    now = datetime.now(timezone.utc).isoformat()
    corrected_by = str(current_user.get("email") or current_user.get("sub") or current_user.get("id") or "admin")
    patch.update({
        "corrected_at": now,
        "corrected_by": corrected_by,
        "updated_at": now,
    })
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": patch})
    updated = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}) or {**doc, **patch}

    try:
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=corrected_by,
            product="mandirmitra",
            action="public_payment_corrected",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={key: doc.get(key) for key in patch if key in doc},
            new_value={key: patch.get(key) for key in patch},
        )
    except Exception:
        pass

    return mandir_router._sanitize_mongo_doc(updated)


@router.patch("/public-payments/{payment_id}/verify", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_verify_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = mandir_router.get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")

    if doc.get("status") == "verified":
        raise HTTPException(status_code=400, detail="Payment already verified")

    utr_reference = mandir_router._normalize_public_payment_utr_reference(
        payload.get("utr_reference") or doc.get("utr_reference") or doc.get("upi_reference_number")
    )
    payment_date = str(
        payload.get("payment_date") or datetime.now(timezone.utc).date().isoformat()
    ).strip()
    bank_account_id = payload.get("bank_account_id")  # optional explicit bank account

    payment_type = str(doc.get("payment_type") or "seva").lower()
    amount = float(doc.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    devotee_name = str(doc.get("devotee_name") or "").strip() or "Unknown Devotee"
    devotee_phone = str(doc.get("devotee_phone") or "").strip() or None
    devotee_email = str(doc.get("devotee_email") or "").strip() or None
    seva_name = str(doc.get("seva_name") or "").strip()
    seva_id = str(doc.get("seva_id") or "").strip() or None

    source_record: dict[str, Any] = {}
    source_type: str
    source_id: str | None = None

    try:
        if payment_type == "seva":
            seva_payload: dict[str, Any] = {
                "amount_paid": amount,
                "payment_mode": "UPI",
                "devotee_name": devotee_name,
                "devotee_names": devotee_name,
                "devotee_phone": devotee_phone,
                "devotee_mobile": devotee_phone,
                "booking_date": payment_date,
                "seva_name": seva_name,
                "seva_id": seva_id or "",
                "upi_reference_number": utr_reference,
                "gothra": doc.get("gothra"),
                "nakshtra": doc.get("nakshtra"),
                "rashi": doc.get("rashi"),
                "notes": f"Public portal | Payment ID: {payment_id[:8].upper()}",
            }
            if bank_account_id:
                seva_payload["bank_account_id"] = bank_account_id
            source_record = await mandir_router.create_seva_booking(
                payload=seva_payload,
                session=session,
                current_user=current_user,
                x_tenant_id=x_tenant_id,
                x_app_key=app_key,
            )
            source_type = "seva_booking"
            source_id = str(source_record.get("id") or "").strip() or None
        else:
            # Donation — map category_name back to standard category
            _donation_cat_map = {
                "general donation": "General Donation",
                "annadanam": "Annadanam",
                "construction fund": "Construction Fund",
                "corpus fund": "Corpus Fund",
                "vastra seva": "Vastra Seva",
                "nitya puja": "Nitya Puja",
            }
            category = _donation_cat_map.get(seva_name.lower(), seva_name) or "General Donation"
            donation_payload: dict[str, Any] = {
                "amount": amount,
                "payment_mode": "UPI",
                "category": category,
                "devotee_name": devotee_name,
                "devotee_phone": devotee_phone,
                "email": devotee_email,
                "upi_reference_number": utr_reference,
                "donation_date": payment_date,
                "notes": f"Public portal | Payment ID: {payment_id[:8].upper()}",
            }
            if bank_account_id:
                donation_payload["bank_account_id"] = bank_account_id
            source_record = await mandir_router.create_donation(
                payload=donation_payload,
                session=session,
                current_user=current_user,
                x_tenant_id=x_tenant_id,
                x_app_key=app_key,
            )
            source_type = "donation"
            source_id = str(source_record.get("donation_id") or source_record.get("id") or "").strip() or None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to post accounting entry: {exc}") from exc

    now = datetime.now(timezone.utc).isoformat()
    update = {
        "status": "verified",
        "verified_at": now,
        "verified_by": str(current_user.get("email") or current_user.get("sub") or "admin"),
        "utr_reference": utr_reference,
        "source_type": source_type,
        "source_id": source_id,
    }
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": update})

    try:
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=update["verified_by"],
            product="mandirmitra",
            action="public_payment_verified",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={"status": doc.get("status")},
            new_value={
                "status": "verified",
                "utr_reference": utr_reference,
                "source_type": source_type,
                "source_id": source_id,
                "receipt_number": str(source_record.get("receipt_number") or "").strip() or None,
            },
        )
    except Exception:
        pass

    receipt_number = str(source_record.get("receipt_number") or "").strip() or None
    receipt_pdf_url = str(source_record.get("receipt_pdf_url") or "").strip() or None
    if not receipt_pdf_url and source_id:
        if source_type == "seva_booking":
            receipt_pdf_url = f"/api/v1/sevas/bookings/{source_id}/receipt/pdf"
        elif source_type == "donation":
            receipt_pdf_url = f"/api/v1/donations/{source_id}/receipt/pdf"

    return {
        "status": "verified",
        "payment_id": payment_id[:8].upper(),
        "source_type": source_type,
        "source_id": source_id,
        "receipt_number": receipt_number,
        "receipt_pdf_url": receipt_pdf_url,
        "message": "Payment verified and accounting entry posted successfully.",
    }


