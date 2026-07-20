
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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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
    get_cost_centre_ledger_pl,
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
from app.modules.business.dimensions import create_dimension, deactivate_dimension
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
    donation_compliance_receipt_note,
    mask_pan,
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
    'hundi collections': ('44002', 'Hundi Collections'),
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


from app.modules.mandir_compat.helpers.account_categories import (
    _MANDIR_INCOME_BUCKET_ALIASES,
    _MANDIR_INCOME_LEGACY_CODES,
    _MANDIR_LEGACY_ACCOUNT_CODE_MAP,
    _MANDIR_SPONSORSHIP_CATEGORY_MARKERS,
    _MANDIR_UTR_REFERENCE_PATTERN,
    _is_mandir_sponsorship_category,
    _mandir_cash_income_category,
    _mandir_in_kind_debit_account_target,
    _mandir_in_kind_income_category,
    _mandir_income_bucket_for_account,
    _normalize_income_category,
    _normalize_mandir_account_code,
    _normalize_public_payment_utr_reference,
)

# ════════════════════════════════════════════════════════════════════════
# SECTION: ACCOUNT CODE + CATEGORY HELPERS
# NOTE   : moved to helpers/account_categories.py; imported above.
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
    doc = await get_collection("mandir_temples").find_one(query) or {}
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
    if source_kind == "donation" and current_status == "pending_valuation":
        patch["valuation_status"] = "cancelled"
        await collection.update_one(
            {id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key},
            {"$set": patch}, upsert=False,
        )
        return _mandir_donation_view({**existing, **patch})

    inventory_reversal = None
    movement_collection = None
    if source_kind == "donation" and existing.get("inventory_movement_id"):
        movement_collection = get_collection("mandir_inventory_movements")
        receipt_movement = await movement_collection.find_one(
            {"id": str(existing["inventory_movement_id"]), "tenant_id": tenant_id, "app_key": app_key, "status": "posted"}
        )
        item = await get_collection("mandir_inventory_items").find_one(
            {"id": str(existing.get("inventory_item_id") or ""), "tenant_id": tenant_id, "app_key": app_key, "is_active": True}
        )
        if receipt_movement is None or item is None:
            raise HTTPException(status_code=409, detail="Inventory receipt evidence is unavailable for donation reversal")
        available = await _mandir_inventory_item_balance(tenant_id=tenant_id, app_key=app_key, item=item)
        receipt_quantity = Decimal(str(receipt_movement.get("quantity") or "0"))
        if available < receipt_quantity:
            raise HTTPException(status_code=409, detail="Cannot reverse donation after its inventory has been consumed")
        reversal_movement_id = f"donation-reversal-{source_id}"
        inventory_reversal = await movement_collection.find_one(
            {"id": reversal_movement_id, "tenant_id": tenant_id, "app_key": app_key}
        )
        if inventory_reversal is None:
            inventory_reversal = {
                "id": reversal_movement_id, "tenant_id": tenant_id, "app_key": app_key,
                "item_id": receipt_movement.get("item_id"), "item_name": receipt_movement.get("item_name"),
                "movement_type": "receipt_reversal", "quantity": str(receipt_quantity),
                "unit_value": str(receipt_movement.get("unit_value") or "0"),
                "total_value": str(receipt_movement.get("total_value") or "0"),
                "movement_date": datetime.now(timezone.utc).date().isoformat(),
                "source_type": "in_kind_donation_reversal", "source_id": str(source_id),
                "status": "pending_accounting", "created_by": _mandir_actor_id(current_user),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await movement_collection.insert_one(inventory_reversal)
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
    if inventory_reversal is not None and movement_collection is not None:
        await movement_collection.update_one(
            {"id": inventory_reversal["id"], "tenant_id": tenant_id, "app_key": app_key},
            {"$set": {
                "status": "posted", "journal_entry_id": int(reversal_entry.id),
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=False,
        )
        patch["inventory_reversal_movement_id"] = inventory_reversal["id"]

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


# Refund-request routes moved to routes/refunds.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.


# Default COA seed + legacy import helpers moved to helpers/*.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported at end of module.

# Safe coercions, opening balance, mongo, views, pincode, seva, devotee/UPI, and
# tenant helpers moved to helpers/*.py; re-exported at end of module.

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




# Donation/seva view helpers moved to helpers/views.py

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
# Panchang (today) route moved to routes/panchang.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Donations (GET list / POST / cancel / receipt PDF / reconcile / cleanup / export / daily|monthly reports)
# ROUTES : GET /donations/payment-accounts|categories  GET|POST /donations  GET .../receipt/pdf  POST .../cancel|reconcile-posting  DELETE .../cleanup  GET .../report/daily|monthly  GET .../export/excel|pdf
# ════════════════════════════════════════════════════════════════════════

# Donation read routes moved to routes/donations_read.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

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
    donation_type = str(payload.get("donation_type") or "cash").strip().lower() or "cash"
    if donation_type == "in_kind":
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Declared in-kind value must be greater than zero")
        if not _safe_optional_str(payload.get("in_kind_item_name") or payload.get("item_name")):
            raise HTTPException(status_code=400, detail="In-kind item name is required")
        if not _safe_optional_str(payload.get("in_kind_valuation_basis") or payload.get("valuation_basis")):
            raise HTTPException(status_code=400, detail="In-kind valuation basis is required")
    fund = None
    fund_id = str(payload.get("fund_id") or "").strip()
    if fund_id:
        fund = await get_collection("mandir_funds").find_one(
            {"id": fund_id, "tenant_id": tenant_id, "app_key": app_key, "active": True}
        )
        if fund is None:
            raise HTTPException(status_code=404, detail="Active fund not found")
        if not fund.get("accounting_dimension_id"):
            raise HTTPException(status_code=409, detail="Fund accounting dimension is not provisioned")
    festival = None
    festival_id = str(payload.get("festival_id") or "").strip()
    if festival_id:
        festival = await get_collection("mandir_festivals").find_one(
            {"id": festival_id, "tenant_id": tenant_id, "app_key": app_key, "active": True}
        )
        if festival is None:
            raise HTTPException(status_code=404, detail="Active festival not found")
    sponsorship_value = payload.get("is_sponsorship", False)
    is_sponsorship = sponsorship_value is True or str(sponsorship_value).strip().lower() in {"1", "true", "yes"}
    cash_income_category = _mandir_cash_income_category(category)
    if fund and str(fund.get("fund_type") or "").lower() in {"restricted", "corpus"}:
        cash_income_category = "Specific Purpose Donations"
    if is_sponsorship:
        cash_income_category = "Sponsorship Income"
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
    raw_payment_account_id = _safe_optional_str(payload.get("bank_account_id") or payload.get("payment_account_id"))
    compliance_config = await get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    )
    compliance = classify_donation_compliance(
        payload,
        compliance_config,
        amount=Decimal(str(amount)),
        donation_type=donation_type,
        payment_mode=payment_mode,
        donation_date=datetime.now(timezone.utc).date(),
        payment_account_id=raw_payment_account_id,
    )

    donation = {
        "donation_id": donation_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "temple_id": temple_id,
        "amount": amount,
        "category": category,
        "donation_type": donation_type,
        "in_kind_item_name": _safe_optional_str(payload.get("in_kind_item_name") or payload.get("item_name")),
        "in_kind_item_type": _safe_optional_str(payload.get("in_kind_item_type") or payload.get("item_type") or payload.get("asset_type")),
        "in_kind_quantity": _safe_optional_str(payload.get("in_kind_quantity") or payload.get("quantity")),
        "in_kind_valuation_basis": _safe_optional_str(payload.get("in_kind_valuation_basis") or payload.get("valuation_basis")),
        "event_name": _safe_optional_str(payload.get("event_name") or payload.get("festival_name")),
        "fund_id": fund_id or None,
        "fund_name": str(fund.get("name")) if fund else None,
        "fund_type": str(fund.get("fund_type")) if fund else None,
        "fund_dimension_id": str(fund.get("accounting_dimension_id")) if fund else None,
        "festival_id": festival_id or None,
        "festival_name": str(festival.get("name")) if festival else None,
        "is_sponsorship": is_sponsorship,
        "income_category": cash_income_category,
        "status": "pending_valuation" if donation_type == "in_kind" else "posted",
        "valuation_status": "pending_approval" if donation_type == "in_kind" else None,
        "inventory_item_id": _safe_optional_str(payload.get("inventory_item_id")),
        "inventory_quantity": _safe_optional_str(payload.get("inventory_quantity")),
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
        "created_by": _mandir_actor_id(current_user),
        "created_at": now,
        **compliance,
    }

    donation["id"] = donation_id
    donation["receipt_number"] = await _next_receipt_number(
        tenant_id=tenant_id,
        app_key=app_key,
        receipt_kind="donation",
        receipt_date=now,
    )
    donation["receipt_pdf_url"] = f"/api/v1/donations/{donation_id}/receipt/pdf"

    col = get_collection("mandir_donations")
    try:
        await col.insert_one(donation)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save donation: {exc}") from exc

    # Valued donations and sponsorships must post into accounting; otherwise reports and TB diverge.
    if amount > 0 and donation_type != "in_kind":
        try:
            raw_account_id = raw_payment_account_id
            debit_account_id = await _resolve_mandir_payment_account_id(
                session,
                tenant_id,
                raw_account_id,
                payment_mode,
            )
            if not debit_account_id:
                await col.delete_one({"donation_id": donation_id, "tenant_id": tenant_id, "app_key": app_key})
                raise HTTPException(status_code=400, detail="No valid cash/bank account is configured for donation posting")
            income_category = cash_income_category

            income_acc_id = await _resolve_mandir_income_account(session, tenant_id, income_category)
            journal_payload = JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"{category} from {donation['devotee']['name']}",
                reference=donation["receipt_number"],
                source_module="mandirmitra",
                source_document_type="donation",
                source_document_id=donation_id,
                lines=[
                    JournalLineIn(account_id=debit_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(
                        account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount)),
                        cost_center_id=str(fund.get("accounting_dimension_id")) if fund else None,
                    ),
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


@router.post("/donations/{donation_id}/valuation/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_in_kind_valuation(
    donation_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="in-kind valuation approval",
    )
    collection = get_collection("mandir_donations")
    query = {"donation_id": donation_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    donation = await collection.find_one(query)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    if str(donation.get("donation_type") or "").lower() != "in_kind":
        raise HTTPException(status_code=409, detail="Only in-kind donations require valuation approval")
    if donation.get("status") == "posted" and donation.get("valuation_status") == "approved":
        return {**_mandir_donation_view(donation), "_idempotent": True}
    if donation.get("valuation_status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending valuations can be approved")
    actor = _mandir_actor_id(current_user)
    if actor == str(donation.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Valuation maker and approver must be different users")
    try:
        approved_amount = Decimal(str(payload.get("approved_amount") or donation.get("amount") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid approved_amount is required") from exc
    if not approved_amount.is_finite() or approved_amount <= 0:
        raise HTTPException(status_code=400, detail="Approved value must be greater than zero")
    approval_basis = str(payload.get("approval_basis") or "").strip()
    if len(approval_basis) < 3:
        raise HTTPException(status_code=400, detail="Valuation approval basis is required")

    await _ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    inventory_enabled = await _mandir_inventory_accounting_enabled(context.tenant_id, context.app_key)
    account_code, account_name, account_type = _mandir_in_kind_debit_account_target(
        donation, donation.get("category"), inventory_accounting_enabled=inventory_enabled,
    )
    debit_account_id = await _resolve_or_create_mandir_account(
        session, context.tenant_id, code=account_code, name=account_name, account_type=account_type,
        classification="nominal" if account_type == "expense" else "real",
    )
    income_category = (
        "In-Kind Sponsorship Income"
        if donation.get("is_sponsorship")
        else _mandir_in_kind_income_category(donation.get("category"))
    )
    income_account_id = await _resolve_mandir_income_account(session, context.tenant_id, income_category)
    dimension_id = str(donation.get("fund_dimension_id") or "") or None

    movement = None
    movement_collection = get_collection("mandir_inventory_movements")
    if account_code in {"14003", "14004"}:
        item_id = str(payload.get("inventory_item_id") or donation.get("inventory_item_id") or "").strip()
        item = await get_collection("mandir_inventory_items").find_one(
            {"id": item_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True}
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Active inventory item is required for inventory-valued donation")
        try:
            quantity = Decimal(str(payload.get("approved_quantity") or donation.get("inventory_quantity") or "0")).quantize(Decimal("0.001"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Valid approved_quantity is required") from exc
        if not quantity.is_finite() or quantity <= 0:
            raise HTTPException(status_code=400, detail="Approved inventory quantity must be greater than zero")
        movement = {
            "id": str(uuid4()), "tenant_id": context.tenant_id, "app_key": context.app_key,
            "item_id": item_id, "item_name": item.get("name"), "movement_type": "receipt",
            "quantity": str(quantity), "unit_value": str((approved_amount / quantity).quantize(Decimal("0.01"))),
            "total_value": str(approved_amount), "movement_date": datetime.now(timezone.utc).date().isoformat(),
            "source_type": "in_kind_donation", "source_id": donation_id,
            "status": "pending_accounting", "created_by": actor, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await movement_collection.insert_one(movement)

    try:
        journal, _created = await post_journal_entry(
            session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
            payload=JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"Approved in-kind valuation: {donation.get('in_kind_item_name') or donation.get('category')}",
                reference=str(donation.get("receipt_number")), source_module="mandirmitra",
                source_document_type="in_kind_donation", source_document_id=donation_id,
                lines=[
                    JournalLineIn(
                        account_id=debit_account_id, debit=approved_amount, credit=Decimal("0"),
                        cost_center_id=dimension_id,
                    ),
                    JournalLineIn(
                        account_id=income_account_id, debit=Decimal("0"), credit=approved_amount,
                        cost_center_id=dimension_id,
                    ),
                ],
            ),
            idempotency_key=f"don_{donation_id}",
        )
    except Exception:
        if movement:
            await movement_collection.update_one(
                {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                {"$set": {"status": "accounting_failed"}}, upsert=False,
            )
        raise

    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "amount": float(approved_amount), "status": "posted", "valuation_status": "approved",
        "approved_value": str(approved_amount), "valuation_approval_basis": approval_basis,
        "valuation_approved_by": actor, "valuation_approved_at": now,
        "journal_entry_id": int(journal.id), "updated_at": now,
    }
    if movement:
        patch.update({"inventory_item_id": movement["item_id"], "inventory_quantity": movement["quantity"], "inventory_movement_id": movement["id"]})
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
        if movement:
            await movement_collection.update_one(
                {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                {"$set": {"status": "posted", "journal_entry_id": int(journal.id), "posted_at": now}}, upsert=False,
            )
    except Exception as exc:
        await reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
            journal_id=int(journal.id), created_by=actor, reason="Compensate failed in-kind valuation persistence",
            idempotency_key=f"don_{donation_id}_valuation_compensation",
        )
        if movement:
            try:
                await movement_collection.update_one(
                    {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                    {"$set": {"status": "compensated", "updated_at": now}}, upsert=False,
                )
            except Exception:
                logger.exception("Failed to mark compensated inventory receipt donation=%s", donation_id)
        try:
            await collection.update_one(
                query, {"$set": {"status": "pending_valuation", "valuation_status": "pending_approval", "updated_at": now}},
                upsert=False,
            )
        except Exception:
            logger.exception("Failed to restore pending valuation state donation=%s", donation_id)
        raise HTTPException(status_code=500, detail="Valuation persistence failed; accounting was reversed") from exc
    return _mandir_donation_view({**donation, **patch})


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


# Devotee routes moved to routes/devotees.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.


# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Sevas (GET / POST / PUT / DELETE / import / lists / dropdown-options / payment-accounts)
# ROUTES : GET /sevas  POST .../sevas  PUT|DELETE .../sevas/{seva_id}  GET|POST .../import  GET .../priests|dropdown-options|payment-accounts
# ════════════════════════════════════════════════════════════════════════

# Seva routes moved to routes/sevas.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Temple routes moved to routes/temples.py

# Accounts / COA routes moved to routes/accounts.py

# Misc compat routes moved to routes/misc_compat.py

# Hundi routes moved to routes/hundi.py

# Inventory routes moved to routes/inventory.py

# Journal routes moved to routes/journal_entries.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# Login and opening balance routes moved to routes/login_opening.py




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



# Pincode route moved to routes/pincode.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# ════════════════════════════════════════════════════════════════════════
# Reports routes moved to routes/reports.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Role permissions (GET list / PUT / GET assignable)
# ROUTES : GET /role-permissions  PUT .../role-permissions/{role_key}  GET .../assignable
# ════════════════════════════════════════════════════════════════════════
# Role permission routes moved to routes/role_permissions.py

# Setup wizard and temple admin routes moved to routes/temples_mgmt.py

# UPI routes moved to routes/upi.py

# Public portal routes moved to routes/public.py

# User routes moved to routes/users.py

# ════════════════════════════════════════════════════════════════════════
# SECTION: ROUTES: Seva bookings (POST / quick-ticket / GET / receipt PDF / cancel / reschedule / approve)
# ROUTES : POST /sevas/bookings  POST .../quick-ticket  GET .../bookings  GET .../receipt/pdf  POST .../cancel  PUT .../reschedule  POST .../approve-reschedule  GET .../pending
# ════════════════════════════════════════════════════════════════════════

# Seva booking routes moved to routes/seva_bookings.py

# Seva reminder routes moved to routes/seva_reminders.py

# GET /users/me moved to routes/users.py

# Refund-request routes moved to routes/refunds.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported for route
# registration and for tests that call handlers via mandir_router.<name>.
from app.modules.mandir_compat.routes.refunds import (  # noqa: E402
    _audit_mandir_refund_event as _audit_mandir_refund_event,
    approve_mandir_refund_request as approve_mandir_refund_request,
    create_mandir_refund_request as create_mandir_refund_request,
    list_mandir_refund_requests as list_mandir_refund_requests,
    mandir_export_refunds_csv as mandir_export_refunds_csv,
    mandir_report_refunds as mandir_report_refunds,
    reject_mandir_refund_request as reject_mandir_refund_request,
    settle_mandir_refund_request as settle_mandir_refund_request,
)

# Dashboard, panchang, and devotee routes moved to routes/*.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); side-effect import registers handlers.

from app.modules.mandir_compat.receipt_pdf import (
    _amount_to_kannada_words as _amount_to_kannada_words,
    _amount_to_words as _amount_to_words,
    _amount_words_receipt_line as _amount_words_receipt_line,
    _as_text as _as_text,
    _bilingual_label as _bilingual_label,
    _build_receipt_pdf_bytes as _build_receipt_pdf_bytes,
    _build_receipt_pdf_bytes_pillow as _build_receipt_pdf_bytes_pillow,
    _build_receipt_pdf_bytes_weasy as _build_receipt_pdf_bytes_weasy,
    _build_temple_receipt_profile as _build_temple_receipt_profile,
    _compose_receipt_address_line as _compose_receipt_address_line,
    _compose_receipt_line_description as _compose_receipt_line_description,
    _compose_receipt_party_name as _compose_receipt_party_name,
    _default_labels as _default_labels,
    _detect_script as _detect_script,
    _extract_seva_line_items as _extract_seva_line_items,
    _first_non_empty_text as _first_non_empty_text,
    _format_payment_mode_for_receipt as _format_payment_mode_for_receipt,
    _format_payment_mode_local_for_receipt as _format_payment_mode_local_for_receipt,
    _format_receipt_date as _format_receipt_date,
    _generate_donation_receipt_pdf_bytes as _generate_donation_receipt_pdf_bytes,
    _generate_seva_receipt_pdf_bytes as _generate_seva_receipt_pdf_bytes,
    _integer_to_kannada_words as _integer_to_kannada_words,
    _integer_to_words as _integer_to_words,
    _name_prefix_from_sources as _name_prefix_from_sources,
    _normalize_local_language as _normalize_local_language,
    _receipt_paragraph as _receipt_paragraph,
    _receipt_payment_line as _receipt_payment_line,
    _resolve_font_name as _resolve_font_name,
    _resolve_temple_receipt_profile as _resolve_temple_receipt_profile,
    _split_amount as _split_amount,
)

import app.modules.mandir_compat.routes.funds  # noqa: E402, F401
import app.modules.mandir_compat.routes.festivals  # noqa: E402, F401
from app.modules.mandir_compat.routes.funds import (  # noqa: E402
    approve_mandir_fund_opening_balance as approve_mandir_fund_opening_balance,
    approve_mandir_fund_transfer as approve_mandir_fund_transfer,
    cancel_mandir_fund_opening_balance as cancel_mandir_fund_opening_balance,
    cancel_mandir_fund_transfer as cancel_mandir_fund_transfer,
    create_mandir_fund as create_mandir_fund,
    create_mandir_fund_opening_balance as create_mandir_fund_opening_balance,
    create_mandir_fund_transfer as create_mandir_fund_transfer,
    list_mandir_fund_opening_balances as list_mandir_fund_opening_balances,
    list_mandir_fund_transfers as list_mandir_fund_transfers,
    list_mandir_funds as list_mandir_funds,
)
from app.modules.mandir_compat.routes.festivals import (  # noqa: E402
    create_mandir_festival as create_mandir_festival,
    list_mandir_festivals as list_mandir_festivals,
)



# Shared helpers moved to helpers/*.py (batch 8); re-exported for route modules and tests.
from app.modules.mandir_compat.helpers.coercions import (
    _normalize_phone as _normalize_phone,
    _parse_iso_datetime as _parse_iso_datetime,
    _parse_opening_balance_decimal as _parse_opening_balance_decimal,
    _safe_bool as _safe_bool,
    _safe_float as _safe_float,
    _safe_optional_float as _safe_optional_float,
    _safe_optional_int as _safe_optional_int,
    _safe_optional_str as _safe_optional_str,
)
from app.modules.mandir_compat.helpers.opening_balance import (
    _current_opening_balance_net as _current_opening_balance_net,
    _find_or_create_opening_balance_offset_account as _find_or_create_opening_balance_offset_account,
    _parse_opening_balance_rows as _parse_opening_balance_rows,
)
from app.modules.mandir_compat.helpers.mongo_utils import (
    _sanitize_mongo_doc as _sanitize_mongo_doc,
)
from app.modules.mandir_compat.helpers.views import (
    _mandir_donation_view as _mandir_donation_view,
    _mandir_filter_rows as _mandir_filter_rows,
    _mandir_row_date_text as _mandir_row_date_text,
    _mandir_row_matches_search as _mandir_row_matches_search,
    _mandir_seva_booking_view as _mandir_seva_booking_view,
    _receipt_number_for_donation as _receipt_number_for_donation,
    _receipt_number_for_seva as _receipt_number_for_seva,
)
from app.modules.mandir_compat.helpers.pincode import (
    MANDIR_PINCODE_FALLBACKS as MANDIR_PINCODE_FALLBACKS,
    _lookup_pincode_city_state as _lookup_pincode_city_state,
    _normalize_pincode as _normalize_pincode,
    _to_positive_int as _to_positive_int,
)
from app.modules.mandir_compat.helpers.seva_booking import (
    _compute_seva_available_today as _compute_seva_available_today,
    _count_seva_bookings_for_date as _count_seva_bookings_for_date,
    _normalize_seva_availability as _normalize_seva_availability,
    _normalize_seva_category as _normalize_seva_category,
    _normalize_seva_day as _normalize_seva_day,
    _parse_booking_date as _parse_booking_date,
    _resolve_export_window as _resolve_export_window,
    _resolve_report_date_window as _resolve_report_date_window,
    _today_weekday_js_index as _today_weekday_js_index,
    _validate_seva_booking_capacity as _validate_seva_booking_capacity,
    _validate_seva_booking_date as _validate_seva_booking_date,
    _weekday_js_index_for_date as _weekday_js_index_for_date,
)
from app.modules.mandir_compat.helpers.seva_builders import (
    _build_seva_item as _build_seva_item,
    _build_seva_patch as _build_seva_patch,
    _canonical_seva_name as _canonical_seva_name,
    _dashboard_posted_stats as _dashboard_posted_stats,
    _seva_import_template_csv as _seva_import_template_csv,
    _serialize_seva_doc as _serialize_seva_doc,
)
from app.modules.mandir_compat.helpers.devotees_upi import (
    _build_upi_intent_uri as _build_upi_intent_uri,
    _find_devotee_by_phone as _find_devotee_by_phone,
    _mandir_upi_payment_view as _mandir_upi_payment_view,
    _upi_receipt_number as _upi_receipt_number,
    _upsert_devotee_from_contribution as _upsert_devotee_from_contribution,
)
from app.modules.mandir_compat.helpers.tenant_platform import (
    _assert_platform_can_write_tenant as _assert_platform_can_write_tenant,
    _is_platform_super_admin as _is_platform_super_admin,
    _payment_accounts as _payment_accounts,
    _resolve_tenant_for_mandir_request as _resolve_tenant_for_mandir_request,
)

from app.modules.mandir_compat.helpers.legacy_coa import (
    _coerce_account_id as _coerce_account_id,
    _infer_cash_bank_nature as _infer_cash_bank_nature,
    _infer_flag as _infer_flag,
    _load_mandir_legacy_accounts as _load_mandir_legacy_accounts,
    _prepare_mandir_account_docs as _prepare_mandir_account_docs,
    _upsert_mandir_account_docs as _upsert_mandir_account_docs,
)
from app.modules.mandir_compat.helpers.account_seeding import (
    MANDIR_DEFAULT_ACCOUNTS as MANDIR_DEFAULT_ACCOUNTS,
    _dedupe_mandir_account_docs as _dedupe_mandir_account_docs,
    _ensure_default_mandir_accounts as _ensure_default_mandir_accounts,
    _ensure_default_mandir_sql_accounts as _ensure_default_mandir_sql_accounts,
    _ensure_default_mandir_sql_accounts_safe as _ensure_default_mandir_sql_accounts_safe,
    _mandir_account_view as _mandir_account_view,
    _mandir_seed_accounts as _mandir_seed_accounts,
    _sync_mandir_sql_accounts_from_seed as _sync_mandir_sql_accounts_from_seed,
)

import app.modules.mandir_compat.routes.sevas  # noqa: E402, F401
import app.modules.mandir_compat.routes.temples  # noqa: E402, F401
import app.modules.mandir_compat.routes.accounts  # noqa: E402, F401
from app.modules.mandir_compat.routes.sevas import (
    create_seva as create_seva,
    delete_seva as delete_seva,
    import_sevas as import_sevas,
    list_sevas as list_sevas,
    seva_date_availability as seva_date_availability,
    seva_dropdown_options as seva_dropdown_options,
    seva_import_template as seva_import_template,
    seva_payment_accounts as seva_payment_accounts,
    seva_priests as seva_priests,
    update_seva as update_seva,
)
from app.modules.mandir_compat.routes.temples import (
    get_current_temple as get_current_temple,
    update_current_temple as update_current_temple,
)
from app.modules.mandir_compat.routes.accounts import (
    mandir_accounts_hierarchy as mandir_accounts_hierarchy,
    mandir_accounts_import_legacy as mandir_accounts_import_legacy,
    mandir_accounts_initialize_default as mandir_accounts_initialize_default,
    mandir_accounts_list as mandir_accounts_list,
    mandir_accounts_update as mandir_accounts_update,
)



import app.modules.mandir_compat.routes.journal_entries  # noqa: E402, F401
import app.modules.mandir_compat.routes.login_opening  # noqa: E402, F401
import app.modules.mandir_compat.routes.role_permissions  # noqa: E402, F401
import app.modules.mandir_compat.routes.temples_mgmt  # noqa: E402, F401
import app.modules.mandir_compat.routes.upi  # noqa: E402, F401
import app.modules.mandir_compat.routes.public  # noqa: E402, F401
import app.modules.mandir_compat.routes.users  # noqa: E402, F401
from app.modules.mandir_compat.routes.journal_entries import (
    _mandir_journal_entry_view as _mandir_journal_entry_view,
    _normalize_mandir_journal_lines as _normalize_mandir_journal_lines,
    _parse_journal_entry_date as _parse_journal_entry_date,
    _resolve_sql_account_for_journal_line as _resolve_sql_account_for_journal_line,
    _validate_mandir_journal_cash_balance as _validate_mandir_journal_cash_balance,
    mandir_cancel_journal_entry as mandir_cancel_journal_entry,
    mandir_create_journal_entry as mandir_create_journal_entry,
    mandir_journal_accounts_payable as mandir_journal_accounts_payable,
    mandir_journal_accounts_receivable as mandir_journal_accounts_receivable,
    mandir_journal_balance_sheet as mandir_journal_balance_sheet,
    mandir_journal_bank_book as mandir_journal_bank_book,
    mandir_journal_cash_book as mandir_journal_cash_book,
    mandir_journal_category_income as mandir_journal_category_income,
    mandir_journal_day_book as mandir_journal_day_book,
    mandir_journal_drilldown as mandir_journal_drilldown,
    mandir_journal_entries as mandir_journal_entries,
    mandir_journal_income_expenditure as mandir_journal_income_expenditure,
    mandir_journal_ledger as mandir_journal_ledger,
    mandir_journal_profit_loss as mandir_journal_profit_loss,
    mandir_journal_receipts_payments as mandir_journal_receipts_payments,
    mandir_journal_top_donors as mandir_journal_top_donors,
    mandir_journal_trial_balance as mandir_journal_trial_balance,
    mandir_post_journal_entry as mandir_post_journal_entry,
    mandir_update_journal_entry as mandir_update_journal_entry,
)
from app.modules.mandir_compat.routes.login_opening import (
    mandir_legacy_login as mandir_legacy_login,
    mandir_opening_balances_import as mandir_opening_balances_import,
    mandir_opening_balances_template as mandir_opening_balances_template,
)
from app.modules.mandir_compat.routes.role_permissions import (
    mandir_role_permissions as mandir_role_permissions,
    mandir_role_permissions_assignable as mandir_role_permissions_assignable,
    mandir_role_permissions_update as mandir_role_permissions_update,
)
from app.modules.mandir_compat.routes.temples_mgmt import (
    _mandir_compliance_report as _mandir_compliance_report,
    _mandir_temple_collection_counts as _mandir_temple_collection_counts,
    _mandir_tenant_app_query as _mandir_tenant_app_query,
    _resolve_temple_target_tenant as _resolve_temple_target_tenant,
    get_mandir_donation_compliance_config as get_mandir_donation_compliance_config,
    update_mandir_donation_compliance_config as update_mandir_donation_compliance_config,
    mandir_activate_temple as mandir_activate_temple,
    mandir_deactivate_temple as mandir_deactivate_temple,
    mandir_remove_temple as mandir_remove_temple,
    mandir_remove_temple_preview as mandir_remove_temple_preview,
    mandir_report_80g_readiness as mandir_report_80g_readiness,
    mandir_report_fcra_readiness as mandir_report_fcra_readiness,
    mandir_setup_wizard_status as mandir_setup_wizard_status,
    mandir_temples as mandir_temples,
    mandir_temples_module_config as mandir_temples_module_config,
    mandir_temples_module_config_update as mandir_temples_module_config_update,
    mandir_temples_onboard as mandir_temples_onboard,
    mandir_temples_upload as mandir_temples_upload,
)
from app.modules.mandir_compat.routes.upi import (
    _mandir_upi_config_view as _mandir_upi_config_view,
    mandir_public_upi_intent as mandir_public_upi_intent,
    mandir_upi_payments as mandir_upi_payments,
    mandir_upi_payments_config as mandir_upi_payments_config,
    mandir_upi_payments_config_update as mandir_upi_payments_config_update,
    mandir_upi_quick_log as mandir_upi_quick_log,
)
from app.modules.mandir_compat.routes.public import (
    _normalize_public_donation_categories as _normalize_public_donation_categories,
    mandir_correct_public_payment as mandir_correct_public_payment,
    mandir_get_version as mandir_get_version,
    mandir_list_public_payments as mandir_list_public_payments,
    mandir_public_create_seva_payment as mandir_public_create_seva_payment,
    mandir_public_devotee_autofill as mandir_public_devotee_autofill,
    mandir_public_donation_categories as mandir_public_donation_categories,
    mandir_public_list_temples as mandir_public_list_temples,
    mandir_public_payment_exceptions as mandir_public_payment_exceptions,
    mandir_public_payment_status as mandir_public_payment_status,
    mandir_public_pincode_lookup as mandir_public_pincode_lookup,
    mandir_public_temple_info as mandir_public_temple_info,
    mandir_public_temple_sevas as mandir_public_temple_sevas,
    mandir_reject_public_payment as mandir_reject_public_payment,
    mandir_verify_public_payment as mandir_verify_public_payment,
)

import app.modules.mandir_compat.routes.pincode  # noqa: E402, F401
import app.modules.mandir_compat.routes.seva_bookings  # noqa: E402, F401
import app.modules.mandir_compat.routes.seva_reminders  # noqa: E402, F401
from app.modules.mandir_compat.routes.pincode import (
    mandir_pincode_lookup as mandir_pincode_lookup,
)
from app.modules.mandir_compat.routes.seva_bookings import (
    cancel_seva_receipt as cancel_seva_receipt,
    create_quick_ticket as create_quick_ticket,
    create_seva_booking as create_seva_booking,
    get_seva_receipt_pdf as get_seva_receipt_pdf,
    mandir_approve_seva_reschedule as mandir_approve_seva_reschedule,
    mandir_request_seva_reschedule as mandir_request_seva_reschedule,
    mandir_seva_bookings as mandir_seva_bookings,
    mandir_seva_reschedule_pending as mandir_seva_reschedule_pending,
)
from app.modules.mandir_compat.routes.seva_reminders import (
    mandir_seva_reminder_config as mandir_seva_reminder_config,
    mandir_seva_reminders_trigger as mandir_seva_reminders_trigger,
    mandir_seva_reminders_upcoming as mandir_seva_reminders_upcoming,
    mandir_update_seva_reminder_config as mandir_update_seva_reminder_config,
)

from app.modules.mandir_compat.routes.users import (
    mandir_update_user_profile as mandir_update_user_profile,
    mandir_users as mandir_users,
    mandir_users_me as mandir_users_me,
)

import app.modules.mandir_compat.routes.donations_read  # noqa: E402, F401
import app.modules.mandir_compat.routes.misc_compat  # noqa: E402, F401
import app.modules.mandir_compat.routes.hundi  # noqa: E402, F401
import app.modules.mandir_compat.routes.inventory  # noqa: E402, F401
import app.modules.mandir_compat.routes.reports  # noqa: E402, F401
from app.modules.mandir_compat.routes.donations_read import (
    donations_categories as donations_categories,
    donations_payment_accounts as donations_payment_accounts,
    get_donation_receipt_pdf as get_donation_receipt_pdf,
    list_donations as list_donations,
)
from app.modules.mandir_compat.routes.misc_compat import _ok as _ok
from app.modules.mandir_compat.routes.hundi import (
    approve_mandir_hundi_opening as approve_mandir_hundi_opening,
    cancel_mandir_hundi_opening as cancel_mandir_hundi_opening,
    create_mandir_hundi_master as create_mandir_hundi_master,
    create_mandir_hundi_opening as create_mandir_hundi_opening,
    mandir_hundi_masters as mandir_hundi_masters,
    mandir_hundi_openings as mandir_hundi_openings,
)
from app.modules.mandir_compat.routes.inventory import (
    _mandir_inventory_item_balance as _mandir_inventory_item_balance,
    _mandir_inventory_item_position as _mandir_inventory_item_position,
    approve_mandir_inventory_consumption as approve_mandir_inventory_consumption,
    cancel_mandir_inventory_consumption as cancel_mandir_inventory_consumption,
    create_mandir_inventory_consumption as create_mandir_inventory_consumption,
    list_mandir_inventory_consumptions as list_mandir_inventory_consumptions,
    list_mandir_inventory_movements as list_mandir_inventory_movements,
    mandir_create_inventory_item as mandir_create_inventory_item,
    mandir_delete_inventory_item as mandir_delete_inventory_item,
    mandir_inventory_items as mandir_inventory_items,
    mandir_inventory_stock_balances as mandir_inventory_stock_balances,
    mandir_inventory_summary as mandir_inventory_summary,
    mandir_update_inventory_item as mandir_update_inventory_item,
)
from app.modules.mandir_compat.routes.reports import (
    _mandir_donation_designation_report as _mandir_donation_designation_report,
    _mandir_fund_subledger_data as _mandir_fund_subledger_data,
    mandir_donations_daily_report as mandir_donations_daily_report,
    mandir_donations_export_excel as mandir_donations_export_excel,
    mandir_donations_export_pdf as mandir_donations_export_pdf,
    mandir_donations_monthly_report as mandir_donations_monthly_report,
    mandir_report_donations_category_wise as mandir_report_donations_category_wise,
    mandir_report_donations_detailed as mandir_report_donations_detailed,
    mandir_report_donations_festival_wise as mandir_report_donations_festival_wise,
    mandir_report_donations_fund_wise as mandir_report_donations_fund_wise,
    mandir_report_fund_subledger as mandir_report_fund_subledger,
    mandir_report_funds_as_of as mandir_report_funds_as_of,
    mandir_report_sevas_detailed as mandir_report_sevas_detailed,
    mandir_report_sevas_schedule as mandir_report_sevas_schedule,
)

import app.modules.mandir_compat.routes.dashboard  # noqa: E402, F401
import app.modules.mandir_compat.routes.panchang  # noqa: E402, F401
import app.modules.mandir_compat.routes.devotees  # noqa: E402, F401






















