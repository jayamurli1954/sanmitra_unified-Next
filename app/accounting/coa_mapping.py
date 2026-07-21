"""COA source-account mapping and onboarding helpers.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.common import (
    AccountingNotFoundError,
    AccountingValidationError,
    _accounting_scope,
    _match_confidence,
    _normalize_key,
    _q,
    _tokenize,
)
from app.accounting.models import Account, CoaMapping, CoaSourceAccount
from app.accounting.schemas import CoaMappingIn, CoaSourceAccountIn

def suggest_canonical_account(source_code: str, source_name: str, canonical_accounts: list[Account]) -> dict | None:
    if not canonical_accounts:
        return None

    normalized_code = source_code.strip().lower()
    normalized_name = _normalize_key(source_name)

    for account in canonical_accounts:
        if account.code and account.code.strip().lower() == normalized_code:
            return {
                "canonical_account_id": account.id,
                "canonical_account_name": account.name,
                "confidence": _match_confidence(0.99),
                "reason": "exact_code_match",
            }

    for account in canonical_accounts:
        if _normalize_key(account.name) == normalized_name:
            return {
                "canonical_account_id": account.id,
                "canonical_account_name": account.name,
                "confidence": _match_confidence(0.90),
                "reason": "exact_name_match",
            }

    source_tokens = _tokenize(source_name)
    best_account: Account | None = None
    best_score = 0.0

    if source_tokens:
        for account in canonical_accounts:
            account_tokens = _tokenize(account.name)
            if not account_tokens:
                continue

            union_size = len(source_tokens | account_tokens)
            if union_size == 0:
                continue

            overlap = len(source_tokens & account_tokens) / union_size
            if overlap > best_score:
                best_score = overlap
                best_account = account

    if best_account is None or best_score < 0.4:
        return None

    confidence = _match_confidence(0.5 + (best_score * 0.4))
    return {
        "canonical_account_id": best_account.id,
        "canonical_account_name": best_account.name,
        "confidence": confidence,
        "reason": "token_similarity",
    }

async def upsert_source_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    items: list[CoaSourceAccountIn],
) -> list[dict]:
    normalized_items: list[tuple[str, str, str, str | None]] = []
    by_system: dict[str, set[str]] = {}

    for item in items:
        source_system = item.source_system
        source_account_code = item.source_account_code.strip()
        source_account_name = item.source_account_name.strip()
        source_account_type = item.source_account_type

        if not source_account_code:
            raise AccountingValidationError("source_account_code cannot be empty")
        if not source_account_name:
            raise AccountingValidationError("source_account_name cannot be empty")

        normalized_items.append((source_system, source_account_code, source_account_name, source_account_type))
        by_system.setdefault(source_system, set()).add(source_account_code)

    existing_by_key: dict[tuple[str, str], CoaSourceAccount] = {}
    for source_system, codes in by_system.items():
        stmt = select(CoaSourceAccount).where(
            *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            CoaSourceAccount.source_system == source_system,
            CoaSourceAccount.source_account_code.in_(codes),
        )
        rows = (await session.execute(stmt)).scalars().all()
        for row in rows:
            existing_by_key[(row.source_system, row.source_account_code)] = row

    touched_accounts: list[CoaSourceAccount] = []
    for source_system, source_account_code, source_account_name, source_account_type in normalized_items:
        key = (source_system, source_account_code)
        existing = existing_by_key.get(key)

        if existing is None:
            existing = CoaSourceAccount(
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
                source_system=source_system,
                source_account_code=source_account_code,
                source_account_name=source_account_name,
                source_account_type=source_account_type,
                is_active=True,
            )
            session.add(existing)
            existing_by_key[key] = existing
        else:
            existing.source_account_name = source_account_name
            existing.source_account_type = source_account_type
            existing.is_active = True

        touched_accounts.append(existing)

    await session.commit()

    for source_account in touched_accounts:
        await session.refresh(source_account)

    touched_ids = [source_account.id for source_account in touched_accounts]
    mapped_stmt = select(CoaMapping.source_account_id).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.status == "active",
        CoaMapping.source_account_id.in_(touched_ids),
    )
    mapped_ids = set((await session.execute(mapped_stmt)).scalars().all())

    return [
        {
            "id": source_account.id,
            "source_system": source_account.source_system,
            "source_account_code": source_account.source_account_code,
            "source_account_name": source_account.source_account_name,
            "source_account_type": source_account.source_account_type,
            "is_active": source_account.is_active,
            "mapped": source_account.id in mapped_ids,
        }
        for source_account in touched_accounts
    ]


async def list_source_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    source_system: str | None = None,
) -> list[dict]:
    stmt = select(CoaSourceAccount).where(
        *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id)
    )
    if source_system:
        stmt = stmt.where(CoaSourceAccount.source_system == source_system)

    stmt = stmt.order_by(CoaSourceAccount.source_system.asc(), CoaSourceAccount.source_account_code.asc())

    source_accounts = list((await session.execute(stmt)).scalars().all())
    source_ids = [source_account.id for source_account in source_accounts]
    if not source_ids:
        return []

    mapped_stmt = select(CoaMapping.source_account_id).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.status == "active",
        CoaMapping.source_account_id.in_(source_ids),
    )
    mapped_ids = set((await session.execute(mapped_stmt)).scalars().all())

    return [
        {
            "id": source_account.id,
            "source_system": source_account.source_system,
            "source_account_code": source_account.source_account_code,
            "source_account_name": source_account.source_account_name,
            "source_account_type": source_account.source_account_type,
            "is_active": source_account.is_active,
            "mapped": source_account.id in mapped_ids,
        }
        for source_account in source_accounts
    ]


async def upsert_coa_mappings(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    mapped_by: str,
    items: list[CoaMappingIn],
) -> list[dict]:
    key_to_item: dict[tuple[str, str], CoaMappingIn] = {}
    source_codes_by_system: dict[str, set[str]] = {}

    for item in items:
        source_system = item.source_system
        source_account_code = item.source_account_code.strip()
        if not source_account_code:
            raise AccountingValidationError("source_account_code cannot be empty")

        key = (source_system, source_account_code)
        key_to_item[key] = item
        source_codes_by_system.setdefault(source_system, set()).add(source_account_code)

    source_lookup: dict[tuple[str, str], CoaSourceAccount] = {}
    for source_system, codes in source_codes_by_system.items():
        stmt = select(CoaSourceAccount).where(
            *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
            CoaSourceAccount.source_system == source_system,
            CoaSourceAccount.source_account_code.in_(codes),
        )
        rows = (await session.execute(stmt)).scalars().all()
        for row in rows:
            source_lookup[(row.source_system, row.source_account_code)] = row

    missing_source_keys = sorted(set(key_to_item.keys()) - set(source_lookup.keys()))
    if missing_source_keys:
        formatted = [f"{system}:{code}" for system, code in missing_source_keys]
        raise AccountingNotFoundError(f"Source accounts not found: {formatted}")

    canonical_account_ids = {item.canonical_account_id for item in key_to_item.values()}
    account_stmt = select(Account).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        Account.id.in_(canonical_account_ids),
    )
    canonical_accounts = list((await session.execute(account_stmt)).scalars().all())
    canonical_by_id = {account.id: account for account in canonical_accounts}

    missing_canonical_ids = sorted(canonical_account_ids - set(canonical_by_id.keys()))
    if missing_canonical_ids:
        raise AccountingNotFoundError(f"Canonical accounts not found for tenant: {missing_canonical_ids}")

    source_ids = [source_lookup[key].id for key in key_to_item.keys()]
    existing_stmt = select(CoaMapping).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.source_account_id.in_(source_ids),
    )
    existing_mappings = list((await session.execute(existing_stmt)).scalars().all())
    existing_by_source_id = {mapping.source_account_id: mapping for mapping in existing_mappings}

    touched_mappings: list[CoaMapping] = []
    for key, item in key_to_item.items():
        source_account = source_lookup[key]
        existing = existing_by_source_id.get(source_account.id)

        if existing is None:
            existing = CoaMapping(
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
                source_account_id=source_account.id,
                canonical_account_id=item.canonical_account_id,
                status=item.status,
                notes=item.notes,
                mapped_by=mapped_by,
                mapped_at=datetime.now(timezone.utc),
            )
            session.add(existing)
            existing_by_source_id[source_account.id] = existing
        else:
            existing.canonical_account_id = item.canonical_account_id
            existing.status = item.status
            existing.notes = item.notes
            existing.mapped_by = mapped_by
            existing.mapped_at = datetime.now(timezone.utc)

        touched_mappings.append(existing)

    await session.commit()

    for mapping in touched_mappings:
        await session.refresh(mapping)

    mapping_ids = [mapping.id for mapping in touched_mappings]
    stmt = (
        select(CoaMapping, CoaSourceAccount, Account)
        .join(CoaSourceAccount, CoaSourceAccount.id == CoaMapping.source_account_id)
        .join(Account, Account.id == CoaMapping.canonical_account_id)
        .where(
            CoaMapping.id.in_(mapping_ids),
            *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        )
        .order_by(CoaSourceAccount.source_system.asc(), CoaSourceAccount.source_account_code.asc())
    )
    rows = (await session.execute(stmt)).all()

    return [
        {
            "id": row.CoaMapping.id,
            "source_system": row.CoaSourceAccount.source_system,
            "source_account_code": row.CoaSourceAccount.source_account_code,
            "source_account_name": row.CoaSourceAccount.source_account_name,
            "canonical_account_id": row.Account.id,
            "canonical_account_name": row.Account.name,
            "status": row.CoaMapping.status,
            "notes": row.CoaMapping.notes,
        }
        for row in rows
    ]


async def list_coa_mappings(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    source_system: str | None = None,
    status: str | None = None,
) -> list[dict]:
    stmt = (
        select(CoaMapping, CoaSourceAccount, Account)
        .join(CoaSourceAccount, CoaSourceAccount.id == CoaMapping.source_account_id)
        .join(Account, Account.id == CoaMapping.canonical_account_id)
        .where(*_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id))
    )

    if source_system:
        stmt = stmt.where(CoaSourceAccount.source_system == source_system)
    if status:
        stmt = stmt.where(CoaMapping.status == status)

    stmt = stmt.order_by(CoaSourceAccount.source_system.asc(), CoaSourceAccount.source_account_code.asc())
    rows = (await session.execute(stmt)).all()

    return [
        {
            "id": row.CoaMapping.id,
            "source_system": row.CoaSourceAccount.source_system,
            "source_account_code": row.CoaSourceAccount.source_account_code,
            "source_account_name": row.CoaSourceAccount.source_account_name,
            "canonical_account_id": row.Account.id,
            "canonical_account_name": row.Account.name,
            "status": row.CoaMapping.status,
            "notes": row.CoaMapping.notes,
        }
        for row in rows
    ]


async def get_coa_mapping_gaps(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    source_system: str,
) -> list[dict]:
    source_stmt = select(CoaSourceAccount).where(
        *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaSourceAccount.source_system == source_system,
        CoaSourceAccount.is_active.is_(True),
    )
    source_accounts = list((await session.execute(source_stmt)).scalars().all())

    if not source_accounts:
        return []

    source_ids = [source_account.id for source_account in source_accounts]
    mapped_stmt = select(CoaMapping.source_account_id).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.status == "active",
        CoaMapping.source_account_id.in_(source_ids),
    )
    mapped_source_ids = set((await session.execute(mapped_stmt)).scalars().all())

    canonical_accounts = list(
        (
            await session.execute(
                select(Account).where(
                    *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id)
                )
            )
        )
        .scalars()
        .all()
    )

    gaps: list[dict] = []
    for source_account in source_accounts:
        if source_account.id in mapped_source_ids:
            continue

        suggestion = suggest_canonical_account(
            source_account.source_account_code,
            source_account.source_account_name,
            canonical_accounts,
        )

        gaps.append(
            {
                "source_system": source_account.source_system,
                "source_account_code": source_account.source_account_code,
                "source_account_name": source_account.source_account_name,
                "source_account_type": source_account.source_account_type,
                "suggestion": suggestion,
            }
        )

    return gaps


async def get_coa_onboarding_status(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    source_system: str,
) -> dict:
    source_stmt = select(CoaSourceAccount).where(
        *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaSourceAccount.source_system == source_system,
        CoaSourceAccount.is_active.is_(True),
    )
    source_accounts = list((await session.execute(source_stmt)).scalars().all())

    if not source_accounts:
        return {
            "source_system": source_system,
            "total_source_accounts": 0,
            "mapped_active": 0,
            "mapped_draft": 0,
            "unmapped": 0,
        }

    source_ids = [source_account.id for source_account in source_accounts]
    mapping_stmt = select(CoaMapping.source_account_id, CoaMapping.status).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.source_account_id.in_(source_ids),
    )
    mapping_rows = (await session.execute(mapping_stmt)).all()

    active_ids = {row.source_account_id for row in mapping_rows if row.status == "active"}
    draft_ids = {row.source_account_id for row in mapping_rows if row.status == "draft"}

    total_source_accounts = len(source_accounts)
    mapped_active = len(active_ids)
    mapped_draft = len(draft_ids - active_ids)
    unmapped = max(0, total_source_accounts - mapped_active - mapped_draft)

    return {
        "source_system": source_system,
        "total_source_accounts": total_source_accounts,
        "mapped_active": mapped_active,
        "mapped_draft": mapped_draft,
        "unmapped": unmapped,
    }


async def approve_coa_mappings(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    source_system: str,
    approved_by: str,
    source_account_codes: list[str] | None = None,
) -> dict:
    source_stmt = select(CoaSourceAccount).where(
        *_accounting_scope(CoaSourceAccount, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaSourceAccount.source_system == source_system,
        CoaSourceAccount.is_active.is_(True),
    )

    normalized_codes: set[str] | None = None
    if source_account_codes:
        normalized_codes = {code.strip() for code in source_account_codes if code.strip()}
        if not normalized_codes:
            raise AccountingValidationError("source_account_codes cannot be empty when provided")
        source_stmt = source_stmt.where(CoaSourceAccount.source_account_code.in_(normalized_codes))

    source_accounts = list((await session.execute(source_stmt)).scalars().all())
    if not source_accounts:
        raise AccountingNotFoundError("No source accounts found for approval scope")

    source_by_code = {source_account.source_account_code: source_account for source_account in source_accounts}
    if normalized_codes is not None:
        missing_codes = sorted(normalized_codes - set(source_by_code.keys()))
        if missing_codes:
            raise AccountingNotFoundError(f"Source accounts not found for approval: {missing_codes}")

    source_ids = [source_account.id for source_account in source_accounts]
    mapping_stmt = select(CoaMapping).where(
        *_accounting_scope(CoaMapping, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        CoaMapping.source_account_id.in_(source_ids),
    )
    mappings = list((await session.execute(mapping_stmt)).scalars().all())

    if not mappings:
        raise AccountingValidationError("No mappings found for approval scope")

    approved_count = 0
    now = datetime.now(timezone.utc)

    for mapping in mappings:
        if mapping.status != "active":
            mapping.status = "active"
            mapping.mapped_by = approved_by
            mapping.mapped_at = now
            approved_count += 1

    await session.commit()

    return {
        "source_system": source_system,
        "approved_count": approved_count,
    }

