from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


PartyType = Literal["customer", "vendor", "both"]
VoucherType = Literal["payment", "receipt", "contra", "journal"]
CaDocumentStatus = Literal["uploaded", "under_review", "query_raised", "reviewed", "posted"]
CaDocumentPriority = Literal["low", "normal", "high", "urgent"]
ApprovalStatus = Literal["auto_posted", "not_submitted", "pending_approval", "approved", "rejected"]
BusinessAttachmentOwnerType = Literal["sales_invoice", "purchase_bill", "ca_document"]


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
    opening_balance: Decimal = Field(
        default=Decimal("0"),
        description="Legacy profile input only. Live opening balances must be posted through the opening-balance journal flow.",
    )


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
    opening_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    balance_source: str = "ledger_reports"
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
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
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
    cost_centre_id: str | None = None
    project_id: str | None = None
    amount: Decimal
    entry_date: date
    debit_account_id: int
    credit_account_id: int
    description: str
    reference: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    reversal_reason: str | None = None
    reversed_at: datetime | None = None
    status: str
    approval_required: bool = True
    approval_status: ApprovalStatus = "pending_approval"
    approval_submitted_at: datetime | None = None
    approval_submitted_by: str | None = None
    approval_decided_at: datetime | None = None
    approval_decided_by: str | None = None
    approval_notes: str | None = None
    rejection_reason: str | None = None
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
    client_owner: str | None = Field(default=None, max_length=120)
    priority: CaDocumentPriority = "normal"
    due_date: str | None = Field(default=None, max_length=20)
    compliance_area: str | None = Field(default=None, max_length=80)
    client_access_enabled: bool = False
    original_file_name: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=500)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CaDocumentUpdateRequest(BaseModel):
    status: CaDocumentStatus | None = None
    assigned_to: str | None = Field(default=None, max_length=120)
    client_owner: str | None = Field(default=None, max_length=120)
    priority: CaDocumentPriority | None = None
    due_date: str | None = Field(default=None, max_length=20)
    compliance_area: str | None = Field(default=None, max_length=80)
    client_access_enabled: bool | None = None
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
    client_owner: str | None = None
    priority: str = "normal"
    due_date: str | None = None
    compliance_area: str | None = None
    client_access_enabled: bool = False
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


CaClientAccessLevel = Literal["view_only", "data_entry", "full_access", "restricted_filing"]


class CaClientCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=2, max_length=160)
    gstin: str | None = Field(default=None, max_length=20)
    pan: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=160)
    contact_phone: str | None = Field(default=None, max_length=40)
    engagement_type: str | None = Field(default=None, max_length=80)
    assigned_to: str | None = Field(default=None, max_length=120)
    client_owner: str | None = Field(default=None, max_length=120)
    access_level: CaClientAccessLevel = "view_only"
    compliance_tracks: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CaClientUpdateRequest(BaseModel):
    client_name: str | None = Field(default=None, min_length=2, max_length=160)
    gstin: str | None = Field(default=None, max_length=20)
    pan: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=160)
    contact_phone: str | None = Field(default=None, max_length=40)
    engagement_type: str | None = Field(default=None, max_length=80)
    assigned_to: str | None = Field(default=None, max_length=120)
    client_owner: str | None = Field(default=None, max_length=120)
    access_level: CaClientAccessLevel | None = None
    compliance_tracks: list[str] | None = None
    notes: str | None = Field(default=None, max_length=500)
    active: bool | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class CaClientResponse(BaseModel):
    client_id: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    client_name: str
    gstin: str | None = None
    pan: str | None = None
    contact_person: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    engagement_type: str | None = None
    assigned_to: str | None = None
    client_owner: str | None = None
    access_level: CaClientAccessLevel = "view_only"
    compliance_tracks: list[str] = Field(default_factory=list)
    notes: str | None = None
    active: bool = True
    created_by: str
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class CaClientListResponse(BaseModel):
    items: list[CaClientResponse]
    total: int


class BusinessDocumentAttachmentResponse(BaseModel):
    attachment_id: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    owner_type: BusinessAttachmentOwnerType
    owner_id: str
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: datetime


class BusinessDocumentAttachmentListResponse(BaseModel):
    items: list[BusinessDocumentAttachmentResponse]
    total: int


class CaInviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    full_name: str = Field(..., min_length=1, max_length=120)


class CaInviteAcceptRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class CaAccessRecord(BaseModel):
    invite_id: str
    email: str
    full_name: str
    status: str
    invited_by: str
    invited_at: datetime | None
    expires_at: datetime | None
    accepted_at: datetime | None
    user_id: str | None


class CaAccessListResponse(BaseModel):
    ca_users: list[CaAccessRecord]
    total: int


class CaRevokeResponse(BaseModel):
    ok: bool
    message: str


SalesInvoiceStatus = Literal["draft", "pending_approval", "posted", "rejected", "cancelled"]


# Supply-type classification for GST returns. "taxable" is the default;
# "zero_rated" marks export/SEZ supply (GSTR-1 6A, 3B 3.1(b) — no tax under
# LUT); the others distinguish 0%-rated from genuinely exempt/non-GST supply.
GstSupplyType = Literal["taxable", "zero_rated", "exempt", "nil_rated", "non_gst"]


class SalesInvoiceLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    uqc: str | None = Field(default=None, max_length=10)  # unit quantity code, e.g. NOS/KGS
    item_id: str | None = Field(default=None, max_length=80)  # inventory item (when enabled)
    supply_type: GstSupplyType = "taxable"
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)


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
    # Accounting dimensions (tags for reporting; no ledger impact).
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
    save_as_draft: bool = False
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class SalesInvoiceCancelRequest(BaseModel):
    reason: str = Field(default="Cancellation", min_length=1, max_length=240)
    cancel_date: date | None = None
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class ApprovalReviewRequest(BaseModel):
    approve: bool = True
    notes: str | None = Field(default=None, max_length=500)
    rejection_reason: str | None = Field(default=None, max_length=240)
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
    cost_centre_id: str | None = None
    project_id: str | None = None
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    approval_required: bool = False
    approval_status: ApprovalStatus = "auto_posted"
    approval_submitted_at: datetime | None = None
    approval_submitted_by: str | None = None
    approval_decided_at: datetime | None = None
    approval_decided_by: str | None = None
    approval_notes: str | None = None
    rejection_reason: str | None = None
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
    # Opt-in inventory accounting. OFF (default): purchases stay pure expense,
    # no stock screens anywhere — service businesses see no change. ON: item
    # master, stock register and the periodic closing-stock journal light up.
    inventory_enabled: bool = False
    # Tenant-admin on/off switch for the HR / Payroll add-on. Second of the
    # two-level HR gate: effective only once the platform owner has provisioned
    # the add-on for the tenant (core_tenants.hr_addon_available).
    hr_enabled: bool = False
    # Tenant-admin on/off for the enterprise Cost-Centre Accounting add-on.
    # Second level of its gate (platform sets core_tenants.cost_centre_addon_available).
    cost_centre_enabled: bool = False
    # Tenant-admin on/off for the Manufacturing add-on. Depends on cost centres
    # (manufacturing posts to cost centres), so enabling it implies cost centres.
    # Second level of its gate (platform sets core_tenants.manufacturing_addon_available).
    manufacturing_enabled: bool = False


class InvoiceSettingsUpdateRequest(InvoiceSettings):
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class InvoiceSettingsResponse(InvoiceSettings):
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    updated_by: str | None = None
    updated_at: datetime | None = None


# ---- MitraBooks admin/settings workspace (Phase 2B backend contracts) ----

BusinessRoleKey = Literal["owner", "admin", "accountant", "cashier", "auditor", "viewer"]


class BusinessOrganizationSettings(BaseModel):
    legal_name: str | None = Field(default=None, max_length=160)
    trade_name: str | None = Field(default=None, max_length=160)
    gstin: str | None = Field(default=None, max_length=20)
    pan: str | None = Field(default=None, max_length=20)
    tan: str | None = Field(default=None, max_length=20)
    cin_llpin: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=500)
    contact_email: str | None = Field(default=None, max_length=160)
    contact_phone: str | None = Field(default=None, max_length=40)
    financial_year_start_month: int = Field(default=4, ge=1, le=12)
    currency_code: str = Field(default="INR", min_length=3, max_length=3)
    timezone: str = Field(default="Asia/Calcutta", min_length=1, max_length=80)
    logo_url: str | None = Field(default=None, max_length=400)


class BusinessBranchSettingsItem(BaseModel):
    branch_code: str = Field(..., min_length=1, max_length=30)
    branch_name: str = Field(..., min_length=1, max_length=160)
    gstin: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=400)
    contact_phone: str | None = Field(default=None, max_length=40)
    warehouse_code: str | None = Field(default=None, max_length=40)
    cost_centre_code: str | None = Field(default=None, max_length=40)
    active: bool = True


class BusinessRoleTemplate(BaseModel):
    role_key: BusinessRoleKey
    display_name: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    can_invite_users: bool = False
    can_approve_documents: bool = False
    can_manage_settings: bool = False


class BusinessPermissionMatrix(BaseModel):
    module_permissions: dict[str, list[BusinessRoleKey]] = Field(default_factory=dict)
    action_permissions: dict[str, list[BusinessRoleKey]] = Field(default_factory=dict)


class BusinessVoucherConfigurationSettings(BaseModel):
    journal_prefix: str = Field(default="JV", min_length=1, max_length=20)
    receipt_prefix: str = Field(default="RV", min_length=1, max_length=20)
    payment_prefix: str = Field(default="PV", min_length=1, max_length=20)
    contra_prefix: str = Field(default="CV", min_length=1, max_length=20)
    approval_threshold_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    approval_required_above_threshold: bool = True
    default_approver_role: BusinessRoleKey = "admin"


class BusinessFinancialControlSettings(BaseModel):
    voucher_lock_date: date | None = None
    backdated_entry_requires_approval: bool = True
    allow_posting_in_locked_period_with_super_admin: bool = False
    period_close_note: str | None = Field(default=None, max_length=240)


class BusinessSecuritySettings(BaseModel):
    mfa_required_for_admins: bool = False
    password_min_length: int = Field(default=10, ge=8, le=128)
    session_timeout_minutes: int = Field(default=480, ge=15, le=1440)
    allow_concurrent_sessions: bool = True
    login_alert_email: str | None = Field(default=None, max_length=160)


class BusinessTemplateSettings(BaseModel):
    invoice_template: str = Field(default="standard", min_length=1, max_length=40)
    receipt_template: str = Field(default="standard", min_length=1, max_length=40)
    payment_voucher_template: str = Field(default="standard", min_length=1, max_length=40)
    statement_template: str = Field(default="standard", min_length=1, max_length=40)
    report_footer: str | None = Field(default=None, max_length=300)


class BusinessNotificationSettings(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = False
    whatsapp_enabled: bool = False
    due_date_reminders: bool = True
    approval_reminders: bool = True
    compliance_reminders: bool = True
    reminder_recipients: list[str] = Field(default_factory=list)


class BusinessSubscriptionBillingSettings(BaseModel):
    billing_contact_name: str | None = Field(default=None, max_length=160)
    billing_email: str | None = Field(default=None, max_length=160)
    billing_phone: str | None = Field(default=None, max_length=40)
    invoice_delivery_email: str | None = Field(default=None, max_length=160)
    renewal_mode: Literal["manual", "notify_only", "auto_renew_request"] = "notify_only"
    payment_provider: str = Field(default="razorpay", min_length=1, max_length=40)


class BusinessIntegrationSettings(BaseModel):
    payment_gateway_provider: str = Field(default="razorpay", min_length=1, max_length=40)
    payment_gateway_enabled: bool = False
    gst_portal_enabled: bool = False
    gst_portal_username_hint: str | None = Field(default=None, max_length=160)
    bank_feed_mode: Literal["manual_import", "api_shell"] = "manual_import"
    bank_provider_label: str | None = Field(default=None, max_length=120)
    whatsapp_enabled: bool = False
    whatsapp_sender_name: str | None = Field(default=None, max_length=120)
    email_provider_enabled: bool = False
    email_from_name: str | None = Field(default=None, max_length=160)
    email_reply_to: str | None = Field(default=None, max_length=160)
    document_storage_provider: Literal["local_filesystem", "supabase", "s3", "gcs", "azure_blob"] = "local_filesystem"
    document_storage_path_prefix: str | None = Field(default=None, max_length=240)
    allowed_upload_mime_types: list[str] = Field(default_factory=lambda: [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ])
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    provider_secrets_configured: dict[str, bool] = Field(default_factory=dict)


class BusinessAiSettings(BaseModel):
    ai_mis_enabled: bool = False
    ocr_enabled: bool = False
    ocr_provider: str | None = Field(default=None, max_length=80)
    categorization_suggestions_enabled: bool = False
    reconciliation_suggestions_enabled: bool = False
    forecasting_enabled: bool = False
    document_review_required: bool = True
    posting_review_required: bool = True
    auto_post_to_ledger: bool = False
    model_label: str | None = Field(default=None, max_length=120)


def _default_role_templates() -> list[BusinessRoleTemplate]:
    return [
        BusinessRoleTemplate(role_key="owner", display_name="Owner", can_invite_users=True, can_approve_documents=True, can_manage_settings=True),
        BusinessRoleTemplate(role_key="admin", display_name="Admin", can_invite_users=True, can_approve_documents=True, can_manage_settings=True),
        BusinessRoleTemplate(role_key="accountant", display_name="Accountant", can_approve_documents=False, can_manage_settings=False),
        BusinessRoleTemplate(role_key="cashier", display_name="Cashier"),
        BusinessRoleTemplate(role_key="auditor", display_name="Auditor"),
        BusinessRoleTemplate(role_key="viewer", display_name="Viewer"),
    ]


def _default_permission_matrix() -> BusinessPermissionMatrix:
    return BusinessPermissionMatrix(
        module_permissions={
            "business": ["owner", "admin", "accountant", "cashier", "auditor", "viewer"],
            "accounting": ["owner", "admin", "accountant", "auditor", "viewer"],
            "inventory": ["owner", "admin", "accountant"],
            "banking": ["owner", "admin", "accountant", "cashier"],
            "reports": ["owner", "admin", "accountant", "auditor", "viewer"],
        },
        action_permissions={
            "voucher_approve": ["owner", "admin"],
            "voucher_reverse": ["owner", "admin", "accountant"],
            "invoice_approve": ["owner", "admin"],
            "bill_approve": ["owner", "admin"],
            "settings_manage": ["owner", "admin"],
        },
    )


class BusinessAdminSettings(BaseModel):
    organization: BusinessOrganizationSettings = Field(default_factory=BusinessOrganizationSettings)
    branches: list[BusinessBranchSettingsItem] = Field(default_factory=list)
    roles: list[BusinessRoleTemplate] = Field(default_factory=_default_role_templates)
    permissions: BusinessPermissionMatrix = Field(default_factory=_default_permission_matrix)
    voucher_configuration: BusinessVoucherConfigurationSettings = Field(default_factory=BusinessVoucherConfigurationSettings)
    financial_controls: BusinessFinancialControlSettings = Field(default_factory=BusinessFinancialControlSettings)
    security: BusinessSecuritySettings = Field(default_factory=BusinessSecuritySettings)
    templates: BusinessTemplateSettings = Field(default_factory=BusinessTemplateSettings)
    notifications: BusinessNotificationSettings = Field(default_factory=BusinessNotificationSettings)
    subscription_billing: BusinessSubscriptionBillingSettings = Field(default_factory=BusinessSubscriptionBillingSettings)
    integrations: BusinessIntegrationSettings = Field(default_factory=BusinessIntegrationSettings)
    ai_settings: BusinessAiSettings = Field(default_factory=BusinessAiSettings)


class BusinessAdminSettingsUpdateRequest(BusinessAdminSettings):
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class BusinessAdminSettingsResponse(BusinessAdminSettings):
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    updated_by: str | None = None
    updated_at: datetime | None = None


# ---- Purchase Bills (vendor invoices, with Input GST / ITC) ----

PurchaseBillStatus = Literal["draft", "pending_approval", "posted", "rejected", "cancelled"]


class PurchaseBillLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=300)
    hsn_sac: str | None = Field(default=None, max_length=20)
    item_id: str | None = Field(default=None, max_length=80)  # inventory item (when enabled)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    rate: Decimal = Field(..., ge=Decimal("0"))
    gst_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"), le=Decimal("100"))
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)


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
    # Accounting dimensions (tags for reporting; no ledger impact).
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
    save_as_draft: bool = False
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
    cost_centre_id: str | None = None
    project_id: str | None = None
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    approval_required: bool = False
    approval_status: ApprovalStatus = "auto_posted"
    approval_submitted_at: datetime | None = None
    approval_submitted_by: str | None = None
    approval_decided_at: datetime | None = None
    approval_decided_by: str | None = None
    approval_notes: str | None = None
    rejection_reason: str | None = None
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
    # Accounting dimensions (tags for reporting; no ledger impact).
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
    save_as_draft: bool = False
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
    cost_centre_id: str | None = None
    project_id: str | None = None
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    note_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    approval_required: bool = False
    approval_status: ApprovalStatus = "auto_posted"
    approval_submitted_at: datetime | None = None
    approval_submitted_by: str | None = None
    approval_decided_at: datetime | None = None
    approval_decided_by: str | None = None
    approval_notes: str | None = None
    rejection_reason: str | None = None
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

DebitNoteStatus = Literal["draft", "pending_approval", "posted", "rejected", "cancelled"]
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
    # Accounting dimensions (tags for reporting; no ledger impact).
    cost_centre_id: str | None = Field(default=None, max_length=80)
    project_id: str | None = Field(default=None, max_length=80)
    save_as_draft: bool = False
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
    cost_centre_id: str | None = None
    project_id: str | None = None
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    gst_total: Decimal
    note_total: Decimal
    status: str
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    approval_required: bool = False
    approval_status: ApprovalStatus = "auto_posted"
    approval_submitted_at: datetime | None = None
    approval_submitted_by: str | None = None
    approval_decided_at: datetime | None = None
    approval_decided_by: str | None = None
    approval_notes: str | None = None
    rejection_reason: str | None = None
    cancel_reason: str | None = None
    cancelled_at: datetime | None = None
    created: bool = False
    created_by: str
    created_at: datetime
    updated_at: datetime


class DebitNoteListResponse(BaseModel):
    items: list[DebitNoteResponse]
    total: int


class ApprovalQueueItem(BaseModel):
    document_type: str
    document_id: str
    document_number: str
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    party_name: str | None = None
    document_date: date | None = None
    amount: Decimal | None = None
    status: str
    approval_status: ApprovalStatus = "auto_posted"
    approval_required: bool = False
    journal_entry_id: int | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApprovalQueueResponse(BaseModel):
    items: list[ApprovalQueueItem]
    total: int


# ---- GST settlement (period-end set-off of output vs input GST) ----


class GstSettlementCreateRequest(BaseModel):
    period: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # YYYY-MM
    lock_period: bool = True
    accounting_entity_id: str = Field(default="primary", min_length=1, max_length=80)


class GstSettlementReverseRequest(BaseModel):
    reason: str = Field(default="GST settlement reversal", min_length=1, max_length=240)
    reversal_date: date | None = None
    unlock_period: bool = True
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
    status: str  # "preview" | "posted" | "reversed"
    posted: bool = False
    period_locked: bool = False
    journal_entry_id: int | None = None
    reversal_journal_entry_id: int | None = None
    note: str | None = None
    settled_by: str | None = None
    settled_at: datetime | None = None
    reversed_by: str | None = None
    reversed_at: datetime | None = None


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
