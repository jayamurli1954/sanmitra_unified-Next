"""Opening-balance import/export and year-end close routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
import re
from datetime import date

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import export_governance
from app.modules.business import opening_close
from app.modules.business.router import _created_by, router


@router.get("/opening-balances/template")
async def business_opening_balance_template(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Sample CSV for the opening-balance import."""
    resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance template",
    )
    from fastapi.responses import Response
    return Response(
        content=opening_close.csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="opening_balances_template.csv"'},
    )


@router.get("/opening-balances/export")
async def business_opening_balance_export(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Export the currently posted opening balances as a CSV file."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance export",
    )
    export_governance.require_export_permission(current_user, export_type="opening_balances")
    from fastapi.responses import Response
    csv_content = await opening_close.export_opening_balances_csv(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )
    response = Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="opening_balances.csv"'},
    )
    return await export_governance.govern_export_response(
        response,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        current_user=current_user,
        export_type="opening_balances",
        export_format="csv",
        report_key="opening_balances",
    )


@router.post("/opening-balances/preview")
async def business_opening_balance_preview(
    payload: dict = Body(..., description='{"csv": "<opening balance CSV>", "as_of": "YYYY-MM-DD", "header_mapping": {}, "preset": null}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Parse + resolve the uploaded opening-balance CSV WITHOUT posting:
    resolved lines, row errors, totals and the Opening-Balance-Equity
    balancing line. Posting requires zero errors (maker-checker)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance preview",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else None
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await opening_close.build_opening_preview(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""), as_of=as_of,
            header_mapping=payload.get("header_mapping"),
            preset=payload.get("preset"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/opening-balances")
async def business_post_opening_balances(
    payload: dict = Body(..., description='{"csv": "...", "as_of": "YYYY-MM-DD", "allow_duplicate": false, "header_mapping": {}, "preset": null}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the opening balances as ONE journal entry (admin only). Any
    debit/credit difference goes to Opening Balance Equity; party rows carry
    party_id so they flow into aging/statements/allocation."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="opening balance posting",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else None
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await opening_close.post_opening_balances(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            csv_text=str(payload.get("csv") or ""), as_of=as_of,
            allow_duplicate=bool(payload.get("allow_duplicate")),
            created_by=_created_by(current_user),
            idempotency_key=x_idempotency_key,
            header_mapping=payload.get("header_mapping"),
            preset=payload.get("preset"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/year-end/preview")
async def business_year_end_preview(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Year-end close preview for 'YYYY-YY': per-account closing lines, the
    Retained Earnings movement, and whether the FY is already closed."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="year-end preview",
    )
    return await opening_close.build_year_end_preview(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, financial_year=financial_year,
    )


@router.post("/year-end/close")
async def business_year_end_close(
    payload: dict = Body(..., description='{"financial_year": "YYYY-YY"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the year-end closing journal (admin only): income/expense accounts
    zeroed to Retained Earnings on 31 March. Idempotent per financial year;
    reverse the entry to reopen the year."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="year-end close",
    )
    financial_year = str(payload.get("financial_year") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}", financial_year):
        raise HTTPException(status_code=422, detail="financial_year must be 'YYYY-YY' (e.g. 2026-27)")
    try:
        return await opening_close.post_year_end_close(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, financial_year=financial_year,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
