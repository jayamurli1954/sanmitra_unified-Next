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


def _staff_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "tenant_id": row.get("tenant_id"),
        "app_key": row.get("app_key"),
        "name": row.get("name") or "",
        "phone_number": row.get("phone_number") or "",
        "role": row.get("role") or "",
        "flat_number": row.get("flat_number"),
        "vehicle_type": row.get("vehicle_type") or "none",
        "vehicle_number": row.get("vehicle_number") or "",
        "status": row.get("status") or "active",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _attendance_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "tenant_id": row.get("tenant_id"),
        "app_key": row.get("app_key"),
        "staff_id": row.get("staff_id"),
        "name": row.get("name") or "",
        "role": row.get("role") or "",
        "flat_number": row.get("flat_number"),
        "vehicle_type": row.get("vehicle_type") or "none",
        "vehicle_number": row.get("vehicle_number") or "",
        "checked_in_at": row.get("checked_in_at"),
        "checked_out_at": row.get("checked_out_at"),
        "status": row.get("status") or "inside",
    }


@router.get("/staff")
async def staff_list(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    rows = await housing_router.get_collection("housing_staff_members").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=1000)
    return [_staff_response(row) for row in rows]


@router.post("/staff", response_model=StaffResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def staff_create(
    payload: StaffCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff create",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    existing = await housing_router.get_collection("housing_staff_members").find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "phone_number": payload.phone_number.strip()
    })
    if existing:
        raise HTTPException(status_code=400, detail="Staff member with this phone number already registered")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "name": payload.name.strip(),
        "phone_number": payload.phone_number.strip(),
        "role": payload.role.strip(),
        "flat_number": payload.flat_number,
        "vehicle_type": (payload.vehicle_type or "none").strip().lower(),
        "vehicle_number": (payload.vehicle_number or "").strip().upper(),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await housing_router.get_collection("housing_staff_members").insert_one(doc)
    return _staff_response(doc)


@router.put("/staff/{staff_id}", response_model=StaffResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def staff_update(
    staff_id: str,
    payload: StaffUpdateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff update",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    existing = await housing_router.get_collection("housing_staff_members").find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "id": staff_id
    })
    if not existing:
        raise HTTPException(status_code=404, detail="Staff member not found")

    updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.phone_number is not None:
        updates["phone_number"] = payload.phone_number.strip()
    if payload.role is not None:
        updates["role"] = payload.role.strip()
    if payload.flat_number is not None:
        updates["flat_number"] = payload.flat_number.strip().upper() if payload.flat_number else None
    if payload.vehicle_type is not None:
        updates["vehicle_type"] = payload.vehicle_type.strip().lower()
    if payload.vehicle_number is not None:
        updates["vehicle_number"] = payload.vehicle_number.strip().upper()
    if payload.status is not None:
        updates["status"] = payload.status

    await housing_router.get_collection("housing_staff_members").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": staff_id},
        {"$set": updates}
    )
    updated = await housing_router.get_collection("housing_staff_members").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": staff_id})
    return _staff_response(updated or existing)


@router.delete("/staff/{staff_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def staff_delete(
    staff_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff delete",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    res = await housing_router.get_collection("housing_staff_members").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": staff_id},
        {"$set": {"status": "inactive", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff member not found")
    return {"status": "success"}


@router.get("/staff/attendance")
async def staff_attendance_list(
    date_str: str | None = Query(default=None, alias="date"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff attendance list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if date_str:
        query["checked_in_at"] = {"$regex": f"^{date_str}"}
    else:
        today = date.today().isoformat()
        query["checked_in_at"] = {"$regex": f"^{today}"}

    rows = await housing_router.get_collection("housing_staff_attendance").find(query).sort("checked_in_at", -1).to_list(length=1000)
    return [_attendance_response(row) for row in rows]


@router.post("/staff/attendance/{staff_id}/check-in", response_model=StaffAttendanceResponse)
async def staff_attendance_check_in(
    staff_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff check-in",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    staff = await housing_router.get_collection("housing_staff_members").find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "id": staff_id,
        "status": "active"
    })
    if not staff:
        raise HTTPException(status_code=400, detail="Active staff member not found")

    already_in = await housing_router.get_collection("housing_staff_attendance").find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "staff_id": staff_id,
        "status": "inside"
    })
    if already_in:
        return _attendance_response(already_in)

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "staff_id": staff_id,
        "name": staff.get("name"),
        "role": staff.get("role"),
        "flat_number": staff.get("flat_number"),
        "vehicle_type": staff.get("vehicle_type") or "none",
        "vehicle_number": staff.get("vehicle_number") or "",
        "checked_in_at": now,
        "checked_out_at": None,
        "status": "inside"
    }
    await housing_router.get_collection("housing_staff_attendance").insert_one(doc)
    return _attendance_response(doc)


@router.post("/staff/attendance/{log_id}/check-out", response_model=StaffAttendanceResponse)
async def staff_attendance_check_out(
    log_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="staff check-out",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    log = await housing_router.get_collection("housing_staff_attendance").find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "id": log_id
    })
    if not log:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if log.get("status") == "exited":
        return _attendance_response(log)

    now = datetime.now(timezone.utc).isoformat()
    await housing_router.get_collection("housing_staff_attendance").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": log_id},
        {"$set": {"status": "exited", "checked_out_at": now}}
    )
    updated = await housing_router.get_collection("housing_staff_attendance").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": log_id})
    return _attendance_response(updated or log)

