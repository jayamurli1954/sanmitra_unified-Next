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


@router.get("/meetings")
async def meetings_list(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    meetings, _ = housing_router._meeting_collections()
    rows = await meetings.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).to_list(length=500)
    return [
        {
            "id": row.get("id"),
            "meeting_title": row.get("meeting_title") or "Meeting",
            "meeting_type": row.get("meeting_type") or "MC",
            "meeting_date": row.get("meeting_date") or "",
            "meeting_time": row.get("meeting_time") or "",
            "venue": row.get("venue") or "",
            "status": housing_router._normalize_status(row.get("status")),
            "notice_sent": bool(row.get("notice_sent") or False),
        }
        for row in rows
    ]


@router.post("/meetings", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def meetings_create(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    title = str(payload.get("meeting_title") or "").strip()
    meeting_date = str(payload.get("meeting_date") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="meeting_title is required")
    if not meeting_date:
        raise HTTPException(status_code=400, detail="meeting_date is required")

    now = datetime.now(timezone.utc).isoformat()
    agenda_items = payload.get("agenda_items")
    if not isinstance(agenda_items, list):
        agenda_items = []
    normalized_agenda: list[dict[str, Any]] = []
    for idx, item in enumerate(agenda_items):
        if not isinstance(item, dict):
            continue
        item_title = str(item.get("item_title") or "").strip()
        item_description = str(item.get("item_description") or "").strip()
        if not item_title and not item_description:
            continue
        normalized_agenda.append(
            {
                "item_number": int(item.get("item_number") or (idx + 1)),
                "item_title": item_title,
                "item_description": item_description,
            }
        )

    eligible_member_ids = housing_router._normalize_member_ids(payload.get("eligible_member_ids") or [])
    selected_members = await housing_router._resolve_eligible_meeting_members(
        tenant_id=tenant_id,
        app_key=app_key,
        member_ids=eligible_member_ids,
    )
    eligible_flat_numbers = housing_router._normalize_flat_numbers([member.get("flat_number") for member in selected_members])
    eligible_default = len(selected_members) if eligible_member_ids else await housing_router._count_eligible_members(tenant_id=tenant_id, app_key=app_key)
    total_members_eligible = len(selected_members) if eligible_member_ids else (
        housing_router._safe_int(payload.get("total_members_eligible"), default=0) or eligible_default
    )
    quorum_required = housing_router._safe_int(payload.get("quorum_required"), default=0)
    notice_room_id = str(payload.get("notice_room_id") or "").strip()
    if notice_room_id:
        rooms_col, _ = housing_router._message_collections()
        notice_room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": notice_room_id})
        if not notice_room:
            raise HTTPException(status_code=400, detail="Notice room not found")

    meeting_id = str(uuid4())
    meeting_doc = {
        "id": meeting_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "meeting_title": title,
        "meeting_type": str(payload.get("meeting_type") or "MC"),
        "meeting_date": meeting_date,
        "meeting_time": str(payload.get("meeting_time") or ""),
        "venue": str(payload.get("venue") or ""),
        "notice_sent_to": str(payload.get("notice_sent_to") or "all_members"),
        "notice_room_id": notice_room_id or None,
        "eligible_member_ids": [str(member.get("id")) for member in selected_members if member.get("id")] if eligible_member_ids else [],
        "eligible_flat_numbers": eligible_flat_numbers,
        "agenda_items": normalized_agenda,
        "agenda": str(payload.get("agenda") or ""),
        "minutes_text": "",
        "status": housing_router._normalize_status(payload.get("status")),
        "total_members_eligible": total_members_eligible,
        "total_members_present": 0,
        "quorum_required": quorum_required,
        "quorum_met": bool(payload.get("quorum_met") or False),
        "notice_sent": False,
        "notice_sent_at": None,
        "last_change_action": None,
        "last_change_reason": None,
        "change_log": [],
        "attendance": [],
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    if quorum_required > 0:
        meeting_doc["quorum_met"] = False
    meetings, _ = housing_router._meeting_collections()
    await meetings.insert_one(meeting_doc)
    return housing_router._sanitize_mongo_doc(meeting_doc)


@router.get("/meetings/{meeting_id}")
async def meetings_get(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    eligible_hint = await housing_router._meeting_eligible_count(tenant_id=tenant_id, app_key=app_key, meeting=row)
    meeting = housing_router._sanitize_mongo_doc(row)
    meeting.update(housing_router._meeting_stats(row, eligible_hint=eligible_hint))
    return meeting


@router.get("/meetings/{meeting_id}/details")
async def meetings_details(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    _, resolutions_col = housing_router._meeting_collections()
    resolutions = await resolutions_col.find({"tenant_id": tenant_id, "app_key": app_key, "meeting_id": meeting_id}).sort("created_at", -1).to_list(length=500)
    eligible_hint = await housing_router._meeting_eligible_count(tenant_id=tenant_id, app_key=app_key, meeting=row)
    meeting = housing_router._sanitize_mongo_doc(row)
    meeting.update(housing_router._meeting_stats(row, eligible_hint=eligible_hint))
    return {
        "meeting": meeting,
        "agenda_items": row.get("agenda_items") or [],
        "attendance": row.get("attendance") or [],
        "resolutions": [housing_router._sanitize_mongo_doc(r) for r in resolutions],
    }


@router.patch("/meetings/{meeting_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def meetings_update(
    meeting_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    allowed = {
        "meeting_title",
        "meeting_type",
        "meeting_date",
        "meeting_time",
        "venue",
        "status",
        "agenda",
        "total_members_eligible",
        "quorum_required",
        "quorum_met",
        "notice_room_id",
        "eligible_member_ids",
        "change_action",
        "change_reason",
    }
    existing = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    update_doc = {k: v for k, v in payload.items() if k in allowed}
    change_action = str(update_doc.get("change_action") or "").strip().lower() or "general_update"
    change_reason = str(update_doc.get("change_reason") or "").strip()
    if change_action in {"cancel", "postpone", "prepone"} and not change_reason:
        raise HTTPException(status_code=400, detail="change_reason is required for cancel/postpone/prepone")
    if change_action == "cancel":
        update_doc["status"] = "CANCELLED"
    if "status" in update_doc:
        update_doc["status"] = housing_router._normalize_status(update_doc.get("status"))
    if "total_members_eligible" in update_doc:
        update_doc["total_members_eligible"] = housing_router._safe_int(update_doc.get("total_members_eligible"), default=0)
    if "quorum_required" in update_doc:
        update_doc["quorum_required"] = housing_router._safe_int(update_doc.get("quorum_required"), default=0)
    if "eligible_member_ids" in update_doc:
        selected_ids = housing_router._normalize_member_ids(update_doc.get("eligible_member_ids") or [])
        selected_members = await housing_router._resolve_eligible_meeting_members(
            tenant_id=tenant_id,
            app_key=app_key,
            member_ids=selected_ids,
        )
        update_doc["eligible_member_ids"] = [
            str(member.get("id")) for member in selected_members if member.get("id")
        ] if selected_ids else []
        update_doc["eligible_flat_numbers"] = housing_router._normalize_flat_numbers(
            [member.get("flat_number") for member in selected_members]
        )
        update_doc["total_members_eligible"] = len(selected_members) if selected_ids else await housing_router._count_eligible_members(
            tenant_id=tenant_id,
            app_key=app_key,
        )
    if "notice_room_id" in update_doc:
        notice_room_id = str(update_doc.get("notice_room_id") or "").strip()
        if notice_room_id:
            rooms_col, _ = housing_router._message_collections()
            notice_room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": notice_room_id})
            if not notice_room:
                raise HTTPException(status_code=400, detail="Notice room not found")
            update_doc["notice_room_id"] = notice_room_id
        else:
            update_doc["notice_room_id"] = None
    now = datetime.now(timezone.utc).isoformat()
    if change_reason:
        update_doc["last_change_reason"] = change_reason
    update_doc["last_change_action"] = change_action
    update_doc["updated_at"] = now
    if any(key in update_doc for key in {"meeting_date", "meeting_time", "status"}) or change_reason:
        previous_log = existing.get("change_log") or []
        if not isinstance(previous_log, list):
            previous_log = []
        change_entry = {
            "changed_at": now,
            "changed_by": str(current_user.get("sub") or "system"),
            "action": change_action,
            "reason": change_reason or None,
            "previous": {
                "meeting_date": existing.get("meeting_date"),
                "meeting_time": existing.get("meeting_time"),
                "status": existing.get("status"),
            },
            "current": {
                "meeting_date": update_doc.get("meeting_date", existing.get("meeting_date")),
                "meeting_time": update_doc.get("meeting_time", existing.get("meeting_time")),
                "status": update_doc.get("status", existing.get("status")),
            },
        }
        update_doc["change_log"] = [change_entry, *previous_log][:50]
    meetings, _ = housing_router._meeting_collections()
    await meetings.update_one({"tenant_id": tenant_id, "app_key": app_key, "id": meeting_id}, {"$set": update_doc})
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    eligible_hint = await housing_router._meeting_eligible_count(tenant_id=tenant_id, app_key=app_key, meeting=row)
    meeting = housing_router._sanitize_mongo_doc(row)
    meeting.update(housing_router._meeting_stats(row, eligible_hint=eligible_hint))
    return meeting


@router.delete("/meetings/{meeting_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def meetings_delete(
    meeting_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    meetings, resolutions_col = housing_router._meeting_collections()
    result = await meetings.delete_one({"tenant_id": tenant_id, "app_key": app_key, "id": meeting_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await resolutions_col.delete_many({"tenant_id": tenant_id, "app_key": app_key, "meeting_id": meeting_id})
    return {"status": "deleted", "id": meeting_id}


@router.post("/meetings/{meeting_id}/attendance")
async def meetings_attendance(
    meeting_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    attendees = payload.get("attendees")
    if not isinstance(attendees, list):
        attendees = []
    normalized: list[dict[str, Any]] = []
    for item in attendees:
        if not isinstance(item, dict):
            continue
        member_id = str(item.get("member_id") or "").strip()
        status = str(item.get("status") or "absent").strip().lower()
        if not member_id:
            continue
        if status not in {"present", "absent", "proxy"}:
            status = "absent"
        normalized.append({"member_id": member_id, "status": status})
    now = datetime.now(timezone.utc).isoformat()
    eligible_hint = await housing_router._meeting_eligible_count(tenant_id=tenant_id, app_key=app_key, meeting=row)
    stats = housing_router._meeting_stats({**row, "attendance": normalized}, eligible_hint=eligible_hint)
    update_set: dict[str, Any] = {
        "attendance": normalized,
        "updated_at": now,
        "total_members_present": stats["total_members_present"],
        "quorum_met": stats["quorum_met"],
    }
    if housing_router._safe_int(row.get("total_members_eligible"), default=0) <= 0 and stats["total_members_eligible"] > 0:
        update_set["total_members_eligible"] = stats["total_members_eligible"]
    meetings, _ = housing_router._meeting_collections()
    await meetings.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": meeting_id},
        {"$set": update_set},
    )
    updated = {**row, **update_set}
    return {"meeting_id": meeting_id, "attendance": normalized, "meeting": housing_router._sanitize_mongo_doc(updated)}


@router.post("/meetings/{meeting_id}/minutes")
async def meetings_minutes(
    meeting_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    minutes_text = str(payload.get("minutes_text") or "")
    now = datetime.now(timezone.utc).isoformat()
    meetings, _ = housing_router._meeting_collections()
    await meetings.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": meeting_id},
        {"$set": {"minutes_text": minutes_text, "updated_at": now}},
    )
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    return {"meeting": housing_router._sanitize_mongo_doc(row)}


@router.post("/meetings/{meeting_id}/resolutions", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def meetings_resolution_create(
    meeting_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    title = str(payload.get("resolution_title") or "").strip()
    text = str(payload.get("resolution_text") or "").strip()
    if not title or not text:
        raise HTTPException(status_code=400, detail="resolution_title and resolution_text are required")
    now = datetime.now(timezone.utc).isoformat()
    resolution = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "meeting_id": meeting_id,
        "resolution_title": title,
        "resolution_text": text,
        "resolution_type": str(payload.get("resolution_type") or "ordinary"),
        "proposed_by_id": str(payload.get("proposed_by_id") or ""),
        "seconded_by_id": str(payload.get("seconded_by_id") or ""),
        "votes_for": int(payload.get("votes_for") or 0),
        "votes_against": int(payload.get("votes_against") or 0),
        "votes_abstain": int(payload.get("votes_abstain") or 0),
        "result": str(payload.get("result") or "passed"),
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    _, resolutions_col = housing_router._meeting_collections()
    await resolutions_col.insert_one(resolution)
    return housing_router._sanitize_mongo_doc(resolution)


@router.post("/meetings/{meeting_id}/send-notice", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def meetings_send_notice(
    meeting_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    meeting = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    now = datetime.now(timezone.utc).isoformat()
    eligible_members = await housing_router._meeting_eligible_count(tenant_id=tenant_id, app_key=app_key, meeting=meeting)
    rooms_col, messages_col = housing_router._message_collections()
    target_room_id = str(payload.get("room_id") or meeting.get("notice_room_id") or "").strip()
    if target_room_id:
        notice_room = await rooms_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": target_room_id})
        if not notice_room:
            raise HTTPException(status_code=404, detail="Notice room not found")
    elif housing_router._normalize_flat_numbers(meeting.get("eligible_flat_numbers") or []):
        notice_room = await housing_router._get_or_create_message_room(
            tenant_id=tenant_id,
            app_key=app_key,
            name=f"Notice: {str(meeting.get('meeting_title') or 'Meeting')[:60]}",
            room_type=f"meeting_notice_{meeting_id}",
            description="Restricted meeting notice room for selected eligible members",
            audience_type="flats",
            allowed_flat_numbers=housing_router._normalize_flat_numbers(meeting.get("eligible_flat_numbers") or []),
        )
    else:
        notice_room = await housing_router._get_or_create_message_room(
            tenant_id=tenant_id,
            app_key=app_key,
            name="Meeting Notices",
            room_type="meeting_notices",
            description="Official meeting notices for eligible society members",
        )

    notice_message_id = str(meeting.get("notice_message_id") or "").strip()
    if notice_message_id:
        notice_message = await messages_col.find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "room_id": notice_room["id"], "id": notice_message_id}
        )
    else:
        notice_message = None

    if not notice_message:
        notice_message = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "room_id": notice_room["id"],
            "sender_id": str(current_user.get("sub") or "system"),
            "sender_name": str(current_user.get("name") or current_user.get("email") or "Society Admin"),
            "content": housing_router._build_meeting_notice_message(meeting, eligible_members),
            "message_type": "meeting_notice",
            "meeting_id": meeting_id,
            "eligible_members": eligible_members,
            "created_at": now,
        }
        await messages_col.insert_one(notice_message)
        await rooms_col.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "id": notice_room["id"]},
            {"$set": {"updated_at": now, "last_message_at": now}},
        )

    meetings, _ = housing_router._meeting_collections()
    await meetings.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": meeting_id},
        {
            "$set": {
                "notice_sent": True,
                "notice_sent_at": now,
                "notice_room_id": notice_room["id"],
                "notice_room_name": notice_room.get("name") or "Meeting Notices",
                "notice_message_id": notice_message["id"],
                "notice_delivery": {
                    "message_board": "posted",
                    "eligible_members": eligible_members,
                },
                "notice_channels": {
                    "message_board": True,
                    "email": bool(payload.get("send_email", False)),
                    "sms": bool(payload.get("send_sms", False)),
                },
                "updated_at": now,
            }
        },
    )
    row = await housing_router._get_meeting_or_404(tenant_id=tenant_id, app_key=app_key, meeting_id=meeting_id)
    return {
        "meeting": housing_router._sanitize_mongo_doc(row),
        "status": "notice_posted",
        "message_room": housing_router._sanitize_mongo_doc(notice_room),
        "message": housing_router._sanitize_mongo_doc(notice_message),
        "eligible_members": eligible_members,
    }


