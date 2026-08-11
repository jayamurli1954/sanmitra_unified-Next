from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=4000)
    due_date: str | None = None
    status: Literal["open", "done", "cancelled"] = "open"


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=4000)
    due_date: str | None = None
    status: Literal["open", "done", "cancelled"] | None = None
    change_reason: str | None = Field(default=None, max_length=500)


class TaskGenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    persist: bool = False


class EmailCreateRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)


class EmailSummarizeRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)
    persist: bool = True
    create_tasks: bool = True


class BriefGenerateRequest(BaseModel):
    include_tasks: bool = True
    include_emails: bool = True
    include_calendar: bool = True
    include_meeting_notes: bool = True


class CalendarEventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    starts_at: str = Field(min_length=1, max_length=64)
    ends_at: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=300)
    raw_text: str | None = Field(default=None, max_length=20000)
    linked_note_id: str | None = None


class CalendarEventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    starts_at: str | None = Field(default=None, max_length=64)
    ends_at: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=300)


class CalendarParseRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)
    persist: bool = True


class MeetingNoteCreateRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)
    linked_event_id: str | None = None


class MeetingNoteSummarizeRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=50000)
    persist: bool = True
    create_tasks: bool = True
    linked_event_id: str | None = None


class ProposalListQuery(BaseModel):
    status: (
        Literal[
            "draft",
            "pending",
            "confirmed",
            "awaiting_checker",
            "applied",
            "failed",
            "dismissed",
            "expired",
            "open",
        ]
        | None
    ) = "pending"
    limit: int = Field(default=50, ge=1, le=100)


class PolicyEvaluateRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=80)
    target_module: str = Field(default="office_ai", max_length=80)
    intent: Literal["propose", "confirm", "approve", "execute", "start_workflow"] = "confirm"
    required_feature: str | None = Field(default=None, max_length=80)
    proposal_id: str | None = Field(default=None, max_length=64)
    maker_id: str | None = Field(default=None, max_length=120)
    checker_id: str | None = Field(default=None, max_length=120)
    allow_self_approval: bool = False
    approval_expiry_hours: int = Field(default=72, ge=1, le=720)


class WorkflowStepInput(BaseModel):
    step_id: str | None = Field(default=None, max_length=80)
    action_type: str = Field(min_length=1, max_length=80)
    payload: dict = Field(default_factory=dict)


class WorkflowTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    template_key: str | None = Field(default=None, max_length=120)
    continue_on_failure: bool = False
    steps: list[WorkflowStepInput] = Field(min_length=1, max_length=50)


class WorkflowRunStartRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=64)
    trigger_source: Literal["proposal", "manual", "scheduled", "api"] = "manual"
    idempotency_key: str | None = Field(default=None, max_length=200)
    proposal_id: str | None = Field(default=None, max_length=64)


class MISPackCreateRequest(BaseModel):
    pack_key: str = Field(min_length=1, max_length=80)
    period: str = Field(min_length=1, max_length=32, description="e.g. 2026-07 or FY2025-26")
    ingestion_path: Literal["excel_import", "mitrabooks", "zoho", "tally", "manual"] = "manual"
    revision: int = Field(default=1, ge=1, le=999)
    supersedes_pack_id: str | None = Field(default=None, max_length=64)


class MISFactInput(BaseModel):
    entity_type: Literal["pnl_line", "bs_line", "cash_summary", "aging_bucket", "kpi", "party"]
    period: str | None = Field(default=None, max_length=32)
    as_of: str | None = Field(default=None, max_length=32)
    source_system: str = Field(default="manual", max_length=40)
    source_id: str | None = Field(default=None, max_length=200)
    source_ref: str | None = Field(default=None, max_length=500)
    amount_decimal: str | None = Field(default=None, max_length=40)
    amount_minor: int | None = None
    currency: str = Field(default="INR", max_length=8)
    value: str | float | int | bool | None = None
    dimensions: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    fact_id: str | None = Field(default=None, max_length=64)


class MISFactsInsertRequest(BaseModel):
    facts: list[MISFactInput] = Field(min_length=1, max_length=500)


class MISPackReconcileRequest(BaseModel):
    data_quality_score: int | None = Field(default=None, ge=0, le=100)
    data_quality_breakdown: dict[str, Any] | None = None
