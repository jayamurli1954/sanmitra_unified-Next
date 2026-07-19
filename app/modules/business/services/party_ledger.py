"""Business party sub-ledger reads (party-wise Debtors / Creditors).

Extracted verbatim from app/modules/business/service.py (party sub-ledger
section) per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move:
logic unchanged; service.py re-exports these names for backward compatibility.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import (
    AccountingNotFoundError,
    get_party_outstanding,
    get_party_wise_balances,
)
from app.db.mongo import get_collection


async def party_wise_ledger(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    kind: str,
    as_of: date | None = None,
) -> dict:
    """Party-wise Sundry Debtors (receivable) / Creditors (payable), enriched with
    party names from Mongo. Ties to the matching Trial Balance account total."""
    from app.modules.business.service import PARTIES_COLLECTION
    as_of = as_of or date.today()
    lines, total = await get_party_wise_balances(
        session, tenant_id=tenant_id, as_of=as_of, kind=kind, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    party_ids = [l["party_id"] for l in lines if l["party_id"]]
    names: dict[str, str | None] = {}
    if party_ids:
        rows = await (
            get_collection(PARTIES_COLLECTION)
            .find({
                "tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id,
                "party_id": {"$in": party_ids},
            })
            .to_list(length=len(party_ids))
        )
        names = {r["party_id"]: r.get("party_name") for r in rows}

    items = []
    for l in lines:
        pid = l["party_id"]
        items.append({
            "party_id": pid,
            "party_name": (names.get(pid) or pid) if pid else "Unallocated (direct entries)",
            "balance": str(l["balance"]),
        })
    # Named parties first (largest balance on top); the Unallocated bucket last.
    items.sort(key=lambda x: (x["party_id"] is None, -Decimal(x["balance"])))
    return {
        "as_of": as_of.isoformat(),
        "kind": kind,
        "accounting_entity_id": accounting_entity_id,
        "items": items,
        "total_balance": str(total),
        "count": len(items),
    }


async def party_outstanding_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
    party_id: str,
    as_of: date | None = None,
) -> dict:
    """Net receivable and payable outstanding for one party (for the voucher form)."""
    from app.modules.business.service import get_party
    as_of = as_of or date.today()
    party = await get_party(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id, party_id=party_id,
    )
    if party is None:
        raise AccountingNotFoundError("Party not found")
    balances = await get_party_outstanding(
        session, tenant_id=tenant_id, party_id=party_id, as_of=as_of, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    return {
        "party_id": party_id,
        "party_name": party.get("party_name"),
        "party_type": party.get("party_type"),
        "as_of": as_of.isoformat(),
        "receivable": str(balances["receivable"]),
        "payable": str(balances["payable"]),
    }
