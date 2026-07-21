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


@router.get("/settings/society", response_model=SocietySettingsResponse)
async def society_settings_get(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="society settings read",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router.get_society_settings(tenant_id=tenant_id, app_key=app_key)
    return SocietySettingsResponse(**row)


@router.patch("/settings/society", response_model=SocietySettingsResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def society_settings_patch(
    payload: SocietySettingsUpdate,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="society settings update",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router.save_society_settings(tenant_id=tenant_id, app_key=app_key, payload=payload)
    return SocietySettingsResponse(**row)


@router.get("/flats", response_model=list[FlatResponse])
@router.get("/flats/", response_model=list[FlatResponse])
async def flats_list(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await housing_router.list_flats(tenant_id=tenant_id, app_key=app_key)
    occupants = await housing_router._flat_occupants_map(tenant_id=tenant_id, app_key=app_key)
    for row in rows:
        row["occupants"] = occupants.get(str(row.get("flat_number") or "").strip().upper(), 0)
    return [FlatResponse(**row) for row in rows]


@router.get("/flats/{flat_id}", response_model=FlatResponse)
async def flats_get(
    flat_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await get_flat(tenant_id=tenant_id, app_key=app_key, flat_id=flat_id)
    return FlatResponse(**row)


@router.post("/flats/", response_model=FlatResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def flats_create(
    payload: FlatCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await create_flat(tenant_id=tenant_id, app_key=app_key, payload=payload)
    return FlatResponse(**row)


@router.put("/flats/{flat_id}", response_model=FlatResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def flats_update(
    flat_id: str,
    payload: FlatUpdateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await update_flat(tenant_id=tenant_id, app_key=app_key, flat_id=flat_id, payload=payload)
    return FlatResponse(**row)


@router.get("/financial-years/", response_model=list[FinancialYearResponse])
async def financial_years_list(
    include_closed: bool = True,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_financial_years(tenant_id=tenant_id, app_key=app_key, include_closed=include_closed)
    return [FinancialYearResponse(**row) for row in rows]


@router.get("/financial-years/active", response_model=FinancialYearResponse)
async def financial_year_active(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await get_active_financial_year(tenant_id=tenant_id, app_key=app_key)
    return FinancialYearResponse(**row)


@router.post("/financial-years/", response_model=FinancialYearResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def financial_year_create(
    payload: FinancialYearCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await create_financial_year(tenant_id=tenant_id, app_key=app_key, payload=payload)
    return FinancialYearResponse(**row)


@router.post("/financial-years/{year_id}/provisional-close", response_model=FinancialYearResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def financial_year_provisional_close(
    year_id: str,
    payload: FinancialYearCloseRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await provisional_close_financial_year(tenant_id=tenant_id, app_key=app_key, year_id=year_id, payload=payload)
    return FinancialYearResponse(**row)


@router.post("/financial-years/{year_id}/final-close", response_model=FinancialYearResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def financial_year_final_close(
    year_id: str,
    payload: FinancialYearCloseRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await final_close_financial_year(tenant_id=tenant_id, app_key=app_key, year_id=year_id, payload=payload)
    return FinancialYearResponse(**row)


@router.post("/v2/societies/{society_id}/join-requests", response_model=PublicJoinRequestResponse)
@router.post("/v2/public/societies/{society_id}/join-requests", response_model=PublicJoinRequestResponse)
async def public_join_request_create(society_id: str, payload: PublicJoinRequestCreate):
    doc = await create_public_join_request(society_id=society_id, payload=payload)
    return PublicJoinRequestResponse(
        membership_id=doc["id"],
        society_id=doc["society_id"],
        status=doc["status"],
        message="Join request submitted. Wait for admin approval before completing registration.",
    )


@router.get("/v2/societies/search", response_model=list[SocietySearchItem])
async def societies_search(q: str | None = None, city: str | None = None, pin_code: str | None = None):
    rows = await search_societies(q=q, city=city, pin_code=pin_code)
    return [SocietySearchItem(**row) for row in rows]


@router.get("/v2/societies/{society_id}", response_model=SocietySearchItem)
@router.get("/society/{society_id}", response_model=SocietySearchItem)
async def society_get(society_id: str):
    row = await get_society(society_id=society_id)
    return SocietySearchItem(**row)


@router.get("/v2/societies/{society_id}/units")
async def society_units_list(society_id: str):
    return await list_society_units(society_id=society_id, app_key="gruhamitra")


@router.get("/v2/me/memberships", response_model=list[MembershipResponse])
async def my_memberships_list(current_user: dict = Depends(get_current_user)):
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_my_memberships(email=str(current_user.get("email") or ""), app_key=app_key)
    return [MembershipResponse(**row) for row in rows]


@router.post(
    "/v2/public/residents/complete-registration",
    response_model=CompleteResidentRegistrationResponse,
)
async def resident_complete_registration(payload: CompleteResidentRegistrationRequest):
    row = await complete_resident_registration(payload=payload)
    return CompleteResidentRegistrationResponse(**row)


@router.get("/v2/societies/{society_id}/join-requests", response_model=list[MembershipResponse])
async def join_requests_list(
    society_id: str,
    status_filter: str = "pending",
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    if tenant_id != society_id and current_user.get("role") != "super_admin":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Access denied to this society")
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_join_requests(society_id=society_id, app_key=app_key, status=status_filter)
    return [MembershipResponse(**row) for row in rows]


@router.post("/v2/join-requests/{membership_id}/approve", response_model=MembershipResponse)
async def join_request_approve(
    membership_id: str,
    payload: ApproveJoinRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await approve_join_request(
        membership_id=membership_id,
        approver=str(current_user.get("sub") or "system"),
        tenant_scope=tenant_id,
        app_key=app_key,
        payload=payload,
    )
    return MembershipResponse(**row)


@router.post("/v2/join-requests/{membership_id}/reject", response_model=MembershipResponse)
async def join_request_reject(
    membership_id: str,
    payload: RejectJoinRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await reject_join_request(
        membership_id=membership_id,
        rejector=str(current_user.get("sub") or "system"),
        tenant_scope=tenant_id,
        app_key=app_key,
        payload=payload,
    )
    return MembershipResponse(**row)

