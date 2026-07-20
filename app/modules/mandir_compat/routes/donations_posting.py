"""MandirMitra donation posting routes (create, valuation approve, cancel, reconcile, cleanup).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import JournalEntry
from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.donation_compliance import classify_donation_compliance
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, _MANDIR_WRITE_ROUTE_DEPS, router

@router.post("/donations", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
@router.post("/donations/", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def create_donation(
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_temple_id: str | None = Header(default=None, alias="X-Temple-Id"),
):
    tenant_context = mandir_router.resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation creation",
    )
    tenant_id = tenant_context.tenant_id
    app_key = tenant_context.app_key
    temple_id = mandir_router._to_positive_int(x_temple_id)
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    donation_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    devotee_phone = mandir_router._normalize_phone(payload.get("devotee_phone") or payload.get("phone"))

    amount = mandir_router._safe_float(payload.get("amount"), 0.0)
    category = str(payload.get("category") or "General Donation")
    payment_mode = str(payload.get("payment_mode") or "Cash").lower()
    donation_type = str(payload.get("donation_type") or "cash").strip().lower() or "cash"
    if donation_type == "in_kind":
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Declared in-kind value must be greater than zero")
        if not mandir_router._safe_optional_str(payload.get("in_kind_item_name") or payload.get("item_name")):
            raise HTTPException(status_code=400, detail="In-kind item name is required")
        if not mandir_router._safe_optional_str(payload.get("in_kind_valuation_basis") or payload.get("valuation_basis")):
            raise HTTPException(status_code=400, detail="In-kind valuation basis is required")
    fund = None
    fund_id = str(payload.get("fund_id") or "").strip()
    if fund_id:
        fund = await mandir_router.get_collection("mandir_funds").find_one(
            {"id": fund_id, "tenant_id": tenant_id, "app_key": app_key, "active": True}
        )
        if fund is None:
            raise HTTPException(status_code=404, detail="Active fund not found")
        if not fund.get("accounting_dimension_id"):
            raise HTTPException(status_code=409, detail="Fund accounting dimension is not provisioned")
    festival = None
    festival_id = str(payload.get("festival_id") or "").strip()
    if festival_id:
        festival = await mandir_router.get_collection("mandir_festivals").find_one(
            {"id": festival_id, "tenant_id": tenant_id, "app_key": app_key, "active": True}
        )
        if festival is None:
            raise HTTPException(status_code=404, detail="Active festival not found")
    sponsorship_value = payload.get("is_sponsorship", False)
    is_sponsorship = sponsorship_value is True or str(sponsorship_value).strip().lower() in {"1", "true", "yes"}
    cash_income_category = mandir_router._mandir_cash_income_category(category)
    if fund and str(fund.get("fund_type") or "").lower() in {"restricted", "corpus"}:
        cash_income_category = "Specific Purpose Donations"
    if is_sponsorship:
        cash_income_category = "Sponsorship Income"
    devotee_prefix = mandir_router._safe_optional_str(
        payload.get("name_prefix")
        or payload.get("devotee_prefix")
        or payload.get("prefix")
        or payload.get("title")
        or payload.get("salutation")
    )
    devotee_name = str(payload.get("devotee_name") or payload.get("first_name") or "Unknown Devotee").strip() or "Unknown Devotee"
    devotee_address = mandir_router._safe_optional_str(payload.get("devotee_address") or payload.get("address"))
    devotee_city = mandir_router._safe_optional_str(payload.get("devotee_city") or payload.get("city"))
    devotee_state = mandir_router._safe_optional_str(payload.get("devotee_state") or payload.get("state"))
    devotee_pincode = mandir_router._safe_optional_str(payload.get("devotee_pincode") or payload.get("pincode"))
    raw_payment_account_id = mandir_router._safe_optional_str(payload.get("bank_account_id") or payload.get("payment_account_id"))
    compliance_config = await mandir_router.get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    )
    compliance = classify_donation_compliance(
        payload,
        compliance_config,
        amount=Decimal(str(amount)),
        donation_type=donation_type,
        payment_mode=payment_mode,
        donation_date=datetime.now(timezone.utc).date(),
        payment_account_id=raw_payment_account_id,
    )

    donation = {
        "donation_id": donation_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "temple_id": temple_id,
        "amount": amount,
        "category": category,
        "donation_type": donation_type,
        "in_kind_item_name": mandir_router._safe_optional_str(payload.get("in_kind_item_name") or payload.get("item_name")),
        "in_kind_item_type": mandir_router._safe_optional_str(payload.get("in_kind_item_type") or payload.get("item_type") or payload.get("asset_type")),
        "in_kind_quantity": mandir_router._safe_optional_str(payload.get("in_kind_quantity") or payload.get("quantity")),
        "in_kind_valuation_basis": mandir_router._safe_optional_str(payload.get("in_kind_valuation_basis") or payload.get("valuation_basis")),
        "event_name": mandir_router._safe_optional_str(payload.get("event_name") or payload.get("festival_name")),
        "fund_id": fund_id or None,
        "fund_name": str(fund.get("name")) if fund else None,
        "fund_type": str(fund.get("fund_type")) if fund else None,
        "fund_dimension_id": str(fund.get("accounting_dimension_id")) if fund else None,
        "festival_id": festival_id or None,
        "festival_name": str(festival.get("name")) if festival else None,
        "is_sponsorship": is_sponsorship,
        "income_category": cash_income_category,
        "status": "pending_valuation" if donation_type == "in_kind" else "posted",
        "valuation_status": "pending_approval" if donation_type == "in_kind" else None,
        "inventory_item_id": mandir_router._safe_optional_str(payload.get("inventory_item_id")),
        "inventory_quantity": mandir_router._safe_optional_str(payload.get("inventory_quantity")),
        "payment_mode": payload.get("payment_mode") or "Cash",
        "devotee_name": devotee_name,
        "devotee_phone": devotee_phone,
        "devotee_prefix": devotee_prefix,
        "devotee_address": devotee_address,
        "devotee_city": devotee_city,
        "devotee_state": devotee_state,
        "devotee_pincode": devotee_pincode,
        "devotee": {
            "name": devotee_name,
            "name_prefix": devotee_prefix,
            "phone": devotee_phone,
            "email": str(payload.get("email") or "") or None,
            "address": devotee_address,
            "city": devotee_city,
            "state": devotee_state,
            "pincode": devotee_pincode,
        },
        "created_by": mandir_router._mandir_actor_id(current_user),
        "created_at": now,
        **compliance,
    }

    donation["id"] = donation_id
    donation["receipt_number"] = await mandir_router._next_receipt_number(
        tenant_id=tenant_id,
        app_key=app_key,
        receipt_kind="donation",
        receipt_date=now,
    )
    donation["receipt_pdf_url"] = f"/api/v1/donations/{donation_id}/receipt/pdf"

    col = mandir_router.get_collection("mandir_donations")
    try:
        await col.insert_one(donation)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save donation: {exc}") from exc

    # Valued donations and sponsorships must post into accounting; otherwise reports and TB diverge.
    if amount > 0 and donation_type != "in_kind":
        try:
            raw_account_id = raw_payment_account_id
            debit_account_id = await mandir_router._resolve_mandir_payment_account_id(
                session,
                tenant_id,
                raw_account_id,
                payment_mode,
            )
            if not debit_account_id:
                await col.delete_one({"donation_id": donation_id, "tenant_id": tenant_id, "app_key": app_key})
                raise HTTPException(status_code=400, detail="No valid cash/bank account is configured for donation posting")
            income_category = cash_income_category

            income_acc_id = await mandir_router._resolve_mandir_income_account(session, tenant_id, income_category)
            journal_payload = JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"{category} from {donation['devotee']['name']}",
                reference=donation["receipt_number"],
                source_module="mandirmitra",
                source_document_type="donation",
                source_document_id=donation_id,
                lines=[
                    JournalLineIn(account_id=debit_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(
                        account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount)),
                        cost_center_id=str(fund.get("accounting_dimension_id")) if fund else None,
                    ),
                ],
            )
            await mandir_router.post_journal_entry(
                session=session,
                app_key=app_key,
                tenant_id=tenant_id,
                created_by="mandir_compat_system",
                payload=journal_payload,
                idempotency_key=f"don_{donation_id}",
            )
        except HTTPException:
            raise
        except Exception as exc:
            await col.delete_one({"donation_id": donation_id, "tenant_id": tenant_id, "app_key": app_key})
            raise HTTPException(status_code=500, detail=f"Failed to post donation journal: {exc}") from exc

    try:
        await mandir_router._upsert_devotee_from_contribution(
            tenant_id,
            app_key,
            temple_id=temple_id,
            phone=devotee_phone,
            name_prefix=devotee_prefix,
            name=devotee_name,
            email=str(payload.get("email") or "") or None,
            address=devotee_address,
            city=devotee_city,
            state=devotee_state,
            pincode=devotee_pincode,
        )
    except Exception as exc:
        mandir_router.logger.warning("Donation saved but devotee upsert failed for tenant=%s phone=%s: %s", tenant_id, devotee_phone, exc)

    return mandir_router._mandir_donation_view(donation)


@router.post("/donations/{donation_id}/valuation/approve", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def approve_mandir_in_kind_valuation(
    donation_id: str,
    payload: dict[str, Any],
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = mandir_router.resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="in-kind valuation approval",
    )
    collection = mandir_router.get_collection("mandir_donations")
    query = {"donation_id": donation_id, "tenant_id": context.tenant_id, "app_key": context.app_key}
    donation = await collection.find_one(query)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")
    if str(donation.get("donation_type") or "").lower() != "in_kind":
        raise HTTPException(status_code=409, detail="Only in-kind donations require valuation approval")
    if donation.get("status") == "posted" and donation.get("valuation_status") == "approved":
        return {**mandir_router._mandir_donation_view(donation), "_idempotent": True}
    if donation.get("valuation_status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending valuations can be approved")
    actor = mandir_router._mandir_actor_id(current_user)
    if actor == str(donation.get("created_by") or ""):
        raise HTTPException(status_code=409, detail="Valuation maker and approver must be different users")
    try:
        approved_amount = Decimal(str(payload.get("approved_amount") or donation.get("amount") or "0")).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid approved_amount is required") from exc
    if not approved_amount.is_finite() or approved_amount <= 0:
        raise HTTPException(status_code=400, detail="Approved value must be greater than zero")
    approval_basis = str(payload.get("approval_basis") or "").strip()
    if len(approval_basis) < 3:
        raise HTTPException(status_code=400, detail="Valuation approval basis is required")

    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, context.tenant_id, raise_on_failure=True)
    inventory_enabled = await mandir_router._mandir_inventory_accounting_enabled(context.tenant_id, context.app_key)
    account_code, account_name, account_type = mandir_router._mandir_in_kind_debit_account_target(
        donation, donation.get("category"), inventory_accounting_enabled=inventory_enabled,
    )
    debit_account_id = await mandir_router._resolve_or_create_mandir_account(
        session, context.tenant_id, code=account_code, name=account_name, account_type=account_type,
        classification="nominal" if account_type == "expense" else "real",
    )
    income_category = (
        "In-Kind Sponsorship Income"
        if donation.get("is_sponsorship")
        else mandir_router._mandir_in_kind_income_category(donation.get("category"))
    )
    income_account_id = await mandir_router._resolve_mandir_income_account(session, context.tenant_id, income_category)
    dimension_id = str(donation.get("fund_dimension_id") or "") or None

    movement = None
    movement_collection = mandir_router.get_collection("mandir_inventory_movements")
    if account_code in {"14003", "14004"}:
        item_id = str(payload.get("inventory_item_id") or donation.get("inventory_item_id") or "").strip()
        item = await mandir_router.get_collection("mandir_inventory_items").find_one(
            {"id": item_id, "tenant_id": context.tenant_id, "app_key": context.app_key, "is_active": True}
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Active inventory item is required for inventory-valued donation")
        try:
            quantity = Decimal(str(payload.get("approved_quantity") or donation.get("inventory_quantity") or "0")).quantize(Decimal("0.001"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Valid approved_quantity is required") from exc
        if not quantity.is_finite() or quantity <= 0:
            raise HTTPException(status_code=400, detail="Approved inventory quantity must be greater than zero")
        movement = {
            "id": str(uuid4()), "tenant_id": context.tenant_id, "app_key": context.app_key,
            "item_id": item_id, "item_name": item.get("name"), "movement_type": "receipt",
            "quantity": str(quantity), "unit_value": str((approved_amount / quantity).quantize(Decimal("0.01"))),
            "total_value": str(approved_amount), "movement_date": datetime.now(timezone.utc).date().isoformat(),
            "source_type": "in_kind_donation", "source_id": donation_id,
            "status": "pending_accounting", "created_by": actor, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await movement_collection.insert_one(movement)

    try:
        journal, _created = await mandir_router.post_journal_entry(
            session=session, app_key=context.app_key, tenant_id=context.tenant_id, created_by=actor,
            payload=JournalPostRequest(
                entry_date=datetime.now(timezone.utc).date(),
                description=f"Approved in-kind valuation: {donation.get('in_kind_item_name') or donation.get('category')}",
                reference=str(donation.get("receipt_number")), source_module="mandirmitra",
                source_document_type="in_kind_donation", source_document_id=donation_id,
                lines=[
                    JournalLineIn(
                        account_id=debit_account_id, debit=approved_amount, credit=Decimal("0"),
                        cost_center_id=dimension_id,
                    ),
                    JournalLineIn(
                        account_id=income_account_id, debit=Decimal("0"), credit=approved_amount,
                        cost_center_id=dimension_id,
                    ),
                ],
            ),
            idempotency_key=f"don_{donation_id}",
        )
    except Exception:
        if movement:
            await movement_collection.update_one(
                {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                {"$set": {"status": "accounting_failed"}}, upsert=False,
            )
        raise

    now = datetime.now(timezone.utc).isoformat()
    patch = {
        "amount": float(approved_amount), "status": "posted", "valuation_status": "approved",
        "approved_value": str(approved_amount), "valuation_approval_basis": approval_basis,
        "valuation_approved_by": actor, "valuation_approved_at": now,
        "journal_entry_id": int(journal.id), "updated_at": now,
    }
    if movement:
        patch.update({"inventory_item_id": movement["item_id"], "inventory_quantity": movement["quantity"], "inventory_movement_id": movement["id"]})
    try:
        await collection.update_one(query, {"$set": patch}, upsert=False)
        if movement:
            await movement_collection.update_one(
                {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                {"$set": {"status": "posted", "journal_entry_id": int(journal.id), "posted_at": now}}, upsert=False,
            )
    except Exception as exc:
        await mandir_router.reverse_journal_entry(
            session=session, tenant_id=context.tenant_id, app_key=context.app_key, accounting_entity_id="primary",
            journal_id=int(journal.id), created_by=actor, reason="Compensate failed in-kind valuation persistence",
            idempotency_key=f"don_{donation_id}_valuation_compensation",
        )
        if movement:
            try:
                await movement_collection.update_one(
                    {"id": movement["id"], "tenant_id": context.tenant_id, "app_key": context.app_key},
                    {"$set": {"status": "compensated", "updated_at": now}}, upsert=False,
                )
            except Exception:
                mandir_router.logger.exception("Failed to mark compensated inventory receipt donation=%s", donation_id)
        try:
            await collection.update_one(
                query, {"$set": {"status": "pending_valuation", "valuation_status": "pending_approval", "updated_at": now}},
                upsert=False,
            )
        except Exception:
            mandir_router.logger.exception("Failed to restore pending valuation state donation=%s", donation_id)
        raise HTTPException(status_code=500, detail="Valuation persistence failed; accounting was reversed") from exc
    return mandir_router._mandir_donation_view({**donation, **patch})


@router.post("/donations/{donation_id}/cancel", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def cancel_donation_receipt(
    donation_id: str,
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    return await mandir_router._cancel_mandir_receipt_source(
        source_kind="donation",
        source_id=donation_id,
        collection_name="mandir_donations",
        id_field="donation_id",
        idempotency_prefix="don_",
        payload=payload,
        session=session,
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
    )


@router.post("/donations/reconcile-posting", dependencies=_MANDIR_WRITE_ROUTE_DEPS)
async def reconcile_donation_posting(
    limit: int = Query(default=500, ge=1, le=5000),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    """
    Backfill journal entries for legacy donation docs that were saved before posting guardrails.
    """
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._ensure_default_mandir_sql_accounts_safe(session, tenant_id, raise_on_failure=True)

    col = mandir_router.get_collection("mandir_donations")
    try:
        docs = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).limit(limit).to_list(length=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load donations for reconciliation: {exc}") from exc

    scanned = 0
    posted = 0
    already_posted = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for doc in docs:
        scanned += 1
        donation_id = str(doc.get("donation_id") or doc.get("id") or doc.get("_id") or "").strip()
        if not donation_id:
            skipped += 1
            continue

        idempotency_key = f"don_{donation_id}"
        exists_stmt = select(JournalEntry.id).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.idempotency_key == idempotency_key,
        )
        existing_journal_id = (await session.execute(exists_stmt)).scalar_one_or_none()
        if existing_journal_id is not None:
            already_posted += 1
            continue

        amount = mandir_router._safe_float(doc.get("amount"), 0.0)
        if amount <= 0:
            skipped += 1
            continue

        payment_mode_raw = str(doc.get("payment_mode") or "Cash").strip().lower()
        payment_mode_for_account = "cash" if payment_mode_raw == "cash" else "bank"

        try:
            resolved_account_id = await mandir_router._resolve_mandir_payment_account_id(
                session,
                tenant_id,
                doc.get("bank_account_id") or doc.get("payment_account_id"),
                payment_mode_for_account,
            )
            if not resolved_account_id:
                resolved_account_id = await mandir_router._resolve_mandir_payment_account_id(session, tenant_id, None, payment_mode_for_account)
            if not resolved_account_id:
                raise ValueError("No valid cash/bank account is configured for donation posting")

            category = str(doc.get("category") or "General Donation")
            income_acc_id = await mandir_router._resolve_mandir_income_account(session, tenant_id, "General Donations")
            devotee = doc.get("devotee") if isinstance(doc.get("devotee"), dict) else {}
            devotee_name = str(devotee.get("name") or doc.get("devotee_name") or "Devotee")

            created_raw = str(doc.get("created_at") or "").strip()
            entry_date = datetime.now(timezone.utc).date()
            if created_raw:
                try:
                    entry_date = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).date()
                except Exception:
                    pass

            journal_payload = JournalPostRequest(
                entry_date=entry_date,
                description=f"{category} from {devotee_name}",
                reference=f"DON-{donation_id[:8].upper()}",
                lines=[
                    JournalLineIn(account_id=resolved_account_id, debit=Decimal(str(amount)), credit=Decimal("0")),
                    JournalLineIn(account_id=income_acc_id, debit=Decimal("0"), credit=Decimal(str(amount))),
                ],
            )
            await mandir_router.post_journal_entry(
                session=session,
                tenant_id=tenant_id,
                created_by="mandir_reconcile",
                payload=journal_payload,
                idempotency_key=idempotency_key,
            )
            posted += 1
        except Exception as exc:
            errors.append({"donation_id": donation_id, "error": str(exc)})

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "app_key": app_key,
        "scanned": scanned,
        "posted": posted,
        "already_posted": already_posted,
        "skipped": skipped,
        "errors": errors[:25],
    }


@router.delete("/donations/cleanup", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def cleanup_donation_entry(
    amount: float = Query(..., gt=0),
    devotee_phone: str = Query(..., min_length=6),
    payment_mode: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    normalized_phone = mandir_router._normalize_phone(devotee_phone)
    normalized_amount = mandir_router._safe_float(amount, 0.0)
    normalized_mode = str(payment_mode or "").strip().lower() or None

    try:
        col = mandir_router.get_collection("mandir_donations")
        candidates = await col.find(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "amount": normalized_amount,
                "devotee_phone": normalized_phone,
            }
        ).sort("created_at", -1).to_list(length=50)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to search donation entries: {exc}") from exc

    if normalized_mode:
        candidates = [
            row
            for row in candidates
            if str(row.get("payment_mode") or "").strip().lower() == normalized_mode
        ]

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="Donation entry not found for the provided amount and phone",
        )

    donation = candidates[0]
    donation_id = str(donation.get("donation_id") or "")

    try:
        await col.delete_one(
            {
                "donation_id": donation_id,
                "tenant_id": tenant_id,
                "app_key": app_key,
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete donation entry: {exc}") from exc

    journal_deleted = False
    journal_status = "not_found"
    journal_idempotency_key = f"don_{donation_id}" if donation_id else None
    if journal_idempotency_key:
        try:
            journal_stmt = select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.idempotency_key == journal_idempotency_key,
            )
            journal_entry = (await session.execute(journal_stmt)).scalar_one_or_none()
            if journal_entry is not None:
                await session.delete(journal_entry)
                await session.commit()
                journal_deleted = True
                journal_status = "deleted"
        except Exception as exc:
            try:
                await session.rollback()
            except Exception:
                pass
            journal_status = f"delete_failed: {exc}"

    return {
        "status": "deleted",
        "matched_count": len(candidates),
        "donation_id": donation_id,
        "amount": normalized_amount,
        "devotee_phone": normalized_phone,
        "payment_mode": donation.get("payment_mode"),
        "journal_deleted": journal_deleted,
        "journal_status": journal_status,
    }

