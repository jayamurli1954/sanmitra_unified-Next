from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.onboarding.service import list_onboarding_requests
from app.core.tenants.service import list_tenants
from app.db.mongo import get_collection


CORE_BILLING_TRANSACTIONS_COLLECTION = "core_billing_transactions"
TRACKED_APP_KEYS = ("legalmitra", "mandirmitra", "gruhamitra", "mitrabooks")
TRACKED_MODULES = ("temple", "housing", "business", "professional", "accounting", "gst", "inventory", "audit")
ONBOARDING_STATUSES = ("pending", "payment_pending", "payment_received", "under_review", "approved", "rejected")
ACTIONABLE_ONBOARDING_STATUSES = {"pending", "payment_received", "under_review"}
TENANT_STATUSES = ("active", "inactive")


def _counter_dict(counter: Counter, keys: tuple[str, ...] = ()) -> dict[str, int]:
    result = {key: int(counter.get(key, 0)) for key in keys}
    for key, value in counter.items():
        result.setdefault(str(key), int(value))
    return result


def _normalize_app_keys(value: Any) -> list[str]:
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value or [])
    return [str(item or "").strip().lower() for item in values if str(item or "").strip()]


def _compact_onboarding_request(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row.get("request_id") or row.get("id"),
        "status": str(row.get("status") or "pending").strip().lower(),
        "app_key": str(row.get("app_key") or "").strip().lower() or None,
        "tenant_name": row.get("tenant_name") or row.get("temple_name") or row.get("trust_name") or "",
        "organization_name": row.get("tenant_name") or row.get("temple_name") or row.get("trust_name") or "",
        "admin_email": row.get("admin_email") or "",
        "payment_status": row.get("payment_status") or "pending",
        "payment_received_at": row.get("payment_received_at"),
        "payment_reference": row.get("payment_reference"),
        "document_verification_status": row.get("document_verification_status") or "pending",
        "verification_notes": row.get("verification_notes"),
        "verification_documents": row.get("verification_documents") or [],
        "documents_deletion_due_at": row.get("documents_deletion_due_at"),
        "submitted_at": row.get("submitted_at") or row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "approved_tenant_id": row.get("approved_tenant_id"),
        "rejection_reason": row.get("rejection_reason"),
    }


def _compact_tenant(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "tenant_id": row.get("tenant_id"),
        "display_name": row.get("display_name"),
        "status": str(row.get("status") or "active").strip().lower(),
        "organization_type": row.get("organization_type"),
        "app_keys": _normalize_app_keys(row.get("app_keys")),
        "enabled_modules": [str(item).strip().lower() for item in row.get("enabled_modules") or [] if str(item).strip()],
        "subscription_plan": str(row.get("subscription_plan") or "free").strip().lower() or "free",
        "subscription_status": str(row.get("subscription_status") or row.get("status") or "active").strip().lower(),
        "hr_addon_available": bool(row.get("hr_addon_available", False)),
        "updated_at": row.get("updated_at"),
    }


def _compact_billing_transaction(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "billing_transaction",
        "tenant_id": row.get("tenant_id"),
        "display_name": row.get("customer_name") or row.get("name") or row.get("email") or row.get("payer_email") or "",
        "payer_email": row.get("email") or row.get("payer_email") or "",
        "app_key": str(row.get("app_key") or "").strip().lower() or None,
        "app_keys": [str(row.get("app_key") or "").strip().lower()] if str(row.get("app_key") or "").strip() else [],
        "subscription_plan": str(row.get("plan") or row.get("billing_plan") or row.get("subscription_plan") or "free").strip().lower() or "free",
        "subscription_status": str(row.get("subscription_status") or "active").strip().lower() or "active",
        "billing_cycle": str(row.get("billing_cycle") or "").strip().lower(),
        "amount": row.get("amount"),
        "currency": row.get("currency") or "INR",
        "subscription_started_at": row.get("subscription_started_at"),
        "subscription_expires_at": row.get("subscription_expires_at"),
        "razorpay_payment_id": row.get("razorpay_payment_id"),
    }


def _record_app_key(row: dict[str, Any]) -> str:
    app_key = str(row.get("app_key") or "").strip().lower()
    if app_key:
        return app_key
    app_keys = _normalize_app_keys(row.get("app_keys"))
    return app_keys[0] if app_keys else ""


def _subscription_identity(row: dict[str, Any]) -> tuple[str, ...]:
    tenant_id = str(row.get("tenant_id") or "").strip().lower()
    if tenant_id:
        return ("tenant", tenant_id)
    payer_email = str(row.get("payer_email") or row.get("email") or "").strip().lower()
    display_name = str(row.get("display_name") or "").strip().lower()
    return (
        "payer",
        payer_email or display_name,
        _record_app_key(row),
        str(row.get("subscription_plan") or "").strip().lower(),
    )


def _dedupe_subscription_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for row in records:
        key = _subscription_identity(row)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


async def list_billing_transactions(*, limit: int = 500) -> list[dict[str, Any]]:
    billing = get_collection(CORE_BILLING_TRANSACTIONS_COLLECTION)
    safe_limit = max(1, min(int(limit or 500), 500))
    cursor = billing.find({}).sort("subscription_started_at", -1).limit(safe_limit)
    docs = await cursor.to_list(length=safe_limit)
    return [_compact_billing_transaction(doc) for doc in docs]


async def get_platform_owner_dashboard(*, limit: int = 25) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 25), 100))
    tenants = [_compact_tenant(row) for row in await list_tenants(limit=500)]
    onboarding = [_compact_onboarding_request(row) for row in await list_onboarding_requests(limit=500)]
    billing_transactions = await list_billing_transactions(limit=500)

    onboarding_by_status = Counter(row["status"] for row in onboarding)
    onboarding_by_app: dict[str, Counter] = defaultdict(Counter)
    for row in onboarding:
        app_key = row.get("app_key") or "unknown"
        onboarding_by_app[app_key][row["status"]] += 1

    tenant_by_status = Counter(row["status"] for row in tenants)
    tenant_by_org = Counter(str(row.get("organization_type") or "UNKNOWN") for row in tenants)
    tenant_by_app = Counter()
    module_enabled = Counter()

    for tenant in tenants:
        app_keys = tenant["app_keys"] or ["unknown"]
        for app_key in app_keys:
            tenant_by_app[app_key] += 1
        for module_key in tenant["enabled_modules"]:
            module_enabled[module_key] += 1

    app_status = []
    for app_key in TRACKED_APP_KEYS:
        app_status.append(
            {
                "app_key": app_key,
                "onboarding": _counter_dict(onboarding_by_app[app_key], ONBOARDING_STATUSES),
                "tenant_count": int(tenant_by_app.get(app_key, 0)),
            }
        )

    module_status = [
        {
            "module_key": module_key,
            "tenant_count": int(module_enabled.get(module_key, 0)),
        }
        for module_key in TRACKED_MODULES
    ]

    pending_approvals = [row for row in onboarding if row["status"] in ACTIONABLE_ONBOARDING_STATUSES][:safe_limit]
    recent_onboarding = onboarding[:safe_limit]
    recent_tenants = tenants[:safe_limit]
    subscription_records = _dedupe_subscription_records([
        {
            "record_type": "tenant",
            **tenant,
        }
        for tenant in tenants
    ] + billing_transactions)
    subscription_by_plan = Counter(row["subscription_plan"] for row in subscription_records)

    return {
        "generated_at": datetime.now(timezone.utc),
        "summary": {
            "onboarding": {
                "total": len(onboarding),
                "by_status": _counter_dict(onboarding_by_status, ONBOARDING_STATUSES),
                "by_app_key": {
                    app_key: _counter_dict(counter, ONBOARDING_STATUSES)
                    for app_key, counter in sorted(onboarding_by_app.items())
                },
            },
            "tenants": {
                "total": len(tenants),
                "by_status": _counter_dict(tenant_by_status, TENANT_STATUSES),
                "by_organization_type": _counter_dict(tenant_by_org),
                "by_app_key": _counter_dict(tenant_by_app),
            },
            "subscriptions": {
                "by_plan": _counter_dict(subscription_by_plan),
            },
        },
        "app_status": app_status,
        "module_status": module_status,
        "pending_approvals": pending_approvals,
        "recent_onboarding_requests": recent_onboarding,
        "recent_onboarding": recent_onboarding,
        "recent_tenants": recent_tenants,
        "subscription_records": subscription_records[: max(safe_limit, 100)],
    }
