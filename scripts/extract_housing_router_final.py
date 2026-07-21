"""Extract housing_compat/router.py into helpers/* + routes/* + slim facade.

Pure move per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
Quarantined posting helpers stay in router.py (§6).

Run: python scripts/extract_housing_router_final.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/housing_compat/router.py"
HELPERS = ROOT / "app/modules/housing_compat/helpers"
ROUTES = ROOT / "app/modules/housing_compat/routes"

# 1-indexed inclusive line ranges in the ORIGINAL router.py
QUARANTINE_RANGES = [
    (143, 198),   # GRUHA_LEGACY + _canonical_gruha_account_code
    (269, 388),   # account lookup + asset capitalization posting
    (1109, 1249), # maintenance bill posting/reversal
]

HELPER_EXTRA_RANGES = [
    (2079, 2122),  # web-push helpers (were inside visitors routes)
    (2520, 2574),  # billing job helpers (inside maintenance routes)
]

HELPER_RANGES = [
    (119, 142),
    (199, 268),
    (391, 1108),
    (1250, 1768),
] + HELPER_EXTRA_RANGES

ROUTE_SLICES: list[tuple[str, int, int]] = [
    ("facilities", 1771, 2047),
    ("visitors", 2048, 2344),
    ("complaints", 2346, 2489),
    ("maintenance", 2492, 3007),
    ("messages_rooms_list", 3009, 3041),
    ("assets", 3044, 3220),
    ("messaging", 3223, 3451),
    ("society_files", 3453, 3770),
    ("meetings", 3772, 4253),
    ("members", 4255, 4495),
    ("settings_flats", 4497, 4745),
    ("move_governance", 4748, 4948),
    ("database", 4951, 5049),
    ("webpush", 5053, 5121),
    ("staff", 5124, 5407),
    ("visitors_public", 5410, 5473),
]

ROUTE_HANDLER_REEXPORTS: list[tuple[str, str]] = [
    ("maintenance", "maintenance_post_bills"),
    ("settings_flats", "society_settings_get"),
    ("settings_flats", "society_settings_patch"),
    ("move_governance", "move_police_verification_form"),
    ("move_governance", "move_tenant_id_form"),
    ("messages_rooms_list", "messages_list_rooms"),
    ("messaging", "messages_list_for_room"),
    ("meetings", "meetings_send_notice"),
    ("visitors", "visitors_list"),
    ("visitors", "visitors_create"),
    ("visitors", "visitors_check_in"),
    ("visitors_public", "visitors_verify_pass"),
    ("webpush", "web_push_subscribe"),
    ("webpush", "web_push_unsubscribe"),
    ("staff", "staff_create"),
    ("staff", "staff_list"),
    ("staff", "staff_update"),
    ("staff", "staff_delete"),
    ("staff", "staff_attendance_check_in"),
    ("staff", "staff_attendance_check_out"),
    ("facilities", "facility_bookings_create"),
    ("facilities", "facility_bookings_cancel"),
    ("facilities", "facility_bookings_approve"),
]

# Symbols re-exported from router for tests/routes (qualify bare calls in extracted code).
ROUTER_SYMBOLS = [
    "get_collection",
    "post_journal_entry",
    "resolve_gruha_tenant",
    "resolve_app_key",
    "resolve_tenant_id",
    "get_async_session",
    "get_session_factory",
    "get_settings",
    "list_flats",
    "get_society_settings",
    "save_society_settings",
    "GRUHA_LEGACY_ACCOUNT_CODE_MAP",
    "_canonical_gruha_account_code",
    "_format_upload_size",
    "_read_housing_upload_with_size_limit",
    "_safe_file_name",
    "_meeting_collections",
    "_message_collections",
    "_complaints_collection",
    "_visitors_collection",
    "_asset_response",
    "_next_asset_code",
    "_find_account_by_code",
    "_find_corpus_account",
    "_asset_accounting_date",
    "_post_asset_capitalization_journal",
    "_get_meeting_or_404",
    "_get_or_create_message_room",
    "_build_meeting_notice_message",
    "_sanitize_mongo_doc",
    "_normalize_status",
    "_safe_int",
    "_safe_float",
    "_round_money",
    "_as_decimal_money",
    "_month_name",
    "_split_charge",
    "_count_eligible_members",
    "_normalize_member_ids",
    "_resolve_eligible_meeting_members",
    "_meeting_eligible_count",
    "_meeting_stats",
    "_build_simple_pdf",
    "_get_society_branding",
    "_draw_pdf_header",
    "_build_branded_pdf",
    "_sanitize_pdf_text",
    "_maintenance_collections",
    "_list_maintenance_bills",
    "_flat_occupants_map",
    "_month_date_range",
    "_expense_period_labels",
    "_matches_expense_period",
    "_is_water_expense_account",
    "_expense_accounts_for_period",
    "_build_maintenance_bills",
    "_account_ids_by_code",
    "_bill_credit_components",
    "_post_maintenance_bill_to_accounting",
    "_reverse_maintenance_bill_accounting",
    "_normalize_header",
    "_truthy",
    "_parse_member_move_in",
    "_row_get",
    "_coerce_bulk_member_payload",
    "_parse_csv_rows",
    "_parse_xlsx_rows",
    "_can_manage_chat_rooms",
    "_normalize_flat_number",
    "_normalize_flat_numbers",
    "_room_response",
    "_message_response",
    "_message_retention_days",
    "_current_user_message_audience",
    "_can_access_message_room",
    "_can_manage_complaints",
    "_can_manage_visitors",
    "_can_manage_facilities",
    "_facility_booking_response",
    "_facility_confirmation_message",
    "format_date_time_for_display",
    "_facility_booking_access_query",
    "_resolve_booking_flat",
    "_find_overlapping_facility_booking",
    "_visitor_response",
    "_visitor_access_query",
    "_get_visitor_or_404",
    "_staff_response",
    "_attendance_response",
    "_send_web_push_sync",
    "_send_web_push_notification",
    "BILLING_JOBS",
    "_run_billing_job",
]

HELPER_HEADER = '''\
"""Shared housing_compat helpers extracted from router.py.

Pure move per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md.
"""
from __future__ import annotations

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

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account, JournalEntry, JournalLine
from app.modules.housing_compat import router as housing_router

'''

ROUTE_HEADER = '''\
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

'''

SLIM_HEADER = '''\
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

'''


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def in_quarantine(line_no: int) -> bool:
    return any(start <= line_no <= end for start, end in QUARANTINE_RANGES)


def qualify_body(body: str, *, skip_defs: bool = True) -> str:
    if skip_defs:
        for name in ROUTER_SYMBOLS:
            body = body.replace(f"async def {name}(", f"async def __DEF_{name}__(")
            body = body.replace(f"def {name}(", f"def __DEF_{name}__(")
    for name in sorted(ROUTER_SYMBOLS, key=len, reverse=True):
        import re as _re

        body = _re.sub(rf"(?<![\w.]){name}(\s*\()", rf"housing_router.{name}\1", body)
    if skip_defs:
        for name in ROUTER_SYMBOLS:
            body = body.replace(f"async def __DEF_{name}__(", f"async def {name}(")
            body = body.replace(f"def __DEF_{name}__(", f"def {name}(")
    return body


def build_helpers(lines: list[str]) -> str:
    parts = [HELPER_HEADER]
    for start, end in HELPER_RANGES:
        parts.append(slice_lines(lines, start, end))
        parts.append("\n")
    body = qualify_body("".join(parts))
    return body


def build_quarantine(lines: list[str]) -> str:
    parts = [
        "\n# ════════════════════════════════════════════════════════════════════════\n",
        "# QUARANTINED (LARGE_FILE_MODULARIZATION_PLAN.md §6): posting + account lookup\n",
        "# ════════════════════════════════════════════════════════════════════════\n\n",
    ]
    for start, end in QUARANTINE_RANGES:
        parts.append(slice_lines(lines, start, end))
        parts.append("\n")
    return "".join(parts)


def build_route_module(name: str, lines: list[str], start: int, end: int) -> str:
    body = qualify_body(slice_lines(lines, start, end))
    return ROUTE_HEADER + "\n" + body + "\n"


def build_facade_reexports() -> str:
    helper_names = [
        "_format_upload_size",
        "_read_housing_upload_with_size_limit",
        "_safe_file_name",
        "_meeting_collections",
        "_message_collections",
        "_complaints_collection",
        "_visitors_collection",
        "_asset_response",
        "_next_asset_code",
        "_get_meeting_or_404",
        "_get_or_create_message_room",
        "_build_meeting_notice_message",
        "_sanitize_mongo_doc",
        "_normalize_status",
        "_safe_int",
        "_safe_float",
        "_round_money",
        "_as_decimal_money",
        "_month_name",
        "_split_charge",
        "_count_eligible_members",
        "_normalize_member_ids",
        "_resolve_eligible_meeting_members",
        "_meeting_eligible_count",
        "_meeting_stats",
        "_build_simple_pdf",
        "_get_society_branding",
        "_draw_pdf_header",
        "_build_branded_pdf",
        "_sanitize_pdf_text",
        "_maintenance_collections",
        "_list_maintenance_bills",
        "_flat_occupants_map",
        "_month_date_range",
        "_expense_period_labels",
        "_matches_expense_period",
        "_is_water_expense_account",
        "_expense_accounts_for_period",
        "_build_maintenance_bills",
        "_normalize_header",
        "_truthy",
        "_parse_member_move_in",
        "_row_get",
        "_coerce_bulk_member_payload",
        "_parse_csv_rows",
        "_parse_xlsx_rows",
        "_can_manage_chat_rooms",
        "_normalize_flat_number",
        "_normalize_flat_numbers",
        "_room_response",
        "_message_response",
        "_message_retention_days",
        "_current_user_message_audience",
        "_can_access_message_room",
        "_can_manage_complaints",
        "_can_manage_visitors",
        "_can_manage_facilities",
        "_facility_booking_response",
        "_facility_confirmation_message",
        "format_date_time_for_display",
        "_facility_booking_access_query",
        "_resolve_booking_flat",
        "_find_overlapping_facility_booking",
        "_visitor_response",
        "_visitor_access_query",
        "_get_visitor_or_404",
        "_send_web_push_sync",
        "_send_web_push_notification",
        "BILLING_JOBS",
        "_run_billing_job",
    ]
    lines = [
        "\n# Helper re-exports (monkeypatch / route compatibility)\n",
        "from app.core.tenants.app_resolvers import resolve_gruha_tenant as resolve_gruha_tenant\n",
        "from app.core.tenants.context import resolve_app_key as resolve_app_key, resolve_tenant_id as resolve_tenant_id\n",
        "from app.db.postgres import get_async_session as get_async_session\n",
        "from app.config import get_settings as get_settings\n",
        "from app.modules.housing_compat.service import (\n",
        "    get_society_settings as get_society_settings,\n",
        "    list_flats as list_flats,\n",
        "    save_society_settings as save_society_settings,\n",
        ")\n",
        "from app.modules.housing_compat.helpers.shared import (\n",
    ]
    for n in helper_names:
        lines.append(f"    {n} as {n},\n")
    lines.append(")\n\n")
    lines.append("# Route modules (side-effect registration)\n")
    for mod_name, _, _ in ROUTE_SLICES:
        lines.append(f"from app.modules.housing_compat.routes import {mod_name} as _housing_{mod_name}_routes  # noqa: E402,F401\n")
    lines.append("\n# Route handler re-exports (tenant-isolation tests call these on the facade)\n")
    for mod_name, handler in ROUTE_HANDLER_REEXPORTS:
        lines.append(
            f"from app.modules.housing_compat.routes.{mod_name} import {handler} as {handler}  # noqa: E402,F401\n"
        )
    return "".join(lines)


def main() -> None:
    lines = read_lines()
    original = len(lines)
    if original < 5000:
        raise SystemExit(f"Expected ~5476 lines, got {original}. Already extracted?")

    HELPERS.mkdir(parents=True, exist_ok=True)
    ROUTES.mkdir(parents=True, exist_ok=True)
    (HELPERS / "__init__.py").write_text("", encoding="utf-8")
    (ROUTES / "__init__.py").write_text("", encoding="utf-8")

    quarantine_body = build_quarantine(lines)

    helper_path = HELPERS / "shared.py"
    helper_path.write_text(build_helpers(lines), encoding="utf-8")

    for mod_name, start, end in ROUTE_SLICES:
        path = ROUTES / f"{mod_name}.py"
        path.write_text(build_route_module(mod_name, lines, start, end), encoding="utf-8")

    new_router = SLIM_HEADER + quarantine_body + build_facade_reexports()
    ROUTER.write_text(new_router, encoding="utf-8")

    updated = len(ROUTER.read_text(encoding="utf-8").splitlines())
    print(f"router.py: {original} -> {updated} lines")
    print(f"helpers/shared.py: {len(helper_path.read_text(encoding='utf-8').splitlines())} lines")
    print(f"route modules: {len(ROUTE_SLICES)}")


if __name__ == "__main__":
    main()
