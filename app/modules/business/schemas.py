from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PartyType = Literal["customer", "vendor", "both"]
VoucherType = Literal["payment", "receipt", "contra", "journal"]
CaDocumentStatus = Literal["uploaded", "under_review", "query_raised", "reviewed", "posted"]


class GstHeadAmounts(BaseModel):
    igst: Decimal = Decimal("0")
    cgst: Decimal = Decimal("0")
    sgst: Decimal = Decimal("0")


class PartyCreateRequest(BaseModel):
    party_name: str = Field(..., min_length=1, max_length=160)
    party_type: PartyType = "customer"
    party_code: str | None = Field(default=None, max_length=40)
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    pincode: str | None = Field(default=None, max_length=12)
    opening_balance: Decimal = Decimal("0")


class PartyUpdateRequest(BaseModel):
    party_name: str | None = Field(default=None, min_length=1, max_length=160)
    party_type: PartyType | None = None
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    billing_address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    pincode: str | None = Field(default=None, max_length=12)


class PartyResponse(BaseModel):
    party_id: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    party_name: str
    party_type: str
    party_code: str
    gstin: str | None = None
    pan: str | None = None
    email: str | None = None
    phone: str | None = None
    billing_address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
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


# Supply-type classification for GST returns. "taxable" is the default; the
# others let GSTR-1/3B distinguish 0%-rated from genuinely exempt/non-GST supply.
GstSupplyType = Literal["taxable", "exempt", "nil_rated", "non_gst"]


class SalesInvoiceLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    uqc: str | None = Field(default=None, max_length=10)  # unit quantity code, e.g. NOS/KGS
    supply_type: GstSupplyType = "taxable"
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
    # TCS (Income-tax 206C): section key from TCS_SECTIONS; rate overridable.
    tcs_section: str | None = Field(default=None, max_length=20)
    tcs_rate: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
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
    document_type: str = "tax_invoice"   # "bill_of_supply" for composition dealers
    is_composition: bool = False
    reference: str | None = None
    notes: str | None = None
    line_items: list[SalesInvoiceLineResponse]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    invoice_total: Decimal
    # TCS collected on top of the invoice total (customer owes grand_total).
    tcs_section: str | None = None
    tcs_rate: Decimal | None = None
    tcs_base_amount: Decimal | None = None
    tcs_amount: Decimal = Decimal("0")
    grand_total: Decimal | None = None
    collectee_pan: str | None = None
    collectee_pan_missing: bool = False
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


# GST registration regime for this entity. "composition" dealers issue a Bill of
# Supply (no tax collected), cannot claim ITC, and file CMP-08 / GSTR-4.
GstRegistrationType = Literal["regular", "composition"]
CompositionCategory = Literal["goods", "restaurant", "services"]


class InvoiceBrandingConfig(BaseModel):
    business_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=400)
    gstin: str | None = Field(default=None, max_length=20)
    bank_details: str | None = Field(default=None, max_length=400)
    terms: str | None = Field(default=None, max_length=1000)
    footer: str | None = Field(default=None, max_length=300)
    logo_url: str | None = Field(default=None, max_length=400)
    gst_registration_type: GstRegistrationType = "regular"
    composition_category: CompositionCategory | None = None


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
    # Reverse charge (GST 9(3)/9(4)): the recipient owes the GST, not the
    # vendor — the vendor is paid the taxable value only.
    is_reverse_charge: bool = False
    expense_account_code: str = Field(default="51001", min_length=1, max_length=50)
    place_of_supply: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[PurchaseBillLineItem] = Field(..., min_length=1)
    # TDS (Income-tax): section key from TDS_SECTIONS; rate defaults from the
    # section master, overridable (rates change by Finance Act / 206AA no-PAN 20%).
    tds_section: str | None = Field(default=None, max_length=20)
    tds_rate: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("100"))
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
    is_reverse_charge: bool = False
    rcm_payable: Decimal = Decimal("0")
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
    # TDS deducted at credit time (vendor is owed net_payable = total - TDS).
    tds_section: str | None = None
    tds_rate: Decimal | None = None
    tds_base_amount: Decimal | None = None
    tds_amount: Decimal = Decimal("0")
    net_payable: Decimal | None = None
    deductee_pan: str | None = None
    deductee_pan_missing: bool = False
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    # Payment tracking (drives GST Rule 37 180-day test)
    payment_status: str = "unpaid"  # "unpaid" | "partial" | "paid"
    paid_amount: Decimal = Decimal("0")
    paid_date: date | None = None
    # ITC reversal / reclaim (GST Rule 37)
    itc_reversed: bool = False
    itc_reversal_journal_entry_id: int | None = None
    itc_reversal_date: date | None = None
    itc_reversal_period: str | None = None
    itc_reversed_amounts: GstHeadAmounts | None = None
    itc_interest_amount: Decimal = Decimal("0")
    itc_reclaimed: bool = False
    itc_reclaim_journal_entry_id: int | None = None
    itc_reclaim_date: date | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class PurchaseBillListResponse(BaseModel):
    items: list[PurchaseBillResponse]
    total: int


# ---- GST period locks (finalised months) ----


class GstPeriodLockUpdateRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM
    locked: bool = True
    note: str | None = Field(default=None, max_length=240)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class GstPeriodLockResponse(BaseModel):
    period: str
    locked: bool
    note: str | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None


class GstPeriodLockListResponse(BaseModel):
    items: list[GstPeriodLockResponse]
    total: int


# ---- Credit Notes (sales-side GST adjustment against an invoice) ----

CreditNoteStatus = Literal["posted", "cancelled"]
CreditNoteReason = Literal["sales_return", "discount", "price_revision", "deficiency", "other"]


class CreditNoteLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    uqc: str | None = Field(default=None, max_length=10)
    supply_type: GstSupplyType = "taxable"
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))


class CreditNoteLineResponse(CreditNoteLineItem):
    taxable_amount: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    line_total: Decimal


class CreditNoteCreateRequest(BaseModel):
    customer_party_id: str = Field(..., min_length=1, max_length=80)
    note_date: date
    original_invoice_id: str | None = Field(default=None, max_length=80)
    original_invoice_number: str | None = Field(default=None, max_length=120)
    reason: CreditNoteReason = "sales_return"
    is_inter_state: bool = False
    income_account_code: str = Field(default="41001", min_length=1, max_length=50)
    place_of_supply: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[CreditNoteLineItem] = Field(..., min_length=1)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CreditNoteCancelRequest(BaseModel):
    reason: str = Field(default="Reversal", min_length=1, max_length=240)
    cancel_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CreditNoteResponse(BaseModel):
    credit_note_id: str
    credit_note_number: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    customer_party_id: str
    customer_name: str | None = None
    customer_gstin: str | None = None
    note_date: date
    original_invoice_id: str | None = None
    original_invoice_number: str | None = None
    reason: str
    is_inter_state: bool
    place_of_supply: str | None = None
    income_account_code: str
    notes: str | None = None
    line_items: list[CreditNoteLineResponse]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    note_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class CreditNoteListResponse(BaseModel):
    items: list[CreditNoteResponse]
    total: int


# ---- Debit Notes (purchase-side GST adjustment against a vendor bill) ----

DebitNoteStatus = Literal["posted", "cancelled"]
DebitNoteReason = Literal["purchase_return", "rejected_goods", "price_revision", "deficiency", "other"]


class DebitNoteLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))


class DebitNoteLineResponse(DebitNoteLineItem):
    taxable_amount: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    line_total: Decimal


class DebitNoteCreateRequest(BaseModel):
    vendor_party_id: str = Field(..., min_length=1, max_length=80)
    note_date: date
    original_bill_id: str | None = Field(default=None, max_length=80)
    original_bill_number: str | None = Field(default=None, max_length=120)
    reason: DebitNoteReason = "purchase_return"
    is_inter_state: bool = False
    expense_account_code: str = Field(default="51001", min_length=1, max_length=50)
    place_of_supply: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[DebitNoteLineItem] = Field(..., min_length=1)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class DebitNoteCancelRequest(BaseModel):
    reason: str = Field(default="Reversal", min_length=1, max_length=240)
    cancel_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class DebitNoteResponse(BaseModel):
    debit_note_id: str
    debit_note_number: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    vendor_party_id: str
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    note_date: date
    original_bill_id: str | None = None
    original_bill_number: str | None = None
    reason: str
    is_inter_state: bool
    place_of_supply: str | None = None
    expense_account_code: str
    notes: str | None = None
    line_items: list[DebitNoteLineResponse]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    note_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class DebitNoteListResponse(BaseModel):
    items: list[DebitNoteResponse]
    total: int


# ---- GST settlement (period-end set-off of output vs input GST) ----


class GstSettlementCreateRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM
    lock_period: bool = True
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class GstSettlementResponse(BaseModel):
    period: str
    accounting_entity_id: str
    output: GstHeadAmounts
    input_credit: GstHeadAmounts
    utilized: GstHeadAmounts
    cash_payable: GstHeadAmounts
    itc_carry_forward: GstHeadAmounts
    net_cash_payable: Decimal
    total_output: Decimal
    total_input: Decimal
    status: str  # "preview" | "posted"
    posted: bool = False
    period_locked: bool = False
    journal_entry_id: int | None = None
    note: str | None = None
    settled_by: str | None = None
    settled_at: datetime | None = None


# ---- ITC reversal (GST Rule 37 — non-payment within 180 days) ----


class BillPaymentUpdateRequest(BaseModel):
    paid_amount: Decimal = Field(..., ge=0)
    paid_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class ItcReversalActionRequest(BaseModel):
    reversal_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class ItcReclaimActionRequest(BaseModel):
    reclaim_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class ItcReversalCandidate(BaseModel):
    bill_id: str
    bill_number: str
    vendor_party_id: str
    vendor_name: str | None = None
    bill_date: date
    due_date: date  # bill_date + 180 days
    days_overdue: int
    payment_status: str
    paid_amount: Decimal = Decimal("0")
    bill_total: Decimal = Decimal("0")
    itc_amounts: GstHeadAmounts
    itc_total: Decimal
    interest_amount: Decimal
    gstr3b_ref: str = "4(B)(2)"


class ItcReversalPreviewResponse(BaseModel):
    as_of: date
    accounting_entity_id: str
    candidates: list[ItcReversalCandidate]
    total_itc: Decimal
    total_interest: Decimal
    count: int


# ---- Party sub-ledger (party-wise Debtors / Creditors + outstanding) ----


class PartyLedgerLine(BaseModel):
    party_id: str | None = None
    party_name: str
    balance: Decimal


class PartyLedgerResponse(BaseModel):
    as_of: date
    kind: str  # "receivable" | "payable"
    accounting_entity_id: str
    items: list[PartyLedgerLine]
    total_balance: Decimal
    count: int


class PartyOutstandingResponse(BaseModel):
    party_id: str
    party_name: str | None = None
    party_type: str | None = None
    as_of: date
    receivable: Decimal
    payable: Decimal


# ---- Payment allocation (open-item AR/AP) ----

AllocationSide = Literal["receivable", "payable"]


class OpenItem(BaseModel):
    open_item_id: str
    open_item_number: str | None = None
    party_id: str | None = None
    item_date: str | None = None
    due_date: str | None = None
    total: Decimal
    allocated: Decimal
    outstanding: Decimal
    days_overdue: int


class OpenItemListResponse(BaseModel):
    kind: AllocationSide
    as_of: date
    accounting_entity_id: str
    items: list[OpenItem]
    count: int
    total_outstanding: Decimal


class UnallocatedPayment(BaseModel):
    payment_id: str
    payment_number: str | None = None
    party_id: str | None = None
    payment_date: str | None = None
    amount: Decimal
    allocated: Decimal
    unallocated: Decimal


class UnallocatedPaymentListResponse(BaseModel):
    kind: AllocationSide
    accounting_entity_id: str
    items: list[UnallocatedPayment]
    count: int
    total_unallocated: Decimal


class AllocationLineInput(BaseModel):
    open_item_id: str = Field(..., min_length=1)
    allocated_amount: Decimal = Field(..., gt=0)


class AllocationCreateRequest(BaseModel):
    kind: AllocationSide
    payment_id: str = Field(..., min_length=1)
    allocations: list[AllocationLineInput] = Field(..., min_length=1)


class AllocationRecord(BaseModel):
    allocation_id: str
    side: AllocationSide
    party_id: str | None = None
    payment_id: str
    payment_number: str | None = None
    open_item_id: str
    open_item_number: str | None = None
    allocated_amount: Decimal
    allocated_date: str | None = None
    status: str


class AllocationCreateResponse(BaseModel):
    payment_id: str
    allocations: list[AllocationRecord]
    count: int


class FifoSuggestionLine(BaseModel):
    open_item_id: str
    open_item_number: str | None = None
    allocated_amount: Decimal


class FifoSuggestionResponse(BaseModel):
    payment_id: str
    payment_number: str | None = None
    party_id: str | None = None
    unallocated: Decimal
    allocations: list[FifoSuggestionLine]


class ReconciliationResponse(BaseModel):
    kind: AllocationSide
    as_of: date
    party_id: str | None = None
    open_items_outstanding: Decimal
    unallocated_payments: Decimal
    computed_net: Decimal
    ledger_balance: Decimal
    difference: Decimal
    balanced: bool
    ledger_unallocated_bucket: Decimal


class AgingPartyRow(BaseModel):
    party_id: str | None = None
    party_name: str | None = None
    buckets: dict[str, Decimal]
    total: Decimal


class AgingResponse(BaseModel):
    kind: AllocationSide
    as_of: date
    accounting_entity_id: str
    buckets_order: list[str]
    totals: dict[str, Decimal]
    grand_total: Decimal
    by_party: list[AgingPartyRow]
