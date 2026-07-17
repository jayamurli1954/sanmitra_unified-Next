from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2, max_length=120)
    tenant_id: str = Field(min_length=2, max_length=64)
    role: str = Field(default="operator", min_length=3, max_length=40)
    accounting_entity_ids: list[str] = Field(default_factory=lambda: ["primary"], max_length=100)


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    tenant_id: str
    role: str
    accounting_entity_ids: list[str] = Field(default_factory=lambda: ["primary"])
    is_active: bool
    subscription_tier: str = "free"
    subscription_status: str = "active"
    accepted_terms_at: datetime | None = None
    daily_research_count: int = 0
    monthly_template_count: int = 0
    total_research_count: int = 0
    total_template_count: int = 0

