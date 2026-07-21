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


@router.post("/move-governance/transfer-to-arrears", response_model=ArrearsResponse, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def move_transfer_to_arrears(
    payload: ArrearsTransferRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await transfer_to_arrears(tenant_id=tenant_id, app_key=app_key, payload=payload)
    return ArrearsResponse(**row)


@router.post("/move-governance/transfer-flat-to-flat", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def move_transfer_flat_to_flat(
    payload: FlatTransferRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    return await transfer_flat_to_flat(tenant_id=tenant_id, app_key=app_key, payload=payload)


@router.get("/move-governance/personal-arrears", response_model=list[ArrearsResponse])
async def move_list_personal_arrears(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_personal_arrears(tenant_id=tenant_id, app_key=app_key)
    return [ArrearsResponse(**row) for row in rows]


@router.get("/move-governance/generate-ndc/{flat_id}")
async def move_generate_ndc(
    flat_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    ndc = await generate_ndc(tenant_id=tenant_id, app_key=app_key, flat_id=flat_id)
    issued_at = ndc.get("issued_at")
    if isinstance(issued_at, datetime):
        issued_at_str = issued_at.strftime("%d-%m-%Y %H:%M")
    else:
        issued_at_str = str(issued_at or datetime.now(timezone.utc).strftime("%d-%m-%Y %H:%M"))
    pdf_bytes = housing_router._build_simple_pdf(
        title="No Dues Certificate (NDC)",
        top_margin=130.0,
        lines=[
            f"Flat Number: {flat_id}",
            f"Certificate Status: {ndc.get('status', 'issued')}",
            f"Issued At: {issued_at_str}",
            "",
            "This certifies that no outstanding dues were found for the above flat",
            "as on the issue date and time recorded in this certificate.",
        ],
    )
    headers = {"Content-Disposition": f'attachment; filename="NDC_{flat_id}.pdf"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/move-governance/police-verification-form/{member_id}")
@router.get("/move-governance/police-verification-form/{member_id}/")
async def move_police_verification_form(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    member = await housing_router.get_collection("housing_members").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member_type = str(member.get("member_type") or "").strip().lower()
    current_occupier = "Tenant" if member_type == "tenant" else "Owner"
    owner_for_flat = None
    if member_type == "tenant":
        owner_for_flat = await housing_router.get_collection("housing_members").find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "flat_number": member.get("flat_number"),
                "member_type": "owner",
            },
            sort=[("status", 1), ("updated_at", -1), ("created_at", -1)],
        )

    move_in = member.get("move_in_date")
    if isinstance(move_in, datetime):
        move_in_str = move_in.strftime("%d-%m-%Y")
    else:
        move_in_str = str(move_in or "N/A")
    pdf_bytes = housing_router._build_simple_pdf(
        title="Owner / Tenant Police Verification Form",
        top_margin=130.0,
        lines=[
            "To,",
            "The Station House Officer,",
            "Local Police Station",
            "",
            "Subject: Police Verification Request",
            "",
            f"Flat Number: {member.get('flat_number', 'N/A')}",
            f"Current Occupier: {current_occupier}",
            f"Resident Name: {member.get('name', 'N/A')}",
            f"Member Type: {str(member.get('member_type') or '').title() or 'N/A'}",
            f"Occupation: {member.get('occupation') or 'N/A'}",
            f"Phone: {member.get('phone_number', 'N/A')}",
            f"Email: {member.get('email', 'N/A')}",
            f"Move-In Date: {move_in_str}",
            f"Total Occupants: {member.get('total_occupants') or 'N/A'}",
            "",
            "Owner Details:",
            f"Owner Name: {(owner_for_flat or member).get('name', 'N/A')}",
            f"Owner Phone: {(owner_for_flat or member).get('phone_number', 'N/A')}",
            f"Owner Email: {(owner_for_flat or member).get('email', 'N/A')}",
            "",
            "Submitted for verification and society records.",
            "",
            "Signature (Resident): ___________________    Date: __________",
            "Signature (Society Office): _____________    Date: __________",
        ],
    )
    safe_member = re.sub(r"[^A-Za-z0-9_-]+", "_", str(member.get("name") or member_id)).strip("_") or member_id
    headers = {"Content-Disposition": f'attachment; filename="Police_Verification_{safe_member}.pdf"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/move-governance/tenant-id-form/{member_id}")
@router.get("/move-governance/tenant-id-form/{member_id}/")
async def move_tenant_id_form(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    member = await housing_router.get_collection("housing_members").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    move_in = member.get("move_in_date")
    if isinstance(move_in, datetime):
        move_in_str = move_in.strftime("%d-%m-%Y")
    else:
        move_in_str = str(move_in or "N/A")
    member_kind = str(member.get("member_type") or "").strip().lower()
    id_title = "Tenant ID Form" if member_kind == "tenant" else "Owner ID Form"
    pdf_bytes = housing_router._build_simple_pdf(
        title=id_title,
        top_margin=130.0,
        lines=[
            f"Flat Number: {member.get('flat_number', 'N/A')}",
            f"Name: {member.get('name', 'N/A')}",
            f"Member Type: {str(member.get('member_type') or '').title() or 'N/A'}",
            f"Move-In Date: {move_in_str}",
            f"Phone: {member.get('phone_number', 'N/A')}",
            f"Email: {member.get('email', 'N/A')}",
            f"Total Occupants: {member.get('total_occupants') or 'N/A'}",
            "",
            "ID / Address Proof Details:",
            "Government ID Type: ______________________",
            "Government ID Number: ____________________",
            "Permanent Address: _______________________",
            "",
            "Emergency Contact Name: __________________",
            "Emergency Contact Number: _______________",
            "",
            "Resident Signature: ______________________",
            "Society Office Seal & Signature: _________",
        ],
    )
    safe_member = re.sub(r"[^A-Za-z0-9_-]+", "_", str(member.get("name") or member_id)).strip("_") or member_id
    headers = {"Content-Disposition": f'attachment; filename="Tenant_ID_{safe_member}.pdf"'}
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.get("/move-governance/calculate-final-bill/{flat_id}", response_model=FinalBillResponse)
async def move_calculate_final_bill(
    flat_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await calculate_final_bill(tenant_id=tenant_id, app_key=app_key, flat_id=flat_id)
    return FinalBillResponse(**row)


@router.post("/move-governance/damage-claim", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def move_damage_claim(
    payload: DamageClaimCreate,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    return await raise_damage_claim(tenant_id=tenant_id, app_key=app_key, payload=payload)

