"""MandirMitra seva reminder configuration and trigger routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

@router.get("/sevas/reminder-config")
async def mandir_seva_reminder_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """List all sevas with their current reminder configuration for this temple."""
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    col = mandir_router.get_collection("mandir_sevas")
    docs = await col.find({"tenant_id": tenant_id, "is_active": True}).to_list(length=500)
    result = []
    for doc in docs:
        result.append({
            "seva_id": str(doc.get("id") or ""),
            "seva_name": str(doc.get("name_english") or doc.get("name") or ""),
            "amount": float(doc.get("amount") or 0),
            "frequency": str(doc.get("frequency") or "one_time"),
            "duration_days": doc.get("duration_days"),
            "reminder_enabled": bool(doc.get("reminder_enabled", False)),
            "reminder_days_before": int(doc.get("reminder_days_before") or 30),
        })
    return result


@router.patch("/sevas/{seva_id}/reminder-config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_update_seva_reminder_config(
    seva_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Update reminder configuration for a specific seva (admin only).

    Accepted fields: reminder_enabled (bool), reminder_days_before (int), duration_days (int).
    """
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    col = mandir_router.get_collection("mandir_sevas")
    doc = await col.find_one({"id": seva_id, "tenant_id": tenant_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Seva not found")

    patch: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "reminder_enabled" in payload:
        patch["reminder_enabled"] = bool(payload["reminder_enabled"])
    if "reminder_days_before" in payload:
        days = int(payload["reminder_days_before"])
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="reminder_days_before must be between 1 and 365")
        patch["reminder_days_before"] = days
    if "duration_days" in payload:
        dur = int(payload["duration_days"])
        if dur < 1:
            raise HTTPException(status_code=400, detail="duration_days must be >= 1")
        patch["duration_days"] = dur

    await col.update_one({"id": seva_id, "tenant_id": tenant_id}, {"$set": patch})
    updated = await col.find_one({"id": seva_id, "tenant_id": tenant_id})
    return {
        "seva_id": seva_id,
        "seva_name": str(updated.get("name_english") or updated.get("name") or ""),
        "reminder_enabled": bool(updated.get("reminder_enabled", False)),
        "reminder_days_before": int(updated.get("reminder_days_before") or 30),
        "duration_days": updated.get("duration_days"),
    }


@router.get("/sevas/reminders/upcoming")
async def mandir_seva_reminders_upcoming(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """List all seva bookings with expiry_date within the next `days` days."""
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days)

    # Get temple display name for WhatsApp messages
    temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id}) or {}
    _temple_display_name = str(temple_doc.get("temple_name") or temple_doc.get("name") or "Temple")

    col = mandir_router.get_collection("mandir_seva_bookings")
    docs = await col.find(
        {
            "tenant_id": tenant_id,
            "expiry_date": {"$exists": True, "$ne": None},
            "status": {"$ne": "cancelled"},
        }
    ).sort("expiry_date", 1).to_list(length=500)

    result = []
    for b in docs:
        expiry_raw = str(b.get("expiry_date") or "")
        if not expiry_raw:
            continue
        try:
            expiry_dt = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if expiry_dt > window_end:
            continue
        days_left = max(0, (expiry_dt.date() - now.date()).days)
        devotee_phone = str(b.get("devotee_phone") or b.get("devotee_mobile") or "")
        devotee_name = str(b.get("devotee_name") or b.get("devotee_names") or "Devotee")
        seva_name = str(b.get("seva_name") or "")
        amount = float(b.get("amount_paid") or b.get("amount") or 0)
        receipt_number = str(b.get("receipt_number") or b.get("id") or "")
        expiry_label = expiry_dt.strftime("%d %b %Y")

        # WhatsApp deep link — admin clicks to send pre-filled message to devotee
        from app.modules.mandir_compat.reminder_worker import build_whatsapp_reminder_link
        whatsapp_link = build_whatsapp_reminder_link(
            devotee_phone=devotee_phone,
            devotee_name=devotee_name,
            seva_name=seva_name,
            temple_name=_temple_display_name,
            expiry_date=expiry_label,
            amount=amount,
            days_left=days_left,
            receipt_number=receipt_number,
        )

        result.append({
            "booking_id": str(b.get("id") or ""),
            "receipt_number": receipt_number,
            "seva_id": str(b.get("seva_id") or ""),
            "seva_name": seva_name,
            "devotee_name": devotee_name,
            "devotee_phone": devotee_phone,
            "devotee_email": str(b.get("devotee_email") or ""),
            "amount": amount,
            "booking_date": str(b.get("booking_date") or ""),
            "expiry_date": expiry_raw,
            "expiry_date_label": expiry_label,
            "days_left": days_left,
            "reminder_count": int(b.get("reminder_count") or 0),
            "reminder_sent_at": b.get("reminder_sent_at"),
            "status": str(b.get("status") or "confirmed"),
            "whatsapp_link": whatsapp_link,
        })
    return result


@router.post("/sevas/reminders/trigger", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_seva_reminders_trigger(
    payload: dict = {},
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Manually trigger the reminder job for this tenant.

    Optional payload fields:
      - seva_id (str): limit to a single seva
      - force (bool): re-send even if reminded recently (default: False)
    """
    from app.modules.mandir_compat.reminder_worker import run_reminders_once

    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    seva_id = str(payload.get("seva_id") or "").strip() or None
    force = bool(payload.get("force", False))

    result = await run_reminders_once(
        tenant_id=tenant_id,
        seva_id=seva_id,
        force=force,
    )
    return {"ok": True, "result": result}

