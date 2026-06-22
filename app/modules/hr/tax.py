"""Form 12BB — investment declarations, proof upload, HR verification, and the
effective Chapter VI-A deduction that feeds old-regime TDS (Step 5).

Lifecycle (the standard Indian payroll cycle):
  DECLARED (April)  ->  SUBMITTED (proof uploaded, Jan)  ->  APPROVED / REJECTED (HR, Feb–Mar)

Only APPROVED verified amounts, each capped at its statutory section limit, count
toward the deduction total. Proof files are stored as bytes in Mongo (the platform
file pattern), never on ephemeral disk.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.core.audit.service import log_audit_event
from app.db.mongo import get_collection
from app.modules.hr.service import HrNotFoundError, HrValidationError, _now, get_employee

HR_TAX_DECLARATIONS_COLLECTION = "hr_tax_declarations"
HR_TAX_PROOFS_COLLECTION = "hr_tax_proofs"

# Statutory section caps (None = uncapped). Data, so a Budget change is an edit.
SECTION_LIMITS: dict[str, Decimal | None] = {
    "80C": Decimal("150000"),
    "80CCD1B": Decimal("50000"),     # additional NPS
    "80D": Decimal("25000"),         # health insurance — self/family
    "80D_PARENTS": Decimal("50000"),  # health insurance — senior parents
    "80E": None,                      # education loan interest — uncapped
    "80G": None,                      # donations — varies, validated outside v1
    "24B": Decimal("200000"),         # home-loan interest (self-occupied)
}

DeclarationStatus = ("declared", "submitted", "approved", "rejected")

# Proof upload guardrails.
MAX_PROOF_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PROOF_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def _serialize(doc: dict) -> dict:
    # Never leak raw proof bytes through the declaration serializer.
    return {k: v for k, v in doc.items() if k not in ("_id", "payload")}


async def _audit(*, tenant_id, app_key, user_id, action, entity_id, new_value=None) -> None:
    try:
        await log_audit_event(
            tenant_id=tenant_id, user_id=user_id, product=app_key,
            action=action, entity_type="hr_tax_declaration", entity_id=entity_id, new_value=new_value,
        )
    except Exception:
        pass


async def ensure_tax_indexes() -> None:
    decls = get_collection(HR_TAX_DECLARATIONS_COLLECTION)
    await decls.create_index([("tenant_id", 1), ("app_key", 1), ("declaration_id", 1)], unique=True)
    await decls.create_index([("tenant_id", 1), ("app_key", 1), ("employee_id", 1), ("financial_year", 1)])
    proofs = get_collection(HR_TAX_PROOFS_COLLECTION)
    await proofs.create_index([("tenant_id", 1), ("app_key", 1), ("proof_id", 1)], unique=True)
    await proofs.create_index([("tenant_id", 1), ("app_key", 1), ("declaration_id", 1)])


# --------------------------------------------------------------------------- #
# Declarations
# --------------------------------------------------------------------------- #

async def create_declaration(
    *, tenant_id, app_key, created_by, employee_id, financial_year, section_code,
    investment_name, declared_amount: Decimal,
) -> dict:
    await get_employee(tenant_id=tenant_id, app_key=app_key, employee_id=employee_id)
    section_code = section_code.strip().upper()
    if section_code not in SECTION_LIMITS:
        raise HrValidationError(f"Unknown tax section: {section_code}")
    if Decimal(declared_amount) < 0:
        raise HrValidationError("declared_amount cannot be negative")

    declaration_id = str(uuid4())
    doc = {
        "declaration_id": declaration_id,
        "tenant_id": tenant_id,
        "app_key": app_key,
        "employee_id": employee_id,
        "financial_year": financial_year,
        "section_code": section_code,
        "investment_name": investment_name,
        "declared_amount": str(Decimal(declared_amount)),
        "verified_amount": "0",
        "status": "declared",
        "created_by": created_by,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await get_collection(HR_TAX_DECLARATIONS_COLLECTION).insert_one(doc)
    await _audit(tenant_id=tenant_id, app_key=app_key, user_id=created_by,
                 action="hr_tax_declared", entity_id=declaration_id,
                 new_value={"section": section_code, "declared": str(declared_amount)})
    return _serialize(doc)


async def list_declarations(*, tenant_id, app_key, employee_id: str | None = None, financial_year: str | None = None) -> dict:
    filters = {"tenant_id": tenant_id, "app_key": app_key}
    if employee_id:
        filters["employee_id"] = employee_id
    if financial_year:
        filters["financial_year"] = financial_year
    rows = await get_collection(HR_TAX_DECLARATIONS_COLLECTION).find(filters).to_list(length=2000)
    return {"declarations": [_serialize(r) for r in rows], "total": len(rows)}


async def _get_declaration(*, tenant_id, app_key, declaration_id) -> dict:
    row = await get_collection(HR_TAX_DECLARATIONS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "declaration_id": declaration_id}
    )
    if row is None:
        raise HrNotFoundError("Tax declaration not found")
    return row


async def verify_declaration(
    *, tenant_id, app_key, verified_by, declaration_id, verified_amount: Decimal, approve: bool,
    rejection_reason: str | None = None,
) -> dict:
    decl = await _get_declaration(tenant_id=tenant_id, app_key=app_key, declaration_id=declaration_id)
    if Decimal(verified_amount) < 0:
        raise HrValidationError("verified_amount cannot be negative")
    update = {
        "verified_amount": str(Decimal(verified_amount) if approve else Decimal("0")),
        "status": "approved" if approve else "rejected",
        "rejection_reason": None if approve else (rejection_reason or "Not substantiated"),
        "verified_by": verified_by,
        "updated_at": _now(),
    }
    await get_collection(HR_TAX_DECLARATIONS_COLLECTION).update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "declaration_id": declaration_id},
        {"$set": update},
    )
    await _audit(tenant_id=tenant_id, app_key=app_key, user_id=verified_by,
                 action="hr_tax_verified", entity_id=declaration_id,
                 new_value={"status": update["status"], "verified": update["verified_amount"]})
    decl.update(update)
    return _serialize(decl)


# --------------------------------------------------------------------------- #
# Proof upload (bytes in Mongo)
# --------------------------------------------------------------------------- #

async def add_proof(
    *, tenant_id, app_key, uploaded_by, declaration_id, file_name, content_type, payload: bytes,
) -> dict:
    await _get_declaration(tenant_id=tenant_id, app_key=app_key, declaration_id=declaration_id)
    if content_type not in ALLOWED_PROOF_TYPES:
        raise HrValidationError(f"Unsupported proof type: {content_type}")
    if not payload:
        raise HrValidationError("Proof file is empty")
    if len(payload) > MAX_PROOF_BYTES:
        raise HrValidationError("Proof file exceeds the 10 MB limit")

    proof_id = str(uuid4())
    await get_collection(HR_TAX_PROOFS_COLLECTION).insert_one(
        {
            "proof_id": proof_id,
            "tenant_id": tenant_id,
            "app_key": app_key,
            "declaration_id": declaration_id,
            "file_name": file_name,
            "content_type": content_type,
            "size_bytes": len(payload),
            "payload": payload,  # BSON binary
            "uploaded_by": uploaded_by,
            "uploaded_at": _now(),
        }
    )
    # Move the declaration to "submitted" once a proof exists.
    await get_collection(HR_TAX_DECLARATIONS_COLLECTION).update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "declaration_id": declaration_id, "status": "declared"},
        {"$set": {"status": "submitted", "updated_at": _now()}},
    )
    return {
        "proof_id": proof_id, "declaration_id": declaration_id,
        "file_name": file_name, "content_type": content_type, "size_bytes": len(payload),
    }


async def get_proof(*, tenant_id, app_key, proof_id) -> dict:
    row = await get_collection(HR_TAX_PROOFS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "proof_id": proof_id}
    )
    if row is None:
        raise HrNotFoundError("Proof not found")
    return row  # includes payload bytes — caller streams it


# --------------------------------------------------------------------------- #
# Effective deductions -> old-regime TDS
# --------------------------------------------------------------------------- #

def cap_for_section(section_code: str) -> Decimal | None:
    return SECTION_LIMITS.get(section_code.strip().upper())


async def compute_effective_deductions(*, tenant_id, app_key, employee_id, financial_year) -> dict:
    """Sum APPROVED verified amounts per section, each capped at its statutory
    limit. Returns the per-section breakdown and the total Chapter VI-A deduction."""
    rows = await get_collection(HR_TAX_DECLARATIONS_COLLECTION).find(
        {
            "tenant_id": tenant_id, "app_key": app_key, "employee_id": employee_id,
            "financial_year": financial_year, "status": "approved",
        }
    ).to_list(length=2000)

    by_section: dict[str, Decimal] = {}
    for r in rows:
        section = r["section_code"]
        by_section[section] = by_section.get(section, Decimal("0")) + Decimal(str(r.get("verified_amount", "0")))

    breakdown: dict[str, Decimal] = {}
    total = Decimal("0")
    for section, amount in by_section.items():
        cap = cap_for_section(section)
        allowed = amount if cap is None else min(amount, cap)
        breakdown[section] = allowed
        total += allowed

    return {
        "employee_id": employee_id,
        "financial_year": financial_year,
        "breakdown": breakdown,
        "total_deductions": total,
        "has_declarations": bool(rows),
    }
