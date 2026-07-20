"""GST tax-period finalisation locks (read / list / set / validate reversals).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Uses runtime lookup on the service module for get_collection so existing tests
that monkeypatch business_service.get_collection keep working.
"""
from app.accounting.service import AccountingValidationError
from app.modules.business import service as business_service
from app.modules.business.schemas import GstPeriodLockUpdateRequest


def _period_key(value) -> str:
    """Return the GST tax period 'YYYY-MM' for a date or ISO date string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:7]
    return f"{value.year:04d}-{value.month:02d}"


def _period_label(period: str) -> str:
    try:
        year, month = period.split("-")
        return f"{business_service._MONTH_NAMES[int(month)]} {year}"
    except Exception:
        return period


async def is_gst_period_locked(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    period: str,
) -> bool:
    if not period:
        return False
    row = await business_service.get_collection(business_service.GST_PERIOD_LOCKS_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "period": period,
        }
    )
    return bool(row and row.get("locked"))


async def _validate_reversal_period(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    original_date,
    reversal_date,
    document_label: str,
) -> None:
    """Enforce that a reversal stays in the original document's GST tax period and
    that the period has not been finalised (locked)."""
    original_period = _period_key(original_date)
    reversal_period = _period_key(reversal_date)
    if original_period and reversal_period and reversal_period != original_period:
        raise AccountingValidationError(
            f"Reversal must be dated within {_period_label(original_period)} "
            f"(the {document_label}'s GST period). Cross-period reversals are not allowed."
        )
    if await is_gst_period_locked(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        period=original_period,
    ):
        raise AccountingValidationError(
            f"The {_period_label(original_period)} GST period is finalised and locked. "
            f"Reversals into a filed period are not allowed; raise a credit/debit note in the open period instead."
        )


def _period_lock_response_doc(doc: dict) -> dict:
    return {
        "period": doc.get("period"),
        "locked": bool(doc.get("locked")),
        "note": doc.get("note"),
        "updated_by": doc.get("updated_by"),
        "updated_at": doc.get("updated_at"),
    }


async def list_gst_period_locks(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    rows = (
        await business_service.get_collection(business_service.GST_PERIOD_LOCKS_COLLECTION)
        .find({"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id})
        .sort("period", -1)
        .to_list(length=500)
    )
    return {"items": [_period_lock_response_doc(row) for row in rows], "total": len(rows)}


async def set_gst_period_lock(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: GstPeriodLockUpdateRequest,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": payload.accounting_entity_id,
        "period": payload.period,
    }
    update_doc = {
        "locked": bool(payload.locked),
        "note": payload.note,
        "updated_by": updated_by,
        "updated_at": business_service._now(),
    }
    await business_service.get_collection(business_service.GST_PERIOD_LOCKS_COLLECTION).update_one(
        filters,
        {"$set": update_doc, "$setOnInsert": {**filters, "created_at": business_service._now()}},
        upsert=True,
    )
    await business_service._audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_gst_period_lock_updated",
        entity_type="business_gst_period_lock",
        entity_id=payload.period,
        new_value={**filters, **update_doc},
    )
    return _period_lock_response_doc({**filters, **update_doc})
