"""e-Invoice (IRN) view and record routes.

Registered on the shared ``router`` from ``app.modules.business.router``.
Moved verbatim per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md; paths and
handler behaviour are unchanged.
"""
from fastapi import Body, Depends, Header, HTTPException, Query

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.modules.business import einvoice as einvoice_module
from app.modules.business.router import _created_by, router


@router.get("/invoices/{invoice_id}/einvoice")
async def business_einvoice_view(
    invoice_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """e-Invoice view for one posted invoice: readiness errors, the INV-01
    JSON payload (when clean), and the recorded IRN status."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="e-invoice view",
    )
    try:
        return await einvoice_module.build_einvoice_view(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, invoice_id=invoice_id,
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/invoices/{invoice_id}/einvoice/record")
async def business_einvoice_record(
    invoice_id: str,
    payload: dict = Body(..., description='{"irn": "<64-hex>", "ack_no": "...", "ack_date": "...", "signed_qr": "..."}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Record the IRN/Ack the e-invoice portal returned for this invoice
    (manual flow today; the future IRP API client will call the same step)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="e-invoice IRN record",
    )
    try:
        return await einvoice_module.record_irn(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, invoice_id=invoice_id,
            irn=str(payload.get("irn") or ""), ack_no=payload.get("ack_no"),
            ack_date=payload.get("ack_date"), signed_qr=payload.get("signed_qr"),
            created_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
