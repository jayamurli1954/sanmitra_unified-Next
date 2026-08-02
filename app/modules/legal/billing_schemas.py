"""Schemas for LegalMitra Stage 6 — practice billing and optional MitraBooks posting."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

InvoiceStatus = Literal["draft", "issued", "partially_paid", "paid", "void"]
CollectionMode = Literal["cash", "bank", "upi", "cheque", "other"]
MoneyStr = Decimal


def _q(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


class FeeLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: MoneyStr = Field(default=Decimal("1.00"))
    unit_rate: MoneyStr = Field(default=Decimal("0.00"))
    tax_rate_percent: MoneyStr = Field(default=Decimal("0.00"))

    @field_validator("quantity", "unit_rate", "tax_rate_percent", mode="before")
    @classmethod
    def _money(cls, v):
        return _q(v)


class FeeInvoiceCreateRequest(BaseModel):
    matter_id: str = Field(min_length=8, max_length=64)
    client_id: str | None = Field(default=None, min_length=8, max_length=64)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    lines: list[FeeLineIn] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=2000)
    gstin: str | None = Field(default=None, max_length=20)
    place_of_supply: str | None = Field(default=None, max_length=120)


class FeeInvoiceUpdateRequest(BaseModel):
    lines: list[FeeLineIn] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    gstin: str | None = Field(default=None, max_length=20)
    place_of_supply: str | None = Field(default=None, max_length=120)


class FeeInvoiceVoidRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)
    confirm: bool = True


class FeeCollectionCreateRequest(BaseModel):
    amount: MoneyStr
    mode: CollectionMode = "bank"
    collected_on: date | None = None
    reference: str | None = Field(default=None, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=128)
    notes: str | None = Field(default=None, max_length=1000)
    # Explicit human confirm required to post into MitraBooks books.
    post_to_mitrabooks: bool = False
    confirm_post_to_mitrabooks: bool = False

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, v):
        amount = _q(v)
        if amount <= 0:
            raise ValueError("Collection amount must be positive")
        return amount


class FeeLineResponse(BaseModel):
    description: str
    quantity: Decimal
    unit_rate: Decimal
    tax_rate_percent: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class FeeCollectionResponse(BaseModel):
    collection_id: str
    invoice_id: str
    tenant_id: str
    app_key: str
    amount: Decimal
    mode: CollectionMode
    collected_on: date
    reference: str | None = None
    notes: str | None = None
    idempotency_key: str
    accounting_status: str = "not_posted"
    accounting_posting_ref: str | None = None
    accounting_journal_id: int | None = None
    accounting_error: str | None = None
    created_by: str
    created_at: datetime


class FeeInvoiceResponse(BaseModel):
    invoice_id: str
    invoice_number: str
    tenant_id: str
    app_key: str
    matter_id: str
    client_id: str | None = None
    status: InvoiceStatus
    currency: str = "INR"
    lines: list[FeeLineResponse] = Field(default_factory=list)
    subtotal: Decimal
    tax_total: Decimal
    grand_total: Decimal
    amount_collected: Decimal
    amount_outstanding: Decimal
    notes: str | None = None
    gstin: str | None = None
    place_of_supply: str | None = None
    issued_at: datetime | None = None
    issued_by: str | None = None
    voided_at: datetime | None = None
    void_reason: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class FeeInvoiceListResponse(BaseModel):
    items: list[FeeInvoiceResponse]
    count: int


class FeeCollectionListResponse(BaseModel):
    items: list[FeeCollectionResponse]
    count: int


class FeeSummaryResponse(BaseModel):
    currency: str = "INR"
    invoices_issued: int = 0
    invoices_paid: int = 0
    invoices_partial: int = 0
    invoices_draft: int = 0
    total_billed: Decimal = Decimal("0.00")
    total_collected: Decimal = Decimal("0.00")
    fees_outstanding: Decimal = Decimal("0.00")
    fees_outstanding_display: str = "₹0.00"
    data_source: str = "live"


class TimeEntryCreateRequest(BaseModel):
    matter_id: str = Field(min_length=8, max_length=64)
    minutes: int = Field(ge=1, le=24 * 60)
    hourly_rate: MoneyStr = Field(default=Decimal("0.00"))
    description: str = Field(min_length=1, max_length=500)
    work_date: date | None = None
    billable: bool = True

    @field_validator("hourly_rate", mode="before")
    @classmethod
    def _rate(cls, v):
        return _q(v)


class TimeEntryResponse(BaseModel):
    entry_id: str
    tenant_id: str
    app_key: str
    matter_id: str
    minutes: int
    hourly_rate: Decimal
    amount: Decimal
    description: str
    work_date: date
    billable: bool
    created_by: str
    created_at: datetime


class TimeEntryListResponse(BaseModel):
    items: list[TimeEntryResponse]
    count: int


class FeeGlMapUpsertRequest(BaseModel):
    bank_account_id: int = Field(ge=1)
    income_account_id: int = Field(ge=1)
    bank_account_code: str | None = Field(default=None, max_length=30)
    income_account_code: str | None = Field(default=None, max_length=30)
    accounting_app_key: str = Field(default="mitrabooks", max_length=40)
    accounting_entity_id: str = Field(default="primary", max_length=64)
    notes: str | None = Field(default=None, max_length=500)


class FeeGlMapResponse(BaseModel):
    tenant_id: str
    app_key: str
    bank_account_id: int | None = None
    income_account_id: int | None = None
    bank_account_code: str | None = None
    income_account_code: str | None = None
    accounting_app_key: str = "mitrabooks"
    accounting_entity_id: str = "primary"
    notes: str | None = None
    configured: bool = False
    updated_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
