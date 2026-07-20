"""MandirMitra platform admin and payment-account resolver helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.tenants.context import resolve_tenant_id
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.service import resolve_tenant_by_temple_id

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

    doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
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
        accounts = mandir_router.get_collection("accounting_accounts")
        await mandir_router._ensure_default_mandir_accounts(tenant_id, app_key)
        docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=200)
        for doc in docs:
            item = mandir_router._mandir_account_view(doc)
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

