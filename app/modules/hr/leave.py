"""Leave management (Step 4) — leave types, an immutable leave **ledger**, and
leave applications whose approval derives Loss-of-Pay.

Borrowed idea (our shape): instead of a mutable balance counter, every credit
(allocation) and debit (approved paid leave) is an immutable ledger row; the
balance is their sum. That makes balances auditable and reconstructable.

LOP is **derived, never typed**: when leave is approved, the engine splits it
into paid days (covered by ledger balance) and unpaid days (LWP leave types, or
paid leave that overflows the balance). ``resolve_lop_days`` then feeds the
payroll run (Step 3 seam).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.hr.service import HrNotFoundError, HrValidationError, _now, get_employee

HR_LEAVE_TYPES_COLLECTION = "hr_leave_types"
HR_LEAVE_LEDGER_COLLECTION = "hr_leave_ledger"
HR_LEAVE_APPLICATIONS_COLLECTION = "hr_leave_applications"


async def ensure_leave_indexes() -> None:
    types = get_collection(HR_LEAVE_TYPES_COLLECTION)
    await types.create_index([("tenant_id", 1), ("app_key", 1), ("leave_type_id", 1)], unique=True)
    await types.create_index([("tenant_id", 1), ("app_key", 1), ("code", 1)], unique=True)
    ledger = get_collection(HR_LEAVE_LEDGER_COLLECTION)
    await ledger.create_index([("tenant_id", 1), ("app_key", 1), ("employee_id", 1), ("leave_type_id", 1)])
    apps = get_collection(HR_LEAVE_APPLICATIONS_COLLECTION)
    await apps.create_index([("tenant_id", 1), ("app_key", 1), ("application_id", 1)], unique=True)
    await apps.create_index([("tenant_id", 1), ("app_key", 1), ("employee_id", 1), ("period", 1), ("status", 1)])


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


async def _audit(*, tenant_id, app_key, user_id, action, entity_id, new_value=None) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id, user_id=user_id, product=app_key,
            action=action, entity_type="hr_leave", entity_id=entity_id, new_value=new_value,
        )
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Leave types
# --------------------------------------------------------------------------- #

async def create_leave_type(
    *, tenant_id: str, app_key: str, created_by: str, code: str, name: str, is_lwp: bool = False
) -> dict:
    code = code.strip().upper()
    types = get_collection(HR_LEAVE_TYPES_COLLECTION)
    if await types.find_one({"tenant_id": tenant_id, "app_key": app_key, "code": code}):
        raise HrValidationError(f"Leave type {code} already exists")
    doc = {
        "leave_type_id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "code": code,
        "name": name,
        # An LWP (leave-without-pay) type never touches paid balance and is always LOP.
        "is_lwp": bool(is_lwp),
        "created_by": created_by,
        "created_at": _now(),
    }
    await types.insert_one(doc)
    return _serialize(doc)


async def list_leave_types(*, tenant_id: str, app_key: str) -> dict:
    rows = await get_collection(HR_LEAVE_TYPES_COLLECTION).find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=200)
    return {"leave_types": [_serialize(r) for r in rows], "total": len(rows)}


async def _get_leave_type(*, tenant_id: str, app_key: str, leave_type_id: str) -> dict:
    row = await get_collection(HR_LEAVE_TYPES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "leave_type_id": leave_type_id}
    )
    if row is None:
        raise HrNotFoundError("Leave type not found")
    return row


# --------------------------------------------------------------------------- #
# Leave ledger (immutable credit/debit rows)
# --------------------------------------------------------------------------- #

async def _post_ledger(
    *, tenant_id, app_key, employee_id, leave_type_id, delta: Decimal, reason: str, ref_id: str | None
) -> None:
    await get_collection(HR_LEAVE_LEDGER_COLLECTION).insert_one(
        {
            "ledger_id": str(uuid4()),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "employee_id": employee_id,
            "leave_type_id": leave_type_id,
            "delta": str(delta),
            "reason": reason,
            "ref_id": ref_id,
            "created_at": _now(),
        }
    )


async def get_leave_balance(*, tenant_id, app_key, employee_id, leave_type_id) -> Decimal:
    rows = await get_collection(HR_LEAVE_LEDGER_COLLECTION).find(
        {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id, "leave_type_id": leave_type_id}
    ).to_list(length=10000)
    return sum((Decimal(str(r["delta"])) for r in rows), Decimal("0"))


async def allocate_leave(
    *, tenant_id, app_key, allocated_by, employee_id, leave_type_id, days: Decimal
) -> dict:
    await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)
    leave_type = await _get_leave_type(tenant_id=tenant_id, app_key=app_key, leave_type_id=leave_type_id)
    if leave_type["is_lwp"]:
        raise HrValidationError("Cannot allocate balance to a leave-without-pay type")
    if Decimal(days) <= 0:
        raise HrValidationError("Allocation days must be positive")
    await _post_ledger(
        tenant_id=tenant_id, app_key=app_key, employee_id=employee_id,
        leave_type_id=leave_type_id, delta=Decimal(days), reason="allocation", ref_id=None,
    )
    await _audit(
        tenant_id=tenant_id, app_key=app_key, user_id=allocated_by,
        action="hr_leave_allocated", entity_id=employee_id,
        new_value={"leave_type_id": leave_type_id, "days": str(days)},
    )
    balance = await get_leave_balance(
        tenant_id=tenant_id, app_key=app_key, employee_id=employee_id, leave_type_id=leave_type_id
    )
    return {"employee_id": employee_id, "leave_type_id": leave_type_id, "balance": balance}


async def list_leave_balances(*, tenant_id, app_key, employee_id) -> dict:
    types = await get_collection(HR_LEAVE_TYPES_COLLECTION).find(
        {"tenant_id": tenant_id, "app_key": app_key}
    ).to_list(length=200)
    balances = []
    for lt in types:
        bal = await get_leave_balance(
            tenant_id=tenant_id, app_key=app_key, employee_id=employee_id, leave_type_id=lt["leave_type_id"]
        )
        balances.append({"leave_type_id": lt["leave_type_id"], "code": lt["code"], "balance": bal})
    return {"employee_id": employee_id, "balances": balances}


# --------------------------------------------------------------------------- #
# Leave applications — approval derives LOP
# --------------------------------------------------------------------------- #

def _inclusive_days(from_date: date, to_date: date) -> Decimal:
    return Decimal((to_date - from_date).days + 1)


async def apply_leave(
    *, tenant_id, app_key, applied_by, employee_id, leave_type_id, from_date: date, to_date: date
) -> dict:
    await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)
    await _get_leave_type(tenant_id=tenant_id, app_key=app_key, leave_type_id=leave_type_id)
    if to_date < from_date:
        raise HrValidationError("to_date cannot be before from_date")
    # v1 constraint: a leave application stays within one calendar month so LOP
    # attributes cleanly to a single payroll period. Span months -> split it.
    if (from_date.year, from_date.month) != (to_date.year, to_date.month):
        raise HrValidationError("Leave application must be within a single calendar month")

    application_id = str(uuid4())
    doc = {
        "application_id": application_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "employee_id": employee_id,
        "leave_type_id": leave_type_id,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "days": str(_inclusive_days(from_date, to_date)),
        "period": f"{from_date.year:04d}-{from_date.month:02d}",
        "status": "pending",
        "paid_days": "0",
        "lop_days": "0",
        "applied_by": applied_by,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).insert_one(doc)
    return _serialize(doc)


async def _get_application(*, tenant_id, app_key, application_id) -> dict:
    row = await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "application_id": application_id}
    )
    if row is None:
        raise HrNotFoundError("Leave application not found")
    return row


async def approve_leave(*, tenant_id, app_key, approved_by, application_id) -> dict:
    app_doc = await _get_application(tenant_id=tenant_id, app_key=app_key, application_id=application_id)
    if app_doc["status"] != "pending":
        raise HrValidationError(f"Leave application is already {app_doc['status']}")

    leave_type = await _get_leave_type(
        tenant_id=tenant_id, app_key=app_key, leave_type_id=app_doc["leave_type_id"]
    )
    days = Decimal(app_doc["days"])

    if leave_type["is_lwp"]:
        paid_days = Decimal("0")
        lop_days = days
    else:
        balance = await get_leave_balance(
            tenant_id=tenant_id, app_key=app_key,
            employee_id=app_doc["employee_id"], leave_type_id=app_doc["leave_type_id"],
        )
        available = max(Decimal("0"), balance)
        paid_days = min(days, available)
        lop_days = days - paid_days
        if paid_days > 0:
            # Debit the ledger for the covered days.
            await _post_ledger(
                tenant_id=tenant_id, app_key=app_key, employee_id=app_doc["employee_id"],
                leave_type_id=app_doc["leave_type_id"], delta=-paid_days,
                reason="leave_approved", ref_id=application_id,
            )

    update = {
        "status": "approved",
        "paid_days": str(paid_days),
        "lop_days": str(lop_days),
        "approved_by": approved_by,
        "updated_at": _now(),
    }
    await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "application_id": application_id},
        {"$set": update},
    )
    await _audit(
        tenant_id=tenant_id, app_key=app_key, user_id=approved_by,
        action="hr_leave_approved", entity_id=application_id,
        new_value={"paid_days": str(paid_days), "lop_days": str(lop_days)},
    )
    app_doc.update(update)
    return _serialize(app_doc)


async def reject_leave(*, tenant_id, app_key, rejected_by, application_id) -> dict:
    app_doc = await _get_application(tenant_id=tenant_id, app_key=app_key, application_id=application_id)
    if app_doc["status"] != "pending":
        raise HrValidationError(f"Leave application is already {app_doc['status']}")
    update = {"status": "rejected", "rejected_by": rejected_by, "updated_at": _now()}
    await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "application_id": application_id},
        {"$set": update},
    )
    app_doc.update(update)
    return _serialize(app_doc)


async def list_leave_applications(*, tenant_id, app_key, employee_id: str | None = None) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key}
    if employee_id:
        filters["employee_id"] = employee_id
    rows = await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).find(filters).to_list(length=2000)
    return {"applications": [_serialize(r) for r in rows], "total": len(rows)}


# --------------------------------------------------------------------------- #
# The payroll seam: LOP for a period, derived from approved leave.
# --------------------------------------------------------------------------- #

async def resolve_lop_days(*, tenant_id, app_key, employee_id, year: int, month: int) -> Decimal:
    """Sum unpaid days from approved leave applications in the payroll period."""
    period = f"{year:04d}-{month:02d}"
    rows = await get_collection(HR_LEAVE_APPLICATIONS_COLLECTION).find(
        {
            "tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id,
            "period": period, "status": "approved",
        }
    ).to_list(length=2000)
    return sum((Decimal(str(r.get("lop_days", "0"))) for r in rows), Decimal("0"))
