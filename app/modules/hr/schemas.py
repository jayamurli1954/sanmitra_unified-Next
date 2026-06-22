"""Pydantic models for the MitraBooks HR / Payroll add-on.

v1 foundation: the Employee profile. Statutory identifiers (PAN / UAN / IFSC)
carry strict Indian-format validation. Aadhaar is deliberately out of v1 —
storing it triggers UIDAI obligations and payroll needs only PAN + UAN.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TaxRegime = Literal["new", "old"]

EmployeeStatus = Literal["onboarding", "active", "exited"]
Gender = Literal["M", "F", "O"]

# Indian statutory identifier formats.
_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_UAN_RE = re.compile(r"^1[0-9]{11}$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class EmployeeBase(BaseModel):
    # Link to the core Sanmitra user. One HR profile per user per tenant.
    user_id: str = Field(..., min_length=1, max_length=120)
    full_name: str = Field(..., min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=200)
    designation: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)

    date_of_joining: date
    date_of_birth: date | None = None
    gender: Gender | None = None

    # --- Bank details for salary credit ---
    bank_name: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=30)
    ifsc_code: str | None = Field(default=None, max_length=11)

    # --- Statutory identity ---
    pan_number: str | None = Field(default=None, max_length=10)
    uan_number: str | None = Field(default=None, max_length=12)

    # --- Compliance flags ---
    is_pf_eligible: bool = True
    is_esic_eligible: bool = False
    state_for_professional_tax: str | None = Field(default=None, max_length=60)

    status: EmployeeStatus = "onboarding"

    @field_validator("pan_number")
    @classmethod
    def _validate_pan(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        value = value.strip().upper()
        if not _PAN_RE.match(value):
            raise ValueError("Invalid PAN. Must be 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F).")
        return value

    @field_validator("uan_number")
    @classmethod
    def _validate_uan(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        value = value.strip()
        if not _UAN_RE.match(value):
            raise ValueError("Invalid UAN. Must be a 12-digit number starting with 1.")
        return value

    @field_validator("ifsc_code")
    @classmethod
    def _validate_ifsc(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        value = value.strip().upper()
        if not _IFSC_RE.match(value):
            raise ValueError("Invalid IFSC code (e.g. HDFC0001234).")
        return value


class EmployeeCreateRequest(EmployeeBase):
    pass


class EmployeeUpdateRequest(BaseModel):
    """Partial update — every field optional; only provided keys are changed."""
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=200)
    designation: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    date_of_joining: date | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    bank_name: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=30)
    ifsc_code: str | None = Field(default=None, max_length=11)
    pan_number: str | None = Field(default=None, max_length=10)
    uan_number: str | None = Field(default=None, max_length=12)
    is_pf_eligible: bool | None = None
    is_esic_eligible: bool | None = None
    state_for_professional_tax: str | None = Field(default=None, max_length=60)
    status: EmployeeStatus | None = None

    # Reuse the strict statutory validators.
    _v_pan = field_validator("pan_number")(EmployeeBase._validate_pan.__func__)
    _v_uan = field_validator("uan_number")(EmployeeBase._validate_uan.__func__)
    _v_ifsc = field_validator("ifsc_code")(EmployeeBase._validate_ifsc.__func__)


class EmployeeResponse(EmployeeBase):
    employee_id: str
    tenant_id: str
    app_key: str
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeResponse]
    total: int


# --------------------------------------------------------------------------- #
# Salary structure (configurable, formula-driven earnings)
# --------------------------------------------------------------------------- #

_ABBR_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class SalaryComponentModel(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    abbr: str = Field(..., min_length=1, max_length=20)  # formula identifier
    formula: str = Field(..., min_length=1, max_length=200)
    statutory_kind: str | None = Field(default=None, max_length=20)
    depends_on_payment_days: bool = True

    @field_validator("abbr")
    @classmethod
    def _validate_abbr(cls, value: str) -> str:
        value = value.strip().upper()
        if not _ABBR_RE.match(value):
            raise ValueError("abbr must be UPPER_SNAKE (letters/digits/underscore, start with a letter)")
        return value


class SalaryStructureCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    components: list[SalaryComponentModel] = Field(..., min_length=1)

    @field_validator("components")
    @classmethod
    def _require_basic(cls, components: list[SalaryComponentModel]) -> list[SalaryComponentModel]:
        kinds = {c.statutory_kind for c in components}
        abbrs = {c.abbr for c in components}
        if "basic" not in kinds and "BASIC" not in abbrs:
            raise ValueError("structure must include a Basic component (statutory_kind='basic' or abbr 'BASIC')")
        if len(abbrs) != len(components):
            raise ValueError("component abbrs must be unique")
        return components


class SalaryStructureResponse(SalaryStructureCreateRequest):
    structure_id: str
    tenant_id: str
    app_key: str
    created_by: str | None = None
    created_at: datetime | None = None


class SalaryStructureListResponse(BaseModel):
    structures: list[SalaryStructureResponse]
    total: int


# --------------------------------------------------------------------------- #
# Salary assignment (one active per employee)
# --------------------------------------------------------------------------- #

class SalaryAssignmentRequest(BaseModel):
    structure_id: str = Field(..., min_length=1)
    monthly_gross: Decimal = Field(..., gt=Decimal("0"))
    regime: TaxRegime = "new"
    chapter_via_deductions: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class SalaryAssignmentResponse(SalaryAssignmentRequest):
    employee_id: str
    tenant_id: str
    app_key: str
    updated_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Payroll run + salary slips
# --------------------------------------------------------------------------- #

class PayrollRunRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    # Optional override of working/calendar days; defaults to calendar days of month.
    total_days: int | None = Field(default=None, ge=1, le=31)


class SalarySlipResponse(BaseModel):
    slip_id: str
    run_id: str
    employee_id: str
    period: str               # "YYYY-MM"
    payment_days: Decimal
    total_days: Decimal
    lop_days: Decimal
    earnings: dict[str, Decimal]
    earned_gross: Decimal
    deductions: dict[str, Decimal]
    employer_contributions: dict[str, Decimal]
    net_pay: Decimal


class PayrollRunResponse(BaseModel):
    run_id: str
    period: str
    status: str
    employee_count: int
    totals: dict[str, Decimal]
    journal_entry_id: int | None = None
    slips: list[SalarySlipResponse] = Field(default_factory=list)


class PayrollRunListResponse(BaseModel):
    runs: list[PayrollRunResponse]
    total: int


# --------------------------------------------------------------------------- #
# Leave (Step 4)
# --------------------------------------------------------------------------- #

class LeaveTypeCreateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=80)
    is_lwp: bool = False  # leave-without-pay: never paid, always LOP


class LeaveTypeResponse(BaseModel):
    leave_type_id: str
    code: str
    name: str
    is_lwp: bool


class LeaveTypeListResponse(BaseModel):
    leave_types: list[LeaveTypeResponse]
    total: int


class LeaveAllocationRequest(BaseModel):
    leave_type_id: str = Field(..., min_length=1)
    days: Decimal = Field(..., gt=Decimal("0"))


class LeaveBalanceRow(BaseModel):
    leave_type_id: str
    code: str
    balance: Decimal


class LeaveBalancesResponse(BaseModel):
    employee_id: str
    balances: list[LeaveBalanceRow]


class LeaveApplicationRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    leave_type_id: str = Field(..., min_length=1)
    from_date: date
    to_date: date


class LeaveApplicationResponse(BaseModel):
    application_id: str
    employee_id: str
    leave_type_id: str
    from_date: str
    to_date: str
    days: Decimal
    period: str
    status: str
    paid_days: Decimal
    lop_days: Decimal


class LeaveApplicationListResponse(BaseModel):
    applications: list[LeaveApplicationResponse]
    total: int


# --------------------------------------------------------------------------- #
# Form 12BB tax declarations (Step 5)
# --------------------------------------------------------------------------- #

class TaxDeclarationCreateRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    financial_year: str = Field(..., min_length=4, max_length=9)  # e.g. "2025-26"
    section_code: str = Field(..., min_length=2, max_length=20)   # e.g. "80C"
    investment_name: str = Field(..., min_length=1, max_length=120)
    declared_amount: Decimal = Field(..., ge=Decimal("0"))


class TaxDeclarationResponse(BaseModel):
    declaration_id: str
    employee_id: str
    financial_year: str
    section_code: str
    investment_name: str
    declared_amount: Decimal
    verified_amount: Decimal
    status: str
    rejection_reason: str | None = None


class TaxDeclarationListResponse(BaseModel):
    declarations: list[TaxDeclarationResponse]
    total: int


class TaxVerifyRequest(BaseModel):
    verified_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    approve: bool = True
    rejection_reason: str | None = Field(default=None, max_length=300)


class EffectiveDeductionsResponse(BaseModel):
    employee_id: str
    financial_year: str
    breakdown: dict[str, Decimal]
    total_deductions: Decimal
    has_declarations: bool


class TaxProofResponse(BaseModel):
    proof_id: str
    declaration_id: str
    file_name: str
    content_type: str
    size_bytes: int


# --------------------------------------------------------------------------- #
# Full & Final settlement (Step 6)
# --------------------------------------------------------------------------- #

class FnfCreateRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    last_working_day: date
    last_drawn_basic: Decimal = Field(..., gt=Decimal("0"))
    unutilized_leaves: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    unpaid_notice_days: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    other_payouts: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    other_recoveries: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class FnfResponse(BaseModel):
    fnf_id: str
    employee_id: str
    last_working_day: str
    date_of_joining: str
    exact_years: str
    completed_years: int
    last_drawn_basic: str
    unutilized_leaves: str
    unpaid_notice_days: str
    settlement: dict
    status: str


class FnfListResponse(BaseModel):
    settlements: list[FnfResponse]
    total: int
