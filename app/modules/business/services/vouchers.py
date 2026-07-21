"""Typed business voucher create / list / review / approve / reverse / post.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.

Quarantined helpers (_reserve_voucher_number, _reverse_after_domain_persistence_failure)
are resolved at runtime via the service facade so monkeypatches keep working.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    AccountingNotFoundError,
    AccountingValidationError,
)
from app.modules.business.schemas import (
    ApprovalReviewRequest,
    TypedVoucherCreateRequest,
    TypedVoucherReversalRequest,
)
from app.modules.business import service as business_service
from app.modules.business.services.common import (
    _audit_business_event,
    _ensure_business_chart_for_voucher_codes,
    _json_safe_doc,
    _money,
    _now,
    _voucher_response_doc,
)

async def list_vouchers(
    *,
    session: AsyncSession | None = None,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    voucher_type: str | None = None,
    status: str | None = None,
    approval_status: str | None = None,
    limit: int = 100,
) -> dict:
    del session  # Voucher headers are stored in Mongo; posted accounting rows remain linked by journal_entry_id.
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
    }
    if voucher_type:
        filters["voucher_type"] = voucher_type
    if status:
        filters["status"] = status
    if approval_status:
        filters["approval_status"] = approval_status

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await business_service.get_collection(business_service.VOUCHERS_COLLECTION)
        .find(filters)
        .sort("entry_date", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_voucher_response_doc(row) for row in rows], "total": len(rows)}


async def get_voucher(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    voucher_id: str,
) -> dict | None:
    row = await business_service.get_collection(business_service.VOUCHERS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "voucher_id": voucher_id,
        }
    )
    return _voucher_response_doc(row) if row else None


async def review_typed_voucher(
    *,
    session: AsyncSession | None = None,
    tenant_id: str,
    app_key: str,
    voucher_id: str,
    reviewed_by: str,
    payload: ApprovalReviewRequest,
) -> dict:
    vouchers = business_service.get_collection(business_service.VOUCHERS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "voucher_id": voucher_id,
    }
    voucher = await vouchers.find_one(filters)
    if voucher is None:
        raise AccountingNotFoundError("Voucher not found")
    old_value = _voucher_response_doc(voucher)
    current_status = str(voucher.get("status") or "").strip().lower()
    if current_status in {"draft", "pending_approval"}:
        if current_status == "draft":
            raise AccountingValidationError("Only submitted vouchers can be approved or rejected")
        if payload.approve:
            return await _approve_typed_voucher_document(
                session=session,
                tenant_id=tenant_id,
                app_key=app_key,
                reviewed_by=reviewed_by,
                voucher=voucher,
                old_value=old_value,
                approval_notes=payload.notes,
            )
        patch = {
            "status": "rejected",
            "approval_required": True,
            "approval_status": "rejected",
            "approval_decided_at": _now(),
            "approval_decided_by": reviewed_by,
            "approval_notes": payload.notes,
            "rejection_reason": payload.rejection_reason or "Rejected during manual review",
            "updated_at": _now(),
        }
        if voucher.get("approval_submitted_at") is None:
            patch["approval_submitted_at"] = voucher.get("created_at")
            patch["approval_submitted_by"] = voucher.get("created_by")
        await vouchers.update_one(filters, {"$set": patch})
        voucher.update(patch)
        result = _voucher_response_doc(voucher)
        await _audit_business_event(
            tenant_id=tenant_id,
            app_key=app_key,
            user_id=reviewed_by,
            action="business_voucher_reviewed",
            entity_type="business_voucher",
            entity_id=voucher_id,
            old_value=old_value,
            new_value=result,
        )
        return result
    if current_status != "posted":
        raise AccountingValidationError("Only posted or pending-approval vouchers can be reviewed")

    approval_status = "approved" if payload.approve else "rejected"
    patch = {
        "approval_required": True,
        "approval_status": approval_status,
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": payload.notes,
        "rejection_reason": None if payload.approve else (payload.rejection_reason or "Rejected during manual review"),
        "updated_at": _now(),
    }
    if voucher.get("approval_submitted_at") is None:
        patch["approval_submitted_at"] = voucher.get("created_at")
        patch["approval_submitted_by"] = voucher.get("created_by")

    await vouchers.update_one(filters, {"$set": patch})
    voucher.update(patch)
    result = _voucher_response_doc(voucher)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_voucher_reviewed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def _approve_typed_voucher_document(
    *,
    session,
    tenant_id: str,
    app_key: str,
    reviewed_by: str,
    voucher: dict,
    old_value: dict,
    approval_notes: str | None,
) -> dict:
    if session is None:
        raise AccountingValidationError("Approval posting requires an active accounting session")

    voucher_id = str(voucher.get("voucher_id") or "")
    voucher_number = str(voucher.get("voucher_number") or voucher_id)
    accounting_entity_id = str(voucher.get("accounting_entity_id") or "primary")
    entry_date = date.fromisoformat(str(voucher.get("entry_date") or "")[:10])
    amount = Decimal(str(voucher.get("amount") or "0")).quantize(Decimal("0.01"))
    debit_account_id = int(voucher.get("debit_account_id"))
    credit_account_id = int(voucher.get("credit_account_id"))
    party_id = voucher.get("party_id")
    voucher_type = str(voucher.get("voucher_type") or "journal")
    description = str(voucher.get("description") or f"{voucher_type.title()} voucher")
    reference = str(voucher.get("reference") or voucher_number)
    vouchers = business_service.get_collection(business_service.VOUCHERS_COLLECTION)

    try:
        journal_entry, created = await business_service.post_journal_entry(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            payload=JournalPostRequest(
                entry_date=entry_date,
                description=description,
                reference=reference,
                source_module="business",
                source_document_type="voucher",
                source_document_id=voucher_id,
                lines=[
                    JournalLineIn(
                        account_id=debit_account_id,
                        debit=amount,
                        credit=Decimal("0"),
                        party_id=party_id if voucher_type == "payment" else None,
                    ),
                    JournalLineIn(
                        account_id=credit_account_id,
                        debit=Decimal("0"),
                        credit=amount,
                        party_id=party_id if voucher_type == "receipt" else None,
                    ),
                ],
            ),
            idempotency_key=f"business-voucher:{voucher_id}",
        )
    except Exception as exc:
        raise AccountingValidationError(f"Voucher approval posting failed: {exc}") from exc

    patch = {
        "status": "posted",
        "journal_entry_id": journal_entry.id,
        "approval_required": True,
        "approval_status": "approved",
        "approval_submitted_at": voucher.get("approval_submitted_at") or voucher.get("created_at"),
        "approval_submitted_by": voucher.get("approval_submitted_by") or voucher.get("created_by"),
        "approval_decided_at": _now(),
        "approval_decided_by": reviewed_by,
        "approval_notes": approval_notes or "Approved and posted",
        "rejection_reason": None,
        "updated_at": _now(),
    }
    try:
        await vouchers.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "voucher_id": voucher_id},
            {"$set": patch},
        )
    except Exception as exc:
        await business_service._reverse_after_domain_persistence_failure(
            session,
            tenant_id=tenant_id,
            app_key=app_key,
            accounting_entity_id=accounting_entity_id,
            created_by=reviewed_by,
            journal_entry_id=int(journal_entry.id),
            document_label="Business voucher",
            document_id=voucher_id,
            reversal_reason=f"Compensation after business voucher approval persistence failure for {voucher_number}",
            reversal_idempotency_key=f"business-voucher-approve-compensate:{voucher_id}:{journal_entry.id}",
        )
        raise AccountingValidationError(
            "Business voucher approval persistence failed after journal posting; the accounting entry was automatically reversed"
        ) from exc
    voucher.update(patch)
    result = _voucher_response_doc(voucher, created=created)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=reviewed_by,
        action="business_voucher_reviewed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_value,
        new_value=result,
    )
    return result


async def reverse_typed_voucher(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    voucher_id: str,
    created_by: str,
    payload: TypedVoucherReversalRequest,
    idempotency_key: str | None,
) -> dict:
    vouchers = business_service.get_collection(business_service.VOUCHERS_COLLECTION)
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "voucher_id": voucher_id,
    }
    voucher = await vouchers.find_one(filters)
    if voucher is None:
        raise AccountingNotFoundError("Business voucher not found")

    if voucher.get("status") == "reversed" and voucher.get("reversal_journal_entry_id"):
        doc = _json_safe_doc(voucher)
        doc["created"] = False
        return doc

    journal_entry_id = voucher.get("journal_entry_id")
    if not journal_entry_id:
        raise AccountingValidationError("Business voucher is not linked to a posted journal entry")
    if voucher.get("status") != "posted":
        raise AccountingValidationError("Only posted business vouchers can be reversed")

    old_voucher = _json_safe_doc(voucher)
    reversal_key = idempotency_key or f"business-voucher-reversal:{voucher_id}"
    reversal, created = await business_service.reverse_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        created_by=created_by,
        journal_id=int(journal_entry_id),
        reversal_date=payload.reversal_date or date.today(),
        reason=payload.reason,
        idempotency_key=reversal_key,
    )
    update = {
        "status": "reversed",
        "reversal_journal_entry_id": reversal.id,
        "reversal_reason": payload.reason,
        "reversed_at": _now(),
        "updated_at": _now(),
    }
    await vouchers.update_one(filters, {"$set": update})
    voucher.update(update)
    doc = _json_safe_doc(voucher)
    doc["created"] = created
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_voucher_reversed",
        entity_type="business_voucher",
        entity_id=voucher_id,
        old_value=old_voucher,
        new_value=doc,
    )
    return doc


async def post_typed_voucher(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: TypedVoucherCreateRequest,
    idempotency_key: str | None,
) -> dict:
    amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    await _ensure_business_chart_for_voucher_codes(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        payload=payload,
    )
    debit_account_id = await business_service._resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=payload.debit_account_id,
        account_code=payload.debit_account_code,
        side="debit",
    )
    credit_account_id = await business_service._resolve_voucher_account_id(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        account_id=payload.credit_account_id,
        account_code=payload.credit_account_code,
        side="credit",
    )
    if debit_account_id == credit_account_id:
        raise AccountingValidationError("Debit and credit accounts must be different")

    await business_service.validate_dimension_refs(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        cost_centre_id=payload.cost_centre_id,
        project_id=payload.project_id,
    )

    if idempotency_key:
        existing = await business_service.get_collection(business_service.VOUCHERS_COLLECTION).find_one(
            {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "accounting_entity_id": payload.accounting_entity_id,
                "idempotency_key": idempotency_key,
            }
        )
        if existing is not None:
            doc = _json_safe_doc(existing)
            doc["created"] = False
            return doc

    voucher_id = str(uuid4())
    voucher_number = payload.reference or await business_service._reserve_voucher_number(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=payload.accounting_entity_id,
        voucher_type=payload.voucher_type,
        entry_date=payload.entry_date,
    )
    reference = voucher_number
    now = _now()
    doc = {
        "voucher_id": voucher_id,
        "voucher_number": voucher_number,
        "voucher_type": payload.voucher_type,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "party_id": payload.party_id,
        "cost_centre_id": payload.cost_centre_id,
        "project_id": payload.project_id,
        "amount": _money(amount),
        "entry_date": payload.entry_date.isoformat(),
        "debit_account_id": debit_account_id,
        "credit_account_id": credit_account_id,
        "description": payload.description,
        "reference": reference,
        "status": "pending_approval",
        "approval_required": True,
        "approval_status": "pending_approval",
        "approval_submitted_at": now,
        "approval_submitted_by": created_by,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    if idempotency_key:
        doc["idempotency_key"] = idempotency_key
    vouchers = business_service.get_collection(business_service.VOUCHERS_COLLECTION)
    await vouchers.insert_one(doc)

    result = _voucher_response_doc(doc, created=True)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_voucher_created",
        entity_type="business_voucher",
        entity_id=voucher_id,
        new_value=result,
    )
    return result


