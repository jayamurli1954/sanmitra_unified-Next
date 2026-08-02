"""Schemas for LegalMitra Stage 5 — Agentic Workflows."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

CatalogStatus = Literal["mvp", "planned", "disabled"]
RunStatus = Literal["draft", "running", "awaiting_human", "completed", "cancelled", "failed"]
StepStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "awaiting_human",
    "approved",
    "rejected",
    "revised",
]
FailureClass = Literal["retryable", "requires_human", "permanent"]
RecommendedFrom = Literal["morning_brief", "alert", "manual"]


class WorkflowCatalogItem(BaseModel):
    workflow_key: str
    display_name: str
    catalog_status: CatalogStatus
    description: str = ""


class WorkflowCatalogResponse(BaseModel):
    items: list[WorkflowCatalogItem]
    count: int


class WorkflowStepDefinition(BaseModel):
    step_key: str
    adapter: str
    requires_human_gate: bool = False
    estimated_minutes: int = 5


class WorkflowDefinitionResponse(BaseModel):
    workflow_key: str
    version: int
    workflow_template: str = "general"
    display_name: str
    catalog_status: CatalogStatus
    steps: list[WorkflowStepDefinition]
    allowed_practice_areas: list[str] = Field(default_factory=list)
    enabled: bool = True


class WorkflowDefinitionListResponse(BaseModel):
    items: list[WorkflowDefinitionResponse]
    count: int


class WorkflowRunCreateRequest(BaseModel):
    workflow_key: str = "prepare_matter_response"
    workflow_template: str = "general"
    matter_id: str = Field(min_length=8, max_length=64)
    alert_id: str | None = None
    recommended_from: RecommendedFrom = "manual"
    persona: str = "advocate"


class WorkflowStepRejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class WorkflowStepResponse(BaseModel):
    step_id: str
    run_id: str
    step_key: str
    attempt: int
    status: StepStatus
    failure_class: FailureClass | None = None
    confidence: float | None = None
    estimated_minutes: int = 5
    human_review_required: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    error: str | None = None
    input_ref: str | None = None
    output_ref: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkflowRunResponse(BaseModel):
    run_id: str
    tenant_id: str
    app_key: str
    workflow_key: str
    workflow_version: int
    workflow_template: str
    matter_id: str
    client_id: str | None = None
    alert_id: str | None = None
    recommended_from: RecommendedFrom = "manual"
    status: RunStatus
    persona: str = "advocate"
    ready_to_file: bool = False
    steps: list[WorkflowStepResponse] = Field(default_factory=list)
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    total_duration_ms: int | None = None
    approval_count: int = 0
    rejection_count: int = 0
    revision_count: int = 0
    retry_count: int = 0


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunResponse]
    count: int


class WorkflowArtifactResponse(BaseModel):
    artifact_id: str
    run_id: str
    step_id: str | None = None
    artifact_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    human_review_required: bool = True
    created_at: datetime


class WorkflowArtifactListResponse(BaseModel):
    items: list[WorkflowArtifactResponse]
    count: int


class WorkflowTimelineEventResponse(BaseModel):
    event_id: str
    run_id: str
    matter_id: str | None = None
    event_type: str
    summary: str
    actor_id: str
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowTimelineListResponse(BaseModel):
    items: list[WorkflowTimelineEventResponse]
    count: int


class ReadyToFileRequest(BaseModel):
    ready_to_file: bool = True
    confirm: bool = Field(
        default=False,
        description="Must be true. Does not file or send; only marks human readiness.",
    )
