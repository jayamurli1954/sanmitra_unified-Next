"""Schemas for LegalMitra Stage 4 — Proactive Assistant."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AlertStatus = Literal["open", "snoozed", "resolved", "dismissed"]
AlertSeverity = Literal["low", "normal", "high", "urgent"]
BriefWindow = Literal["daily", "weekly", "monthly", "quarterly"]
Persona = Literal["advocate", "ca", "cs", "corporate"]

ALERT_TYPES = {
    "deadline_approaching",
    "hearing_approaching",
    "compliance_gap_missing_documents",
    "matter_awaiting_review",
    "dormant_matter",
}


class AlertUpdateRequest(BaseModel):
    status: AlertStatus | None = None
    snoozed_until: datetime | None = None


class PracticeAlertResponse(BaseModel):
    alert_id: str
    tenant_id: str
    app_key: str
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    matter_id: str | None = None
    client_id: str | None = None
    title: str
    summary: str
    due_at: date | None = None
    dedupe_key: str
    priority_score: int = 0
    suggested_actions: list[str] = Field(default_factory=list)
    recommended_action: str | None = None
    recommended_priority: str | None = None
    matter_health: int | None = None
    client_health: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    snoozed_until: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    created_at: datetime
    updated_at: datetime
    action_href: str | None = None


class PracticeAlertListResponse(BaseModel):
    items: list[PracticeAlertResponse]
    count: int


class AlertRefreshResponse(BaseModel):
    upserted: int
    resolved: int
    open_alerts: int


class NotificationResponse(BaseModel):
    notification_id: str
    tenant_id: str
    app_key: str
    user_id: str
    source_type: str
    source_id: str | None = None
    title: str
    body: str
    action_href: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    count: int
    unread_count: int


class MorningBriefGenerateRequest(BaseModel):
    persona: Persona = "advocate"
    window: BriefWindow = "daily"
    force_refresh: bool = False


class MorningBriefSections(BaseModel):
    date_context: str
    persona_context: str
    practice_health_score: int = Field(ge=0, le=100)
    practice_health_label: str
    priority_actions: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_hearings: list[dict[str, Any]] = Field(default_factory=list)
    upcoming_deadlines: list[dict[str, Any]] = Field(default_factory=list)
    matters_awaiting_review: list[dict[str, Any]] = Field(default_factory=list)
    compliance_gaps: list[dict[str, Any]] = Field(default_factory=list)
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)
    suggested_focus: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    human_review_required: bool = True


class MorningBriefResponse(BaseModel):
    brief_id: str
    tenant_id: str
    app_key: str
    user_id: str
    brief_date: date
    window: BriefWindow = "daily"
    persona: Persona = "advocate"
    practice_health_score: int
    practice_health_label: str
    sections: MorningBriefSections
    alert_ids: list[str] = Field(default_factory=list)
    matter_ids: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    advisory_notice: str
    confidence: float
    human_review_required: bool = True
    generation_strategy: str = "grounded_practice_summary"
    generated_at: datetime
    generated_by: str
    empty_practice: bool = False
