"""MandirMitra inventory items, movements, and consumption routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

@router.get("/inventory/items")
@router.get("/inventory/items/")
async def mandir_inventory_items(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    docs = await mandir_router.get_collection("mandir_inventory_items").find({"tenant_id": tenant_id, "app_key": app_key}).sort("updated_at", -1).to_list(length=1000)
    return [mandir_router._sanitize_mongo_doc(doc) for doc in docs]


@router.post("/inventory/items", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/inventory/items/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_create_inventory_item(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    try:
        opening_quantity = Decimal(str(payload.get("opening_quantity") or "0")).quantize(Decimal("0.001"))
        opening_unit_value = Decimal(str(payload.get("opening_unit_value") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid opening quantity and unit value are required") from exc
    if not opening_quantity.is_finite() or opening_quantity < 0 or not opening_unit_value.is_finite() or opening_unit_value < 0:
        raise HTTPException(status_code=400, detail="Opening quantity and unit value cannot be negative")
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid4())
    item = {
        "id": item_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "code": str(payload.get("code") or "").strip(),
        "name": str(payload.get("name") or "").strip() or "Inventory Item",
        "category": str(payload.get("category") or "OTHER").strip() or "OTHER",
        "unit": str(payload.get("unit") or "PIECE").strip() or "PIECE",
        "reorder_level": int(payload.get("reorder_level") or 0),
        "reorder_quantity": int(payload.get("reorder_quantity") or 0),
        "description": str(payload.get("description") or "").strip(),
        "opening_quantity": str(opening_quantity),
        "opening_unit_value": str(opening_unit_value),
        "is_active": bool(payload.get("is_active", True)),
        "created_at": now,
        "updated_at": now,
    }
    await mandir_router.get_collection("mandir_inventory_items").insert_one(item)
    return mandir_router._sanitize_mongo_doc(item)


@router.put("/inventory/items/{item_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_update_inventory_item(
    item_id: str,
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    allowed = {"code", "name", "category", "unit", "reorder_level", "reorder_quantity", "description", "is_active"}
    patch = {k: payload.get(k) for k in allowed if k in payload}
    if "reorder_level" in patch:
        patch["reorder_level"] = int(patch["reorder_level"] or 0)
    if "reorder_quantity" in patch:
        patch["reorder_quantity"] = int(patch["reorder_quantity"] or 0)
    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
    await mandir_router.get_collection("mandir_inventory_items").update_one(
        {"id": item_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )
    row = await mandir_router.get_collection("mandir_inventory_items").find_one({"id": item_id, "tenant_id": tenant_id, "app_key": app_key})
    if row is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return mandir_router._sanitize_mongo_doc(row)


@router.delete("/inventory/items/{item_id}", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def mandir_delete_inventory_item(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    now = datetime.now(timezone.utc).isoformat()
    await mandir_router.get_collection("mandir_inventory_items").update_one(
        {"id": item_id, "tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": False, "updated_at": now}},
        upsert=False,
    )
    return {"status": "deactivated", "id": item_id}


async def _mandir_inventory_item_position(
    *, tenant_id: str, app_key: str, item: dict[str, Any]
) -> tuple[Decimal, Decimal]:
    quantity_balance = Decimal(str(item.get("opening_quantity") or "0"))
    value_balance = (
        quantity_balance * Decimal(str(item.get("opening_unit_value") or "0"))
    ).quantize(Decimal("0.01"))
    movements = await mandir_router.get_collection("mandir_inventory_movements").find(
        {"tenant_id": tenant_id, "app_key": app_key, "item_id": str(item.get("id")), "status": "posted"}
    ).to_list(length=5000)
    positive_types = {"receipt", "issue_reversal", "adjustment_in"}
    negative_types = {"issue", "receipt_reversal", "adjustment_out"}
    for movement in movements:
        quantity = Decimal(str(movement.get("quantity") or "0"))
        movement_value = Decimal(str(movement.get("total_value") or "0"))
        movement_type = str(movement.get("movement_type") or "")
        if movement_type in positive_types:
            quantity_balance += quantity
            value_balance += movement_value
        elif movement_type in negative_types:
            quantity_balance -= quantity
            value_balance -= movement_value
    return (
        quantity_balance.quantize(Decimal("0.001")),
        value_balance.quantize(Decimal("0.01")),
    )


async def _mandir_inventory_item_balance(*, tenant_id: str, app_key: str, item: dict[str, Any]) -> Decimal:
    quantity_balance, _value_balance = await _mandir_inventory_item_position(
        tenant_id=tenant_id, app_key=app_key, item=item
    )
    return quantity_balance


@router.get("/inventory/movements")
async def list_mandir_inventory_movements(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="inventory movement listing"
    )
    rows = await mandir_router.get_collection("mandir_inventory_movements").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("created_at", -1).to_list(length=2000)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.get("/inventory/consumptions")
async def list_mandir_inventory_consumptions(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="inventory consumption listing"
    )
    rows = await mandir_router.get_collection("mandir_inventory_consumptions").find(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    ).sort("created_at", -1).to_list(length=1000)
    return [mandir_router._sanitize_mongo_doc(row) for row in rows]


@router.post("/inventory/consumptions", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_mandir_inventory_consumption(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="inventory consumption submission"
    )
    if not await mandir_router._mandir_inventory_accounting_enabled(context.tenant_id, context.app_key):
        raise HTTPException(status_code=409, detail="Inventory accounting is not enabled for this temple")
    item_id = str(payload.get("item_id") or "").strip()
    item = await mandir_router.get_collection("mandir_inventory_items").find_one(
        {"id": item_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True}
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Active inventory item not found")
    try:
        quantity = Decimal(str(payload.get("quantity") or "0")).quantize(Decimal("0.001"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid quantity is required") from exc
    if not quantity.is_finite() or quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
    available_quantity, available_value = await _mandir_inventory_item_position(
        tenant_id=context.tenant_id, app_key=context.app_key, item=item
    )
    if available_quantity <= 0 or available_value <= 0:
        raise HTTPException(status_code=409, detail="Valued inventory stock is unavailable for this item")
    unit_value = (available_value / available_quantity).quantize(Decimal("0.01"))
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Consumption reason is required")
    consumed_on = str(payload.get("consumed_on") or datetime.now(timezone.utc).date().isoformat()).strip()
    try:
        date.fromisoformat(consumed_on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Valid consumed_on date is required") from exc
    fund_id = str(payload.get("fund_id") or "").strip()
    dimension_id = None
    fund_name = None
    if fund_id:
        fund = await mandir_router.get_collection("mandir_funds").find_one(
            {"id": fund_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "active": True}
        )
        if fund is None or not fund.get("accounting_dimension_id"):
            raise HTTPException(status_code=404, detail="Active accounting-enabled fund not found")
        dimension_id = str(fund["accounting_dimension_id"])
        fund_name = fund.get("name")
    consumption_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consumption_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
        "item_id": item_id, "item_name": item.get("name"), "item_category": item.get("category"),
        "quantity": str(quantity), "unit_value": str(unit_value),
        "total_value": str((quantity * unit_value).quantize(Decimal("0.01"))),
        "consumed_on": consumed_on, "reason": reason, "fund_id": fund_id or None,
        "fund_name": fund_name, "fund_dimension_id": dimension_id,
        "reference": f"CON-{consumption_id[:8].upper()}", "status": "pending_approval",
        "created_by": mandir_router._mandir_actor_id(current_user), "created_at": now, "updated_at": now,
    }
    await mandir_router.get_collection("mandir_inventory_consumptions").insert_one(doc)
    return mandir_router._sanitize_mongo_doc(doc)


@router.post("/inventory/consumptions/{consumption_id}/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_inventory_consumption(
    consumption_id: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="inventory consumption approval"
    )
    collection = mandir_router.get_collection("mandir_inventory_consumptions")
    query = {"id": consumption_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Inventory consumption not found")
    if existing.get("status") == "posted":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending consumptions can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(existing.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Consumption maker and approver must be different users")
    item = await mandir_router.get_collection("mandir_inventory_items").find_one(
        {"id": existing.get("item_id"), "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True}
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Active inventory item not found")
    quantity = Decimal(str(existing["quantity"]))
    available, available_value = await _mandir_inventory_item_position(
        tenant_id=context.tenant_id, app_key=context.app_key, item=item
    )
    if available < quantity:
        raise HTTPException(status_code=409, detail=f"Insufficient stock; available quantity is {available}")
    if available <= 0 or available_value <= 0:
        raise HTTPException(status_code=409, detail="Valued inventory stock is unavailable for this item")
    unit_value = (available_value / available).quantize(Decimal("0.01"))
    amount = (quantity * unit_value).quantize(Decimal("0.01"))
    category = mandir_router._normalize_income_category(item.get("category"))
    if any(marker in category for marker in ("food", "rice", "prasadam", "annadan")):
        inventory_code, inventory_name, expense_code, expense_name = "14004", "Prasadam Inventory", "54007", "Prasadam Expenses"
    elif any(marker in category for marker in ("flower", "decoration", "festival")):
        inventory_code, inventory_name, expense_code, expense_name = "14003", "Pooja Materials Inventory", "54006", "Decoration Expenses"
    else:
        inventory_code, inventory_name, expense_code, expense_name = "14003", "Pooja Materials Inventory", "51004", "Pooja Materials Expenses"
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    inventory_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code=inventory_code, name=inventory_name, account_type="asset", classification="real"
    )
    expense_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code=expense_code, name=expense_name, account_type="expense", classification="nominal"
    )
    movement_collection = mandir_router.get_collection("mandir_inventory_movements")
    movement = {
        "id": str(uuid4()), "tenant_id": context.tenant_id, "app_key": context.app_key,
        "item_id": existing["item_id"], "item_name": existing.get("item_name"), "movement_type": "issue",
        "quantity": str(quantity), "unit_value": str(unit_value), "total_value": str(amount),
        "movement_date": str(existing["consumed_on"]), "source_type": "inventory_consumption",
        "source_id": consumption_id, "status": "pending_accounting", "created_by": actor,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await movement_collection.insert_one(movement)
    try:
        journal, _created = await mandir_router.post_journal_entry(
            session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
            payload=JournalPostRequest(
                entry_date=date.fromisoformat(str(existing["consumed_on"])),
                description=f"Inventory consumption: {existing.get('item_name')} - {existing.get('reason')}",
                reference=str(existing["reference"]), source_module="mandirmitra",
                source_document_type="inventory_consumption", source_document_id=consumption_id,
                lines=[
                    JournalLineIn(
                        account_id=expense_account_id, debit=amount, credit=Decimal("0"),
                        cost_center_id=existing.get("fund_dimension_id"),
                    ),
                    JournalLineIn(
                        account_id=inventory_account_id, debit=Decimal("0"), credit=amount,
                        cost_center_id=existing.get("fund_dimension_id"),
                    ),
                ],
            ),
            idempotency_key=f"inventory_consumption_{consumption_id}",
        )
    except Exception:
        await movement_collection.update_one(
            {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
            {"$set": {"status": "accounting_failed"}}, upsert=False,
        )
        raise
    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "status": "posted", "approved_by": actor, "approved_at": now,
        "unit_value": str(unit_value), "total_value": str(amount),
        "journal_entry_id": int(journal.id), "inventory_movement_id": movement["id"], "updated_at": now,
    }
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
        await movement_collection.update_one(
            {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
            {"$set": {"status": "posted", "journal_entry_id": int(journal.id), "posted_at": now}}, upsert=False,
        )
    except Exception as exc:
        await mandir_router.reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
            journal_id=int(journal.id), created_by=actor, reason="Compensate failed inventory consumption persistence",
            idempotency_key=f"inventory_consumption_{consumption_id}_approval_compensation",
        )
        try:
            await movement_collection.update_one(
                {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                {"$set": {"status": "compensated", "updated_at": now}}, upsert=False,
            )
        except Exception:
            mandir_router.logger.exception("Failed to mark compensated inventory issue consumption=%s", consumption_id)
        try:
            await collection.update_one(
                query,
                {"$set": {
                    "status": "pending_approval", "journal_entry_id": None,
                    "inventory_movement_id": None, "approved_by": None,
                    "approved_at": None, "updated_at": now,
                }},
                upsert=False,
            )
        except Exception:
            mandir_router.logger.exception("Failed to restore pending inventory consumption=%s", consumption_id)
        raise HTTPException(status_code=500, detail="Consumption persistence failed; accounting was reversed") from exc
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.post("/inventory/consumptions/{consumption_id}/cancel", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cancel_mandir_inventory_consumption(
    consumption_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key, operation="inventory consumption reversal"
    )
    collection = mandir_router.get_collection("mandir_inventory_consumptions")
    query = {"id": consumption_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    existing = await collection.find_one(query)
    if existing is None:
        raise HTTPException(status_code=404, detail="Inventory consumption not found")
    if existing.get("status") == "reversed":
        return {**mandir_router._sanitize_mongo_doc(existing), "_idempotent": True}
    if existing.get("status") != "posted":
        raise HTTPException(status_code=409, detail="Only posted consumptions can be reversed")
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Reversal reason is required")
    movement_collection = mandir_router.get_collection("mandir_inventory_movements")
    reversal_movement_id = f"consumption-reversal-{consumption_id}"
    reversal_movement = await movement_collection.find_one(
        {"id": reversal_movement_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    )
    if reversal_movement is None:
        reversal_movement = {
            "id": reversal_movement_id, "tenant_id": context.tenant_id, "app_key": context.app_key,
            "item_id": existing["item_id"], "item_name": existing.get("item_name"),
            "movement_type": "issue_reversal", "quantity": str(existing["quantity"]),
            "unit_value": str(existing["unit_value"]), "total_value": str(existing["total_value"]),
            "movement_date": datetime.now(timezone.utc).date().isoformat(),
            "source_type": "inventory_consumption_reversal", "source_id": consumption_id,
            "status": "pending_accounting", "created_by": mandir_router._mandir_actor_id(current_user),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await movement_collection.insert_one(reversal_movement)
    try:
        reversal, _created = await mandir_router._reverse_mandir_source_journal(
            session, tenant_id=context.tenant_id, app_key=context.app_key,
            source_key=f"inventory_consumption_{consumption_id}", reason=reason, current_user=current_user,
        )
    except Exception:
        await movement_collection.update_one(
            {"id": reversal_movement_id, "tenant_id": context.tenant_id, "app_key": context.app_key},
            {"$set": {"status": "accounting_failed"}}, upsert=False,
        )
        raise
    now = datetime.now(timezone.utc).isoformat()
    await movement_collection.update_one(
        {"id": reversal_movement_id, "tenant_id": context.tenant_id, "app_key": context.app_key},
        {"$set": {"status": "posted", "journal_entry_id": int(reversal.id), "posted_at": now}}, upsert=False,
    )
    patch = {
        "status": "reversed", "reversal_journal_id": int(reversal.id), "reversal_reason": reason,
        "reversed_by": mandir_router._mandir_actor_id(current_user), "reversed_at": now,
        "reversal_inventory_movement_id": reversal_movement_id, "updated_at": now,
    }
    await collection.update_one(query, {"$set": patch}, upsert=False)
    return mandir_router._sanitize_mongo_doc({**existing, **patch})


@router.get("/inventory/stock-balances")
@router.get("/inventory/stock-balances/")
async def mandir_inventory_stock_balances(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="inventory stock balance reporting",
    )
    items = await mandir_router.get_collection("mandir_inventory_items").find({
        "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True,
    }).to_list(length=1000)
    rows = []
    for item in items:
        reorder_level = int(item.get("reorder_level") or 0)
        on_hand_qty, on_hand_value = await _mandir_inventory_item_position(
            tenant_id=context.tenant_id, app_key=context.app_key, item=item,
        )
        weighted_average_unit_value = (
            (on_hand_value / on_hand_qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if on_hand_qty > 0
            else Decimal("0.00")
        )
        rows.append(
            {
                "item_id": str(item.get("id") or ""),
                "item_code": str(item.get("code") or ""),
                "item_name": str(item.get("name") or ""),
                "unit": str(item.get("unit") or "PIECE"),
                "on_hand_qty": str(on_hand_qty),
                "on_hand_value": str(on_hand_value),
                "weighted_average_unit_value": str(weighted_average_unit_value),
                "reorder_level": reorder_level,
                "reorder_required": bool(reorder_level > 0 and on_hand_qty <= Decimal(str(reorder_level))),
            }
        )
    return rows


@router.get("/inventory/summary")
@router.get("/inventory/summary/")
async def mandir_inventory_summary(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="inventory summary reporting",
    )
    items = await mandir_router.get_collection("mandir_inventory_items").find({
        "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True,
    }).to_list(length=1000)
    low_stock = 0
    total_value = Decimal("0.00")
    for item in items:
        reorder_level = int(item.get("reorder_level") or 0)
        on_hand_qty, on_hand_value = await _mandir_inventory_item_position(
            tenant_id=context.tenant_id, app_key=context.app_key, item=item,
        )
        total_value += on_hand_value
        if reorder_level > 0 and on_hand_qty <= Decimal(str(reorder_level)):
            low_stock += 1
    return {
        "totalItems": len(items),
        "lowStockItems": low_stock,
        "totalValue": str(total_value.quantize(Decimal("0.01"))),
        "summary": {
            "total_items": len(items),
            "low_stock_items": low_stock,
            "total_value": str(total_value.quantize(Decimal("0.01"))),
        },
    }

