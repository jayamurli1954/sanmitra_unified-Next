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


@router.get("/visitors")
async def visitors_list(
    status: str | None = Query(default=None),
    visitor_type: str | None = Query(default=None),
    flat_number: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor register list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    access_query = await housing_router._visitor_access_query(current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if access_query:
        query.update(access_query)
    if isinstance(status, str) and status.strip():
        query["status"] = str(status).strip().lower()
    if isinstance(visitor_type, str) and visitor_type.strip():
        query["visitor_type"] = str(visitor_type).strip().lower()
    if isinstance(flat_number, str) and flat_number.strip() and housing_router._can_manage_visitors(current_user.get("role")):
        query["flat_number"] = housing_router._normalize_flat_number(flat_number)
    rows = await housing_router._visitors_collection().find(query).sort("created_at", -1).to_list(length=1000)
    return [housing_router._visitor_response(row) for row in rows]


import asyncio

def _send_web_push_sync(subscription_info: dict, data: str, private_key: str) -> None:
    try:
        pywebpush.webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=private_key,
            vapid_claims={"sub": "mailto:support@sanmitra.net"}
        )
    except Exception:
        pass


async def _send_web_push_notification(
    tenant_id: str, app_key: str, flat_number: str, title: str, body: str, visitor_id: str
) -> None:
    app_settings = housing_router.get_settings()
    sub_col = housing_router.get_collection("housing_web_push_subscriptions")
    cursor = sub_col.find({"tenant_id": tenant_id, "app_key": app_key, "flat_number": flat_number})
    subscriptions = await cursor.to_list(length=100)
    if not subscriptions:
        return

    payload = {
        "title": title,
        "body": body,
        "data": {
            "visitor_id": visitor_id,
            "flat_number": flat_number,
            "type": "visitor_approval",
        },
    }
    data_str = json.dumps(payload)

    for sub_doc in subscriptions:
        if not app_settings.VAPID_PRIVATE_KEY:
            continue
        await asyncio.to_thread(
            _send_web_push_sync,
            sub_doc["subscription"],
            data_str,
            app_settings.VAPID_PRIVATE_KEY
        )


@router.post("/visitors")
async def visitors_create(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor register create",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    visitor_name = str(payload.get("visitor_name") or payload.get("name") or "").strip()
    flat_number = housing_router._normalize_flat_number(payload.get("flat_number"))
    if not visitor_name:
        raise HTTPException(status_code=400, detail="visitor_name is required")
    if not flat_number:
        raise HTTPException(status_code=400, detail="flat_number is required")

    visitor_type = str(payload.get("visitor_type") or "guest").strip().lower()
    if visitor_type not in {"guest", "delivery", "cab", "vendor", "service_staff", "domestic_help", "other"}:
        visitor_type = "other"
    creator = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")
    status = "pending"
    if not housing_router._can_manage_visitors(current_user.get("role")):
        audience = await housing_router._current_user_message_audience(current_user=current_user, tenant_id=tenant_id, app_key=app_key)
        if flat_number not in audience["flats"]:
            raise HTTPException(status_code=403, detail="Residents can create expected visitors only for their own flat")
        status = "approved"

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    validity_hours = int(payload.get("validity_hours") or 24)
    if validity_hours not in {4, 8, 12, 24}:
        validity_hours = 24

    from datetime import timedelta
    expires_at = (now_dt + timedelta(hours=validity_hours)).isoformat()

    vehicle_type = str(payload.get("vehicle_type") or "none").strip().lower()
    import random
    passcode = "".join(random.choices("0123456789", k=6))

    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "flat_number": flat_number,
        "visitor_type": visitor_type,
        "visitor_name": visitor_name,
        "phone_number": str(payload.get("phone_number") or "").strip(),
        "vehicle_type": vehicle_type,
        "vehicle_number": str(payload.get("vehicle_number") or "").strip().upper(),
        "purpose": str(payload.get("purpose") or "").strip(),
        "vendor_name": str(payload.get("vendor_name") or "").strip(),
        "passcode": passcode,
        "status": status,
        "approval_by": creator if status == "approved" else None,
        "approved_at": now if status == "approved" else None,
        "rejected_reason": None,
        "checked_in_at": None,
        "checked_out_at": None,
        "created_by": creator,
        "created_at": now,
        "updated_at": now,
        "validity_hours": validity_hours,
        "expires_at": expires_at,
    }
    await housing_router._visitors_collection().insert_one(doc)

    if status == "pending":
        if visitor_type == "delivery":
            vendor = str(payload.get("vendor_name") or payload.get("visitor_name") or "Delivery").strip()
            title = f"Delivery Alert: {vendor}"
            body = f"A delivery person from {vendor} is at the gate. Tap to approve."
        elif visitor_type == "guest":
            title = f"Guest Arrival: {visitor_name}"
            body = f"{visitor_name} is at the gate. Tap to approve."
        else:
            title = f"Visitor Alert: {visitor_name}"
            body = f"A {visitor_type} is at the gate. Tap to approve."

        asyncio.create_task(
            housing_router._send_web_push_notification(
                tenant_id=tenant_id,
                app_key=app_key,
                flat_number=flat_number,
                title=title,
                body=body,
                visitor_id=doc["id"],
            )
        )

    return housing_router._visitor_response(doc)


@router.post("/visitors/{visitor_id}/approve")
async def visitors_approve(
    visitor_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor approval",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router._get_visitor_or_404(visitor_id=visitor_id, current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if row.get("status") in {"inside", "exited", "cancelled"}:
        raise HTTPException(status_code=400, detail="Visitor entry cannot be approved in its current status")
    actor = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router._visitors_collection().update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id},
        {"$set": {"status": "approved", "approval_by": actor, "approved_at": now, "updated_at": now}},
    )
    updated = await housing_router._visitors_collection().find_one({"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id})
    return housing_router._visitor_response(updated or row)


@router.post("/visitors/{visitor_id}/reject")
async def visitors_reject(
    visitor_id: str,
    payload: dict[str, Any] | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor rejection",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router._get_visitor_or_404(visitor_id=visitor_id, current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if row.get("status") in {"inside", "exited"}:
        raise HTTPException(status_code=400, detail="Visitor already entered or exited")
    actor = str(current_user.get("sub") or current_user.get("user_id") or current_user.get("email") or "system")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router._visitors_collection().update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id},
        {
            "$set": {
                "status": "rejected",
                "approval_by": actor,
                "rejected_reason": str((payload or {}).get("reason") or "").strip() or None,
                "updated_at": now,
            }
        },
    )
    updated = await housing_router._visitors_collection().find_one({"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id})
    return housing_router._visitor_response(updated or row)


@router.post("/visitors/{visitor_id}/check-in")
async def visitors_check_in(
    visitor_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor check-in",
    )
    if not housing_router._can_manage_visitors(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only gate/security or admin can check visitors in")
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router._get_visitor_or_404(visitor_id=visitor_id, current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if row.get("status") in {"rejected", "cancelled", "exited"}:
        raise HTTPException(status_code=400, detail="Visitor entry cannot be checked in")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router._visitors_collection().update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id},
        {"$set": {"status": "inside", "checked_in_at": now, "updated_at": now}},
    )
    updated = await housing_router._visitors_collection().find_one({"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id})
    return housing_router._visitor_response(updated or row)


@router.post("/visitors/{visitor_id}/check-out")
async def visitors_check_out(
    visitor_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="visitor check-out",
    )
    if not housing_router._can_manage_visitors(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only gate/security or admin can check visitors out")
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    row = await housing_router._get_visitor_or_404(visitor_id=visitor_id, current_user=current_user, tenant_id=tenant_id, app_key=app_key)
    if row.get("status") != "inside":
        raise HTTPException(status_code=400, detail="Only visitors currently inside can be checked out")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router._visitors_collection().update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id},
        {"$set": {"status": "exited", "checked_out_at": now, "updated_at": now}},
    )
    updated = await housing_router._visitors_collection().find_one({"tenant_id": tenant_id, "app_key": app_key, "id": visitor_id})
    return housing_router._visitor_response(updated or row)


