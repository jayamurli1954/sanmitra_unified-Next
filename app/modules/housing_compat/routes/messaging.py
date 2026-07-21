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


@router.post("/messages/rooms")
async def messages_create_room(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    if not housing_router._can_manage_chat_rooms(current_user.get("role")):
        raise HTTPException(status_code=403, detail="Only admin/secretary can create chat rooms")

    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    room_type = str(payload.get("type") or "general").strip().lower() or "general"
    description = str(payload.get("description") or "").strip()
    audience_type = str(payload.get("audience_type") or "public").strip().lower() or "public"
    if audience_type not in {"public", "flats"}:
        raise HTTPException(status_code=400, detail="audience_type must be public or flats")
    allowed_flat_numbers = housing_router._normalize_flat_numbers(
        payload.get("allowed_flat_numbers") or payload.get("flat_numbers") or []
    )
    if audience_type == "flats" and not allowed_flat_numbers:
        raise HTTPException(status_code=400, detail="Select at least one flat for a restricted room")
    now = datetime.now(timezone.utc).isoformat()
    room_id = str(uuid4())
    doc = {
        "id": room_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "name": name,
        "type": room_type,
        "description": description,
        "audience_type": audience_type,
        "allowed_flat_numbers": allowed_flat_numbers if audience_type == "flats" else [],
        "allowed_member_ids": [],
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "updated_at": now,
        "last_message_at": None,
    }
    rooms_col, _ = housing_router._message_collections()
    await rooms_col.insert_one(doc)
    return housing_router._room_response(doc)


@router.get("/messages/rooms/{room_id}/messages")
async def messages_list_for_room(
    room_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rooms_col, messages_col = housing_router._message_collections()
    room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not await housing_router._can_access_message_room(room=room, current_user=current_user, tenant_id=tenant_id, app_key=app_key):
        raise HTTPException(status_code=404, detail="Room not found")
    now = datetime.now(timezone.utc).isoformat()
    await messages_col.delete_many({"tenant_id": tenant_id, "app_key": app_key, "room_id": room_id, "expires_at": {"$lte": now}})
    rows = (
        await messages_col.find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "room_id": room_id,
                "$or": [{"expires_at": {"$exists": False}}, {"expires_at": {"$gt": now}}],
            }
        )
        .sort("created_at", 1)
        .to_list(length=limit)
    )
    return [housing_router._message_response(row) for row in rows]


@router.get("/messages/rooms/{room_id}/messages/{message_id}/attachments/{attachment_id}")
async def messages_download_attachment(
    room_id: str,
    message_id: str,
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rooms_col, messages_col = housing_router._message_collections()
    room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not await housing_router._can_access_message_room(room=room, current_user=current_user, tenant_id=tenant_id, app_key=app_key):
        raise HTTPException(status_code=404, detail="Room not found")
    message = await messages_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "room_id": room_id, "id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Attachment not found")
    expires_at = str(message.get("expires_at") or "")
    if expires_at and expires_at <= datetime.now(timezone.utc).isoformat():
        await messages_col.delete_one({"tenant_id": tenant_id, "app_key": app_key, "room_id": room_id, "id": message_id})
        raise HTTPException(status_code=404, detail="Attachment expired")
    for item in message.get("attachments") or []:
        if isinstance(item, dict) and item.get("id") == attachment_id:
            headers = {"Content-Disposition": f'attachment; filename="{housing_router._safe_file_name(item.get("file_name") or "attachment", "attachment")}"'}
            return Response(content=bytes(item.get("content") or b""), media_type=item.get("content_type") or "application/octet-stream", headers=headers)
    raise HTTPException(status_code=404, detail="Attachment not found")


@router.post("/messages/rooms/{room_id}/messages")
async def messages_send_to_room(
    room_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rooms_col, messages_col = housing_router._message_collections()
    room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not await housing_router._can_access_message_room(room=room, current_user=current_user, tenant_id=tenant_id, app_key=app_key):
        raise HTTPException(status_code=404, detail="Room not found")

    content = str(payload.get("text") or payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="text is required")

    now = datetime.now(timezone.utc).isoformat()
    retention_days = housing_router._message_retention_days(payload.get("retention_days"))
    expires_at = (datetime.now(timezone.utc) + timedelta(days=retention_days)).isoformat()
    sender_name = (
        str(current_user.get("full_name") or "").strip()
        or str(current_user.get("email") or "").strip()
        or "User"
    )
    message_doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "room_id": room_id,
        "sender_id": str(current_user.get("sub") or "system"),
        "sender_name": sender_name,
        "content": content,
        "message_type": "text",
        "attachments": [],
        "retention_days": retention_days,
        "expires_at": expires_at,
        "created_at": now,
    }
    await messages_col.insert_one(message_doc)
    await rooms_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": room_id},
        {"$set": {"updated_at": now, "last_message_at": now}},
    )
    return housing_router._message_response(message_doc)


@router.post("/messages/rooms/{room_id}/messages/with-attachment")
async def messages_send_to_room_with_attachment(
    room_id: str,
    text: str = Form(default=""),
    retention_days: int = Form(default=30),
    file: UploadFile | None = File(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rooms_col, messages_col = housing_router._message_collections()
    room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not await housing_router._can_access_message_room(room=room, current_user=current_user, tenant_id=tenant_id, app_key=app_key):
        raise HTTPException(status_code=404, detail="Room not found")

    content = str(text or "").strip()
    attachment_items: list[dict[str, Any]] = []
    if file is not None and file.filename:
        raw = await file.read()
        if len(raw) > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Attachment must be 10 MB or smaller")
        attachment_id = str(uuid4())
        attachment_items.append(
            {
                "id": attachment_id,
                "file_name": file.filename,
                "content_type": file.content_type or "application/octet-stream",
                "size": len(raw),
                "content": raw,
                "download_url": f"/api/v1/messages/rooms/{room_id}/messages/{{message_id}}/attachments/{attachment_id}",
            }
        )
    if not content and not attachment_items:
        raise HTTPException(status_code=400, detail="message text or attachment is required")

    now_dt = datetime.now(timezone.utc)
    now = now_dt.isoformat()
    retention = housing_router._message_retention_days(retention_days)
    message_id = str(uuid4())
    message_doc = {
        "id": message_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "room_id": room_id,
        "sender_id": str(current_user.get("sub") or "system"),
        "sender_name": str(current_user.get("full_name") or current_user.get("email") or "User"),
        "content": content,
        "message_type": "attachment" if attachment_items else "text",
        "attachments": attachment_items,
        "retention_days": retention,
        "expires_at": (now_dt + timedelta(days=retention)).isoformat(),
        "created_at": now,
    }
    for item in attachment_items:
        item["download_url"] = item["download_url"].replace("{message_id}", message_id)
    await messages_col.insert_one(message_doc)
    await rooms_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": room_id},
        {"$set": {"updated_at": now, "last_message_at": now}},
    )
    return housing_router._message_response(message_doc)


