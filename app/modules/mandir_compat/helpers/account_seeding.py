"""MandirMitra account seeding and SQL COA sync helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers import legacy_coa as _legacy_coa

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
def _mandir_seed_accounts() -> list[dict[str, Any]]:
    legacy = _legacy_coa._load_mandir_legacy_accounts()
    return legacy if legacy else MANDIR_DEFAULT_ACCOUNTS


def _mandir_account_view(doc: dict[str, Any]) -> dict[str, Any]:
    account_id = doc.get("account_id") or doc.get("_id")
    account_id_str = str(account_id or "")
    account_name = str(doc.get("account_name") or doc.get("name") or "Account")
    account_code = mandir_router._normalize_mandir_account_code(
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
        account_code = mandir_router._normalize_mandir_account_code(
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
            mandir_router._normalize_mandir_account_code(
                item.get("account_code") or item.get("account_id"),
                account_name=item.get("account_name") or item.get("name"),
            )
            or item.get("account_id")
            or ""
        )
    )
    return unique_docs

async def _ensure_default_mandir_accounts(tenant_id: str, app_key: str) -> int:
    result = await _legacy_coa._upsert_mandir_account_docs(
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
    prepared_rows = _legacy_coa._prepare_mandir_account_docs(seed_rows, tenant_id, "mandirmitra")
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

    existing_accounts = await mandir_router.list_accounts(session, tenant_id=tenant_id)
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
                created_acc = await mandir_router.create_account(
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
                existing_accounts = await mandir_router.list_accounts(session, tenant_id=tenant_id)
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
    await mandir_router._normalize_mandir_income_accounts(session, tenant_id)

async def _ensure_default_mandir_sql_accounts_safe(
    session: AsyncSession, tenant_id: str, *, raise_on_failure: bool = False
) -> None:
    if not hasattr(session, "execute"):
        return
    try:
        await mandir_router._ensure_default_mandir_sql_accounts(session, tenant_id)
    except Exception as exc:
        rollback = getattr(session, "rollback", None)
        if callable(rollback):
            try:
                await rollback()
            except Exception:
                pass
        if raise_on_failure:
            mandir_router.logger.error(
                "COA normalization failed for tenant %s - aborting posting: %s",
                tenant_id, exc, exc_info=True,
            )
            raise HTTPException(
                status_code=503,
                detail="Accounting setup is incomplete. Please retry in a moment or contact support.",
            ) from exc
        mandir_router.logger.warning("Skipped COA normalization for tenant %s due to: %s", tenant_id, exc)
        return

