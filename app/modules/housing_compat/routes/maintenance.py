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


@router.get("/maintenance/bills")
async def maintenance_list_bills(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    return await housing_router._list_maintenance_bills(tenant_id=tenant_id, app_key=app_key, month=month, year=year)


@router.get("/maintenance/expense-accounts-for-period")
async def maintenance_expense_accounts_for_period(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = housing_router.resolve_tenant_id(current_user, x_tenant_id)
    housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    app_key = housing_router.resolve_app_key((x_app_key or current_user.get("app_key") or "gruhamitra").strip())
    return await housing_router._expense_accounts_for_period(session, tenant_id=tenant_id, app_key=app_key, month=month, year=year)


BILLING_JOBS = "housing_billing_jobs"


async def _run_billing_job(
    *,
    job_id: str,
    tenant_id: str,
    app_key: str,
    payload: dict[str, Any],
    created_by: str,
) -> None:
    """Background task: executes bill generation and updates the job record."""
    jobs_col = housing_router.get_collection(BILLING_JOBS)
    try:
        await jobs_col.update_one(
            {"id": job_id},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}},
        )
        session_factory = housing_router.get_session_factory()
        async with session_factory() as session:
            result = await housing_router._build_maintenance_bills(
                tenant_id=tenant_id,
                app_key=app_key,
                payload=payload,
                current_user={"sub": created_by},
                session=session,
                replace_existing=True,
            )
        await jobs_col.update_one(
            {"id": job_id},
            {"$set": {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_bills": result.get("total_bills_generated", 0),
                "total_amount": result.get("total_amount", 0),
            }},
        )
    except HTTPException as exc:
        await jobs_col.update_one(
            {"id": job_id},
            {"$set": {
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc.detail),
            }},
        )
    except Exception as exc:
        await jobs_col.update_one(
            {"id": job_id},
            {"$set": {
                "status": "failed",
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }},
        )


@router.post("/maintenance/generate-bills", status_code=202, dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def maintenance_generate_bills(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance bill generation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    month = housing_router._safe_int(payload.get("month"))
    year = housing_router._safe_int(payload.get("year"))
    if month < 1 or month > 12 or year < 2000:
        raise HTTPException(status_code=422, detail="Valid month and year are required")

    flats = await list_flats(tenant_id=tenant_id, app_key=app_key)
    if not flats:
        raise HTTPException(status_code=400, detail="No flats found. Please add flats before generating bills.")

    bills_col, _ = housing_router._maintenance_collections()
    existing_posted = await bills_col.count_documents(
        {"tenant_id": tenant_id, "app_key": app_key, "month": month, "year": year, "is_posted": True}
    )
    if existing_posted:
        raise HTTPException(
            status_code=409,
            detail=f"Posted bills already exist for {housing_router._month_name(month)} {year}. Reverse them before regenerating.",
        )

    jobs_col = housing_router.get_collection(BILLING_JOBS)
    running_job = await jobs_col.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "month": month, "year": year,
         "status": {"$in": ["pending", "running"]}}
    )
    if running_job:
        return {
            "job_id": running_job["id"],
            "status": running_job["status"],
            "total_flats": len(flats),
            "message": f"A billing job for {housing_router._month_name(month)} {year} is already in progress.",
        }

    job_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    payload_snapshot = {k: v for k, v in payload.items() if k != "adjusted_inmates"}
    await jobs_col.insert_one({
        "id": job_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "month": month,
        "year": year,
        "status": "pending",
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "total_flats": len(flats),
        "payload_snapshot": payload_snapshot,
    })

    background_tasks.add_task(
        _run_billing_job,
        job_id=job_id,
        tenant_id=tenant_id,
        app_key=app_key,
        payload=payload,
        created_by=str(current_user.get("sub") or "system"),
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "total_flats": len(flats),
        "message": (
            f"Bill generation for {housing_router._month_name(month)} {year} started for {len(flats)} flats. "
            f"Poll GET /housing-compat/maintenance/billing-jobs/{job_id} for progress."
        ),
    }


@router.get("/maintenance/billing-jobs/{job_id}")
async def get_billing_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="read",
    )
    jobs_col = housing_router.get_collection(BILLING_JOBS)
    job = await jobs_col.find_one(
        {"id": job_id, "tenant_id": tenant_context.tenant_id, "app_key": tenant_context.app_key}
    )
    if not job:
        raise HTTPException(status_code=404, detail="Billing job not found")
    return housing_router._sanitize_mongo_doc(job)


@router.post("/maintenance/post-bills", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def maintenance_post_bills(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance bill posting",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    month = housing_router._safe_int(payload.get("month"))
    year = housing_router._safe_int(payload.get("year"))
    if month < 1 or month > 12 or year < 2000:
        raise HTTPException(status_code=422, detail="Valid month and year are required")
    bills_col, _ = housing_router._maintenance_collections()
    bills = await bills_col.find(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "month": month,
            "year": year,
            "status": {"$ne": "reversed"},
            "is_posted": {"$ne": True},
        }
    ).to_list(length=5000)
    if not bills:
        return {"month": month, "year": year, "total_bills_generated": 0, "posted_journal_entries": []}

    flat_occupants = await housing_router._flat_occupants_map(tenant_id=tenant_id, app_key=app_key)
    unassigned_flats = sorted(
        {
            str(bill.get("flat_number") or "").strip()
            for bill in bills
            if str(bill.get("flat_number") or "").strip().upper() not in flat_occupants
        }
    )
    if unassigned_flats:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot post maintenance bills for flats without active onboarded members: "
                + ", ".join(unassigned_flats)
            ),
        )

    now = datetime.now(timezone.utc).isoformat()
    posted_entries: list[int] = []
    for bill in bills:
        journal_entry_id = await housing_router._post_maintenance_bill_to_accounting(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            bill=bill,
            current_user=current_user,
        )
        posted_entries.append(journal_entry_id)
        await bills_col.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "id": bill.get("id")},
            {
                "$set": {
                    "is_posted": True,
                    "posting_status": "posted",
                    "status": "posted",
                    "journal_entry_id": journal_entry_id,
                    "posted_at": now,
                    "updated_at": now,
                }
            },
        )
    return {
        "month": month,
        "year": year,
        "total_bills_generated": len(posted_entries),
        "posted_journal_entries": posted_entries,
    }


@router.post("/maintenance/add-extra-charge", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def maintenance_add_extra_charge(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance extra charge",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    bill_id = str(payload.get("bill_id") or "").strip()
    amount = housing_router._round_money(housing_router._safe_float(payload.get("amount")))
    description = str(payload.get("description") or "").strip()
    if not bill_id:
        raise HTTPException(status_code=422, detail="bill_id is required")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than zero")
    if not description:
        raise HTTPException(status_code=422, detail="Description is required")

    bills_col, _ = housing_router._maintenance_collections()
    bill = await bills_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": bill_id})
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.get("is_posted") or str(bill.get("status") or "").lower() == "posted":
        raise HTTPException(status_code=409, detail="Posted bills cannot be edited. Reverse and regenerate before adding charges.")
    if str(bill.get("status") or "").lower() == "reversed":
        raise HTTPException(status_code=409, detail="Cannot add charges to a reversed bill")

    now = datetime.now(timezone.utc).isoformat()
    charge = {
        "id": str(uuid4()),
        "name": str(payload.get("name") or "Damage / Extra Charge").strip(),
        "amount": amount,
        "description": description,
        "calculation": description,
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
    }
    existing_extra = housing_router._safe_float(bill.get("extra_charges_amount"))
    existing_amount = housing_router._safe_float(bill.get("amount"))
    await bills_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": bill_id},
        {
            "$inc": {"amount": amount, "extra_charges_amount": amount},
            "$push": {"breakdown.supplementary_charges": charge},
            "$set": {"updated_at": now},
        },
    )
    updated = await bills_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": bill_id})
    if updated:
        updated["amount"] = housing_router._round_money(existing_amount + amount)
        updated["extra_charges_amount"] = housing_router._round_money(existing_extra + amount)
    return housing_router._sanitize_mongo_doc(updated or bill)


@router.post("/maintenance/reverse-bill", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def maintenance_reverse_bill(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance bill reversal",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    bill_id = str(payload.get("bill_id") or "").strip()
    if not bill_id:
        raise HTTPException(status_code=422, detail="bill_id is required")
    reason = str(payload.get("reversal_reason") or "").strip()
    if len(reason) < 10:
        raise HTTPException(status_code=422, detail="Reversal reason must be at least 10 characters")
    bills_col, reversals_col = housing_router._maintenance_collections()
    row = await bills_col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": bill_id})
    if not row:
        raise HTTPException(status_code=404, detail="Bill not found")
    now = datetime.now(timezone.utc).isoformat()
    reversal_journal_entry_id = None
    if row.get("is_posted"):
        reversal_journal_entry_id = await housing_router._reverse_maintenance_bill_accounting(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            bill=row,
            reason=reason,
            current_user=current_user,
        )
    await bills_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": bill_id},
        {
            "$set": {
                "status": "reversed",
                "is_posted": False,
                "posting_status": "reversed",
                "reversal_reason": reason,
                "reversal_journal_entry_id": reversal_journal_entry_id,
                "reversed_at": now,
                "updated_at": now,
            }
        },
    )
    reversal_doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "bill_id": bill_id,
        "flat_id": row.get("flat_id"),
        "flat_number": row.get("flat_number"),
        "month": row.get("month"),
        "year": row.get("year"),
        "amount": row.get("amount"),
        "reason": reason,
        "committee_approval": payload.get("committee_approval"),
        "reversal_journal_entry_id": reversal_journal_entry_id,
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
    }
    await reversals_col.insert_one(reversal_doc)
    return {
        "status": "reversed",
        "reversal_journal_entry_id": reversal_journal_entry_id,
        "bill": housing_router._sanitize_mongo_doc({**row, "status": "reversed", "is_posted": False}),
    }


@router.post("/maintenance/regenerate-bill", dependencies=_HOUSING_ADMIN_ROUTE_DEPS)
async def maintenance_regenerate_bill(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = housing_router.resolve_gruha_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="maintenance bill regeneration",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    flat_id = str(payload.get("flat_id") or "").strip()
    month = housing_router._safe_int(payload.get("month"))
    year = housing_router._safe_int(payload.get("year"))
    flat = await housing_router.get_collection("housing_flats").find_one({"tenant_id": tenant_id, "app_key": app_key, "id": flat_id})
    if not flat:
        raise HTTPException(status_code=404, detail="Flat not found")
    bills_col, _ = housing_router._maintenance_collections()
    previous = await bills_col.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "flat_id": flat_id, "month": month, "year": year},
        sort=[("updated_at", -1), ("created_at", -1)],
    )
    now = datetime.now(timezone.utc).isoformat()
    breakdown = dict((previous or {}).get("breakdown") or {})
    corrected_occupants = housing_router._safe_int(payload.get("corrected_occupants"), 0)
    water_rate = housing_router._safe_float(breakdown.get("water_per_person_rate"))
    maintenance = (
        housing_router._safe_float(payload.get("override_maintenance"))
        if payload.get("override_maintenance") not in (None, "")
        else housing_router._safe_float((previous or {}).get("maintenance_amount"))
    )
    if payload.get("override_water") not in (None, ""):
        water = housing_router._safe_float(payload.get("override_water"))
    elif corrected_occupants > 0 and water_rate > 0:
        water = housing_router._round_money(water_rate * corrected_occupants)
    else:
        water = housing_router._safe_float((previous or {}).get("water_amount"))
    fixed = (
        housing_router._safe_float(payload.get("override_fixed"))
        if payload.get("override_fixed") not in (None, "")
        else housing_router._safe_float((previous or {}).get("fixed_amount"))
    )
    sinking = (
        housing_router._safe_float(payload.get("override_sinking"))
        if payload.get("override_sinking") not in (None, "")
        else housing_router._safe_float((previous or {}).get("sinking_fund_amount"))
    )
    repair = (
        housing_router._safe_float(payload.get("override_repair"))
        if payload.get("override_repair") not in (None, "")
        else housing_router._safe_float((previous or {}).get("repair_fund_amount"))
    )
    association = housing_router._safe_float((previous or {}).get("association_fund_amount"))
    corpus = (
        housing_router._safe_float(payload.get("override_corpus"))
        if payload.get("override_corpus") not in (None, "")
        else housing_router._safe_float((previous or {}).get("corpus_fund_amount"))
    )
    amount = housing_router._round_money(maintenance + water + fixed + sinking + repair + association + corpus)
    if corrected_occupants > 0 and water_rate > 0:
        breakdown["inmates_used"] = corrected_occupants
        breakdown["water_charges"] = water
        breakdown["water_calculation"] = f"Corrected: {water_rate:,.2f} x {corrected_occupants} resident(s)"
    doc = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "flat_id": flat_id,
        "flat_number": flat.get("flat_number"),
        "month": month,
        "year": year,
        "amount": amount,
        "maintenance_amount": maintenance,
        "water_amount": water,
        "fixed_amount": fixed,
        "sinking_fund_amount": sinking,
        "repair_fund_amount": repair,
        "association_fund_amount": association,
        "corpus_fund_amount": corpus,
        "status": "generated",
        "is_posted": False,
        "posting_status": "not_posted",
        "notes": payload.get("notes"),
        "breakdown": {
            **breakdown,
            "maintenance_sqft": maintenance,
            "water_charges": water,
            "fixed_expenses": fixed,
            "sinking_fund": sinking,
            "repair_fund": repair,
            "association_fund": association,
            "corpus_fund": corpus,
        },
        "created_by": str(current_user.get("sub") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    await bills_col.insert_one(doc)
    return housing_router._sanitize_mongo_doc(doc)


