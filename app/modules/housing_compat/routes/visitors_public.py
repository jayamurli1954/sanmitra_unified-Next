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


@router.post("/visitors/verify-pass")
async def visitors_verify_pass(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="verify guest pass",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    code = str(payload.get("code") or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="Passcode or Visitor ID is required")

    # Search by passcode or visitor ID
    query = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "$or": [
            {"passcode": code},
            {"id": code}
        ]
    }
    row = await housing_router._visitors_collection().find_one(query)
    if not row:
        raise HTTPException(status_code=404, detail="Invalid pass or guest not found")

    if row.get("expires_at"):
        from datetime import datetime, timezone
        expires_dt = datetime.fromisoformat(row["expires_at"])
        if datetime.now(timezone.utc) > expires_dt:
            raise HTTPException(status_code=410, detail="This pass has expired")

    return housing_router._visitor_response(row)


@router.get("/visitors/public/{visitor_id}")
async def get_public_visitor_pass(visitor_id: str):
    doc = await housing_router._visitors_collection().find_one({"id": visitor_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Invite pass not found")

    expires_at = doc.get("expires_at")
    is_expired = False
    if expires_at:
        from datetime import datetime, timezone
        is_expired = datetime.now(timezone.utc) > datetime.fromisoformat(expires_at)

    return {
        "id": doc["id"],
        "visitor_name": doc["visitor_name"],
        "flat_number": doc["flat_number"],
        "passcode": doc["passcode"],
        "visitor_type": doc["visitor_type"],
        "status": doc["status"],
        "created_at": doc.get("created_at"),
        "expires_at": expires_at,
        "is_expired": is_expired
    }

