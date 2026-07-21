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


@router.get("/database/backups")
async def database_backups_list(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    col = housing_router.get_collection("housing_backups")
    rows = (
        await col.find({"tenant_id": tenant_id, "app_key": app_key})
        .sort("created_at", -1)
        .limit(25)
        .to_list(length=25)
    )
    backups: list[dict[str, Any]] = []
    for row in rows:
        size_kb = row.get("size_kb")
        if size_kb is None:
            size_kb = 1
        backups.append(
            {
                "filename": str(row.get("filename") or ""),
                "created_at": row.get("created_at") or datetime.now(timezone.utc).isoformat(),
                "size_kb": int(size_kb),
            }
        )
    return backups


@router.post("/database/backup", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def database_backup_create(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    filename = f"{tenant_id}_{now.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}.json"
    payload = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "created_at": created_at,
        "kind": "metadata-only-backup",
        "note": "Compatibility backup created from GruhaMitra settings page.",
    }
    encoded_payload = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    size_kb = max(1, len(encoded_payload) // 1024)
    doc = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "filename": filename,
        "created_at": created_at,
        "size_kb": size_kb,
        "payload": payload,
    }
    await housing_router.get_collection("housing_backups").insert_one(doc)
    return {"message": "Backup created successfully", "filename": filename, "created_at": created_at, "size_kb": size_kb}


@router.post("/database/restore", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def database_backup_restore(
    filename: str = Query(..., min_length=1),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    doc = await housing_router.get_collection("housing_backups").find_one({"tenant_id": tenant_id, "app_key": app_key, "filename": filename})
    if not doc:
        raise HTTPException(status_code=404, detail="Backup file not found")
    return {"message": f"Restore prepared for '{filename}'. Restart backend to apply restored data."}


@router.get("/database/backups/{filename}/download")
async def database_backup_download(
    filename: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    doc = await housing_router.get_collection("housing_backups").find_one({"tenant_id": tenant_id, "app_key": app_key, "filename": filename})
    if not doc:
        raise HTTPException(status_code=404, detail="Backup file not found")

    payload = doc.get("payload") or {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "filename": filename,
        "created_at": doc.get("created_at"),
        "kind": "metadata-only-backup",
    }
    content = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

