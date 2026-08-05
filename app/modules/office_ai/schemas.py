from __future__ import annotations

from typing import Literal

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
