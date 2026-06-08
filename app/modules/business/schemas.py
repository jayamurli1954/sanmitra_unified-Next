from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PartyType = Literal["customer", "vendor", "both"]
VoucherType = Literal["payment", "receipt", "contra", "journal"]
CaDocumentStatus = Literal["uploaded", "under_review", "query_raised", "reviewed", "posted"]


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


class CaDocumentCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=160)
    document_type: str = Field(..., min_length=1, max_length=80)
    period: str = Field(..., min_length=1, max_length=80)
    assigned_to: str | None = Field(default=None, max_length=120)
    original_file_name: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=500)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CaDocumentUpdateRequest(BaseModel):
    status: CaDocumentStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=120)
    next_action: str | None = Field(default=None, max_length=160)
    posting_reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CaDocumentResponse(BaseModel):
    document_id: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    client_name: str
    document_type: str
    period: str
    status: str
    assigned_to: str | None = None
    original_file_name: str | None = None
    next_action: str
    posting_reference: str | None = None
    notes: str | None = None
    created_by: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class CaDocumentListResponse(BaseModel):
    items: list[CaDocumentResponse]
    total: int


SalesInvoiceStatus = Literal["posted", "cancelled"]


class SalesInvoiceLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))


class SalesInvoiceLineResponse(SalesInvoiceLineItem):
    taxable_amount: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    line_total: Decimal


class SalesInvoiceCreateRequest(BaseModel):
    customer_party_id: str = Field(..., min_length=1, max_length=80)
    invoice_date: date
    due_date: date | None = None
    is_inter_state: bool = False
    income_account_code: str = Field(default="41001", min_length=1, max_length=50)
    place_of_supply: str | None = Field(default=None, max_length=80)
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[SalesInvoiceLineItem] = Field(..., min_length=1)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class SalesInvoiceCancelRequest(BaseModel):
    reason: str = Field(default="Cancellation", min_length=1, max_length=240)
    cancel_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class SalesInvoiceResponse(BaseModel):
    invoice_id: str
    invoice_number: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    customer_party_id: str
    customer_name: str | None = None
    customer_gstin: str | None = None
    invoice_date: date
    due_date: date | None = None
    is_inter_state: bool
    place_of_supply: str | None = None
    income_account_code: str
    reference: str | None = None
    notes: str | None = None
    line_items: list[SalesInvoiceLineResponse]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    invoice_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class SalesInvoiceListResponse(BaseModel):
    items: list[SalesInvoiceResponse]
    total: int


# ---- Invoice form customization settings (per-tenant) ----

# Standard optional fields that admins can show/hide/require on the invoice form.
INVOICE_STANDARD_FIELDS = ["due_date", "place_of_supply", "reference", "notes", "hsn_sac"]


class InvoiceFieldRule(BaseModel):
    visible: bool = True
    required: bool = False


class InvoiceNumberingConfig(BaseModel):
    prefix: str = Field(default="INV", min_length=1, max_length=20)
    # Token-based format. Supported tokens: {PREFIX} {FY} {FYSHORT} {SEQ}
    number_format: str = Field(default="{PREFIX}-{FY}-{SEQ}", min_length=1, max_length=80)
    start_number: int = Field(default=1, ge=1)
    seq_padding: int = Field(default=6, ge=1, le=12)
    reset_yearly: bool = True


class InvoiceCustomFieldDef(BaseModel):
    key: str = Field(..., min_length=1, max_length=40, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    label: str = Field(..., min_length=1, max_length=60)
    scope: Literal["header", "line"] = "header"
    field_type: Literal["text", "number", "date"] = "text"
    required: bool = False


class InvoiceBrandingConfig(BaseModel):
    business_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=400)
    gstin: str | None = Field(default=None, max_length=20)
    bank_details: str | None = Field(default=None, max_length=400)
    terms: str | None = Field(default=None, max_length=1000)
    footer: str | None = Field(default=None, max_length=300)
    logo_url: str | None = Field(default=None, max_length=400)


def _default_field_config() -> dict[str, InvoiceFieldRule]:
    return {key: InvoiceFieldRule() for key in INVOICE_STANDARD_FIELDS}


class InvoiceSettings(BaseModel):
    field_config: dict[str, InvoiceFieldRule] = Field(default_factory=_default_field_config)
    numbering: InvoiceNumberingConfig = Field(default_factory=InvoiceNumberingConfig)
    custom_fields: list[InvoiceCustomFieldDef] = Field(default_factory=list)
    branding: InvoiceBrandingConfig = Field(default_factory=InvoiceBrandingConfig)


class InvoiceSettingsUpdateRequest(InvoiceSettings):
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class InvoiceSettingsResponse(InvoiceSettings):
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    updated_by: str | None = None
    updated_at: datetime | None = None


# ---- Purchase Bills (vendor invoices, with Input GST / ITC) ----

PurchaseBillStatus = Literal["posted", "cancelled"]


class PurchaseBillLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))


class PurchaseBillLineResponse(PurchaseBillLineItem):
    taxable_amount: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    line_total: Decimal


class PurchaseBillCreateRequest(BaseModel):
    vendor_party_id: str = Field(..., min_length=1, max_length=80)
    bill_number: str = Field(..., min_length=1, max_length=120)
    bill_date: date
    due_date: date | None = None
    is_inter_state: bool = False
    expense_account_code: str = Field(default="51001", min_length=1, max_length=50)
    place_of_supply: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[PurchaseBillLineItem] = Field(..., min_length=1)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class PurchaseBillCancelRequest(BaseModel):
    reason: str = Field(default="Cancellation", min_length=1, max_length=240)
    cancel_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class PurchaseBillResponse(BaseModel):
    bill_id: str
    bill_number: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    vendor_party_id: str
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    bill_date: date
    due_date: date | None = None
    is_inter_state: bool
    place_of_supply: str | None = None
    expense_account_code: str
    notes: str | None = None
    line_items: list[PurchaseBillLineResponse]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    bill_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class PurchaseBillListResponse(BaseModel):
    items: list[PurchaseBillResponse]
    total: int
