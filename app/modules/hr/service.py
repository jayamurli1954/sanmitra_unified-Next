"""Service layer for the HR add-on. v1 foundation: Employee profile CRUD.

All data is tenant-scoped (tenant_id + app_key) and every mutation is written to
the shared core audit log — HR carries sensitive PII, so reads/writes of it must
be traceable. We reuse app/core/audit rather than building a new audit system.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.hr.schemas import (
    EmployeeCreateRequest,
    EmployeeUpdateRequest,
    SalaryAssignmentRequest,
    SalaryStructureCreateRequest,
)

HR_EMPLOYEES_COLLECTION = "hr_employees"
HR_STRUCTURES_COLLECTION = "hr_salary_structures"
HR_ASSIGNMENTS_COLLECTION = "hr_salary_assignments"
HR_SLIPS_COLLECTION = "hr_salary_slips"
HR_RUNS_COLLECTION = "hr_payroll_runs"


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_hr_indexes() -> None:
    employees = get_collection(HR_EMPLOYEES_COLLECTION)
    await employees.create_index(
        [("tenant_id", 1), ("app_key", 1), ("employee_id", 1)], unique=True
    )
    # One HR profile per core user per tenant.
    await employees.create_index(
        [("tenant_id", 1), ("app_key", 1), ("user_id", 1)], unique=True
    )
    structures = get_collection(HR_STRUCTURES_COLLECTION)
    await structures.create_index(
        [("tenant_id", 1), ("app_key", 1), ("structure_id", 1)], unique=True
    )
    assignments = get_collection(HR_ASSIGNMENTS_COLLECTION)
    await assignments.create_index(
        [("tenant_id", 1), ("app_key", 1), ("employee_id", 1)], unique=True
    )
    slips = get_collection(HR_SLIPS_COLLECTION)
    await slips.create_index(
        [("tenant_id", 1), ("app_key", 1), ("slip_id", 1)], unique=True
    )
    await slips.create_index([("tenant_id", 1), ("app_key", 1), ("run_id", 1)])
    runs = get_collection(HR_RUNS_COLLECTION)
    await runs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("run_id", 1)], unique=True
    )
    # One payroll run per period per book.
    await runs.create_index(
        [("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("period", 1)],
        unique=True,
    )


def _serialize(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


async def _audit(
    *,
    tenant_id: str,
    app_key: str,
    user_id: str,
    action: str,
    entity_id: str,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id,
            user_id=user_id,
            product=app_key,
            action=action,
            entity_type="hr_employee",
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
        )
    except Exception:
        # Best-effort: the domain write has already happened.
        pass


class HrConflictError(Exception):
    """Raised when an employee already exists for the given user."""


class HrNotFoundError(Exception):
    """Raised when an employee is not found in the tenant scope."""


class HrValidationError(Exception):
    """Raised on an invalid HR operation (e.g. payroll run with nothing to pay)."""


async def create_employee(
    *,
    tenant_id: str,
    app_key: str,
    created_by: str,
    payload: EmployeeCreateRequest,
) -> dict:
    employees = get_collection(HR_EMPLOYEES_COLLECTION)

    existing = await employees.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "user_id": payload.user_id}
    )
    if existing is not None:
        raise HrConflictError("An employee profile already exists for this user")

    employee_id = str(uuid4())
    doc = payload.model_dump(mode="json")  # dates -> ISO strings (BSON-safe)
    doc.update(
        {
            "employee_id": employee_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "created_by": created_by,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    await employees.insert_one(doc)

    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=created_by,
        action="hr_employee_created",
        entity_id=employee_id,
        new_value=_redact(doc),
    )
    return _serialize(doc)


async def list_employees(
    *,
    tenant_id: str,
    app_key: str,
    status: str | None = None,
    limit: int = 100,
) -> dict:
    filters: dict = {"tenant_id": tenant_id, "app_key": app_key}
    if status:
        filters["status"] = status
    safe_limit = max(1, min(int(limit or 100), 500))
    employees = get_collection(HR_EMPLOYEES_COLLECTION)
    rows = (
        await employees.find(filters)
        .sort("created_at", -1)
        .limit(safe_limit)
        .to_list(length=safe_limit)
    )
    total = await employees.count_documents(filters)
    return {"employees": [_serialize(r) for r in rows], "total": total}


async def get_employee(*, tenant_id: str, app_key: str, employee_id: str) -> dict:
    row = await get_collection(HR_EMPLOYEES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id}
    )
    if row is None:
        raise HrNotFoundError("Employee not found")
    return _serialize(row)


async def update_employee(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    employee_id: str,
    payload: EmployeeUpdateRequest,
) -> dict:
    employees = get_collection(HR_EMPLOYEES_COLLECTION)
    existing = await employees.find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id}
    )
    if existing is None:
        raise HrNotFoundError("Employee not found")

    changes = payload.model_dump(mode="json", exclude_unset=True)
    if changes:
        changes["updated_at"] = _now()
        await employees.update_one(
            {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id},
            {"$set": changes},
        )

    await _audit(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="hr_employee_updated",
        entity_id=employee_id,
        old_value=_redact(existing),
        new_value=_redact(changes),
    )
    return await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)


# --------------------------------------------------------------------------- #
# Salary structure CRUD
# --------------------------------------------------------------------------- #

async def create_salary_structure(
    *, tenant_id: str, app_key: str, created_by: str, payload: SalaryStructureCreateRequest
) -> dict:
    structure_id = str(uuid4())
    doc = payload.model_dump(mode="json")
    doc.update(
        {
            "structure_id": structure_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "created_by": created_by,
            "created_at": _now(),
        }
    )
    await get_collection(HR_STRUCTURES_COLLECTION).insert_one(doc)
    await _audit(
        tenant_id=tenant_id, app_key=app_key, user_id=created_by,
        action="hr_salary_structure_created", entity_id=structure_id, new_value={"name": payload.name},
    )
    return _serialize(doc)


async def list_salary_structures(*, tenant_id: str, app_key: str) -> dict:
    col = get_collection(HR_STRUCTURES_COLLECTION)
    filters = {"tenant_id": tenant_id, "app_key": app_key}
    rows = await col.find(filters).sort("created_at", -1).limit(500).to_list(length=500)
    total = await col.count_documents(filters)
    return {"structures": [_serialize(r) for r in rows], "total": total}


async def get_salary_structure(*, tenant_id: str, app_key: str, structure_id: str) -> dict:
    row = await get_collection(HR_STRUCTURES_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "structure_id": structure_id}
    )
    if row is None:
        raise HrNotFoundError("Salary structure not found")
    return _serialize(row)


# --------------------------------------------------------------------------- #
# Salary assignment (one active per employee)
# --------------------------------------------------------------------------- #

async def upsert_salary_assignment(
    *, tenant_id: str, app_key: str, updated_by: str, employee_id: str, payload: SalaryAssignmentRequest
) -> dict:
    # Both employee and structure must exist in scope.
    await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)
    await get_salary_structure(tenant_id=tenant_id, app_key=app_key, structure_id=payload.structure_id)

    doc = payload.model_dump(mode="json")
    doc.update({"employee_id": employee_id, "tenant_id": tenant_id, "app_key": app_key, "updated_at": _now()})
    filters = {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id}
    await get_collection(HR_ASSIGNMENTS_COLLECTION).update_one(
        filters, {"$set": doc, "$setOnInsert": {"created_at": _now()}}, upsert=True
    )
    await _audit(
        tenant_id=tenant_id, app_key=app_key, user_id=updated_by,
        action="hr_salary_assignment_updated", entity_id=employee_id,
        new_value={"structure_id": payload.structure_id, "monthly_gross": str(payload.monthly_gross), "regime": payload.regime},
    )
    return await get_salary_assignment(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)


async def get_salary_assignment(*, tenant_id: str, app_key: str, employee_id: str) -> dict:
    row = await get_collection(HR_ASSIGNMENTS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id}
    )
    if row is None:
        raise HrNotFoundError("Salary assignment not found")
    return _serialize(row)


# Fields too sensitive to copy verbatim into the audit trail.
_SENSITIVE_FIELDS = {"account_number", "pan_number", "uan_number"}


def _redact(doc: dict | None) -> dict | None:
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k != "_id"}
    for field in _SENSITIVE_FIELDS:
        if field in out and out[field]:
            out[field] = "******"
    return out
