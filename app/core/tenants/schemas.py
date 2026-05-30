from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.modules.registry import OrganizationType

TenantStatus = Literal["active", "inactive"]


class TenantResponse(BaseModel):
    tenant_id: str
    display_name: str | None = None
    status: TenantStatus
    organization_type: OrganizationType
    enabled_modules: list[str] = Field(default_factory=list)
    app_keys: list[str] = Field(default_factory=list)
    subscription_plan: str = "free"
    created_at: datetime
    updated_at: datetime
    updated_by: str | None = None


class TenantStatusUpdateRequest(BaseModel):
    status: TenantStatus = Field(description="Set tenant lifecycle status")


class TenantEntitlementsUpdateRequest(BaseModel):
    subscription_plan: str | None = Field(default=None, min_length=2, max_length=40)
    enabled_modules: list[str] | None = None
