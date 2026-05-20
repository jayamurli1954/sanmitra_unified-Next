from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class DonationCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    donor_name: str | None = Field(default=None, max_length=120)
    payment_mode: str = Field(default="bank", min_length=2, max_length=40)
    donated_on: date
    reference: str | None = Field(default=None, max_length=120)

    bank_account_id: int
    donation_income_account_id: int

    @field_validator("amount")
    @classmethod
    def round_amount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class DonationCreateResponse(BaseModel):
    donation_id: str
    tenant_id: str
    app_key: str
    amount: Decimal
    journal_entry_id: int
    created: bool


class SevaCollectionCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    seva_name: str = Field(min_length=1, max_length=160)
    devotee_name: str | None = Field(default=None, max_length=120)
    payment_mode: str = Field(default="bank", min_length=2, max_length=40)
    collected_on: date
    reference: str | None = Field(default=None, max_length=120)

    bank_account_id: int
    seva_income_account_id: int

    @field_validator("amount")
    @classmethod
    def round_amount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class SevaCollectionCreateResponse(BaseModel):
    seva_collection_id: str
    tenant_id: str
    app_key: str
    amount: Decimal
    journal_entry_id: int
    created: bool
