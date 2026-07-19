"""GST return routes (GSTR-3B/1, CMP-08, GSTR-4, GSTR-2B reconcile).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged. The returns-only _resolve_business_gstin helper
moved here with the handlers.
"""
import re

from fastapi import Body, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import gst_returns
from app.modules.business.service import get_invoice_settings
from app.modules.business.router import _created_by, router


async def _resolve_business_gstin(tenant_id: str, app_key: str, accounting_entity_id: str) -> str | None:
    """Seller GSTIN for return headers, from invoice-settings branding (if set)."""
    try:
        settings = await get_invoice_settings(
            tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
        )
        gstin = ((settings or {}).get("branding") or {}).get("gstin")
        if gstin and str(gstin).strip():
            return str(gstin).strip()
    except Exception:
        pass
    return None


@router.get("/returns/gstr-3b")
async def business_gstr3b_return(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """GSTR-3B monthly summary return for a 'YYYY-MM' period. Tax heads come from
    the immutable ledger (reusing the settlement set-off); taxable value from the
    posted sales-invoice/credit-note documents. Includes the GSTN JSON shape."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-3B return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr3b(
        session,
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstin=gstin,
    )


@router.get("/returns/gstr-1")
async def business_gstr1_return(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """GSTR-1 outward-supplies return for a 'YYYY-MM' period. Built from posted
    sales-invoice and credit-note documents, grouped into the statutory sections
    (B2B / B2CL / B2CS / CDNR / HSN / DOCS). Includes the GSTN JSON shape."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-1 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr1(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstin=gstin,
    )


@router.get("/returns/cmp-08")
async def business_cmp08_return(
    quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Form CMP-08 — quarterly self-assessed liability for a composition dealer
    ('YYYY-Q1'..'YYYY-Q4', FY quarters). Tax = turnover x composition rate."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="CMP-08 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    report = await gst_returns.build_cmp08(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        quarter=quarter,
        gstin=gstin,
    )
    report["liability_posting"] = await gst_returns.find_cmp08_posting(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, quarter=quarter,
    )
    return report


@router.post("/returns/cmp-08/post")
async def business_cmp08_post_liability(
    payload: dict = Body(..., description='{"quarter": "YYYY-Q1"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Book the quarter's composition levy in the ledger (admin only):
    Dr GST Expense (Composition) 54007 / Cr GST Payable (Net) 22004 on the
    quarter-end date. Idempotent per quarter; reverse the journal to redo."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="CMP-08 liability posting",
    )
    quarter = str(payload.get("quarter") or "").strip().upper()
    if not re.fullmatch(r"\d{4}-Q[1-4]", quarter):
        raise HTTPException(status_code=422, detail="quarter must be 'YYYY-Q1'..'YYYY-Q4'")
    try:
        return await gst_returns.post_cmp08_liability(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, quarter=quarter,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/returns/gstr-4")
async def business_gstr4_return(
    financial_year: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Form GSTR-4 — annual composition return for a financial year ('YYYY-YY',
    e.g. '2026-27'). Consolidates the four CMP-08 quarters, the annual outward
    liability, and inward purchases (registered / unregistered)."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-4 return",
    )
    gstin = await _resolve_business_gstin(context.tenant_id, context.app_key, accounting_entity_id)
    return await gst_returns.build_gstr4(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        financial_year=financial_year,
        gstin=gstin,
    )


@router.post("/returns/gstr-2b/reconcile")
async def business_gstr2b_reconcile(
    period: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    gstr2b: dict = Body(..., description="The GSTR-2B JSON downloaded from the GST portal."),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Reconcile an uploaded GSTR-2B JSON for a 'YYYY-MM' period against the input
    GST booked on posted purchase bills. Classifies matched / mismatch / available-
    not-booked / at-risk (booked but not in 2B, per Section 16(2)(aa))."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="GSTR-2B reconciliation",
    )
    return await gst_returns.build_gstr2b_reconciliation(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        period=period,
        gstr2b_payload=gstr2b,
    )
