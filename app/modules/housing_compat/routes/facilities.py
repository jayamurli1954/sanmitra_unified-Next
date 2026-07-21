"""Housing compat routes (pure move from router.py)."""
from __future__ import annotations

import asyncio
import calendar
import csv
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response, StreamingResponse
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

import pywebpush

from app.accounting.models import Account, JournalEntry, JournalLine
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.config import get_settings
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_gruha_tenant
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.postgres import get_async_session, get_session_factory
from app.modules.housing_compat import router as housing_router
from app.modules.housing_compat.router import _HOUSING_ADMIN_ROUTE_DEPS, router
from app.modules.housing_compat.schemas import (
    ApproveJoinRequest,
    ArrearsResponse,
    ArrearsTransferRequest,
    CompleteResidentRegistrationRequest,
    CompleteResidentRegistrationResponse,
    DamageClaimCreate,
    FacilityBookingCreateRequest,
    FacilityBookingResponse,
    FacilityCreateRequest,
    FacilityResponse,
    FacilityUpdateRequest,
    FinancialYearCloseRequest,
    FinancialYearCreateRequest,
    FinancialYearResponse,
    FinalBillResponse,
    FlatCreateRequest,
    FlatResponse,
    FlatTransferRequest,
    FlatUpdateRequest,
    MemberCreateRequest,
    MemberChecklistResponse,
    MemberChecklistUpdate,
    MemberResponse,
    MemberUpdateRequest,
    MembershipResponse,
    PublicJoinRequestCreate,
    PublicJoinRequestResponse,
    RejectJoinRequest,
    SocietySettingsResponse,
    SocietySettingsUpdate,
    SocietySearchItem,
    WebPushSubscribeRequest,
    StaffCreateRequest,
    StaffResponse,
    StaffUpdateRequest,
    StaffAttendanceResponse,
)
from app.modules.housing_compat.service import (
    approve_join_request,
    calculate_final_bill,
    complete_resident_registration,
    create_member,
    create_facility,
    get_member_checklist,
    create_public_join_request,
    create_flat,
    create_financial_year,
    generate_ndc,
    get_society,
    get_society_settings,
    get_flat,
    get_active_financial_year,
    list_flats,
    list_financial_years,
    list_facilities,
    list_join_requests,
    list_members,
    list_my_memberships,
    list_personal_arrears,
    list_society_units,
    raise_damage_claim,
    reject_join_request,
    provisional_close_financial_year,
    save_society_settings,
    search_societies,
    transfer_flat_to_flat,
    transfer_to_arrears,
    update_member_checklist,
    update_member,
    update_facility,
    update_flat,
    final_close_financial_year,
)


@router.get("/facilities", response_model=list[FacilityResponse])
@router.get("/facilities/", response_model=list[FacilityResponse])
async def facilities_list(
    include_inactive: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility catalog list",
    )
    rows = await list_facilities(
        tenant_id=tenant_context.tenant_id,
        app_key=tenant_context.app_key,
        include_inactive=include_inactive and housing_router._can_manage_facilities(current_user.get("role")),
    )
    return [FacilityResponse(**row) for row in rows]


@router.post("/facilities", response_model=FacilityResponse)
@router.post("/facilities/", response_model=FacilityResponse)
async def facilities_create(
    payload: FacilityCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not housing_router._can_manage_facilities(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only society administrators can manage facilities")
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility create",
    )
    row = await create_facility(tenant_id=tenant_context.tenant_id, app_key=tenant_context.app_key, payload=payload)
    return FacilityResponse(**row)


@router.patch("/facilities/{facility_id}", response_model=FacilityResponse)
async def facilities_update(
    facility_id: str,
    payload: FacilityUpdateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not housing_router._can_manage_facilities(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only society administrators can manage facilities")
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility update",
    )
    row = await update_facility(
        tenant_id=tenant_context.tenant_id,
        app_key=tenant_context.app_key,
        facility_id=facility_id,
        payload=payload,
    )
    return FacilityResponse(**row)


@router.get("/facility-bookings", response_model=list[FacilityBookingResponse])
@router.get("/facility-bookings/", response_model=list[FacilityBookingResponse])
async def facility_bookings_list(
    facility_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_time: datetime | None = Query(default=None),
    to_time: datetime | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility booking list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    access_query = await housing_router._facility_booking_access_query(current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if access_query:
        query.update(access_query)
    if facility_id:
        query["facility_id"] = facility_id
    if status:
        query["status"] = str(status).strip().lower()
    if from_time or to_time:
        time_query: dict[str, Any] = {}
        if from_time:
            time_query["$gte"] = from_time
        if to_time:
            time_query["$lte"] = to_time
        query["start_time"] = time_query
    rows = (
        await housing_router.get_collection("housing_facility_bookings")
        .find(query)
        .sort([("start_time", -1), ("created_at", -1)])
        .to_list(length=1000)
    )
    return [FacilityBookingResponse(**housing_router._facility_booking_response(row)) for row in rows]


@router.post("/facility-bookings", response_model=FacilityBookingResponse)
@router.post("/facility-bookings/", response_model=FacilityBookingResponse)
async def facility_bookings_create(
    payload: FacilityBookingCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility booking create",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=422, detail="Booking end time must be after start time")

    facility = await housing_router.get_collection("housing_facilities").find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": payload.facility_id}
    )
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    if str(facility.get("status") or "active").lower() != "active":
        raise HTTPException(status_code=409, detail="Facility is not active for booking")

    overlap = await housing_router._find_overlapping_facility_booking(
        tenant_id=tenant_id,
        app_key=app_key,
        facility_id=payload.facility_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    if overlap:
        raise HTTPException(status_code=409, detail="Facility already has an active booking for this time")

    flat_number = await housing_router._resolve_booking_flat(
        requested_flat=payload.flat_number,
        current_user=current_user,
        tenant_id=tenant_id,
        app_key=app_key,
    )
    amount = housing_router._as_decimal_money(facility.get("booking_fee") or 0)
    deposit_amount = housing_router._as_decimal_money(facility.get("deposit_amount") or 0)
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "facility_id": payload.facility_id,
        "facility_name": facility.get("name") or "Facility",
        "flat_number": flat_number,
        "resident_name": (payload.resident_name or current_user.get("name") or current_user.get("full_name") or "").strip() or None,
        "resident_phone": (payload.resident_phone or current_user.get("phone_number") or "").strip() or None,
        "purpose": (payload.purpose or "").strip() or None,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "attendee_count": payload.attendee_count,
        "amount": str(amount),
        "deposit_amount": str(deposit_amount),
        "status": "approved" if housing_router._can_manage_facilities(current_user.get("role")) else "pending",
        "payment_status": "unpaid" if amount > 0 or deposit_amount > 0 else "not_required",
        "accounting_reference": None,
        "confirmation_message": None,
        "created_by": str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    if doc["status"] == "approved":
        doc["approved_at"] = now
        doc["approved_by"] = doc["created_by"]
        doc["confirmation_message"] = housing_router._facility_confirmation_message(doc)
    await housing_router.get_collection("housing_facility_bookings").insert_one(doc)
    return FacilityBookingResponse(**housing_router._facility_booking_response(doc))


@router.post("/facility-bookings/{booking_id}/approve", response_model=FacilityBookingResponse)
async def facility_bookings_approve(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not housing_router._can_manage_facilities(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only society administrators can approve facility bookings")
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility booking approve",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    bookings = housing_router.get_collection("housing_facility_bookings")
    query = {"tenant_id": tenant_id, "app_key": app_key, "id": booking_id}
    row = await bookings.find_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Facility booking not found")
    if row.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled booking cannot be approved")

    overlap = await housing_router._find_overlapping_facility_booking(
        tenant_id=tenant_id,
        app_key=app_key,
        facility_id=str(row.get("facility_id") or ""),
        start_time=row["start_time"],
        end_time=row["end_time"],
        exclude_id=booking_id,
    )
    if overlap:
        raise HTTPException(status_code=409, detail="Facility already has an active booking for this time")

    now = datetime.now(timezone.utc)
    updated_row = {**row, "status": "approved"}
    confirmation_message = housing_router._facility_confirmation_message(updated_row)
    updates = {
        "status": "approved",
        "approved_at": now,
        "approved_by": str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system"),
        "confirmation_message": confirmation_message,
        "updated_at": now,
    }
    await bookings.update_one(query, {"$set": updates})
    updated = await bookings.find_one(query)
    return FacilityBookingResponse(**housing_router._facility_booking_response(updated or {**row, **updates}))


@router.post("/facility-bookings/{booking_id}/cancel", response_model=FacilityBookingResponse)
async def facility_bookings_cancel(
    booking_id: str,
    payload: dict[str, Any] | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="facility booking cancel",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key, "id": booking_id}
    access_query = await housing_router._facility_booking_access_query(current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if access_query:
        query.update(access_query)
    bookings = housing_router.get_collection("housing_facility_bookings")
    row = await bookings.find_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Facility booking not found")
    if row.get("status") == "cancelled":
        return FacilityBookingResponse(**housing_router._facility_booking_response(row))
    now = datetime.now(timezone.utc)
    updates = {
        "status": "cancelled",
        "cancelled_at": now,
        "cancelled_by": str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system"),
        "cancellation_reason": str((payload or {}).get("reason") or "").strip() or None,
        "updated_at": now,
    }
    await bookings.update_one({"tenant_id": tenant_id, "app_key": app_key, "id": booking_id}, {"$set": updates})
    updated = await bookings.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": booking_id})
    return FacilityBookingResponse(**housing_router._facility_booking_response(updated or {**row, **updates}))



