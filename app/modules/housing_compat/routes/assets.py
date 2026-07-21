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


@router.get("/assets")
@router.get("/assets/")
async def assets_list(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rows = (
        await housing_router.get_collection("housing_assets")
        .find({"tenant_id": tenant_id, "app_key": app_key})
        .sort([("created_at", -1)])
        .to_list(length=1000)
    )
    return [housing_router._asset_response(row) for row in rows]


@router.post("/assets", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
@router.post("/assets/", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def assets_create(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Asset name is required")
    category = str(payload.get("category") or "other").strip().lower() or "other"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "asset_code": await housing_router._next_asset_code(tenant_id=tenant_id, app_key=app_key, category=category),
        "name": name,
        "category": category,
        "account_code": housing_router._canonical_gruha_account_code(payload.get("account_code") or "16003"),
        "quantity": max(1, housing_router._safe_int(payload.get("quantity"), default=1)),
        "location": str(payload.get("location") or "").strip(),
        "status": str(payload.get("status") or "Active").strip() or "Active",
        "acquisition_type": str(payload.get("acquisition_type") or "builder_handover").strip(),
        "handover_date": payload.get("handover_date"),
        "purchase_date": payload.get("purchase_date"),
        "original_cost": housing_router._safe_float(payload.get("original_cost")),
        "depreciation_method": str(payload.get("depreciation_method") or "straight_line").strip(),
        "depreciation_rate": housing_router._safe_float(payload.get("depreciation_rate")),
        "useful_life_years": housing_router._safe_int(payload.get("useful_life_years"), default=0),
        "residual_value": housing_router._safe_float(payload.get("residual_value")),
        "amc_vendor": str(payload.get("amc_vendor") or "").strip(),
        "amc_expiry": payload.get("amc_expiry"),
        "insurance_policy_no": str(payload.get("insurance_policy_no") or "").strip(),
        "insurance_expiry": payload.get("insurance_expiry"),
        "vendor_name": str(payload.get("vendor_name") or "").strip(),
        "invoice_no": str(payload.get("invoice_no") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
        "is_scrapped": False,
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    if doc["acquisition_type"] == "builder_handover" and doc["original_cost"] > 0:
        entry = await housing_router._post_asset_capitalization_journal(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            asset=doc,
            created_by=str(current_user.get("sub") or "system"),
        )
        if entry is not None:
            doc["journal_entry_id"] = entry.id
            doc["accounting_posting_status"] = "posted"
            doc["accounting_posted_at"] = now
    elif doc["acquisition_type"] == "society_purchase" and doc["original_cost"] > 0:
        doc["accounting_posting_status"] = "pending_payment_account"
    else:
        doc["accounting_posting_status"] = "not_required"
    await housing_router.get_collection("housing_assets").insert_one(doc)
    return housing_router._asset_response(doc)


@router.get("/assets/{asset_id}")
async def assets_get(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    row = await housing_router.get_collection("housing_assets").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": asset_id})
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    return housing_router._asset_response(row)


@router.post("/assets/{asset_id}/post-accounting", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def assets_post_accounting(
    asset_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    assets = housing_router.get_collection("housing_assets")
    row = await assets.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": asset_id})
    if not row:
        raise HTTPException(status_code=404, detail="Asset not found")
    if row.get("journal_entry_id"):
        return housing_router._asset_response(row)

    entry = await housing_router._post_asset_capitalization_journal(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        asset=row,
        created_by=str(current_user.get("sub") or "system"),
    )
    if entry is None:
        raise HTTPException(status_code=422, detail="This asset does not require automatic accounting posting.")

    now = datetime.now(timezone.utc).isoformat()
    await assets.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": asset_id},
        {
            "$set": {
                "journal_entry_id": entry.id,
                "accounting_posting_status": "posted",
                "accounting_posted_at": now,
                "updated_at": now,
            }
        },
    )
    row.update(
        {
            "journal_entry_id": entry.id,
            "accounting_posting_status": "posted",
            "accounting_posted_at": now,
            "updated_at": now,
        }
    )
    return housing_router._asset_response(row)


@router.post("/assets/{asset_id}/scrap", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def assets_scrap(
    asset_id: str,
    scrapping_reason: str = Query(default=""),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    result = await housing_router.get_collection("housing_assets").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": asset_id},
        {
            "$set": {
                "status": "Scrapped",
                "is_scrapped": True,
                "scrapping_reason": scrapping_reason,
                "scrapped_at": now,
                "updated_at": now,
            }
        },
    )
    if getattr(result, "matched_count", 0) == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    row = await housing_router.get_collection("housing_assets").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": asset_id})
    return housing_router._asset_response(row or {})

