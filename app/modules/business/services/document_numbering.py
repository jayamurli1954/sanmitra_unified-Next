"""Shared Mongo counter-based document number reservation.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Uses runtime lookup on the service module for get_collection so existing tests
that monkeypatch business_service.get_collection keep working.
"""
from app.modules.business import service as business_service


async def _reserve_sequence_number(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    doc_type: str,
    prefix: str,
    on_date,
    fallback_collection: str,
) -> str:
    financial_year = f"{on_date.year}-{on_date.year + 1}" if on_date.month >= 4 else f"{on_date.year - 1}-{on_date.year}"
    counter_id = f"{tenant_id}:{app_key}:{accounting_entity_id}:{doc_type}:{financial_year}"
    counters = business_service.get_collection(business_service.VOUCHER_COUNTERS_COLLECTION)
    try:
        from pymongo import ReturnDocument

        counter = await counters.find_one_and_update(
            {"_id": counter_id},
            {
                "$inc": {"seq": 1},
                "$setOnInsert": {
                    "tenant_id": tenant_id,
                    "app_key": app_key,
                    "accounting_entity_id": accounting_entity_id,
                    "voucher_type": doc_type,
                    "financial_year": financial_year,
                    "created_at": business_service._now(),
                },
                "$set": {"updated_at": business_service._now()},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq = int((counter or {}).get("seq") or 1)
    except Exception:
        existing = await business_service.get_collection(fallback_collection).count_documents(
            {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
        )
        seq = int(existing) + 1
    return f"{prefix}-{financial_year}-{seq:06d}"
