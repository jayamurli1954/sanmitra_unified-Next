import inspect
import json
from datetime import datetime, timedelta, timezone

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


class _FakeBillingCollection:
    def __init__(self):
        self.inserted = None

    async def insert_one(self, doc: dict):
        self.inserted = doc


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
    assert BillingService._resolve_plan({"notes": {}}, 399) == "growth"
    assert BillingService._resolve_plan({"notes": {}}, 3999) == "growth"
    assert BillingService._resolve_plan({"notes": {}}, 899) == "professional"
    assert BillingService._resolve_plan({"notes": {}}, 8999) == "professional"


def test_billing_public_config_uses_shared_sanmitra_razorpay_account(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        RAZORPAY_KEY_ID = "rzp_test_public"
        RAZORPAY_WEBHOOK_SECRET = "webhook-secret"
        RAZORPAY_ACCOUNT_OWNER = "Sanmita Tech Solutions"
        RAZORPAY_MERCHANT_SCOPE = "sanmitra_platform"

    monkeypatch.setattr("app.core.billing.service.get_settings", lambda: _Settings())

    config = BillingService.razorpay_public_config("mitrabooks")

    assert config["provider"] == "razorpay"
    assert config["merchant_account"] == "Sanmita Tech Solutions"
    assert config["merchant_scope"] == "sanmitra_platform"
    assert config["shared_platform_account"] is True
    assert config["key_id"] == "rzp_test_public"
    assert config["key_id_configured"] is True
    assert config["webhook_configured"] is True
    assert set(config["supported_app_keys"]) >= {"legalmitra", "mandirmitra", "gruhamitra", "mitrabooks"}


@pytest.mark.asyncio
async def test_billing_records_product_metadata_for_shared_razorpay_account(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection({"email": "owner@example.test"})
    billing = _FakeBillingCollection()

    def fake_get_collection(name: str):
        return billing if name == "core_billing_transactions" else users

    class _Settings:
        RAZORPAY_ACCOUNT_OWNER = "Sanmita Tech Solutions"
        RAZORPAY_MERCHANT_SCOPE = "sanmitra_platform"

    monkeypatch.setattr("app.core.billing.service.get_collection", fake_get_collection)
    monkeypatch.setattr("app.core.billing.service.get_settings", lambda: _Settings())

    result = await BillingService.handle_payment_success(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_123",
                        "order_id": "order_123",
                        "customer_id": "cust_123",
                        "email": "OWNER@EXAMPLE.TEST",
                        "amount": 299900,
                        "currency": "INR",
                        "notes": {
                            "app_key": "mitrabooks",
                            "plan": "growth",
                            "tenant_id": "tenant-1",
                        },
                    }
                }
            },
        }
    )

    assert result["status"] == "success"
    assert result["app_key"] == "mitrabooks"
    assert result["plan"] == "growth"
    assert result["billing_cycle"] == "monthly"
    assert result["tier"] == "growth"
    assert result["subscription_expires_at"]
    assert users.update_filter == {"email": "owner@example.test"}
    assert users.update_query["$set"]["billing_app_key"] == "mitrabooks"
    assert users.update_query["$set"]["billing_plan"] == "growth"
    assert users.update_query["$set"]["billing_cycle"] == "monthly"
    assert users.update_query["$set"]["subscription_status"] == "active"
    assert users.update_query["$set"]["subscription_expires_at"] > users.update_query["$set"]["subscription_started_at"]
    assert billing.inserted["app_key"] == "mitrabooks"
    assert billing.inserted["plan"] == "growth"
    assert billing.inserted["billing_cycle"] == "monthly"
    assert billing.inserted["tenant_id"] == "tenant-1"
    assert billing.inserted["merchant_account"] == "Sanmita Tech Solutions"
    assert billing.inserted["shared_platform_account"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("page_id", "amount_paise", "plan", "billing_cycle", "subscription_days", "expected_tier"),
    [
        ("pl_T0f5if7cZZxXYf", 39900, "growth", "monthly", 30, "growth"),
        ("pl_T0IIA3gIcKWr9y", 399900, "growth", "yearly", 365, "growth"),
        ("pl_T0mNwxh7rvpXf9", 89900, "professional", "monthly", 30, "pro"),
        ("pl_T0mPFYkQ3JVNkG", 899900, "professional", "yearly", 365, "pro"),
    ],
)
async def test_legalmitra_payment_page_mapping_sets_cycle_and_expiry(
    monkeypatch: pytest.MonkeyPatch,
    page_id: str,
    amount_paise: int,
    plan: str,
    billing_cycle: str,
    subscription_days: int,
    expected_tier: str,
) -> None:
    users = _FakeUsersCollection({"email": "jayanthimr56@gmail.com"})
    billing = _FakeBillingCollection()

    def fake_get_collection(name: str):
        return billing if name == "core_billing_transactions" else users

    class _Settings:
        RAZORPAY_ACCOUNT_OWNER = "Sanmita Tech Solutions"
        RAZORPAY_MERCHANT_SCOPE = "sanmitra_platform"
        RAZORPAY_PAYMENT_PAGE_MAP_JSON = ""

    monkeypatch.setattr("app.core.billing.service.get_collection", fake_get_collection)
    monkeypatch.setattr("app.core.billing.service.get_settings", lambda: _Settings())

    created_at = 1780572000
    result = await BillingService.handle_payment_success(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_T0gOCO2xZ5EYcl",
                        "order_id": "order_T0fzIAn3HMw8MD",
                        "email": "JAYANTHIMR56@GMAIL.COM",
                        "amount": amount_paise,
                        "currency": "INR",
                        "created_at": created_at,
                        "payment_page_id": page_id,
                        "notes": {},
                    }
                }
            },
        }
    )

    expected_start = datetime.fromtimestamp(created_at, tz=timezone.utc)
    expected_expiry = expected_start + timedelta(days=subscription_days)
    assert result["status"] == "success"
    assert result["app_key"] == "legalmitra"
    assert result["plan"] == plan
    assert result["billing_cycle"] == billing_cycle
    assert result["tier"] == expected_tier
    assert result["subscription_expires_at"] == expected_expiry.isoformat()
    assert users.update_filter == {"email": "jayanthimr56@gmail.com"}
    assert users.update_query["$set"]["billing_app_key"] == "legalmitra"
    assert users.update_query["$set"]["billing_plan"] == plan
    assert users.update_query["$set"]["billing_cycle"] == billing_cycle
    assert users.update_query["$set"]["subscription_tier"] == expected_tier
    assert users.update_query["$set"]["subscription_started_at"] == expected_start
    assert users.update_query["$set"]["subscription_expires_at"] == expected_expiry
    assert users.update_query["$set"]["razorpay_payment_page_id"] == page_id
    assert billing.inserted["razorpay_payment_page_id"] == page_id
    assert billing.inserted["billing_cycle"] == billing_cycle
    assert billing.inserted["subscription_expires_at"] == expected_expiry


@pytest.mark.asyncio
async def test_payment_page_mapping_rejects_amount_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    users = _FakeUsersCollection({"email": "payer@example.test"})
    billing = _FakeBillingCollection()

    def fake_get_collection(name: str):
        return billing if name == "core_billing_transactions" else users

    class _Settings:
        RAZORPAY_PAYMENT_PAGE_MAP_JSON = ""

    monkeypatch.setattr("app.core.billing.service.get_collection", fake_get_collection)
    monkeypatch.setattr("app.core.billing.service.get_settings", lambda: _Settings())

    result = await BillingService.handle_payment_success(
        {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_bad_amount",
                        "email": "payer@example.test",
                        "amount": 89900,
                        "payment_page_id": "pl_T0f5if7cZZxXYf",
                    }
                }
            },
        }
    )

    assert result == {
        "status": "error",
        "message": "Payment amount does not match configured payment page amount",
        "razorpay_payment_page_id": "pl_T0f5if7cZZxXYf",
    }
    assert users.update_query is None
    assert billing.inserted is None


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
