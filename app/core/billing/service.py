import hashlib
import hmac
from datetime import datetime, timezone

from app.config import get_settings
from app.core.billing.pricing import PRODUCT_PRICING
from app.db.mongo import get_collection

USERS_COLLECTION = "core_users"
BILLING_COLLECTION = "core_billing_transactions"
KNOWN_TIERS = {"free", "basic", "growth", "pro", "popular"}
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
    def _resolve_app_key(payment_entity: dict) -> str:
        notes = payment_entity.get("notes", {}) or {}
        raw_app_key = notes.get("app_key") or notes.get("product") or notes.get("product_app_key")
        app_key = str(raw_app_key or "").strip().lower()
        if app_key in PRODUCT_PRICING:
            return app_key
        return "legalmitra"

    @staticmethod
    def _resolve_plan(payment_entity: dict, amount: float) -> str:
        notes = payment_entity.get("notes", {}) or {}
        raw_plan = notes.get("plan") or notes.get("tier") or notes.get("subscription_plan")
        plan = str(raw_plan or "").strip().lower()
        if plan in PLAN_TO_LEGACY_USER_TIER:
            return plan
        return BillingService._resolve_tier(payment_entity, amount)

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
        app_key = BillingService._resolve_app_key(payment_entity)
        plan = BillingService._resolve_plan(payment_entity, amount)
        new_tier = PLAN_TO_LEGACY_USER_TIER.get(plan, BillingService._resolve_tier(payment_entity, amount))
        notes = payment_entity.get("notes", {}) or {}

        users = get_collection(USERS_COLLECTION)
        await users.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "subscription_tier": new_tier,
                    "subscription_status": "active",
                    "billing_app_key": app_key,
                    "billing_plan": plan,
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
                "tenant_id": str(notes.get("tenant_id") or "").strip() or None,
                "merchant_account": getattr(settings, "RAZORPAY_ACCOUNT_OWNER", "Sanmita Tech Solutions"),
                "merchant_scope": getattr(settings, "RAZORPAY_MERCHANT_SCOPE", "sanmitra_platform"),
                "shared_platform_account": True,
                "razorpay_payment_id": payment_entity.get("id"),
                "razorpay_order_id": payment_entity.get("order_id"),
                "razorpay_customer_id": payment_entity.get("customer_id"),
                "event": event,
                "tier": new_tier,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return {"status": "success", "app_key": app_key, "plan": plan, "tier": new_tier}


billing_service = BillingService()
