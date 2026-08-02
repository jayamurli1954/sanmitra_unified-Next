"""Optional MitraBooks posting for LegalMitra fee collections.

Uses shared accounting service only — never writes journal lines directly.
Posting is off unless LEGALMITRA_MITRABOOKS_POSTING_ENABLED and explicit human confirm.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import Account
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry, reverse_journal_entry
from app.config import get_settings


class BillingPostingError(Exception):
    """Raised when optional GL posting fails or is misconfigured."""


def posting_enabled() -> bool:
    return bool(getattr(get_settings(), "LEGALMITRA_MITRABOOKS_POSTING_ENABLED", False))


async def _resolve_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    account_id: int,
) -> Account:
    result = await session.execute(
        select(Account).where(
            Account.tenant_id == tenant_id,
            Account.app_key == app_key,
            Account.accounting_entity_id == accounting_entity_id,
            Account.id == account_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise BillingPostingError(
            f"GL account {account_id} not found for tenant books "
            f"(app_key={app_key}, entity={accounting_entity_id})"
        )
    return account


async def post_fee_collection_to_books(
    session: AsyncSession,
    *,
    legal_tenant_id: str,
    actor_id: str,
    collection_id: str,
    invoice_number: str,
    amount: Decimal,
    collected_on: date,
    gl_map: dict,
) -> dict:
    """Dr Bank/Cash, Cr Fee income — mapped accounts only."""
    if not posting_enabled():
        raise BillingPostingError("MitraBooks posting is disabled")

    books_tenant = str(gl_map.get("books_tenant_id") or legal_tenant_id)
    books_app_key = str(gl_map.get("accounting_app_key") or "mitrabooks")
    entity_id = str(gl_map.get("accounting_entity_id") or "primary")
    bank_id = gl_map.get("bank_account_id")
    income_id = gl_map.get("income_account_id")
    if not bank_id or not income_id:
        raise BillingPostingError("Fee GL map is incomplete (bank_account_id, income_account_id)")

    await _resolve_account(
        session,
        tenant_id=books_tenant,
        app_key=books_app_key,
        accounting_entity_id=entity_id,
        account_id=int(bank_id),
    )
    await _resolve_account(
        session,
        tenant_id=books_tenant,
        app_key=books_app_key,
        accounting_entity_id=entity_id,
        account_id=int(income_id),
    )

    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= 0:
        raise BillingPostingError("Posting amount must be positive")

    idempotency_key = f"legal-fee-collection:{collection_id}"
    journal, created = await post_journal_entry(
        session,
        tenant_id=books_tenant,
        app_key=books_app_key,
        accounting_entity_id=entity_id,
        created_by=actor_id,
        payload=JournalPostRequest(
            entry_date=collected_on,
            description=f"LegalMitra fee collection {invoice_number}",
            reference=invoice_number,
            source_module="legalmitra",
            source_document_type="fee_collection",
            source_document_id=collection_id,
            lines=[
                JournalLineIn(account_id=int(bank_id), debit=amount, credit=Decimal("0")),
                JournalLineIn(account_id=int(income_id), debit=Decimal("0"), credit=amount),
            ],
        ),
        idempotency_key=idempotency_key,
    )
    return {
        "journal_id": int(journal.id),
        "created": bool(created),
        "idempotency_key": idempotency_key,
        "books_tenant_id": books_tenant,
        "books_app_key": books_app_key,
        "accounting_entity_id": entity_id,
    }


async def reverse_fee_collection_posting(
    session: AsyncSession,
    *,
    actor_id: str,
    journal_id: int,
    gl_map: dict,
    reason: str | None = None,
) -> dict:
    books_tenant = str(gl_map.get("books_tenant_id") or gl_map.get("tenant_id") or "")
    books_app_key = str(gl_map.get("accounting_app_key") or "mitrabooks")
    entity_id = str(gl_map.get("accounting_entity_id") or "primary")
    if not books_tenant:
        raise BillingPostingError("Cannot reverse posting without books tenant")
    journal, created = await reverse_journal_entry(
        session,
        tenant_id=books_tenant,
        journal_id=journal_id,
        app_key=books_app_key,
        accounting_entity_id=entity_id,
        created_by=actor_id,
        reason=reason or "LegalMitra fee collection void/compensation",
        idempotency_key=f"legal-fee-collection-reversal:{journal_id}",
    )
    return {"journal_id": int(journal.id), "created": bool(created)}
