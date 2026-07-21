"""Shared business service helpers.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Re-exported via the service.py facade for compatibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.accounting.service import AccountingNotFoundError
from app.modules.business import service as business_service
from app.modules.business.schemas import TypedVoucherCreateRequest

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal("0.01")))


def _json_safe_doc(doc: dict) -> dict:
    return {key: value for key, value in doc.items() if key != "_id"}


def _apply_approval_defaults(result: dict) -> dict:
    result.setdefault("approval_required", False)
    result.setdefault("approval_status", "auto_posted")
    result.setdefault("approval_submitted_at", None)
    result.setdefault("approval_submitted_by", None)
    result.setdefault("approval_decided_at", None)
    result.setdefault("approval_decided_by", None)
    result.setdefault("approval_notes", None)
    result.setdefault("rejection_reason", None)
    return result


def _voucher_response_doc(doc: dict, *, created: bool = False) -> dict:
    result = _json_safe_doc(doc)
    _apply_approval_defaults(result)
    result.setdefault("journal_entry_id", None)
    result.setdefault("reversal_journal_entry_id", None)
    result.setdefault("reversal_reason", None)
    result.setdefault("reversed_at", None)
    result.setdefault("created", created)
    return result


async def _audit_business_event(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    try:
        # Resolve via service facade so tests can monkeypatch business_service.log_audit_event.
        from app.modules.business import service as business_service

        await business_service.log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            product=app_key,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        # Audit writes are best-effort here because accounting/domain writes may
        # already be committed by the time this hook runs.
        pass


async def _resolve_voucher_account_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int | None,
    account_code: str | None,
    side: str,
) -> int:
    if account_id:
        account = (
            await session.execute(
                select(Account).where(
                    Account.id == account_id,
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == accounting_entity_id,
                )
            )
        ).scalar_one_or_none()
        if account is not None:
            return int(account.id)

    code = str(account_code or "").strip()
    if code:
        account = (
            await session.execute(
                select(Account).where(
                    Account.tenant_id == tenant_id,
                    Account.app_key == app_key,
                    Account.accounting_entity_id == accounting_entity_id,
                    Account.code == code,
                )
            )
        ).scalar_one_or_none()
        if account is not None:
            return int(account.id)

    raise AccountingNotFoundError(f"{side.capitalize()} account not found for this tenant")


async def _ensure_business_chart_for_voucher_codes(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    payload: TypedVoucherCreateRequest,
) -> None:
    if not payload.debit_account_code and not payload.credit_account_code:
        return
    if app_key != "mitrabooks":
        return

    await business_service.initialize_default_chart_of_accounts(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        organization_type="BUSINESS",
    )


