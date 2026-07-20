"""MandirMitra account code and income category helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

_MANDIR_UTR_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]{3,79}$")

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

