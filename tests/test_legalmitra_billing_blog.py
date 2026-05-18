import inspect
import json
from datetime import datetime, timezone

import pytest

from app.core.billing.limits import get_tier_limits
from app.core.billing.service import BillingService
from app.core.billing import usage as usage_module
from app.modules.blog import service as blog_service
from app.modules.legal_compat.router import v2_template_render


class _FakeUsersCollection:
    def __init__(self, user: dict):
        self.user = user
        self.update_filter = None
        self.update_query = None

    async def find_one(self, query: dict):
        return self.user

    async def update_one(self, query: dict, update: dict):
        self.update_filter = query
        self.update_query = update


class _FakeBlogCollection:
    def __init__(self):
        self.query = None

    async def find_one(self, query: dict):
        self.query = query
        return None


def test_paid_tier_limits_are_json_safe_and_match_pricing() -> None:
    pro_limits = get_tier_limits("pro")
    basic_limits = get_tier_limits("growth")
    free_limits = get_tier_limits("free")

    assert free_limits["monthly_templates"] == 5
    assert free_limits["chat_history_retention_days"] == 30
    assert free_limits["uploaded_document_retention_days"] == 30
    assert basic_limits["monthly_templates"] == 30
    assert basic_limits["chat_history_retention_days"] == 150
    assert basic_limits["uploaded_document_retention_days"] == 150
    assert pro_limits["daily_research_queries"] is None
    assert pro_limits["monthly_templates"] == 200
    assert pro_limits["chat_history_retention_days"] == 300
    assert pro_limits["uploaded_document_retention_days"] == 300
    json.dumps(pro_limits)


def test_billing_resolves_visible_pricing_tiers() -> None:
    assert BillingService._resolve_tier({"notes": {"tier": "growth"}}, 0) == "basic"
    assert BillingService._resolve_tier({"notes": {"tier": "popular"}}, 0) == "popular"
    assert BillingService._resolve_tier({"notes": {}}, 399) == "basic"
    assert BillingService._resolve_tier({"notes": {}}, 899) == "pro"
    assert BillingService._resolve_tier({"notes": {}}, 99) == "free"


@pytest.mark.asyncio
async def test_daily_usage_reset_persists_counter_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    yesterday = datetime.now(timezone.utc).strftime("old-%Y-%m-%d")
    users = _FakeUsersCollection(
        {
            "user_id": "user-1",
            "subscription_tier": "free",
            "last_research_date": yesterday,
            "daily_research_count": 5,
        }
    )

    monkeypatch.setattr(usage_module, "get_collection", lambda name: users)

    await usage_module.check_and_increment_usage("user-1", "daily_research_queries")

    assert users.update_filter == {"user_id": "user-1"}
    assert users.update_query["$set"]["daily_research_count"] == 1
    assert "daily_research_count" not in users.update_query.get("$inc", {})
    assert users.update_query["$inc"] == {"total_research_count": 1}


@pytest.mark.asyncio
async def test_super_admin_bypasses_usage_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection(
        {
            "user_id": "owner-1",
            "role": "super_admin",
            "subscription_tier": "free",
            "last_research_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "daily_research_count": 5,
        }
    )

    monkeypatch.setattr(usage_module, "get_collection", lambda name: users)

    assert await usage_module.check_and_increment_usage("owner-1", "daily_research_queries") is True
    assert users.update_query is None


@pytest.mark.asyncio
async def test_platform_owner_token_bypasses_usage_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection(
        {
            "user_id": "owner-1",
            "role": "operator",
            "subscription_tier": "free",
            "last_research_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "daily_research_count": 5,
        }
    )

    monkeypatch.setattr(usage_module, "get_collection", lambda name: users)

    assert await usage_module.check_and_increment_usage(
        "owner-1",
        "daily_research_queries",
        actor={"role": "platform_owner"},
    ) is True
    assert users.update_query is None


@pytest.mark.asyncio
async def test_configured_super_admin_email_bypasses_usage_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection(
        {
            "user_id": "owner-1",
            "email": "owner@example.test",
            "role": "operator",
            "subscription_tier": "free",
            "last_research_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "daily_research_count": 5,
        }
    )

    class _Settings:
        SUPER_ADMIN_EMAIL = "owner@example.test"

    monkeypatch.setattr(usage_module, "get_collection", lambda name: users)
    monkeypatch.setattr(usage_module, "get_settings", lambda: _Settings())

    assert await usage_module.check_and_increment_usage("owner-1", "daily_research_queries") is True
    assert users.update_query is None


@pytest.mark.asyncio
async def test_monthly_usage_reset_persists_counter_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection(
        {
            "user_id": "user-1",
            "subscription_tier": "basic",
            "last_template_month": "old-month",
            "monthly_template_count": 30,
        }
    )

    monkeypatch.setattr(usage_module, "get_collection", lambda name: users)

    await usage_module.check_and_increment_usage("user-1", "monthly_templates")

    assert users.update_query["$set"]["monthly_template_count"] == 1
    assert "monthly_template_count" not in users.update_query.get("$inc", {})
    assert users.update_query["$inc"] == {"total_template_count": 1}


@pytest.mark.asyncio
async def test_public_blog_slug_lookup_filters_to_published(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _FakeBlogCollection()
    monkeypatch.setattr(blog_service, "get_collection", lambda name: collection)

    await blog_service.get_blog_post_by_slug("legalmitra", "draft-post")

    assert collection.query == {
        "app_key": "legalmitra",
        "slug": "draft-post",
        "is_published": True,
    }


def test_template_render_injects_current_user() -> None:
    signature = inspect.signature(v2_template_render)

    assert "current_user" in signature.parameters
