"""MandirMitra shared receipt cancellation helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Used by donation, seva, and refund receipt cancellation flows.

Important for tests:
- These helpers call other symbols via `mandir_router.<name>` so monkeypatching
  `app.modules.mandir_compat.router.<name>` continues to affect runtime behavior.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import JournalEntry
from app.accounting.service import reverse_journal_entry
from app.modules.mandir_compat import router as mandir_router

def _mandir_receipt_cancellation_metadata(payload: dict[str, Any] | None, current_user: dict[str, Any]) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    reason = str(
        payload.get("reason")
        or payload.get("cancellation_reason")
        or payload.get("refund_reason")
        or ""
    ).strip()
    if len(reason) < 3:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")
    now = datetime.now(timezone.utc).isoformat()
    refund_mode = mandir_router._safe_optional_str(payload.get("refund_mode") or payload.get("refund_payment_mode"))
    refund_reference = mandir_router._safe_optional_str(payload.get("refund_reference") or payload.get("refund_utr") or payload.get("refund_transaction_reference"))
    refund_date = mandir_router._safe_optional_str(payload.get("refund_date")) or now[:10]
    return {
        "status": "reversed",
        "cancellation_reason": reason,
        "refund_mode": refund_mode,
        "refund_reference": refund_reference,
        "refund_date": refund_date if refund_mode or refund_reference else None,
        "reversed_at": now,
        "cancelled_at": now,
        "cancelled_by": mandir_router._mandir_actor_id(current_user),
        "updated_at": now,
    }


async def _reverse_mandir_source_journal(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    source_key: str,
    reason: str,
    current_user: dict[str, Any],
) -> tuple[JournalEntry, bool]:
    stmt = select(JournalEntry).where(
        JournalEntry.tenant_id == tenant_id,
        JournalEntry.app_key == app_key,
        JournalEntry.accounting_entity_id == "primary",
        JournalEntry.idempotency_key == source_key,
    )
    original = (await session.execute(stmt)).scalar_one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Original accounting journal was not found for this receipt")
    try:
        return await reverse_journal_entry(
            session=session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id="primary",
            journal_id=int(original.id),
            created_by=mandir_router._mandir_actor_id(current_user),
            reason=reason,
            idempotency_key=f"{source_key}_receipt_reversal",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reverse receipt journal: {exc}") from exc


async def _cancel_mandir_receipt_source(
    *,
    source_kind: str,
    source_id: str,
    collection_name: str,
    id_field: str,
    idempotency_prefix: str,
    payload: dict[str, Any] | None,
    session: AsyncSession,
    current_user: dict[str, Any],
    x_tenant_id: str | None,
    x_app_key: str | None,
) -> dict[str, Any]:
    tenant_context = mandir_router.resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation=f"{source_kind} receipt cancellation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    collection = mandir_router.get_collection(collection_name)
    existing = await collection.find_one({id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key})
    if existing is None:
        raise HTTPException(status_code=404, detail=f"{source_kind.title()} receipt not found")

    current_status = str(existing.get("status") or "").strip().lower()
    if current_status in {"cancelled", "reversed"}:
        view = mandir_router._mandir_donation_view(existing) if source_kind == "donation" else mandir_router._mandir_seva_booking_view(existing)
        view["_idempotent"] = True
        return view

    patch = _mandir_receipt_cancellation_metadata(payload, current_user)
    if source_kind == "donation" and current_status == "pending_valuation":
        patch["valuation_status"] = "cancelled"
        await collection.update_one(
            {id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key},
            {"$set": patch}, upsert=False,
        )
        return mandir_router._mandir_donation_view({**existing, **patch})

    inventory_reversal = None
    movement_collection = None
    if source_kind == "donation" and existing.get("inventory_movement_id"):
        movement_collection = mandir_router.get_collection("mandir_inventory_movements")
        receipt_movement = await movement_collection.find_one(
            {"id": str(existing["inventory_movement_id"]), "tenant_id": tenant_id, "app_key": app_key, "status": "posted"}
        )
        item = await mandir_router.get_collection("mandir_inventory_items").find_one(
            {"id": str(existing.get("inventory_item_id") or ""), "tenant_id": tenant_id, "app_key": app_key, "is_active": True}
        )
        if receipt_movement is None or item is None:
            raise HTTPException(status_code=409, detail="Inventory receipt evidence is unavailable for donation reversal")
        available = await mandir_router._mandir_inventory_item_balance(tenant_id=tenant_id, app_key=app_key, item=item)
        receipt_quantity = Decimal(str(receipt_movement.get("quantity") or "0"))
        if available < receipt_quantity:
            raise HTTPException(status_code=409, detail="Cannot reverse donation after its inventory has been consumed")
        reversal_movement_id = f"donation-reversal-{source_id}"
        inventory_reversal = await movement_collection.find_one(
            {"id": reversal_movement_id, "tenant_id": tenant_id, "app_key": app_key}
        )
        if inventory_reversal is None:
            inventory_reversal = {
                "id": reversal_movement_id, "tenant_id": tenant_id, "app_key": app_key,
                "item_id": receipt_movement.get("item_id"), "item_name": receipt_movement.get("item_name"),
                "movement_type": "receipt_reversal", "quantity": str(receipt_quantity),
                "unit_value": str(receipt_movement.get("unit_value") or "0"),
                "total_value": str(receipt_movement.get("total_value") or "0"),
                "movement_date": datetime.now(timezone.utc).date().isoformat(),
                "source_type": "in_kind_donation_reversal", "source_id": str(source_id),
                "status": "pending_accounting", "created_by": mandir_router._mandir_actor_id(current_user),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await movement_collection.insert_one(inventory_reversal)
    reversal_entry, _created = await mandir_router._reverse_mandir_source_journal(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        source_key=f"{idempotency_prefix}{source_id}",
        reason=str(patch["cancellation_reason"]),
        current_user=current_user,
    )
    patch["reversal_journal_id"] = int(reversal_entry.id)
    patch["reversal_idempotency_key"] = f"{idempotency_prefix}{source_id}_receipt_reversal"
    if inventory_reversal is not None and movement_collection is not None:
        await movement_collection.update_one(
            {"id": inventory_reversal["id"], "tenant_id": tenant_id, "app_key": app_key},
            {"$set": {
                "status": "posted", "journal_entry_id": int(reversal_entry.id),
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=False,
        )
        patch["inventory_reversal_movement_id"] = inventory_reversal["id"]

    await collection.update_one(
        {id_field: str(source_id), "tenant_id": tenant_id, "app_key": app_key},
        {"$set": patch},
        upsert=False,
    )
    try:
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=mandir_router._mandir_actor_id(current_user),
            product=app_key,
            action=f"{source_kind}_receipt_cancelled",
            entity_type=f"mandir_{source_kind}_receipt",
            entity_id=str(source_id),
            old_value={"status": existing.get("status"), "receipt_number": existing.get("receipt_number")},
            new_value={
                "status": patch["status"],
                "reason": patch["cancellation_reason"],
                "reversal_journal_id": patch["reversal_journal_id"],
                "refund_mode": patch.get("refund_mode"),
                "refund_reference": patch.get("refund_reference"),
            },
        )
    except Exception:
        mandir_router.logger.warning("Failed to write audit event for %s receipt cancellation %s", source_kind, source_id, exc_info=True)

    updated = {**existing, **patch}
    return mandir_router._mandir_donation_view(updated) if source_kind == "donation" else mandir_router._mandir_seva_booking_view(updated)


