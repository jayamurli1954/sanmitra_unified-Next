"""MandirMitra seva master CRUD and import routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from fastapi import Depends, File, Header, HTTPException, Query, Response, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

@router.get("/sevas/")
@router.get("/sevas")
async def list_sevas(
    include_inactive: bool = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        mandir_router._to_positive_int(x_temple_id),
    )
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    try:
        col = mandir_router.get_collection("mandir_sevas")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
        if not include_inactive:
            query["is_active"] = True
        rows = await (
            col.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return [mandir_router._serialize_seva_doc(row) for row in rows]
    except Exception as exc:
        mandir_router.logger.error("Failed to list sevas for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []


@router.get("/sevas/{seva_id}/availability")
async def seva_date_availability(
    seva_id: str,
    booking_date: str = Query(..., description="Booking date in YYYY-MM-DD format"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva date availability check",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    parsed_date = mandir_router._parse_booking_date(booking_date)
    if parsed_date is None:
        raise HTTPException(status_code=400, detail="Please enter a valid booking date.")

    seva_doc = await mandir_router.get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
    if not seva_doc:
        seva_doc = await mandir_router.get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id})
    if not seva_doc:
        raise HTTPException(status_code=404, detail="Seva not found")

    mandir_router._validate_seva_booking_date(seva_doc, parsed_date)
    max_bookings, booked_count, slots_left = await mandir_router._validate_seva_booking_capacity(
        seva_doc,
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=str(seva_id),
        booking_date=parsed_date,
    )
    return {
        "seva_id": str(seva_id),
        "booking_date": parsed_date.isoformat(),
        "available": slots_left is None or slots_left > 0,
        "max_bookings_per_day": max_bookings,
        "booked_count": booked_count,
        "slots_left": slots_left,
    }


@router.post("/sevas/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/sevas", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_seva(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        mandir_router._to_positive_int(x_temple_id),
    )
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    item = mandir_router._build_seva_item(payload, tenant_id=tenant_id, app_key=app_key)
    try:
        col = mandir_router.get_collection("mandir_sevas")
        await col.insert_one(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save seva: {exc}") from exc
    return mandir_router._serialize_seva_doc(item)


@router.put("/sevas/{seva_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def update_seva(
    seva_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        mandir_router._to_positive_int(x_temple_id),
    )
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    patch = mandir_router._build_seva_patch(payload)
    patch.pop("id", None)
    patch.pop("_id", None)
    patch.pop("tenant_id", None)
    patch.pop("app_key", None)
    if not patch:
        raise HTTPException(status_code=400, detail="No updatable seva fields provided")
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    col = mandir_router.get_collection("mandir_sevas")
    try:
        await col.update_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": patch}, upsert=False)
        doc = await col.find_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update seva: {exc}") from exc
    if not doc:
        raise HTTPException(status_code=404, detail="Seva not found")
    return mandir_router._serialize_seva_doc(doc)


@router.delete("/sevas/{seva_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def delete_seva(
    seva_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        mandir_router._to_positive_int(x_temple_id),
    )
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    col = mandir_router.get_collection("mandir_sevas")
    await col.delete_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key})
    return {"status": "deleted", "id": seva_id}


@router.get("/sevas/import/template")
async def seva_import_template(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    await mandir_router._resolve_tenant_for_mandir_request(current_user, x_tenant_id, mandir_router._to_positive_int(x_temple_id))
    mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    csv_body = mandir_router._seva_import_template_csv()
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sevas_import_template.csv"},
    )


@router.post("/sevas/import", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def import_sevas(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        mandir_router._to_positive_int(x_temple_id),
    )
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    filename = str(file.filename or "").strip().lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for seva import")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Try multiple encodings to handle files from Excel, Google Sheets, etc.
    # Excel on Windows often uses Windows-1252 (cp1252)
    # Google Sheets exports UTF-8, but some systems may use UTF-16
    encodings_to_try = [
        "utf-8-sig",  # UTF-8 with BOM
        "utf-8",      # UTF-8 without BOM
        "cp1252",     # Windows-1252 (Excel on Windows)
        "iso-8859-1", # Latin1 (fallback)
    ]

    # Check if file looks like UTF-16
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        encodings_to_try.insert(0, "utf-16")

    text = None
    decode_errors = []

    for encoding in encodings_to_try:
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError) as e:
            decode_errors.append(f"{encoding}: {str(e)[:50]}")
            continue

    if text is None:
        error_detail = "Unable to decode CSV file. Tried encodings: " + ", ".join(encodings_to_try)
        raise HTTPException(status_code=400, detail=error_detail)

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV header row is missing")

    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for row_number, row in enumerate(reader, start=2):
        normalized = {
            str(key or "").strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
            if key is not None
        }
        if not any(str(value or "").strip() for value in normalized.values()):
            continue

        provided_name = normalized.get("name_english") or normalized.get("name") or normalized.get("seva_name")
        if not str(provided_name or "").strip():
            errors.append({"row": row_number, "error": "name_english is required"})
            continue

        amount_value = mandir_router._safe_optional_float(normalized.get("amount"))
        if amount_value is None:
            errors.append({"row": row_number, "error": "amount is required"})
            continue
        if amount_value < 0:
            errors.append({"row": row_number, "error": "amount must be greater than or equal to 0"})
            continue

        payload = dict(normalized)
        payload["amount"] = amount_value
        items.append(mandir_router._build_seva_item(payload, tenant_id=tenant_id, app_key=app_key))

    if items:
        col = mandir_router.get_collection("mandir_sevas")
        try:
            await col.insert_many(items)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to import sevas: {exc}") from exc

    return {
        "status": "ok",
        "inserted_count": len(items),
        "failed_count": len(errors),
        "errors": errors[:200],
    }


@router.get("/sevas/lists/priests")
async def seva_priests(_current_user: dict = Depends(get_current_user)):
    return [{"id": "p1", "name": "Temple Priest"}]


@router.get("/sevas/dropdown-options")
async def seva_dropdown_options(_current_user: dict = Depends(get_current_user)):
    return {
        "categories": ["General", "Special", "Festival"],
        "time_slots": ["06:00", "08:00", "10:00", "18:00"],
    }


@router.get("/sevas/payment-accounts")
async def seva_payment_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await mandir_router._payment_accounts(tenant_id, app_key)


