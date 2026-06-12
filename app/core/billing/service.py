import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.core.billing.pricing import PRODUCT_PRICING
from app.db.mongo import get_collection

USERS_COLLECTION = "core_users"
BILLING_COLLECTION = "core_billing_transactions"
KNOWN_TIERS = {"free", "basic", "growth", "pro", "popular"}
DEFAULT_PAYMENT_PAGE_MAP = {
    "pl_T0f5if7cZZxXYf": {
        "app_key": "legalmitra",
        "plan": "growth",
        "billing_cycle": "monthly",
        "amount_paise": 39900,
        "subscription_days": 30,
    },
    "pl_T0IIA3gIcKWr9y": {
        "app_key": "legalmitra",
        "plan": "growth",
        "billing_cycle": "yearly",
        "amount_paise": 399900,
        "subscription_days": 365,
    },
    "pl_T0mNwxh7rvpXf9": {
        "app_key": "legalmitra",
        "plan": "professional",
        "billing_cycle": "monthly",
        "amount_paise": 89900,
        "subscription_days": 30,
    },
    "pl_T0mPFYkQ3JVNkG": {
        "app_key": "legalmitra",
        "plan": "professional",
        "billing_cycle": "yearly",
        "amount_paise": 899900,
        "subscription_days": 365,
    },
}
PLAN_TO_LEGACY_USER_TIER = {
    "free": "free",
    "starter": "basic",
    "basic": "basic",
    "growth": "growth",
    "professional": "pro",
    "pro": "pro",
    "popular": "popular",
}


class BillingService:
    @staticmethod
    async def verify_webhook_signature(payload: bytes, signature: str) -> bool:
        """Verify the signature from Razorpay Webhook."""
        settings = get_settings()
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
        if not webhook_secret:
            return False

        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    @staticmethod
    def _configured_payment_page_map() -> dict:
        settings = get_settings()
        mapping = dict(DEFAULT_PAYMENT_PAGE_MAP)
        raw_mapping = getattr(settings, "RAZORPAY_PAYMENT_PAGE_MAP_JSON", "") or ""
        if not raw_mapping:
            return mapping

        try:
            configured_mapping = json.loads(raw_mapping)
        except json.JSONDecodeError:
            return mapping

        if isinstance(configured_mapping, dict):
            for page_id, page_config in configured_mapping.items():
                if isinstance(page_id, str) and isinstance(page_config, dict):
                    mapping[page_id] = page_config
        return mapping

    @staticmethod
    def _find_payment_page_id(value) -> str | None:
        if isinstance(value, dict):
            for key in (
                "payment_page_id",
                "razorpay_payment_page_id",
                "page_id",
                "payment_page",
                "payment_link_id",
            ):
                raw_value = value.get(key)
                if isinstance(raw_value, str) and raw_value.startswith("pl_"):
                    return raw_value
            for child_value in value.values():
                found = BillingService._find_payment_page_id(child_value)
                if found:
                    return found
        elif isinstance(value, list):
            for child_value in value:
                found = BillingService._find_payment_page_id(child_value)
                if found:
                    return found
        elif isinstance(value, str) and value.startswith("pl_"):
            return value
        return None

    @staticmethod
    def _payment_page_context(payload: dict, payment_entity: dict) -> tuple[str | None, dict | None]:
        page_id = BillingService._find_payment_page_id(payment_entity) or BillingService._find_payment_page_id(payload)
        if not page_id:
            return None, None
        return page_id, BillingService._configured_payment_page_map().get(page_id)

    @staticmethod
    def _resolve_tier(payment_entity: dict, amount: float) -> str:
        notes = payment_entity.get("notes", {})
        note_tier = str(notes.get("tier") or "").strip().lower()
        if note_tier in KNOWN_TIERS:
            return "basic" if note_tier == "growth" else note_tier

        if 380 <= amount <= 480 or 3800 <= amount <= 4300:
            return "basic"
        if 850 <= amount <= 1100 or 8500 <= amount <= 9500:
            return "pro"
        if 590 <= amount <= 720:
            return "pro"

        return "free"

    @staticmethod
    def _resolve_billing_cycle(payment_entity: dict, amount: float, page_config: dict | None = None) -> str:
        if page_config and page_config.get("billing_cycle"):
            return str(page_config["billing_cycle"]).strip().lower()

        notes = payment_entity.get("notes", {}) or {}
        raw_cycle = notes.get("billing_cycle") or notes.get("cycle") or notes.get("subscription_cycle")
        cycle = str(raw_cycle or "").strip().lower()
        if cycle in {"monthly", "yearly"}:
            return cycle

        if 3800 <= amount <= 4300 or 8500 <= amount <= 9500:
            return "yearly"
        return "monthly"

    @staticmethod
    def _resolve_plan(payment_entity: dict, amount: float, page_config: dict | None = None) -> str:
        if page_config and page_config.get("plan"):
            return str(page_config["plan"]).strip().lower()

        notes = payment_entity.get("notes", {}) or {}
        raw_plan = notes.get("plan") or notes.get("tier") or notes.get("subscription_plan")
        plan = str(raw_plan or "").strip().lower()
        if plan in PLAN_TO_LEGACY_USER_TIER:
            return plan
        if 380 <= amount <= 480 or 3800 <= amount <= 4300:
            return "growth"
        if 850 <= amount <= 1100 or 8500 <= amount <= 9500:
            return "professional"
        return BillingService._resolve_tier(payment_entity, amount)

    @staticmethod
    def _resolve_app_key(payment_entity: dict, page_config: dict | None = None) -> str:
        if page_config:
            configured_app_key = str(page_config.get("app_key") or "").strip().lower()
            if configured_app_key in PRODUCT_PRICING:
                return configured_app_key

        notes = payment_entity.get("notes", {}) or {}
        raw_app_key = notes.get("app_key") or notes.get("product") or notes.get("product_app_key")
        app_key = str(raw_app_key or "").strip().lower()
        if app_key in PRODUCT_PRICING:
            return app_key
        return "legalmitra"

    @staticmethod
    def _payment_timestamp(payment_entity: dict) -> datetime:
        for key in ("captured_at", "created_at"):
            raw_timestamp = payment_entity.get(key)
            if isinstance(raw_timestamp, (int, float)) and raw_timestamp > 0:
                return datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)
        return datetime.now(timezone.utc)

    @staticmethod
    def _subscription_days(billing_cycle: str, page_config: dict | None = None) -> int:
        if page_config:
            configured_days = page_config.get("subscription_days")
            if isinstance(configured_days, int) and configured_days > 0:
                return configured_days
        return 365 if billing_cycle == "yearly" else 30

    @staticmethod
    def _page_amount_matches(payment_entity: dict, page_config: dict | None = None) -> bool:
        if not page_config or "amount_paise" not in page_config:
            return True
        expected_amount = page_config.get("amount_paise")
        actual_amount = payment_entity.get("amount", 0)
        return isinstance(expected_amount, int) and actual_amount == expected_amount

    @staticmethod
    def razorpay_public_config(app_key: str) -> dict:
        normalized_app_key = str(app_key or "").strip().lower()
        if normalized_app_key not in PRODUCT_PRICING:
            raise KeyError("Unknown pricing product")

        settings = get_settings()
        return {
            "app_key": normalized_app_key,
            "provider": "razorpay",
            "merchant_account": getattr(settings, "RAZORPAY_ACCOUNT_OWNER", "Sanmita Tech Solutions"),
            "merchant_scope": getattr(settings, "RAZORPAY_MERCHANT_SCOPE", "sanmitra_platform"),
            "shared_platform_account": True,
            "supported_app_keys": sorted(PRODUCT_PRICING.keys()),
            "key_id": getattr(settings, "RAZORPAY_KEY_ID", "") or None,
            "key_id_configured": bool(getattr(settings, "RAZORPAY_KEY_ID", "")),
            "webhook_configured": bool(getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")),
        }

    @staticmethod
    async def handle_payment_success(payload: dict):
        """Handle successful payment and upgrade user tier."""
        event = payload.get("event")
        data = payload.get("payload", {})

        payment_entity = data.get("payment", {}).get("entity", {})
        email = payment_entity.get("email")

        if not email:
            return {"status": "error", "message": "No email found in payment"}

        amount = payment_entity.get("amount", 0) / 100
        payment_page_id, page_config = BillingService._payment_page_context(payload, payment_entity)
        if not BillingService._page_amount_matches(payment_entity, page_config):
            return {
                "status": "error",
                "message": "Payment amount does not match configured payment page amount",
                "razorpay_payment_page_id": payment_page_id,
            }

        app_key = BillingService._resolve_app_key(payment_entity, page_config)
        plan = BillingService._resolve_plan(payment_entity, amount, page_config)
        billing_cycle = BillingService._resolve_billing_cycle(payment_entity, amount, page_config)
        new_tier = PLAN_TO_LEGACY_USER_TIER.get(plan, BillingService._resolve_tier(payment_entity, amount))
        notes = payment_entity.get("notes", {}) or {}
        subscription_started_at = BillingService._payment_timestamp(payment_entity)
        subscription_expires_at = subscription_started_at + timedelta(
            days=BillingService._subscription_days(billing_cycle, page_config)
        )

        users = get_collection(USERS_COLLECTION)
        await users.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "subscription_tier": new_tier,
                    "subscription_status": "active",
                    "billing_app_key": app_key,
                    "billing_plan": plan,
                    "billing_cycle": billing_cycle,
                    "subscription_started_at": subscription_started_at,
                    "subscription_expires_at": subscription_expires_at,
                    "razorpay_payment_page_id": payment_page_id,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        settings = get_settings()
        billing = get_collection(BILLING_COLLECTION)
        await billing.insert_one(
            {
                "email": email.lower(),
                "amount": amount,
                "amount_paise": payment_entity.get("amount", 0),
                "currency": payment_entity.get("currency", "INR"),
                "app_key": app_key,
                "plan": plan,
                "billing_cycle": billing_cycle,
                "subscription_started_at": subscription_started_at,
                "subscription_expires_at": subscription_expires_at,
                "tenant_id": str(notes.get("tenant_id") or "").strip() or None,
                "merchant_account": getattr(settings, "RAZORPAY_ACCOUNT_OWNER", "Sanmita Tech Solutions"),
                "merchant_scope": getattr(settings, "RAZORPAY_MERCHANT_SCOPE", "sanmitra_platform"),
                "shared_platform_account": True,
                "razorpay_payment_page_id": payment_page_id,
                "razorpay_payment_id": payment_entity.get("id"),
                "razorpay_order_id": payment_entity.get("order_id"),
                "razorpay_customer_id": payment_entity.get("customer_id"),
                "event": event,
                "tier": new_tier,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return {
            "status": "success",
            "app_key": app_key,
            "plan": plan,
            "billing_cycle": billing_cycle,
            "tier": new_tier,
            "subscription_expires_at": subscription_expires_at.isoformat(),
        }


billing_service = BillingService()
