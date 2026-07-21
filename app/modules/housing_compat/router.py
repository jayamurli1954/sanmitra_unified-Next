"""GruhaMitra housing compat router facade.

Quarantined compensation/posting helpers stay here (LARGE_FILE_MODULARIZATION_PLAN.md §6).
Domain routes register via side-effect imports at the end of this module.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
    post_journal_entry as post_journal_entry,
)
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.db.mongo import get_collection

router = APIRouter(tags=["housing-compat"])

_HOUSING_ADMIN_ROUTE_DEPS = [
    Depends(require_enabled_module("housing")),
    Depends(require_roles([Role.tenant_admin, Role.super_admin])),
]

_logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# QUARANTINED (LARGE_FILE_MODULARIZATION_PLAN.md §6): posting + account lookup
# ════════════════════════════════════════════════════════════════════════

GRUHA_LEGACY_ACCOUNT_CODE_MAP: dict[str, str] = {
    "1000": "11001",
    "1010": "11010",
    "1020": "11011",
    "1030": "15010",
    "1040": "12003",
    "1100": "12001",
    "1110": "12002",
    "1120": "12004",
    "1210": "13002",
    "1220": "15001",
    "1230": "15002",
    "1300": "16001",
    "1310": "16002",
    "1320": "16003",
    "1500": "16003",
    "2000": "31001",
    "2010": "24001",
    "2020": "24002",
    "2100": "21001",
    "2110": "21002",
    "2120": "23002",
    "2130": "23001",
    "3000": "31002",
    "3010": "31003",
    "3020": "31004",
    "3030": "31005",
    "3040": "31006",
    "3050": "31099",
    "4000": "41001",
    "4010": "41002",
    "4020": "41003",
    "4030": "41004",
    "4040": "42001",
    "4050": "41005",
    "4060": "41006",
    "4070": "42002",
    "5000": "53005",
    "5010": "53002",
    "5020": "52001",
    "5030": "53003",
    "5040": "53004",
    "5050": "53006",
    "5060": "53007",
    "5070": "53008",
    "5080": "54002",
    "5090": "54001",
    "5100": "54003",
    "5110": "53009",
    "5120": "53010",
}


def _canonical_gruha_account_code(code: Any) -> str:
    raw = str(code or "").strip()
    return GRUHA_LEGACY_ACCOUNT_CODE_MAP.get(raw, raw)

async def _find_account_by_code(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    code: str,
    account_type: str | None = None,
    accounting_entity_id: str = "primary",
) -> Account | None:
    conditions = [
        Account.tenant_id == tenant_id,
        Account.app_key == app_key,
        Account.accounting_entity_id == accounting_entity_id,
        Account.code == str(code).strip(),
    ]
    if account_type:
        conditions.append(Account.type == account_type)
    result = await session.execute(select(Account).where(*conditions))
    return result.scalar_one_or_none()


async def _find_corpus_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
) -> Account | None:
    scoped = [
        Account.tenant_id == tenant_id,
        Account.app_key == app_key,
        Account.accounting_entity_id == accounting_entity_id,
        Account.type == "equity",
    ]
    by_name = await session.execute(select(Account).where(*scoped, func.lower(Account.name) == "corpus fund"))
    account = by_name.scalar_one_or_none()
    if account is not None:
        return account

    for code in ("31002",):
        by_code = await session.execute(select(Account).where(*scoped, Account.code == code, Account.name.ilike("%corpus%")))
        account = by_code.scalar_one_or_none()
        if account is not None:
            return account
    return None


def _asset_accounting_date(row: dict[str, Any]) -> date:
    value = row.get("purchase_date") or row.get("handover_date")
    if value:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            pass
    return datetime.now(timezone.utc).date()


async def _post_asset_capitalization_journal(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    asset: dict[str, Any],
    created_by: str,
) -> JournalEntry | None:
    amount = Decimal(str(_safe_float(asset.get("original_cost")))).quantize(Decimal("0.01"))
    if amount <= 0:
        return None
    if asset.get("acquisition_type") != "builder_handover":
        return None

    asset_account = await _find_account_by_code(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        code=_canonical_gruha_account_code(asset.get("account_code") or ""),
        account_type="asset",
    )
    if asset_account is None and _canonical_gruha_account_code(asset.get("account_code") or "") == "16003":
        asset_account = await _find_account_by_code(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            code="16003",
            account_type="asset",
        )
    if asset_account is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Asset account {asset.get('account_code') or ''} was not found in this tenant's Chart of Accounts. "
                "Initialize the Chart of Accounts or choose an existing asset account."
            ),
        )

    corpus_account = await _find_corpus_account(session, tenant_id=tenant_id, app_key=app_key)
    if corpus_account is None:
        raise HTTPException(status_code=422, detail="Corpus Fund account was not found in this tenant's Chart of Accounts.")

    try:
        entry, _created = await post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            created_by=created_by,
            payload=JournalPostRequest(
                entry_date=_asset_accounting_date(asset),
                description=f"Asset capitalized: {asset.get('name') or asset.get('asset_code')}",
                reference=str(asset.get("asset_code") or asset.get("id") or "")[:120],
                lines=[
                    JournalLineIn(account_id=int(asset_account.id), debit=amount, credit=Decimal("0.00")),
                    JournalLineIn(account_id=int(corpus_account.id), debit=Decimal("0.00"), credit=amount),
                ],
            ),
            idempotency_key=f"housing-asset:{asset.get('id')}:capitalization",
        )
    except (AccountingNotFoundError, AccountingValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return entry

async def _account_ids_by_code(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    codes: set[str],
) -> dict[str, int]:
    requested_codes = {str(code).strip() for code in codes if str(code).strip()}
    canonical_by_requested = {code: _canonical_gruha_account_code(code) for code in requested_codes}
    canonical_codes = set(canonical_by_requested.values())
    rows = (
        await session.execute(
            select(Account.code, Account.id).where(
                Account.tenant_id == tenant_id,
                Account.app_key == app_key,
                Account.accounting_entity_id == "primary",
                Account.code.in_(canonical_codes),
            )
        )
    ).all()
    found = {str(code): int(account_id) for code, account_id in rows}
    missing = sorted(canonical_codes - set(found))
    if missing:
        raise HTTPException(status_code=400, detail=f"Required accounting accounts missing: {', '.join(missing)}")
    result = dict(found)
    for requested, canonical in canonical_by_requested.items():
        result[requested] = found[canonical]
    return result


def _bill_credit_components(bill: dict[str, Any]) -> list[tuple[str, Decimal]]:
    total = _as_decimal_money(bill.get("amount"))
    return [("41001", total)] if total > 0 else []


async def _post_maintenance_bill_to_accounting(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill: dict[str, Any],
    current_user: dict[str, Any],
) -> int:
    month = _safe_int(bill.get("month"))
    year = _safe_int(bill.get("year"))
    _from_date, entry_date = _month_date_range(month, year)
    credit_components = _bill_credit_components(bill)
    if not credit_components:
        raise HTTPException(status_code=400, detail=f"Bill {bill.get('flat_number')} has no billable components")

    total = _as_decimal_money(bill.get("amount"))
    credit_total = sum((amount for _code, amount in credit_components), Decimal("0.00"))
    if total != credit_total:
        total = credit_total

    required_codes = {"12001", *(code for code, _amount in credit_components)}
    account_ids = await _account_ids_by_code(session, tenant_id=tenant_id, app_key=app_key, codes=required_codes)
    lines = [JournalLineIn(account_id=account_ids["12001"], debit=total, credit=Decimal("0.00"))]
    lines.extend(
        JournalLineIn(account_id=account_ids[code], debit=Decimal("0.00"), credit=amount)
        for code, amount in credit_components
    )
    reference = f"MBILL-{year}-{month:02d}-{bill.get('flat_number')}"
    try:
        entry, _created = await post_journal_entry(
            session,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id="primary",
            created_by=str(current_user.get("sub") or "system"),
            payload=JournalPostRequest(
                entry_date=entry_date,
                description=f"Monthly maintenance bill for {bill.get('flat_number')} - {_month_name(month)} {year}",
                reference=reference,
                lines=lines,
            ),
            idempotency_key=f"gruhamitra:{tenant_id}:{app_key}:maintenance-bill:{bill.get('id')}",
        )
    except (AccountingValidationError, AccountingNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return int(entry.id)


async def _reverse_maintenance_bill_accounting(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    bill: dict[str, Any],
    reason: str,
    current_user: dict[str, Any],
) -> int | None:
    original_journal_id = bill.get("journal_entry_id")
    if not original_journal_id:
        return None

    rows = (
        await session.execute(
            select(JournalLine.account_id, JournalLine.debit, JournalLine.credit, JournalEntry.entry_date)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.app_key == app_key,
                JournalEntry.accounting_entity_id == "primary",
                JournalEntry.id == int(original_journal_id),
            )
            .order_by(JournalLine.id.asc())
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=400, detail="Original bill journal entry not found for reversal")

    lines = [
        JournalLineIn(
            account_id=int(row.account_id),
            debit=Decimal(row.credit or 0).quantize(Decimal("0.01")),
            credit=Decimal(row.debit or 0).quantize(Decimal("0.01")),
        )
        for row in rows
    ]
    month = _safe_int(bill.get("month"))
    year = _safe_int(bill.get("year"))
    _from_date, entry_date = _month_date_range(month, year)
    try:
        entry, _created = await post_journal_entry(
            session,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id="primary",
            created_by=str(current_user.get("sub") or "system"),
            payload=JournalPostRequest(
                entry_date=entry_date,
                description=f"Reversal of maintenance bill for {bill.get('flat_number')} - {_month_name(month)} {year}: {reason}",
                reference=f"REV-MBILL-{year}-{month:02d}-{bill.get('flat_number')}",
                lines=lines,
            ),
            idempotency_key=f"gruhamitra:{tenant_id}:{app_key}:maintenance-bill-reversal:{bill.get('id')}",
        )
    except (AccountingValidationError, AccountingNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return int(entry.id)


# Helper re-exports (monkeypatch / route compatibility)
from app.core.tenants.app_resolvers import resolve_gruha_tenant as resolve_gruha_tenant
from app.core.tenants.context import resolve_app_key as resolve_app_key, resolve_tenant_id as resolve_tenant_id
from app.db.postgres import get_async_session as get_async_session
from app.config import get_settings as get_settings
from app.modules.housing_compat.service import (
    get_society_settings as get_society_settings,
    list_flats as list_flats,
    save_society_settings as save_society_settings,
)
from app.modules.housing_compat.helpers.shared import (
    _format_upload_size as _format_upload_size,
    _read_housing_upload_with_size_limit as _read_housing_upload_with_size_limit,
    _safe_file_name as _safe_file_name,
    _meeting_collections as _meeting_collections,
    _message_collections as _message_collections,
    _complaints_collection as _complaints_collection,
    _visitors_collection as _visitors_collection,
    _asset_response as _asset_response,
    _next_asset_code as _next_asset_code,
    _get_meeting_or_404 as _get_meeting_or_404,
    _get_or_create_message_room as _get_or_create_message_room,
    _build_meeting_notice_message as _build_meeting_notice_message,
    _sanitize_mongo_doc as _sanitize_mongo_doc,
    _normalize_status as _normalize_status,
    _safe_int as _safe_int,
    _safe_float as _safe_float,
    _round_money as _round_money,
    _as_decimal_money as _as_decimal_money,
    _month_name as _month_name,
    _split_charge as _split_charge,
    _count_eligible_members as _count_eligible_members,
    _normalize_member_ids as _normalize_member_ids,
    _resolve_eligible_meeting_members as _resolve_eligible_meeting_members,
    _meeting_eligible_count as _meeting_eligible_count,
    _meeting_stats as _meeting_stats,
    _build_simple_pdf as _build_simple_pdf,
    _get_society_branding as _get_society_branding,
    _draw_pdf_header as _draw_pdf_header,
    _build_branded_pdf as _build_branded_pdf,
    _sanitize_pdf_text as _sanitize_pdf_text,
    _maintenance_collections as _maintenance_collections,
    _list_maintenance_bills as _list_maintenance_bills,
    _flat_occupants_map as _flat_occupants_map,
    _month_date_range as _month_date_range,
    _expense_period_labels as _expense_period_labels,
    _matches_expense_period as _matches_expense_period,
    _is_water_expense_account as _is_water_expense_account,
    _expense_accounts_for_period as _expense_accounts_for_period,
    _build_maintenance_bills as _build_maintenance_bills,
    _normalize_header as _normalize_header,
    _truthy as _truthy,
    _parse_member_move_in as _parse_member_move_in,
    _row_get as _row_get,
    _coerce_bulk_member_payload as _coerce_bulk_member_payload,
    _parse_csv_rows as _parse_csv_rows,
    _parse_xlsx_rows as _parse_xlsx_rows,
    _can_manage_chat_rooms as _can_manage_chat_rooms,
    _normalize_flat_number as _normalize_flat_number,
    _normalize_flat_numbers as _normalize_flat_numbers,
    _room_response as _room_response,
    _message_response as _message_response,
    _message_retention_days as _message_retention_days,
    _current_user_message_audience as _current_user_message_audience,
    _can_access_message_room as _can_access_message_room,
    _can_manage_complaints as _can_manage_complaints,
    _can_manage_visitors as _can_manage_visitors,
    _can_manage_facilities as _can_manage_facilities,
    _facility_booking_response as _facility_booking_response,
    _facility_confirmation_message as _facility_confirmation_message,
    format_date_time_for_display as format_date_time_for_display,
    _facility_booking_access_query as _facility_booking_access_query,
    _resolve_booking_flat as _resolve_booking_flat,
    _find_overlapping_facility_booking as _find_overlapping_facility_booking,
    _visitor_response as _visitor_response,
    _visitor_access_query as _visitor_access_query,
    _get_visitor_or_404 as _get_visitor_or_404,
    _send_web_push_sync as _send_web_push_sync,
    _send_web_push_notification as _send_web_push_notification,
    BILLING_JOBS as BILLING_JOBS,
    _run_billing_job as _run_billing_job,
)

# Route modules (side-effect registration)
from app.modules.housing_compat.routes import facilities as _housing_facilities_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import visitors as _housing_visitors_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import complaints as _housing_complaints_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import maintenance as _housing_maintenance_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import messages_rooms_list as _housing_messages_rooms_list_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import assets as _housing_assets_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import messaging as _housing_messaging_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import society_files as _housing_society_files_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import meetings as _housing_meetings_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import members as _housing_members_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import settings_flats as _housing_settings_flats_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import move_governance as _housing_move_governance_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import database as _housing_database_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import webpush as _housing_webpush_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import staff as _housing_staff_routes  # noqa: E402,F401
from app.modules.housing_compat.routes import visitors_public as _housing_visitors_public_routes  # noqa: E402,F401

# Route handler re-exports (tenant-isolation tests call these on the facade)
from app.modules.housing_compat.routes.maintenance import maintenance_post_bills as maintenance_post_bills  # noqa: E402,F401
from app.modules.housing_compat.routes.settings_flats import society_settings_get as society_settings_get  # noqa: E402,F401
from app.modules.housing_compat.routes.settings_flats import society_settings_patch as society_settings_patch  # noqa: E402,F401
from app.modules.housing_compat.routes.move_governance import move_police_verification_form as move_police_verification_form  # noqa: E402,F401
from app.modules.housing_compat.routes.move_governance import move_tenant_id_form as move_tenant_id_form  # noqa: E402,F401
from app.modules.housing_compat.routes.messages_rooms_list import messages_list_rooms as messages_list_rooms  # noqa: E402,F401
from app.modules.housing_compat.routes.messaging import messages_list_for_room as messages_list_for_room  # noqa: E402,F401
from app.modules.housing_compat.routes.meetings import meetings_send_notice as meetings_send_notice  # noqa: E402,F401
from app.modules.housing_compat.routes.visitors import visitors_list as visitors_list  # noqa: E402,F401
from app.modules.housing_compat.routes.visitors import visitors_create as visitors_create  # noqa: E402,F401
from app.modules.housing_compat.routes.visitors import visitors_check_in as visitors_check_in  # noqa: E402,F401
from app.modules.housing_compat.routes.visitors_public import visitors_verify_pass as visitors_verify_pass  # noqa: E402,F401
from app.modules.housing_compat.routes.webpush import web_push_subscribe as web_push_subscribe  # noqa: E402,F401
from app.modules.housing_compat.routes.webpush import web_push_unsubscribe as web_push_unsubscribe  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_create as staff_create  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_list as staff_list  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_update as staff_update  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_delete as staff_delete  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_attendance_check_in as staff_attendance_check_in  # noqa: E402,F401
from app.modules.housing_compat.routes.staff import staff_attendance_check_out as staff_attendance_check_out  # noqa: E402,F401
from app.modules.housing_compat.routes.facilities import facility_bookings_create as facility_bookings_create  # noqa: E402,F401
from app.modules.housing_compat.routes.facilities import facility_bookings_cancel as facility_bookings_cancel  # noqa: E402,F401
from app.modules.housing_compat.routes.facilities import facility_bookings_approve as facility_bookings_approve  # noqa: E402,F401
