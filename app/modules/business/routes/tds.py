"""TDS/TCS routes (section masters, quarterly register).

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from fastapi import Depends, Header, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business import tds as tds_module
from app.modules.business.router import router


@router.get("/tds/sections")
async def business_tds_sections(
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """TDS / TCS section masters (default rates) for the document forms."""
    resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="TDS sections",
    )
    return tds_module.list_sections()


@router.get("/tds/register")
async def business_tds_register(
    quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$"),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Quarterly TDS/TCS register ('YYYY-Q1'..'YYYY-Q4', FY quarters) — the
    section-wise deductee/collectee working paper that feeds Form 26Q / 27EQ."""
    context = resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mitrabooks",
        operation="TDS register",
    )
    return await tds_module.build_tds_register(
        tenant_id=context.tenant_id,
        app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
        quarter=quarter,
    )
