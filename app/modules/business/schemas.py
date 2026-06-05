from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PartyType = Literal["customer", "vendor", "both"]
VoucherType = Literal["payment", "receipt", "contra", "journal"]


class PartyCreateRequest(BaseModel):
    party_name: str = Field(..., min_length=1, max_length=160)
    party_type: PartyType = "customer"
    party_code: str | None = Field(default=None, max_length=40)
    gstin: str | None = Field(default=None, max_length=15)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=500)
    opening_balance: Decimal = Decimal("0")


class PartyUpdateRequest(BaseModel):
    party_name: str | None = Field(default=None, min_length=1, max_length=160)
    party_type: PartyType | None = None
    gstin: str | None = Field(default=None, max_length=15)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=500)


class PartyResponse(BaseModel):
    party_id: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    party_name: str
    party_type: str
    party_code: str
    gstin: str | None = None
    email: str | None = None
    phone: str | None = None
    billing_address: str | None = None
    opening_balance: Decimal
    current_balance: Decimal
    is_active: bool
    created_by: str
    updated_by: str | None = None
    deactivated_by: str | None = None
    deactivated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PartyListResponse(BaseModel):
    items: list[PartyResponse]
    total: int


class TypedVoucherCreateRequest(BaseModel):
    voucher_type: VoucherType
    entry_date: date
    amount: Decimal = Field(..., gt=Decimal("0"))
    debit_account_id: int | None = None
    credit_account_id: int | None = None
    debit_account_code: str | None = Field(default=None, min_length=1, max_length=50)
    credit_account_code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str = Field(..., min_length=1, max_length=300)
    reference: str | None = Field(default=None, max_length=120)
    party_id: str | None = Field(default=None, max_length=80)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class TypedVoucherReversalRequest(BaseModel):
    reversal_date: date | None = None
    reason: str = Field(default="Correction", min_length=1, max_length=240)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class TypedVoucherResponse(BaseModel):
    voucher_id: str
    voucher_number: str
    voucher_type: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    party_id: str | None = None
    amount: Decimal
    entry_date: date
    debit_account_id: int
    credit_account_id: int
    description: str
    reference: str
    journal_entry_id: int
    reversal_journal_entry_id: int | None = None
    reversal_reason: str | None = None
    reversed_at: datetime | None = None
    status: str
    created: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class TypedVoucherListResponse(BaseModel):
    items: list[TypedVoucherResponse]
    total: int
