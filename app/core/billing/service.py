import hashlib
import hmac
from datetime import datetime, timezone

from app.config import get_settings
from app.db.mongo import get_collection

USERS_COLLECTION = "core_users"
BILLING_COLLECTION = "core_billing_transactions"
KNOWN_TIERS = {"free", "basic", "growth", "pro", "popular"}


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
    async def handle_payment_success(payload: dict):
        """Handle successful payment and upgrade user tier."""
        event = payload.get("event")
        data = payload.get("payload", {})

        payment_entity = data.get("payment", {}).get("entity", {})
        email = payment_entity.get("email")

        if not email:
            return {"status": "error", "message": "No email found in payment"}

        amount = payment_entity.get("amount", 0) / 100
        new_tier = BillingService._resolve_tier(payment_entity, amount)

        users = get_collection(USERS_COLLECTION)
        await users.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "subscription_tier": new_tier,
                    "subscription_status": "active",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        billing = get_collection(BILLING_COLLECTION)
        await billing.insert_one(
            {
                "email": email.lower(),
                "amount": amount,
                "razorpay_payment_id": payment_entity.get("id"),
                "event": event,
                "tier": new_tier,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return {"status": "success", "tier": new_tier}


billing_service = BillingService()
