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


@router.post("/member-onboarding", response_model=MemberResponse)
@router.post("/member-onboarding/", response_model=MemberResponse)
async def member_onboarding_create(
    payload: MemberCreateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    doc = await create_member(tenant_id=tenant_id, app_key=app_key, payload=payload)
    return MemberResponse(**doc)


@router.get("/member-onboarding/template")
async def member_onboarding_template_download():
    csv_text = (
        "name,phone_number,email,flat_number,member_type,move_in_date,total_occupants,occupation,is_primary,is_mobile_public\n"
        "Raghavan Iyer,9876512340,raghavan.iyer01@gmail.com,A-101,owner,2025-12-01,5,Professional,true,true\n"
        "Lakshmi Narayanan,9876523451,lakshmi.narayanan02@gmail.com,A-102,owner,2026-01-01,4,Homemaker,true,false\n"
        "Suresh Babu,9876534562,suresh.babu03@gmail.com,A-103,tenant,2025-12-01,6,Doctor,true,true\n"
    )
    headers = {"Content-Disposition": 'attachment; filename="members_template.csv"'}
    return StreamingResponse(BytesIO(csv_text.encode("utf-8")), media_type="text/csv", headers=headers)


@router.post("/member-onboarding/bulk-import", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def member_onboarding_bulk_import(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    file_name = str(file.filename or "").strip().lower()
    content_type = str(file.content_type or "").strip().lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be less than 5MB")

    is_csv = file_name.endswith(".csv") or "csv" in content_type
    is_excel = file_name.endswith(".xlsx") or "spreadsheetml" in content_type
    if not (is_csv or is_excel):
        raise HTTPException(status_code=400, detail="Only CSV or XLSX files are supported")

    try:
        rows = housing_router._parse_csv_rows(content) if is_csv else housing_router._parse_xlsx_rows(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in uploaded file")

    created = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    created_members: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=2):
        try:
            payload = housing_router._coerce_bulk_member_payload(row, idx)
            doc = await create_member(tenant_id=tenant_id, app_key=app_key, payload=payload)
            created += 1
            created_members.append(
                {
                    "id": str(doc.get("id") or ""),
                    "flat_number": str(doc.get("flat_number") or ""),
                    "name": str(doc.get("name") or ""),
                }
            )
        except HTTPException as exc:
            failed += 1
            errors.append({"row": idx, "error": str(exc.detail)})
        except Exception as exc:
            failed += 1
            errors.append({"row": idx, "error": str(exc)})

    return {
        "status": "completed",
        "total_rows": len(rows),
        "created": created,
        "failed": failed,
        "created_members": created_members[:100],
        "errors": errors[:200],
    }


@router.get("/onboarding-imports/templates/{kind}.csv")
async def onboarding_import_template(kind: str):
    if kind == "flats":
        csv_text = "flat_number,block,floor,status,area_sqft,bedrooms,parking_slots\nA-101,A,1,vacant,1000,2,P1\n"
    else:
        csv_text = "name,phone_number,email,flat_number,member_type,status,total_occupants\nResident,9999999999,resident@example.com,A-101,owner,active,1\n"
    return Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})


@router.post("/onboarding-imports/demo/import", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def onboarding_import_demo(current_user: dict = Depends(get_current_user)):
    return {"status": "ok", "message": "Demo import hook acknowledged", "tenant_id": current_user.get("tenant_id")}


@router.post("/onboarding-imports/import/flats", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def onboarding_import_flats(
    file: UploadFile = File(...),
    replace_existing: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    content = (await file.read()).decode("utf-8-sig", "replace")
    rows = list(csv.DictReader(content.splitlines()))
    if replace_existing:
        await housing_router.get_collection("housing_flats").delete_many({"tenant_id": tenant_id, "app_key": app_key})
    imported = 0
    errors: list[dict[str, Any]] = []
    for index, item in enumerate(rows, start=2):
        flat_number = str(item.get("flat_number") or item.get("unit") or "").strip()
        if not flat_number:
            errors.append({"row": index, "error": "flat_number is required"})
            continue
        try:
            await create_flat(
                tenant_id=tenant_id,
                app_key=app_key,
                payload=FlatCreateRequest(
                    flat_number=flat_number,
                    block=(item.get("block") or None),
                    floor=int(item["floor"]) if str(item.get("floor") or "").strip() else None,
                    status=(item.get("status") or "vacant"),
                    area_sqft=float(item["area_sqft"]) if str(item.get("area_sqft") or "").strip() else None,
                    bedrooms=int(item["bedrooms"]) if str(item.get("bedrooms") or "").strip() else None,
                    parking_slots=(item.get("parking_slots") or None),
                ),
            )
            imported += 1
        except Exception as exc:
            errors.append({"row": index, "error": str(exc)})
    return {"status": "ok", "imported": imported, "errors": errors, "total_rows": len(rows)}


@router.post("/onboarding-imports/import/members", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def onboarding_import_members(
    file: UploadFile = File(...),
    update_existing: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    result = await member_onboarding_bulk_import(file=file, current_user=current_user, x_tenant_id=x_tenant_id)
    result["update_existing"] = update_existing
    return result


@router.get("/member-onboarding", response_model=list[MemberResponse])
@router.get("/member-onboarding/", response_model=list[MemberResponse])
async def member_onboarding_list(
    status_filter: str | None = None,
    flat_number: str | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_members(tenant_id=tenant_id, app_key=app_key, status_filter=status_filter, flat_number=flat_number)
    return [MemberResponse(**row) for row in rows]


@router.get("/member-onboarding/my-profile", response_model=MemberResponse)
async def member_onboarding_my_profile(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    email = str(current_user.get("email") or "").strip().lower()
    rows = await list_members(tenant_id=tenant_id, app_key=app_key, status_filter=None, flat_number=None)
    for row in rows:
        if str(row.get("email") or "").strip().lower() == email:
            return MemberResponse(**row)
    raise HTTPException(status_code=404, detail="Member profile not found")


@router.get("/member-onboarding/debug")
async def member_onboarding_debug(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    rows = await list_members(tenant_id=tenant_id, app_key=app_key, status_filter=None, flat_number=None)
    return {"tenant_id": tenant_id, "app_key": app_key, "member_count": len(rows)}


@router.patch("/member-onboarding/{member_id}", response_model=MemberResponse)
@router.patch("/member-onboarding/{member_id}/", response_model=MemberResponse)
async def member_onboarding_update(
    member_id: str,
    payload: MemberUpdateRequest,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await update_member(tenant_id=tenant_id, app_key=app_key, member_id=member_id, payload=payload)
    return MemberResponse(**row)


@router.get("/member-onboarding/{member_id}/checklist", response_model=MemberChecklistResponse)
@router.get("/member-onboarding/{member_id}/checklist/", response_model=MemberChecklistResponse)
async def member_onboarding_checklist_get(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await get_member_checklist(tenant_id=tenant_id, app_key=app_key, member_id=member_id)
    return MemberChecklistResponse(**row)


@router.patch("/member-onboarding/{member_id}/checklist", response_model=MemberChecklistResponse)
@router.patch("/member-onboarding/{member_id}/checklist/", response_model=MemberChecklistResponse)
async def member_onboarding_checklist_update(
    member_id: str,
    payload: MemberChecklistUpdate,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = str(current_user.get("app_key") or "gruhamitra")
    row = await update_member_checklist(
        tenant_id=tenant_id,
        app_key=app_key,
        member_id=member_id,
        payload=payload,
        updated_by=str(current_user.get("sub") or "system"),
    )
    return MemberChecklistResponse(**row)


