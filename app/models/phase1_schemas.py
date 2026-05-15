"""
Phase 1: Foundation - Pydantic Schemas

Request/Response models for FastAPI validation and documentation.

These are stubs for Phase 1. They'll be extended as each domain is implemented.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================================
# Base Models (used by multiple domains)
# ============================================================================


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=50, ge=1, le=200, description="Number of records to return")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    total: int = Field(description="Total count of records")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Number of records returned")
    items: List = Field(description="List of items")


class AuditLog(BaseModel):
    """Audit log entry (for request context)."""

    entity_type: str = Field(description="Type of entity (donation, journal_entry, etc.)")
    entity_id: str = Field(description="ID of entity being audited")
    action: str = Field(description="Action performed (created, updated, deleted)")
    user_id: Optional[str] = Field(default=None, description="User who performed action")
    tenant_id: str = Field(description="Tenant ID")
    before_state: Optional[dict] = Field(default=None, description="State before action")
    after_state: Optional[dict] = Field(default=None, description="State after action")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When action occurred")


# ============================================================================
# Authentication Schemas
# ============================================================================


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(description="User email")
    password: str = Field(min_length=6, description="User password")


class LoginResponse(BaseModel):
    """Login response with token."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str = Field(description="User ID (subject)")
    tenant_id: str = Field(description="Tenant ID")
    app_key: str = Field(description="App key (mandirmitra, gruhamitra, etc.)")
    exp: datetime = Field(description="Expiration time")


# ============================================================================
# Donation Schemas (Placeholder - will be extended in Phase 3)
# ============================================================================


class PaymentMode(str, Enum):
    """Payment modes for donations."""

    CASH = "cash"
    BANK = "bank"
    UPI = "upi"
    CHEQUE = "cheque"
    CARD = "card"


class DonationCreate(BaseModel):
    """Create donation request."""

    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Donation amount")
    category: str = Field(..., min_length=1, max_length=100, description="Donation category")
    donor_name: Optional[str] = Field(None, max_length=255, description="Donor name")
    donor_phone: Optional[str] = Field(None, description="Donor phone number")
    payment_mode: PaymentMode = Field(default=PaymentMode.CASH, description="Payment method")
    temple_id: Optional[str] = Field(None, description="Temple ID (if applicable)")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for duplicate prevention")
    notes: Optional[str] = Field(None, description="Additional notes")

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class DonationResponse(DonationCreate):
    """Donation response."""

    donation_id: str = Field(description="Unique donation ID")
    receipt_number: Optional[str] = Field(None, description="Receipt number")
    created_at: datetime = Field(description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="User who created donation")
    tenant_id: str = Field(description="Tenant ID")


# ============================================================================
# Accounting Schemas (Placeholder - will be extended in Phase 2)
# ============================================================================


class AccountType(str, Enum):
    """Account types in Chart of Accounts."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class AccountCreate(BaseModel):
    """Create account request."""

    account_number: str = Field(..., max_length=50, description="Account number (must be unique per tenant)")
    account_name: str = Field(..., max_length=255, description="Account name")
    account_type: AccountType = Field(..., description="Account type")
    account_category: Optional[str] = Field(None, max_length=100, description="Account category/grouping")
    description: Optional[str] = Field(None, description="Account description")


class AccountUpdate(BaseModel):
    """Update account request."""

    account_name: Optional[str] = Field(None, max_length=255, description="Updated account name")
    account_category: Optional[str] = Field(None, max_length=100, description="Updated category")
    description: Optional[str] = Field(None, description="Updated description")
    is_active: Optional[bool] = Field(None, description="Active/inactive status")


class AccountResponse(AccountCreate):
    """Account response."""

    id: int = Field(description="Account ID")
    tenant_id: str = Field(description="Tenant ID")
    is_active: bool = Field(description="Is account active")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class JournalLineRequest(BaseModel):
    """Single line in journal entry (debit or credit)."""

    account_id: int = Field(description="Account ID")
    debit: Decimal = Field(default=0, ge=0, decimal_places=2, description="Debit amount")
    credit: Decimal = Field(default=0, ge=0, decimal_places=2, description="Credit amount")
    description: Optional[str] = Field(None, max_length=500, description="Line description")

    @validator("debit", "credit")
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError("Amounts must be non-negative")
        return v


class JournalEntryCreate(BaseModel):
    """Create journal entry request."""

    entry_date: datetime = Field(description="Entry date")
    description: str = Field(..., max_length=500, description="Entry description")
    reference: Optional[str] = Field(None, max_length=100, description="External reference (donation:123)")
    lines: List[JournalLineRequest] = Field(..., min_items=2, description="Debit and credit lines")

    @validator("lines")
    def validate_lines(cls, v):
        # Ensure debits == credits
        total_debit = sum(line.debit for line in v)
        total_credit = sum(line.credit for line in v)

        if total_debit != total_credit:
            raise ValueError(f"Debits ({total_debit}) must equal credits ({total_credit})")

        return v


class JournalEntryResponse(BaseModel):
    """Journal entry response."""

    entry_id: str = Field(description="Unique entry ID")
    entry_date: datetime = Field(description="Entry date")
    description: str = Field(description="Entry description")
    reference: Optional[str] = Field(None, description="External reference")
    status: str = Field(description="Entry status (draft, posted, cancelled)")
    total_amount: Decimal = Field(description="Total debit/credit amount")
    created_at: datetime = Field(description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="User who created entry")
    tenant_id: str = Field(description="Tenant ID")


# ============================================================================
# Error Response Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    status_code: int = Field(description="HTTP status code")
    detail: str = Field(description="Error message")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# ============================================================================
# Health Check Schemas
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Application status")
    environment: str = Field(description="Environment (development, staging, production)")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
