"""MandirMitra account resolver helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Important for tests:
- These helpers call other helpers via `mandir_router.<name>` so monkeypatching
  `app.modules.mandir_compat.router.<name>` continues to affect runtime behavior.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.accounting.service import create_account, list_accounts
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers.account_categories import (
    _mandir_in_kind_debit_account_target,
    _mandir_income_bucket_for_account,
    _MANDIR_CANONICAL_INCOME_CODES,
    _normalize_income_category,
)


async def _normalize_mandir_income_accounts(session: AsyncSession, tenant_id: str) -> dict[str, int]:
    canonical_targets = {
        "donation": ("44001", "General Donations"),
        "seva": ("42002", "Seva Income - General"),
    }

    accounts = await list_accounts(session, tenant_id=tenant_id)
    income_accounts = [acc for acc in accounts if str(acc.type or "").strip().lower() == "income"]

    canonical_by_bucket: dict[str, Account] = {}
    dirty = False
    remapped_lines = 0

    for bucket, (target_code, target_name) in canonical_targets.items():
        canonical = next((acc for acc in income_accounts if str(acc.code or "").strip() == target_code), None)

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
                candidate.type = "income"
                candidate.classification = "nominal"
                canonical = candidate
                dirty = True
            else:
                canonical = await create_account(
                    session,
                    tenant_id=tenant_id,
                    code=target_code,
                    name=target_name,
                    account_type="income",
                    classification="nominal",
                    is_cash_bank=False,
                    is_receivable=False,
                    is_payable=False,
                )
                accounts = await list_accounts(session, tenant_id=tenant_id)
                income_accounts = [acc for acc in accounts if str(acc.type or "").strip().lower() == "income"]

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

    return {"remapped_lines": remapped_lines}


async def _resolve_mandir_income_account(session: AsyncSession, tenant_id: str, category_name: str) -> int:
    normalized_category = _normalize_income_category(category_name)
    preferred_code, preferred_name = _MANDIR_CANONICAL_INCOME_CODES.get(
        normalized_category,
        ("42002", "Seva Income - General")
        if any(token in normalized_category for token in ("seva", "pooja"))
        else ("44001", "General Donations"),
    )

    await mandir_router._normalize_mandir_income_accounts(session, tenant_id)

    accounts = await list_accounts(session, tenant_id=tenant_id)
    for acc in accounts:
        if str(acc.type or "").strip().lower() == "income" and str(acc.code or "").strip() == preferred_code:
            return int(acc.id)

    new_acc = await create_account(
        session,
        tenant_id=tenant_id,
        code=preferred_code,
        name=preferred_name,
        account_type="income",
        classification="nominal",
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
    doc = await mandir_router.get_collection("mandir_temples").find_one(query) or {}
    return bool(doc.get("module_inventory_enabled", False))


async def _resolve_mandir_in_kind_debit_account(
    session: AsyncSession,
    tenant_id: str,
    payload: dict[str, Any],
    category_name: Any,
    *,
    app_key: str = "mandirmitra",
) -> int:
    inventory_enabled = await mandir_router._mandir_inventory_accounting_enabled(tenant_id, app_key)
    code, name, account_type = _mandir_in_kind_debit_account_target(
        payload,
        category_name,
        inventory_accounting_enabled=inventory_enabled,
    )
    classification = "nominal" if account_type == "expense" else "real"
    return await mandir_router._resolve_or_create_mandir_account(
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
        maybe_id = mandir_router._safe_optional_int(raw_value)
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
        code_candidate = mandir_router._normalize_mandir_account_code(code_candidate)

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

