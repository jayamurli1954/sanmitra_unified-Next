"""Business party master CRUD (create / list / get / update / deactivate).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Party balances are NOT stored here — ledger reports remain the source of truth
(see services/party_ledger.py). Imported via the service.py facade.
"""
from uuid import uuid4

from app.db.mongo import get_collection
from app.modules.business.schemas import PartyCreateRequest, PartyUpdateRequest
from app.modules.business.service import (
    PARTIES_COLLECTION,
    _audit_business_event,
    _json_safe_doc,
    _money,
    _now,
)


def _party_response_doc(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    result = _json_safe_doc(doc)
    # Party master data is not the accounting source of truth. Real receivable
    # and payable balances come from posted journal lines via party-ledger and
    # outstanding endpoints.
    result["opening_balance"] = "0.00"
    result["current_balance"] = "0.00"
    result["balance_source"] = "ledger_reports"
    return result


async def create_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    created_by: str,
    payload: PartyCreateRequest,
) -> dict:
    party_id = str(uuid4())
    now = _now()
    code = str(payload.party_code or f"P-{party_id[:8].upper()}").strip()
    opening_balance = _money(payload.opening_balance)
    doc = {
        "party_id": party_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_name": payload.party_name.strip(),
        "party_type": payload.party_type,
        "party_code": code,
        "gstin": payload.gstin,
        "pan": payload.pan,
        "email": payload.email,
        "phone": payload.phone,
        "billing_address": payload.billing_address,
        "city": payload.city,
        "state": payload.state,
        "pincode": payload.pincode,
        "legacy_opening_balance_input": opening_balance,
        "balance_source": "ledger_reports",
        "is_active": True,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    await get_collection(PARTIES_COLLECTION).insert_one(doc)
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="business_party_created",
        entity_type="business_party",
        entity_id=party_id,
        new_value=_party_response_doc(doc),
    )
    return _party_response_doc(doc)


async def list_parties(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_type: str | None = None,
    limit: int = 100,
) -> dict:
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "is_active": True,
    }
    if party_type:
        filters["party_type"] = party_type

    safe_limit = max(1, min(int(limit or 100), 500))
    rows = (
        await get_collection(PARTIES_COLLECTION)
        .find(filters)
        .sort("party_name", 1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    return {"items": [_party_response_doc(row) for row in rows], "total": len(rows)}


async def get_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
) -> dict | None:
    row = await get_collection(PARTIES_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "party_id": party_id,
        }
    )
    return _party_response_doc(row) if row else None


async def update_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    updated_by: str,
    payload: PartyUpdateRequest,
) -> dict | None:
    existing = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    if existing is None:
        return None

    patch = payload.model_dump(exclude_unset=True)
    if "party_name" in patch and patch["party_name"] is not None:
        patch["party_name"] = str(patch["party_name"]).strip()
    patch = {key: value for key, value in patch.items() if value is not None}
    patch["updated_by"] = updated_by
    patch["updated_at"] = _now()
    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_id": party_id,
    }
    parties = get_collection(PARTIES_COLLECTION)
    await parties.update_one(filters, {"$set": patch})
    updated = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_party_updated",
        entity_type="business_party",
        entity_id=party_id,
        old_value=existing,
        new_value=updated,
    )
    return updated


async def deactivate_party(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    deactivated_by: str,
) -> dict | None:
    existing = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    if existing is None:
        return None

    filters = {
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "party_id": party_id,
    }
    patch = {
        "is_active": False,
        "deactivated_by": deactivated_by,
        "deactivated_at": _now(),
        "updated_by": deactivated_by,
        "updated_at": _now(),
    }
    parties = get_collection(PARTIES_COLLECTION)
    await parties.update_one(filters, {"$set": patch})
    updated = await get_party(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
        party_id=party_id,
    )
    await _audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=deactivated_by,
        action="business_party_deactivated",
        entity_type="business_party",
        entity_id=party_id,
        old_value=existing,
        new_value=updated,
    )
    return updated
