"""MandirMitra legacy chart-of-accounts import helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.modules.mandir_compat import router as mandir_router

MANDIR_COMPAT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANDIR_LEGACY_COA_PATH = MANDIR_COMPAT_DATA_DIR / "legacy_mandir_coa.json"


@lru_cache(maxsize=1)
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
        account_subtype = mandir_router._safe_optional_str(seed.get("account_subtype"))
        account_id = _coerce_account_id(seed.get("account_id"), account_code)
        parent_account_code = mandir_router._safe_optional_str(seed.get("parent_account_code"))
        cash_bank_nature = mandir_router._safe_optional_str(seed.get("cash_bank_nature"))
        if cash_bank_nature:
            cash_bank_nature = cash_bank_nature.lower()
        else:
            cash_bank_nature = _infer_cash_bank_nature(account_name, account_type, account_subtype)

        is_cash_bank = mandir_router._safe_bool(seed.get("is_cash_bank"), False) or cash_bank_nature in {"cash", "bank"} or account_subtype == "cash_bank"
        is_receivable = mandir_router._safe_bool(seed.get("is_receivable"), False) or _infer_flag(account_name, account_subtype, "receivable", "debtors", "advance")
        is_payable = mandir_router._safe_bool(seed.get("is_payable"), False) or _infer_flag(account_name, account_subtype, "payable", "creditors")
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
            "is_system_account": mandir_router._safe_bool(seed.get("is_system_account"), True),
            "is_active": mandir_router._safe_bool(seed.get("is_active"), True),
            "is_locked": mandir_router._safe_bool(seed.get("is_locked"), False),
            "account_name_kannada": seed.get("account_name_kannada"),
        }
        code_to_account_id[account_code] = account_id
        prepared_rows.append(prepared)

    for row in prepared_rows:
        parent_code = mandir_router._safe_optional_str(row.get("parent_account_code"))
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
    accounts = mandir_router.get_collection("accounting_accounts")
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
        if not mandir_router._safe_bool(existing.get("is_active"), True):
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

