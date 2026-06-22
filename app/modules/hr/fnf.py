"""Full & Final settlement (Step 6) — gratuity, leave encashment, notice recovery
on exit, with a draft -> approved -> paid status machine.

Tenure (and thus gratuity eligibility) is computed from the employee's joining
date and last working day, so HR cannot fat-finger years of service. GL posting
of the settlement is intentionally deferred (same pattern as the payroll run);
this slice establishes the computation and lifecycle.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.hr.payroll_engine import compute_fnf
from app.modules.hr.service import (
    HR_EMPLOYEES_COLLECTION,
    HrNotFoundError,
    HrValidationError,
    _now,
    get_employee,
)

HR_FNF_COLLECTION = "hr_fnf_settlements"


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


async def ensure_fnf_indexes() -> None:
    col = get_collection(HR_FNF_COLLECTION)
    await col.create_index([("tenant_id", 1), ("app_key", 1), ("fnf_id", 1)], unique=True)
    await col.create_index([("tenant_id", 1), ("app_key", 1), ("employee_id", 1)])


def _tenure(doj: date, last_working_day: date) -> tuple[Decimal, int, int]:
    """Returns (exact_years, completed_years, gratuity_years)."""
    days = (last_working_day - doj).days
    exact = Decimal(days) / Decimal("365.25")
    completed = int(exact)  # floor
    gratuity_years = int(exact.to_integral_value(rounding="ROUND_HALF_UP"))
    return exact, completed, gratuity_years


async def create_fnf(
    *, tenant_id, app_key, created_by, employee_id, last_working_day: date,
    last_drawn_basic: Decimal, unutilized_leaves: Decimal = Decimal("0"),
    unpaid_notice_days: Decimal = Decimal("0"), other_payouts: Decimal = Decimal("0"),
    other_recoveries: Decimal = Decimal("0"),
) -> dict:
    employee = await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)
    doj_raw = employee.get("date_of_joining")
    if not doj_raw:
        raise HrValidationError("Employee has no date_of_joining; cannot compute settlement")
    doj = date.fromisoformat(str(doj_raw))
    if last_working_day < doj:
        raise HrValidationError("last_working_day cannot be before date_of_joining")

    exact, completed, gratuity_years = _tenure(doj, last_working_day)
    years_for_gratuity = gratuity_years if completed >= 5 else 0

    settlement = compute_fnf(
        last_drawn_basic=Decimal(last_drawn_basic),
        years_of_service=years_for_gratuity,
        unutilized_leaves=Decimal(unutilized_leaves),
        unpaid_notice_days=Decimal(unpaid_notice_days),
        other_payouts=Decimal(other_payouts),
        other_recoveries=Decimal(other_recoveries),
    )

    fnf_id = str(uuid4())
    doc = {
        "fnf_id": fnf_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "employee_id": employee_id,
        "last_working_day": last_working_day.isoformat(),
        "date_of_joining": doj.isoformat(),
        "exact_years": str(exact.quantize(Decimal("0.01"))),
        "completed_years": completed,
        "last_drawn_basic": str(Decimal(last_drawn_basic)),
        "unutilized_leaves": str(Decimal(unutilized_leaves)),
        "unpaid_notice_days": str(Decimal(unpaid_notice_days)),
        "settlement": {k: str(v) if isinstance(v, Decimal) else v for k, v in settlement.items()},
        "status": "draft",
        "created_by": created_by,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await get_collection(HR_FNF_COLLECTION).insert_one(doc)
    await _audit(tenant_id=tenant_id, app_key=app_key, user_id=created_by,
                 action="hr_fnf_created", entity_id=fnf_id,
                 new_value={"employee_id": employee_id, "net": settlement["net_settlement"]})
    return _serialize(doc)


async def _get(*, tenant_id, app_key, fnf_id) -> dict:
    row = await get_collection(HR_FNF_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "fnf_id": fnf_id}
    )
    if row is None:
        raise HrNotFoundError("F&F settlement not found")
    return row


async def get_fnf(*, tenant_id, app_key, fnf_id) -> dict:
    return _serialize(await _get(tenant_id=tenant_id, app_key=app_key, fnf_id=fnf_id))


async def list_fnf(*, tenant_id, app_key, employee_id: str | None = None) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key}
    if employee_id:
        filters["employee_id"] = employee_id
    rows = await get_collection(HR_FNF_COLLECTION).find(filters).to_list(length=2000)
    return {"settlements": [_serialize(r) for r in rows], "total": len(rows)}


_TRANSITIONS = {"draft": "approved", "approved": "paid"}


async def transition_fnf(*, tenant_id, app_key, actor, fnf_id, target: str) -> dict:
    doc = await _get(tenant_id=tenant_id, app_key=app_key, fnf_id=fnf_id)
    current = doc["status"]
    if _TRANSITIONS.get(current) != target:
        raise HrValidationError(f"Cannot move F&F from {current} to {target}")

    update = {"status": target, "updated_at": _now()}
    await get_collection(HR_FNF_COLLECTION).update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "fnf_id": fnf_id}, {"$set": update}
    )
    # Settling the F&F exits the employee.
    if target == "paid":
        await get_collection(HR_EMPLOYEES_COLLECTION).update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "employee_id": doc["employee_id"]},
            {"$set": {"status": "exited", "updated_at": _now()}},
        )
    await _audit(tenant_id=tenant_id, app_key=app_key, user_id=actor,
                 action=f"hr_fnf_{target}", entity_id=fnf_id, new_value={"status": target})
    doc.update(update)
    return _serialize(doc)


async def _audit(*, tenant_id, app_key, user_id, action, entity_id, new_value=None) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id, user_id=user_id, product=app_key,
            action=action, entity_type="hr_fnf", entity_id=entity_id, new_value=new_value,
        )
    except Exception:
        pass
