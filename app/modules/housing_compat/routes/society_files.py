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


@router.post("/society/upload-logo", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def society_upload_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())

    allowed = {"image/png", "image/jpeg", "image/jpg"}
    content_type = (file.content_type or "").lower()
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only PNG and JPG files are allowed")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo file must be less than 2MB")

    stored_name = housing_router._safe_file_name(file.filename or "logo.png", prefix="logo")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router.get_collection("housing_documents").insert_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "stored_name": stored_name,
            "original_name": file.filename or stored_name,
            "content_type": content_type,
            "document_type": "society_logo",
            "size_bytes": len(content),
            "content": content,
            "created_at": now,
            "updated_at": now,
        }
    )

    logo_url = f"/society/documents/{stored_name}"
    return {"logo_url": logo_url, "file_name": stored_name, "content_type": content_type, "size_bytes": len(content)}


@router.post("/society/upload-document", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def society_upload_document(
    file: UploadFile = File(...),
    document_type: str = "other",
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Document file must be less than 10MB")

    stored_name = housing_router._safe_file_name(file.filename or "document.bin", prefix="doc")
    now = datetime.now(timezone.utc).isoformat()
    await housing_router.get_collection("housing_documents").insert_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "stored_name": stored_name,
            "original_name": file.filename or stored_name,
            "content_type": file.content_type or "application/octet-stream",
            "document_type": (document_type or "other").strip().lower(),
            "size_bytes": len(content),
            "content": content,
            "created_at": now,
            "updated_at": now,
        }
    )

    url = f"/society/documents/{stored_name}"
    return {"url": url, "file_name": file.filename or stored_name, "stored_name": stored_name, "size_bytes": len(content)}


@router.get("/society/documents/{file_name}")
async def society_download_document(
    file_name: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    doc = await housing_router.get_collection("housing_documents").find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "stored_name": file_name}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content = doc.get("content")
    if content is None:
        raise HTTPException(status_code=404, detail="Document content missing")
    content_type = str(doc.get("content_type") or "application/octet-stream")
    original_name = str(doc.get("original_name") or file_name)
    headers = {"Content-Disposition": f'inline; filename="{original_name}"'}
    return StreamingResponse(BytesIO(bytes(content)), media_type=content_type, headers=headers)


@router.delete("/society/documents/{file_name}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def society_delete_document(
    file_name: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    result = await housing_router.get_collection("housing_documents").delete_one(
        {"tenant_id": tenant_id, "app_key": app_key, "stored_name": file_name}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "file_name": file_name}


@router.post("/attachments/upload/{journal_entry_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def attachment_upload(
    journal_entry_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    settings = housing_router.get_settings()
    limit_bytes = max(1, int(settings.HOUSING_JOURNAL_ATTACHMENT_MAX_UPLOAD_MB)) * 1024 * 1024
    content = await housing_router._read_housing_upload_with_size_limit(
        file=file,
        limit_bytes=limit_bytes,
        feature_name="Journal attachment",
    )
    now = datetime.now(timezone.utc).isoformat()
    attachment_id = str(uuid4())
    stored_name = housing_router._safe_file_name(file.filename or "attachment", "attachment")
    await housing_router.get_collection("housing_documents").insert_one(
        {
            "id": attachment_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "document_type": "journal_attachment",
            "journal_entry_id": str(journal_entry_id),
            "stored_name": stored_name,
            "file_name": file.filename or stored_name,
            "content_type": file.content_type or "application/octet-stream",
            "content": content,
            "size_bytes": len(content),
            "created_at": now,
            "updated_at": now,
        }
    )
    return {"id": attachment_id, "journal_entry_id": str(journal_entry_id), "file_name": file.filename or stored_name}


@router.get("/attachments/journal/{journal_entry_id}")
async def attachment_list(
    journal_entry_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    rows = await housing_router.get_collection("housing_documents").find(
        {"tenant_id": tenant_id, "app_key": app_key, "document_type": "journal_attachment", "journal_entry_id": str(journal_entry_id)},
        {"content": 0},
    ).sort("created_at", -1).to_list(length=500)
    return [
        {
            "id": row.get("id"),
            "journal_entry_id": row.get("journal_entry_id"),
            "file_name": row.get("file_name") or row.get("stored_name"),
            "content_type": row.get("content_type"),
            "size_bytes": row.get("size_bytes") or 0,
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


@router.get("/attachments/{attachment_id}")
async def attachment_download(
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    doc = await housing_router.get_collection("housing_documents").find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "document_type": "journal_attachment", "id": attachment_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Attachment not found")
    headers = {"Content-Disposition": f'attachment; filename="{housing_router._safe_file_name(doc.get("file_name") or "attachment", "attachment")}"'}
    return Response(content=bytes(doc.get("content") or b""), media_type=doc.get("content_type") or "application/octet-stream", headers=headers)


@router.delete("/attachments/{attachment_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def attachment_delete(
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    result = await housing_router.get_collection("housing_documents").delete_one(
        {"tenant_id": tenant_id, "app_key": app_key, "document_type": "journal_attachment", "id": attachment_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"status": "deleted"}


@router.post("/resources/files/upload", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def resource_file_upload(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    description: str | None = Form(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    content = await file.read()
    now = datetime.now(timezone.utc).isoformat()
    file_id = str(uuid4())
    stored_name = housing_router._safe_file_name(file.filename or "resource", "resource")
    await housing_router.get_collection("housing_documents").insert_one(
        {
            "id": file_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "document_type": "resource_file",
            "category": (category or "general").strip() or "general",
            "description": (description or "").strip(),
            "stored_name": stored_name,
            "file_name": file.filename or stored_name,
            "content_type": file.content_type or "application/octet-stream",
            "content": content,
            "size_bytes": len(content),
            "created_at": now,
            "updated_at": now,
        }
    )
    return {"id": file_id, "file_name": file.filename or stored_name, "category": category, "size_bytes": len(content)}


@router.get("/resources/files")
async def resource_files_list(
    category: str | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    query = {"tenant_id": tenant_id, "app_key": app_key, "document_type": "resource_file"}
    if category:
        query["category"] = category
    rows = await housing_router.get_collection("housing_documents").find(query, {"content": 0}).sort("created_at", -1).to_list(length=500)
    return [
        {
            "id": row.get("id"),
            "file_name": row.get("file_name") or row.get("stored_name"),
            "category": row.get("category") or "general",
            "description": row.get("description") or "",
            "content_type": row.get("content_type"),
            "size_bytes": row.get("size_bytes") or 0,
            "created_at": row.get("created_at"),
        }
        for row in rows
    ]


@router.get("/resources/files/{file_id}")
@router.get("/resources/files/{file_id}/download")
async def resource_file_download(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    doc = await housing_router.get_collection("housing_documents").find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "document_type": "resource_file", "id": file_id}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Resource file not found")
    headers = {"Content-Disposition": f'attachment; filename="{housing_router._safe_file_name(doc.get("file_name") or "resource", "resource")}"'}
    return Response(content=bytes(doc.get("content") or b""), media_type=doc.get("content_type") or "application/octet-stream", headers=headers)


@router.delete("/resources/files/{file_id}", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def resource_file_delete(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    result = await housing_router.get_collection("housing_documents").delete_one(
        {"tenant_id": tenant_id, "app_key": app_key, "document_type": "resource_file", "id": file_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Resource file not found")
    return {"status": "deleted"}


