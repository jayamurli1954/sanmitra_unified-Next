from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

OnboardingStatus = Literal["pending", "payment_pending", "payment_received", "under_review", "approved", "rejected"]
OnboardingIntent = Literal["register", "demo"]
OnboardingVerificationChannel = Literal["email", "mobile"]
OnboardingPaymentStatus = Literal["not_required", "pending", "received", "verified", "failed", "refunded"]
OnboardingDocumentStatus = Literal[
    "not_required",
    "pending",
    "uploaded",
    "verified",
    "rejected",
    "scheduled_for_deletion",
    "deleted",
]


class OnboardingVerificationDocument(BaseModel):
    document_id: str = Field(min_length=2, max_length=120)
    document_type: str = Field(min_length=2, max_length=80)
    file_name: str | None = Field(default=None, max_length=200)
    storage_key: str | None = Field(default=None, max_length=500)
    checksum_sha256: str | None = Field(default=None, max_length=128)
    uploaded_at: datetime | None = None
    verified_at: datetime | None = None
    verified_by: str | None = Field(default=None, max_length=160)
    status: OnboardingDocumentStatus = "uploaded"
    deletion_due_at: datetime | None = None
    deleted_at: datetime | None = None


class OnboardingPaymentUpdateRequest(BaseModel):
    payment_status: OnboardingPaymentStatus = "received"
    razorpay_payment_id: str | None = Field(default=None, max_length=120)
    razorpay_subscription_id: str | None = Field(default=None, max_length=120)
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    received_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def normalize(self):
        self.currency = (self.currency or "INR").strip().upper()
        self.razorpay_payment_id = (self.razorpay_payment_id or "").strip() or None
        self.razorpay_subscription_id = (self.razorpay_subscription_id or "").strip() or None
        self.notes = (self.notes or "").strip() or None
        return self


class OnboardingVerificationUpdateRequest(BaseModel):
    document_verification_status: OnboardingDocumentStatus = "uploaded"
    verification_notes: str | None = Field(default=None, max_length=1000)
    verification_documents: list[OnboardingVerificationDocument] = Field(default_factory=list)
    deletion_due_at: datetime | None = None

    @model_validator(mode="after")
    def normalize(self):
        self.verification_notes = (self.verification_notes or "").strip() or None
        return self


class OnboardingRequestCreate(BaseModel):
    organization_name: str | None = Field(default=None, max_length=200)
    organization_type: str | None = Field(default=None, max_length=40)
    authority_designation: str | None = Field(default=None, max_length=120)
    authority_designation_other: str | None = Field(default=None, max_length=120)
    request_intent: OnboardingIntent = "register"
    selected_plan: str | None = Field(default=None, max_length=80)
    plan_timing: str | None = Field(default=None, max_length=80)
    verification_channel: OnboardingVerificationChannel = "email"
    terms_accepted: bool = False
    temple_name: str | None = Field(default=None, max_length=200)
    trust_name: str | None = Field(default=None, max_length=200)
    temple_slug: str | None = Field(default=None, max_length=120)
    primary_deity: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    admin_full_name: str = Field(min_length=2, max_length=160)
    admin_email: EmailStr
    admin_phone: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def validate_names(self):
        organization_name = (self.organization_name or "").strip()
        temple_name = (self.temple_name or "").strip()
        trust_name = (self.trust_name or "").strip()
        if not organization_name and not temple_name and not trust_name:
            raise ValueError("organization_name, temple_name, or trust_name is required")
        if not self.terms_accepted:
            raise ValueError("terms_accepted is required")
        self.organization_name = organization_name or None
        self.organization_type = (self.organization_type or "").strip().upper() or None
        self.authority_designation = (self.authority_designation or "").strip() or None
        self.authority_designation_other = (self.authority_designation_other or "").strip() or None
        if (self.authority_designation or "").lower() == "other" and not self.authority_designation_other:
            raise ValueError("authority_designation_other is required when authority_designation is Other")
        self.selected_plan = (self.selected_plan or "").strip() or None
        self.plan_timing = (self.plan_timing or "").strip() or None
        self.temple_name = temple_name or None
        self.trust_name = trust_name or None
        self.temple_slug = (self.temple_slug or "").strip().lower() or None
        self.primary_deity = (self.primary_deity or "").strip() or None
        self.address = (self.address or "").strip() or None
        self.city = (self.city or "").strip() or None
        self.state = (self.state or "").strip() or None
        self.pincode = (self.pincode or "").strip() or None
        self.phone = (self.phone or "").strip() or None
        self.admin_full_name = self.admin_full_name.strip()
        self.admin_phone = (self.admin_phone or "").strip() or None
        return self


class OnboardingRequestResponse(BaseModel):
    request_id: str
    status: OnboardingStatus
    admin_email: EmailStr
    tenant_name: str
    message: str


class OnboardingRequestItem(BaseModel):
    id: str | None = None
    request_id: str
    status: OnboardingStatus
    tenant_name: str
    app_key: str | None = None
    organization_name: str | None = None
    organization_type: str | None = None
    authority_designation: str | None = None
    authority_designation_other: str | None = None
    request_intent: OnboardingIntent | None = None
    selected_plan: str | None = None
    plan_timing: str | None = None
    verification_channel: OnboardingVerificationChannel | None = None
    terms_accepted: bool | None = None
    payment_status: OnboardingPaymentStatus = "pending"
    payment_received_at: datetime | None = None
    payment_reference: str | None = None
    document_verification_status: OnboardingDocumentStatus = "pending"
    verification_notes: str | None = None
    verification_documents: list[OnboardingVerificationDocument] = Field(default_factory=list)
    verification_updated_at: datetime | None = None
    documents_deletion_due_at: datetime | None = None
    documents_deleted_at: datetime | None = None
    temple_name: str | None = None
    trust_name: str | None = None
    temple_slug: str | None = None
    city: str | None = None
    state: str | None = None
    created_at: datetime | None = None
    admin_full_name: str
    admin_email: EmailStr
    submitted_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None
    approved_tenant_id: str | None = None
    approved_admin_user_id: str | None = None
    rejection_reason: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None


class OnboardingApproveRequest(BaseModel):
    tenant_id: str | None = Field(default=None, min_length=2, max_length=64)
    initial_password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def normalize(self):
        self.tenant_id = (self.tenant_id or "").strip() or None
        self.initial_password = (self.initial_password or "").strip() or None
        return self


class OnboardingApproveResponse(BaseModel):
    request_id: str
    status: OnboardingStatus
    tenant_id: str
    admin_email: EmailStr
    admin_user_id: str
    temporary_password: str
    email_sent: bool = False
    email_error: str | None = None
    message: str


class OnboardingRejectRequest(BaseModel):
    reason: str | None = Field(default=None, min_length=3, max_length=500)
    review_notes: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def normalize(self):
        normalized_reason = (self.reason or self.review_notes or "").strip()
        if len(normalized_reason) < 3:
            raise ValueError("reason is required")
        self.reason = normalized_reason
        self.review_notes = normalized_reason
        return self


class OnboardingRejectResponse(BaseModel):
    request_id: str
    status: OnboardingStatus
    message: str


class OnboardingResendRequest(BaseModel):
    initial_password: str | None = Field(default=None, min_length=8, max_length=128)
    app_key: str | None = Field(default=None, min_length=3, max_length=40)

    @model_validator(mode="after")
    def normalize(self):
        self.initial_password = (self.initial_password or "").strip() or None
        self.app_key = (self.app_key or "").strip().lower() or None
        return self
