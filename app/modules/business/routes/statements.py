"""Party statement + dunning routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from datetime import date

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import statements
from app.modules.business.router import _created_by, router


@router.get("/statements/{party_id}")
async def business_party_statement(
    party_id: str,
    kind: str = Query(default="receivable", pattern="^(receivable|payable)$"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Statement of account for one customer/vendor: opening balance, dated
    transactions with running balance, closing balance, open items with aging,
    and (for receivables) the dunning suggestion + reminder letter + log."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="party statement",
    )
    try:
        return await statements.build_party_statement(
            session,
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            party_id=party_id,
            kind=kind,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/statements/{party_id}/dunning")
async def business_record_dunning(
    party_id: str,
    payload: dict = Body(..., description='{"level": 1-3, "note": "...", "overdue_total": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Record that a payment reminder was sent (sending itself is manual —
    print/email/WhatsApp). Builds the dunning audit trail for the party."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="dunning record",
    )
    try:
        return await statements.record_dunning_sent(
            tenant_id=context.tenant_id,
            app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            party_id=party_id,
            level=int(payload.get("level") or 0),
            note=payload.get("note"),
            overdue_total=payload.get("overdue_total"),
            created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
