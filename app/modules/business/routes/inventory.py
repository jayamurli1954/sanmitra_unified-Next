"""Inventory routes (items, stock movements, closing stock).

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
from app.core.permissions.rbac import Role, require_roles
from app.core.tenants.app_resolvers import resolve_business_app_tenant
from app.db.postgres import get_async_session
from app.modules.business import inventory as inventory_module
from app.modules.business.router import _created_by, router


@router.post("/inventory/items")
async def business_create_item(
    payload: dict = Body(..., description='{"code": "...", "name": "...", "uqc": "NOS", "hsn_sac": "...", "opening_qty": 0, "opening_value": 0}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Create an inventory item (requires inventory accounting to be enabled)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item create",
    )
    if not await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    ):
        raise HTTPException(status_code=422, detail="Inventory accounting is disabled — enable it in Invoice Settings first")
    try:
        return await inventory_module.create_item(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/inventory/items")
async def business_list_items(
    include_inactive: bool = Query(default=False),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Item master. Also reports whether inventory accounting is enabled."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item list",
    )
    enabled = await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    )
    result = await inventory_module.list_items(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, include_inactive=include_inactive,
    )
    result["inventory_enabled"] = enabled
    return result


@router.get("/inventory/policy")
async def business_inventory_policy(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Current inventory valuation policy for this accounting entity."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="inventory policy",
    )
    enabled = await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    )
    policy = inventory_module.inventory_policy()
    policy["inventory_enabled"] = enabled
    policy["accounting_entity_id"] = accounting_entity_id
    return policy


@router.patch("/inventory/items/{item_id}/deactivate")
async def business_deactivate_item(
    item_id: str,
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Soft-deactivate an item (existing documents keep their tag)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="item deactivate",
    )
    try:
        return await inventory_module.deactivate_item(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            item_id=item_id, updated_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/inventory/movements")
async def business_list_stock_movements(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Tenant-scoped operational stock issues and adjustments."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="stock movement list",
    )
    return await inventory_module.list_stock_movements(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


@router.post("/inventory/movements")
async def business_create_stock_movement(
    payload: dict = Body(..., description='{"movement_type": "issue|adjustment", "item_id": "...", "quantity": "1", "value": "0", "movement_date": "YYYY-MM-DD"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Record an operational stock issue or adjustment.

    Periodic inventory keeps these as audited movement records; financial impact
    is realized through the closing-stock journal.
    """
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="stock movement create",
    )
    if not await inventory_module.is_inventory_enabled(
        tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id=accounting_entity_id,
    ):
        raise HTTPException(status_code=422, detail="Inventory accounting is disabled - enable it in Invoice Settings first")
    try:
        return await inventory_module.create_stock_movement(
            tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id,
            payload=payload, created_by=_created_by(current_user),
        )
    except AccountingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/inventory/stock-register")
async def business_stock_register(
    as_of: date | None = Query(default=None),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Per-item stock position as of a date (weighted-average valuation)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="stock register",
    )
    return await inventory_module.build_stock_register(
        tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id, as_of=as_of,
    )


@router.get("/inventory/closing-stock/entries")
async def business_closing_stock_entries(
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """Previously posted closing-stock journals (newest first)."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="closing stock entries",
    )
    return {"items": await inventory_module.find_closing_stock_entries(
        session, tenant_id=context.tenant_id, app_key=context.app_key,
        accounting_entity_id=accounting_entity_id,
    )}


@router.post("/inventory/closing-stock")
async def business_post_closing_stock(
    payload: dict = Body(..., description='{"as_of": "YYYY-MM-DD"}'),
    accounting_entity_id: str = Query(default="primary", min_length=1, max_length=80),
    _module_context: dict = Depends(require_enabled_module("business")),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_roles([Role.super_admin, Role.tenant_admin])),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """Post the closing-stock journal (admin only): Dr Inventory 13001 /
    Cr COGS 51002 at the register's value. Reverse the previous closing entry
    before posting a fresh position."""
    context = resolve_business_app_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        expected_app_key="mitrabooks", operation="closing stock posting",
    )
    as_of_raw = str(payload.get("as_of") or "").strip()
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else date.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be YYYY-MM-DD")
    try:
        return await inventory_module.post_closing_stock(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            accounting_entity_id=accounting_entity_id, as_of=as_of,
            created_by=_created_by(current_user), idempotency_key=x_idempotency_key,
        )
    except AccountingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
