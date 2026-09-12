"""Legacy COA CSV preview and user-confirmed map-or-create decisions.

The system suggests MitraBooks accounts. Nothing is mapped or created until
the user confirms. Each confirm writes an append-only decision row plus a
core audit event so legacy codes remain searchable.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.coa_mapping import suggest_canonical_account
from app.accounting.common import AccountingNotFoundError, AccountingValidationError, _accounting_scope
from app.accounting.models import Account, CoaMapping, CoaMappingDecision, CoaSourceAccount
from app.accounting.schemas import (
    CoaSourceAccountIn,
    LegacyCoaDecisionIn,
    SourceSystem,
)
from app.core.audit.service import log_audit_event

_logger = logging.getLogger(__name__)

_VALID_TYPES = {"asset", "liability", "equity", "income", "expense"}
_HEADER_ALIASES = {
    "source_account_code": [
        "source_account_code",
        "account code",
        "code",
        "ledger code",
        "gl code",
        "account no",
        "account number",
        "acct code",
    ],
    "source_account_name": [
        "source_account_name",
        "account name",
        "account",
        "ledger",
        "ledger name",
        "description",
        "name",
        "head",
        "account head",
    ],
    "source_account_type": [
        "source_account_type",
        "account type",
        "type",
        "group",
        "nature",
    ],
}


def legacy_coa_csv_template() -> str:
    return (
        "source_account_code,source_account_name,source_account_type\n"
        "1001,Cash in Hand,asset\n"
        "2001,Sundry Creditors,liability\n"
        "4101,Sales,income\n"
    )


def _norm_header(value: str) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def parse_legacy_coa_csv(csv_text: str) -> list[dict]:
    text = (csv_text or "").lstrip("\ufeff")
    if not text.strip():
        raise ValueError("The uploaded file is empty")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("Could not read a CSV header row")

    normalized_fields = {_norm_header(name): name for name in reader.fieldnames if name}
    headers: dict[str, str] = {}
    for key, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if _norm_header(alias) in normalized_fields:
                headers[key] = normalized_fields[_norm_header(alias)]
                break

    if "source_account_code" not in headers and "source_account_name" not in headers:
        raise ValueError("Could not find a legacy account code or name column")

    rows: list[dict] = []
    seen_codes: dict[str, int] = {}
    for line_no, row in enumerate(reader, start=2):
        code = str(row.get(headers.get("source_account_code", ""), "") or "").strip()
        name = str(row.get(headers.get("source_account_name", ""), "") or "").strip()
        if not code and not name:
            continue
        if not code:
            raise ValueError(f"Row {line_no}: legacy account code is required")
        if not name:
            raise ValueError(f"Row {line_no}: legacy account name/description is required")
        if code in seen_codes:
            raise ValueError(
                f"Duplicate legacy account code '{code}' on rows {seen_codes[code]} and {line_no}"
            )
        seen_codes[code] = line_no
        raw_type = str(row.get(headers.get("source_account_type", ""), "") or "").strip().lower()
        account_type = raw_type if raw_type in _VALID_TYPES else None
        rows.append(
            {
                "row_number": line_no,
                "source_account_code": code,
                "source_account_name": name,
                "source_account_type": account_type,
            }
        )
    if not rows:
        raise ValueError("No legacy account rows could be parsed from the file")
    return rows


def _decision_payload(decision: CoaMappingDecision) -> dict:
    return {
        "id": decision.id,
        "source_system": decision.source_system,
        "source_account_code": decision.source_account_code,
        "source_account_name": decision.source_account_name,
        "action": decision.action,
        "canonical_account_id": decision.canonical_account_id,
        "canonical_account_code": decision.canonical_account_code,
        "canonical_account_name": decision.canonical_account_name,
        "created_account": decision.created_account,
        "suggested_account_id": decision.suggested_account_id,
        "suggested_account_name": decision.suggested_account_name,
        "suggestion_confidence": decision.suggestion_confidence,
        "suggestion_reason": decision.suggestion_reason,
        "notes": decision.notes,
        "decided_by": decision.decided_by,
        "decided_at": decision.decided_at,
        "mapping_id": decision.mapping_id,
        "audit_event_id": decision.audit_event_id,
    }


async def preview_legacy_coa_csv(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    csv_text: str,
    source_system: SourceSystem,
) -> dict:
    from app.accounting.chart import initialize_default_chart_of_accounts

    if app_key == "mitrabooks":
        await initialize_default_chart_of_accounts(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            organization_type="BUSINESS",
        )

    parsed = parse_legacy_coa_csv(csv_text)
    canonical_accounts = list(
        (
            await session.execute(
                select(Account).where(
                    *_accounting_scope(
                        Account,
                        app_key=app_key,
                        tenant_id=tenant_id,
                        accounting_entity_id=accounting_entity_id,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    codes = [row["source_account_code"] for row in parsed]
    source_rows = list(
        (
            await session.execute(
                select(CoaSourceAccount).where(
                    *_accounting_scope(
                        CoaSourceAccount,
                        app_key=app_key,
                        tenant_id=tenant_id,
                        accounting_entity_id=accounting_entity_id,
                    ),
                    CoaSourceAccount.source_system == source_system,
                    CoaSourceAccount.source_account_code.in_(codes),
                )
            )
        )
        .scalars()
        .all()
    )
    source_by_code = {row.source_account_code: row for row in source_rows}
    mapped_by_source_id: dict[int, tuple[CoaMapping, Account]] = {}
    if source_rows:
        mapped_stmt = (
            select(CoaMapping, Account)
            .join(Account, Account.id == CoaMapping.canonical_account_id)
            .where(
                *_accounting_scope(
                    CoaMapping,
                    app_key=app_key,
                    tenant_id=tenant_id,
                    accounting_entity_id=accounting_entity_id,
                ),
                CoaMapping.status == "active",
                CoaMapping.source_account_id.in_([row.id for row in source_rows]),
            )
        )
        for mapping, account in (await session.execute(mapped_stmt)).all():
            mapped_by_source_id[mapping.source_account_id] = (mapping, account)

    preview_rows: list[dict] = []
    suggested_count = 0
    unmatched_count = 0
    already_mapped_count = 0
    for row in parsed:
        source = source_by_code.get(row["source_account_code"])
        mapped = mapped_by_source_id.get(source.id) if source is not None else None
        suggestion = suggest_canonical_account(
            row["source_account_code"],
            row["source_account_name"],
            canonical_accounts,
        )
        if mapped is not None:
            _mapping, account = mapped
            match_status = "already_mapped"
            already_mapped_count += 1
            mapped_account_id = account.id
            mapped_account_code = account.code
            mapped_account_name = account.name
        elif suggestion is not None:
            match_status = "suggested"
            suggested_count += 1
            mapped_account_id = None
            mapped_account_code = None
            mapped_account_name = None
        else:
            match_status = "unmatched"
            unmatched_count += 1
            mapped_account_id = None
            mapped_account_code = None
            mapped_account_name = None

        preview_rows.append(
            {
                "row_number": row["row_number"],
                "source_account_code": row["source_account_code"],
                "source_account_name": row["source_account_name"],
                "source_account_type": row["source_account_type"],
                "match_status": match_status,
                "already_mapped": mapped is not None,
                "mapped_account_id": mapped_account_id,
                "mapped_account_code": mapped_account_code,
                "mapped_account_name": mapped_account_name,
                "suggestion": suggestion,
            }
        )

    return {
        "source_system": source_system,
        "rows": preview_rows,
        "canonical_accounts": [
            {
                "id": account.id,
                "code": account.code,
                "name": account.name,
                "type": account.type,
            }
            for account in sorted(canonical_accounts, key=lambda item: (item.code or "", item.name))
        ],
        "row_count": len(preview_rows),
        "suggested_count": suggested_count,
        "unmatched_count": unmatched_count,
        "already_mapped_count": already_mapped_count,
        "can_confirm_suggested": suggested_count > 0 or already_mapped_count > 0,
    }


async def _get_or_create_source_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    item: CoaSourceAccountIn,
) -> CoaSourceAccount:
    stmt = select(CoaSourceAccount).where(
        *_accounting_scope(
            CoaSourceAccount,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
        ),
        CoaSourceAccount.source_system == item.source_system,
        CoaSourceAccount.source_account_code == item.source_account_code,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        existing = CoaSourceAccount(
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            source_system=item.source_system,
            source_account_code=item.source_account_code,
            source_account_name=item.source_account_name,
            source_account_type=item.source_account_type,
            is_active=True,
        )
        session.add(existing)
        await session.flush()
        return existing
    existing.source_account_name = item.source_account_name
    existing.source_account_type = item.source_account_type
    existing.is_active = True
    return existing


async def _get_or_create_mapping(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    source_account: CoaSourceAccount,
    canonical_account_id: int,
    mapped_by: str,
    notes: str | None,
) -> CoaMapping:
    stmt = select(CoaMapping).where(
        *_accounting_scope(
            CoaMapping,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
        ),
        CoaMapping.source_account_id == source_account.id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if existing is None:
        existing = CoaMapping(
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            source_account_id=source_account.id,
            canonical_account_id=canonical_account_id,
            status="active",
            notes=notes,
            mapped_by=mapped_by,
            mapped_at=now,
        )
        session.add(existing)
        await session.flush()
        return existing
    existing.canonical_account_id = canonical_account_id
    existing.status = "active"
    existing.notes = notes
    existing.mapped_by = mapped_by
    existing.mapped_at = now
    return existing


async def confirm_legacy_coa_decisions(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    source_system: SourceSystem,
    decided_by: str,
    decisions: list[LegacyCoaDecisionIn],
) -> dict:
    if not decisions:
        raise AccountingValidationError("At least one mapping decision is required")

    canonical_stmt = select(Account).where(
        *_accounting_scope(
            Account,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
        )
    )
    canonical_accounts = list((await session.execute(canonical_stmt)).scalars().all())
    canonical_by_id = {account.id: account for account in canonical_accounts}
    codes_in_use = {str(account.code) for account in canonical_accounts if account.code}

    created_count = 0
    mapped_existing_count = 0
    persisted: list[CoaMappingDecision] = []

    for index, item in enumerate(decisions, start=1):
        source_code = item.source_account_code.strip()
        source_name = item.source_account_name.strip()
        if not source_code or not source_name:
            raise AccountingValidationError(f"Decision {index}: legacy code and name are required")

        created_account = False
        if item.action == "map_existing":
            if item.canonical_account_id is None:
                raise AccountingValidationError(
                    f"Decision {index}: canonical_account_id is required when mapping to an existing account"
                )
            canonical = canonical_by_id.get(item.canonical_account_id)
            if canonical is None:
                raise AccountingNotFoundError(
                    f"Canonical account {item.canonical_account_id} was not found for this tenant"
                )
            mapped_existing_count += 1
        elif item.action == "create_new":
            if item.create is None:
                raise AccountingValidationError(
                    f"Decision {index}: create details are required when creating a MitraBooks account"
                )
            create = item.create
            new_code = (create.code or "").strip() or None
            if new_code and new_code in codes_in_use:
                raise AccountingValidationError(
                    f"Decision {index}: MitraBooks account code '{new_code}' already exists"
                )
            canonical = Account(
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
                code=new_code,
                name=create.name.strip(),
                type=create.type,
                classification=create.classification,
                is_cash_bank=create.is_cash_bank,
                is_receivable=create.is_receivable,
                is_payable=create.is_payable,
            )
            session.add(canonical)
            await session.flush()
            canonical_by_id[canonical.id] = canonical
            if new_code:
                codes_in_use.add(new_code)
            created_account = True
            created_count += 1
        else:
            raise AccountingValidationError(f"Decision {index}: unknown action '{item.action}'")

        source_account = await _get_or_create_source_account(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            item=CoaSourceAccountIn(
                source_system=source_system,
                source_account_code=source_code,
                source_account_name=source_name,
                source_account_type=item.source_account_type,
            ),
        )
        mapping = await _get_or_create_mapping(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            source_account=source_account,
            canonical_account_id=canonical.id,
            mapped_by=decided_by,
            notes=item.notes,
        )
        suggestion = item.suggestion
        decision = CoaMappingDecision(
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            source_system=source_system,
            source_account_code=source_code,
            source_account_name=source_name,
            action="created_then_mapped" if created_account else "mapped_to_existing",
            canonical_account_id=canonical.id,
            canonical_account_code=canonical.code,
            canonical_account_name=canonical.name,
            created_account=created_account,
            suggested_account_id=suggestion.canonical_account_id if suggestion else None,
            suggested_account_name=suggestion.canonical_account_name if suggestion else None,
            suggestion_confidence=suggestion.confidence if suggestion else None,
            suggestion_reason=suggestion.reason if suggestion else None,
            notes=item.notes,
            decided_by=decided_by,
            decided_at=datetime.now(timezone.utc),
            mapping_id=mapping.id,
        )
        session.add(decision)
        persisted.append(decision)

    await session.commit()
    for decision in persisted:
        await session.refresh(decision)

    for decision in persisted:
        try:
            event_id = await log_audit_event(
                tenant_id=tenant_id,
                user_id=decided_by,
                product=app_key,
                action="coa_legacy_mapping_confirmed",
                entity_type="coa_mapping_decision",
                entity_id=str(decision.id),
                new_value={
                    "source_system": decision.source_system,
                    "source_account_code": decision.source_account_code,
                    "source_account_name": decision.source_account_name,
                    "action": decision.action,
                    "canonical_account_id": decision.canonical_account_id,
                    "canonical_account_code": decision.canonical_account_code,
                    "canonical_account_name": decision.canonical_account_name,
                    "created_account": decision.created_account,
                    "suggested_account_id": decision.suggested_account_id,
                    "suggestion_confidence": (
                        str(decision.suggestion_confidence) if decision.suggestion_confidence is not None else None
                    ),
                    "suggestion_reason": decision.suggestion_reason,
                    "notes": decision.notes,
                },
            )
            decision.audit_event_id = event_id
        except Exception:
            _logger.exception("Failed to write COA mapping audit event for decision %s", decision.id)
    await session.commit()

    return {
        "source_system": source_system,
        "confirmed_count": len(persisted),
        "created_account_count": created_count,
        "mapped_existing_count": mapped_existing_count,
        "decisions": [_decision_payload(decision) for decision in persisted],
    }


async def list_legacy_coa_decisions(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    source_system: SourceSystem | None = None,
    limit: int = 200,
) -> list[dict]:
    stmt = select(CoaMappingDecision).where(
        *_accounting_scope(
            CoaMappingDecision,
            app_key=app_key,
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
        )
    )
    if source_system:
        stmt = stmt.where(CoaMappingDecision.source_system == source_system)
    stmt = stmt.order_by(CoaMappingDecision.decided_at.desc()).limit(max(1, min(int(limit or 200), 500)))
    rows = list((await session.execute(stmt)).scalars().all())
    return [_decision_payload(row) for row in rows]


async def legacy_account_lookups(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict[str, dict]:
    """Active legacy source codes -> canonical account, excluding codes that already exist on the COA."""
    stmt = (
        select(CoaSourceAccount.source_account_code, Account.id, Account.code, Account.name)
        .join(CoaMapping, CoaMapping.source_account_id == CoaSourceAccount.id)
        .join(Account, Account.id == CoaMapping.canonical_account_id)
        .where(
            *_accounting_scope(
                CoaSourceAccount,
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
            ),
            *_accounting_scope(
                CoaMapping,
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
            ),
            CoaSourceAccount.is_active.is_(True),
            CoaMapping.status == "active",
        )
    )
    by_legacy: dict[str, dict] = {}
    conflicts: set[str] = set()
    for source_code, account_id, code, name in (await session.execute(stmt)).all():
        info = {"account_id": account_id, "code": code, "name": name}
        existing = by_legacy.get(source_code)
        if existing is None:
            by_legacy[source_code] = info
        elif existing["account_id"] != account_id:
            conflicts.add(source_code)
    for code in conflicts:
        by_legacy.pop(code, None)
    return by_legacy
