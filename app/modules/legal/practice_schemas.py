"""Pydantic schemas for LegalMitra Stage 3 — Clients, Matters, Documents, Timeline, Briefs."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class MatterStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PENDING = "pending"
    ON_HOLD = "on_hold"
    CLOSED = "closed"
    ARCHIVED = "archived"


MATTER_STATUS_VALUES = {s.value for s in MatterStatus}

# Allowed transitions (same-status updates always allowed via other fields).
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    MatterStatus.DRAFT.value: {
        MatterStatus.ACTIVE.value,
        MatterStatus.PENDING.value,
        MatterStatus.ON_HOLD.value,
        MatterStatus.ARCHIVED.value,
    },
    MatterStatus.ACTIVE.value: {
        MatterStatus.PENDING.value,
        MatterStatus.ON_HOLD.value,
        MatterStatus.CLOSED.value,
        MatterStatus.ARCHIVED.value,
    },
    MatterStatus.PENDING.value: {
        MatterStatus.ACTIVE.value,
        MatterStatus.ON_HOLD.value,
        MatterStatus.CLOSED.value,
        MatterStatus.ARCHIVED.value,
    },
    MatterStatus.ON_HOLD.value: {
        MatterStatus.ACTIVE.value,
        MatterStatus.PENDING.value,
        MatterStatus.CLOSED.value,
        MatterStatus.ARCHIVED.value,
    },
    MatterStatus.CLOSED.value: {
        MatterStatus.ARCHIVED.value,
        MatterStatus.ACTIVE.value,  # reopen with audit
    },
    MatterStatus.ARCHIVED.value: {
        MatterStatus.ACTIVE.value,  # explicit reopen
    },
}

ClientType = Literal["individual", "organization"]
ClientStatus = Literal["active", "archived"]
MatterPriority = Literal["low", "normal", "high", "urgent"]

PRACTICE_AREA_PREFIXES: dict[str, str] = {
    "litigation": "LIT",
    "gst": "GST",
    "income_tax": "IT",
    "secretarial": "CS",
    "contract": "CTR",
    "advisory": "ADV",
    "compliance": "CMP",
    "general": "LM",
}


# ── Clients ──────────────────────────────────────────────────────────────────


class ClientCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=200)
    client_type: ClientType = "organization"
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    pan: str | None = Field(default=None, max_length=10)
    gstin: str | None = Field(default=None, max_length=15)
    address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    status: ClientStatus = "active"

    @field_validator("pan")
    @classmethod
    def normalize_pan(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return str(value).strip().upper()

    @field_validator("gstin")
    @classmethod
    def normalize_gstin(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return str(value).strip().upper()


class ClientUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=200)
    client_type: ClientType | None = None
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    pan: str | None = Field(default=None, max_length=10)
    gstin: str | None = Field(default=None, max_length=15)
    address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    status: ClientStatus | None = None

    @field_validator("pan")
    @classmethod
    def normalize_pan(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not str(value).strip():
            return None
        return str(value).strip().upper()

    @field_validator("gstin")
    @classmethod
    def normalize_gstin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not str(value).strip():
            return None
        return str(value).strip().upper()


class ClientResponse(BaseModel):
    client_id: str
    tenant_id: str
    app_key: str
    display_name: str
    client_type: ClientType
    email: str | None = None
    phone: str | None = None
    pan: str | None = None
    gstin: str | None = None
    address: str | None = None
    notes: str | None = None
    status: ClientStatus
    created_by: str
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    count: int


# ── Matters ──────────────────────────────────────────────────────────────────


class MatterCreateRequest(BaseModel):
    client_id: str = Field(min_length=8, max_length=64)
    title: str = Field(min_length=3, max_length=200)
    matter_type: str = Field(default="engagement", min_length=2, max_length=60)
    status: MatterStatus = MatterStatus.DRAFT
    jurisdiction: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    # Reserved / future-proof optional fields (accepted now, lightly used).
    assigned_users: list[str] = Field(default_factory=list, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=40)
    priority: MatterPriority = "normal"
    practice_area: str | None = Field(default=None, max_length=60)
    court: str | None = Field(default=None, max_length=200)
    opposite_party: str | None = Field(default=None, max_length=200)
    billing_reference: str | None = Field(default=None, max_length=120)
    case_number: str | None = Field(default=None, max_length=120)
    issues: list[str] = Field(default_factory=list, max_length=40)
    next_hearing_date: date | None = None
    next_deadline_date: date | None = None

    @field_validator("issues")
    @classmethod
    def normalize_issues(cls, value: list[str] | None) -> list[str]:
        cleaned: list[str] = []
        for item in value or []:
            text = str(item or "").strip()
            if text and text not in cleaned:
                cleaned.append(text[:500])
            if len(cleaned) >= 40:
                break
        return cleaned


class MatterUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    matter_type: str | None = Field(default=None, min_length=2, max_length=60)
    status: MatterStatus | None = None
    jurisdiction: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    assigned_users: list[str] | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=40)
    priority: MatterPriority | None = None
    practice_area: str | None = Field(default=None, max_length=60)
    court: str | None = Field(default=None, max_length=200)
    opposite_party: str | None = Field(default=None, max_length=200)
    billing_reference: str | None = Field(default=None, max_length=120)
    case_number: str | None = Field(default=None, max_length=120)
    issues: list[str] | None = Field(default=None, max_length=40)
    next_hearing_date: date | None = None
    next_deadline_date: date | None = None

    @field_validator("issues")
    @classmethod
    def normalize_issues(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text not in cleaned:
                cleaned.append(text[:500])
            if len(cleaned) >= 40:
                break
        return cleaned


class MatterResponse(BaseModel):
    matter_id: str
    matter_number: str
    tenant_id: str
    app_key: str
    client_id: str
    client_name: str | None = None
    title: str
    matter_type: str
    status: str
    jurisdiction: str | None = None
    description: str | None = None
    assigned_users: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    priority: str = "normal"
    practice_area: str | None = None
    court: str | None = None
    opposite_party: str | None = None
    billing_reference: str | None = None
    case_number: str | None = None
    issues: list[str] = Field(default_factory=list)
    next_hearing_date: date | None = None
    next_deadline_date: date | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class MatterListResponse(BaseModel):
    items: list[MatterResponse]
    count: int


# ── Documents ────────────────────────────────────────────────────────────────


DocCustodySource = Literal["manual_register", "chamber_sync"]
DocOcrStatus = Literal["none", "pending", "done", "failed", "not_applicable"]
DocExtractStatus = Literal["none", "pending", "done", "failed"]

DOC_CLASSIFICATION_VALUES = {
    "court_order",
    "notice",
    "affidavit",
    "petition",
    "evidence",
    "contract",
    "tax_notice",
    "invoice",
    "identity",
    "board_resolution",
    "general",
    "unclassified",
}


class MatterDocumentCreateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=260)
    doc_type: str = Field(default="general", min_length=2, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)
    storage_ref: str | None = Field(default=None, max_length=500)
    content_hash: str | None = Field(default=None, max_length=128)
    custody_source: DocCustodySource = "manual_register"
    version: int = Field(default=1, ge=1, le=9999)
    page_count: int | None = Field(default=None, ge=1, le=100000)
    language: str | None = Field(default=None, max_length=40)
    ocr_status: DocOcrStatus = "none"
    classification: str | None = Field(default=None, max_length=60)
    extract_status: DocExtractStatus = "none"
    ai_generated: bool = False
    human_review_required: bool = True

    @field_validator("content_hash")
    @classmethod
    def normalize_hash(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return str(value).strip().lower()

    @field_validator("classification")
    @classmethod
    def normalize_classification(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        return key[:60]


class MatterDocumentResponse(BaseModel):
    document_id: str
    matter_id: str
    tenant_id: str
    app_key: str
    filename: str
    doc_type: str
    notes: str | None = None
    storage_ref: str | None = None
    content_hash: str | None = None
    custody_source: str = "manual_register"
    version: int = 1
    page_count: int | None = None
    language: str | None = None
    ocr_status: str = "none"
    classification: str | None = None
    extract_status: str = "none"
    ai_generated: bool = False
    human_review_required: bool = True
    created_by: str
    created_at: datetime


class MatterDocumentListResponse(BaseModel):
    items: list[MatterDocumentResponse]
    count: int


# ── Timeline ─────────────────────────────────────────────────────────────────


class TimelineEventCreateRequest(BaseModel):
    event_type: str = Field(min_length=2, max_length=60)
    summary: str = Field(min_length=2, max_length=1000)
    occurred_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelineEventResponse(BaseModel):
    event_id: str
    matter_id: str
    tenant_id: str
    app_key: str
    event_type: str
    summary: str
    actor_id: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TimelineListResponse(BaseModel):
    items: list[TimelineEventResponse]
    count: int


# ── Matter briefs ────────────────────────────────────────────────────────────


class MatterBriefSections(BaseModel):
    matter_overview: str
    key_facts: list[str] = Field(default_factory=list)
    applicable_law: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    documents_reviewed: list[str] = Field(default_factory=list)
    current_status: str
    risks: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    human_review_required: bool = True


class MatterBriefResponse(BaseModel):
    brief_id: str
    matter_id: str
    tenant_id: str
    app_key: str
    sections: MatterBriefSections
    sources: list[dict[str, Any]] = Field(default_factory=list)
    advisory_notice: str
    generated_by: str
    generated_at: datetime
    generation_strategy: str = "grounded_matter_summary"


class MatterBriefGenerateRequest(BaseModel):
    include_timeline: bool = True
    include_documents: bool = True
    notes_for_brief: str | None = Field(default=None, max_length=2000)


# ── Document custody (P0) ────────────────────────────────────────────────────


class DocCustodyMode(str, Enum):
    """Stable enum keys. UI display names live in DOC_CUSTODY_DISPLAY_NAMES."""

    CLOUD_MINIMIZED = "cloud_minimized"  # Personal Practice
    CHAMBER_LAN = "chamber_lan"  # Chamber LAN


DOC_CUSTODY_MODE_VALUES = {m.value for m in DocCustodyMode}

DOC_CUSTODY_DISPLAY_NAMES: dict[str, str] = {
    DocCustodyMode.CLOUD_MINIMIZED.value: "Personal Practice",
    DocCustodyMode.CHAMBER_LAN.value: "Chamber LAN",
}


class DocCustodySettingsResponse(BaseModel):
    tenant_id: str
    app_key: str
    doc_custody_mode: str
    display_name: str
    doc_cloud_originals_opt_in: bool = False
    chamber_connector_enabled: bool = False
    extract_retention_days: int = 365
    onboarding_answered: bool = False
    updated_at: datetime | None = None
    updated_by: str | None = None
    can_manage: bool = False
    onboarding_question: str
    mode_guidance: dict[str, str] = Field(default_factory=dict)


class DocCustodySettingsUpdateRequest(BaseModel):
    doc_custody_mode: DocCustodyMode | None = None
    doc_cloud_originals_opt_in: bool | None = None
    chamber_connector_enabled: bool | None = None
    extract_retention_days: int | None = Field(default=None, ge=1, le=3650)
    onboarding_answered: bool | None = None


# ── Matter extracts / chunks (P2) ─────────────────────────────────────────────


class MatterExtractIngestRequest(BaseModel):
    extract_text: str = Field(min_length=1, max_length=80_000)
    approve: bool = False
    authorize_external_provider: bool = False


class MatterExtractResponse(BaseModel):
    extract_id: str
    matter_id: str
    document_id: str
    tenant_id: str
    app_key: str
    source_kind: str = "matter_paper"
    content_hash: str
    extract_text: str
    approval_status: str
    retention_tier: str = "warm"
    expires_at: datetime | None = None
    provider_used: str = "none"
    created_by: str
    created_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    human_review_required: bool = True


class MatterChunkResponse(BaseModel):
    chunk_id: str
    matter_id: str
    document_id: str
    extract_id: str
    tenant_id: str
    app_key: str
    source_kind: str = "matter_paper"
    chunk_index: int
    text: str
    token_count: int = 0
    approval_status: str
    expires_at: datetime | None = None
    created_at: datetime


class MatterExtractIngestResponse(BaseModel):
    deduped: bool = False
    extract: MatterExtractResponse
    chunks: list[MatterChunkResponse] = Field(default_factory=list)
    suggestions: dict[str, Any] = Field(default_factory=dict)
    advisory_notice: str = (
        "Suggestions are heuristic only. An advocate must review before apply. "
        "Advisory working product — not final legal advice."
    )


class MatterExtractListResponse(BaseModel):
    items: list[MatterExtractResponse]
    count: int


class MatterChunkListResponse(BaseModel):
    items: list[MatterChunkResponse]
    count: int


class CaseCardSuggestResponse(BaseModel):
    extract_id: str
    matter_id: str
    suggestions: dict[str, Any] = Field(default_factory=dict)
    human_review_required: bool = True
    advisory_notice: str


class CaseCardApplyRequest(BaseModel):
    """Explicit field map only — never silent overwrite of advocate-edited fields."""

    fields: dict[str, Any] = Field(default_factory=dict)


class RetentionDryRunResponse(BaseModel):
    dry_run: bool = True
    as_of: datetime
    expired_extract_count: int = 0
    expired_chunk_count: int = 0
    expired_extracts: list[dict[str, Any]] = Field(default_factory=list)
    advisory_notice: str


# ── Dashboard ────────────────────────────────────────────────────────────────


class PracticeDashboardResponse(BaseModel):
    active_matters: int
    pending_matters: int
    awaiting_review: int
    upcoming_hearings: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_deadlines: list[dict[str, Any]] = Field(default_factory=list)
    recent_clients: list[dict[str, Any]] = Field(default_factory=list)
    recent_briefs: list[dict[str, Any]] = Field(default_factory=list)
    recent_documents: list[dict[str, Any]] = Field(default_factory=list)
    fees_outstanding: str = "—"
    data_source: str = "live"
    # Stage 4 proactive enrichments (optional / non-breaking).
    open_alerts: int = 0
    practice_health_score: int | None = None
    practice_health_label: str | None = None
    priority_alerts: list[dict[str, Any]] = Field(default_factory=list)
    # P0 document custody identity (summary for Tracker badge).
    doc_custody: dict[str, Any] | None = None
