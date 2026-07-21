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


@router.get("/complaints/")
async def complaints_list(
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance bill regeneration",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if status:
        query["status"] = str(status).strip().lower()

    role = str(current_user.get("role") or "").strip().lower()
    user_sub = str(current_user.get("sub") or "").strip()
    if not housing_router._can_manage_complaints(role):
        query["$or"] = [{"scope": "common_area"}, {"created_by": user_sub}]

    col = housing_router._complaints_collection()
    rows = await col.find(query).sort("created_at", -1).to_list(length=1000)
    return [
        {
            "id": row.get("id"),
            "title": row.get("title") or "",
            "description": row.get("description") or "",
            "type": row.get("type") or "other",
            "priority": row.get("priority") or "medium",
            "scope": row.get("scope") or "individual",
            "status": row.get("status") or "open",
            "user_name": row.get("user_name") or "Resident",
            "flat_number": row.get("flat_number") or "N/A",
            "created_by": row.get("created_by"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "resolved_at": row.get("resolved_at"),
        }
        for row in rows
    ]


@router.post("/complaints/")
async def complaints_create(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())

    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if not description:
        raise HTTPException(status_code=400, detail="description is required")

    complaint_type = str(payload.get("type") or "other").strip().lower() or "other"
    priority = str(payload.get("priority") or "medium").strip().lower() or "medium"
    scope = str(payload.get("scope") or "individual").strip().lower() or "individual"
    if priority not in {"low", "medium", "high"}:
        priority = "medium"
    if scope not in {"individual", "common_area"}:
        scope = "individual"

    now = datetime.now(timezone.utc).isoformat()
    creator_email = str(current_user.get("email") or "").strip()
    creator_sub = str(current_user.get("sub") or "system")
    user_name = (
        str(current_user.get("full_name") or "").strip()
        or creator_email
        or "Resident"
    )
    flat_number = str(current_user.get("flat_number") or "").strip() or "N/A"
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "title": title,
        "description": description,
        "type": complaint_type,
        "priority": priority,
        "scope": scope,
        "status": "open",
        "user_name": user_name,
        "flat_number": flat_number,
        "created_by": creator_sub,
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }
    await housing_router._complaints_collection().insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@router.patch("/complaints/{complaint_id}")
async def complaints_update(
    complaint_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    col = housing_router._complaints_collection()
    row = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": complaint_id})
    if not row:
        raise HTTPException(status_code=404, detail="Complaint not found")

    role = str(current_user.get("role") or "").strip().lower()
    user_sub = str(current_user.get("sub") or "").strip()
    allowed_status = {"open", "in_progress", "resolved", "closed"}
    requested_status = str(payload.get("status") or "").strip().lower()
    if requested_status and requested_status not in allowed_status:
        raise HTTPException(status_code=400, detail="Invalid status")

    can_manage = housing_router._can_manage_complaints(role)
    if not can_manage:
        if row.get("created_by") != user_sub:
            raise HTTPException(status_code=403, detail="Only creator or admin can update this complaint")
        if requested_status and requested_status != "closed":
            raise HTTPException(status_code=403, detail="Residents can only close their own complaint")

    update_doc: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if requested_status:
        update_doc["status"] = requested_status
        if requested_status in {"resolved", "closed"}:
            update_doc["resolved_at"] = update_doc["updated_at"]

    if len(update_doc) == 1:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    await col.update_one({"tenant_id": tenant_id, "app_key": app_key, "id": complaint_id}, {"$set": update_doc})
    updated = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": complaint_id})
    if not updated:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {k: v for k, v in updated.items() if k != "_id"}

