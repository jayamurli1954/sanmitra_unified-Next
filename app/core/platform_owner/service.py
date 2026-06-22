from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.core.onboarding.service import list_onboarding_requests
from app.core.tenants.service import list_tenants


TRACKED_APP_KEYS = ("mandirmitra", "gruhamitra", "mitrabooks")
TRACKED_MODULES = ("temple", "housing", "business", "professional", "accounting", "gst", "inventory", "audit")
ONBOARDING_STATUSES = ("pending", "approved", "rejected")
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
        "hr_addon_available": bool(row.get("hr_addon_available", False)),
        "updated_at": row.get("updated_at"),
    }


async def get_platform_owner_dashboard(*, limit: int = 25) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit or 25), 100))
    tenants = [_compact_tenant(row) for row in await list_tenants(limit=500)]
    onboarding = [_compact_onboarding_request(row) for row in await list_onboarding_requests(limit=500)]

    onboarding_by_status = Counter(row["status"] for row in onboarding)
    onboarding_by_app: dict[str, Counter] = defaultdict(Counter)
    for row in onboarding:
        app_key = row.get("app_key") or "unknown"
        onboarding_by_app[app_key][row["status"]] += 1

    tenant_by_status = Counter(row["status"] for row in tenants)
    tenant_by_org = Counter(str(row.get("organization_type") or "UNKNOWN") for row in tenants)
    tenant_by_app = Counter()
    subscription_by_plan = Counter(row["subscription_plan"] for row in tenants)
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

    pending_approvals = [row for row in onboarding if row["status"] == "pending"][:safe_limit]
    recent_onboarding = onboarding[:safe_limit]
    recent_tenants = tenants[:safe_limit]

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
        "recent_tenants": recent_tenants,
    }
