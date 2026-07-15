
# ════════════════════════════════════════════════════════════════════════
# SECTION: MODULE HEADER + IMPORTS
# NOTE   : 9K-line MandirMitra FastAPI router. Use Ctrl+F '# SECTION:' to navigate.
# Split trigger: when a second developer joins or file exceeds 12K lines.
# ════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import calendar
import json
import logging
import os
import re
from urllib.parse import urlencode
from datetime import date, datetime, timedelta, timezone
from io import BytesIO, StringIO
import csv
import httpx
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal, InvalidOperation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader

try:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont, features as pil_features
except Exception:
    PILImage = None
    ImageDraw = None
    ImageFont = None
    pil_features = None

try:
    from weasyprint import HTML
except Exception:
    HTML = None

from app.core.auth.dependencies import get_current_user
from app.core.audit.service import log_audit_event
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.rate_limiting import limiter
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.db.mongo import get_collection
from app.db.postgres import get_async_session
from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.accounting.service import (
    AccountingValidationError,
    create_account,
    get_accounts_payable,
    get_accounts_receivable,
    get_balance_sheet,
    get_journal_drilldown,
    get_ledger_lines,
    get_profit_loss,
    get_receipts_payments,
    get_trial_balance,
    list_accounts,
    post_journal_entry,
    reverse_journal_entry,
    validate_cash_balance_for_journal_lines,
)
from app.accounting.schemas import JournalPostRequest, JournalLineIn
from app.modules.mandir_compat.report_helpers import (
    accounts_payable_report,
    accounts_receivable_report,
    balance_sheet_report,
    bank_book_report,
    cash_book_report,
    category_income_report,
    day_book_report,
    detailed_donation_report,
    detailed_seva_report,
    donation_category_wise_report,
    donation_daily_report,
    donation_monthly_report,
    journal_entries_report,
    ledger_report,
    posted_donations,
    posted_sevas,
    profit_loss_report,
    receipts_payments_report,
    seva_schedule_report,
    top_donors_report,
    trial_balance_report,
)
from app.modules.mandir_compat.donation_compliance import (
    classify_donation_compliance,
    compliance_public_fields,
    donation_compliance_config_view,
    validate_donation_compliance_config,
)
from app.modules.mandir_compat.schemas import (
    MandirFirstLoginOnboardingRequest,
    MandirFirstLoginOnboardingResponse,
)
from app.modules.mandir_compat.service import (
    create_mandir_first_login_onboarding,
    ensure_temple_numeric_id,
    list_mandir_temples,
    resolve_tenant_by_temple_id,
)
from app.services.panchang import PanchangService

router = APIRouter(tags=["mandir-compat"])
_MANDIR_WRITE_ROUTE_DEPS = [
    Depends(require_enabled_module("temple")),
    Depends(require_roles([Role.operator, Role.accountant, Role.tenant_admin, Role.super_admin])),
]
_MANDIR_ADMIN_ROUTE_DEPS = [
    Depends(require_enabled_module("temple")),
    Depends(require_roles([Role.tenant_admin, Role.super_admin])),
]
MANDIR_COMPAT_DATA_DIR = Path(__file__).resolve().parent / "data"
MANDIR_LEGACY_COA_PATH = MANDIR_COMPAT_DATA_DIR / "legacy_mandir_coa.json"
logger = logging.getLogger(__name__)

_MANDIR_COUNTERS_COLLECTION = "mandir_counters"
_MANDIR_RECEIPT_WIDTH = 7
_MANDIR_RECEIPT_PREFIX_BY_KIND = {
    "donation": "DON",
    "seva": "SEV",
}
_MANDIR_UTR_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{3,79}$")
_MANDIR_JOURNAL_ENTRY_PREFIX = "JE"
_DEFAULT_PUBLIC_DONATION_CATEGORIES = [
    {"id": "general", "name": "General Donation", "description": "General donation to the temple"},
    {"id": "annadanam", "name": "Annadanam", "description": "Sponsoring food/meals for devotees"},
    {"id": "construction", "name": "Construction Fund", "description": "Temple construction and renovation"},
    {"id": "corpus", "name": "Corpus Fund", "description": "Temple corpus fund"},
    {"id": "vastra_seva", "name": "Vastra Seva", "description": "Clothing and decoration for deity"},
    {"id": "nitya_puja", "name": "Nitya Puja", "description": "Daily worship sponsorship"},
]

_PANCHANG_DEFAULT_LOCATION = {
    "name": "Bengaluru",
    "state": "Karnataka",
    "country": "India",
    "lat": 12.9716,
    "lon": 77.5946,
    "timezone": "Asia/Kolkata",
    "display": "Bengaluru, Karnataka",
}

_PANCHANG_CITY_OPTIONS: tuple[dict[str, Any], ...] = (
    _PANCHANG_DEFAULT_LOCATION,
    {"name": "Mysuru", "state": "Karnataka", "country": "India", "lat": 12.2958, "lon": 76.6394, "timezone": "Asia/Kolkata", "display": "Mysuru, Karnataka"},
    {"name": "Mangaluru", "state": "Karnataka", "country": "India", "lat": 12.9141, "lon": 74.8560, "timezone": "Asia/Kolkata", "display": "Mangaluru, Karnataka"},
    {"name": "Udupi", "state": "Karnataka", "country": "India", "lat": 13.3409, "lon": 74.7421, "timezone": "Asia/Kolkata", "display": "Udupi, Karnataka"},
    {"name": "Chennai", "state": "Tamil Nadu", "country": "India", "lat": 13.0827, "lon": 80.2707, "timezone": "Asia/Kolkata", "display": "Chennai, Tamil Nadu"},
    {"name": "Coimbatore", "state": "Tamil Nadu", "country": "India", "lat": 11.0168, "lon": 76.9558, "timezone": "Asia/Kolkata", "display": "Coimbatore, Tamil Nadu"},
    {"name": "Madurai", "state": "Tamil Nadu", "country": "India", "lat": 9.9252, "lon": 78.1198, "timezone": "Asia/Kolkata", "display": "Madurai, Tamil Nadu"},
    {"name": "Hyderabad", "state": "Telangana", "country": "India", "lat": 17.3850, "lon": 78.4867, "timezone": "Asia/Kolkata", "display": "Hyderabad, Telangana"},
    {"name": "Tirupati", "state": "Andhra Pradesh", "country": "India", "lat": 13.6288, "lon": 79.4192, "timezone": "Asia/Kolkata", "display": "Tirupati, Andhra Pradesh"},
    {"name": "Mumbai", "state": "Maharashtra", "country": "India", "lat": 19.0760, "lon": 72.8777, "timezone": "Asia/Kolkata", "display": "Mumbai, Maharashtra"},
    {"name": "Pune", "state": "Maharashtra", "country": "India", "lat": 18.5204, "lon": 73.8567, "timezone": "Asia/Kolkata", "display": "Pune, Maharashtra"},
    {"name": "New Delhi", "state": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090, "timezone": "Asia/Kolkata", "display": "New Delhi, Delhi"},
    {"name": "Kolkata", "state": "West Bengal", "country": "India", "lat": 22.5726, "lon": 88.3639, "timezone": "Asia/Kolkata", "display": "Kolkata, West Bengal"},
    {"name": "Ahmedabad", "state": "Gujarat", "country": "India", "lat": 23.0225, "lon": 72.5714, "timezone": "Asia/Kolkata", "display": "Ahmedabad, Gujarat"},
    {"name": "Varanasi", "state": "Uttar Pradesh", "country": "India", "lat": 25.3176, "lon": 82.9739, "timezone": "Asia/Kolkata", "display": "Varanasi, Uttar Pradesh"},
)


_MANDIR_CANONICAL_INCOME_CODES: dict[str, tuple[str, str]] = {
    'general donation': ('44001', 'General Donations'),
    'donation income': ('44001', 'General Donations'),
    'general donations': ('44001', 'General Donations'),
    'specific purpose donation': ('44003', 'Specific Purpose Donations'),
    'specific purpose donations': ('44003', 'Specific Purpose Donations'),
    'in-kind donation income': ('44004', 'In-Kind Donation Income'),
    'in kind donation income': ('44004', 'In-Kind Donation Income'),
    'sponsorship': ('45001', 'Sponsorship Income'),
    'sponsorship income': ('45001', 'Sponsorship Income'),
    'in-kind sponsorship income': ('45002', 'In-Kind Sponsorship Income'),
    'in kind sponsorship income': ('45002', 'In-Kind Sponsorship Income'),
    'seva booking revenue': ('42002', 'Seva Income - General'),
    'pooja revenue': ('42002', 'Seva Income - General'),
    'seva income': ('42002', 'Seva Income - General'),
    'seva income - general': ('42002', 'Seva Income - General'),
}

_MANDIR_SPONSORSHIP_CATEGORY_MARKERS = {
    "annadanam",
    "annadana",
    "sponsorship",
    "flower",
    "decoration",
    "lighting",
    "vastra",
    "nitya puja",
    "festival",
}

_MANDIR_INCOME_BUCKET_ALIASES: dict[str, set[str]] = {
    'donation': {'general donation', 'donation income', 'general donations'},
    'seva': {'seva income', 'seva income - general', 'seva booking revenue', 'pooja revenue'},
}

_MANDIR_INCOME_LEGACY_CODES: dict[str, set[str]] = {
    'donation': {'4000'},
    'seva': {'4100'},
}

_MANDIR_LEGACY_ACCOUNT_CODE_MAP: dict[str, str] = {
    "1001": "11001",
    "1002": "12001",
    "4000": "44001",
    "4100": "42002",
}



# ════════════════════════════════════════════════════════════════════════
# SECTION: ACCOUNT CODE + CATEGORY HELPERS
# NOTE   : _normalize_mandir_account_code, _normalize_income_category, _normalize_public_payment_utr_reference, _is_mandir_sponsorship_category, _mandir_cash_income_category, _mandir_in_kind_income_category, _mandir_in_kind_debit_account_target, _mandir_income_bucket_for_account
# ════════════════════════════════════════════════════════════════════════

def _normalize_mandir_account_code(code: Any, *, account_name: Any = None) -> str:
    raw_code = str(code or "").strip()
    if not raw_code:
        return ""

    mapped = _MANDIR_LEGACY_ACCOUNT_CODE_MAP.get(raw_code)
    if mapped:
        return mapped

    if raw_code.isdigit() and len(raw_code) < 5:
        normalized_name = str(account_name or "").strip().lower()
        if "cash" in normalized_name or "hundi" in normalized_name:
            return "11001"
        if "bank" in normalized_name:
            return "12001"

    return raw_code


def _normalize_income_category(value: Any) -> str:
    return ' '.join(str(value or '').strip().lower().split())


def _normalize_public_payment_utr_reference(value: Any) -> str:
    reference = " ".join(str(value or "").strip().split())
    if not reference:
        raise HTTPException(status_code=400, detail="UTR/reference is required before verifying a public payment")
    if not _MANDIR_UTR_REFERENCE_PATTERN.fullmatch(reference):
        raise HTTPException(
            status_code=400,
            detail="UTR/reference must be 4-80 characters and contain only letters, numbers, spaces, dot, slash, colon, underscore, or hyphen",
        )
    return reference


def _is_mandir_sponsorship_category(value: Any) -> bool:
    normalized = _normalize_income_category(value)
    return any(marker in normalized for marker in _MANDIR_SPONSORSHIP_CATEGORY_MARKERS)


def _mandir_cash_income_category(category_name: Any) -> str:
    normalized = _normalize_income_category(category_name)
    if _is_mandir_sponsorship_category(normalized):
        return "Sponsorship Income"
    if any(marker in normalized for marker in ("construction", "renovation", "corpus", "specific purpose")):
        return "Specific Purpose Donations"
    return "General Donations"


def _mandir_in_kind_income_category(category_name: Any) -> str:
    return "In-Kind Sponsorship Income" if _is_mandir_sponsorship_category(category_name) else "In-Kind Donation Income"


def _mandir_in_kind_debit_account_target(
    payload: dict[str, Any],
    category_name: Any,
    *,
    inventory_accounting_enabled: bool = False,
) -> tuple[str, str, str]:
    item_text = _normalize_income_category(
        payload.get("in_kind_item_type")
        or payload.get("asset_type")
        or payload.get("item_type")
        or payload.get("item_name")
        or payload.get("description")
        or category_name
    )
    if any(marker in item_text for marker in ("gold", "silver", "ornament", "jewel", "idol", "vigraha", "precious")):
        return ("15010", "Temple Gold & Silver", "asset")
    if any(marker in item_text for marker in ("rice", "dal", "oil", "ghee", "prasadam", "annadan", "food")):
        if inventory_accounting_enabled:
            return ("14004", "Prasadam Inventory", "asset")
        return ("54007", "Prasadam Expenses", "expense")
    if any(marker in item_text for marker in ("flower", "decoration", "lighting", "festival", "event", "service")):
        return ("54006", "Decoration Expenses", "expense")
    if inventory_accounting_enabled:
        return ("14003", "Pooja Materials Inventory", "asset")
    return ("51004", "Pooja Materials Expenses", "expense")


def _mandir_income_bucket_for_account(name: Any, code: Any) -> str | None:
    normalized_name = _normalize_income_category(name)
    code_text = str(code or '').strip()

    if code_text in {'44001', *(_MANDIR_INCOME_LEGACY_CODES.get('donation') or set())}:
        return 'donation'
    if code_text in {'42002', *(_MANDIR_INCOME_LEGACY_CODES.get('seva') or set())}:
        return 'seva'

    if any(alias in normalized_name for alias in _MANDIR_INCOME_BUCKET_ALIASES['donation']):
        return 'donation'
    if any(alias in normalized_name for alias in _MANDIR_INCOME_BUCKET_ALIASES['seva']):
        return 'seva'
    return None



# ════════════════════════════════════════════════════════════════════════
# SECTION: ASYNC ACCOUNT RESOLVERS
# NOTE   : _normalize_mandir_income_accounts, _resolve_mandir_income_account, _resolve_or_create_mandir_account, _mandir_inventory_accounting_enabled, _resolve_mandir_in_kind_debit_account, _resolve_mandir_payment_account_id
# ════════════════════════════════════════════════════════════════════════

async def _normalize_mandir_income_accounts(session: AsyncSession, tenant_id: str) -> dict[str, int]:
    canonical_targets = {
        'donation': ('44001', 'General Donations'),
        'seva': ('42002', 'Seva Income - General'),
    }

    accounts = await list_accounts(session, tenant_id=tenant_id)
    income_accounts = [acc for acc in accounts if str(acc.type or '').strip().lower() == 'income']

    canonical_by_bucket: dict[str, Account] = {}
    dirty = False
    remapped_lines = 0

    for bucket, (target_code, target_name) in canonical_targets.items():
        canonical = next((acc for acc in income_accounts if str(acc.code or '').strip() == target_code), None)

        if canonical is None:
            candidate = next(
                (
                    acc
                    for acc in income_accounts
                    if _mandir_income_bucket_for_account(acc.name, acc.code) == bucket
                ),
                None,
            )
            if candidate is not None:
                candidate.code = target_code
                candidate.name = target_name
                candidate.type = 'income'
                candidate.classification = 'nominal'
                canonical = candidate
                dirty = True
            else:
                canonical = await create_account(
                    session,
                    tenant_id=tenant_id,
                    code=target_code,
                    name=target_name,
                    account_type='income',
                    classification='nominal',
                    is_cash_bank=False,
                    is_receivable=False,
                    is_payable=False,
                )
                accounts = await list_accounts(session, tenant_id=tenant_id)
                income_accounts = [acc for acc in accounts if str(acc.type or '').strip().lower() == 'income']

        canonical_by_bucket[bucket] = canonical

    for bucket, canonical in canonical_by_bucket.items():
        duplicate_ids = [
            int(acc.id)
            for acc in income_accounts
            if int(acc.id) != int(canonical.id)
            and _mandir_income_bucket_for_account(acc.name, acc.code) == bucket
        ]
        if not duplicate_ids:
            continue

        tenant_journal_ids = select(JournalEntry.id).where(JournalEntry.tenant_id == tenant_id)
        remap_stmt = (
            update(JournalLine)
            .where(
                JournalLine.account_id.in_(duplicate_ids),
                JournalLine.journal_id.in_(tenant_journal_ids),
            )
            .values(account_id=int(canonical.id))
        )
        result = await session.execute(remap_stmt)
        changed = int(result.rowcount or 0)
        if changed > 0:
            remapped_lines += changed
            dirty = True

    if dirty:
        await session.commit()

    return {'remapped_lines': remapped_lines}


async def _resolve_mandir_income_account(session: AsyncSession, tenant_id: str, category_name: str) -> int:
    normalized_category = _normalize_income_category(category_name)
    preferred_code, preferred_name = _MANDIR_CANONICAL_INCOME_CODES.get(
        normalized_category,
        ('42002', 'Seva Income - General') if any(token in normalized_category for token in ('seva', 'pooja')) else ('44001', 'General Donations'),
    )

    await _normalize_mandir_income_accounts(session, tenant_id)

    accounts = await list_accounts(session, tenant_id=tenant_id)
    for acc in accounts:
        if str(acc.type or '').strip().lower() == 'income' and str(acc.code or '').strip() == preferred_code:
            return int(acc.id)

    new_acc = await create_account(
        session,
        tenant_id=tenant_id,
        code=preferred_code,
        name=preferred_name,
        account_type='income',
        classification='nominal',
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    return int(new_acc.id)


async def _resolve_or_create_mandir_account(
    session: AsyncSession,
    tenant_id: str,
    *,
    code: str,
    name: str,
    account_type: str,
    classification: str,
) -> int:
    accounts = await list_accounts(session, tenant_id=tenant_id)
    for acc in accounts:
        if str(acc.code or "").strip() == str(code).strip():
            return int(acc.id)
    new_acc = await create_account(
        session,
        tenant_id=tenant_id,
        code=code,
        name=name,
        account_type=account_type,
        classification=classification,
        is_cash_bank=False,
        is_receivable=False,
        is_payable=False,
    )
    return int(new_acc.id)


async def _mandir_inventory_accounting_enabled(tenant_id: str, app_key: str) -> bool:
    query = {"tenant_id": tenant_id, "app_key": app_key}
    doc = await get_collection("mandir_temples").find_one(query)
    if doc is None:
        doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id}) or {}
    return bool(doc.get("module_inventory_enabled", False))


async def _resolve_mandir_in_kind_debit_account(
    session: AsyncSession,
    tenant_id: str,
    payload: dict[str, Any],
    category_name: Any,
    *,
    app_key: str = "mandirmitra",
) -> int:
    inventory_enabled = await _mandir_inventory_accounting_enabled(tenant_id, app_key)
    code, name, account_type = _mandir_in_kind_debit_account_target(
        payload,
        category_name,
        inventory_accounting_enabled=inventory_enabled,
    )
    classification = "nominal" if account_type == "expense" else "real"
    return await _resolve_or_create_mandir_account(
        session,
        tenant_id,
        code=code,
        name=name,
        account_type=account_type,
        classification=classification,
    )


async def _resolve_mandir_payment_account_id(
    session: AsyncSession,
    tenant_id: str,
    raw_account_id: Any,
    payment_mode: str | None,
) -> int | None:
    raw_value = str(raw_account_id).strip() if raw_account_id is not None else ""

    if raw_value:
        maybe_id = _safe_optional_int(raw_value)
        if maybe_id:
            by_id_stmt = select(Account.id).where(
                Account.tenant_id == tenant_id,
                Account.id == maybe_id,
            )
            by_id = (await session.execute(by_id_stmt)).scalar_one_or_none()
            if by_id is not None:
                return int(by_id)

        code_candidate = raw_value
        if " - " in raw_value:
            code_candidate = raw_value.split(" - ", 1)[0].strip()
        code_candidate = _normalize_mandir_account_code(code_candidate)

        if code_candidate.isdigit():
            by_code_stmt = select(Account.id).where(
                Account.tenant_id == tenant_id,
                Account.code == code_candidate,
            )
            by_code = (await session.execute(by_code_stmt)).scalar_one_or_none()
            if by_code is not None:
                return int(by_code)

    accounts = await list_accounts(session, tenant_id=tenant_id)
    mode = str(payment_mode or "").strip().lower()

    if mode == "cash":
        for preferred_code in ("11001",):
            preferred = next(
                (
                    acc
                    for acc in accounts
                    if acc.is_cash_bank and str(acc.code or "").strip() == preferred_code
                ),
                None,
            )
            if preferred is not None:
                return int(preferred.id)
        for acc in accounts:
            if acc.is_cash_bank and "cash" in str(acc.name).lower():
                return int(acc.id)
    elif mode == "bank":
        for preferred_code in ("12001",):
            preferred = next(
                (
                    acc
                    for acc in accounts
                    if acc.is_cash_bank and str(acc.code or "").strip() == preferred_code
                ),
                None,
            )
            if preferred is not None:
                return int(preferred.id)
        for acc in accounts:
            if acc.is_cash_bank and "bank" in str(acc.name).lower():
                return int(acc.id)

    for acc in accounts:
        if acc.is_cash_bank:
            return int(acc.id)

    return None


def _mandir_actor_id(current_user: dict[str, Any]) -> str:
    return str(
        current_user.get("sub")
        or current_user.get("user_id")
        or current_user.get("email")
        or "mandir_compat_system"
    )



# ════════════════════════════════════════════════════════════════════════
# SECTION: RECEIPT CANCELLATION HELPERS
# NOTE   : _mandir_actor_id, _mandir_receipt_cancellation_metadata, _reverse_mandir_source_journal, _cancel_mandir_receipt_source
# ════════════════════════════════════════════════════════════════════════

def _mandir_receipt_cancellation_metadata(payload: dict[str, Any] | None, current_user: dict[str, Any]) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    reason = str(
        payload.get("reason")
        or payload.get("cancellation_reason")
        or payload.get("refund_reason")
        or ""
    ).strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    now = datetime.now(timezone.utc).isoformat()
    refund_mode = _safe_optional_str(payload.get("refund_mode") or payload.get("refund_payment_mode"))
    refund_reference = _safe_optional_str(payload.get("refund_reference") or payload.get("refund_utr") or payload.get("refund_transaction_reference"))
    refund_date = _safe_optional_str(payload.get("refund_date")) or now[:10]
    return {
        "status": "reversed",
        "cancellation_reason": reason,
        "refund_mode": refund_mode,
        "refund_reference": refund_reference,
        "refund_date": refund_date if refund_mode or refund_reference else None,
        "reversed_at": now,
        "cancelled_at": now,
        "cancelled_by": _mandir_actor_id(current_user),
        "updated_at": now,
    }


async def _reverse_mandir_source_journal(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    source_key: str,
    reason: str,
    current_user: dict[str, Any],
) -> tuple[JournalEntry, bool]:
    stmt = select(JournalEntry).where(
        JournalEntry.tenant_id == tenant_id,
        JournalEntry.app_key == app_key,
        JournalEntry.accounting_entity_id == "primary",
        JournalEntry.idempotency_key == source_key,
    )
    original = (await session.execute(stmt)).scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Original accounting journal was not found for this receipt")
    try:
        return await reverse_journal_entry(
            session=session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            journal_id=int(original.id),
            created_by=_mandir_actor_id(current_user),
            reason=reason,
            idempotency_key=f"{source_key}_receipt_reversal",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reverse receipt journal: {exc}") from exc


async def _cancel_mandir_receipt_source(
    *,
    source_kind: str,
    source_id: str,
    collection_name: str,
    id_field: str,
    idempotency_prefix: str,
    payload: dict[str, Any] | None,
    session: AsyncSession,
    current_user: dict[str, Any],
    x_tenant_id: str | None,
    x_app_key: str | None,
) -> dict[str, Any]:
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation=f"{source_kind} receipt cancellation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    collection = get_collection(collection_name)
    existing = await collection.find_one({id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail=f"{source_kind.title()} receipt not found")

    current_status = str(existing.get("status") or "").strip().lower()
    if current_status in {"cancelled", "reversed"}:
        view = _mandir_donation_view(existing) if source_kind == "donation" else _mandir_seva_booking_view(existing)
        view["_idempotent"] = True
        return view

    patch = _mandir_receipt_cancellation_metadata(payload, current_user)
    reversal_entry, _created = await _reverse_mandir_source_journal(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        source_key=f"{idempotency_prefix}{source_id}",
        reason=str(patch["cancellation_reason"]),
        current_user=current_user,
    )
    patch["reversal_journal_id"] = int(reversal_entry.id)
    patch["reversal_idempotency_key"] = f"{idempotency_prefix}{source_id}_receipt_reversal"

    await collection.update_one(
        {id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=_mandir_actor_id(current_user),
            product=app_key,
            action=f"{source_kind}_receipt_cancelled",
            entity_type=f"mandir_{source_kind}_receipt",
            entity_id=str(source_id),
            old_value={"status": existing.get("status"), "receipt_number": existing.get("receipt_number")},
            new_value={
                "status": patch["status"],
                "reason": patch["cancellation_reason"],
                "reversal_journal_id": patch["reversal_journal_id"],
                "refund_mode": patch.get("refund_mode"),
                "refund_reference": patch.get("refund_reference"),
            },
        )
    except Exception:
        logger.warning("Failed to write audit event for %s receipt cancellation %s", source_kind, source_id, exc_info=True)

    updated = {**existing, **patch}
    return _mandir_donation_view(updated) if source_kind == "donation" else _mandir_seva_booking_view(updated)


MANDIR_DEFAULT_ACCOUNTS: list[dict[str, Any]] = [
    {
        "account_id": 11001,
        "account_code": "11001",
        "account_name": "Cash in Hand - Counter",
        "account_type": "asset",
        "classification": "real",
        "is_cash_bank": True,
        "cash_bank_nature": "cash",
        "is_receivable": False,
        "is_payable": False,
        "is_system_account": True,
    },
    {
        "account_id": 12001,
        "account_code": "12001",
        "account_name": "Bank - Current Account",
        "account_type": "asset",
        "classification": "real",
        "is_cash_bank": True,
        "cash_bank_nature": "bank",
        "is_receivable": False,
        "is_payable": False,
        "is_system_account": True,
    },
    {
        "account_id": 13000,
        "account_code": "13000",
        "account_name": "Trade Receivables",
        "account_type": "asset",
        "classification": "real",
        "is_cash_bank": False,
        "cash_bank_nature": None,
        "is_receivable": True,
        "is_payable": False,
        "is_system_account": True,
    },
    {
        "account_id": 44001,
        "account_code": "44001",
        "account_name": "General Donations",
        "account_type": "income",
        "classification": "nominal",
        "is_cash_bank": False,
        "cash_bank_nature": None,
        "is_receivable": False,
        "is_payable": False,
        "is_system_account": True,
    },
    {
        "account_id": 42002,
        "account_code": "42002",
        "account_name": "Seva Income - General",
        "account_type": "income",
        "classification": "nominal",
        "is_cash_bank": False,
        "cash_bank_nature": None,
        "is_receivable": False,
        "is_payable": False,
        "is_system_account": True,
    },
    {
        "account_id": 54012,
        "account_code": "54012",
        "account_name": "Miscellaneous Expenses",
        "account_type": "expense",
        "classification": "nominal",
        "is_cash_bank": False,
        "cash_bank_nature": None,
        "is_receivable": False,
        "is_payable": False,
        "is_system_account": True,
    },
]



# ════════════════════════════════════════════════════════════════════════
# SECTION: ACCOUNT SEEDING
# NOTE   : _mandir_seed_accounts, _mandir_account_view, _dedupe_mandir_account_docs, _ensure_default_mandir_accounts, _sync_mandir_sql_accounts_from_seed, _ensure_default_mandir_sql_accounts
# ════════════════════════════════════════════════════════════════════════

def _mandir_seed_accounts() -> list[dict[str, Any]]:
    legacy = _load_mandir_legacy_accounts()
    return legacy if legacy else MANDIR_DEFAULT_ACCOUNTS


def _mandir_account_view(doc: dict[str, Any]) -> dict[str, Any]:
    account_id = doc.get("account_id") or doc.get("_id")
    account_id_str = str(account_id or "")
    account_name = str(doc.get("account_name") or doc.get("name") or "Account")
    account_code = _normalize_mandir_account_code(
        doc.get("account_code") or account_id_str,
        account_name=account_name,
    )
    account_type = str(doc.get("account_type") or "asset")

    cash_bank_nature = str(doc.get("cash_bank_nature") or "").lower()
    return {
        "id": account_id,
        "account_id": account_id,
        "account_code": account_code,
        "account_name": account_name,
        "account_name_kannada": doc.get("account_name_kannada"),
        "description": doc.get("description"),
        "account_type": account_type,
        "account_subtype": doc.get("account_subtype"),
        "parent_account_id": doc.get("parent_account_id"),
        "is_system_account": bool(doc.get("is_system_account", False)),
        "is_active": bool(doc.get("is_active", True)),
        "cash_bank_nature": cash_bank_nature or None,
        "cash_account_id": account_id if cash_bank_nature == "cash" else None,
        "bank_account_id": account_id if cash_bank_nature == "bank" else None,
        "sub_accounts": [],
    }



def _dedupe_mandir_account_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_docs = sorted(
        docs,
        key=lambda item: (
            str(item.get("updated_at") or item.get("created_at") or ""),
            str(item.get("account_name") or item.get("name") or ""),
            str(item.get("account_id") or item.get("_id") or ""),
        ),
        reverse=True,
    )

    deduped: dict[str, dict[str, Any]] = {}
    for doc in ordered_docs:
        account_name = str(doc.get("account_name") or doc.get("name") or "").strip()
        account_code = _normalize_mandir_account_code(
            doc.get("account_code") or doc.get("account_id"),
            account_name=account_name,
        )
        dedupe_key = account_code or str(doc.get("account_id") or doc.get("_id") or "").strip()
        if not dedupe_key:
            continue
        deduped.setdefault(dedupe_key, doc)

    unique_docs = list(deduped.values())
    unique_docs.sort(
        key=lambda item: str(
            _normalize_mandir_account_code(
                item.get("account_code") or item.get("account_id"),
                account_name=item.get("account_name") or item.get("name"),
            )
            or item.get("account_id")
            or ""
        )
    )
    return unique_docs

async def _ensure_default_mandir_accounts(tenant_id: str, app_key: str) -> int:
    result = await _upsert_mandir_account_docs(
        tenant_id,
        app_key,
        _mandir_seed_accounts(),
        update_existing=False,
    )
    return result["created"]


async def _sync_mandir_sql_accounts_from_seed(
    session: AsyncSession,
    *,
    tenant_id: str,
    seed_rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Mirror Mandir COA seed rows into SQL accounts used by journal posting/reporting."""
    prepared_rows = _prepare_mandir_account_docs(seed_rows, tenant_id, "mandirmitra")
    if not prepared_rows:
        return {"created": 0, "updated": 0, "total": 0}

    valid_types = {"asset", "liability", "equity", "income", "expense"}
    valid_classifications = {"personal", "real", "nominal"}
    def _index_existing_accounts(rows: list[Account]) -> tuple[dict[str, Account], dict[tuple[str, str], list[Account]]]:
        by_code: dict[str, Account] = {}
        by_key: dict[tuple[str, str], list[Account]] = {}
        for acc in rows:
            code = str(acc.code or "").strip()
            if code:
                by_code[code] = acc
            key = (" ".join(str(acc.name or "").strip().lower().split()), str(acc.type or "").strip().lower())
            by_key.setdefault(key, []).append(acc)
        return by_code, by_key

    existing_accounts = await list_accounts(session, tenant_id=tenant_id)
    existing_by_code, existing_by_key = _index_existing_accounts(existing_accounts)
    created = 0
    updated = 0
    dirty = False

    for row in prepared_rows:
        code = str(row.get("account_code") or "").strip()
        account_type = str(row.get("account_type") or "asset").strip().lower()
        if not code or account_type not in valid_types:
            continue

        account_name = str(row.get("account_name") or "Account").strip() or "Account"
        classification = str(row.get("classification") or "real").strip().lower()
        if classification not in valid_classifications:
            classification = "real" if account_type in {"asset", "liability", "equity"} else "nominal"

        existing = existing_by_code.get(code)
        if existing is None:
            key = (" ".join(account_name.lower().split()), account_type)
            candidates = existing_by_key.get(key, [])
            existing = next(
                (
                    acc
                    for acc in candidates
                    if (not str(acc.code or "").strip())
                    or str(acc.code or "").strip().upper().startswith("INC-M-")
                    or (str(acc.code or "").strip().isdigit() and len(str(acc.code or "").strip()) < 5)
                ),
                None,
            )

        if existing is None:
            try:
                created_acc = await create_account(
                    session,
                    tenant_id=tenant_id,
                    code=code,
                    name=account_name,
                    account_type=account_type,
                    classification=classification,
                    is_cash_bank=bool(row.get("is_cash_bank", False)),
                    is_receivable=bool(row.get("is_receivable", False)),
                    is_payable=bool(row.get("is_payable", False)),
                )
                created += 1
                existing_by_code[code] = created_acc
                key = (" ".join(str(created_acc.name or "").strip().lower().split()), str(created_acc.type or "").strip().lower())
                existing_by_key.setdefault(key, []).append(created_acc)
            except IntegrityError:
                await session.rollback()
                # Rollback expires ORM instances; rebuild indexes from a fresh query.
                existing_accounts = await list_accounts(session, tenant_id=tenant_id)
                existing_by_code, existing_by_key = _index_existing_accounts(existing_accounts)
            continue

        changed = False
        if str(existing.code or "").strip() != code:
            existing.code = code
            changed = True
        if str(existing.name or "").strip() != account_name:
            existing.name = account_name
            changed = True
        if str(existing.type or "").strip().lower() != account_type:
            existing.type = account_type
            changed = True
        if str(existing.classification or "").strip().lower() != classification:
            existing.classification = classification
            changed = True
        if bool(existing.is_cash_bank) != bool(row.get("is_cash_bank", False)):
            existing.is_cash_bank = bool(row.get("is_cash_bank", False))
            changed = True
        if bool(existing.is_receivable) != bool(row.get("is_receivable", False)):
            existing.is_receivable = bool(row.get("is_receivable", False))
            changed = True
        if bool(existing.is_payable) != bool(row.get("is_payable", False)):
            existing.is_payable = bool(row.get("is_payable", False))
            changed = True

        if changed:
            updated += 1
            dirty = True
        existing_by_code[code] = existing

    if dirty:
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()

    return {"created": created, "updated": updated, "total": len(prepared_rows)}


async def _ensure_default_mandir_sql_accounts(session: AsyncSession, tenant_id: str) -> None:
    await _sync_mandir_sql_accounts_from_seed(
        session,
        tenant_id=tenant_id,
        seed_rows=_mandir_seed_accounts(),
    )
    await _normalize_mandir_income_accounts(session, tenant_id)

async def _ensure_default_mandir_sql_accounts_safe(
    session: AsyncSession, tenant_id: str, *, raise_on_failure: bool = False
) -> None:
    if not hasattr(session, "execute"):
        return
    try:
        await _ensure_default_mandir_sql_accounts(session, tenant_id)
    except Exception as exc:
        rollback = getattr(session, "rollback", None)
        if callable(rollback):
            try:
                await rollback()
            except Exception:
                pass
        if raise_on_failure:
            logger.error(
                "COA normalization failed for tenant %s - aborting posting: %s",
                tenant_id, exc, exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Accounting setup is incomplete. Please retry in a moment or contact support.",
            ) from exc
        logger.warning("Skipped COA normalization for tenant %s due to: %s", tenant_id, exc)
        return


# ════════════════════════════════════════════════════════════════════════
# SECTION: SAFE TYPE COERCIONS
# NOTE   : _safe_float, _safe_optional_float, _safe_optional_int, _safe_bool, _safe_optional_str, _parse_opening_balance_decimal
# ════════════════════════════════════════════════════════════════════════

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0

    raw = str(value).strip().lower()
    if raw in {"true", "1", "yes", "y", "on"}:
        return True
    if raw in {"false", "0", "no", "n", "off", ""}:
        return False
    return default


def _safe_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return raw if raw else None


def _parse_opening_balance_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    cleaned = raw.replace(',', '')
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = f"-{cleaned[1:-1]}"
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Invalid amount value: {value}")



# ════════════════════════════════════════════════════════════════════════
# SECTION: OPENING BALANCE HELPERS
# NOTE   : _parse_opening_balance_rows, _find_or_create_opening_balance_offset_account, _current_opening_balance_net
# ════════════════════════════════════════════════════════════════════════

async def _parse_opening_balance_rows(file: UploadFile) -> list[dict[str, Any]]:
    filename = str(file.filename or '').strip()
    if not filename:
        raise HTTPException(status_code=400, detail='File name is required')

    suffix = Path(filename).suffix.lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail='Uploaded file is empty')

    if suffix == '.csv':
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail='Unable to decode CSV file as UTF-8') from exc
        rows = list(csv.DictReader(StringIO(text)))
        return [row for row in rows if isinstance(row, dict)]

    if suffix in {'.xlsx', '.xlsm'}:
        try:
            from openpyxl import load_workbook
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail='XLSX import support is unavailable on server (missing openpyxl dependency)',
            ) from exc

        try:
            workbook = load_workbook(BytesIO(raw), data_only=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail='Unable to read XLSX workbook') from exc

        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            return []

        headers = [str(cell).strip() if cell is not None else '' for cell in values[0]]
        parsed_rows: list[dict[str, Any]] = []
        for row in values[1:]:
            if not any(cell not in (None, '') for cell in row):
                continue
            item: dict[str, Any] = {}
            for index, header in enumerate(headers):
                if not header:
                    continue
                if index < len(row):
                    item[header] = row[index]
            if item:
                parsed_rows.append(item)
        return parsed_rows

    raise HTTPException(status_code=400, detail='Unsupported file format. Use .csv or .xlsx')


async def _find_or_create_opening_balance_offset_account(session: AsyncSession, tenant_id: str) -> Account:
    stmt = select(Account).where(
        Account.tenant_id == tenant_id,
        Account.code == '33001',
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    try:
        return await create_account(
            session,
            tenant_id=tenant_id,
            code='33001',
            name='Opening Balance',
            account_type='equity',
            classification='real',
            is_cash_bank=False,
            is_receivable=False,
            is_payable=False,
        )
    except IntegrityError:
        await session.rollback()
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            raise
        return existing


async def _current_opening_balance_net(
    session: AsyncSession,
    *,
    tenant_id: str,
    account_id: int,
    reference: str,
) -> Decimal:
    stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), 0).label('debit_total'),
            func.coalesce(func.sum(JournalLine.credit), 0).label('credit_total'),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.reference == reference,
            JournalLine.account_id == account_id,
        )
    )
    row = (await session.execute(stmt)).one()
    debit_total = Decimal(str(row.debit_total or 0))
    credit_total = Decimal(str(row.credit_total or 0))
    return debit_total - credit_total


@lru_cache(maxsize=1)

# ════════════════════════════════════════════════════════════════════════
# SECTION: LEGACY COA IMPORT
# NOTE   : _load_mandir_legacy_accounts, _coerce_account_id, _infer_cash_bank_nature, _infer_flag, _prepare_mandir_account_docs, _upsert_mandir_account_docs
# ════════════════════════════════════════════════════════════════════════

def _load_mandir_legacy_accounts() -> list[dict[str, Any]]:
    if not MANDIR_LEGACY_COA_PATH.exists():
        return []

    payload = json.loads(MANDIR_LEGACY_COA_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {MANDIR_LEGACY_COA_PATH}")

    rows: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _coerce_account_id(value: Any, account_code: str) -> Any:
    if value is not None and str(value).strip():
        return value
    if account_code.isdigit():
        return int(account_code)
    return account_code


def _infer_cash_bank_nature(account_name: str, account_type: str, account_subtype: str | None) -> str | None:
    normalized_name = account_name.lower()
    normalized_type = account_type.lower()
    normalized_subtype = (account_subtype or "").lower()

    cash_markers = ("cash", "hundi", "petty", "counter")
    bank_markers = ("bank", "current account", "savings account", "od / cc", "od/cc", "od cc", "fixed deposit", "fd", "margin money")

    if any(marker in normalized_name for marker in bank_markers):
        return "bank"
    if any(marker in normalized_name for marker in cash_markers):
        return "cash"
    if normalized_subtype == "cash_bank" and normalized_type == "asset":
        return "cash"
    return None


def _infer_flag(account_name: str, account_subtype: str | None, *markers: str) -> bool:
    normalized_name = account_name.lower()
    normalized_subtype = (account_subtype or "").lower()
    if normalized_subtype in markers:
        return True
    return any(marker in normalized_name for marker in markers)


def _prepare_mandir_account_docs(seed_rows: list[dict[str, Any]], tenant_id: str, app_key: str) -> list[dict[str, Any]]:
    code_to_account_id: dict[str, Any] = {}
    prepared_rows: list[dict[str, Any]] = []

    for seed in seed_rows:
        account_code = str(seed.get("account_code") or seed.get("account_id") or "").strip()
        if not account_code:
            continue

        account_name = str(seed.get("account_name") or seed.get("name") or "Account").strip() or "Account"
        account_type = str(seed.get("account_type") or "asset").strip().lower() or "asset"
        account_subtype = _safe_optional_str(seed.get("account_subtype"))
        account_id = _coerce_account_id(seed.get("account_id"), account_code)
        parent_account_code = _safe_optional_str(seed.get("parent_account_code"))
        cash_bank_nature = _safe_optional_str(seed.get("cash_bank_nature"))
        if cash_bank_nature:
            cash_bank_nature = cash_bank_nature.lower()
        else:
            cash_bank_nature = _infer_cash_bank_nature(account_name, account_type, account_subtype)

        is_cash_bank = _safe_bool(seed.get("is_cash_bank"), False) or cash_bank_nature in {"cash", "bank"} or account_subtype == "cash_bank"
        is_receivable = _safe_bool(seed.get("is_receivable"), False) or _infer_flag(account_name, account_subtype, "receivable", "debtors", "advance")
        is_payable = _safe_bool(seed.get("is_payable"), False) or _infer_flag(account_name, account_subtype, "payable", "creditors")
        classification = str(seed.get("classification") or ("nominal" if account_type in {"income", "expense"} else "real")).strip().lower() or "real"

        prepared = {
            "account_id": account_id,
            "account_code": account_code,
            "account_name": account_name,
            "account_type": account_type,
            "classification": classification,
            "account_subtype": account_subtype,
            "description": seed.get("description"),
            "parent_account_code": parent_account_code,
            "is_cash_bank": is_cash_bank,
            "cash_bank_nature": cash_bank_nature,
            "is_receivable": is_receivable,
            "is_payable": is_payable,
            "is_system_account": _safe_bool(seed.get("is_system_account"), True),
            "is_active": _safe_bool(seed.get("is_active"), True),
            "is_locked": _safe_bool(seed.get("is_locked"), False),
            "account_name_kannada": seed.get("account_name_kannada"),
        }
        code_to_account_id[account_code] = account_id
        prepared_rows.append(prepared)

    for row in prepared_rows:
        parent_code = _safe_optional_str(row.get("parent_account_code"))
        row["parent_account_id"] = code_to_account_id.get(parent_code) if parent_code else None
        row["source"] = "mandir_legacy_coa"
    return prepared_rows


async def _upsert_mandir_account_docs(
    tenant_id: str,
    app_key: str,
    seed_rows: list[dict[str, Any]],
    *,
    update_existing: bool = True,
) -> dict[str, int]:
    accounts = get_collection("accounting_accounts")
    existing_docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key}).to_list(length=1000)
    existing_by_code = {
        str(doc.get("account_code") or doc.get("account_id") or "").strip(): doc
        for doc in existing_docs
        if str(doc.get("account_code") or doc.get("account_id") or "").strip()
    }

    prepared_rows = _prepare_mandir_account_docs(seed_rows, tenant_id, app_key)
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    reactivated = 0
    updated = 0

    for row in prepared_rows:
        account_code = str(row["account_code"]).strip()
        existing = existing_by_code.get(account_code)
        row_doc = {
            **row,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "name": row["account_name"],
            "updated_at": now,
        }

        if existing is None:
            row_doc["created_at"] = now
            await accounts.insert_one(row_doc)
            created += 1
            continue
        if not update_existing:
            continue
        if not _safe_bool(existing.get("is_active"), True):
            reactivated += 1
        else:
            updated += 1

        await accounts.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "account_code": account_code},
            {
                "$set": row_doc,
                "$setOnInsert": {"created_at": existing.get("created_at") or now},
            },
            upsert=True,
        )

    return {
        "created": created,
        "reactivated": reactivated,
        "updated": updated,
        "total": len(prepared_rows),
    }


def _sanitize_mongo_doc(doc: dict[str, Any]) -> dict[str, Any]:
    row = dict(doc or {})
    # ObjectId is not JSON serializable; hide Mongo internals from API clients.
    row.pop("_id", None)
    return row



# ════════════════════════════════════════════════════════════════════════
# SECTION: SEQUENCE NUMBERS
# NOTE   : _format_mandir_receipt_number, _format_mandir_sequence_number, _next_receipt_number, _next_journal_entry_number, _receipt_number_for_donation, _sanitize_mongo_doc
# ════════════════════════════════════════════════════════════════════════

def _format_mandir_receipt_number(prefix: str, sequence: int) -> str:
    normalized_prefix = str(prefix or "").strip().upper()
    if normalized_prefix not in {"DON", "SEV"}:
        raise ValueError(f"Unsupported MandirMitra receipt prefix: {prefix!r}")
    if int(sequence) < 1:
        raise ValueError("Receipt sequence must be positive")
    return f"{normalized_prefix}-{int(sequence):0{_MANDIR_RECEIPT_WIDTH}d}"


def _format_mandir_sequence_number(prefix: str, sequence: int) -> str:
    normalized_prefix = str(prefix or "").strip().upper()
    if not normalized_prefix:
        raise ValueError("Sequence prefix is required")
    if int(sequence) < 1:
        raise ValueError("Sequence must be positive")
    return f"{normalized_prefix}-{int(sequence):0{_MANDIR_RECEIPT_WIDTH}d}"


async def _next_receipt_number(
    *,
    tenant_id: str,
    app_key: str,
    receipt_kind: str,
    receipt_date: Any = None,
) -> str:
    prefix = _MANDIR_RECEIPT_PREFIX_BY_KIND.get(str(receipt_kind or "").strip().lower())
    if not prefix:
        raise ValueError(f"Unsupported MandirMitra receipt kind: {receipt_kind!r}")

    now = datetime.now(timezone.utc).isoformat()
    counter_id = f"{app_key}:{tenant_id}:receipt:{prefix}"
    counters = get_collection(_MANDIR_COUNTERS_COLLECTION)
    result = await counters.find_one_and_update(
        {"_id": counter_id},
        {
            "$inc": {"seq": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "app_key": app_key,
                "tenant_id": tenant_id,
                "prefix": prefix,
                "kind": receipt_kind,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    sequence = int((result or {}).get("seq") or 1)
    return _format_mandir_receipt_number(prefix, sequence)


async def _next_journal_entry_number(*, tenant_id: str, app_key: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    counter_id = f"{app_key}:{tenant_id}:journal-entry:{_MANDIR_JOURNAL_ENTRY_PREFIX}"
    counters = get_collection(_MANDIR_COUNTERS_COLLECTION)
    result = await counters.find_one_and_update(
        {"_id": counter_id},
        {
            "$inc": {"seq": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "app_key": app_key,
                "tenant_id": tenant_id,
                "prefix": _MANDIR_JOURNAL_ENTRY_PREFIX,
                "kind": "journal_entry",
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    sequence = int((result or {}).get("seq") or 1)
    return _format_mandir_sequence_number(_MANDIR_JOURNAL_ENTRY_PREFIX, sequence)



def _receipt_number_for_donation(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    donation_id = str(doc.get("donation_id") or doc.get("id") or "").strip()
    if donation_id:
        return f"DON-{donation_id[:8].upper()}"

    return f"DON-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"



# ════════════════════════════════════════════════════════════════════════
# SECTION: DONATION VIEW + ROW FILTERING
# NOTE   : _mandir_donation_view, _mandir_row_date_text, _mandir_row_matches_search, _mandir_filter_rows
# ════════════════════════════════════════════════════════════════════════

def _mandir_donation_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    row.pop("donor_pan", None)
    row.update(compliance_public_fields(doc))
    donation_id = str(row.get("donation_id") or row.get("id") or "").strip()
    if donation_id and not str(row.get("id") or "").strip():
        row["id"] = donation_id
    if donation_id and not str(row.get("donation_id") or "").strip():
        row["donation_id"] = donation_id

    receipt_number = _receipt_number_for_donation(row)
    row["receipt_number"] = receipt_number
    if donation_id:
        row["receipt_pdf_url"] = f"/api/v1/donations/{donation_id}/receipt/pdf"
    if not row.get("donation_date") and row.get("created_at"):
        row["donation_date"] = row.get("created_at")
    return row


def _mandir_row_date_text(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return value[:10]
    return ""


def _mandir_row_matches_search(row: dict[str, Any], query: str, fields: tuple[str, ...]) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    return any(normalized_query in str(row.get(field) or "").lower() for field in fields)


def _mandir_filter_rows(
    rows: list[dict[str, Any]],
    *,
    q: str | None,
    from_date: date | None,
    to_date: date | None,
    date_fields: tuple[str, ...],
    search_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    from_text = from_date.isoformat() if from_date else None
    to_text = to_date.isoformat() if to_date else None
    for row in rows:
        row_date = _mandir_row_date_text(row, date_fields)
        if from_text and row_date and row_date < from_text:
            continue
        if to_text and row_date and row_date > to_text:
            continue
        if q and not _mandir_row_matches_search(row, q, search_fields):
            continue
        filtered.append(row)
    return filtered



# ════════════════════════════════════════════════════════════════════════
# SECTION: DONATION RECEIPT PDF (ReportLab)
# NOTE   : _generate_donation_receipt_pdf_bytes
# ════════════════════════════════════════════════════════════════════════

def _generate_donation_receipt_pdf_bytes(
    donation: dict[str, Any],
    *,
    temple_name: str = "Temple",
    temple_profile: dict[str, Any] | None = None,
) -> bytes:
    temple_profile = _build_temple_receipt_profile(temple_profile or {"temple_name": temple_name})
    amount = _safe_float(donation.get("amount"), 0.0)
    devotee = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
    party_source = {
        "devotee_name": donation.get("devotee_name"),
        "name": donation.get("devotee_name") or donation.get("name"),
        "name_prefix": donation.get("devotee_prefix") or donation.get("name_prefix"),
    }
    address_source = {
        "devotee_address": donation.get("devotee_address") or donation.get("address"),
        "city": donation.get("devotee_city") or donation.get("city"),
        "state": donation.get("devotee_state") or donation.get("state"),
        "pincode": donation.get("devotee_pincode") or donation.get("pincode"),
    }
    devotee_name = _compose_receipt_party_name(party_source, devotee, fallback="Unknown Devotee")
    payment_mode = _format_payment_mode_for_receipt(donation.get("payment_mode") or donation.get("payment_method") or "Cash")
    receipt_number = _receipt_number_for_donation(donation)
    donation_date = _format_receipt_date(donation.get("donation_date") or donation.get("created_at"))
    category = str(donation.get("category") or "General Donation").strip() or "General Donation"
    item_parts = [
        str(donation.get("in_kind_item_name") or "").strip(),
        str(donation.get("in_kind_quantity") or "").strip(),
    ]
    item_text = " - ".join(part for part in item_parts if part)
    line_description = category
    if str(donation.get("donation_type") or "").strip().lower() == "in_kind" and item_text:
        line_description = f"{category} ({item_text})"
    devotee_address = _compose_receipt_address_line(address_source, devotee, fallback="--")
    payload = {
        **temple_profile,
        "receipt_title": "Donation Receipt",
        "receipt_title_local": "ದೇಣಿಗೆ ರಶೀದಿ",
        "line_item_header": "Donation Details",
        "line_item_local": "ದೇಣಿಗೆ ವಿವರ",
        "service_date_label": "Donation Date",
        "receipt_number": receipt_number,
        "receipt_date": donation_date,
        "party_name": devotee_name,
        "address_value": devotee_address,
        "amount_words_line": _amount_words_receipt_line(amount, local_language=temple_profile.get("local_language")),
        "payment_line": _receipt_payment_line(
            payment_mode=payment_mode,
            local_language=temple_profile.get("local_language"),
            purpose="donation",
        ),
        "line_items": [{"description": line_description, "amount": amount}],
        "total_amount": amount,
        "include_astro_row": False,
        "include_service_row": False,
        "include_note_row": False,
        "service_date": donation_date,
        "note_english": "",
        "system_generated_line": "",
        "powered_by_line": "Powered by Sanmitra Tech Solutions.",
        "local_language": temple_profile.get("local_language"),
        "use_local_labels": True,
    }
    return _build_receipt_pdf_bytes(payload)



# ════════════════════════════════════════════════════════════════════════
# SECTION: SEVA RECEIPT PDF (ReportLab) + SEVA BOOKING VIEW
# NOTE   : _receipt_number_for_seva, _mandir_seva_booking_view, _generate_seva_receipt_pdf_bytes
# ════════════════════════════════════════════════════════════════════════

def _receipt_number_for_seva(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    booking_id = str(doc.get("id") or doc.get("booking_id") or "").strip()
    if booking_id:
        return f"SEV-{booking_id[:8].upper()}"

    return f"SEV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _mandir_seva_booking_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    booking_id = str(row.get("id") or row.get("booking_id") or "").strip()
    if booking_id and not str(row.get("id") or "").strip():
        row["id"] = booking_id
    receipt_number = _receipt_number_for_seva(row)
    row["receipt_number"] = receipt_number
    if booking_id:
        row["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id}/receipt/pdf"
    return row


def _generate_seva_receipt_pdf_bytes(
    booking: dict[str, Any],
    *,
    temple_name: str = "Temple",
    temple_profile: dict[str, Any] | None = None,
) -> bytes:
    temple_profile = _build_temple_receipt_profile(temple_profile or {"temple_name": temple_name})
    amount = _safe_float(booking.get("amount_paid") or booking.get("amount"), 0.0)
    seva_name = str(booking.get("seva_name") or booking.get("seva") or "Seva Booking").strip() or "Seva Booking"
    use_local_labels = bool(temple_profile.get("local_language"))
    seva_name_local = _as_text(
        booking.get("seva_name_local")
        or booking.get("name_kannada")
        or booking.get("seva_name_kannada"),
        "",
    )
    devotee = booking.get("devotee") if isinstance(booking.get("devotee"), dict) else {}
    party_source = {
        "devotee_name": booking.get("devotee_names") or booking.get("devotee_name"),
        "name": booking.get("devotee_names") or booking.get("devotee_name"),
        "name_prefix": booking.get("devotee_prefix") or booking.get("name_prefix"),
    }
    address_source = {
        "devotee_address": booking.get("devotee_address") or booking.get("address"),
        "city": booking.get("devotee_city") or booking.get("city"),
        "state": booking.get("devotee_state") or booking.get("state"),
        "pincode": booking.get("devotee_pincode") or booking.get("pincode"),
    }
    devotee_name = _compose_receipt_party_name(party_source, devotee, fallback="Devotee")
    booking_date = _format_receipt_date(booking.get("booking_date") or booking.get("created_at"))
    payment_mode = _format_payment_mode_for_receipt(booking.get("payment_mode") or booking.get("payment_method") or "Cash")
    receipt_number = _receipt_number_for_seva(booking)
    devotee_address = _compose_receipt_address_line(address_source, devotee, fallback="--")
    line_items = _extract_seva_line_items(
        booking,
        fallback_name=_compose_receipt_line_description(seva_name, seva_name_local, use_local_labels=use_local_labels),
        fallback_amount=amount,
        use_local_labels=use_local_labels,
    )
    total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)
    if total_amount <= 0:
        total_amount = amount

    payload = {
        **temple_profile,
        "receipt_title": "Seva Receipt",
        "receipt_title_local": "ಸೇವಾ ರಶೀದಿ",
        "receipt_number": receipt_number,
        "receipt_date": booking_date,
        "party_name": devotee_name,
        "address_value": devotee_address,
        "amount_words_line": _amount_words_receipt_line(total_amount, local_language=temple_profile.get("local_language")),
        "payment_line": _receipt_payment_line(
            payment_mode=payment_mode,
            local_language=temple_profile.get("local_language"),
            purpose="seva",
        ),
        "line_items": line_items,
        "total_amount": total_amount,
        "include_astro_row": True,
        "include_service_row": True,
        "gotra": booking.get("gotra"),
        "nakshatra": booking.get("nakshatra") or booking.get("star"),
        "rashi": booking.get("rashi"),
        "service_date": _format_receipt_date(booking.get("seva_date") or booking.get("booking_date") or booking.get("created_at")),
        "note_english": "Note: Sevakartas to be present 10 minutes before Pooja time for Sankalpa and collect the prasadam on the same day.",
        "powered_by_line": "Powered by Sanmitra Tech Solutions.",
        "local_language": temple_profile.get("local_language"),
        "use_local_labels": True,
    }
    return _build_receipt_pdf_bytes(payload)


_ONES_WORDS = [
    "ZERO",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
    "THIRTEEN",
    "FOURTEEN",
    "FIFTEEN",
    "SIXTEEN",
    "SEVENTEEN",
    "EIGHTEEN",
    "NINETEEN",
]
_TENS_WORDS = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]
_KANNADA_ONES_WORDS = [
    "ಸೊನ್ನೆ",
    "ಒಂದು",
    "ಎರಡು",
    "ಮೂರು",
    "ನಾಲ್ಕು",
    "ಐದು",
    "ಆರು",
    "ಏಳು",
    "ಎಂಟು",
    "ಒಂಬತ್ತು",
    "ಹತ್ತು",
    "ಹನ್ನೊಂದು",
    "ಹನ್ನೆರಡು",
    "ಹದಿಮೂರು",
    "ಹದಿನಾಲ್ಕು",
    "ಹದಿನೈದು",
    "ಹದಿನಾರು",
    "ಹದಿನೇಳು",
    "ಹದಿನೆಂಟು",
    "ಹತ್ತೊಂಬತ್ತು",
]
_KANNADA_TENS_WORDS = {
    20: "ಇಪ್ಪತ್ತು",
    30: "ಮೂವತ್ತು",
    40: "ನಲವತ್ತು",
    50: "ಐವತ್ತು",
    60: "ಅರವತ್ತು",
    70: "ಎಪ್ಪತ್ತು",
    80: "ಎಂಬತ್ತು",
    90: "ತೊಂಬತ್ತು",
}
_KANNADA_COMPOUND_TENS_STEMS = {
    20: "\u0c87\u0caa\u0ccd\u0caa\u0ca4\u0ccd",
    30: "\u0cae\u0cc2\u0cb5\u0ca4\u0ccd",
    40: "\u0ca8\u0cb2\u0cb5\u0ca4\u0ccd",
    50: "\u0c90\u0cb5\u0ca4\u0ccd",
    60: "\u0c85\u0cb0\u0cb5\u0ca4\u0ccd",
    70: "\u0c8e\u0caa\u0ccd\u0caa\u0ca4\u0ccd",
    80: "\u0c8e\u0c82\u0cac\u0ca4\u0ccd",
    90: "\u0ca4\u0cca\u0c82\u0cac\u0ca4\u0ccd",
}
_KANNADA_COMPOUND_SUFFIXES = {
    1: "\u0ca4\u0cca\u0c82\u0ca6\u0cc1",
    2: "\u0ca4\u0cc6\u0cb0\u0ca1\u0cc1",
    3: "\u0ca4\u0cae\u0cc2\u0cb0\u0cc1",
    4: "\u0ca8\u0cbe\u0cb2\u0ccd\u0c95\u0cc1",
    5: "\u0ca4\u0cc8\u0ca6\u0cc1",
    6: "\u0ca4\u0cbe\u0cb0\u0cc1",
    7: "\u0ca4\u0cc7\u0cb3\u0cc1",
    8: "\u0ca4\u0cc6\u0c82\u0c9f\u0cc1",
    9: "\u0ca4\u0cca\u0c82\u0cac\u0ca4\u0ccd\u0ca4\u0cc1",
}

_SUPPORTED_LOCAL_LANGUAGES = {"kannada", "tamil", "telugu", "malayalam", "hindi"}
_HTML_LANG_BY_LOCAL_LANGUAGE = {
    "kannada": "kn",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "hindi": "hi",
}

_LOCAL_LABELS = {
    "kannada": {
        "receipt_title": "ರಶೀದಿ",
        "receipt_number": "ರಶೀದಿ ಸಂಖ್ಯೆ",
        "date": "ದಿನಾಂಕ",
        "party": "ಭಕ್ತ",
        "donation_party": "ದಾನಿ",
        "address": "ವಿಳಾಸ",
        "line_item": "ಸೇವಾ ವಿವರ",
        "total": "ಒಟ್ಟು ಮೊತ್ತ",
        "gotra": "ಗೋತ್ರ",
        "nakshatra": "ನಕ್ಷತ್ರ",
        "rashi": "ರಾಶಿ",
        "service_date": "ಸೇವಾ ದಿನಾಂಕ",
        "cashier": "ನಗದುಗಾರ",
        "note": "ಸೂಚನೆ: ಸೇವಾಕರ್ತರು ಪೂಜೆಯ ಸಮಯಕ್ಕಿಂತ 10 ನಿಮಿಷ ಮೊದಲು ಹಾಜರಿರಬೇಕು ಮತ್ತು ಅದೇ ದಿನ ಪ್ರಸಾದವನ್ನು ಪಡೆಯಬೇಕು.",
    },
    "tamil": {
        "receipt_title": "?????",
        "receipt_number": "????? ???",
        "date": "????",
        "party": "????/???????",
        "address": "??????",
        "line_item": "???? ??????",
        "total": "???????",
        "gotra": "?????????",
        "nakshatra": "???????????",
        "rashi": "????",
        "service_date": "???? ????",
        "cashier": "?????????",
        "note": "????????: ???? ??????????? 10 ??????? ?????? ?????? ??????? ??? ?????? ???????? ???????.",
    },
    "telugu": {
        "receipt_title": "?????",
        "receipt_number": "????? ?????",
        "date": "????",
        "party": "????/???????",
        "address": "????????",
        "line_item": "??? ???????",
        "total": "??????",
        "gotra": "??????",
        "nakshatra": "????????",
        "rashi": "????",
        "service_date": "??? ????",
        "cashier": "??????",
        "note": "?????: ??? ???????? 10 ??????? ????? ???? ????? ??????? ??? ????? ?????????.",
    },
    "malayalam": {
        "receipt_title": "?????",
        "receipt_number": "????? ?????",
        "date": "?????",
        "party": "????/???????",
        "address": "??????",
        "line_item": "??? ???????????",
        "total": "???",
        "gotra": "??????",
        "nakshatra": "????????",
        "rashi": "????",
        "service_date": "??? ?????",
        "cashier": "??????",
        "note": "????????: ??? ???? ???????? 10 ???????? ??????? ????? ??????? ??? ????? ??????????.",
    },
    "hindi": {
        "receipt_title": "????",
        "receipt_number": "???? ??????",
        "date": "??????",
        "party": "????/???????",
        "address": "???",
        "line_item": "???? ?????",
        "total": "???",
        "gotra": "?????",
        "nakshatra": "???????",
        "rashi": "????",
        "service_date": "???? ????",
        "cashier": "??????",
        "note": "???: ????? ???? ??? ?? 10 ???? ???? ??? ?? ?????? ??? ??? ??????? ?????",
    },
}

_ENGLISH_LABELS = {
    "receipt_title": "RECEIPT",
    "receipt_number": "Receipt No",
    "date": "Date",
    "party": "Devotee",
    "address": "Address",
    "line_item": "Seva Details",
    "total": "Total",
    "gotra": "Gotra",
    "nakshatra": "Star",
    "rashi": "Rashi",
    "service_date": "Seva Date",
    "cashier": "Cashier",
}

_SCRIPT_RANGES = {
    "kannada": (0x0C80, 0x0CFF),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "malayalam": (0x0D00, 0x0D7F),
    "hindi": (0x0900, 0x097F),
}

_SCRIPT_FONT_FILES = {
    "kannada": ["NotoSansKannada-Regular.ttf", "NotoSansKannada-Bold.ttf", "Tunga.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "tamil": ["NotoSansTamil-Regular.ttf", "NotoSansTamil-Bold.ttf", "Latha.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "telugu": ["NotoSansTelugu-Regular.ttf", "NotoSansTelugu-Bold.ttf", "Gautami.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "malayalam": ["NotoSansMalayalam-Regular.ttf", "NotoSansMalayalam-Bold.ttf", "Kartika.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "hindi": ["NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "Mangal.ttf", "Nirmala.ttc", "Nirmala.ttf"],
}

_GENERIC_FONT_FILES = ["Nirmala.ttc", "Nirmala.ttf", "NirmalaB.ttf"]
_FONT_SEARCH_DIRS = [
    r"C:\Windows\Fonts",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/opentype/noto",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/app/fonts",
    str(MANDIR_COMPAT_DATA_DIR / "fonts"),
]




# ════════════════════════════════════════════════════════════════════════
# SECTION: AMOUNT TO WORDS (English + Kannada)
# NOTE   : _integer_to_words, _amount_to_words, _integer_to_kannada_words, _amount_to_kannada_words, _amount_words_receipt_line
# ════════════════════════════════════════════════════════════════════════

def _integer_to_words(value: int) -> str:
    if value < 20:
        return _ONES_WORDS[value]
    if value < 100:
        tens = _TENS_WORDS[value // 10]
        remainder = value % 10
        return f"{tens} {_ONES_WORDS[remainder]}".strip() if remainder else tens
    if value < 1000:
        hundreds = f"{_ONES_WORDS[value // 100]} HUNDRED"
        remainder = value % 100
        return f"{hundreds} {_integer_to_words(remainder)}".strip() if remainder else hundreds
    if value < 100000:
        thousands = f"{_integer_to_words(value // 1000)} THOUSAND"
        remainder = value % 1000
        return f"{thousands} {_integer_to_words(remainder)}".strip() if remainder else thousands
    if value < 10000000:
        lakhs = f"{_integer_to_words(value // 100000)} LAKH"
        remainder = value % 100000
        return f"{lakhs} {_integer_to_words(remainder)}".strip() if remainder else lakhs
    crores = f"{_integer_to_words(value // 10000000)} CRORE"
    remainder = value % 10000000
    return f"{crores} {_integer_to_words(remainder)}".strip() if remainder else crores



def _amount_to_words(amount: float) -> str:
    try:
        major = int(round(float(amount or 0)))
    except Exception:
        major = 0
    return f"{_integer_to_words(max(major, 0))} ONLY"


def _integer_to_kannada_words(value: int) -> str:
    if value < 20:
        return _KANNADA_ONES_WORDS[value]
    if value < 100:
        tens_value = (value // 10) * 10
        remainder = value % 10
        tens = _KANNADA_TENS_WORDS[tens_value]
        if remainder:
            stem = _KANNADA_COMPOUND_TENS_STEMS.get(tens_value)
            suffix = _KANNADA_COMPOUND_SUFFIXES.get(remainder)
            if stem and suffix:
                return f"{stem}{suffix}"
        return f"{tens} {_KANNADA_ONES_WORDS[remainder]}".strip() if remainder else tens
    if value < 1000:
        hundreds = f"{_KANNADA_ONES_WORDS[value // 100]} ನೂರು"
        remainder = value % 100
        return f"{hundreds} {_integer_to_kannada_words(remainder)}".strip() if remainder else hundreds
    if value < 100000:
        thousands = f"{_integer_to_kannada_words(value // 1000)} ಸಾವಿರ"
        remainder = value % 1000
        return f"{thousands} {_integer_to_kannada_words(remainder)}".strip() if remainder else thousands
    if value < 10000000:
        lakhs = f"{_integer_to_kannada_words(value // 100000)} ಲಕ್ಷ"
        remainder = value % 100000
        return f"{lakhs} {_integer_to_kannada_words(remainder)}".strip() if remainder else lakhs
    crores = f"{_integer_to_kannada_words(value // 10000000)} ಕೋಟಿ"
    remainder = value % 10000000
    return f"{crores} {_integer_to_kannada_words(remainder)}".strip() if remainder else crores


def _amount_to_kannada_words(amount: float) -> str:
    try:
        major = int(round(float(amount or 0)))
    except Exception:
        major = 0
    return f"ರೂಪಾಯಿ {_integer_to_kannada_words(max(major, 0))} ಮಾತ್ರ"


def _amount_words_receipt_line(amount: float, *, local_language: str | None = None) -> str:
    english = f"Rupees {_amount_to_words(amount).title()}"
    if _normalize_local_language(local_language) == "kannada":
        return f"{_amount_to_kannada_words(amount)} / {english}"
    return f"Received {english}"




# ════════════════════════════════════════════════════════════════════════
# SECTION: RECEIPT TEXT COMPOSITION
# NOTE   : _as_text, _first_non_empty_text, _name_prefix_from_sources, _compose_receipt_party_name, _compose_receipt_address_line, _split_amount, _normalize_local_language, _detect_script
# ════════════════════════════════════════════════════════════════════════

def _as_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback




def _first_non_empty_text(*values: Any) -> str:
    for value in values:
        text = _as_text(value)
        if text:
            return text
    return ""


def _name_prefix_from_sources(*sources: Any) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue
        prefix = _first_non_empty_text(
            source.get("name_prefix"),
            source.get("devotee_prefix"),
            source.get("prefix"),
            source.get("title"),
            source.get("salutation"),
        )
        if prefix:
            return prefix
    return ""


def _compose_receipt_party_name(*sources: Any, fallback: str = "Devotee") -> str:
    name_value = ""
    for source in sources:
        if not isinstance(source, dict):
            continue
        name_value = _first_non_empty_text(
            source.get("devotee_name"),
            source.get("devotee_names"),
            source.get("name"),
            source.get("full_name"),
            source.get("first_name"),
        )
        if name_value:
            break

    if not name_value:
        return fallback

    prefix_value = _name_prefix_from_sources(*sources)
    if not prefix_value:
        return name_value

    normalized_prefix = " ".join(prefix_value.replace(".", " ").split()).lower()
    normalized_name = " ".join(name_value.replace(".", " ").split()).lower()
    if normalized_name.startswith(f"{normalized_prefix} ") or normalized_name == normalized_prefix:
        return name_value
    return f"{prefix_value} {name_value}".strip()


def _compose_receipt_address_line(*sources: Any, fallback: str = "--") -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("devotee_address", "address", "city", "state", "pincode"):
            part = _as_text(source.get(key))
            if not part:
                continue
            normalized = " ".join(part.replace(",", " ").split()).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            parts.append(part)
    return ", ".join(parts) if parts else fallback

def _split_amount(value: Any) -> tuple[str, str]:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    normalized = f"{amount:.2f}"
    major, minor = normalized.split(".", 1)
    return major, minor



def _normalize_local_language(value: Any) -> str | None:
    if value is None:
        return None
    language = str(value).strip().lower()
    language = {
        "kannada": "kannada",
        "kan": "kannada",
        "tamil": "tamil",
        "tam": "tamil",
        "telugu": "telugu",
        "tel": "telugu",
        "malayalam": "malayalam",
        "mal": "malayalam",
        "hindi": "hindi",
        "hin": "hindi",
    }.get(language, language)
    return language if language in _SUPPORTED_LOCAL_LANGUAGES else None



def _detect_script(text: str) -> str | None:
    for char in text:
        code = ord(char)
        for script_name, (start, end) in _SCRIPT_RANGES.items():
            if start <= code <= end:
                return script_name
    return None




# ════════════════════════════════════════════════════════════════════════
# SECTION: FONT RESOLUTION + REPORTLAB STYLES
# NOTE   : _font_candidate_paths, _resolve_font_name, _receipt_paragraph, _format_receipt_date, _format_payment_mode_for_receipt, _format_payment_mode_local, _receipt_payment_line, _compose_receipt_line_description, _extract_seva_line_items
# ════════════════════════════════════════════════════════════════════════

def _font_candidate_paths(script_hint: str | None) -> list[str]:
    candidates: list[str] = []
    script_files = _SCRIPT_FONT_FILES.get(script_hint or "", [])
    for file_name in script_files:
        for search_dir in _FONT_SEARCH_DIRS:
            candidates.append(os.path.join(search_dir, file_name))
    for file_name in _GENERIC_FONT_FILES:
        for search_dir in _FONT_SEARCH_DIRS:
            candidates.append(os.path.join(search_dir, file_name))
    seen: set[str] = set()
    deduped: list[str] = []
    for p in candidates:
        normalized = os.path.normpath(p)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped



def _resolve_font_name(script_hint: str | None) -> str:
    for idx, font_path in enumerate(_font_candidate_paths(script_hint)):
        if not os.path.exists(font_path):
            continue
        font_name = f"MandirReceipt_{script_hint or 'generic'}_{idx}"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            except Exception:
                continue
        return font_name
    return "Helvetica"



def _receipt_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    raw_text = _as_text(text, "-")
    pieces: list[str] = []
    buffer: list[str] = []
    buffer_is_latin: bool | None = None

    def flush_buffer() -> None:
        nonlocal buffer, buffer_is_latin
        if not buffer:
            return
        escaped_text = escape("".join(buffer))
        if buffer_is_latin and style.fontName != "Helvetica":
            pieces.append(f'<font name="Helvetica">{escaped_text}</font>')
        elif not buffer_is_latin and style.fontName != "Helvetica":
            pieces.append(f'<font name="{style.fontName}">{escaped_text}</font>')
        else:
            pieces.append(escaped_text)
        buffer = []
        buffer_is_latin = None

    for char in raw_text:
        if char == "\n":
            flush_buffer()
            pieces.append("<br/>")
            continue

        is_latin = ord(char) < 128
        if buffer_is_latin is None:
            buffer_is_latin = is_latin
        elif buffer_is_latin != is_latin:
            flush_buffer()
            buffer_is_latin = is_latin
        buffer.append(char)

    flush_buffer()
    return Paragraph("".join(pieces), style)



def _format_receipt_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d/%m/%Y")
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d/%m/%Y")
    except Exception:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).strftime("%d/%m/%Y")
            except Exception:
                continue
    return raw



def _format_payment_mode_for_receipt(value: Any) -> str:
    mode = _as_text(value, "Cash")
    lowered = mode.lower()
    if "cash" in lowered:
        return "Cash"
    if "upi" in lowered:
        return mode
    if any(token in lowered for token in ["upi", "bank", "cheque", "check", "online", "transfer", "neft", "rtgs", "card"]):
        return f"Bank ({mode})"
    return mode


def _format_payment_mode_local_for_receipt(value: Any, *, local_language: str | None = None) -> str:
    if _normalize_local_language(local_language) != "kannada":
        return _format_payment_mode_for_receipt(value)
    mode = _as_text(value, "Cash")
    lowered = mode.lower()
    if "cash" in lowered:
        return "ನಗದು"
    if "cheque" in lowered or "check" in lowered:
        return "ಚೆಕ್"
    if "upi" in lowered:
        return "ಯುಪಿಐ"
    if any(token in lowered for token in ["online", "bank", "transfer", "neft", "rtgs", "card"]):
        return "ಆನ್‌ಲೈನ್ / ಬ್ಯಾಂಕ್"
    return mode


def _receipt_payment_line(
    *,
    payment_mode: str,
    local_language: str | None = None,
    purpose: str = "donation",
) -> str:
    if _normalize_local_language(local_language) != "kannada":
        if purpose == "seva":
            return f"Received with thanks for the below mentioned seva by {payment_mode}."
        return f"Received with thanks for donation by {payment_mode}."
    local_mode = _format_payment_mode_local_for_receipt(payment_mode, local_language=local_language)
    if purpose == "seva":
        return f"ಈ ಕೆಳಗೆ ಕಾಣಿಸಿದ ಸೇವೆಯ ಸಲುವಾಗಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ಪಾವತಿ ವಿಧಾನ: {local_mode} / Received with thanks for the below mentioned seva by {payment_mode}."
    return f"ಧನ್ಯವಾದಗಳೊಂದಿಗೆ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ಪಾವತಿ ವಿಧಾನ: {local_mode} / Received by {payment_mode}."



def _compose_receipt_line_description(name: Any, local_name: Any = None, *, use_local_labels: bool = False) -> str:
    english = _as_text(name, "Seva").strip() or "Seva"
    local = _as_text(local_name, "").strip()
    if use_local_labels and local and local != english:
        return f"{local} / {english}"
    return english


def _extract_seva_line_items(
    booking: dict[str, Any],
    *,
    fallback_name: str,
    fallback_amount: float,
    use_local_labels: bool = False,
) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    candidate_lists = [booking.get("line_items"), booking.get("seva_items"), booking.get("sevas"), booking.get("booked_sevas")]
    for candidate in candidate_lists:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if not isinstance(item, dict):
                continue
            name = _as_text(item.get("description") or item.get("seva_name") or item.get("name"), "")
            local_name = _as_text(
                item.get("description_local")
                or item.get("seva_name_local")
                or item.get("name_kannada")
                or item.get("local_name"),
                "",
            )
            amount = _safe_float(item.get("amount") or item.get("amount_paid") or item.get("fee"), 0.0)
            if not name and amount <= 0:
                continue
            line_items.append({
                "description": _compose_receipt_line_description(name or fallback_name, local_name, use_local_labels=use_local_labels),
                "amount": amount or fallback_amount,
            })

    if not line_items:
        csv_names = _as_text(booking.get("seva_names"))
        if csv_names:
            names = [part.strip() for part in csv_names.split(",") if part.strip()]
            if names:
                split_amount = fallback_amount / len(names) if fallback_amount > 0 else 0.0
                for name in names:
                    line_items.append({"description": name, "amount": split_amount})

    if not line_items:
        line_items = [{"description": fallback_name, "amount": fallback_amount}]
    return line_items




# ════════════════════════════════════════════════════════════════════════
# SECTION: TEMPLE RECEIPT PROFILE
# NOTE   : _build_temple_receipt_profile, _resolve_temple_receipt_profile, _bilingual_label
# ════════════════════════════════════════════════════════════════════════

def _build_temple_receipt_profile(temple_doc: dict[str, Any] | None) -> dict[str, str | None]:
    temple_doc = temple_doc if isinstance(temple_doc, dict) else {}
    temple_name = _as_text(temple_doc.get("temple_name") or temple_doc.get("name"), "Temple")
    trust_name = _as_text(temple_doc.get("trust_name"), temple_name)
    address = _as_text(temple_doc.get("address") or temple_doc.get("temple_address"))
    city = _as_text(temple_doc.get("city") or temple_doc.get("city_name"))
    state = _as_text(temple_doc.get("state") or temple_doc.get("state_name"))
    pincode = _as_text(temple_doc.get("pincode"))
    email = _as_text(temple_doc.get("email") or temple_doc.get("temple_email"))
    phone = _as_text(temple_doc.get("phone") or temple_doc.get("contact_number") or temple_doc.get("temple_contact_number"))
    website = _as_text(temple_doc.get("website") or temple_doc.get("temple_website"))
    header_local_line = _as_text(temple_doc.get("header_local_line"))
    local_language = _normalize_local_language(
        temple_doc.get("receipt_local_language")
        or temple_doc.get("local_language")
        or temple_doc.get("primary_language")
        or temple_doc.get("language")
    )
    if local_language == "kannada" and temple_name == "Temple":
        temple_name = "ದೇವಸ್ಥಾನ"
        if trust_name == "Temple":
            trust_name = temple_name
    return {
        "trust_name": trust_name,
        "temple_name": temple_name,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
        "email": email,
        "phone": phone,
        "website": website,
        "header_local_line": header_local_line,
        "local_language": local_language,
    }



async def _resolve_temple_receipt_profile(
    *,
    tenant_id: str,
    app_key: str,
    lang: str | None = None,
) -> dict[str, str | None]:
    temple_doc: dict[str, Any] = {}
    try:
        temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
        if not temple_doc:
            temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id}) or {}
    except Exception as exc:
        logger.warning("Mandir receipt temple profile lookup failed for tenant=%s app=%s: %s", tenant_id, app_key, exc)

    lang_doc: dict[str, Any] = {}
    try:
        lang_doc = await get_collection("mandir_panchang_settings").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    except Exception as exc:
        logger.warning("Mandir receipt language lookup failed for tenant=%s app=%s: %s", tenant_id, app_key, exc)

    temple_profile = _build_temple_receipt_profile(temple_doc)
    selected_language = _normalize_local_language(
        lang
        or lang_doc.get("receipt_local_language")
        or temple_doc.get("receipt_local_language")
        or lang_doc.get("local_language")
        or temple_doc.get("local_language")
        or lang_doc.get("primary_language")
        or temple_doc.get("primary_language")
        or temple_profile.get("local_language")
        or "kannada"
    )
    temple_profile["local_language"] = selected_language or "kannada"
    return temple_profile


def _bilingual_label(local_label: str, english_label: str, use_local_labels: bool) -> str:
    if use_local_labels and local_label:
        return f"{local_label} / {english_label}"
    return english_label




# ════════════════════════════════════════════════════════════════════════
# SECTION: WEASYPRINT + BILINGUAL LABEL HELPERS
# NOTE   : _default_labels, _receipt_html_escape, _receipt_html_mixed, _receipt_weasy_font_css (entry)
# ════════════════════════════════════════════════════════════════════════

def _default_labels(local_language: str | None, use_local_labels: bool) -> dict[str, str]:
    local_labels = _LOCAL_LABELS.get(local_language or "", {})
    return {
        "receipt_title": _bilingual_label(local_labels.get("receipt_title", ""), _ENGLISH_LABELS["receipt_title"], use_local_labels),
        "receipt_number": _bilingual_label(local_labels.get("receipt_number", ""), _ENGLISH_LABELS["receipt_number"], use_local_labels),
        "date": _bilingual_label(local_labels.get("date", ""), _ENGLISH_LABELS["date"], use_local_labels),
        "party": _bilingual_label(local_labels.get("party", ""), _ENGLISH_LABELS["party"], use_local_labels),
        "address": _bilingual_label(local_labels.get("address", ""), _ENGLISH_LABELS["address"], use_local_labels),
        "line_item": _bilingual_label(local_labels.get("line_item", ""), _ENGLISH_LABELS["line_item"], use_local_labels),
        "total": _bilingual_label(local_labels.get("total", ""), _ENGLISH_LABELS["total"], use_local_labels),
        "gotra": _bilingual_label(local_labels.get("gotra", ""), _ENGLISH_LABELS["gotra"], use_local_labels),
        "nakshatra": _bilingual_label(local_labels.get("nakshatra", ""), _ENGLISH_LABELS["nakshatra"], use_local_labels),
        "rashi": _bilingual_label(local_labels.get("rashi", ""), _ENGLISH_LABELS["rashi"], use_local_labels),
        "service_date": _bilingual_label(local_labels.get("service_date", ""), _ENGLISH_LABELS["service_date"], use_local_labels),
        "cashier": _bilingual_label(local_labels.get("cashier", ""), _ENGLISH_LABELS["cashier"], use_local_labels),
        "note_local": local_labels.get("note", ""),
    }


def _receipt_html_escape(value: Any, fallback: str = "-") -> str:
    return escape(_as_text(value, fallback), {'"': "&quot;", "'": "&#x27;"})


def _receipt_html_mixed(value: Any, fallback: str = "-") -> str:
    raw_text = _as_text(value, fallback)
    pieces: list[str] = []
    buffer: list[str] = []
    buffer_is_latin: bool | None = None

    def flush_buffer() -> None:
        nonlocal buffer, buffer_is_latin
        if not buffer:
            return
        escaped_text = escape("".join(buffer), {'"': "&quot;", "'": "&#x27;"})
        if buffer_is_latin:
            pieces.append(f'<span class="latin">{escaped_text}</span>')
        else:
            pieces.append(escaped_text)
        buffer = []
        buffer_is_latin = None

    for char in raw_text:
        if char == "\n":
            flush_buffer()
            pieces.append("<br/>")
            continue

        is_latin = ord(char) < 128
        if buffer_is_latin is None:
            buffer_is_latin = is_latin
        elif buffer_is_latin != is_latin:
            flush_buffer()
            buffer_is_latin = is_latin
        buffer.append(char)

    flush_buffer()
    return "".join(pieces)


def _receipt_weasy_font_css(local_language: str | None) -> str:
    candidates = []
    for candidate in _font_candidate_paths(local_language):
        path = Path(candidate)
        if path.exists() and path.suffix.lower() in {".ttf", ".otf", ".ttc"}:
            candidates.append(path)
    nirmala = Path(r"C:\Windows\Fonts\Nirmala.ttc")
    if nirmala.exists():
        candidates.append(nirmala)

    if not candidates:
        return ""

    font_faces = []
    for index, path in enumerate(candidates[:3]):
        font_faces.append(
            "@font-face {"
            f"font-family: 'MandirReceiptLocal{index}';"
            f"src: url('{path.resolve().as_uri()}');"
            "}"
        )
    return "\n".join(font_faces)



# ════════════════════════════════════════════════════════════════════════
# SECTION: WEASYPRINT RECEIPT PDF BUILDER
# NOTE   : _build_receipt_pdf_bytes_weasy, _receipt_weasy_font_css — HTML-to-PDF receipt via WeasyPrint
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes_weasy(
    payload: dict[str, Any],
    *,
    local_language: str,
    labels: dict[str, str],
    local_labels: dict[str, str],
    use_local_labels: bool,
) -> bytes:
    if HTML is None:
        raise RuntimeError("weasyprint is not available")

    line_items = payload.get("line_items") or []
    if not line_items:
        line_items = [{"description": "-", "amount": payload.get("total_amount", 0)}]

    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    def bilingual(local_key: str, english_value: Any, fallback_key: str) -> str:
        english = _as_text(english_value)
        if not english:
            return labels[fallback_key]
        local = _as_text(payload.get(f"{local_key}_local")) or local_labels.get(local_key, "")
        return _bilingual_label(local, english, use_local_labels)

    receipt_title = bilingual("receipt_title", payload.get("receipt_title"), "receipt_title")
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label = labels["party"] if payload.get("party_label") is None else _as_text(payload.get("party_label"), "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header = bilingual("line_item", payload.get("line_item_header"), "line_item")
    total_label = _as_text(payload.get("total_label")) or labels["total"]
    gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
    star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
    rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
    service_date_label = bilingual("service_date", payload.get("service_date_label"), "service_date")

    header_local_line = _as_text(payload.get("header_local_line"))
    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""
    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )

    header_parts = []
    if header_local_line:
        header_parts.append(f"<div class='local-header'>{_receipt_html_mixed(header_local_line)}</div>")
    header_parts.append(f"<div class='trust'>{_receipt_html_mixed(primary_header)}</div>")
    if secondary_header:
        header_parts.append(f"<div class='temple'>{_receipt_html_mixed(secondary_header)}</div>")
    if address_line:
        header_parts.append(f"<div>{_receipt_html_mixed(address_line)}</div>")
    if _as_text(payload.get("website")):
        header_parts.append(f"<div>{_receipt_html_mixed(payload.get('website'))}</div>")
    if _as_text(payload.get("email")):
        header_parts.append(f"<div>{_receipt_html_mixed(payload.get('email'))}</div>")
    if _as_text(payload.get("phone")):
        header_parts.append(f"<div>{_receipt_html_mixed('Phone')}: {_receipt_html_mixed(payload.get('phone'))}</div>")

    rows_html = []
    for item in line_items:
        major, minor = _split_amount(item.get("amount"))
        rows_html.append(
            "<tr>"
            f"<td class='desc'>{_receipt_html_mixed(item.get('description'))}</td>"
            f"<td class='amt amt-major'>{_receipt_html_mixed(major)}</td>"
            f"<td class='amt amt-minor'>{_receipt_html_mixed(minor)}</td>"
            "</tr>"
        )

    total_major, total_minor = _split_amount(total_amount)
    rows_html.append(
        "<tr>"
        f"<td class='desc total'>{_receipt_html_mixed(total_label)}</td>"
        f"<td class='amt amt-major total'>{_receipt_html_mixed(total_major)}</td>"
        f"<td class='amt amt-minor total'>{_receipt_html_mixed(total_minor)}</td>"
        "</tr>"
    )

    include_note_row = bool(payload.get("include_note_row", True))
    note_lines = [
        _as_text(payload.get("note_local"), labels.get("note_local", "")) if use_local_labels and include_note_row else "",
        _as_text(payload.get("note_english"), "") if include_note_row else "",
    ]
    note_html = "<br/>".join(_receipt_html_mixed(line) for line in note_lines if line)

    astro_html = ""
    if bool(payload.get("include_astro_row", True)):
        astro_html = (
            "<div class='meta-row'>"
            f"{_receipt_html_mixed(gotra_label)}: {_receipt_html_mixed(payload.get('gotra'), '--')}"
            f"&nbsp;&nbsp; {_receipt_html_mixed(star_label)}: {_receipt_html_mixed(payload.get('nakshatra'), '--')}"
            f"&nbsp;&nbsp; {_receipt_html_mixed(rashi_label)}: {_receipt_html_mixed(payload.get('rashi'), '--')}"
            "</div>"
        )

    service_html = ""
    if bool(payload.get("include_service_row", True)):
        service_html = (
            "<div class='meta-row'>"
            f"{_receipt_html_mixed(service_date_label)}: {_receipt_html_mixed(payload.get('service_date'), '--')}"
            "</div>"
        )

    system_line = payload.get("system_generated_line")
    if system_line is None:
        system_line = "This is a system generated receipt and does not require any signature."

    css = f"""
    {_receipt_weasy_font_css(local_language)}
    @page {{ size: A5; margin: 8mm; }}
    body {{
        font-family: 'MandirReceiptLocal0', 'MandirReceiptLocal1', 'Nirmala UI', Arial, sans-serif;
        font-size: 9px;
        line-height: 1.35;
        color: #111;
        font-variant-ligatures: normal;
        font-feature-settings: "kern" 1, "liga" 1, "clig" 1;
        text-rendering: optimizeLegibility;
    }}
    .header {{ text-align: center; margin-bottom: 5px; }}
    .trust {{ font-weight: 700; font-size: 12px; }}
    .temple {{ font-size: 9px; }}
    .local-header {{ font-weight: 700; font-size: 11px; }}
    table.receipt {{ width: 100%; border-collapse: collapse; border: 1px solid #888; }}
    table.receipt td {{ border: 1px solid #aaa; padding: 4px 6px; vertical-align: middle; }}
    .title {{ text-align: center; font-weight: 700; background: #f2f2f2; font-size: 10px; }}
    .right {{ text-align: right; }}
    .date-cell {{ text-align: right; white-space: nowrap; }}
    .center {{ text-align: center; }}
    .desc {{ width: 78%; }}
    .amt-major {{ width: 14%; text-align: right; }}
    .amt-minor {{ width: 8%; text-align: center; }}
    .total {{ font-weight: 700; }}
    .note {{ text-align: center; background: #f8f8f8; }}
    .meta-row {{ margin-top: 5px; font-size: 8px; }}
    .powered {{ text-align: right; color: #555; font-size: 7px; margin-top: 4px; }}
    .latin {{ font-family: Arial, 'DejaVu Sans', sans-serif; }}
    """
    html_lang = _HTML_LANG_BY_LOCAL_LANGUAGE.get(local_language, local_language)
    html = f"""
    <!doctype html>
    <html lang="{_receipt_html_escape(html_lang)}">
    <head><meta charset="utf-8"/><style>{css}</style></head>
    <body>
      <div class="header">{''.join(header_parts)}</div>
      <table class="receipt">
        <tr><td class="title" colspan="3">{_receipt_html_mixed(receipt_title)}</td></tr>
        <tr>
          <td>{_receipt_html_mixed(receipt_no_label)}: {_receipt_html_mixed(payload.get('receipt_number'), '-')}</td>
          <td class="date-cell" colspan="2">{_receipt_html_mixed(date_label)}: {_receipt_html_mixed(payload.get('receipt_date'), '-')}</td>
        </tr>
        <tr><td colspan="3">{_receipt_html_mixed(party_label)}: {_receipt_html_mixed(payload.get('party_name'), '-')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(address_label)}: {_receipt_html_mixed(payload.get('address_value'), '--')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(payload.get('amount_words_line'), 'Received with thanks')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(payload.get('payment_line'), 'Received with thanks.')}</td></tr>
        <tr>
          <td class="desc total">{_receipt_html_mixed(line_item_header)}</td>
          <td class="center total amt-major">Rs</td>
          <td class="center total amt-minor"></td>
        </tr>
        {''.join(rows_html)}
        {f'<tr><td class="note" colspan="3">{note_html or "-"}</td></tr>' if include_note_row else ''}
      </table>
      {astro_html}
      {service_html}
      <div class="center">{_receipt_html_mixed(system_line, '')}</div>
      <div class="powered">{_receipt_html_mixed(payload.get('powered_by_line'), '')}</div>
    </body>
    </html>
    """
    return HTML(string=html, base_url=str(Path.cwd().resolve())).write_pdf()



# ════════════════════════════════════════════════════════════════════════
# SECTION: PILLOW FONT + TEXT RENDERING HELPERS
# NOTE   : _load_receipt_pillow_font, _load_receipt_latin_pillow_font, _receipt_text_runs, _draw_receipt_text, _receipt_text_width, _wrap_receipt_text, _draw_receipt_cell_text
# ════════════════════════════════════════════════════════════════════════

def _load_receipt_pillow_font(script_hint: str | None, size_px: int) -> Any:
    if ImageFont is None:
        raise RuntimeError("Pillow font support is not available")
    for font_path in _font_candidate_paths(script_hint):
        path = Path(font_path)
        if not path.exists() or path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
            continue
        try:
            return ImageFont.truetype(str(path), size_px)
        except Exception:
            continue
    return ImageFont.load_default()


def _load_receipt_latin_pillow_font(size_px: int) -> Any:
    if ImageFont is None:
        raise RuntimeError("Pillow font support is not available")
    for candidate in [
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if not Path(candidate).exists():
            continue
        try:
            return ImageFont.truetype(candidate, size_px)
        except Exception:
            continue
    return ImageFont.load_default()


def _receipt_text_runs(text: str) -> list[tuple[str, bool]]:
    runs: list[tuple[str, bool]] = []
    current: list[str] = []
    current_is_latin: bool | None = None
    for char in text:
        is_latin = ord(char) < 128
        if current_is_latin is None:
            current_is_latin = is_latin
        elif current_is_latin != is_latin:
            runs.append(("".join(current), current_is_latin))
            current = []
            current_is_latin = is_latin
        current.append(char)
    if current:
        runs.append(("".join(current), bool(current_is_latin)))
    return runs


def _draw_receipt_text(
    draw: Any,
    xy: tuple[int, int],
    text: str,
    font: Any,
    *,
    latin_font: Any | None = None,
    fill: str = "#111111",
    anchor: str | None = None,
) -> None:
    if latin_font is not None and text and anchor in {"la", "ma", "ra"}:
        width = _receipt_text_width(draw, text, font, latin_font=latin_font)
        x, y = xy
        if anchor == "ma":
            x -= width // 2
        elif anchor == "ra":
            x -= width
        for run, is_latin in _receipt_text_runs(text):
            run_font = latin_font if is_latin else font
            draw.text((x, y), run, font=run_font, fill=fill)
            x += _receipt_text_width(draw, run, run_font)
        return
    kwargs = {"font": font, "fill": fill}
    if anchor:
        kwargs["anchor"] = anchor
    draw.text(xy, text, **kwargs)


def _receipt_text_width(draw: Any, text: str, font: Any, *, latin_font: Any | None = None) -> int:
    if latin_font is not None:
        return sum(
            _receipt_text_width(draw, run, latin_font if is_latin else font)
            for run, is_latin in _receipt_text_runs(text)
        )
    try:
        return int(draw.textlength(text, font=font))
    except Exception:
        bbox = draw.textbbox((0, 0), text, font=font)
        return int(bbox[2] - bbox[0])


def _wrap_receipt_text(draw: Any, text: str, font: Any, max_width: int, *, latin_font: Any | None = None) -> list[str]:
    words = _as_text(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _receipt_text_width(draw, candidate, font, latin_font=latin_font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def _draw_receipt_cell_text(
    draw: Any,
    rect: tuple[int, int, int, int],
    text: str,
    font: Any,
    *,
    latin_font: Any | None = None,
    align: str = "left",
    bold_font: Any | None = None,
    max_lines: int = 2,
) -> None:
    x1, y1, x2, y2 = rect
    pad = 10
    selected_font = bold_font or font
    selected_latin_font = latin_font
    lines = _wrap_receipt_text(
        draw,
        _as_text(text, "-"),
        selected_font,
        max(10, x2 - x1 - (pad * 2)),
        latin_font=selected_latin_font,
    )[:max_lines]
    line_height = int(selected_font.size * 1.25) if hasattr(selected_font, "size") else 18
    total_height = line_height * len(lines)
    y = y1 + max(0, ((y2 - y1) - total_height) // 2)
    for line in lines:
        if align == "right":
            x = x2 - pad
            anchor = "ra"
        elif align == "center":
            x = (x1 + x2) // 2
            anchor = "ma"
        else:
            x = x1 + pad
            anchor = "la"
        _draw_receipt_text(draw, (x, y), line, selected_font, latin_font=selected_latin_font, anchor=anchor)
        y += line_height



# ════════════════════════════════════════════════════════════════════════
# SECTION: PILLOW IMAGE RECEIPT BUILDER
# NOTE   : _build_receipt_pdf_bytes_pillow — renders receipt as PNG wrapped in PDF using Pillow
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes_pillow(
    payload: dict[str, Any],
    *,
    local_language: str,
    labels: dict[str, str],
    local_labels: dict[str, str],
    use_local_labels: bool,
) -> bytes:
    if PILImage is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is not available")
    if pil_features is not None and not pil_features.check("raqm"):
        raise RuntimeError("Pillow was built without RAQM/HarfBuzz shaping")

    scale = 3
    page_w_pt, page_h_pt = A5
    page_w = int(page_w_pt * scale)
    page_h = int(page_h_pt * scale)
    image = PILImage.new("RGB", (page_w, page_h), "white")
    draw = ImageDraw.Draw(image)

    font_small = _load_receipt_pillow_font(local_language, 24)
    font_body = _load_receipt_pillow_font(local_language, 28)
    font_header = _load_receipt_pillow_font(local_language, 34)
    font_title = _load_receipt_pillow_font(local_language, 30)
    font_footer = _load_receipt_pillow_font(local_language, 20)
    latin_small = _load_receipt_latin_pillow_font(24)
    latin_body = _load_receipt_latin_pillow_font(28)
    latin_header = _load_receipt_latin_pillow_font(34)
    latin_title = _load_receipt_latin_pillow_font(30)
    latin_footer = _load_receipt_latin_pillow_font(20)

    def p(value: float) -> int:
        return int(value * scale)

    def line(x1: int, y1: int, x2: int, y2: int, width: int = 1) -> None:
        draw.line((x1, y1, x2, y2), fill="#777777", width=max(1, width * scale))

    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""
    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )

    margin = p(10)
    left = margin
    right = page_w - margin
    outer_top = margin
    outer_bottom = page_h - p(52)
    line(left, outer_top, right, outer_top)
    line(left, outer_top, left, outer_bottom)
    line(right, outer_top, right, outer_bottom)
    line(left, outer_bottom, right, outer_bottom)

    header_top = outer_top
    header_bottom = p(100)
    title_bottom = p(120)
    line(left, header_bottom, right, header_bottom)
    line(left, title_bottom, right, title_bottom)

    logo_source = _as_text(payload.get("logo"))
    logo_box = (left + p(4), header_top + p(10), left + p(68), header_bottom - p(4))
    if logo_source and Path(logo_source).exists():
        try:
            logo = PILImage.open(logo_source).convert("RGB")
            logo.thumbnail((logo_box[2] - logo_box[0], logo_box[3] - logo_box[1]))
            logo_x = logo_box[0] + ((logo_box[2] - logo_box[0]) - logo.width) // 2
            logo_y = logo_box[1] + ((logo_box[3] - logo_box[1]) - logo.height) // 2
            image.paste(logo, (logo_x, logo_y))
        except Exception:
            logo_source = ""

    header_left = logo_box[2] + p(8) if logo_source and Path(logo_source).exists() else left
    header_center_x = (header_left + right) // 2
    y = header_top + p(14)
    header_rows = [
        (_as_text(payload.get("header_local_line")), font_title, latin_title),
        (primary_header, font_header, latin_header),
        (address_line, font_small, latin_small),
        (_as_text(payload.get("website")), font_footer, latin_footer),
        (_as_text(payload.get("email")), font_footer, latin_footer),
        (f"Phone : {_as_text(payload.get('phone'))}" if _as_text(payload.get("phone")) else "", font_footer, latin_footer),
    ]
    for text, font, latin_font in header_rows:
        if not text:
            continue
        _draw_receipt_text(draw, (header_center_x, y), text, font, latin_font=latin_font, anchor="ma")
        y += int(font.size * 1.05)

    top = title_bottom
    col1 = left + int((right - left) * 0.73)
    col2 = left + int((right - left) * 0.91)

    line_items = payload.get("line_items") or [{"description": "-", "amount": payload.get("total_amount", 0)}]
    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    def bilingual(local_key: str, english_value: Any, fallback_key: str) -> str:
        english = _as_text(english_value)
        if not english:
            return labels[fallback_key]
        local = _as_text(payload.get(f"{local_key}_local")) or local_labels.get(local_key, "")
        return _bilingual_label(local, english, use_local_labels)

    receipt_title = bilingual("receipt_title", payload.get("receipt_title"), "receipt_title")
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label = labels["party"] if payload.get("party_label") is None else _as_text(payload.get("party_label"), "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header = bilingual("line_item", payload.get("line_item_header"), "line_item")
    total_label = _as_text(payload.get("total_label")) or labels["total"]

    details_top = top
    meta_top = p(417) if bool(payload.get("include_astro_row", True)) else p(395)
    note_top = p(495) if bool(payload.get("include_astro_row", True)) else p(462)
    bottom = outer_bottom
    line(left, details_top, right, details_top)
    line(left, meta_top, right, meta_top)
    if bool(payload.get("include_astro_row", True)):
        line(left, note_top, right, note_top)

    r1 = details_top + p(30)
    r2 = r1 + p(22)
    r3 = r2 + p(22)
    r4 = r3 + p(30)
    r5 = r4 + p(38)
    item_header_top = r5
    item_header_bottom = item_header_top + p(24)
    total_top = meta_top - p(22)

    for y_line in [r1, r2, r3, r4, r5, item_header_bottom, total_top]:
        line(left, y_line, right, y_line)
    line(col1, item_header_top, col1, meta_top)
    line(col2, item_header_bottom, col2, meta_top)

    _draw_receipt_cell_text(draw, (left, header_bottom, right, title_bottom), receipt_title, font_title, latin_font=latin_title, align="center")
    _draw_receipt_cell_text(
        draw,
        (left, details_top, col1, r1),
        f"{receipt_no_label}: {_as_text(payload.get('receipt_number'), '-')}",
        font_body,
        latin_font=latin_body,
    )
    _draw_receipt_cell_text(
        draw,
        (col1, details_top, right, r1),
        f"{date_label}: {_as_text(payload.get('receipt_date'), '-')}",
        font_body,
        latin_font=latin_body,
        align="right",
    )
    _draw_receipt_cell_text(draw, (left, r1, right, r2), f"{party_label}: {_as_text(payload.get('party_name'), '-')}", font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r2, right, r3), f"{address_label}: {_as_text(payload.get('address_value'), '--')}", font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r3, right, r4), _as_text(payload.get("amount_words_line"), "-"), font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r4, right, r5), _as_text(payload.get("payment_line"), "-"), font_body, latin_font=latin_body, max_lines=2)
    _draw_receipt_cell_text(draw, (left, item_header_top, col1, item_header_bottom), line_item_header, font_body, latin_font=latin_body, align="center")
    _draw_receipt_cell_text(draw, (col1, item_header_top, right, item_header_bottom), "ರೂ Rs", font_body, latin_font=latin_body, align="center")

    item_y = item_header_bottom
    item_height = max(p(24), (total_top - item_header_bottom) // max(1, len(line_items)))
    for item in line_items:
        major, minor = _split_amount(item.get("amount"))
        _draw_receipt_cell_text(draw, (left, item_y, col1, min(item_y + item_height, total_top)), _as_text(item.get("description"), "-"), font_body, latin_font=latin_body)
        _draw_receipt_cell_text(draw, (col1, item_y, col2, min(item_y + item_height, total_top)), major, font_body, latin_font=latin_body, align="right")
        _draw_receipt_cell_text(draw, (col2, item_y, right, min(item_y + item_height, total_top)), minor, font_body, latin_font=latin_body, align="center")
        item_y += item_height

    total_major, total_minor = _split_amount(total_amount)
    _draw_receipt_cell_text(draw, (left, total_top, col1, meta_top), total_label, font_body, latin_font=latin_body, align="right")
    _draw_receipt_cell_text(draw, (col1, total_top, col2, meta_top), total_major, font_body, latin_font=latin_body, align="right")
    _draw_receipt_cell_text(draw, (col2, total_top, right, meta_top), total_minor, font_body, latin_font=latin_body, align="center")

    if bool(payload.get("include_astro_row", True)):
        meta_mid = meta_top + p(38)
        gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
        star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
        rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
        service_date_label = bilingual("service_date", payload.get("service_date_label"), "service_date")
        meta_width = (right - left) // 3
        for idx, (label, value) in enumerate([
            (gotra_label, payload.get("gotra")),
            (star_label, payload.get("nakshatra")),
            (rashi_label, payload.get("rashi")),
        ]):
            x1 = left + (meta_width * idx)
            x2 = right if idx == 2 else left + (meta_width * (idx + 1))
            _draw_receipt_cell_text(draw, (x1, meta_top, x2, meta_mid), f"{label}: {_as_text(value, '--')}", font_small, latin_font=latin_small, max_lines=2)
        _draw_receipt_cell_text(
            draw,
            (left, meta_mid, left + p(150), note_top),
            f"{service_date_label}: {_as_text(payload.get('service_date'), '--')}",
            font_small,
            latin_font=latin_small,
            max_lines=2,
        )
        _draw_receipt_cell_text(draw, (right - p(170), meta_mid, right, note_top), labels["cashier"], font_small, latin_font=latin_small, align="center")

    include_note_row = bool(payload.get("include_note_row", True))
    note_lines = [
        _as_text(payload.get("note_local"), labels.get("note_local", "")) if use_local_labels and include_note_row else "",
        _as_text(payload.get("note_english"), "") if include_note_row else "",
    ]
    note_text = "\n".join(line for line in note_lines if line)
    if include_note_row:
        note_rect = (left, note_top if bool(payload.get("include_astro_row", True)) else meta_top, right, bottom)
        _draw_receipt_cell_text(draw, note_rect, note_text, font_small, latin_font=latin_small, align="center", max_lines=4)
    system_line_raw = payload.get("system_generated_line")
    if system_line_raw is None:
        system_line = "This is a system generated receipt and does not require any signature."
    else:
        system_line = str(system_line_raw).strip()
    _draw_receipt_text(draw, (page_w // 2, outer_bottom + p(8)), system_line, font_footer, latin_font=latin_footer, anchor="ma")
    _draw_receipt_text(draw, (right, page_h - p(22)), _as_text(payload.get("powered_by_line"), ""), font_footer, latin_font=latin_footer, anchor="ra", fill="#333333")

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    pdf_buffer = BytesIO()
    canvas = pdf_canvas.Canvas(pdf_buffer, pagesize=A5)
    canvas.drawImage(ImageReader(image_buffer), 0, 0, width=page_w_pt, height=page_h_pt)
    try:
        hidden_font = _resolve_font_name(local_language)
        canvas.setFont(hidden_font, 1)
        canvas.setFillColor(colors.white)
        canvas.drawString(1, 1, receipt_title)
        canvas.drawString(1, 2, _as_text(payload.get("amount_words_line"), ""))
    except Exception:
        pass
    canvas.showPage()
    canvas.save()
    return pdf_buffer.getvalue()




# ════════════════════════════════════════════════════════════════════════
# SECTION: RECEIPT PDF ORCHESTRATOR
# NOTE   : _build_receipt_pdf_bytes — picks WeasyPrint → Pillow → ReportLab strategy
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes(payload: dict[str, Any]) -> bytes:
    local_language = _normalize_local_language(payload.get("local_language"))
    script_hint = _detect_script(_as_text(payload.get("header_local_line"))) or local_language
    font_name = _resolve_font_name(script_hint)
    has_local_font = font_name != "Helvetica"

    requested_local_labels = payload.get("use_local_labels")
    if requested_local_labels is None:
        requested_local_labels = True
    use_local_labels = bool(requested_local_labels) and has_local_font and local_language in _SUPPORTED_LOCAL_LANGUAGES
    labels = _default_labels(local_language, use_local_labels)
    local_labels = _LOCAL_LABELS.get(local_language or "", {})

    if use_local_labels and local_language:
        try:
            return _build_receipt_pdf_bytes_weasy(
                payload,
                local_language=local_language,
                labels=labels,
                local_labels=local_labels,
                use_local_labels=use_local_labels,
            )
        except Exception as exc:
            logger.warning(
                "Weasy bilingual receipt rendering failed for %s receipt; trying shaped Pillow fallback: %s",
                local_language,
                exc,
                exc_info=True,
            )
        try:
            return _build_receipt_pdf_bytes_pillow(
                payload,
                local_language=local_language,
                labels=labels,
                local_labels=local_labels,
                use_local_labels=use_local_labels,
            )
        except Exception as exc:
            logger.warning(
                "Pillow bilingual receipt rendering failed for %s receipt; falling back to ReportLab with bundled fonts: %s",
                local_language,
                exc,
                exc_info=True,
            )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )

    styles = getSampleStyleSheet()
    header_title = ParagraphStyle(
        "ReceiptHeaderTitle",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=11.5,
        leading=13,
        alignment=1,
        spaceAfter=1,
    )
    header_line = ParagraphStyle(
        "ReceiptHeaderLine",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.5,
        leading=10,
        alignment=1,
    )
    table_cell = ParagraphStyle(
        "ReceiptTableCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=11,
    )
    table_cell_small = ParagraphStyle(
        "ReceiptTableCellSmall",
        parent=table_cell,
        fontSize=8.4,
        leading=10.2,
    )
    table_cell_bold = ParagraphStyle(
        "ReceiptTableCellBold",
        parent=table_cell,
        fontName=f"{font_name}-Bold" if font_name == "Helvetica" else font_name,
    )
    table_cell_center = ParagraphStyle("ReceiptTableCellCenter", parent=table_cell, alignment=1)
    table_cell_right = ParagraphStyle("ReceiptTableCellRight", parent=table_cell, alignment=2)
    table_cell_small_right = ParagraphStyle("ReceiptTableCellSmallRight", parent=table_cell_small, alignment=2)
    footer_note = ParagraphStyle(
        "ReceiptFooterNote",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7.8,
        leading=9.2,
        alignment=1,
    )
    powered_by_note = ParagraphStyle(
        "ReceiptPoweredByNote",
        parent=footer_note,
        fontSize=6.6,
        leading=8,
        alignment=2,
    )

    elements: list[Any] = []

    logo_obj = None
    logo_source = payload.get("logo")
    if logo_source:
        try:
            logo_obj = Image(logo_source, width=16 * mm, height=16 * mm)
        except Exception:
            logo_obj = None

    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""

    header_lines: list[Any] = []
    header_local_line = _as_text(payload.get("header_local_line"))
    if header_local_line and use_local_labels:
        header_lines.append(_receipt_paragraph(header_local_line, header_line))
    header_lines.append(_receipt_paragraph(primary_header, header_title))
    if secondary_header:
        header_lines.append(_receipt_paragraph(secondary_header, header_line))

    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )
    if address_line:
        header_lines.append(_receipt_paragraph(address_line, header_line))
    if _as_text(payload.get("website")):
        header_lines.append(_receipt_paragraph(_as_text(payload.get("website")), header_line))
    if _as_text(payload.get("email")):
        header_lines.append(_receipt_paragraph(_as_text(payload.get("email")), header_line))
    if _as_text(payload.get("phone")):
        header_lines.append(_receipt_paragraph(f"Phone : {_as_text(payload.get('phone'))}", header_line))

    if logo_obj:
        logo_width = 22 * mm
        header_table = Table([[logo_obj, header_lines]], colWidths=[logo_width, doc.width - logo_width])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        elements.append(header_table)
    else:
        elements.extend(header_lines)

    elements.append(Spacer(1, 4))

    line_items = payload.get("line_items") or []
    if not line_items:
        line_items = [{"description": "-", "amount": payload.get("total_amount", 0)}]

    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    receipt_title_raw = _as_text(payload.get("receipt_title"))
    receipt_title_local = _as_text(payload.get("receipt_title_local")) or local_labels.get("receipt_title", "")
    receipt_title = _bilingual_label(receipt_title_local, receipt_title_raw, use_local_labels) if receipt_title_raw else labels["receipt_title"]
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label_raw = payload.get("party_label")
    party_label = labels["party"] if party_label_raw is None else _as_text(party_label_raw, "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header_raw = _as_text(payload.get("line_item_header"))
    line_item_local = _as_text(payload.get("line_item_local")) or local_labels.get("line_item", "")
    line_item_header = _bilingual_label(line_item_local, line_item_header_raw, use_local_labels) if line_item_header_raw else labels["line_item"]
    total_label = _as_text(payload.get("total_label")) or labels["total"]
    gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
    star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
    rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
    service_date_label_raw = _as_text(payload.get("service_date_label"))
    service_date_local = _as_text(payload.get("service_date_local")) or local_labels.get("service_date", "")
    service_date_label = _bilingual_label(service_date_local, service_date_label_raw, use_local_labels) if service_date_label_raw else labels["service_date"]
    signatory_label = _as_text(payload.get("signatory_label"), labels["cashier"])

    rows: list[list[Any]] = []
    rows.append([_receipt_paragraph(receipt_title, table_cell_center), "", ""])
    rows.append([
        _receipt_paragraph(f"{receipt_no_label}: {_as_text(payload.get('receipt_number'), '-')}", table_cell_small),
        _receipt_paragraph(f"{date_label}: {_as_text(payload.get('receipt_date'), '-')}", table_cell_small_right),
        "",
    ])
    party_name = _as_text(payload.get("party_name"), "-")
    party_line = f"{party_label}: {party_name}" if party_label else party_name
    rows.append([_receipt_paragraph(party_line, table_cell), "", ""])
    rows.append([_receipt_paragraph(f"{address_label}: {_as_text(payload.get('address_value'), '--')}", table_cell), "", ""])
    rows.append([_receipt_paragraph(_as_text(payload.get('amount_words_line'), 'Received with thanks'), table_cell_small), "", ""])
    rows.append([_receipt_paragraph(_as_text(payload.get('payment_line'), 'Received with thanks.'), table_cell_small), "", ""])

    rows.append([
        _receipt_paragraph(line_item_header, table_cell_bold),
        _receipt_paragraph('Rs', table_cell_center),
        _receipt_paragraph('', table_cell_center),
    ])

    for item in line_items:
        major, minor = _split_amount(item.get('amount'))
        rows.append([
            _receipt_paragraph(_as_text(item.get('description'), '-'), table_cell),
            _receipt_paragraph(major, table_cell_right),
            _receipt_paragraph(minor, table_cell_right),
        ])

    total_major, total_minor = _split_amount(total_amount)
    rows.append([
        _receipt_paragraph(total_label, table_cell_right),
        _receipt_paragraph(total_major, table_cell_right),
        _receipt_paragraph(total_minor, table_cell_right),
    ])

    include_note_row = bool(payload.get("include_note_row", True))
    if include_note_row:
        note_line_local = _as_text(payload.get('note_local'), labels['note_local'])
        note_line_english = _as_text(payload.get('note_english'), '')
        note_lines = [line for line in [note_line_local if use_local_labels else '', note_line_english] if line]
        note_block = '\n'.join(note_lines)
        rows.append([_receipt_paragraph(note_block or '-', table_cell_center), '', ''])

    col1 = doc.width * 0.72
    col2 = doc.width * 0.20
    col3 = doc.width - col1 - col2
    table = Table(rows, colWidths=[col1, col2, col3])

    note_row_index = len(rows) - 1 if include_note_row else None
    table_style = [
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#808080')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A0A0A0')),
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (1, 1), (2, 1)),
        ('SPAN', (0, 2), (2, 2)),
        ('SPAN', (0, 3), (2, 3)),
        ('SPAN', (0, 4), (2, 4)),
        ('SPAN', (0, 5), (2, 5)),
        ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#F2F2F2')),
        ('BACKGROUND', (0, 6), (2, 6), colors.HexColor('#F8F8F8')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 2), (2, 5), 4),
        ('BOTTOMPADDING', (0, 2), (2, 5), 4),
        ('LEFTPADDING', (0, 2), (0, 5), 6),
        ('TOPPADDING', (0, 6), (2, 6), 4),
        ('BOTTOMPADDING', (0, 6), (2, 6), 4),
    ]
    if note_row_index is not None:
        table_style.extend([
            ('SPAN', (0, note_row_index), (2, note_row_index)),
            ('BACKGROUND', (0, note_row_index), (2, note_row_index), colors.HexColor('#F8F8F8')),
            ('BOTTOMPADDING', (0, note_row_index), (2, note_row_index), 5),
        ])
    table.setStyle(TableStyle(table_style))

    elements.append(table)
    elements.append(Spacer(1, 4))

    if bool(payload.get('include_astro_row', True)):
        astro_line = (
            f"{gotra_label}: {_as_text(payload.get('gotra'), '--')}    "
            f"{star_label}: {_as_text(payload.get('nakshatra'), '--')}    "
            f"{rashi_label}: {_as_text(payload.get('rashi'), '--')}"
        )
        elements.append(_receipt_paragraph(astro_line, table_cell_small))
        elements.append(Spacer(1, 2))

    if bool(payload.get('include_service_row', True)):
        service_line = f"{service_date_label}: {_as_text(payload.get('service_date'), '--')}"
        elements.append(_receipt_paragraph(service_line, table_cell_small))
        elements.append(Spacer(1, 2))

    system_line_raw = payload.get('system_generated_line')
    if system_line_raw is None:
        system_line = 'This is a system generated receipt and does not require any signature.'
    else:
        system_line = str(system_line_raw).strip()

    powered_by = _as_text(payload.get('powered_by_line'), 'Powered by Sanmitra Tech Solutions.')

    if system_line:
        elements.append(_receipt_paragraph(system_line, footer_note))
        elements.append(Spacer(1, 4))
    elements.append(_receipt_paragraph(powered_by, powered_by_note))

    doc.build(elements)
    return buffer.getvalue()



# ════════════════════════════════════════════════════════════════════════
# SECTION: PINCODE + DATE-WINDOW HELPERS
# NOTE   : _normalize_pincode, _lookup_pincode_city_state, _to_positive_int
# ════════════════════════════════════════════════════════════════════════

def _normalize_pincode(value: Any) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:6]


MANDIR_PINCODE_FALLBACKS: dict[str, tuple[str, str]] = {
    "560001": ("Bengaluru", "Karnataka"),
    "560002": ("Bengaluru", "Karnataka"),
    "560003": ("Bengaluru", "Karnataka"),
    "560004": ("Bengaluru", "Karnataka"),
    "560011": ("Bengaluru", "Karnataka"),
    "560019": ("Bengaluru", "Karnataka"),
    "560070": ("Bengaluru", "Karnataka"),
    "560078": ("Bengaluru", "Karnataka"),
    "575001": ("Mangaluru", "Karnataka"),
    "575002": ("Mangaluru", "Karnataka"),
    "575003": ("Mangaluru", "Karnataka"),
    "575004": ("Mangaluru", "Karnataka"),
    "575005": ("Mangaluru", "Karnataka"),
    "600004": ("Chennai", "Tamil Nadu"),
    "600017": ("Chennai", "Tamil Nadu"),
    "600020": ("Chennai", "Tamil Nadu"),
    "600028": ("Chennai", "Tamil Nadu"),
    "500034": ("Hyderabad", "Telangana"),
    "530017": ("Visakhapatnam", "Andhra Pradesh"),
    "641002": ("Coimbatore", "Tamil Nadu"),
}


async def _lookup_pincode_city_state(pincode: str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"https://api.postalpincode.in/pincode/{pincode}")
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    if not isinstance(payload, list) or not payload:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    first = payload[0] if isinstance(payload[0], dict) else {}
    if str(first.get("Status") or "").strip().lower() != "success":
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    offices = first.get("PostOffice")
    if not isinstance(offices, list) or not offices:
        return MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    primary = offices[0] if isinstance(offices[0], dict) else {}
    city = str(primary.get("District") or primary.get("Taluk") or primary.get("Name") or "").strip() or None
    state = str(primary.get("State") or "").strip() or None
    return (city, state) if city and state else MANDIR_PINCODE_FALLBACKS.get(pincode, (city, state))


def _to_positive_int(value: Any) -> int | None:
    parsed = _safe_optional_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


_SEVA_ALLOWED_CATEGORIES = {
    "abhisheka",
    "alankara",
    "pooja",
    "archana",
    "vahana_seva",
    "special",
    "festival",
}
_SEVA_ALLOWED_AVAILABILITY = {
    "daily",
    "weekday",
    "weekend",
    "specific_day",
    "except_day",
    "festival_only",
}



# ════════════════════════════════════════════════════════════════════════
# SECTION: SEVA BOOKING HELPERS
# NOTE   : _normalize_seva_category/availability/day, _today_weekday, _parse_booking_date, _validate_seva_booking_date, _count_seva_bookings_for_date, _validate_seva_booking_capacity, _compute_seva_available_today, _resolve_report_date_window, _resolve_export_window
# ════════════════════════════════════════════════════════════════════════

def _normalize_seva_category(value: Any) -> str:
    candidate = str(value or "pooja").strip().lower()
    return candidate if candidate in _SEVA_ALLOWED_CATEGORIES else "pooja"


def _normalize_seva_availability(value: Any) -> str:
    candidate = str(value or "daily").strip().lower()
    return candidate if candidate in _SEVA_ALLOWED_AVAILABILITY else "daily"


def _normalize_seva_day(value: Any) -> int | None:
    parsed = _safe_optional_int(value)
    if parsed is None:
        return None
    if 0 <= parsed <= 6:
        return parsed
    return None


_IST_TIMEZONE = ZoneInfo("Asia/Kolkata")


def _today_weekday_js_index() -> int:
    # JavaScript Date.getDay convention: Sunday=0 ... Saturday=6.
    return (datetime.now(_IST_TIMEZONE).weekday() + 1) % 7


def _weekday_js_index_for_date(value: date) -> int:
    # JavaScript Date.getDay convention: Sunday=0 ... Saturday=6.
    return (value.weekday() + 1) % 7


def _parse_booking_date(value: Any) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except Exception:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except Exception:
                continue
    return None


def _validate_seva_booking_date(seva_doc: dict[str, Any] | None, booking_date: date) -> None:
    if not seva_doc:
        return

    target_day = _weekday_js_index_for_date(booking_date)
    specific_day = _normalize_seva_day(seva_doc.get("specific_day"))
    except_day = _normalize_seva_day(seva_doc.get("except_day"))
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    if specific_day is not None and target_day != specific_day:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is available only on {day_names[specific_day]}. Please select a {day_names[specific_day]} date.",
        )
    if except_day is not None and target_day == except_day:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is not available on {day_names[except_day]}. Please select another date.",
        )

    availability = _normalize_seva_availability(seva_doc.get("availability"))
    if availability == "weekday" and target_day not in {1, 2, 3, 4, 5}:
        raise HTTPException(status_code=400, detail="This seva is available only on weekdays.")
    if availability == "weekend" and target_day not in {0, 6}:
        raise HTTPException(status_code=400, detail="This seva is available only on weekends.")
    if availability == "festival_only":
        raise HTTPException(status_code=400, detail="This seva is available only on configured festival dates.")


async def _count_seva_bookings_for_date(
    *,
    tenant_id: str,
    app_key: str,
    seva_id: str,
    booking_date: date,
) -> int:
    booking_date_text = booking_date.isoformat()
    docs = await get_collection("mandir_seva_bookings").find(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "seva_id": str(seva_id),
            "booking_date": booking_date_text,
        }
    ).to_list(length=5000)
    return sum(
        1
        for doc in docs
        if str(doc.get("status") or "").strip().lower() not in {"cancelled", "canceled"}
    )


async def _validate_seva_booking_capacity(
    seva_doc: dict[str, Any] | None,
    *,
    tenant_id: str,
    app_key: str,
    seva_id: str,
    booking_date: date,
) -> tuple[int | None, int, int | None]:
    max_bookings = _safe_optional_int((seva_doc or {}).get("max_bookings_per_day"))
    booked_count = await _count_seva_bookings_for_date(
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=seva_id,
        booking_date=booking_date,
    )
    if max_bookings is None or max_bookings <= 0:
        return None, booked_count, None

    slots_left = max(max_bookings - booked_count, 0)
    if slots_left <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"This seva is fully booked for {booking_date.strftime('%d-%m-%Y')}. Please select another date.",
        )
    return max_bookings, booked_count, slots_left


def _compute_seva_available_today(row: dict[str, Any]) -> bool:
    if not _safe_bool(row.get("is_active"), True):
        return False

    slots_left = _safe_optional_int(row.get("bookings_available"))
    if slots_left is not None and slots_left <= 0:
        return False

    today = _today_weekday_js_index()
    specific_day = _normalize_seva_day(row.get("specific_day"))
    except_day = _normalize_seva_day(row.get("except_day"))

    # Explicit day constraints are authoritative even if availability is stale.
    if specific_day is not None:
        return specific_day == today
    if except_day is not None:
        return except_day != today

    availability = _normalize_seva_availability(row.get("availability"))
    if availability == "weekday":
        return 1 <= today <= 5
    if availability == "weekend":
        return today in {0, 6}
    if availability == "festival_only":
        return False
    return True

def _resolve_report_date_window(
    *,
    from_date: date | None,
    to_date: date | None,
    single_date: date | None = None,
    month: int | None = None,
    year: int | None = None,
) -> tuple[date, date]:
    if single_date is not None:
        return single_date, single_date

    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
        return from_date, to_date

    if month is not None or year is not None:
        resolved_year = year or datetime.now(timezone.utc).year
        if month is None:
            start = date(resolved_year, 1, 1)
            end = date(resolved_year, 12, 31)
            return start, end

        _, last_day = calendar.monthrange(resolved_year, month)
        start = date(resolved_year, month, 1)
        end = date(resolved_year, month, last_day)
        return start, end

    if from_date is not None and to_date is None:
        return from_date, from_date
    if to_date is not None and from_date is None:
        return to_date, to_date

    raise HTTPException(
        status_code=422,
        detail="Provide either date, from_date/to_date, or month/year query parameters",
    )


def _resolve_export_window(
    *,
    from_date: date | None,
    to_date: date | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    start = from_date or date_from
    end = to_date or date_to
    if start is None or end is None:
        raise HTTPException(status_code=422, detail="from_date/to_date (or date_from/date_to) are required")
    if start > end:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    return start, end



# ════════════════════════════════════════════════════════════════════════
# SECTION: DASHBOARD STATS + SEVA BUILDERS
# NOTE   : _dashboard_posted_stats, _canonical_seva_name, _build_seva_item, _build_seva_patch, _serialize_seva_doc, _seva_import_template_csv, _normalize_phone, _parse_iso_datetime
# ════════════════════════════════════════════════════════════════════════

async def _dashboard_posted_stats(
    *,
    session: AsyncSession,
    tenant_id: str,
    app_key: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    today = datetime.now(timezone.utc).date()
    start_of_year = date(today.year, 1, 1)
    try:
        donations = await posted_donations(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            from_date=start_of_year,
            to_date=today,
        )
    except Exception as exc:
        logger.warning("Dashboard: failed to fetch posted donations for tenant=%s: %s", tenant_id, exc)
        donations = []

    try:
        sevas = await posted_sevas(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            from_date=start_of_year,
            to_date=today,
        )
    except Exception as exc:
        logger.warning("Dashboard: failed to fetch posted sevas for tenant=%s: %s", tenant_id, exc)
        sevas = []

    return donations, sevas

def _canonical_seva_name(payload: dict[str, Any]) -> str:
    name = str(payload.get("name_english") or payload.get("name") or payload.get("seva_name") or "Seva").strip()
    return name or "Seva"


def _build_seva_item(payload: dict[str, Any], *, tenant_id: str, app_key: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    name = _canonical_seva_name(payload)
    advance_days = _safe_optional_int(payload.get("advance_booking_days"))

    return {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "name": name,
        "name_english": name,
        "name_kannada": _safe_optional_str(payload.get("name_kannada")) or "",
        "name_sanskrit": _safe_optional_str(payload.get("name_sanskrit")) or "",
        "description": _safe_optional_str(payload.get("description")) or "",
        "category": _normalize_seva_category(payload.get("category")),
        "amount": _safe_float(payload.get("amount"), 0.0),
        "min_amount": _safe_optional_float(payload.get("min_amount")),
        "max_amount": _safe_optional_float(payload.get("max_amount")),
        "availability": _normalize_seva_availability(payload.get("availability")),
        "specific_day": _normalize_seva_day(payload.get("specific_day")),
        "except_day": _normalize_seva_day(payload.get("except_day")),
        "time_slot": _safe_optional_str(payload.get("time_slot")) or "",
        "max_bookings_per_day": _safe_optional_int(payload.get("max_bookings_per_day")),
        "advance_booking_days": advance_days if advance_days and advance_days > 0 else 30,
        "requires_approval": _safe_bool(payload.get("requires_approval"), False),
        "is_active": _safe_bool(payload.get("is_active"), True),
        "quick_ticket_enabled": _safe_bool(payload.get("quick_ticket_enabled"), False),
        "requires_devotee_details": _safe_bool(payload.get("requires_devotee_details"), True),
        "benefits": _safe_optional_str(payload.get("benefits")) or "",
        "instructions": _safe_optional_str(payload.get("instructions")) or "",
        "duration_minutes": _safe_optional_int(payload.get("duration_minutes")),
        "created_at": now,
        "updated_at": now,
    }


def _build_seva_patch(payload: dict[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}

    if {"name", "name_english", "seva_name"} & payload.keys():
        name = _canonical_seva_name(payload)
        patch["name"] = name
        patch["name_english"] = name

    if "name_kannada" in payload:
        patch["name_kannada"] = _safe_optional_str(payload.get("name_kannada")) or ""
    if "name_sanskrit" in payload:
        patch["name_sanskrit"] = _safe_optional_str(payload.get("name_sanskrit")) or ""
    if "description" in payload:
        patch["description"] = _safe_optional_str(payload.get("description")) or ""
    if "category" in payload:
        patch["category"] = _normalize_seva_category(payload.get("category"))
    if "amount" in payload:
        patch["amount"] = _safe_float(payload.get("amount"), 0.0)
    if "min_amount" in payload:
        patch["min_amount"] = _safe_optional_float(payload.get("min_amount"))
    if "max_amount" in payload:
        patch["max_amount"] = _safe_optional_float(payload.get("max_amount"))
    if "availability" in payload:
        patch["availability"] = _normalize_seva_availability(payload.get("availability"))
    if "specific_day" in payload:
        patch["specific_day"] = _normalize_seva_day(payload.get("specific_day"))
    if "except_day" in payload:
        patch["except_day"] = _normalize_seva_day(payload.get("except_day"))
    if "time_slot" in payload:
        patch["time_slot"] = _safe_optional_str(payload.get("time_slot")) or ""
    if "max_bookings_per_day" in payload:
        patch["max_bookings_per_day"] = _safe_optional_int(payload.get("max_bookings_per_day"))
    if "advance_booking_days" in payload:
        days = _safe_optional_int(payload.get("advance_booking_days"))
        patch["advance_booking_days"] = days if days and days > 0 else 30
    if "requires_approval" in payload:
        patch["requires_approval"] = _safe_bool(payload.get("requires_approval"), False)
    if "is_active" in payload:
        patch["is_active"] = _safe_bool(payload.get("is_active"), True)
    if "quick_ticket_enabled" in payload:
        patch["quick_ticket_enabled"] = _safe_bool(payload.get("quick_ticket_enabled"), False)
    if "requires_devotee_details" in payload:
        patch["requires_devotee_details"] = _safe_bool(payload.get("requires_devotee_details"), True)
    if "benefits" in payload:
        patch["benefits"] = _safe_optional_str(payload.get("benefits")) or ""
    if "instructions" in payload:
        patch["instructions"] = _safe_optional_str(payload.get("instructions")) or ""
    if "duration_minutes" in payload:
        patch["duration_minutes"] = _safe_optional_int(payload.get("duration_minutes"))

    return patch


def _serialize_seva_doc(doc: dict[str, Any]) -> dict[str, Any]:
    row = dict(doc)
    row.pop("_id", None)

    name = str(row.get("name_english") or row.get("name") or row.get("seva_name") or "Seva").strip() or "Seva"
    row["name_english"] = name
    row["name"] = name
    row["category"] = _normalize_seva_category(row.get("category"))
    row["availability"] = _normalize_seva_availability(row.get("availability"))
    row["amount"] = _safe_float(row.get("amount"), 0.0)
    row["min_amount"] = _safe_optional_float(row.get("min_amount"))
    row["max_amount"] = _safe_optional_float(row.get("max_amount"))
    row["specific_day"] = _normalize_seva_day(row.get("specific_day"))
    row["except_day"] = _normalize_seva_day(row.get("except_day"))
    row["max_bookings_per_day"] = _safe_optional_int(row.get("max_bookings_per_day"))
    row["bookings_available"] = _safe_optional_int(row.get("bookings_available"))
    row["duration_minutes"] = _safe_optional_int(row.get("duration_minutes"))
    row["advance_booking_days"] = _safe_optional_int(row.get("advance_booking_days")) or 30
    row["requires_approval"] = _safe_bool(row.get("requires_approval"), False)
    row["is_active"] = _safe_bool(row.get("is_active"), True)
    row["quick_ticket_enabled"] = _safe_bool(row.get("quick_ticket_enabled"), False)
    row["requires_devotee_details"] = _safe_bool(row.get("requires_devotee_details"), True)
    row["is_available_today"] = _compute_seva_available_today(row)
    row["description"] = _safe_optional_str(row.get("description")) or ""
    row["name_kannada"] = _safe_optional_str(row.get("name_kannada")) or ""
    row["name_sanskrit"] = _safe_optional_str(row.get("name_sanskrit")) or ""
    row["time_slot"] = _safe_optional_str(row.get("time_slot")) or ""
    row["benefits"] = _safe_optional_str(row.get("benefits")) or ""
    row["instructions"] = _safe_optional_str(row.get("instructions")) or ""
    row["id"] = str(row.get("id") or row.get("seva_id") or "")

    return row


_SEVA_IMPORT_COLUMNS = [
    "name_english",
    "name_kannada",
    "name_sanskrit",
    "description",
    "category",
    "amount",
    "min_amount",
    "max_amount",
    "availability",
    "specific_day",
    "except_day",
    "time_slot",
    "max_bookings_per_day",
    "advance_booking_days",
    "requires_approval",
    "is_active",
    "benefits",
    "instructions",
    "duration_minutes",
]


def _seva_import_template_csv() -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=_SEVA_IMPORT_COLUMNS)
    writer.writeheader()
    writer.writerow(
        {
            "name_english": "Daily Archana",
            "name_kannada": "ದೈನಿಕ ಆರ್ಚನೆ",
            "name_sanskrit": "दैनिक आरचना",
            "description": "Daily morning archana seva",
            "category": "archana",
            "amount": "50",
            "min_amount": "",
            "max_amount": "",
            "availability": "daily",
            "specific_day": "",
            "except_day": "",
            "time_slot": "Morning 6:00 AM",
            "max_bookings_per_day": "",
            "advance_booking_days": "30",
            "requires_approval": "false",
            "is_active": "true",
            "benefits": "",
            "instructions": "",
            "duration_minutes": "",
        }
    )
    writer.writerow(
        {
            "name_english": "Sarva Seva",
            "name_kannada": "ಸರ್ವ ಸೇವೆ",
            "name_sanskrit": "सर्व सेवा",
            "description": "Comprehensive daily worship services",
            "category": "pooja",
            "amount": "500",
            "min_amount": "",
            "max_amount": "",
            "availability": "daily",
            "specific_day": "",
            "except_day": "",
            "time_slot": "Daily",
            "max_bookings_per_day": "",
            "advance_booking_days": "30",
            "requires_approval": "false",
            "is_active": "true",
            "benefits": "",
            "instructions": "",
            "duration_minutes": "",
        }
    )
    return output.getvalue()

def _normalize_phone(phone: str | None) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return digits[-10:] if len(digits) > 10 else digits


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None



# ════════════════════════════════════════════════════════════════════════
# SECTION: DEVOTEE + UPI HELPERS
# NOTE   : _upi_receipt_number, _mandir_upi_payment_view, _find_devotee_by_phone, _upsert_devotee_from_contribution, _build_upi_intent_uri
# ════════════════════════════════════════════════════════════════════════

def _upi_receipt_number(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    row_id = str(doc.get("id") or "").strip()
    if row_id:
        return f"UPI-{row_id[:8].upper()}"

    return f"UPI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _mandir_upi_payment_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    row_id = str(row.get("id") or "").strip()
    if row_id:
        row["id"] = row_id

    row["amount"] = _safe_float(row.get("amount"), 0.0)
    row["payment_purpose"] = str(row.get("payment_purpose") or "DONATION").strip().upper()
    row["receipt_number"] = _upi_receipt_number(row)
    if not row.get("payment_datetime"):
        row["payment_datetime"] = row.get("created_at")

    row["sender_phone"] = _normalize_phone(row.get("sender_phone") or row.get("devotee_phone"))
    row["devotee_phone"] = _normalize_phone(row.get("devotee_phone") or row.get("sender_phone"))
    return row


async def _find_devotee_by_phone(
    tenant_id: str,
    app_key: str,
    phone: str,
    temple_id: int | None = None,
) -> dict[str, Any] | None:
    normalized = _normalize_phone(phone)
    if not normalized:
        return None

    scope_query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if temple_id is not None and temple_id > 0:
        scope_query["temple_id"] = temple_id

    legacy_scope_query: dict[str, Any] | None = None
    if temple_id is not None and temple_id > 0:
        # Older MandirMitra donation/seva-derived devotee data was tenant-scoped
        # but did not persist temple_id. Keep this fallback inside the resolved
        # tenant/app and only match records with no explicit temple assignment.
        legacy_scope_query = {"tenant_id": tenant_id, "app_key": app_key, "temple_id": None}

    devotee_col = get_collection("mandir_devotees")
    docs = await devotee_col.find({**scope_query, "phone": normalized}).limit(1).to_list(length=1)
    if docs:
        return _sanitize_mongo_doc(docs[0])
    if legacy_scope_query is not None:
        docs = await devotee_col.find({**legacy_scope_query, "phone": normalized}).limit(1).to_list(length=1)
        if docs:
            devotee = _sanitize_mongo_doc(docs[0])
            devotee["temple_id"] = temple_id
            return devotee

    donation_col = get_collection("mandir_donations")
    donation_docs = await (
        donation_col.find({**scope_query, "devotee_phone": normalized})
        .sort("created_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if donation_docs:
        donation = _sanitize_mongo_doc(donation_docs[0])
        snapshot = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
        return {
            "id": str(snapshot.get("id") or donation.get("devotee_id") or f"donation:{donation.get('donation_id') or donation.get('id')}"),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "temple_id": temple_id,
            "name_prefix": donation.get("devotee_prefix") or snapshot.get("name_prefix"),
            "name": donation.get("devotee_name") or snapshot.get("name") or "Devotee",
            "first_name": donation.get("devotee_name") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
            "last_name": snapshot.get("last_name") or "",
            "phone": normalized,
            "email": donation.get("devotee_email") or snapshot.get("email"),
            "address": donation.get("devotee_address") or snapshot.get("address"),
            "city": donation.get("devotee_city") or snapshot.get("city"),
            "state": donation.get("devotee_state") or snapshot.get("state"),
            "pincode": donation.get("devotee_pincode") or snapshot.get("pincode"),
            "source": "donation",
        }
    if legacy_scope_query is not None:
        donation_docs = await (
            donation_col.find({**legacy_scope_query, "devotee_phone": normalized})
            .sort("created_at", -1)
            .limit(1)
            .to_list(length=1)
        )
        if donation_docs:
            donation = _sanitize_mongo_doc(donation_docs[0])
            snapshot = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
            return {
                "id": str(snapshot.get("id") or donation.get("devotee_id") or f"donation:{donation.get('donation_id') or donation.get('id')}"),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "temple_id": temple_id,
                "name_prefix": donation.get("devotee_prefix") or snapshot.get("name_prefix"),
                "name": donation.get("devotee_name") or snapshot.get("name") or "Devotee",
                "first_name": donation.get("devotee_name") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
                "last_name": snapshot.get("last_name") or "",
                "phone": normalized,
                "email": donation.get("devotee_email") or snapshot.get("email"),
                "address": donation.get("devotee_address") or snapshot.get("address"),
                "city": donation.get("devotee_city") or snapshot.get("city"),
                "state": donation.get("devotee_state") or snapshot.get("state"),
                "pincode": donation.get("devotee_pincode") or snapshot.get("pincode"),
                "source": "donation",
            }

    seva_col = get_collection("mandir_seva_bookings")
    seva_docs = await (
        seva_col.find({**scope_query, "devotee_phone": normalized})
        .sort("created_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if seva_docs:
        seva = _sanitize_mongo_doc(seva_docs[0])
        snapshot = seva.get("devotee") if isinstance(seva.get("devotee"), dict) else {}
        return {
            "id": str(snapshot.get("id") or seva.get("devotee_id") or f"seva:{seva.get('booking_id') or seva.get('id')}"),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "temple_id": temple_id,
            "name_prefix": seva.get("devotee_prefix") or snapshot.get("name_prefix"),
            "name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("name") or "Devotee",
            "first_name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
            "last_name": snapshot.get("last_name") or "",
            "phone": normalized,
            "email": seva.get("devotee_email") or snapshot.get("email"),
            "address": seva.get("devotee_address") or seva.get("address") or snapshot.get("address"),
            "city": seva.get("devotee_city") or seva.get("city") or snapshot.get("city"),
            "state": seva.get("devotee_state") or seva.get("state") or snapshot.get("state"),
            "pincode": seva.get("devotee_pincode") or seva.get("pincode") or snapshot.get("pincode"),
            "source": "seva",
        }
    if legacy_scope_query is not None:
        seva_docs = await (
            seva_col.find({**legacy_scope_query, "devotee_phone": normalized})
            .sort("created_at", -1)
            .limit(1)
            .to_list(length=1)
        )
        if seva_docs:
            seva = _sanitize_mongo_doc(seva_docs[0])
            snapshot = seva.get("devotee") if isinstance(seva.get("devotee"), dict) else {}
            return {
                "id": str(snapshot.get("id") or seva.get("devotee_id") or f"seva:{seva.get('booking_id') or seva.get('id')}"),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "temple_id": temple_id,
                "name_prefix": seva.get("devotee_prefix") or snapshot.get("name_prefix"),
                "name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("name") or "Devotee",
                "first_name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
                "last_name": snapshot.get("last_name") or "",
                "phone": normalized,
                "email": seva.get("devotee_email") or snapshot.get("email"),
                "address": seva.get("devotee_address") or seva.get("address") or snapshot.get("address"),
                "city": seva.get("devotee_city") or seva.get("city") or snapshot.get("city"),
                "state": seva.get("devotee_state") or seva.get("state") or snapshot.get("state"),
                "pincode": seva.get("devotee_pincode") or seva.get("pincode") or snapshot.get("pincode"),
                "source": "seva",
            }

    return None


async def _upsert_devotee_from_contribution(
    tenant_id: str,
    app_key: str,
    *,
    temple_id: int | None = None,
    phone: str | None,
    name_prefix: str | None = None,
    name: str | None = None,
    email: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    pincode: str | None = None,
) -> None:
    normalized = _normalize_phone(phone)
    if not normalized:
        return

    now = datetime.now(timezone.utc).isoformat()
    devotee_patch: dict[str, Any] = {"updated_at": now}
    if temple_id is not None and temple_id > 0:
        devotee_patch["temple_id"] = temple_id
    for key, value in {
        "name_prefix": name_prefix,
        "name": name,
        "first_name": name,
        "email": email,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
    }.items():
        if value not in (None, ""):
            devotee_patch[key] = value

    col = get_collection("mandir_devotees")
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized}
    if temple_id is not None and temple_id > 0:
        query["temple_id"] = temple_id

    insert_doc: dict[str, Any] = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "phone": normalized,
        "created_at": now,
    }
    if temple_id is not None and temple_id > 0:
        insert_doc["temple_id"] = temple_id

    await col.update_one(
        query,
        {
            "$setOnInsert": insert_doc,
            "$set": devotee_patch,
        },
        upsert=True,
    )


def _build_upi_intent_uri(
    *,
    upi_id: str,
    payee_name: str,
    amount: float | None,
    note: str | None,
    reference: str | None,
    currency: str = "INR",
) -> str:
    params: list[tuple[str, str]] = [("pa", upi_id), ("pn", payee_name), ("cu", currency)]
    if amount is not None and amount > 0:
        params.append(("am", f"{amount:.2f}"))
    if note:
        params.append(("tn", note))
    if reference:
        params.append(("tr", reference))
    return f"upi://pay?{urlencode(params)}"



# ════════════════════════════════════════════════════════════════════════
# SECTION: PLATFORM + TENANT RESOLVERS
# NOTE   : _is_platform_super_admin, _resolve_tenant_for_mandir_request, _assert_platform_can_write_tenant, _payment_accounts
# ════════════════════════════════════════════════════════════════════════

def _is_platform_super_admin(user: dict[str, Any]) -> bool:
    return bool(user.get("is_superuser")) or str(user.get("role") or "").strip().lower() == "super_admin"


async def _resolve_tenant_for_mandir_request(
    current_user: dict[str, Any],
    x_tenant_id: str | None,
    temple_id: int | None,
    app_key: str = "mandirmitra",
) -> str:
    if temple_id and _is_platform_super_admin(current_user):
        mapped_tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
        if mapped_tenant_id:
            return mapped_tenant_id
    return resolve_tenant_id(current_user, x_tenant_id)


async def _assert_platform_can_write_tenant(
    current_user: dict[str, Any],
    *,
    tenant_id: str,
    app_key: str,
) -> None:
    if not _is_platform_super_admin(current_user):
        return

    doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not bool(doc.get("platform_can_write", False)):
        tenant_name = str(doc.get("name") or doc.get("trust_name") or "Selected tenant").strip()
        raise HTTPException(
            status_code=403,
            detail=f"{tenant_name} is read-only for the platform administrator.",
        )


async def _payment_accounts(tenant_id: str, app_key: str) -> dict[str, list[dict[str, Any]]]:
    cash_accounts: list[dict[str, Any]] = []
    bank_accounts: list[dict[str, Any]] = []
    seen_cash_codes: set[str] = set()
    seen_bank_codes: set[str] = set()

    try:
        accounts = get_collection("accounting_accounts")
        await _ensure_default_mandir_accounts(tenant_id, app_key)
        docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=200)
        for doc in docs:
            item = _mandir_account_view(doc)
            account_code = str(item.get("account_code") or "").strip()
            # Mandir COA uses 5-digit numeric account codes.
            if account_code.isdigit() and len(account_code) < 5:
                continue

            account_type = item["account_type"].lower()
            cash_bank_nature = str(item.get("cash_bank_nature") or "").lower()
            name = str(item.get("account_name") or "").lower()
            if cash_bank_nature == "cash" or account_type in {"cash", "cash_in_hand"} or ("cash" in name and item.get("is_cash_bank")):
                if account_code and account_code in seen_cash_codes:
                    continue
                cash_accounts.append(item)
                if account_code:
                    seen_cash_codes.add(account_code)
            elif cash_bank_nature == "bank" or account_type in {"bank", "bank_account", "current_asset"} or ("bank" in name and item.get("is_cash_bank")):
                if account_code and account_code in seen_bank_codes:
                    continue
                bank_accounts.append(item)
                if account_code:
                    seen_bank_codes.add(account_code)
    except Exception:
        pass
    if not cash_accounts:
        cash_accounts = [{
            "id": "cash-main",
            "account_id": "cash-main",
            "account_code": "11001",
            "account_name": "Cash in Hand - Counter",
            "account_type": "asset",
            "cash_bank_nature": "cash",
            "is_cash_bank": True,
            "is_active": True,
            "sub_accounts": [],
        }]
    return {"cash_accounts": cash_accounts, "bank_accounts": bank_accounts}



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Dashboard stats
# ROUTES : GET /dashboard/stats
# ════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/stats")
async def dashboard_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva booking",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    month = now.strftime("%Y-%m")
    year = now.year

    donations, sevas = await _dashboard_posted_stats(session=session, tenant_id=tenant_id, app_key=app_key)

    def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
        out = {
            "today": {"amount": 0.0, "count": 0},
            "month": {"amount": 0.0, "count": 0},
            "year": {"amount": 0.0, "count": 0},
        }
        for row in rows:
            created = str(row.get("created_at") or row.get("date") or row.get("booking_date") or "")
            amount = _safe_float(row.get("amount"), 0.0)
            if created[:10] == today:
                out["today"]["amount"] += amount
                out["today"]["count"] += 1
            if created[:7] == month:
                out["month"]["amount"] += amount
                out["month"]["count"] += 1
            if created[:4] == str(year):
                out["year"]["amount"] += amount
                out["year"]["count"] += 1
        return out

    return {"donations": summarize(donations), "sevas": summarize(sevas)}


def _panchang_city_options() -> list[dict[str, Any]]:
    return [dict(city) for city in _PANCHANG_CITY_OPTIONS]


def _safe_panchang_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_panchang_location(
    settings_doc: dict[str, Any],
    temple_doc: dict[str, Any],
    *,
    city_name: str | None = None,
    latitude: float | str | None = None,
    longitude: float | str | None = None,
) -> tuple[float, float, str]:
    override_lat = _safe_panchang_float(latitude)
    override_lon = _safe_panchang_float(longitude)
    if override_lat is not None and override_lon is not None:
        return override_lat, override_lon, str(city_name or "Selected Location").strip() or "Selected Location"

    settings_lat = _safe_panchang_float(settings_doc.get("latitude"))
    settings_lon = _safe_panchang_float(settings_doc.get("longitude"))
    settings_city = str(settings_doc.get("city_name") or "").strip()
    if settings_lat is not None and settings_lon is not None:
        return settings_lat, settings_lon, settings_city or str(_PANCHANG_DEFAULT_LOCATION["name"])

    temple_lat = _safe_panchang_float(temple_doc.get("latitude"))
    temple_lon = _safe_panchang_float(temple_doc.get("longitude"))
    temple_city = str(temple_doc.get("city") or temple_doc.get("city_name") or "").strip()
    if temple_lat is not None and temple_lon is not None:
        return temple_lat, temple_lon, temple_city or str(_PANCHANG_DEFAULT_LOCATION["name"])

    return (
        float(_PANCHANG_DEFAULT_LOCATION["lat"]),
        float(_PANCHANG_DEFAULT_LOCATION["lon"]),
        str(_PANCHANG_DEFAULT_LOCATION["name"]),
    )



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Panchang (today)
# ROUTES : GET /panchang/today
# ════════════════════════════════════════════════════════════════════════

@router.get("/panchang/today")
async def panchang_today(
    city_name: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Calculate today's panchang using Swiss Ephemeris with temple location."""
    try:
        tenant_id = resolve_tenant_id(current_user, x_tenant_id)
        app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

        # Get temple location from MongoDB
        temple_doc = await get_collection("mandir_temples").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        )
        if not temple_doc:
            temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id})
        if not temple_doc:
            temple_doc = {}

        # Get panchang display settings for overrides
        settings_doc = await get_collection("mandir_panchang_settings").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        ) or {}

        latitude, longitude, city = _resolve_panchang_location(
            settings_doc,
            temple_doc,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )

        # Calculate panchang using Swiss Ephemeris
        panchang_service = PanchangService()
        now = datetime.now()
        panchang_data = panchang_service.calculate_panchang(now, latitude, longitude, city)

        return panchang_data
    except Exception as e:
        logger.error(f"Error calculating panchang: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate panchang: {str(e)}"
        )



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Donations (GET list / POST / cancel / receipt PDF / reconcile / cleanup / export / daily|monthly reports)
# ROUTES : GET /donations/payment-accounts|categories  GET|POST /donations  GET .../receipt/pdf  POST .../cancel|reconcile-posting  DELETE .../cleanup  GET .../report/daily|monthly  GET .../export/excel|pdf
# ════════════════════════════════════════════════════════════════════════

@router.get("/donations/payment-accounts")
async def donations_payment_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await _payment_accounts(tenant_id, app_key)


@router.get("/donations/categories/")
@router.get("/donations/categories")
async def donations_categories(_current_user: dict = Depends(get_current_user)):
    return [
        {"id": "general", "name": "General Donation"},
        {"id": "annadanam", "name": "Annadanam"},
        {"id": "construction", "name": "Construction Fund"},
        {"id": "corpus", "name": "Corpus Fund"},
    ]


@router.get("/donations")
async def list_donations(
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    try:
        col = get_collection("mandir_donations")
        fetch_limit = 2000 if any([q, from_date, to_date, payment_mode]) else min(limit + offset, 2000)
        rows = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).limit(fetch_limit).to_list(length=fetch_limit)
    except Exception as exc:
        logger.error("Failed to list donations for tenant=%s: %s", tenant_id, exc, exc_info=True)
        rows = []

    viewed = [_mandir_donation_view(row) for row in rows]
    if payment_mode:
        normalized_mode = str(payment_mode).strip().lower()
        viewed = [row for row in viewed if str(row.get("payment_mode") or "").strip().lower() == normalized_mode]
    filtered = _mandir_filter_rows(
        viewed,
        q=q,
        from_date=from_date,
        to_date=to_date,
        date_fields=("donation_date", "created_at"),
        search_fields=("receipt_number", "devotee_name", "donor_name", "name", "category", "upi_reference_number"),
    )
    return filtered[offset:offset + limit]


@router.post("/donations", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/donations/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_donation(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation creation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = _to_positive_int(x_temple_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    donation_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    devotee_phone = _normalize_phone(payload.get("devotee_phone") or payload.get("phone"))

    amount = _safe_float(payload.get("amount"), 0.0)
    category = str(payload.get("category") or "General Donation")
    payment_mode = str(payload.get("payment_mode") or "Cash").lower()
    devotee_prefix = _safe_optional_str(
        payload.get("name_prefix")
        or payload.get("devotee_prefix")
        or payload.get("prefix")
        or payload.get("title")
        or payload.get("salutation")
    )
    devotee_name = str(payload.get("devotee_name") or payload.get("first_name") or "Unknown Devotee").strip() or "Unknown Devotee"
    devotee_address = _safe_optional_str(payload.get("devotee_address") or payload.get("address"))
    devotee_city = _safe_optional_str(payload.get("devotee_city") or payload.get("city"))
    devotee_state = _safe_optional_str(payload.get("devotee_state") or payload.get("state"))
    devotee_pincode = _safe_optional_str(payload.get("devotee_pincode") or payload.get("pincode"))

    donation = {
        "donation_id": donation_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "temple_id": temple_id,
        "amount": amount,
        "category": category,
        "donation_type": str(payload.get("donation_type") or "cash").strip().lower() or "cash",
        "in_kind_item_name": _safe_optional_str(payload.get("in_kind_item_name") or payload.get("item_name")),
        "in_kind_item_type": _safe_optional_str(payload.get("in_kind_item_type") or payload.get("item_type") or payload.get("asset_type")),
        "in_kind_quantity": _safe_optional_str(payload.get("in_kind_quantity") or payload.get("quantity")),
        "in_kind_valuation_basis": _safe_optional_str(payload.get("in_kind_valuation_basis") or payload.get("valuation_basis")),
        "event_name": _safe_optional_str(payload.get("event_name") or payload.get("festival_name")),
        "payment_mode": payload.get("payment_mode") or "Cash",
        "devotee_name": devotee_name,
        "devotee_phone": devotee_phone,
        "devotee_prefix": devotee_prefix,
        "devotee_address": devotee_address,
        "devotee_city": devotee_city,
        "devotee_state": devotee_state,
        "devotee_pincode": devotee_pincode,
        "devotee": {
            "name": devotee_name,
            "name_prefix": devotee_prefix,
            "phone": devotee_phone,
            "email": str(payload.get("email") or "") or None,
            "address": devotee_address,
            "city": devotee_city,
            "state": devotee_state,
            "pincode": devotee_pincode,
        },
        "created_at": now,
    }

    donation["id"] = donation_id
    donation["receipt_number"] = await _next_receipt_number(
        tenant_id=tenant_id,
        app_key=app_key,
        receipt_kind="donation",
        receipt_date=now,
    )
    donation["receipt_pdf_url"] = f"/api/v1/donations/{donation_id}/receipt/pdf"

    raw_payment_account_id = _safe_optional_str(payload.get("bank_account_id") or payload.get("payment_account_id"))
    compliance_config = await get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    )
    compliance = classify_donation_compliance(
        payload,
        compliance_config,
        amount=Decimal(str(amount)),
        donation_type=str(donation.get("donation_type") or "cash"),
        payment_mode=payment_mode,
        donation_date=datetime.now(timezone.utc).date(),
        payment_account_id=raw_payment_account_id,
    )
    donation.update(compliance)

    col = get_collection("mandir_donations")
    try:
        await col.insert_one(donation)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save donation: {exc}") from exc

    donation_type = str(payload.get("donation_type") or "").strip().lower()

    # Valued donations and sponsorships must post into accounting; otherwise reports and TB diverge.
    if amount > 0:
        try:
            if donation_type == "in_kind":
                debit_account_id = await _resolve_mandir_in_kind_debit_account(
                    session,
                    tenant_id,
                    payload,
                    category,
                    app_key=app_key,
                )
                income_category = _mandir_in_kind_income_category(category)
            else:
                raw_account_id = payload.get("bank_account_id") or payload.get("payment_account_id")
                debit_account_id = await _resolve_mandir_payment_account_id(
                    session,
                    tenant_id,
                    raw_account_id,
                    payment_mode,
                )
                if not debit_account_id:
                    await col.delete_one({"donation_id": donation_id, "tenant_id": tenant_id, "app_key": app_key})
                    raise HTTPException(status_code=400, detail="No valid cash/bank account is configured for donation posting")
                income_category = _mandir_cash_income_category(category)

            income_acc_id = await _resolve_mandir_income_account(session, tenant_id, income_category)
            journal_payload = JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"{category} from {donation['devotee']['name']}",
                reference=donation["receipt_number"],
                lines=[
                    JournalLineIn(account_id=debit_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount))),
                ],
            )
            await post_journal_entry(
                session=session,
                app_key=app_key,
                tenant_id=tenant_id,
                created_by="mandir_compat_system",
                payload=journal_payload,
                idempotency_key=f"don_{donation_id}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            await col.delete_one({"donation_id": donation_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=500, detail=f"Failed to post donation journal: {exc}") from exc

    try:
        await _upsert_devotee_from_contribution(
            tenant_id,
            app_key,
            temple_id=temple_id,
            phone=devotee_phone,
            name_prefix=devotee_prefix,
            name=devotee_name,
            email=str(payload.get("email") or "") or None,
            address=devotee_address,
            city=devotee_city,
            state=devotee_state,
            pincode=devotee_pincode,
        )
    except Exception as exc:
        logger.warning("Donation saved but devotee upsert failed for tenant=%s phone=%s: %s", tenant_id, devotee_phone, exc)

    return _mandir_donation_view(donation)


@router.get("/donations/{donation_id}/receipt/pdf")
async def get_donation_receipt_pdf(
    donation_id: str,
    lang: str | None = Query(default=None, description="Override receipt language (kannada/hindi/tamil/telugu/malayalam)"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    col = get_collection("mandir_donations")
    donation = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "donation_id": donation_id})
    if donation is None:
        donation = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": donation_id})
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation_id_text = str(donation.get("donation_id") or donation.get("id") or donation_id).strip()
    donation["donation_id"] = donation_id_text
    donation["id"] = donation_id_text
    receipt_number = _receipt_number_for_donation(donation)
    donation["receipt_number"] = receipt_number
    donation["receipt_pdf_url"] = f"/api/v1/donations/{donation_id_text}/receipt/pdf"

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "donation_id": donation_id_text},
        {
            "$set": {
                "id": donation_id_text,
                "receipt_number": receipt_number,
                "receipt_pdf_url": donation["receipt_pdf_url"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=False,
    )

    temple_profile = await _resolve_temple_receipt_profile(tenant_id=tenant_id, app_key=app_key, lang=lang)

    try:
        pdf_bytes = _generate_donation_receipt_pdf_bytes(
            donation,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    safe_receipt = "".join(ch for ch in str(receipt_number) if ch.isalnum() or ch in ("-", "_")) or donation_id_text[:8]
    filename = f"donation_receipt_{safe_receipt}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/donations/{donation_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def cancel_donation_receipt(
    donation_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    return await _cancel_mandir_receipt_source(
        source_kind="donation",
        source_id=donation_id,
        collection_name="mandir_donations",
        id_field="donation_id",
        idempotency_prefix="don_",
        payload=payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )


@router.post("/donations/reconcile-posting", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def reconcile_donation_posting(
    limit: int = Query(default=500, ge=1, le=5000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """
    Backfill journal entries for legacy donation docs that were saved before posting guardrails.
    """
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    col = get_collection("mandir_donations")
    try:
        docs = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).limit(limit).to_list(length=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load donations for reconciliation: {exc}") from exc

    scanned = 0
    posted = 0
    already_posted = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for doc in docs:
        scanned += 1
        donation_id = str(doc.get("donation_id") or doc.get("id") or doc.get("_id") or "").strip()
        if not donation_id:
            skipped += 1
            continue

        idempotency_key = f"don_{donation_id}"
        exists_stmt = select(JournalEntry.id).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.idempotency_key == idempotency_key,
        )
        existing_journal_id = (await session.execute(exists_stmt)).scalar_one_or_none()
        if existing_journal_id is not None:
            already_posted += 1
            continue

        amount = _safe_float(doc.get("amount"), 0.0)
        if amount <= 0:
            skipped += 1
            continue

        payment_mode_raw = str(doc.get("payment_mode") or "Cash").strip().lower()
        payment_mode_for_account = "cash" if payment_mode_raw == "cash" else "bank"

        try:
            resolved_account_id = await _resolve_mandir_payment_account_id(
                session,
                tenant_id,
                doc.get("bank_account_id") or doc.get("payment_account_id"),
                payment_mode_for_account,
            )
            if not resolved_account_id:
                resolved_account_id = await _resolve_mandir_payment_account_id(session, tenant_id, None, payment_mode_for_account)
            if not resolved_account_id:
                raise ValueError("No valid cash/bank account is configured for donation posting")

            category = str(doc.get("category") or "General Donation")
            income_acc_id = await _resolve_mandir_income_account(session, tenant_id, "General Donations")
            devotee = doc.get("devotee") if isinstance(doc.get("devotee"), dict) else {}
            devotee_name = str(devotee.get("name") or doc.get("devotee_name") or "Devotee")

            created_raw = str(doc.get("created_at") or "").strip()
            entry_date = datetime.now(timezone.utc).date()
            if created_raw:
                try:
                    entry_date = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).date()
                except Exception:
                    pass

            journal_payload = JournalPostRequest(
                entry_date=entry_date,
                description=f"{category} from {devotee_name}",
                reference=f"DON-{donation_id[:8].upper()}",
                lines=[
                    JournalLineIn(account_id=resolved_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount))),
                ],
            )
            await post_journal_entry(
                session=session,
                tenant_id=tenant_id,
                created_by="mandir_reconcile",
                payload=journal_payload,
                idempotency_key=idempotency_key,
            )
            posted += 1
        except Exception as exc:
            errors.append({"donation_id": donation_id, "error": str(exc)})

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "app_key": app_key,
        "scanned": scanned,
        "posted": posted,
        "already_posted": already_posted,
        "skipped": skipped,
        "errors": errors[:25],
    }


@router.delete("/donations/cleanup", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cleanup_donation_entry(
    amount: float = Query(..., gt=0),
    devotee_phone: str = Query(..., min_length=6),
    payment_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    normalized_phone = _normalize_phone(devotee_phone)
    normalized_amount = _safe_float(amount, 0.0)
    normalized_mode = str(payment_mode or "").strip().lower() or None

    try:
        col = get_collection("mandir_donations")
        candidates = await col.find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "amount": normalized_amount,
                "devotee_phone": normalized_phone,
            }
        ).sort("created_at", -1).to_list(length=50)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to search donation entries: {exc}") from exc

    if normalized_mode:
        candidates = [
            row
            for row in candidates
            if str(row.get("payment_mode") or "").strip().lower() == normalized_mode
        ]

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="Donation entry not found for the provided amount and phone",
        )

    donation = candidates[0]
    donation_id = str(donation.get("donation_id") or "")

    try:
        await col.delete_one(
            {
                "donation_id": donation_id,
                "tenant_id": tenant_id,
                "app_key": app_key,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete donation entry: {exc}") from exc

    journal_deleted = False
    journal_status = "not_found"
    journal_idempotency_key = f"don_{donation_id}" if donation_id else None
    if journal_idempotency_key:
        try:
            journal_stmt = select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.idempotency_key == journal_idempotency_key,
            )
            journal_entry = (await session.execute(journal_stmt)).scalar_one_or_none()
            if journal_entry is not None:
                await session.delete(journal_entry)
                await session.commit()
                journal_deleted = True
                journal_status = "deleted"
        except Exception as exc:
            try:
                await session.rollback()
            except Exception:
                pass
            journal_status = f"delete_failed: {exc}"

    return {
        "status": "deleted",
        "matched_count": len(candidates),
        "donation_id": donation_id,
        "amount": normalized_amount,
        "devotee_phone": normalized_phone,
        "payment_mode": donation.get("payment_mode"),
        "journal_deleted": journal_deleted,
        "journal_status": journal_status,
    }


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Devotees (GET / POST / search by mobile / autofill)
# ROUTES : GET /devotees  POST .../devotees  GET .../search/by-mobile/{phone}  GET .../autofill/by-mobile/{phone}
# ════════════════════════════════════════════════════════════════════════

@router.get("/devotees")
@router.get("/devotees/")
async def list_devotees(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee list",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = _to_positive_int(x_temple_id)

    try:
        col = get_collection("mandir_devotees")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
        if temple_id is not None:
            query["temple_id"] = temple_id
        rows = await (
            col.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return [_sanitize_mongo_doc(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to list devotees for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []


@router.post("/devotees", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/devotees/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_devotee(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee create",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = _to_positive_int(x_temple_id)

    devotee = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "temple_id": temple_id,
        "name": str(payload.get("name") or payload.get("first_name") or "Unnamed Devotee"),
        "first_name": str(payload.get("first_name") or ""),
        "last_name": str(payload.get("last_name") or ""),
        "phone": _normalize_phone(payload.get("phone") or payload.get("mobile") or payload.get("devotee_phone")),
        "email": str(payload.get("email") or "") or None,
        "address": str(payload.get("address") or "") or None,
        "city": str(payload.get("city") or "") or None,
        "state": str(payload.get("state") or "") or None,
        "pincode": str(payload.get("pincode") or "") or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        col = get_collection("mandir_devotees")
        await col.insert_one(devotee)
    except Exception as exc:
        logger.error("Failed to insert devotee for tenant=%s: %s", tenant_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save devotee") from exc

    return _sanitize_mongo_doc(devotee)


@router.get("/devotees/search/by-mobile/{phone}")
async def search_devotee_by_mobile(
    phone: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee mobile search",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = _to_positive_int(x_temple_id)
    normalized = _normalize_phone(phone)

    if not normalized:
        return []

    try:
        col = get_collection("mandir_devotees")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized}
        if temple_id is not None:
            query["temple_id"] = temple_id
        docs = await col.find(query).limit(5).to_list(length=5)
        if docs:
            return [_sanitize_mongo_doc(doc) for doc in docs]
        fallback = await _find_devotee_by_phone(tenant_id, app_key, normalized, temple_id=temple_id)
        return [fallback] if fallback else []
    except Exception as exc:
        logger.error("Failed to search devotees by mobile for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []

@router.get("/devotees/autofill/by-mobile/{phone}")
async def autofill_devotee_by_mobile(
    phone: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="devotee mobile autofill",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = _to_positive_int(x_temple_id)
    normalized = _normalize_phone(phone)
    if not normalized:
        return {"found": False, "phone": normalized, "devotee": None}

    try:
        devotee = await _find_devotee_by_phone(tenant_id, app_key, normalized, temple_id=temple_id)
        if devotee is None:
            return {"found": False, "phone": normalized, "devotee": None}
        return {"found": True, "phone": normalized, "devotee": devotee}
    except Exception as exc:
        logger.error("Failed to autofill devotee by mobile for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return {"found": False, "phone": normalized, "devotee": None}



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Sevas (GET / POST / PUT / DELETE / import / lists / dropdown-options / payment-accounts)
# ROUTES : GET /sevas  POST .../sevas  PUT|DELETE .../sevas/{seva_id}  GET|POST .../import  GET .../priests|dropdown-options|payment-accounts
# ════════════════════════════════════════════════════════════════════════

@router.get("/sevas/")
@router.get("/sevas")
async def list_sevas(
    include_inactive: bool = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await _resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        _to_positive_int(x_temple_id),
    )
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    try:
        col = get_collection("mandir_sevas")
        query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
        if not include_inactive:
            query["is_active"] = True
        rows = await (
            col.find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        return [_serialize_seva_doc(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to list sevas for tenant=%s: %s", tenant_id, exc, exc_info=True)
        return []


@router.get("/sevas/{seva_id}/availability")
async def seva_date_availability(
    seva_id: str,
    booking_date: str = Query(..., description="Booking date in YYYY-MM-DD format"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva date availability check",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    parsed_date = _parse_booking_date(booking_date)
    if parsed_date is None:
        raise HTTPException(status_code=400, detail="Please enter a valid booking date.")

    seva_doc = await get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
    if not seva_doc:
        seva_doc = await get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id})
    if not seva_doc:
        raise HTTPException(status_code=404, detail="Seva not found")

    _validate_seva_booking_date(seva_doc, parsed_date)
    max_bookings, booked_count, slots_left = await _validate_seva_booking_capacity(
        seva_doc,
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=str(seva_id),
        booking_date=parsed_date,
    )
    return {
        "seva_id": str(seva_id),
        "booking_date": parsed_date.isoformat(),
        "available": slots_left is None or slots_left > 0,
        "max_bookings_per_day": max_bookings,
        "booked_count": booked_count,
        "slots_left": slots_left,
    }


@router.post("/sevas/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/sevas", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_seva(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await _resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        _to_positive_int(x_temple_id),
    )
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    item = _build_seva_item(payload, tenant_id=tenant_id, app_key=app_key)
    try:
        col = get_collection("mandir_sevas")
        await col.insert_one(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save seva: {exc}") from exc
    return _serialize_seva_doc(item)


@router.put("/sevas/{seva_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def update_seva(
    seva_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await _resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        _to_positive_int(x_temple_id),
    )
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    patch = _build_seva_patch(payload)
    patch.pop("id", None)
    patch.pop("_id", None)
    patch.pop("tenant_id", None)
    patch.pop("app_key", None)
    if not patch:
        raise HTTPException(status_code=400, detail="No updatable seva fields provided")
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    col = get_collection("mandir_sevas")
    try:
        await col.update_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": patch}, upsert=False)
        doc = await col.find_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update seva: {exc}") from exc
    if not doc:
        raise HTTPException(status_code=404, detail="Seva not found")
    return _serialize_seva_doc(doc)


@router.delete("/sevas/{seva_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def delete_seva(
    seva_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await _resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        _to_positive_int(x_temple_id),
    )
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    col = get_collection("mandir_sevas")
    await col.delete_one({"id": seva_id, "tenant_id": tenant_id, "app_key": app_key})
    return {"status": "deleted", "id": seva_id}


@router.get("/sevas/import/template")
async def seva_import_template(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, _to_positive_int(x_temple_id))
    resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    csv_body = _seva_import_template_csv()
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sevas_import_template.csv"},
    )


@router.post("/sevas/import", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def import_sevas(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_id = await _resolve_tenant_for_mandir_request(
        current_user,
        x_tenant_id,
        _to_positive_int(x_temple_id),
    )
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _assert_platform_can_write_tenant(current_user, tenant_id=tenant_id, app_key=app_key)

    filename = str(file.filename or "").strip().lower()
    if filename and not filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for seva import")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Try multiple encodings to handle files from Excel, Google Sheets, etc.
    # Excel on Windows often uses Windows-1252 (cp1252)
    # Google Sheets exports UTF-8, but some systems may use UTF-16
    encodings_to_try = [
        "utf-8-sig",  # UTF-8 with BOM
        "utf-8",      # UTF-8 without BOM
        "cp1252",     # Windows-1252 (Excel on Windows)
        "iso-8859-1", # Latin1 (fallback)
    ]

    # Check if file looks like UTF-16
    if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
        encodings_to_try.insert(0, "utf-16")

    text = None
    decode_errors = []

    for encoding in encodings_to_try:
        try:
            text = raw.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError) as e:
            decode_errors.append(f"{encoding}: {str(e)[:50]}")
            continue

    if text is None:
        error_detail = "Unable to decode CSV file. Tried encodings: " + ", ".join(encodings_to_try)
        raise HTTPException(status_code=400, detail=error_detail)

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV header row is missing")

    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for row_number, row in enumerate(reader, start=2):
        normalized = {
            str(key or "").strip(): (value.strip() if isinstance(value, str) else value)
            for key, value in row.items()
            if key is not None
        }
        if not any(str(value or "").strip() for value in normalized.values()):
            continue

        provided_name = normalized.get("name_english") or normalized.get("name") or normalized.get("seva_name")
        if not str(provided_name or "").strip():
            errors.append({"row": row_number, "error": "name_english is required"})
            continue

        amount_value = _safe_optional_float(normalized.get("amount"))
        if amount_value is None:
            errors.append({"row": row_number, "error": "amount is required"})
            continue
        if amount_value < 0:
            errors.append({"row": row_number, "error": "amount must be greater than or equal to 0"})
            continue

        payload = dict(normalized)
        payload["amount"] = amount_value
        items.append(_build_seva_item(payload, tenant_id=tenant_id, app_key=app_key))

    if items:
        col = get_collection("mandir_sevas")
        try:
            await col.insert_many(items)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to import sevas: {exc}") from exc

    return {
        "status": "ok",
        "inserted_count": len(items),
        "failed_count": len(errors),
        "errors": errors[:200],
    }


@router.get("/sevas/lists/priests")
async def seva_priests(_current_user: dict = Depends(get_current_user)):
    return [{"id": "p1", "name": "Temple Priest"}]


@router.get("/sevas/dropdown-options")
async def seva_dropdown_options(_current_user: dict = Depends(get_current_user)):
    return {
        "categories": ["General", "Special", "Festival"],
        "time_slots": ["06:00", "08:00", "10:00", "18:00"],
    }


@router.get("/sevas/payment-accounts")
async def seva_payment_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await _payment_accounts(tenant_id, app_key)



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Temples current (GET / PUT)
# ROUTES : GET /temples/current  PUT .../current
# ════════════════════════════════════════════════════════════════════════

@router.get("/temples/current")
async def get_current_temple(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    col = get_collection("mandir_temples")
    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key})
    if doc:
        return _sanitize_mongo_doc(doc)

    now = datetime.now(timezone.utc).isoformat()
    transient_temple_id = temple_id if temple_id and temple_id > 0 else None
    fallback = {
        "id": transient_temple_id,
        "temple_id": transient_temple_id,
        "tenant_id": tenant_id,
        "name": "Temple",
        "trust_name": "Temple Trust",
        "city": "Bengaluru",
        "state": "Karnataka",
        "platform_can_write": False,
        "is_placeholder": True,
        "is_active": True,
        "updated_at": now,
        "created_at": now,
    }
    return fallback


@router.put("/temples/current", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def update_current_temple(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await ensure_temple_numeric_id(tenant_id, app_key=app_key)
    col = get_collection("mandir_temples")
    now = datetime.now(timezone.utc).isoformat()
    update = {k: v for k, v in payload.items() if k not in {"id", "_id", "tenant_id", "temple_id"}}
    if "donation_categories" in payload:
        update["donation_categories"] = _normalize_public_donation_categories(
            payload.get("donation_categories"),
            fallback_to_default=False,
        )
    update["updated_at"] = now

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": {**update, "id": assigned_temple_id, "temple_id": assigned_temple_id},
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return await col.find_one({"tenant_id": tenant_id})

# --- Additional Mandir legacy compatibility endpoints to prevent 404s ---

def _ok(name: str, **extra: Any) -> dict[str, Any]:
    return {"status": "ok", "endpoint": name, **extra}



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Accounts / COA (GET list / GET hierarchy / PUT / import legacy / initialize default)
# ROUTES : GET /accounts  GET .../hierarchy  PUT .../accounts/{account_id}  POST .../import-legacy  POST .../initialize-default
# ════════════════════════════════════════════════════════════════════════

@router.get("/accounts")
async def mandir_accounts_list(_current_user: dict = Depends(get_current_user)):
    tenant_id = resolve_tenant_id(_current_user, None)
    app_key = resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    await _ensure_default_mandir_accounts(tenant_id, app_key)
    accounts = get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=500)
    unique_docs = _dedupe_mandir_account_docs(docs)
    return [_mandir_account_view(doc) for doc in unique_docs]


@router.get("/accounts/hierarchy")
async def mandir_accounts_hierarchy(_current_user: dict = Depends(get_current_user)):
    tenant_id = resolve_tenant_id(_current_user, None)
    app_key = resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    await _ensure_default_mandir_accounts(tenant_id, app_key)
    accounts = get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=500)
    unique_docs = _dedupe_mandir_account_docs(docs)
    return [_mandir_account_view(doc) for doc in unique_docs]


@router.put("/accounts/{account_id}", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_update(
    account_id: str,
    payload: dict[str, Any],
    reason: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(_current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())

    reason_text = str(reason or "").strip()
    if not reason_text:
        raise HTTPException(status_code=400, detail="Reason is required for audit trail")

    accounts = get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key}).to_list(length=1000)

    raw_identifier = str(account_id or "").strip()
    normalized_identifier = _normalize_mandir_account_code(raw_identifier)

    def _matches_identifier(doc: dict[str, Any]) -> bool:
        doc_id = str(doc.get("account_id") or "").strip()
        doc_code = str(doc.get("account_code") or doc.get("account_id") or "").strip()
        normalized_doc_code = _normalize_mandir_account_code(
            doc_code,
            account_name=doc.get("account_name") or doc.get("name"),
        )
        return raw_identifier in {doc_id, doc_code, normalized_doc_code} or normalized_identifier in {doc_id, doc_code, normalized_doc_code}

    target_doc = next((doc for doc in docs if _matches_identifier(doc)), None)
    if target_doc is None:
        raise HTTPException(status_code=404, detail="Account not found")

    updated_name = str(payload.get("account_name") or target_doc.get("account_name") or target_doc.get("name") or "").strip()
    if not updated_name:
        raise HTTPException(status_code=400, detail="Account name is required")

    now = datetime.now(timezone.utc).isoformat()
    account_code = _normalize_mandir_account_code(
        target_doc.get("account_code") or target_doc.get("account_id") or raw_identifier,
        account_name=target_doc.get("account_name") or target_doc.get("name"),
    )

    update_doc: dict[str, Any] = {
        "account_name": updated_name,
        "name": updated_name,
        "updated_at": now,
        "updated_by": str(_current_user.get("sub") or _current_user.get("email") or "system"),
        "update_reason": reason_text,
    }

    if "account_name_kannada" in payload:
        update_doc["account_name_kannada"] = _safe_optional_str(payload.get("account_name_kannada"))
    if "description" in payload:
        update_doc["description"] = _safe_optional_str(payload.get("description"))

    update_query = {"tenant_id": tenant_id, "app_key": app_key}
    if account_code:
        update_query["account_code"] = account_code
    else:
        update_query["account_id"] = target_doc.get("account_id")

    await accounts.update_one(update_query, {"$set": update_doc}, upsert=False)

    if account_code:
        try:
            account_stmt = select(Account).where(
                Account.tenant_id == tenant_id,
                Account.code == account_code,
            )
            sql_account = (await session.execute(account_stmt)).scalar_one_or_none()
            if sql_account is not None and str(sql_account.name or "").strip() != updated_name:
                sql_account.name = updated_name
                await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.warning(
                "Failed to sync SQL account name for tenant %s code %s: %s",
                tenant_id,
                account_code,
                exc,
            )

    try:
        old_value = {
            "account_name": target_doc.get("account_name") or target_doc.get("name"),
            "account_name_kannada": target_doc.get("account_name_kannada"),
            "description": target_doc.get("description"),
        }
        new_value = {
            "account_name": update_doc.get("account_name"),
            "account_name_kannada": update_doc.get("account_name_kannada", old_value.get("account_name_kannada")),
            "description": update_doc.get("description", old_value.get("description")),
            "reason": reason_text,
        }
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=str(_current_user.get("sub") or _current_user.get("email") or "system"),
            product="mandirmitra",
            action="coa_account_updated",
            entity_type="accounting_account",
            entity_id=str(account_code or target_doc.get("account_id") or raw_identifier),
            old_value=old_value,
            new_value=new_value,
        )
    except Exception as exc:
        logger.warning("Failed to write COA update audit log for tenant %s: %s", tenant_id, exc)

    updated_doc = await accounts.find_one(update_query)
    if not updated_doc:
        updated_doc = {**target_doc, **update_doc, "account_code": account_code}

    return _mandir_account_view(updated_doc)

@router.post("/accounts/import-legacy", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_import_legacy(
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
):
    tenant_id = resolve_tenant_id(_current_user, None)
    app_key = resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())

    seed_rows = payload.get("items") if isinstance(payload, dict) else None
    if seed_rows is None:
        seed_rows = _load_mandir_legacy_accounts()

    if not isinstance(seed_rows, list) or not seed_rows:
        raise HTTPException(status_code=400, detail="Legacy COA payload is empty")

    normalized_seed_rows = [row for row in seed_rows if isinstance(row, dict)]
    mongo_result = await _upsert_mandir_account_docs(tenant_id, app_key, normalized_seed_rows)
    sql_result = await _sync_mandir_sql_accounts_from_seed(
        session,
        tenant_id=tenant_id,
        seed_rows=normalized_seed_rows,
    )
    await _normalize_mandir_income_accounts(session, tenant_id)
    return _ok(
        "accounts/import-legacy",
        message="Legacy accounts imported",
        created=mongo_result["created"],
        reactivated=mongo_result["reactivated"],
        updated=mongo_result["updated"],
        total=mongo_result["total"],
        sql_created=sql_result["created"],
        sql_updated=sql_result["updated"],
        sql_total=sql_result["total"],
    )


@router.post("/accounts/initialize-default", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_initialize_default(
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
):
    tenant_id = resolve_tenant_id(_current_user, None)
    app_key = resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    seed_rows = _mandir_seed_accounts()
    mongo_result = await _upsert_mandir_account_docs(tenant_id, app_key, seed_rows)
    sql_result = await _sync_mandir_sql_accounts_from_seed(
        session,
        tenant_id=tenant_id,
        seed_rows=seed_rows,
    )
    await _normalize_mandir_income_accounts(session, tenant_id)
    return _ok(
        "accounts/initialize-default",
        message="Default accounts initialized",
        created=mongo_result["created"],
        reactivated=mongo_result["reactivated"],
        updated=mongo_result["updated"],
        sql_created=sql_result["created"],
        sql_updated=sql_result["updated"],
        sql_total=sql_result["total"],
    )




# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Assets, backup, bank accounts
# ROUTES : GET /assets  GET .../cwip|reports/summary  POST .../revaluation  GET|POST /backup-restore  GET|POST /bank-accounts
# ════════════════════════════════════════════════════════════════════════

@router.get("/assets")
async def mandir_assets(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/assets/cwip")
async def mandir_assets_cwip(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/assets/reports/summary")
async def mandir_assets_report_summary(_current_user: dict = Depends(get_current_user)):
    return {"summary": {}}


@router.post("/assets/revaluation", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_assets_revaluation(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("assets/revaluation")


@router.get("/backup-restore/status")
async def mandir_backup_status(_current_user: dict = Depends(get_current_user)):
    return {"backup_enabled": False, "last_backup_at": None, "status": "idle"}


@router.post("/backup-restore/backup", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_backup_now(_current_user: dict = Depends(get_current_user)):
    return _ok("backup-restore/backup")


@router.get("/bank-accounts")
async def mandir_bank_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    docs = await get_collection("mandir_bank_accounts").find({"tenant_id": tenant_id, "app_key": app_key}).sort("updated_at", -1).to_list(length=200)
    return [_sanitize_mongo_doc(doc) for doc in docs]


@router.post("/bank-accounts", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
@router.post("/bank-accounts/", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_create_bank_account(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    account_id = str(uuid4())
    doc = {
        "id": account_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        **{k: v for k, v in payload.items() if k not in {"id", "_id", "tenant_id", "app_key"}},
        "created_at": now,
        "updated_at": now,
    }
    await get_collection("mandir_bank_accounts").insert_one(doc)
    return _sanitize_mongo_doc(doc)


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Bank reconciliation (accounts / match / reconcile / statements / import / summary / entries)
# ROUTES : GET /bank-reconciliation/accounts  POST .../match|reconcile|statements/import  GET .../statements  GET .../statements/{id}/summary|entries|unmatched-book-entries
# ════════════════════════════════════════════════════════════════════════

@router.get("/bank-reconciliation/accounts")
async def mandir_bank_rec_accounts(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)

    sql_accounts = await list_accounts(session, app_key=app_key, tenant_id=tenant_id)
    bank_accounts = []
    cash_bank_accounts = []

    for account in sql_accounts:
        if not bool(getattr(account, "is_cash_bank", False)):
            continue

        name = str(getattr(account, "name", "") or "").lower()
        code = str(getattr(account, "code", "") or "").strip()
        row = {
            "id": int(account.id),
            "account_id": int(account.id),
            "code": code,
            "name": str(getattr(account, "name", "") or "").strip(),
            "type": str(getattr(account, "type", "") or "").strip(),
            "account_code": code,
            "account_name": str(getattr(account, "name", "") or "").strip(),
            "account_type": str(getattr(account, "type", "") or "").strip(),
            "is_cash_bank": True,
            "cash_bank_nature": "bank" if "bank" in name else "cash",
        }
        cash_bank_accounts.append(row)
        if "bank" in name or code == "12001":
            row["cash_bank_nature"] = "bank"
            bank_accounts.append(row)

    return bank_accounts or cash_bank_accounts


@router.post("/bank-reconciliation/match", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_match(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("bank-reconciliation/match")


@router.post("/bank-reconciliation/reconcile", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_reconcile(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("bank-reconciliation/reconcile")


@router.get("/bank-reconciliation/statements")
async def mandir_bank_rec_statements(_current_user: dict = Depends(get_current_user)):
    return []


@router.post("/bank-reconciliation/statements/import", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_bank_rec_statements_import(
    file: UploadFile | None = File(default=None),
    account_id: str | None = Query(default=None),
    statement_date: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    statement_id = str(uuid4())
    filename = str((file.filename if file else "") or "").strip() or "statement.csv"
    doc = {
        "id": statement_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "account_id": account_id,
        "statement_date": statement_date,
        "filename": filename,
        "status": "imported",
        "entries_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection("mandir_bank_statements").insert_one(doc)
    return _sanitize_mongo_doc(doc)


@router.get("/bank-reconciliation/statements/{statement_id}/summary")
async def mandir_bank_rec_statement_summary(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    statement = await get_collection("mandir_bank_statements").find_one({"id": statement_id, "tenant_id": tenant_id, "app_key": app_key})
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    return {
        "statement_id": statement_id,
        "status": str(statement.get("status") or "imported"),
        "total_entries": int(statement.get("entries_count") or 0),
        "matched_entries": 0,
        "unmatched_entries": int(statement.get("entries_count") or 0),
        "closing_balance": 0.0,
        "book_balance": 0.0,
        "difference": 0.0,
    }


@router.get("/bank-reconciliation/statements/{statement_id}/entries")
async def mandir_bank_rec_statement_entries(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    rows = await get_collection("mandir_bank_statement_entries").find(
        {"statement_id": statement_id, "tenant_id": tenant_id, "app_key": app_key}
    ).sort("entry_date", 1).to_list(length=2000)
    return [_sanitize_mongo_doc(row) for row in rows]


@router.get("/bank-reconciliation/statements/{statement_id}/unmatched-book-entries")
async def mandir_bank_rec_unmatched_book_entries(
    statement_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    rows = await get_collection("mandir_bank_unmatched_entries").find(
        {"statement_id": statement_id, "tenant_id": tenant_id, "app_key": app_key}
    ).sort("entry_date", 1).to_list(length=2000)
    return [_sanitize_mongo_doc(row) for row in rows]


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Sacred events, financial closing, auth (forgot / reset), HR, hundi
# ROUTES : GET /dashboard/sacred-events  POST /financial-closing/close-month|close-year  GET .../closing-summary|financial-years|period-closings  POST /forgot-password|reset-password  GET /hr/employees|attendance  GET /hundi/masters|openings
# ════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/sacred-events/nakshatra/{nakshatra}")
async def mandir_nakshatra_dates(nakshatra: str, limit: int = Query(default=8, ge=1, le=30), _current_user: dict = Depends(get_current_user)):
    today = date.today()
    out = []
    for i in range(limit):
        d = today.replace(day=min(28, today.day))
        out.append({"event_date": str(d), "weekday": d.strftime("%A"), "days_away": i, "is_today": i == 0})
    return {"nakshatra": nakshatra, "next_occurrences": out}


@router.post("/financial-closing/close-month", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_close_month(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("financial-closing/close-month")


@router.post("/financial-closing/close-year", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_close_year(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("financial-closing/close-year")


@router.get("/financial-closing/closing-summary")
async def mandir_closing_summary(_current_user: dict = Depends(get_current_user)):
    return {"summary": {}}


@router.get("/financial-closing/financial-years")
async def mandir_financial_years(_current_user: dict = Depends(get_current_user)):
    y = datetime.now(timezone.utc).year
    return [{"financial_year": f"{y}-{y+1}", "is_current": True}]


@router.get("/financial-closing/period-closings")
async def mandir_period_closings(_current_user: dict = Depends(get_current_user)):
    return []


@router.post("/forgot-password")
async def mandir_forgot_password(_payload: dict[str, Any]):
    return _ok("forgot-password")


@router.post("/reset-password")
async def mandir_reset_password(_payload: dict[str, Any]):
    return _ok("reset-password")


@router.get("/hr/employees")
async def mandir_hr_employees(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/hr/attendance/monthly")
async def mandir_hr_attendance_monthly(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/hundi/masters")
async def mandir_hundi_masters(_current_user: dict = Depends(get_current_user)):
    return []


@router.get("/hundi/openings")
async def mandir_hundi_openings(_current_user: dict = Depends(get_current_user)):
    return []



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Inventory (items CRUD / stock-balances / summary)
# ROUTES : GET|POST /inventory/items  PUT|DELETE .../items/{item_id}  GET .../stock-balances  GET .../summary
# ════════════════════════════════════════════════════════════════════════

@router.get("/inventory/items")
@router.get("/inventory/items/")
async def mandir_inventory_items(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    docs = await get_collection("mandir_inventory_items").find({"tenant_id": tenant_id, "app_key": app_key}).sort("updated_at", -1).to_list(length=1000)
    return [_sanitize_mongo_doc(doc) for doc in docs]


@router.post("/inventory/items", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/inventory/items/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_create_inventory_item(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid4())
    item = {
        "id": item_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip() or "Inventory Item",
        "category": str(payload.get("category") or "OTHER").strip() or "OTHER",
        "unit": str(payload.get("unit") or "PIECE").strip() or "PIECE",
        "reorder_level": int(payload.get("reorder_level") or 0),
        "reorder_quantity": int(payload.get("reorder_quantity") or 0),
        "description": str(payload.get("description") or "").strip(),
        "is_active": bool(payload.get("is_active", True)),
        "created_at": now,
        "updated_at": now,
    }
    await get_collection("mandir_inventory_items").insert_one(item)
    return _sanitize_mongo_doc(item)


@router.put("/inventory/items/{item_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_update_inventory_item(
    item_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    allowed = {"code", "name", "category", "unit", "reorder_level", "reorder_quantity", "description", "is_active"}
    patch = {k: payload.get(k) for k in allowed if k in payload}
    if "reorder_level" in patch:
        patch["reorder_level"] = int(patch["reorder_level"] or 0)
    if "reorder_quantity" in patch:
        patch["reorder_quantity"] = int(patch["reorder_quantity"] or 0)
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    await get_collection("mandir_inventory_items").update_one(
        {"id": item_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )
    row = await get_collection("mandir_inventory_items").find_one({"id": item_id, "tenant_id": tenant_id, "app_key": app_key})
    if row is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return _sanitize_mongo_doc(row)


@router.delete("/inventory/items/{item_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_delete_inventory_item(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    await get_collection("mandir_inventory_items").update_one(
        {"id": item_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": False, "updated_at": now}},
        upsert=False,
    )
    return {"status": "deactivated", "id": item_id}


@router.get("/inventory/stock-balances")
@router.get("/inventory/stock-balances/")
async def mandir_inventory_stock_balances(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    items = await get_collection("mandir_inventory_items").find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=1000)
    rows = []
    for item in items:
        reorder_level = int(item.get("reorder_level") or 0)
        on_hand_qty = float(item.get("on_hand_qty") or 0.0)
        rows.append(
            {
                "item_id": str(item.get("id") or ""),
                "item_code": str(item.get("code") or ""),
                "item_name": str(item.get("name") or ""),
                "unit": str(item.get("unit") or "PIECE"),
                "on_hand_qty": on_hand_qty,
                "reorder_level": reorder_level,
                "reorder_required": bool(reorder_level > 0 and on_hand_qty <= reorder_level),
            }
        )
    return rows


@router.get("/inventory/summary")
@router.get("/inventory/summary/")
async def mandir_inventory_summary(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    items = await get_collection("mandir_inventory_items").find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=1000)
    low_stock = 0
    for item in items:
        reorder_level = int(item.get("reorder_level") or 0)
        on_hand_qty = float(item.get("on_hand_qty") or 0.0)
        if reorder_level > 0 and on_hand_qty <= reorder_level:
            low_stock += 1
    return {
        "totalItems": len(items),
        "lowStockItems": low_stock,
        "totalValue": 0.0,
        "summary": {
            "total_items": len(items),
            "low_stock_items": low_stock,
        },
    }


def _parse_journal_entry_date(value: Any) -> date:
    if isinstance(value, date):
        return value

    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).date()

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return date.fromisoformat(raw[:10])
        except Exception:
            return datetime.now(timezone.utc).date()


async def _resolve_sql_account_for_journal_line(
    session: AsyncSession,
    *,
    tenant_id: str,
    raw_account_id: Any,
) -> Account | None:
    raw_value = str(raw_account_id or "").strip()
    if not raw_value:
        return None

    maybe_id = _safe_optional_int(raw_value)
    if maybe_id is not None:
        by_id_stmt = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.id == maybe_id,
        )
        by_id = (await session.execute(by_id_stmt)).scalar_one_or_none()
        if by_id is not None:
            return by_id

    code_candidate = raw_value.split(" - ", 1)[0].strip()
    normalized_code = _normalize_mandir_account_code(code_candidate)
    if normalized_code:
        by_code_stmt = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.code == normalized_code,
        )
        by_code = (await session.execute(by_code_stmt)).scalar_one_or_none()
        if by_code is not None:
            return by_code

    return None


async def _normalize_mandir_journal_lines(
    session: AsyncSession,
    *,
    tenant_id: str,
    raw_lines: Any,
) -> tuple[list[dict[str, Any]], Decimal, Decimal]:
    if not isinstance(raw_lines, list) or len(raw_lines) < 2:
        raise HTTPException(status_code=400, detail="At least two journal lines are required")

    normalized_lines: list[dict[str, Any]] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for index, line in enumerate(raw_lines, start=1):
        if not isinstance(line, dict):
            raise HTTPException(status_code=400, detail=f"Journal line #{index} is invalid")

        account_ref = line.get("account_id")
        account = await _resolve_sql_account_for_journal_line(
            session,
            tenant_id=tenant_id,
            raw_account_id=account_ref,
        )
        if account is None:
            raise HTTPException(status_code=400, detail=f"Invalid account on journal line #{index}")

        try:
            debit_amount = Decimal(str(line.get("debit_amount") or 0)).quantize(Decimal("0.01"))
            credit_amount = Decimal(str(line.get("credit_amount") or 0)).quantize(Decimal("0.01"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid amount on journal line #{index}") from exc

        if debit_amount < 0 or credit_amount < 0:
            raise HTTPException(status_code=400, detail=f"Amounts cannot be negative on line #{index}")
        if debit_amount == 0 and credit_amount == 0:
            raise HTTPException(status_code=400, detail=f"Either debit or credit is required on line #{index}")
        if debit_amount > 0 and credit_amount > 0:
            raise HTTPException(status_code=400, detail=f"Line #{index} cannot have both debit and credit")

        total_debit += debit_amount
        total_credit += credit_amount

        reference_account_id = _safe_optional_int(account_ref)
        if reference_account_id is None:
            reference_account_id = _safe_optional_int(str(account.code or "").strip()) or int(account.id)

        normalized_lines.append(
            {
                "account_id": reference_account_id,
                "account_code": str(account.code or "").strip(),
                "account_name": str(account.name or "").strip(),
                "ledger_account_id": int(account.id),
                "debit_amount": float(debit_amount),
                "credit_amount": float(credit_amount),
                "description": str(line.get("description") or "").strip(),
            }
        )

    if total_debit <= 0 or total_credit <= 0:
        raise HTTPException(status_code=400, detail="Total debit and credit must be greater than zero")
    if total_debit != total_credit:
        raise HTTPException(status_code=400, detail="Total debit and credit must be equal")

    return normalized_lines, total_debit, total_credit


async def _validate_mandir_journal_cash_balance(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    normalized_lines: list[dict[str, Any]],
) -> None:
    accounting_lines: list[tuple[int, Decimal, Decimal]] = []
    for line in normalized_lines:
        ledger_account_id = _safe_optional_int(line.get("ledger_account_id"))
        if ledger_account_id is None:
            continue
        accounting_lines.append(
            (
                ledger_account_id,
                Decimal(str(line.get("debit_amount") or 0)).quantize(Decimal("0.01")),
                Decimal(str(line.get("credit_amount") or 0)).quantize(Decimal("0.01")),
            )
        )

    try:
        await validate_cash_balance_for_journal_lines(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            normalized_lines=accounting_lines,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _mandir_journal_entry_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    row["entry_number"] = str(row.get("entry_number") or f"JE-{str(row.get('id') or '')[:8].upper()}")
    row["entry_date"] = str(row.get("entry_date") or datetime.now(timezone.utc).date().isoformat())[:10]
    row["narration"] = str(row.get("narration") or row.get("description") or "").strip()
    row["reference_type"] = str(row.get("reference_type") or "").strip().lower() or None
    row["reference_id"] = _safe_optional_int(row.get("reference_id"))
    row["status"] = str(row.get("status") or "draft").strip().lower() or "draft"
    row["total_debit"] = _safe_float(row.get("total_debit"), 0.0)
    row["total_credit"] = _safe_float(row.get("total_credit"), 0.0)
    row["total_amount"] = _safe_float(
        row.get("total_amount"),
        _safe_float(row.get("total_debit"), 0.0),
    )

    journal_lines: list[dict[str, Any]] = []
    for line in row.get("journal_lines") or []:
        if not isinstance(line, dict):
            continue
        journal_lines.append(
            {
                "account_id": _safe_optional_int(line.get("account_id")),
                "account_code": str(line.get("account_code") or "").strip(),
                "account_name": str(line.get("account_name") or "").strip(),
                "debit_amount": _safe_float(line.get("debit_amount"), 0.0),
                "credit_amount": _safe_float(line.get("credit_amount"), 0.0),
                "description": str(line.get("description") or "").strip(),
            }
        )
    row["journal_lines"] = journal_lines
    return row



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Journal entries (GET / POST / drilldown / financial reports / day-book / cash-book / bank-book)
# ROUTES : GET /journal-entries  POST .../journal-entries  GET .../reports/drilldown|balance-sheet|accounts-receivable|payable|ledger|category-income|top-donors|day-book|cash-book|bank-book
# ════════════════════════════════════════════════════════════════════════

@router.get("/journal-entries")
@router.get("/journal-entries/")
async def mandir_journal_entries(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if reference_type:
        query["reference_type"] = str(reference_type).strip().lower()

    try:
        docs = await get_collection("mandir_journal_entries").find(query).sort("updated_at", -1).limit(limit).to_list(length=limit)
    except Exception:
        docs = []

    rows: list[dict[str, Any]] = []
    for doc in docs:
        view = _mandir_journal_entry_view(doc)
        entry_date = _parse_journal_entry_date(view.get("entry_date"))
        if from_date and entry_date < from_date:
            continue
        if to_date and entry_date > to_date:
            continue
        rows.append(view)

    if rows:
        return rows

    # Backward-compatible fallback: expose posted SQL journals in the same list shape.
    report = await journal_entries_report(session, tenant_id=tenant_id, limit=limit)
    fallback_rows: list[dict[str, Any]] = []
    for item in report.get("items", []):
        entry_date = _parse_journal_entry_date(item.get("entry_date"))
        if from_date and entry_date < from_date:
            continue
        if to_date and entry_date > to_date:
            continue
        fallback_reference_type = str(item.get("reference") or "").split("-", 1)[0].lower() or None
        if reference_type and fallback_reference_type != str(reference_type).strip().lower():
            continue

        fallback_rows.append(
            {
                "id": int(item.get("id")),
                "entry_number": f"JE-{item.get('id')}",
                "entry_date": entry_date.isoformat(),
                "narration": str(item.get("description") or "").strip(),
                "reference_type": fallback_reference_type,
                "reference_id": None,
                "status": "posted",
                "total_amount": _safe_float(item.get("total_debit"), 0.0),
                "total_debit": _safe_float(item.get("total_debit"), 0.0),
                "total_credit": _safe_float(item.get("total_credit"), 0.0),
                "journal_lines": [],
            }
        )

    return fallback_rows


@router.post("/journal-entries", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/journal-entries/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_create_journal_entry(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry creation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    normalized_lines, total_debit, total_credit = await _normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=payload.get("journal_lines"),
    )
    await _validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    entry_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    entry_date = _parse_journal_entry_date(payload.get("entry_date"))
    entry_number = await _next_journal_entry_number(tenant_id=tenant_id, app_key=app_key)

    entry_doc = {
        "id": entry_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "entry_number": entry_number,
        "entry_date": entry_date.isoformat(),
        "narration": str(payload.get("narration") or "").strip(),
        "reference_type": str(payload.get("reference_type") or "expense").strip().lower(),
        "reference_id": _safe_optional_int(payload.get("reference_id")),
        "status": "draft",
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "idempotency_key": f"man_je_{entry_id}",
        "created_by": str(current_user.get("sub") or current_user.get("email") or "system"),
        "created_at": now,
        "updated_at": now,
    }

    await get_collection("mandir_journal_entries").insert_one(entry_doc)
    return _mandir_journal_entry_view(entry_doc)


@router.put("/journal-entries/{entry_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_update_journal_entry(
    entry_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry update",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    collection = get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if str(existing.get("status") or "").lower() != "draft":
        raise HTTPException(status_code=400, detail="Only draft entries can be edited")

    normalized_lines, total_debit, total_credit = await _normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=payload.get("journal_lines"),
    )
    await _validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    patch = {
        "entry_date": _parse_journal_entry_date(payload.get("entry_date") or existing.get("entry_date")).isoformat(),
        "narration": str(payload.get("narration") or "").strip(),
        "reference_type": str(payload.get("reference_type") or existing.get("reference_type") or "expense").strip().lower(),
        "reference_id": _safe_optional_int(payload.get("reference_id")),
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    updated = {**existing, **patch}
    return _mandir_journal_entry_view(updated)


@router.post("/journal-entries/{entry_id}/post", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_post_journal_entry(
    entry_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="journal entry posting",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    collection = get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if str(existing.get("status") or "").lower() == "posted":
        return _mandir_journal_entry_view(existing)

    if str(existing.get("status") or "").lower() in {"cancelled", "reversed"}:
        raise HTTPException(status_code=400, detail="Cancelled/reversed entries cannot be posted")

    normalized_lines, total_debit, total_credit = await _normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=existing.get("journal_lines"),
    )
    await _validate_mandir_journal_cash_balance(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        normalized_lines=normalized_lines,
    )

    post_lines: list[JournalLineIn] = []
    for line in normalized_lines:
        ledger_account_id = _safe_optional_int(line.get("ledger_account_id"))
        if not ledger_account_id:
            account = await _resolve_sql_account_for_journal_line(
                session,
                tenant_id=tenant_id,
                raw_account_id=line.get("account_id"),
            )
            if account is None:
                raise HTTPException(status_code=400, detail="Unable to resolve account while posting")
            ledger_account_id = int(account.id)

        post_lines.append(
            JournalLineIn(
                account_id=ledger_account_id,
                debit=Decimal(str(line.get("debit_amount") or 0)),
                credit=Decimal(str(line.get("credit_amount") or 0)),
            )
        )

    journal_payload = JournalPostRequest(
        entry_date=_parse_journal_entry_date(existing.get("entry_date")),
        description=str(existing.get("narration") or "").strip(),
        reference=f"{str(existing.get('reference_type') or 'expense').upper()}-{str(existing.get('entry_number') or '')}",
        lines=post_lines,
    )

    try:
        posted_entry, _created = await post_journal_entry(
            session=session,
            tenant_id=tenant_id,
            created_by=str(current_user.get("sub") or current_user.get("email") or "system"),
            payload=journal_payload,
            idempotency_key=str(existing.get("idempotency_key") or f"man_je_{entry_id}"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to post journal entry: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_lines": normalized_lines,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "total_amount": float(total_debit),
        "posted_journal_id": int(posted_entry.id),
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    return _mandir_journal_entry_view({**existing, **patch})


@router.post("/journal-entries/{entry_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_cancel_journal_entry(
    entry_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva booking",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    collection = get_collection("mandir_journal_entries")
    existing = await collection.find_one({"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    current_status = str(existing.get("status") or "").lower()
    if current_status in {"cancelled", "reversed"}:
        return _mandir_journal_entry_view(existing)

    cancellation_reason = str((payload or {}).get("cancellation_reason") or "").strip() or "Reversal entry"

    if current_status == "draft":
        patch = {
            "status": "cancelled",
            "cancellation_reason": cancellation_reason,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await collection.update_one(
            {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
            {"$set": patch},
            upsert=False,
        )
        return _mandir_journal_entry_view({**existing, **patch})

    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)
    normalized_lines, _total_debit, _total_credit = await _normalize_mandir_journal_lines(
        session,
        tenant_id=tenant_id,
        raw_lines=existing.get("journal_lines"),
    )

    reversal_lines: list[JournalLineIn] = []
    for line in normalized_lines:
        ledger_account_id = _safe_optional_int(line.get("ledger_account_id"))
        if not ledger_account_id:
            account = await _resolve_sql_account_for_journal_line(
                session,
                tenant_id=tenant_id,
                raw_account_id=line.get("account_id"),
            )
            if account is None:
                raise HTTPException(status_code=400, detail="Unable to resolve account while reversing")
            ledger_account_id = int(account.id)

        reversal_lines.append(
            JournalLineIn(
                account_id=ledger_account_id,
                debit=Decimal(str(line.get("credit_amount") or 0)),
                credit=Decimal(str(line.get("debit_amount") or 0)),
            )
        )

    reversal_payload = JournalPostRequest(
        entry_date=datetime.now(timezone.utc).date(),
        description=f"Reversal of {existing.get('entry_number')}: {cancellation_reason}",
        reference=f"REV-{existing.get('entry_number')}",
        lines=reversal_lines,
    )

    try:
        reversal_entry, _created = await post_journal_entry(
            session=session,
            tenant_id=tenant_id,
            created_by=str(current_user.get("sub") or current_user.get("email") or "system"),
            payload=reversal_payload,
            idempotency_key=f"{str(existing.get('idempotency_key') or f'man_je_{entry_id}')}_rev",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reverse journal entry: {exc}") from exc

    patch = {
        "status": "reversed",
        "cancellation_reason": cancellation_reason,
        "reversed_at": datetime.now(timezone.utc).isoformat(),
        "reversal_journal_id": int(reversal_entry.id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await collection.update_one(
        {"id": str(entry_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    return _mandir_journal_entry_view({**existing, **patch})


@router.get("/journal-entries/reports/trial-balance")
async def mandir_journal_trial_balance(
    as_of: date,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    try:
        return await trial_balance_report(session, tenant_id=tenant_id, as_of=as_of)
    except (ConnectionRefusedError, OSError, SQLAlchemyError) as exc:
        logger.exception("Trial balance query failed", extra={"tenant_id": tenant_id, "as_of": as_of.isoformat()})
        raise HTTPException(status_code=503, detail="Accounting database unavailable. Please retry shortly.") from exc


@router.get("/journal-entries/reports/profit-loss")
async def mandir_journal_profit_loss(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await profit_loss_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/income-expenditure")
async def mandir_journal_income_expenditure(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await profit_loss_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/receipts-payments")
async def mandir_journal_receipts_payments(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await receipts_payments_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/drilldown")
async def mandir_journal_drilldown(
    from_date: date = Query(...),
    to_date: date = Query(...),
    level: str = Query(default="month", pattern="^(month|week|day|voucher)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    week_start: date | None = Query(default=None),
    day: date | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await get_journal_drilldown(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id="primary",
        from_date=from_date,
        to_date=to_date,
        level=level,
        month=month,
        week_start=week_start,
        day=day,
        limit=limit,
    )


@router.get("/journal-entries/reports/balance-sheet")
async def mandir_journal_balance_sheet(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await balance_sheet_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/accounts-receivable")
async def mandir_journal_accounts_receivable(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await accounts_receivable_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/accounts-payable")
async def mandir_journal_accounts_payable(
    as_of: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await accounts_payable_report(session, tenant_id=tenant_id, as_of=as_of)


@router.get("/journal-entries/reports/ledger/{account_id}")
async def mandir_journal_ledger(
    account_id: int,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await ledger_report(session, tenant_id=tenant_id, account_id=account_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/category-income")
async def mandir_journal_category_income(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await category_income_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/top-donors")
async def mandir_journal_top_donors(
    from_date: date = Query(...),
    to_date: date = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await top_donors_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date, limit=limit)


@router.get("/journal-entries/reports/day-book")
async def mandir_journal_day_book(
    date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await day_book_report(session, tenant_id=tenant_id, date_value=date)


@router.get("/journal-entries/reports/cash-book")
async def mandir_journal_cash_book(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await cash_book_report(session, tenant_id=tenant_id, from_date=from_date, to_date=to_date)


@router.get("/journal-entries/reports/bank-book/{account_id}")
async def mandir_journal_bank_book(
    account_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)
    return await bank_book_report(session, tenant_id=tenant_id, account_id=account_id, from_date=from_date, to_date=to_date)



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Login + opening balances (template / import)
# ROUTES : POST /login  POST /login/access-token  GET /opening-balances/template  POST .../import
# ════════════════════════════════════════════════════════════════════════

@router.post("/login")
@router.post("/login/access-token")
async def mandir_legacy_login(payload: dict[str, Any], x_app_key: str | None = Header(default=None, alias="X-App-Key")):
    from app.core.auth.service import login_user

    email = str(payload.get("email") or payload.get("username") or "")
    password = str(payload.get("password") or "")
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    access_token, refresh_token = await login_user(email, password, app_key=app_key)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/opening-balances/template")
async def mandir_opening_balances_template():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    sheet = wb.active
    sheet.title = "Opening Balances"

    headers = ["account_code", "account_name", "opening_balance_debit", "opening_balance_credit"]
    sheet.append(headers)

    header_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    example_data = [
        (11001, "Cash", 50000, None),
        (11002, "Bank Account", 100000, None),
        (32001, "General Reserve", None, 150000),
        (21001, "Loan Payable", None, 50000),
    ]

    for row_data in example_data:
        sheet.append(row_data)

    sheet.column_dimensions["A"].width = 15
    sheet.column_dimensions["B"].width = 25
    sheet.column_dimensions["C"].width = 25
    sheet.column_dimensions["D"].width = 25

    for row in sheet.iter_rows(min_row=2, max_col=4):
        for cell in row:
            cell.alignment = Alignment(horizontal="right")

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Opening_Balance_Template.xlsx"},
    )


@router.post("/opening-balances/import")
async def mandir_opening_balances_import(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    try:
        tenant_id = resolve_tenant_id(_current_user, x_tenant_id)
        await _ensure_default_mandir_sql_accounts_safe(session, tenant_id)

        rows = await _parse_opening_balance_rows(file)
        if not rows:
            raise HTTPException(status_code=400, detail="Import file is empty")

        sql_accounts = await list_accounts(session, tenant_id=tenant_id)
        accounts_by_code: dict[str, Account] = {}

        def _score_account(acc: Account, normalized_code: str) -> tuple[int, int, int]:
            raw_code = str(acc.code or "").strip()
            return (
                1 if raw_code == normalized_code else 0,
                len(raw_code),
                int(acc.id or 0),
            )

        for acc in sql_accounts:
            normalized_code = _normalize_mandir_account_code(acc.code, account_name=acc.name)
            if not normalized_code:
                continue
            existing = accounts_by_code.get(normalized_code)
            if existing is None or _score_account(acc, normalized_code) > _score_account(existing, normalized_code):
                accounts_by_code[normalized_code] = acc

        opening_offset_account = await _find_or_create_opening_balance_offset_account(session, tenant_id)

        updated_rows: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        skipped_count = 0

        for row_number, raw_row in enumerate(rows, start=2):
            try:
                row = {
                    str(key or "").strip().lower(): value
                    for key, value in (raw_row or {}).items()
                    if key is not None
                }

                raw_code = row.get("account_code") or row.get("legacy_code") or row.get("code")
                account_name_hint = row.get("account_name") or row.get("name")
                account_code = _normalize_mandir_account_code(raw_code, account_name=account_name_hint)
                if not account_code:
                    raise ValueError("account_code or legacy_code is required")

                account = accounts_by_code.get(account_code)
                if account is None:
                    raise ValueError(f"Account '{account_code}' not found")

                account_type = str(account.type or "").strip().lower()
                if account_type not in {"asset", "liability", "equity"}:
                    raise ValueError("Only balance sheet accounts can have opening balances")

                debit_raw = _parse_opening_balance_decimal(row.get("opening_balance_debit"))
                credit_raw = _parse_opening_balance_decimal(row.get("opening_balance_credit"))
                signed_raw = _parse_opening_balance_decimal(row.get("opening_balance"))

                if debit_raw is None and credit_raw is None and signed_raw is None:
                    raise ValueError("Provide opening_balance_debit/opening_balance_credit or opening_balance")

                debit_amount = max(debit_raw or Decimal("0"), Decimal("0"))
                credit_amount = max(credit_raw or Decimal("0"), Decimal("0"))

                if debit_raw is None and credit_raw is None and signed_raw is not None:
                    if account_type == "asset":
                        debit_amount = max(signed_raw, Decimal("0"))
                        credit_amount = max(-signed_raw, Decimal("0"))
                    else:
                        credit_amount = max(signed_raw, Decimal("0"))
                        debit_amount = max(-signed_raw, Decimal("0"))

                if debit_amount > 0 and credit_amount > 0:
                    raise ValueError("Only one side can be positive for opening balance")

                desired_net = debit_amount - credit_amount
                reference = f"OPENING-{account_code}"
                current_net = await _current_opening_balance_net(
                    session,
                    tenant_id=tenant_id,
                    account_id=int(account.id),
                    reference=reference,
                )
                delta_net = desired_net - current_net

                if delta_net == 0:
                    skipped_count += 1
                    continue

                account_debit = delta_net if delta_net > 0 else Decimal("0")
                account_credit = -delta_net if delta_net < 0 else Decimal("0")

                payload = JournalPostRequest(
                    entry_date=date.today(),
                    reference=reference,
                    description=f"Opening balance import for {account.code} - {account.name}",
                    lines=[
                        JournalLineIn(
                            account_id=int(account.id),
                            debit=account_debit,
                            credit=account_credit,
                        ),
                        JournalLineIn(
                            account_id=int(opening_offset_account.id),
                            debit=account_credit,
                            credit=account_debit,
                        ),
                    ],
                )

                idempotency_key = f"mandir-opening-balance:{account_code}:{str(desired_net)}"
                await post_journal_entry(
                    session,
                    tenant_id=tenant_id,
                    created_by=str(_current_user.get("sub") or _current_user.get("email") or "system"),
                    payload=payload,
                    idempotency_key=idempotency_key,
                )

                updated_rows.append(
                    {
                        "account_code": account_code,
                        "account_name": account.name,
                        "opening_balance_debit": _safe_float(max(desired_net, Decimal("0"))),
                        "opening_balance_credit": _safe_float(max(-desired_net, Decimal("0"))),
                        "applied_delta": _safe_float(delta_net),
                    }
                )
            except Exception as exc:
                errors.append({"row": row_number, "error": str(exc)})

        has_errors = len(errors) > 0
        success = len(updated_rows) > 0 and not has_errors

        if success:
            message = f"✓ Successfully imported {len(updated_rows)} opening balance(s)"
        elif len(updated_rows) > 0:
            message = f"⚠ Partial success: {len(updated_rows)} imported, {len(errors)} failed"
        else:
            message = f"✗ Import failed: All {len(rows)} row(s) had errors"

        return {
            "success": success,
            "status": "success" if success else ("partial" if len(updated_rows) > 0 else "failed"),
            "message": message,
            "processed_count": len(rows),
            "updated_count": len(updated_rows),
            "skipped_count": skipped_count,
            "error_count": len(errors),
            "updated": updated_rows,
            "errors": errors[:200],
        }
    except HTTPException:
        raise
    except Exception as exc:
        return {
            "success": False,
            "status": "failed",
            "message": f"✗ Import failed: {str(exc)}",
            "processed_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "updated": [],
            "errors": [{"row": 0, "error": str(exc)}],
        }



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Panchang display settings + panchang on-date
# ROUTES : GET|PUT /panchang/display-settings  GET .../cities  GET /panchang/on-date  GET /panchang/on-date-full
# ════════════════════════════════════════════════════════════════════════

@router.get("/panchang/display-settings")
@router.get("/panchang/display-settings/")
async def mandir_panchang_display_settings(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    doc = await get_collection("mandir_panchang_settings").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return {
        # Display mode and language
        "display_mode": str(doc.get("display_mode") or "full"),
        "primary_language": str(doc.get("primary_language") or "English"),
        "show_on_dashboard": bool(doc.get("show_on_dashboard", True)),
        # Panchang limb visibility flags (Panch Angs: Var, Tithi, Nakshatra, Karana, Yoga)
        "show_tithi": bool(doc.get("show_tithi", True)),
        "show_nakshatra": bool(doc.get("show_nakshatra", True)),
        "show_yoga": bool(doc.get("show_yoga", True)),
        "show_karana": bool(doc.get("show_karana", True)),
        # Optional timing displays
        "show_sun_timings": bool(doc.get("show_sun_timings", True)),
        "show_rahu_kaal": bool(doc.get("show_rahu_kaal", True)),
        "show_yamaganda": bool(doc.get("show_yamaganda", True)),
        "show_gulika": bool(doc.get("show_gulika", True)),
        "show_abhijit_muhurat": bool(doc.get("show_abhijit_muhurat", True)),
        # Location settings
        "city_name": doc.get("city_name"),
        "latitude": doc.get("latitude"),
        "longitude": doc.get("longitude"),
        "timezone": doc.get("timezone"),
    }


@router.put("/panchang/display-settings", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
@router.put("/panchang/display-settings/", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_panchang_display_settings_update(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    allowed = {
        # Display mode and language
        "display_mode",
        "primary_language",
        "show_on_dashboard",
        # Panchang limb visibility flags (Panch Angs)
        "show_tithi",
        "show_nakshatra",
        "show_yoga",
        "show_karana",
        # Optional timing displays
        "show_sun_timings",
        "show_rahu_kaal",
        "show_yamaganda",
        "show_gulika",
        "show_abhijit_muhurat",
        # Location settings
        "city_name",
        "latitude",
        "longitude",
        "timezone",
    }
    patch = {k: payload.get(k) for k in allowed if k in payload}
    patch["updated_at"] = now
    await get_collection("mandir_panchang_settings").update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": patch,
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": now,
            },
        },
        upsert=True,
    )
    return await mandir_panchang_display_settings(current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key)

@router.get("/panchang/display-settings/cities")
async def mandir_panchang_cities(_current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": _panchang_city_options()}


@router.get("/panchang/on-date")
async def mandir_panchang_on_date(
    target_date: str = Query(...),
    city_name: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Get panchang for a specific date for Nakshatra lookup."""
    try:
        # Parse the target date
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")

        tenant_id = resolve_tenant_id(current_user, x_tenant_id)
        app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

        # Get temple location from MongoDB
        temple_doc = await get_collection("mandir_temples").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        )
        if not temple_doc:
            temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id})

        # Get panchang display settings for overrides
        settings_doc = await get_collection("mandir_panchang_settings").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        ) or {}

        if not temple_doc:
            temple_doc = {}

        latitude, longitude, city = _resolve_panchang_location(
            settings_doc,
            temple_doc,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )

        # Calculate panchang for the target date
        panchang_service = PanchangService()
        panchang_data = panchang_service.calculate_panchang(target_dt, latitude, longitude, city)

        return {
            "lookup_requested_date": target_date,
            "panchang": panchang_data.get("panchang"),
            "date": panchang_data.get("date"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        logger.error(f"Error calculating panchang for date {target_date}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate panchang: {str(e)}"
        )


@router.get("/panchang/on-date-full")
async def mandir_panchang_on_date_full(
    target_date: str = Query(...),
    city_name: str | None = Query(default=None),
    latitude: float | None = Query(default=None),
    longitude: float | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Get complete panchang for any date (past/future). Returns full panchang data with all limbs and muhurtas."""
    try:
        # Parse the target date
        target_dt = datetime.strptime(target_date, "%Y-%m-%d")

        tenant_id = resolve_tenant_id(current_user, x_tenant_id)
        app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

        # Get temple location from MongoDB
        temple_doc = await get_collection("mandir_temples").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        )
        if not temple_doc:
            temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id})
        if not temple_doc:
            temple_doc = {}

        # Get panchang display settings for overrides
        settings_doc = await get_collection("mandir_panchang_settings").find_one(
            {"tenant_id": tenant_id, "app_key": app_key}
        ) or {}

        latitude, longitude, city = _resolve_panchang_location(
            settings_doc,
            temple_doc,
            city_name=city_name,
            latitude=latitude,
            longitude=longitude,
        )

        # Calculate panchang using Swiss Ephemeris
        panchang_service = PanchangService()
        panchang_data = panchang_service.calculate_panchang(target_dt, latitude, longitude, city)

        return panchang_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}")
    except Exception as e:
        logger.error(f"Error calculating panchang for date {target_date}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate panchang: {str(e)}"
        )



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Pincode lookup
# ROUTES : GET /pincode/lookup
# ════════════════════════════════════════════════════════════════════════

@router.get("/pincode/lookup")
async def mandir_pincode_lookup(pincode: str = Query(...), _current_user: dict = Depends(get_current_user)):
    normalized = _normalize_pincode(pincode)
    if len(normalized) != 6:
        return {"pincode": normalized, "city": None, "state": None, "country": "India", "found": False}

    city, state = await _lookup_pincode_city_state(normalized)
    found = bool(city and state)

    return {
        "pincode": normalized,
        "city": city if found else None,
        "state": state if found else None,
        "country": "India",
        "found": found,
    }

# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Reports (donations category-wise / detailed / sevas / daily / monthly / export)
# ROUTES : GET /reports/donations/category-wise|detailed  GET /reports/sevas/detailed|schedule  GET /donations/report/daily|monthly  GET /donations/export/excel|pdf
# ════════════════════════════════════════════════════════════════════════

@router.get("/reports/donations/category-wise")
async def mandir_report_donations_category_wise(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await donation_category_wise_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date)


@router.get("/reports/donations/detailed")
async def mandir_report_donations_detailed(
    from_date: date = Query(...),
    to_date: date = Query(...),
    category: str | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await detailed_donation_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=from_date,
        to_date=to_date,
        category=category,
        payment_mode=payment_mode,
    )


@router.get("/reports/sevas/detailed")
async def mandir_report_sevas_detailed(
    from_date: date = Query(...),
    to_date: date = Query(...),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await detailed_seva_report(session, tenant_id=tenant_id, app_key=app_key, from_date=from_date, to_date=to_date, status=status)


@router.get("/reports/sevas/schedule")
async def mandir_report_sevas_schedule(
    days: int = Query(default=3, ge=1, le=30),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await seva_schedule_report(session, tenant_id=tenant_id, app_key=app_key, days=days)


@router.get("/donations/report/daily")
async def mandir_donations_daily_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_value: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = _resolve_report_date_window(from_date=from_date, to_date=to_date, single_date=date_value)
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await donation_daily_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    category_data = await donation_category_wise_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=start_date,
        to_date=end_date,
    )
    data["total"] = data.get("total_amount", 0.0)
    data["count"] = data.get("total_count", 0)
    data["by_category"] = category_data.get("categories", [])
    return data


@router.get("/donations/report/monthly")
async def mandir_donations_monthly_report(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=1900, le=3000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = _resolve_report_date_window(
        from_date=from_date,
        to_date=to_date,
        month=month,
        year=year,
    )
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await donation_monthly_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    category_data = await donation_category_wise_report(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=start_date,
        to_date=end_date,
    )
    data["total"] = data.get("total_amount", 0.0)
    data["count"] = data.get("total_count", 0)
    data["by_category"] = category_data.get("categories", [])
    return data


@router.get("/donations/export/excel")
async def mandir_donations_export_excel(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = _resolve_export_window(from_date=from_date, to_date=to_date, date_from=date_from, date_to=date_to)
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await detailed_donation_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    return {**data, "export_format": "excel"}


@router.get("/donations/export/pdf")
async def mandir_donations_export_pdf(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    start_date, end_date = _resolve_export_window(from_date=from_date, to_date=to_date, date_from=date_from, date_to=date_to)
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    data = await detailed_donation_report(session, tenant_id=tenant_id, app_key=app_key, from_date=start_date, to_date=end_date)
    return {**data, "export_format": "pdf"}



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Role permissions (GET list / PUT / GET assignable)
# ROUTES : GET /role-permissions  PUT .../role-permissions/{role_key}  GET .../assignable
# ════════════════════════════════════════════════════════════════════════

@router.get("/role-permissions")
async def mandir_role_permissions(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    default_roles = [
        {"role_key": "president", "display_name": "President", "is_enabled": True},
        {"role_key": "secretary", "display_name": "Secretary", "is_enabled": True},
        {"role_key": "treasurer", "display_name": "Treasurer", "is_enabled": True},
        {"role_key": "counter_clerk", "display_name": "Counter Clerk", "is_enabled": True},
        {"role_key": "accounts_clerk", "display_name": "Accounts Clerk", "is_enabled": True},
        {"role_key": "priest_operator", "display_name": "Priest / Temple Operator", "is_enabled": True},
    ]
    docs = await get_collection("mandir_role_permissions").find({"tenant_id": tenant_id, "app_key": app_key}).to_list(length=200)
    by_role = {str(doc.get("role_key") or ""): doc for doc in docs}
    roles = []
    for base in default_roles:
        current = by_role.get(base["role_key"]) or {}
        roles.append(
            {
                "role_key": base["role_key"],
                "display_name": base["display_name"],
                "is_enabled": bool(current.get("is_enabled", base["is_enabled"])),
                "module_permissions": current.get("module_permissions") or {},
                "action_permissions": current.get("action_permissions") or {},
            }
        )
    return {
        "modules": [],
        "actions": [],
        "roles": roles,
        "policy_notice": "Accounting transactions should be reversed with audit reason instead of hard delete.",
    }


@router.put("/role-permissions/{role_key}", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_role_permissions_update(
    role_key: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "role_key": str(role_key).strip().lower(),
        "display_name": str(payload.get("display_name") or role_key).strip(),
        "is_enabled": bool(payload.get("is_enabled", True)),
        "module_permissions": payload.get("module_permissions") or {},
        "action_permissions": payload.get("action_permissions") or {},
        "updated_at": now,
    }
    await get_collection("mandir_role_permissions").update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "role_key": doc["role_key"]},
        {
            "$set": doc,
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )
    return {"role": doc}


@router.get("/role-permissions/assignable")
async def mandir_role_permissions_assignable(_current_user: dict = Depends(get_current_user)):
    return {
        "roles": [
            {"role_key": "treasurer", "display_name": "Treasurer"},
            {"role_key": "counter_clerk", "display_name": "Counter Clerk"},
            {"role_key": "accounts_clerk", "display_name": "Accounts Clerk"},
            {"role_key": "priest_operator", "display_name": "Priest / Temple Operator"},
        ]
    }


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Setup wizard + Temples management (CRUD / activate / deactivate / onboard / upload / modules config)
# ROUTES : GET /setup-wizard/status  GET /temples  POST /temples/{id}/activate|deactivate|remove  POST /temples/onboard  POST .../upload  GET|PUT .../modules/config
# ════════════════════════════════════════════════════════════════════════

@router.get("/setup-wizard/status")
async def mandir_setup_wizard_status(_current_user: dict = Depends(get_current_user)):
    return {"completed": False, "steps": []}


@router.get("/temples/")
@router.get("/temples")
async def mandir_temples(
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    if _is_platform_super_admin(_current_user):
        rows = await list_mandir_temples(app_key=app_key, limit=500)
    else:
        tenant_id = resolve_tenant_id(_current_user, x_tenant_id)
        rows = await list_mandir_temples(tenant_id=tenant_id, app_key=app_key, limit=20)

    if rows:
        return [_sanitize_mongo_doc(row) for row in rows]

    if _is_platform_super_admin(_current_user):
        return []

    return []




async def _resolve_temple_target_tenant(
    temple_id: int,
    *,
    current_user: dict,
    x_tenant_id: str | None,
    app_key: str = "mandirmitra",
) -> str:
    target_tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not target_tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    actor_tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    if not _is_platform_super_admin(current_user) and actor_tenant_id != target_tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for this tenant")

    return target_tenant_id


_MANDIR_TEMPLE_PURGE_COLLECTIONS = [
    "mandir_temples",
    "mandir_donations",
    "mandir_sevas",
    "mandir_seva_bookings",
    "mandir_devotees",
    "mandir_bank_accounts",
    "mandir_bank_statements",
    "mandir_bank_statement_entries",
    "mandir_bank_unmatched_entries",
    "mandir_inventory_items",
    "mandir_journal_entries",
    "mandir_public_payments",
    "mandir_upi_payments",
    "mandir_role_permissions",
    "mandir_panchang_settings",
]

_MANDIR_TEMPLE_BUSINESS_COLLECTIONS = [
    name
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS
    if name not in {"mandir_temples", "mandir_role_permissions", "mandir_panchang_settings"}
]


def _mandir_tenant_app_query(tenant_id: str, app_key: str) -> dict[str, Any]:
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if app_key == "mandirmitra":
        query["$or"] = [
            {"app_key": app_key},
            {"app_key": {"$exists": False}},
            {"app_key": None},
            {"app_key": ""},
        ]
    else:
        query["app_key"] = app_key
    return query


async def _mandir_temple_collection_counts(tenant_id: str, app_key: str) -> dict[str, int]:
    query = _mandir_tenant_app_query(tenant_id, app_key)
    counts: dict[str, int] = {}
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS:
        try:
            counts[name] = int(await get_collection(name).count_documents(query))
        except Exception:
            counts[name] = 0
    return counts


@router.post("/temples/{temple_id}/activate", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_activate_temple(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    now = datetime.now(timezone.utc).isoformat()
    await get_collection("mandir_temples").update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": True, "updated_at": now}},
        upsert=False,
    )
    doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {"tenant_id": tenant_id}
    return {"status": "activated", "temple_id": temple_id, "temple": _sanitize_mongo_doc(doc)}


@router.post("/temples/{temple_id}/deactivate", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_deactivate_temple(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    now = datetime.now(timezone.utc).isoformat()
    await get_collection("mandir_temples").update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": False, "updated_at": now}},
        upsert=False,
    )
    doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {"tenant_id": tenant_id}
    return {"status": "deactivated", "temple_id": temple_id, "temple": _sanitize_mongo_doc(doc)}


@router.get("/temples/{temple_id}/remove-preview")
async def mandir_remove_temple_preview(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not _is_platform_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only platform administrators can preview temple removal")

    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    target_tenant_id = await _resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    counts = await _mandir_temple_collection_counts(target_tenant_id, app_key)
    business_counts = {name: count for name, count in counts.items() if name in _MANDIR_TEMPLE_BUSINESS_COLLECTIONS and count > 0}
    return {
        "temple_id": temple_id,
        "tenant_id": target_tenant_id,
        "counts": counts,
        "has_business_data": bool(business_counts),
        "business_counts": business_counts,
        "can_remove_placeholder_safely": not business_counts,
    }


@router.delete("/temples/{temple_id}/remove", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_remove_temple(
    temple_id: int,
    payload: dict[str, Any] | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not _is_platform_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only platform administrators can remove temples")

    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    target_tenant_id = await _resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    expected = f"DELETE {temple_id}"
    confirm_text = str((payload or {}).get("confirm_text") or "").strip()
    if confirm_text != expected:
        raise HTTPException(status_code=400, detail=f"Confirmation text mismatch. Expected: {expected}")

    counts = await _mandir_temple_collection_counts(target_tenant_id, app_key)
    business_counts = {name: count for name, count in counts.items() if name in _MANDIR_TEMPLE_BUSINESS_COLLECTIONS and count > 0}
    allow_data_delete = bool((payload or {}).get("allow_data_delete"))
    if business_counts and not allow_data_delete:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Temple has business data. Review remove-preview before deleting.",
                "tenant_id": target_tenant_id,
                "business_counts": business_counts,
            },
        )

    delete_query = _mandir_tenant_app_query(target_tenant_id, app_key)
    deleted_counts: dict[str, int] = {}
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS:
        try:
            result = await get_collection(name).delete_many(delete_query)
            deleted_counts[name] = int(getattr(result, "deleted_count", 0) or 0)
        except Exception:
            deleted_counts[name] = 0

    return {
        "status": "removed",
        "temple_id": temple_id,
        "tenant_id": target_tenant_id,
        "deleted": deleted_counts,
    }

@router.post("/temples/onboard", response_model=MandirFirstLoginOnboardingResponse)
@router.post("/onboarding/first-login", response_model=MandirFirstLoginOnboardingResponse)
async def mandir_temples_onboard(
    payload: MandirFirstLoginOnboardingRequest,
    request: Request,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_onboarding_token: str | None = Header(default=None, alias="X-Onboarding-Token"),
):
    from app.config import get_settings as _get_settings
    _settings = _get_settings()
    required_secret = _settings.MANDIR_ONBOARDING_SECRET
    if required_secret:
        provided = (x_onboarding_token or "").strip()
        if not provided or provided != required_secret:
            logger.warning(
                "Onboarding attempt rejected: missing/invalid X-Onboarding-Token from %s",
                request.client.host if request.client else "unknown",
            )
            raise HTTPException(status_code=403, detail="Invalid or missing onboarding token")
    else:
        if str(_settings.ENVIRONMENT or "").strip().lower() in {"production", "prod"}:
            raise HTTPException(status_code=503, detail="Mandir onboarding is not configured")
        logger.info(
            "Onboarding endpoint called without secret enforcement (MANDIR_ONBOARDING_SECRET not set). "
            "Set this env var in production to protect this endpoint."
        )
    if not str(x_app_key or "").strip():
        raise HTTPException(status_code=400, detail="X-App-Key header is required")
    app_key = resolve_app_key(str(x_app_key).strip())
    return await create_mandir_first_login_onboarding(payload, app_key=app_key)


@router.post("/temples/upload", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_temples_upload(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return _ok("temples/upload")




@router.get("/compliance/donations/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def get_mandir_donation_compliance_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation compliance configuration read",
    )
    doc = await get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    )
    return donation_compliance_config_view(doc)


@router.put("/compliance/donations/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def update_mandir_donation_compliance_config(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation compliance configuration update",
    )
    await _assert_platform_can_write_tenant(
        current_user, tenant_id=context.tenant_id, app_key=context.app_key
    )
    config = validate_donation_compliance_config(payload)
    now = datetime.now(timezone.utc).isoformat()
    stored = {**config, "updated_at": now, "updated_by": _mandir_actor_id(current_user)}
    collection = get_collection("mandir_donation_compliance_config")
    await collection.update_one(
        {"tenant_id": context.tenant_id, "app_key": context.app_key},
        {
            "$set": stored,
            "$setOnInsert": {
                "tenant_id": context.tenant_id,
                "app_key": context.app_key,
                "created_at": now,
            },
        },
        upsert=True,
    )
    try:
        await log_audit_event(
            tenant_id=context.tenant_id,
            user_id=_mandir_actor_id(current_user),
            product=context.app_key,
            action="donation_compliance_config_updated",
            entity_type="mandir_donation_compliance_config",
            entity_id=f"{context.tenant_id}:{context.app_key}",
            old_value=None,
            new_value={
                "enable_80g": config["enable_80g"],
                "enable_fcra": config["enable_fcra"],
                "approval_valid_from": config.get("approval_valid_from"),
                "approval_valid_to": config.get("approval_valid_to"),
                "fcra_valid_from": config.get("fcra_valid_from"),
                "fcra_valid_to": config.get("fcra_valid_to"),
            },
        )
    except Exception:
        logger.warning("Failed to audit donation compliance configuration update", exc_info=True)
    return donation_compliance_config_view(stored)


async def _mandir_compliance_report(
    *, kind: str, tenant_id: str, app_key: str, from_date: date, to_date: date, session: AsyncSession
) -> dict[str, Any]:
    rows = await posted_donations(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=from_date,
        to_date=to_date,
    )
    items: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    for row in rows:
        if kind == "80g" and not bool(row.get("request_80g")):
            continue
        if kind == "fcra" and not bool(row.get("is_foreign_contribution")):
            continue
        public = compliance_public_fields(row)
        status_field = "80g_eligibility_status" if kind == "80g" else "fcra_status"
        status = str(public[status_field])
        status_counts[status] = status_counts.get(status, 0) + 1
        items.append({
            "donation_id": row.get("donation_id"),
            "receipt_number": row.get("receipt_number"),
            "date": row.get("date"),
            "amount": row.get("amount"),
            "payment_mode": row.get("payment_mode"),
            "devotee_name": row.get("devotee_name"),
            **public,
        })
    return {
        "report_kind": kind,
        "filing_artifact": False,
        "filing_notice": "Readiness report only; this is not an official government filing or certificate.",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "count": len(items),
        "status_counts": status_counts,
        "items": items,
    }


@router.get("/reports/compliance/80g", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_report_80g_readiness(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="80G readiness reporting",
    )
    return await _mandir_compliance_report(
        kind="80g", tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=from_date, to_date=to_date, session=session,
    )


@router.get("/reports/compliance/fcra", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_report_fcra_readiness(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="FCRA readiness reporting",
    )
    return await _mandir_compliance_report(
        kind="fcra", tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=from_date, to_date=to_date, session=session,
    )


@router.get("/temples/modules/config")
async def mandir_temples_module_config(
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(_current_user, x_tenant_id, temple_id, app_key)
    col = get_collection("mandir_temples")
    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    compliance_doc = await get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    )
    compliance = donation_compliance_config_view(compliance_doc)
    return {
        "module_donations_enabled": bool(doc.get("module_donations_enabled", True)),
        "module_sevas_enabled": bool(doc.get("module_sevas_enabled", True)),
        "module_inventory_enabled": bool(doc.get("module_inventory_enabled", False)),
        "module_assets_enabled": bool(doc.get("module_assets_enabled", False)),
        "module_hr_enabled": bool(doc.get("module_hr_enabled", False)),
        "module_hundi_enabled": bool(doc.get("module_hundi_enabled", False)),
        "module_accounting_enabled": bool(doc.get("module_accounting_enabled", True)),
        "module_panchang_enabled": bool(doc.get("module_panchang_enabled", True)),
        "enable_80g": compliance["enable_80g"],
        "enable_fcra": compliance["enable_fcra"],
    }


@router.put("/temples/modules/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_temples_module_config_update(
    payload: dict[str, Any],
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    tenant_id = await _resolve_tenant_for_mandir_request(_current_user, x_tenant_id, temple_id)
    app_key = resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    assigned_temple_id = await ensure_temple_numeric_id(tenant_id, app_key=app_key)
    col = get_collection("mandir_temples")

    allowed_keys = {
        "module_donations_enabled",
        "module_sevas_enabled",
        "module_inventory_enabled",
        "module_assets_enabled",
        "module_hr_enabled",
        "module_hundi_enabled",
        "module_accounting_enabled",
        "module_panchang_enabled",
    }
    update = {key: bool(payload.get(key)) for key in allowed_keys if key in payload}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["id"] = assigned_temple_id
    update["temple_id"] = assigned_temple_id

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": update,
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )

    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return {
        "module_donations_enabled": bool(doc.get("module_donations_enabled", True)),
        "module_sevas_enabled": bool(doc.get("module_sevas_enabled", True)),
        "module_inventory_enabled": bool(doc.get("module_inventory_enabled", False)),
        "module_assets_enabled": bool(doc.get("module_assets_enabled", False)),
        "module_hr_enabled": bool(doc.get("module_hr_enabled", False)),
        "module_hundi_enabled": bool(doc.get("module_hundi_enabled", False)),
        "module_accounting_enabled": bool(doc.get("module_accounting_enabled", True)),
        "module_panchang_enabled": bool(doc.get("module_panchang_enabled", True)),
    }


def _mandir_upi_config_view(doc: dict[str, Any], temple_id: int) -> dict[str, Any]:
    upi_id = str(doc.get("upi_id") or "").strip()
    payee_name = str(doc.get("upi_payee_name") or doc.get("trust_name") or doc.get("temple_name") or doc.get("name") or "Temple").strip()
    currency = str(doc.get("upi_currency") or "INR").strip().upper() or "INR"
    return {
        "temple_id": int(temple_id),
        "upi_public_enabled": bool(doc.get("upi_public_enabled", False)),
        "upi_id": upi_id,
        "upi_payee_name": payee_name,
        "upi_currency": currency,
        "upi_qr_note": str(doc.get("upi_qr_note") or "").strip() or None,
        "qr_code_image_url": str(doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": str(doc.get("admin_whatsapp") or "").strip() or None,
    }



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: UPI payments config (GET / PUT)
# ROUTES : GET /upi-payments/config  PUT .../config
# ════════════════════════════════════════════════════════════════════════

@router.get("/upi-payments/config")
async def mandir_upi_payments_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await ensure_temple_numeric_id(tenant_id, app_key=app_key)
    doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return _mandir_upi_config_view(doc, assigned_temple_id)


@router.put("/upi-payments/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_upi_payments_config_update(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    assigned_temple_id = await ensure_temple_numeric_id(tenant_id, app_key=app_key)

    upi_id = str(payload.get("upi_id") or "").strip().lower()
    upi_payee_name = str(payload.get("upi_payee_name") or "").strip()
    upi_qr_note = str(payload.get("upi_qr_note") or "").strip()
    upi_currency = str(payload.get("upi_currency") or "INR").strip().upper() or "INR"

    update = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "id": assigned_temple_id,
        "temple_id": assigned_temple_id,
    }
    if "upi_public_enabled" in payload:
        update["upi_public_enabled"] = bool(payload.get("upi_public_enabled"))
    if "upi_id" in payload:
        update["upi_id"] = upi_id or None
    if "upi_payee_name" in payload:
        update["upi_payee_name"] = upi_payee_name or None
    if "upi_qr_note" in payload:
        update["upi_qr_note"] = upi_qr_note or None
    if "upi_currency" in payload:
        update["upi_currency"] = upi_currency
    if "qr_code_image_url" in payload:
        update["qr_code_image_url"] = str(payload.get("qr_code_image_url") or "").strip() or None
    if "admin_whatsapp" in payload:
        update["admin_whatsapp"] = str(payload.get("admin_whatsapp") or "").strip() or None

    col = get_collection("mandir_temples")
    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": update,
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )
    doc = await col.find_one({"tenant_id": tenant_id}) or {}
    return _mandir_upi_config_view(doc, assigned_temple_id)


@router.get("/public/temples/{temple_id}/upi-intent")
async def mandir_public_upi_intent(
    temple_id: int,
    amount: float | None = Query(default=None, ge=0),
    purpose: str | None = Query(default=None),
    reference: str | None = Query(default=None),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    temples = get_collection("mandir_temples")
    temple_doc = await temples.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not temple_doc:
        temple_doc = await temples.find_one({"tenant_id": tenant_id}) or {}

    if not bool(temple_doc.get("upi_public_enabled", False)):
        raise HTTPException(status_code=404, detail="Public UPI is not enabled for this temple")

    upi_id = str(temple_doc.get("upi_id") or "").strip().lower()
    if not upi_id:
        raise HTTPException(status_code=404, detail="Temple UPI ID is not configured")

    payee_name = str(
        temple_doc.get("upi_payee_name")
        or temple_doc.get("trust_name")
        or temple_doc.get("temple_name")
        or temple_doc.get("name")
        or "Temple"
    ).strip()
    currency = str(temple_doc.get("upi_currency") or "INR").strip().upper() or "INR"
    note_text = str(purpose or temple_doc.get("upi_qr_note") or "Temple Offering").strip()
    reference_text = str(reference or "").strip() or None

    intent_uri = _build_upi_intent_uri(
        upi_id=upi_id,
        payee_name=payee_name,
        amount=amount,
        note=note_text,
        reference=reference_text,
        currency=currency,
    )

    return {
        "temple_id": temple_id,
        "upi_id": upi_id,
        "payee_name": payee_name,
        "currency": currency,
        "amount": amount,
        "purpose": note_text,
        "reference": reference_text,
        "intent_uri": intent_uri,
        "qr_payload": intent_uri,
    }


# ---------------------------------------------------------------------------
# VERSION ENDPOINT
# ---------------------------------------------------------------------------


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Version + public UPI intent
# ROUTES : GET /mandir/version  GET /public/temples/{temple_id}/upi-intent
# ════════════════════════════════════════════════════════════════════════

@router.get("/mandir/version")
async def mandir_get_version():
    """Get MandirMitra version info. No authentication required."""
    from app.config import get_settings
    from datetime import datetime
    settings = get_settings()
    return {
        "app": "MandirMitra",
        "version": settings.APP_VERSION,
        "released_at": "2026-04-14T00:00:00Z",  # Release date of v1.2.0
        "features": [
            "Quick Ticket Counter mode",
            "Seva renewal reminders (Email + SMS)",
            "Public payment idempotency & audit logging",
            "Rate limiting on public endpoints",
            "Multilingual support (en/kn/hi) for public portal",
            "Indic font rendering for PDFs"
        ]
    }


# ---------------------------------------------------------------------------
# PUBLIC SEVA PAYMENT ENDPOINTS  (no authentication required)
# ---------------------------------------------------------------------------

def _normalize_public_donation_categories(raw: Any, *, fallback_to_default: bool = True) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return [dict(item) for item in _DEFAULT_PUBLIC_DONATION_CATEGORIES] if fallback_to_default else []

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        category_id = str(item.get("id") or "").strip().lower()
        if not category_id:
            category_id = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or f"category_{index + 1}"
        base_id = category_id
        suffix = 2
        while category_id in seen:
            category_id = f"{base_id}_{suffix}"
            suffix += 1
        seen.add(category_id)
        normalized.append(
            {
                "id": category_id[:80],
                "name": name[:120],
                "description": str(item.get("description") or "").strip()[:300],
            }
        )

    if normalized or not fallback_to_default:
        return normalized
    return [dict(item) for item in _DEFAULT_PUBLIC_DONATION_CATEGORIES]



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public endpoints (temples list / info / sevas / autofill / pincode / donation-categories)
# ROUTES : GET /public/temples  GET .../info  GET .../sevas  GET .../devotee/autofill  GET .../donation-categories  GET /public/location/pincode
# ════════════════════════════════════════════════════════════════════════

@router.get("/public/temples")
async def mandir_public_list_temples(
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """List temples that have public payments enabled (for temple selector on public page)."""
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    col = get_collection("mandir_temples")
    visibility_query: dict[str, Any] = {
        "$or": [
            {"upi_public_enabled": True},
            {"upi_id": {"$exists": True, "$ne": None, "$ne": ""}},
        ]
    }
    if app_key == "mandirmitra":
        visibility_query["$and"] = [
            {
                "$or": [
                    {"app_key": app_key},
                    {"app_key": {"$exists": False}},
                    {"app_key": None},
                    {"app_key": ""},
                ]
            }
        ]
    else:
        visibility_query["app_key"] = app_key
    docs = await col.find(visibility_query).to_list(length=100)
    result = []
    for doc in docs:
        temple_id = doc.get("temple_id") or doc.get("id")
        if not temple_id:
            continue
        if app_key == "mandirmitra" and not str(doc.get("app_key") or "").strip():
            await col.update_one({"_id": doc.get("_id")}, {"$set": {"app_key": app_key}}, upsert=False)
        result.append({
            "temple_id": int(temple_id),
            "temple_name": str(doc.get("temple_name") or doc.get("name") or ""),
            "trust_name": str(doc.get("trust_name") or ""),
            "city": str(doc.get("city") or ""),
            "state": str(doc.get("state") or ""),
        })
    return result


@router.get("/public/temples/{temple_id}/info")
async def mandir_public_temple_info(
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not doc:
        raise HTTPException(status_code=404, detail="Temple not found")

    return {
        "temple_id": temple_id,
        "temple_name": str(doc.get("temple_name") or doc.get("name") or ""),
        "trust_name": str(doc.get("trust_name") or ""),
        "address": str(doc.get("address") or ""),
        "city": str(doc.get("city") or ""),
        "state": str(doc.get("state") or ""),
        "upi_id": str(doc.get("upi_id") or "").strip() or None,
        "upi_payee_name": str(doc.get("upi_payee_name") or doc.get("trust_name") or doc.get("temple_name") or ""),
        "qr_code_image_url": str(doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": str(doc.get("admin_whatsapp") or "").strip() or None,
        "upi_public_enabled": bool(doc.get("upi_public_enabled", False)),
    }


@router.get("/public/temples/{temple_id}/sevas")
@limiter.limit("30/minute")
async def mandir_public_temple_sevas(
    request: Request,
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    col = get_collection("mandir_sevas")
    docs = await col.find({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "is_active": {"$ne": False},
    }).sort("seva_name", 1).to_list(length=200)

    return [
        {
            "seva_id": str(doc.get("_id") or doc.get("id") or ""),
            "seva_name": str(doc.get("seva_name") or doc.get("name") or ""),
            "description": str(doc.get("description") or ""),
            "amount": doc.get("amount"),
            "frequency": str(doc.get("frequency") or "one_time"),
            "duration_days": doc.get("duration_days"),
        }
        for doc in docs
        if doc.get("seva_name") or doc.get("name")
    ]


@router.get("/public/temples/{temple_id}/devotee/autofill/{phone}")
@limiter.limit("20/minute")
async def mandir_public_devotee_autofill(
    request: Request,
    temple_id: int,
    phone: str,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    normalized = _normalize_phone(phone)
    if not normalized:
        return {"found": False, "devotee": None}

    # Scoped by tenant_id + app_key - mobile linked to THIS temple only
    col = get_collection("mandir_devotees")
    docs = await col.find({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "phone": normalized,
    }).limit(1).to_list(length=1)

    if not docs:
        return {"found": False, "devotee": None}

    doc = docs[0]
    return {
        "found": True,
        "devotee": {
            "name": str(doc.get("name") or ""),
            "city": str(doc.get("city") or ""),
            "state": str(doc.get("state") or ""),
            "pincode": str(doc.get("pincode") or ""),
            "gothra": str(doc.get("gothra") or ""),
            "nakshtra": str(doc.get("nakshtra") or ""),
            "rashi": str(doc.get("rashi") or ""),
        },
    }


@router.get("/public/location/pincode/{pincode}")
async def mandir_public_pincode_lookup(pincode: str):
    if not pincode.isdigit() or len(pincode) != 6:
        raise HTTPException(status_code=400, detail="Invalid pincode. Must be 6 digits.")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.postalpincode.in/pincode/{pincode}")
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0].get("Status") == "Success":
                post_offices = data[0].get("PostOffice") or []
                if post_offices:
                    po = post_offices[0]
                    return {
                        "found": True,
                        "pincode": pincode,
                        "city": str(po.get("District") or po.get("Name") or ""),
                        "state": str(po.get("State") or ""),
                        "district": str(po.get("District") or ""),
                    }
    except Exception:
        pass

    return {"found": False, "pincode": pincode, "city": "", "state": "", "district": ""}


@router.get("/public/temples/{temple_id}/donation-categories")
async def mandir_public_donation_categories(
    temple_id: int,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return _normalize_public_donation_categories(temple_doc.get("donation_categories"))



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public seva payments (create / status)
# ROUTES : POST /public/temples/{temple_id}/seva-payments  GET /public/payments/{payment_id}/status
# ════════════════════════════════════════════════════════════════════════

@router.post("/public/temples/{temple_id}/seva-payments")
@limiter.limit("10/minute")
async def mandir_public_create_seva_payment(
    temple_id: int,
    payload: dict[str, Any],
    request: Request,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    # Idempotency: if client sends idempotency_key and a matching pending record
    # exists (submitted in the last 10 minutes), return it without creating a duplicate.
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if idempotency_key:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        existing = await get_collection("mandir_public_payments").find_one({
            "tenant_id": tenant_id,
            "app_key": app_key,
            "idempotency_key": idempotency_key,
            "created_at": {"$gte": cutoff},
        })
        if existing:
            temple_doc_i = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
            return {
                "payment_id": existing["id"][:8].upper(),
                "full_payment_id": existing["id"],
                "status": existing.get("status", "pending"),
                "payment_type": existing.get("payment_type", "seva"),
                "seva_name": existing.get("seva_name", ""),
                "amount": existing.get("amount"),
                "upi_id": str(temple_doc_i.get("upi_id") or "").strip() or None,
                "upi_payee_name": str(temple_doc_i.get("upi_payee_name") or temple_doc_i.get("trust_name") or "").strip() or None,
                "qr_code_image_url": str(temple_doc_i.get("qr_code_image_url") or "").strip() or None,
                "admin_whatsapp": str(temple_doc_i.get("admin_whatsapp") or "").strip() or None,
                "whatsapp_link": existing.get("whatsapp_link"),
                "whatsapp_message_template": existing.get("whatsapp_message_template"),
                "message": "Payment already submitted. Please complete UPI payment and send WhatsApp confirmation.",
                "_idempotent": True,
            }

    payment_type = str(payload.get("payment_type") or "seva").strip().lower()
    if payment_type not in ("seva", "donation"):
        payment_type = "seva"

    # Validate required fields
    phone_raw = str(payload.get("phone") or payload.get("mobile") or "").strip()
    normalized_phone = _normalize_phone(phone_raw)
    if not normalized_phone:
        raise HTTPException(status_code=400, detail="Valid mobile number is required")

    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    if payment_type == "donation":
        category_id = str(payload.get("category_id") or "").strip()
        category_name = str(payload.get("category_name") or "").strip()
        if not category_name:
            raise HTTPException(status_code=400, detail="Donation category is required")
        seva_id = None
        seva_name = category_name
    else:
        seva_id = str(payload.get("seva_id") or "").strip()
        seva_name = str(payload.get("seva_name") or "").strip()
        if not seva_name:
            raise HTTPException(status_code=400, detail="Seva selection is required")

    now = datetime.now(timezone.utc).isoformat()

    # Upsert devotee record - scoped to this temple's tenant_id
    devotee_col = get_collection("mandir_devotees")
    devotee_update = {
        "name": name,
        "phone": normalized_phone,
        "email": str(payload.get("email") or "").strip() or None,
        "address": str(payload.get("address") or "").strip() or None,
        "city": str(payload.get("city") or "").strip() or None,
        "state": str(payload.get("state") or "").strip() or None,
        "pincode": str(payload.get("pincode") or "").strip() or None,
        "gothra": str(payload.get("gothra") or "").strip() or None,
        "nakshtra": str(payload.get("nakshtra") or "").strip() or None,
        "rashi": str(payload.get("rashi") or "").strip() or None,
        "updated_at": now,
    }
    devotee_update_clean = {k: v for k, v in devotee_update.items() if v is not None}

    await devotee_col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized_phone},
        {
            "$set": devotee_update_clean,
            "$setOnInsert": {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": now,
                "verified": False,
            },
        },
        upsert=True,
    )

    # Create payment record with pending status
    payment_id = str(uuid4())
    payment_doc = {
        "id": payment_id,
        "temple_id": temple_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "payment_type": payment_type,
        "seva_id": seva_id or None,
        "seva_name": seva_name,
        "amount": float(payload.get("amount") or 0) or None,
        "devotee_name": name,
        "devotee_phone": normalized_phone,
        "devotee_email": str(payload.get("email") or "").strip() or None,
        "gothra": str(payload.get("gothra") or "").strip() or None if payment_type == "seva" else None,
        "nakshtra": str(payload.get("nakshtra") or "").strip() or None if payment_type == "seva" else None,
        "rashi": str(payload.get("rashi") or "").strip() or None if payment_type == "seva" else None,
        "status": "pending",
        "utr_reference": None,
        "verified_at": None,
        "verified_by": None,
        "created_at": now,
        "source_ip": str(request.client.host if request.client else ""),
        "idempotency_key": idempotency_key or None,
    }

    await get_collection("mandir_public_payments").insert_one(payment_doc)

    # Formal audit log for every public payment submission
    from app.core.audit.service import log_audit_event
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=f"public:{normalized_phone}",
            product="mandirmitra",
            action="public_payment_submitted",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            new_value={
                "payment_type": payment_type,
                "seva_name": seva_name,
                "amount": payload.get("amount"),
                "devotee_phone": normalized_phone,
            },
            ip_address=str(request.client.host if request.client else ""),
        )
    except Exception:
        pass  # Audit is best-effort; never block the payment flow

    # Build WhatsApp message template
    temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    admin_whatsapp = str(temple_doc.get("admin_whatsapp") or "").strip()
    upi_id = str(temple_doc.get("upi_id") or "").strip()
    amount_str = f"Rs.{payload.get('amount')}" if payload.get("amount") else ""
    payment_label = "Donation" if payment_type == "donation" else "Seva payment"
    whatsapp_message = (
        f"Namaste, I have made the {seva_name} {payment_label} {amount_str}.\n"
        f"UTR/Reference: [PASTE UTR HERE]\n"
        f"Name: {name}\n"
        f"Mobile: {normalized_phone}\n"
        f"Payment ID: {payment_id[:8].upper()}"
    )
    whatsapp_link = None
    if admin_whatsapp:
        from urllib.parse import quote
        whatsapp_link = f"https://wa.me/{admin_whatsapp.replace('+', '').replace(' ', '')}?text={quote(whatsapp_message)}"

    # Store whatsapp details on payment doc for idempotency replay
    await get_collection("mandir_public_payments").update_one(
        {"id": payment_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"whatsapp_link": whatsapp_link, "whatsapp_message_template": whatsapp_message}},
    )

    return {
        "payment_id": payment_id[:8].upper(),
        "full_payment_id": payment_id,
        "status": "pending",
        "payment_type": payment_type,
        "seva_name": seva_name,
        "amount": payload.get("amount"),
        "upi_id": upi_id or None,
        "upi_payee_name": str(temple_doc.get("upi_payee_name") or temple_doc.get("trust_name") or temple_doc.get("temple_name") or "").strip() or None,
        "qr_code_image_url": str(temple_doc.get("qr_code_image_url") or "").strip() or None,
        "admin_whatsapp": admin_whatsapp or None,
        "whatsapp_link": whatsapp_link,
        "whatsapp_message_template": whatsapp_message,
        "message": "Devotee details saved. Please complete payment via UPI and send WhatsApp confirmation to the temple admin.",
    }


@router.get("/public/payments/{payment_id}/status")
async def mandir_public_payment_status(
    payment_id: str,
    temple_id: int = Query(..., ge=1),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or "mandirmitra").strip())
    tenant_id = await resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    normalized_payment_id = str(payment_id or "").strip()
    if not normalized_payment_id:
        raise HTTPException(status_code=400, detail="Payment ID is required")

    col = get_collection("mandir_public_payments")
    doc = await col.find_one({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "id": normalized_payment_id,
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "payment_id": str(doc.get("id") or "")[:8].upper(),
        "seva_name": doc.get("seva_name"),
        "amount": doc.get("amount"),
        "status": doc.get("status", "pending"),
        "verified_at": doc.get("verified_at"),
    }



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Public payments management (list / exceptions / reject / correct / verify)
# ROUTES : GET /public-payments  GET .../exceptions  PATCH .../reject|correction|verify
# ════════════════════════════════════════════════════════════════════════

@router.get("/public-payments")
async def mandir_list_public_payments(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    payment_type: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await _resolve_tenant_for_mandir_request(current_user, x_tenant_id, temple_id, app_key=app_key)
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    normalized_status = str(status or "").strip().lower()
    if normalized_status and normalized_status != "all":
        query["status"] = normalized_status

    col = get_collection("mandir_public_payments")
    normalized_q = str(q or "").strip().lower()
    normalized_type = str(payment_type or "").strip().lower()
    needs_in_memory_filter = any([normalized_q, normalized_type])
    fetch_limit = 500 if needs_in_memory_filter else min(limit + offset, 500)
    docs = await col.find(query).sort("created_at", -1).limit(fetch_limit).to_list(length=fetch_limit)
    filtered: list[dict[str, Any]] = []
    for doc in docs:
        doc_type = str(doc.get("payment_type") or doc.get("payment_purpose") or "").strip().lower()
        if normalized_type and doc_type != normalized_type:
            continue
        if normalized_q:
            haystack = " ".join(
                str(doc.get(key) or "")
                for key in (
                    "id",
                    "payment_id",
                    "devotee_name",
                    "name",
                    "devotee_phone",
                    "phone",
                    "seva_name",
                    "payment_type",
                    "payment_purpose",
                    "status",
                    "utr_reference",
                )
            ).lower()
            if normalized_q not in haystack:
                continue
        filtered.append(_sanitize_mongo_doc(doc))
    return filtered[offset:offset + limit]


@router.get("/public-payments/exceptions")
async def mandir_public_payment_exceptions(
    older_than_hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    reason: str | None = Query(default=None),
    status: str | None = Query(default=None),
    payment_type: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=older_than_hours)
    docs = await get_collection("mandir_public_payments").find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).sort("created_at", -1).limit(500).to_list(length=500)

    rows: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    normalized_q = str(q or "").strip().lower()
    normalized_reason = str(reason or "").strip().lower()
    normalized_status = str(status or "").strip().lower()
    normalized_type = str(payment_type or "").strip().lower()
    for doc in docs:
        doc_status = str(doc.get("status") or "pending").strip().lower()
        amount = _safe_float(doc.get("amount"), 0.0)
        created_at = _parse_iso_datetime(doc.get("created_at"))
        reasons: list[str] = []

        if doc_status in {"failed", "error", "rejected"}:
            reasons.append(doc_status)
        if doc_status == "pending" and created_at and created_at < stale_cutoff:
            reasons.append("stale_pending")
        if amount <= 0:
            reasons.append("invalid_amount")
        if not _normalize_phone(doc.get("devotee_phone")):
            reasons.append("missing_phone")
        doc_payment_type = str(doc.get("payment_type") or "").strip().lower()
        if doc_payment_type not in {"donation", "seva"}:
            reasons.append("invalid_payment_type")
        if doc_payment_type == "seva" and not str(doc.get("seva_name") or "").strip():
            reasons.append("missing_seva")
        if doc_payment_type == "donation" and not str(doc.get("seva_name") or doc.get("category") or "").strip():
            reasons.append("missing_donation_category")

        if not reasons:
            continue
        if normalized_reason and normalized_reason not in reasons:
            continue
        if normalized_status and normalized_status != "all" and doc_status != normalized_status:
            continue
        if normalized_type and doc_payment_type != normalized_type:
            continue
        if normalized_q:
            haystack = " ".join(
                str(doc.get(key) or "")
                for key in (
                    "id",
                    "payment_id",
                    "devotee_name",
                    "name",
                    "devotee_phone",
                    "phone",
                    "seva_name",
                    "payment_type",
                    "payment_purpose",
                    "status",
                    "utr_reference",
                )
            ).lower()
            if normalized_q not in haystack:
                continue

        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        row = _sanitize_mongo_doc(doc)
        row["exception_reasons"] = reasons
        row["age_hours"] = round(((now - created_at).total_seconds() / 3600), 2) if created_at else None
        rows.append(row)

    return {
        "summary": {
            "total": len(rows),
            "by_reason": reason_counts,
            "older_than_hours": older_than_hours,
        },
        "items": rows[offset:offset + limit],
    }


@router.patch("/public-payments/{payment_id}/reject", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_reject_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    reason = " ".join(str(payload.get("reason") or "").strip().split())
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Rejection reason is required")

    col = get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    if str(doc.get("status") or "").strip().lower() == "verified":
        raise HTTPException(status_code=400, detail="Verified payment cannot be rejected")

    now = datetime.now(timezone.utc).isoformat()
    rejected_by = str(current_user.get("email") or current_user.get("sub") or current_user.get("id") or "admin")
    update = {
        "status": "rejected",
        "rejection_reason": reason,
        "rejected_at": now,
        "rejected_by": rejected_by,
        "updated_at": now,
    }
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": update})

    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=rejected_by,
            product="mandirmitra",
            action="public_payment_rejected",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={"status": doc.get("status")},
            new_value={"status": "rejected", "reason": reason},
        )
    except Exception:
        pass

    return {
        "status": "rejected",
        "payment_id": payment_id[:8].upper(),
        "reason": reason,
        "rejected_at": now,
    }


@router.patch("/public-payments/{payment_id}/correction", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_correct_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")
    if str(doc.get("status") or "").strip().lower() == "verified":
        raise HTTPException(status_code=400, detail="Verified payment cannot be corrected")

    patch: dict[str, Any] = {}
    if "amount" in payload:
        amount = _safe_float(payload.get("amount"), 0.0)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")
        patch["amount"] = amount
    if "devotee_phone" in payload:
        phone = _normalize_phone(payload.get("devotee_phone"))
        if not phone:
            raise HTTPException(status_code=400, detail="Valid mobile number is required")
        patch["devotee_phone"] = phone
    if "payment_type" in payload:
        payment_type = str(payload.get("payment_type") or "").strip().lower()
        if payment_type not in {"donation", "seva"}:
            raise HTTPException(status_code=400, detail="payment_type must be donation or seva")
        patch["payment_type"] = payment_type
    if "seva_name" in payload:
        purpose = " ".join(str(payload.get("seva_name") or "").strip().split())
        if not purpose:
            raise HTTPException(status_code=400, detail="Donation/seva purpose is required")
        patch["seva_name"] = purpose

    if not patch:
        raise HTTPException(status_code=400, detail="No correction fields provided")

    now = datetime.now(timezone.utc).isoformat()
    corrected_by = str(current_user.get("email") or current_user.get("sub") or current_user.get("id") or "admin")
    patch.update({
        "corrected_at": now,
        "corrected_by": corrected_by,
        "updated_at": now,
    })
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": patch})
    updated = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}) or {**doc, **patch}

    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=corrected_by,
            product="mandirmitra",
            action="public_payment_corrected",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={key: doc.get(key) for key in patch if key in doc},
            new_value={key: patch.get(key) for key in patch},
        )
    except Exception:
        pass

    return _sanitize_mongo_doc(updated)


@router.patch("/public-payments/{payment_id}/verify", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_verify_public_payment(
    payment_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = get_collection("mandir_public_payments")
    doc = await col.find_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key})
    if not doc:
        raise HTTPException(status_code=404, detail="Payment not found")

    if doc.get("status") == "verified":
        raise HTTPException(status_code=400, detail="Payment already verified")

    utr_reference = _normalize_public_payment_utr_reference(
        payload.get("utr_reference") or doc.get("utr_reference") or doc.get("upi_reference_number")
    )
    payment_date = str(
        payload.get("payment_date") or datetime.now(timezone.utc).date().isoformat()
    ).strip()
    bank_account_id = payload.get("bank_account_id")  # optional explicit bank account

    payment_type = str(doc.get("payment_type") or "seva").lower()
    amount = float(doc.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    devotee_name = str(doc.get("devotee_name") or "").strip() or "Unknown Devotee"
    devotee_phone = str(doc.get("devotee_phone") or "").strip() or None
    devotee_email = str(doc.get("devotee_email") or "").strip() or None
    seva_name = str(doc.get("seva_name") or "").strip()
    seva_id = str(doc.get("seva_id") or "").strip() or None

    source_record: dict[str, Any] = {}
    source_type: str
    source_id: str | None = None

    try:
        if payment_type == "seva":
            seva_payload: dict[str, Any] = {
                "amount_paid": amount,
                "payment_mode": "UPI",
                "devotee_name": devotee_name,
                "devotee_names": devotee_name,
                "devotee_phone": devotee_phone,
                "devotee_mobile": devotee_phone,
                "booking_date": payment_date,
                "seva_name": seva_name,
                "seva_id": seva_id or "",
                "upi_reference_number": utr_reference,
                "gothra": doc.get("gothra"),
                "nakshtra": doc.get("nakshtra"),
                "rashi": doc.get("rashi"),
                "notes": f"Public portal | Payment ID: {payment_id[:8].upper()}",
            }
            if bank_account_id:
                seva_payload["bank_account_id"] = bank_account_id
            source_record = await create_seva_booking(
                payload=seva_payload,
                session=session,
                current_user=current_user,
                x_tenant_id=x_tenant_id,
                x_app_key=app_key,
            )
            source_type = "seva_booking"
            source_id = str(source_record.get("id") or "").strip() or None
        else:
            # Donation — map category_name back to standard category
            _donation_cat_map = {
                "general donation": "General Donation",
                "annadanam": "Annadanam",
                "construction fund": "Construction Fund",
                "corpus fund": "Corpus Fund",
                "vastra seva": "Vastra Seva",
                "nitya puja": "Nitya Puja",
            }
            category = _donation_cat_map.get(seva_name.lower(), seva_name) or "General Donation"
            donation_payload: dict[str, Any] = {
                "amount": amount,
                "payment_mode": "UPI",
                "category": category,
                "devotee_name": devotee_name,
                "devotee_phone": devotee_phone,
                "email": devotee_email,
                "upi_reference_number": utr_reference,
                "donation_date": payment_date,
                "notes": f"Public portal | Payment ID: {payment_id[:8].upper()}",
            }
            if bank_account_id:
                donation_payload["bank_account_id"] = bank_account_id
            source_record = await create_donation(
                payload=donation_payload,
                session=session,
                current_user=current_user,
                x_tenant_id=x_tenant_id,
                x_app_key=app_key,
            )
            source_type = "donation"
            source_id = str(source_record.get("donation_id") or source_record.get("id") or "").strip() or None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to post accounting entry: {exc}") from exc

    now = datetime.now(timezone.utc).isoformat()
    update = {
        "status": "verified",
        "verified_at": now,
        "verified_by": str(current_user.get("email") or current_user.get("sub") or "admin"),
        "utr_reference": utr_reference,
        "source_type": source_type,
        "source_id": source_id,
    }
    await col.update_one({"id": payment_id, "tenant_id": tenant_id, "app_key": app_key}, {"$set": update})

    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=update["verified_by"],
            product="mandirmitra",
            action="public_payment_verified",
            entity_type="mandir_public_payment",
            entity_id=payment_id,
            old_value={"status": doc.get("status")},
            new_value={
                "status": "verified",
                "utr_reference": utr_reference,
                "source_type": source_type,
                "source_id": source_id,
                "receipt_number": str(source_record.get("receipt_number") or "").strip() or None,
            },
        )
    except Exception:
        pass

    receipt_number = str(source_record.get("receipt_number") or "").strip() or None
    receipt_pdf_url = str(source_record.get("receipt_pdf_url") or "").strip() or None
    if not receipt_pdf_url and source_id:
        if source_type == "seva_booking":
            receipt_pdf_url = f"/api/v1/sevas/bookings/{source_id}/receipt/pdf"
        elif source_type == "donation":
            receipt_pdf_url = f"/api/v1/donations/{source_id}/receipt/pdf"

    return {
        "status": "verified",
        "payment_id": payment_id[:8].upper(),
        "source_type": source_type,
        "source_id": source_id,
        "receipt_number": receipt_number,
        "receipt_pdf_url": receipt_pdf_url,
        "message": "Payment verified and accounting entry posted successfully.",
    }



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: UPI payments management (list / quick-log)
# ROUTES : GET /upi-payments  POST .../quick-log
# ════════════════════════════════════════════════════════════════════════

@router.get("/upi-payments")
async def mandir_upi_payments(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    rows = await get_collection("mandir_upi_payments").find({"tenant_id": tenant_id, "app_key": app_key}).sort("payment_datetime", -1).limit(limit).to_list(length=limit)

    filtered: list[dict[str, Any]] = []
    for row in rows:
        parsed = _parse_iso_datetime(row.get("payment_datetime") or row.get("created_at"))
        if parsed is not None:
            row_date = parsed.date()
            if from_date and row_date < from_date:
                continue
            if to_date and row_date > to_date:
                continue
        filtered.append(row)

    filtered.sort(key=lambda item: str(item.get("payment_datetime") or item.get("created_at") or ""), reverse=True)
    return [_mandir_upi_payment_view(row) for row in filtered]


@router.post("/upi-payments/quick-log", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_upi_quick_log(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="UPI quick log",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key

    amount = _safe_float(payload.get("amount"), 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    purpose = str(payload.get("payment_purpose") or "DONATION").strip().upper()
    payment_dt = _parse_iso_datetime(payload.get("payment_datetime")) or datetime.now(timezone.utc)
    payment_datetime = payment_dt.isoformat()

    normalized_phone = _normalize_phone(payload.get("devotee_phone") or payload.get("sender_phone") or payload.get("phone"))
    devotee_name = str(payload.get("devotee_name") or payload.get("sender_name") or "").strip() or "Walk-in Devotee"
    sender_upi_id = str(payload.get("sender_upi_id") or "").strip() or None
    upi_reference_number = str(payload.get("upi_reference_number") or "").strip() or None
    notes = str(payload.get("notes") or "").strip() or None

    col = get_collection("mandir_upi_payments")
    if upi_reference_number:
        existing = await col.find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "upi_reference_number": upi_reference_number,
            }
        )
        if existing is not None:
            return _mandir_upi_payment_view(existing)

    source_record: dict[str, Any]
    source_type: str
    source_id: str | None

    if purpose == "SEVA":
        seva_payload = {
            **payload,
            "amount_paid": amount,
            "payment_mode": "UPI",
            "devotee_name": devotee_name,
            "devotee_names": str(payload.get("devotee_names") or devotee_name),
            "devotee_phone": normalized_phone,
            "devotee_mobile": normalized_phone,
            "booking_date": str(payload.get("booking_date") or payment_dt.date().isoformat()),
            "seva_name": str(payload.get("seva_name") or "Seva Booking"),
        }
        source_record = await create_seva_booking(
            payload=seva_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        source_type = "seva"
        source_id = str(source_record.get("id") or "").strip() or None
    else:
        donation_category_map = {
            "ANNADANA": "Annadanam",
            "ANNADANAM": "Annadanam",
            "SPONSORSHIP": "Sponsorship",
            "OTHER": "General Donation",
            "DONATION": "General Donation",
        }
        donation_payload = {
            **payload,
            "amount": amount,
            "payment_mode": "UPI",
            "category": str(payload.get("category") or donation_category_map.get(purpose, "General Donation")),
            "devotee_name": devotee_name,
            "devotee_phone": normalized_phone,
            "phone": normalized_phone,
        }
        source_record = await create_donation(
            payload=donation_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        source_type = "donation"
        source_id = str(source_record.get("donation_id") or source_record.get("id") or "").strip() or None

    row_id = str(uuid4())
    receipt_number = str(source_record.get("receipt_number") or _upi_receipt_number({"id": row_id})).strip()
    now = datetime.now(timezone.utc).isoformat()
    payment_row = {
        "id": row_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "amount": amount,
        "payment_datetime": payment_datetime,
        "payment_mode": "UPI",
        "payment_purpose": purpose,
        "devotee_name": devotee_name,
        "devotee_phone": normalized_phone,
        "sender_phone": normalized_phone,
        "sender_upi_id": sender_upi_id,
        "upi_reference_number": upi_reference_number,
        "notes": notes,
        "source_type": source_type,
        "source_id": source_id,
        "receipt_number": receipt_number,
        "created_at": now,
        "updated_at": now,
    }
    await col.insert_one(payment_row)

    return _mandir_upi_payment_view(payment_row)



# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Users (GET list / PUT profile)
# ROUTES : GET /users  PUT /users/{user_id}
# ════════════════════════════════════════════════════════════════════════

@router.get("/users")
async def mandir_users(_current_user: dict = Depends(get_current_user), x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")):
    tenant_id = resolve_tenant_id(_current_user, x_tenant_id)
    users = get_collection("core_users")
    docs = await users.find({"tenant_id": tenant_id, "is_active": True}).limit(200).to_list(length=200)
    return [{"user_id": d.get("user_id"), "email": d.get("email"), "full_name": d.get("full_name"), "role": d.get("role")} for d in docs]



@router.put("/users/{user_id}")
async def mandir_update_user_profile(
    user_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    users = get_collection("core_users")
    query = {
        "tenant_id": tenant_id,
        "$or": [
            {"user_id": user_id},
            {"id": user_id},
        ],
    }

    patch: dict[str, Any] = {}
    if "full_name" in payload:
        patch["full_name"] = str(payload.get("full_name") or "").strip()
    if "email" in payload:
        patch["email"] = str(payload.get("email") or "").strip().lower()
    if "phone" in payload:
        phone = str(payload.get("phone") or "").strip()
        patch["phone"] = phone or None
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()

    await users.update_one(query, {"$set": patch}, upsert=False)
    doc = await users.find_one(query)
    if doc is None:
        raise HTTPException(status_code=404, detail="User not found")

    resolved_id = str(doc.get("user_id") or doc.get("id") or user_id)
    return {
        "id": resolved_id,
        "email": str(doc.get("email") or ""),
        "full_name": str(doc.get("full_name") or ""),
        "phone": doc.get("phone"),
        "role": doc.get("role"),
        "system_role": doc.get("system_role") or doc.get("role"),
        "role_key": doc.get("role_key"),
        "role_label": doc.get("role_label"),
        "module_permissions": doc.get("module_permissions") or {},
        "action_permissions": doc.get("action_permissions") or {},
        "is_superuser": bool(doc.get("is_superuser", False)),
        "must_change_password": bool(doc.get("must_change_password", False)),
    }


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Seva bookings (POST / quick-ticket / GET / receipt PDF / cancel / reschedule / approve)
# ROUTES : POST /sevas/bookings  POST .../quick-ticket  GET .../bookings  GET .../receipt/pdf  POST .../cancel  PUT .../reschedule  POST .../approve-reschedule  GET .../pending
# ════════════════════════════════════════════════════════════════════════

@router.post("/sevas/bookings", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/sevas/bookings/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_seva_booking(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="seva booking",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    await _ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    booking_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    amount = _safe_float(payload.get("amount_paid") or payload.get("amount"), 0.0)
    payment_mode = str(payload.get("payment_mode") or payload.get("payment_method") or "Cash")
    seva_id = payload.get("seva_id")
    seva_name = str(payload.get("seva_name") or "Seva Booking")
    col_sevas = get_collection("mandir_sevas")
    seva_doc: dict[str, Any] | None = None
    if seva_id:
        seva_doc = await col_sevas.find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
        if not seva_doc:
            seva_doc = await col_sevas.find_one({"id": str(seva_id), "tenant_id": tenant_id})
        if seva_doc and seva_doc.get("name"):
            seva_name = str(seva_doc["name"])
        if seva_doc and seva_doc.get("name_kannada"):
            payload["seva_name_local"] = str(seva_doc.get("name_kannada") or "").strip()

    booking_date = _parse_booking_date(payload.get("booking_date"))
    if booking_date is None:
        raise HTTPException(status_code=400, detail="Please enter a valid booking date.")
    _validate_seva_booking_date(seva_doc, booking_date)
    await _validate_seva_booking_capacity(
        seva_doc,
        tenant_id=tenant_id,
        app_key=app_key,
        seva_id=str(seva_id),
        booking_date=booking_date,
    )

    # Compute expiry_date from seva's duration_days (for annual/subscription sevas)
    seva_expiry_date: str | None = None
    if seva_doc:
        duration_days = seva_doc.get("duration_days")
        if duration_days and int(duration_days) > 0:
            booking_date_raw = str(payload.get("booking_date") or "").strip()
            try:
                base_dt = datetime.fromisoformat(booking_date_raw)
            except Exception:
                base_dt = datetime.now(timezone.utc)
            seva_expiry_date = (base_dt + timedelta(days=int(duration_days))).date().isoformat()

    devotee_doc: dict[str, Any] | None = None
    devotee_id = str(payload.get("devotee_id") or "").strip()
    if devotee_id:
        devotee_doc = await get_collection("mandir_devotees").find_one(
            {"id": devotee_id, "tenant_id": tenant_id, "app_key": app_key}
        )
        if not devotee_doc:
            devotee_doc = await get_collection("mandir_devotees").find_one(
                {"id": devotee_id, "tenant_id": tenant_id}
            )

    devotee_phone = _normalize_phone(
        payload.get("devotee_phone") or payload.get("devotee_mobile") or payload.get("phone")
    )
    if devotee_doc is None and devotee_phone:
        devotee_doc = await _find_devotee_by_phone(tenant_id, app_key, devotee_phone)

    devotee_snapshot = _sanitize_mongo_doc(devotee_doc) if isinstance(devotee_doc, dict) else {}
    devotee_name = str(
        payload.get("devotee_names")
        or payload.get("devotee_name")
        or devotee_snapshot.get("name")
        or "Devotee"
    ).strip() or "Devotee"
    devotee_address = str(
        payload.get("devotee_address")
        or payload.get("address")
        or devotee_snapshot.get("address")
        or ""
    ).strip() or None
    devotee_phone = devotee_phone or _normalize_phone(devotee_snapshot.get("phone"))

    booking = {
        "id": booking_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        **{k: v for k, v in payload.items() if k not in ("id", "_id", "tenant_id", "app_key")},
        "payment_mode": payment_mode,
        "created_at": now,
        "updated_at": now,
        "status": "confirmed",
    }
    booking["seva_name"] = seva_name
    if payload.get("seva_name_local"):
        booking["seva_name_local"] = str(payload.get("seva_name_local") or "").strip()
    booking["devotee_id"] = devotee_id or str(booking.get("devotee_id") or devotee_snapshot.get("id") or "").strip() or None
    booking["devotee_name"] = devotee_name
    booking["devotee_names"] = devotee_name
    booking["devotee_phone"] = devotee_phone or None
    if devotee_address:
        booking["devotee_address"] = devotee_address
        booking["address"] = devotee_address
    if devotee_snapshot:
        booking["devotee"] = {
            "id": devotee_snapshot.get("id"),
            "name": devotee_name,
            "phone": devotee_phone or devotee_snapshot.get("phone"),
            "address": devotee_address or devotee_snapshot.get("address"),
            "city": devotee_snapshot.get("city"),
            "state": devotee_snapshot.get("state"),
            "pincode": devotee_snapshot.get("pincode"),
        }
    booking["receipt_number"] = await _next_receipt_number(
        tenant_id=tenant_id,
        app_key=app_key,
        receipt_kind="seva",
        receipt_date=booking.get("booking_date") or now,
    )
    booking["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id}/receipt/pdf"
    if seva_expiry_date:
        booking["expiry_date"] = seva_expiry_date
        booking["reminder_count"] = 0
        booking["reminder_sent_at"] = None

    col = get_collection("mandir_seva_bookings")
    try:
        await col.insert_one(booking)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save seva booking: {exc}") from exc

    if amount > 0:
        raw_account_id = payload.get("bank_account_id") or payload.get("payment_account_id")
        resolved_account_id = await _resolve_mandir_payment_account_id(
            session,
            tenant_id,
            raw_account_id,
            payment_mode,
        )
        if not resolved_account_id:
            await col.delete_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=400, detail="No valid cash/bank account is configured for seva posting")

        try:
            income_acc_id = await _resolve_mandir_income_account(session, tenant_id, "Seva Income - General")
            devotee_names = str(booking.get("devotee_names") or booking.get("devotee_name") or "Devotee")
            journal_payload = JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"Seva Booking ({seva_name}) - {devotee_names}",
                reference=booking["receipt_number"],
                lines=[
                    JournalLineIn(account_id=resolved_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount))),
                ],
            )
            await post_journal_entry(
                session=session,
                app_key=app_key,
                tenant_id=tenant_id,
                created_by="mandir_compat_system",
                payload=journal_payload,
                idempotency_key=f"sev_{booking_id}",
            )
        except Exception as exc:
            await col.delete_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=500, detail=f"Failed to post seva journal: {exc}") from exc

    return _mandir_seva_booking_view(booking)

@router.post("/sevas/bookings/quick-ticket", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_quick_ticket(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    ticket_type = str(payload.get("ticket_type") or payload.get("purpose") or payload.get("payment_purpose") or "seva").strip().lower()
    normalized_phone = _normalize_phone(payload.get("devotee_phone") or payload.get("phone") or payload.get("mobile"))

    devotee = None
    if normalized_phone:
        try:
            devotee = await _find_devotee_by_phone(tenant_id, app_key, normalized_phone)
        except Exception:
            devotee = None

    devotee_name = str(
        payload.get("devotee_name")
        or payload.get("devotee_names")
        or (devotee or {}).get("name")
        or "Walk-in Devotee"
    ).strip() or "Walk-in Devotee"

    if ticket_type in {"donation", "annadanam", "annadana", "sponsorship", "other"}:
        category_map = {
            "annadanam": "Annadanam",
            "annadana": "Annadanam",
            "sponsorship": "Sponsorship",
            "other": "General Donation",
            "donation": "General Donation",
        }
        donation_payload = {
            **payload,
            "amount": _safe_float(payload.get("amount") or payload.get("amount_paid"), 0.0),
            "devotee_name": devotee_name,
            "devotee_phone": normalized_phone,
            "phone": normalized_phone,
            "category": str(payload.get("category") or category_map.get(ticket_type, "General Donation")),
            "payment_mode": str(payload.get("payment_mode") or payload.get("payment_method") or "Cash"),
        }
        donation = await create_donation(
            payload=donation_payload,
            session=session,
            current_user=current_user,
            x_tenant_id=x_tenant_id,
            x_app_key=x_app_key,
        )
        return {
            "ticket_type": "donation",
            "autofill_found": bool(devotee),
            "devotee": devotee,
            "receipt_number": donation.get("receipt_number"),
            "receipt_pdf_url": donation.get("receipt_pdf_url"),
            "record": donation,
        }

    seva_payload = {
        **payload,
        "amount_paid": _safe_float(payload.get("amount_paid") or payload.get("amount"), 0.0),
        "devotee_name": devotee_name,
        "devotee_names": str(payload.get("devotee_names") or devotee_name),
        "devotee_phone": normalized_phone,
        "devotee_mobile": normalized_phone,
        "payment_mode": str(payload.get("payment_mode") or payload.get("payment_method") or "Cash"),
        "booking_date": str(payload.get("booking_date") or datetime.now(timezone.utc).date().isoformat()),
    }
    booking = await create_seva_booking(
        payload=seva_payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )
    return {
        "ticket_type": "seva",
        "autofill_found": bool(devotee),
        "devotee": devotee,
        "receipt_number": booking.get("receipt_number"),
        "receipt_pdf_url": booking.get("receipt_pdf_url"),
        "record": booking,
    }


@router.get("/sevas/bookings")
async def mandir_seva_bookings(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = get_collection("mandir_seva_bookings")
    fetch_limit = 500 if any([q, from_date, to_date, status]) else min(limit + offset, 500)
    docs = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("booking_date", -1).limit(fetch_limit).to_list(length=fetch_limit)
    viewed = [_mandir_seva_booking_view(doc) for doc in docs]
    if status:
        normalized_status = str(status).strip().lower()
        viewed = [row for row in viewed if str(row.get("status") or "").strip().lower() == normalized_status]
    filtered = _mandir_filter_rows(
        viewed,
        q=q,
        from_date=from_date,
        to_date=to_date,
        date_fields=("booking_date", "created_at"),
        search_fields=("receipt_number", "devotee_name", "devotee_names", "seva_name", "seva", "upi_reference_number"),
    )
    return filtered[offset:offset + limit]


@router.get("/sevas/bookings/{booking_id}/receipt/pdf")
async def get_seva_receipt_pdf(
    booking_id: str,
    lang: str | None = Query(default=None, description="Override receipt language (kannada/hindi/tamil/telugu/malayalam)"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    col = get_collection("mandir_seva_bookings")
    booking = await col.find_one({"id": str(booking_id), "tenant_id": tenant_id, "app_key": app_key})
    if booking is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")

    booking_id_text = str(booking.get("id") or booking_id).strip()
    booking["id"] = booking_id_text

    resolved_seva_name = str(booking.get("seva_name") or "").strip()
    seva_id = booking.get("seva_id")
    seva_doc: dict[str, Any] | None = None
    if seva_id:
        seva_doc = await get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id, "app_key": app_key})
        if not seva_doc:
            seva_doc = await get_collection("mandir_sevas").find_one({"id": str(seva_id), "tenant_id": tenant_id})
    if seva_doc:
        if (not resolved_seva_name or resolved_seva_name.lower() in {"seva booking", "seva"}) and seva_doc.get("name"):
            booking["seva_name"] = str(seva_doc.get("name")).strip()
        if seva_doc.get("name_kannada"):
            booking["seva_name_local"] = str(seva_doc.get("name_kannada") or "").strip()

    devotee_snapshot = booking.get("devotee") if isinstance(booking.get("devotee"), dict) else {}
    if not devotee_snapshot or not any([
        booking.get("devotee_name"),
        booking.get("devotee_names"),
        booking.get("devotee_address"),
        booking.get("address"),
    ]):
        devotee_doc: dict[str, Any] | None = None
        booking_devotee_id = str(booking.get("devotee_id") or "").strip()
        if booking_devotee_id:
            devotee_doc = await get_collection("mandir_devotees").find_one(
                {"id": booking_devotee_id, "tenant_id": tenant_id, "app_key": app_key}
            )
            if not devotee_doc:
                devotee_doc = await get_collection("mandir_devotees").find_one(
                    {"id": booking_devotee_id, "tenant_id": tenant_id}
                )

        if devotee_doc is None:
            booking_phone = _normalize_phone(
                booking.get("devotee_phone") or booking.get("devotee_mobile") or (devotee_snapshot or {}).get("phone")
            )
            if booking_phone:
                devotee_doc = await _find_devotee_by_phone(tenant_id, app_key, booking_phone)

        if devotee_doc:
            devotee_snapshot = _sanitize_mongo_doc(devotee_doc)

    if devotee_snapshot:
        resolved_devotee_name = str(
            booking.get("devotee_names")
            or booking.get("devotee_name")
            or devotee_snapshot.get("name")
            or "Devotee"
        ).strip() or "Devotee"
        resolved_devotee_address = str(
            booking.get("devotee_address")
            or booking.get("address")
            or devotee_snapshot.get("address")
            or ""
        ).strip() or None
        resolved_devotee_phone = _normalize_phone(
            booking.get("devotee_phone") or booking.get("devotee_mobile") or devotee_snapshot.get("phone")
        )
        booking["devotee_id"] = str(booking.get("devotee_id") or devotee_snapshot.get("id") or "").strip() or None
        booking["devotee_name"] = resolved_devotee_name
        booking["devotee_names"] = resolved_devotee_name
        booking["devotee_phone"] = resolved_devotee_phone or None
        if resolved_devotee_address:
            booking["devotee_address"] = resolved_devotee_address
            booking["address"] = resolved_devotee_address
        booking["devotee"] = {
            "id": devotee_snapshot.get("id"),
            "name": resolved_devotee_name,
            "phone": resolved_devotee_phone or devotee_snapshot.get("phone"),
            "address": resolved_devotee_address or devotee_snapshot.get("address"),
            "city": devotee_snapshot.get("city"),
            "state": devotee_snapshot.get("state"),
            "pincode": devotee_snapshot.get("pincode"),
        }
    receipt_number = _receipt_number_for_seva(booking)
    booking["receipt_number"] = receipt_number
    booking["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id_text}/receipt/pdf"

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "id": booking_id_text},
        {
            "$set": {
                "receipt_number": receipt_number,
                "receipt_pdf_url": booking["receipt_pdf_url"],
                "seva_name": booking.get("seva_name"),
                "seva_name_local": booking.get("seva_name_local"),
                "devotee_id": booking.get("devotee_id"),
                "devotee_name": booking.get("devotee_name"),
                "devotee_names": booking.get("devotee_names"),
                "devotee_phone": booking.get("devotee_phone"),
                "devotee_address": booking.get("devotee_address"),
                "address": booking.get("address"),
                "devotee": booking.get("devotee"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=False,
    )

    temple_profile = await _resolve_temple_receipt_profile(tenant_id=tenant_id, app_key=app_key, lang=lang)

    try:
        pdf_bytes = _generate_seva_receipt_pdf_bytes(
            booking,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    safe_receipt = "".join(ch for ch in str(receipt_number) if ch.isalnum() or ch in ("-", "_")) or booking_id_text[:8]
    filename = f"seva_receipt_{safe_receipt}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/sevas/bookings/{booking_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def cancel_seva_receipt(
    booking_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    return await _cancel_mandir_receipt_source(
        source_kind="seva",
        source_id=booking_id,
        collection_name="mandir_seva_bookings",
        id_field="id",
        idempotency_prefix="sev_",
        payload=payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )




@router.put("/sevas/bookings/{booking_id}/reschedule", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_request_seva_reschedule(
    booking_id: str,
    new_date: str = Query(...),
    reason: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    col = get_collection("mandir_seva_bookings")
    await col.update_one(
        {"id": booking_id, "tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": {
                "reschedule_pending": True,
                "status": "reschedule_pending",
                "reschedule_requested_date": new_date,
                "reschedule_reason": str(reason or "").strip() or None,
                "reschedule_requested_at": now,
                "updated_at": now,
            }
        },
        upsert=False,
    )
    doc = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    if doc is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")
    return _mandir_seva_booking_view(doc)


@router.post("/sevas/bookings/{booking_id}/approve-reschedule", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_approve_seva_reschedule(
    booking_id: str,
    approve: bool = Query(default=True),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    col = get_collection("mandir_seva_bookings")
    booking = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    if booking is None:
        raise HTTPException(status_code=404, detail="Seva booking not found")

    requested_date = str(booking.get("reschedule_requested_date") or "").strip()
    patch: dict[str, Any] = {
        "reschedule_pending": False,
        "reschedule_approved": bool(approve),
        "reschedule_decided_at": now,
        "updated_at": now,
    }
    if approve and requested_date:
        patch["booking_date"] = requested_date
        patch["status"] = "confirmed"
    else:
        patch["status"] = "confirmed"

    await col.update_one(
        {"id": booking_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )

    updated = await col.find_one({"id": booking_id, "tenant_id": tenant_id, "app_key": app_key})
    return _mandir_seva_booking_view(updated or booking)

@router.get("/sevas/reschedule/pending")
async def mandir_seva_reschedule_pending(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    app_key = resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    col = get_collection("mandir_seva_bookings")
    q = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "$or": [{"reschedule_pending": True}, {"status": "reschedule_pending"}],
    }
    docs = await col.find(q).sort("updated_at", -1).limit(limit).to_list(length=limit)
    return [_sanitize_mongo_doc(doc) for doc in docs]


@router.get("/users/me")
async def mandir_users_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Seva Reminder Config endpoints (admin — requires auth)
# ---------------------------------------------------------------------------

@router.get("/sevas/reminder-config")
async def mandir_seva_reminder_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """List all sevas with their current reminder configuration for this temple."""
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    col = get_collection("mandir_sevas")
    docs = await col.find({"tenant_id": tenant_id, "is_active": True}).to_list(length=500)
    result = []
    for doc in docs:
        result.append({
            "seva_id": str(doc.get("id") or ""),
            "seva_name": str(doc.get("name_english") or doc.get("name") or ""),
            "amount": float(doc.get("amount") or 0),
            "frequency": str(doc.get("frequency") or "one_time"),
            "duration_days": doc.get("duration_days"),
            "reminder_enabled": bool(doc.get("reminder_enabled", False)),
            "reminder_days_before": int(doc.get("reminder_days_before") or 30),
        })
    return result


@router.patch("/sevas/{seva_id}/reminder-config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_update_seva_reminder_config(
    seva_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Update reminder configuration for a specific seva (admin only).

    Accepted fields: reminder_enabled (bool), reminder_days_before (int), duration_days (int).
    """
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    col = get_collection("mandir_sevas")
    doc = await col.find_one({"id": seva_id, "tenant_id": tenant_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Seva not found")

    patch: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "reminder_enabled" in payload:
        patch["reminder_enabled"] = bool(payload["reminder_enabled"])
    if "reminder_days_before" in payload:
        days = int(payload["reminder_days_before"])
        if days < 1 or days > 365:
            raise HTTPException(status_code=400, detail="reminder_days_before must be between 1 and 365")
        patch["reminder_days_before"] = days
    if "duration_days" in payload:
        dur = int(payload["duration_days"])
        if dur < 1:
            raise HTTPException(status_code=400, detail="duration_days must be >= 1")
        patch["duration_days"] = dur

    await col.update_one({"id": seva_id, "tenant_id": tenant_id}, {"$set": patch})
    updated = await col.find_one({"id": seva_id, "tenant_id": tenant_id})
    return {
        "seva_id": seva_id,
        "seva_name": str(updated.get("name_english") or updated.get("name") or ""),
        "reminder_enabled": bool(updated.get("reminder_enabled", False)),
        "reminder_days_before": int(updated.get("reminder_days_before") or 30),
        "duration_days": updated.get("duration_days"),
    }


@router.get("/sevas/reminders/upcoming")
async def mandir_seva_reminders_upcoming(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """List all seva bookings with expiry_date within the next `days` days."""
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(days=days)

    # Get temple display name for WhatsApp messages
    temple_doc = await get_collection("mandir_temples").find_one({"tenant_id": tenant_id}) or {}
    _temple_display_name = str(temple_doc.get("temple_name") or temple_doc.get("name") or "Temple")

    col = get_collection("mandir_seva_bookings")
    docs = await col.find(
        {
            "tenant_id": tenant_id,
            "expiry_date": {"$exists": True, "$ne": None},
            "status": {"$ne": "cancelled"},
        }
    ).sort("expiry_date", 1).to_list(length=500)

    result = []
    for b in docs:
        expiry_raw = str(b.get("expiry_date") or "")
        if not expiry_raw:
            continue
        try:
            expiry_dt = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if expiry_dt > window_end:
            continue
        days_left = max(0, (expiry_dt.date() - now.date()).days)
        devotee_phone = str(b.get("devotee_phone") or b.get("devotee_mobile") or "")
        devotee_name = str(b.get("devotee_name") or b.get("devotee_names") or "Devotee")
        seva_name = str(b.get("seva_name") or "")
        amount = float(b.get("amount_paid") or b.get("amount") or 0)
        receipt_number = str(b.get("receipt_number") or b.get("id") or "")
        expiry_label = expiry_dt.strftime("%d %b %Y")

        # WhatsApp deep link — admin clicks to send pre-filled message to devotee
        from app.modules.mandir_compat.reminder_worker import build_whatsapp_reminder_link
        whatsapp_link = build_whatsapp_reminder_link(
            devotee_phone=devotee_phone,
            devotee_name=devotee_name,
            seva_name=seva_name,
            temple_name=_temple_display_name,
            expiry_date=expiry_label,
            amount=amount,
            days_left=days_left,
            receipt_number=receipt_number,
        )

        result.append({
            "booking_id": str(b.get("id") or ""),
            "receipt_number": receipt_number,
            "seva_id": str(b.get("seva_id") or ""),
            "seva_name": seva_name,
            "devotee_name": devotee_name,
            "devotee_phone": devotee_phone,
            "devotee_email": str(b.get("devotee_email") or ""),
            "amount": amount,
            "booking_date": str(b.get("booking_date") or ""),
            "expiry_date": expiry_raw,
            "expiry_date_label": expiry_label,
            "days_left": days_left,
            "reminder_count": int(b.get("reminder_count") or 0),
            "reminder_sent_at": b.get("reminder_sent_at"),
            "status": str(b.get("status") or "confirmed"),
            "whatsapp_link": whatsapp_link,
        })
    return result


@router.post("/sevas/reminders/trigger", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)

# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Seva reminders (trigger / upcoming / config)
# ROUTES : POST /sevas/reminders/trigger  GET .../upcoming  PATCH .../reminder-config  GET /users/me
# ════════════════════════════════════════════════════════════════════════

async def mandir_seva_reminders_trigger(
    payload: dict = {},
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """Manually trigger the reminder job for this tenant.

    Optional payload fields:
      - seva_id (str): limit to a single seva
      - force (bool): re-send even if reminded recently (default: False)
    """
    from app.modules.mandir_compat.reminder_worker import run_reminders_once

    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    seva_id = str(payload.get("seva_id") or "").strip() or None
    force = bool(payload.get("force", False))

    result = await run_reminders_once(
        tenant_id=tenant_id,
        seva_id=seva_id,
        force=force,
    )
    return {"ok": True, "result": result}






















