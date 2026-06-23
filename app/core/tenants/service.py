from datetime import datetime, timezone
from time import monotonic

from fastapi import HTTPException

from app.core.modules.registry import derive_enabled_modules, get_module_definition, normalize_organization_type
from app.db.mongo import get_collection

TENANTS_COLLECTION = "core_tenants"
VALID_TENANT_STATUSES = {"active", "inactive"}
VALID_SUBSCRIPTION_PLANS = {"free", "trial", "basic", "growth", "pro", "professional", "elite"}

_TENANT_INDEXES_READY = False
_ACTIVE_TENANT_CACHE_TTL_SECONDS = 10.0
_ACTIVE_TENANT_CACHE: dict[str, tuple[float, str]] = {}


async def ensure_tenants_indexes() -> None:
    global _TENANT_INDEXES_READY
    if _TENANT_INDEXES_READY:
        return

    tenants = get_collection(TENANTS_COLLECTION)
    await tenants.create_index("tenant_id", unique=True)
    await tenants.create_index([("status", 1), ("updated_at", -1)])
    _TENANT_INDEXES_READY = True


def _normalize_tenant_id(tenant_id: str | None) -> str:
    return str(tenant_id or "").strip()


def _serialize_tenant(doc: dict) -> dict:
    app_keys = doc.get("app_keys") or []
    if isinstance(app_keys, str):
        app_keys = [app_keys]
    organization_type = normalize_organization_type(doc.get("organization_type"), app_key=(app_keys[0] if app_keys else None))
    enabled_modules = derive_enabled_modules(
        organization_type=organization_type,
        explicit_modules=doc.get("enabled_modules") or [],
    )
    return {
        "tenant_id": doc.get("tenant_id"),
        "display_name": doc.get("display_name"),
        "status": doc.get("status", "active"),
        "organization_type": organization_type,
        "enabled_modules": enabled_modules,
        "app_keys": [str(key).strip().lower() for key in app_keys if str(key).strip()],
        "subscription_plan": str(doc.get("subscription_plan") or "free").strip().lower() or "free",
        # Platform-owner provisioning flag for the MitraBooks HR add-on (enterprise
        # tier). Defaults False — a tenant cannot self-enable HR; the platform owner
        # must first make it available. The tenant-admin on/off toggle lives
        # separately on MitraBooks InvoiceSettings (hr_enabled).
        "hr_addon_available": bool(doc.get("hr_addon_available", False)),
        # Platform-owner provisioning for the enterprise Cost-Centre Accounting and
        # Manufacturing add-ons (same two-level model as HR). Default False — tenants
        # cannot self-enable; the tenant-admin toggles live on InvoiceSettings
        # (cost_centre_enabled / manufacturing_enabled).
        "cost_centre_addon_available": bool(doc.get("cost_centre_addon_available", False)),
        "manufacturing_addon_available": bool(doc.get("manufacturing_addon_available", False)),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "updated_by": doc.get("updated_by"),
    }


def _set_tenant_status_cache(tenant_id: str, status: str) -> None:
    _ACTIVE_TENANT_CACHE[tenant_id] = (monotonic(), status)


def _get_tenant_status_cache(tenant_id: str) -> str | None:
    cached = _ACTIVE_TENANT_CACHE.get(tenant_id)
    if not cached:
        return None

    ts, status = cached
    if monotonic() - ts > _ACTIVE_TENANT_CACHE_TTL_SECONDS:
        _ACTIVE_TENANT_CACHE.pop(tenant_id, None)
        return None

    return status


def _normalize_enabled_modules(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    modules: list[str] = []
    for value in values or []:
        key = str(value or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            modules.append(key)
    return modules


def _validate_enabled_modules(*, organization_type: str, app_keys: list[str], enabled_modules: list[str]) -> None:
    if not enabled_modules:
        raise ValueError("enabled_modules must not be empty")
    normalized_app_keys = [str(key or "").strip().lower() for key in app_keys if str(key or "").strip()]
    if not normalized_app_keys:
        raise ValueError("tenant must have at least one app key before modules can be updated")

    for module_key in enabled_modules:
        definition = get_module_definition(module_key)
        if definition is None:
            raise ValueError(f"Unknown module: {module_key}")
        if organization_type not in definition.allowed_organization_types:
            raise ValueError(f"Module {module_key} is not available for organization_type={organization_type}")
        if not any(app_key in definition.allowed_app_keys for app_key in normalized_app_keys):
            raise ValueError(f"Module {module_key} is not available for tenant app keys")


async def ensure_tenant_exists(
    tenant_id: str,
    *,
    display_name: str | None = None,
    organization_type: str | None = None,
    enabled_modules: list[str] | None = None,
    app_keys: list[str] | None = None,
    subscription_plan: str | None = None,
    created_by: str = "system",
) -> dict:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        raise ValueError("tenant_id is required")

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)
    now = datetime.now(timezone.utc)
    normalized_org_type = normalize_organization_type(organization_type, app_key=(app_keys or [None])[0])
    derived_modules = derive_enabled_modules(
        organization_type=normalized_org_type,
        explicit_modules=enabled_modules,
    )

    default_app_keys = [str(key).strip().lower() for key in (app_keys or []) if str(key).strip()]
    default_subscription_plan = str(subscription_plan or "free").strip().lower() or "free"
    if derived_modules and (enabled_modules is not None or app_keys is not None):
        _validate_enabled_modules(
            organization_type=normalized_org_type,
            app_keys=default_app_keys,
            enabled_modules=derived_modules,
        )
    update: dict = {
        "$setOnInsert": {
            "tenant_id": normalized_tenant_id,
            "status": "active",
            "created_at": now,
        },
        "$set": {
            "updated_at": now,
            "updated_by": created_by,
        },
    }

    if display_name:
        update["$set"]["display_name"] = display_name.strip()
    if organization_type:
        update["$set"]["organization_type"] = normalized_org_type
    else:
        update["$setOnInsert"]["organization_type"] = normalized_org_type
    if enabled_modules is not None:
        update["$set"]["enabled_modules"] = derived_modules
    else:
        update["$setOnInsert"]["enabled_modules"] = derived_modules
    if app_keys is not None:
        update["$set"]["app_keys"] = default_app_keys
    else:
        update["$setOnInsert"]["app_keys"] = default_app_keys
    if subscription_plan:
        update["$set"]["subscription_plan"] = str(subscription_plan).strip().lower()
    else:
        update["$setOnInsert"]["subscription_plan"] = default_subscription_plan

    await tenants.update_one({"tenant_id": normalized_tenant_id}, update, upsert=True)
    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    _set_tenant_status_cache(normalized_tenant_id, "active")
    return _serialize_tenant(doc or {"tenant_id": normalized_tenant_id, "status": "active"})


async def ensure_seed_tenant() -> None:
    await ensure_tenant_exists(
        "seed-tenant-1",
        display_name="SanMitra Seed Tenant",
        organization_type="TEMPLE",
        enabled_modules=["temple", "accounting", "audit"],
        app_keys=["mandirmitra"],
        created_by="system",
    )


async def get_tenant(tenant_id: str) -> dict | None:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        return None

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)
    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not doc:
        return None
    return _serialize_tenant(doc)


async def list_tenants(*, status: str | None = None, limit: int = 200) -> list[dict]:
    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)

    filters: dict = {}
    if status:
        normalized_status = status.strip().lower()
        if normalized_status not in VALID_TENANT_STATUSES:
            raise ValueError("Invalid tenant status")
        filters["status"] = normalized_status

    cursor = tenants.find(filters).sort("updated_at", -1).limit(max(1, min(limit, 500)))
    docs = await cursor.to_list(length=max(1, min(limit, 500)))
    return [_serialize_tenant(doc) for doc in docs]


async def set_tenant_status(*, tenant_id: str, status: str, updated_by: str) -> dict:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    normalized_status = str(status or "").strip().lower()

    if not normalized_tenant_id:
        raise ValueError("tenant_id is required")
    if normalized_status not in VALID_TENANT_STATUSES:
        raise ValueError("Invalid tenant status")

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)

    now = datetime.now(timezone.utc)
    result = await tenants.update_one(
        {"tenant_id": normalized_tenant_id},
        {
            "$set": {
                "status": normalized_status,
                "updated_at": now,
                "updated_by": updated_by,
            }
        },
    )
    if result.matched_count == 0:
        raise KeyError("Tenant not found")

    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not doc:
        raise KeyError("Tenant not found")

    _set_tenant_status_cache(normalized_tenant_id, normalized_status)
    return _serialize_tenant(doc)


async def set_hr_addon_available(*, tenant_id: str, available: bool, updated_by: str) -> dict:
    """Platform-owner switch: make (or revoke) the MitraBooks HR add-on for a tenant.

    This is the first of the two-level HR gate. Once available, the tenant admin
    still has to turn the module on via InvoiceSettings.hr_enabled.
    """
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        raise ValueError("tenant_id is required")

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)
    now = datetime.now(timezone.utc)
    result = await tenants.update_one(
        {"tenant_id": normalized_tenant_id},
        {"$set": {"hr_addon_available": bool(available), "updated_at": now, "updated_by": updated_by}},
    )
    if result.matched_count == 0:
        raise KeyError("Tenant not found")

    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not doc:
        raise KeyError("Tenant not found")
    return _serialize_tenant(doc)


_ADDON_AVAILABLE_FLAGS = {
    "hr_addon_available",
    "cost_centre_addon_available",
    "manufacturing_addon_available",
}


async def set_addon_available(*, tenant_id: str, flag: str, available: bool, updated_by: str) -> dict:
    """Platform-owner switch to provision (or revoke) an enterprise add-on for a
    tenant — the first of the two-level gate. Generic over the addon-available
    flags; the tenant-admin still has to enable the module on InvoiceSettings.

    Manufacturing depends on cost centres, so provisioning manufacturing also
    provisions cost centres, and revoking cost centres also revokes manufacturing.
    """
    if flag not in _ADDON_AVAILABLE_FLAGS:
        raise ValueError(f"Unknown add-on flag '{flag}'")
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        raise ValueError("tenant_id is required")

    updates = {flag: bool(available)}
    if flag == "manufacturing_addon_available" and available:
        updates["cost_centre_addon_available"] = True
    if flag == "cost_centre_addon_available" and not available:
        updates["manufacturing_addon_available"] = False

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)
    now = datetime.now(timezone.utc)
    result = await tenants.update_one(
        {"tenant_id": normalized_tenant_id},
        {"$set": {**updates, "updated_at": now, "updated_by": updated_by}},
    )
    if result.matched_count == 0:
        raise KeyError("Tenant not found")
    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not doc:
        raise KeyError("Tenant not found")
    return _serialize_tenant(doc)


async def update_tenant_entitlements(
    *,
    tenant_id: str,
    subscription_plan: str | None = None,
    enabled_modules: list[str] | None = None,
    updated_by: str,
) -> dict:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        raise ValueError("tenant_id is required")

    await ensure_tenants_indexes()
    tenants = get_collection(TENANTS_COLLECTION)
    existing = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not existing:
        raise KeyError("Tenant not found")

    serialized = _serialize_tenant(existing)
    update_fields: dict = {
        "updated_at": datetime.now(timezone.utc),
        "updated_by": updated_by,
    }

    if subscription_plan is not None:
        normalized_plan = str(subscription_plan or "").strip().lower()
        if normalized_plan not in VALID_SUBSCRIPTION_PLANS:
            raise ValueError("Invalid subscription plan")
        update_fields["subscription_plan"] = normalized_plan

    if enabled_modules is not None:
        normalized_modules = _normalize_enabled_modules(enabled_modules)
        _validate_enabled_modules(
            organization_type=serialized["organization_type"],
            app_keys=serialized["app_keys"],
            enabled_modules=normalized_modules,
        )
        update_fields["enabled_modules"] = normalized_modules

    if set(update_fields) == {"updated_at", "updated_by"}:
        raise ValueError("No entitlement changes provided")

    result = await tenants.update_one(
        {"tenant_id": normalized_tenant_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise KeyError("Tenant not found")

    doc = await tenants.find_one({"tenant_id": normalized_tenant_id})
    if not doc:
        raise KeyError("Tenant not found")
    return _serialize_tenant(doc)


async def ensure_tenant_is_active(tenant_id: str | None) -> None:
    normalized_tenant_id = _normalize_tenant_id(tenant_id)
    if not normalized_tenant_id:
        return

    cached_status = _get_tenant_status_cache(normalized_tenant_id)
    if cached_status is not None:
        if cached_status != "active":
            raise HTTPException(status_code=403, detail="Tenant is inactive")
        return

    # During local startup and certain tests Mongo may be intentionally absent.
    # In those cases we skip lifecycle enforcement to avoid false negatives.
    try:
        await ensure_tenants_indexes()
        tenants = get_collection(TENANTS_COLLECTION)
    except RuntimeError:
        return

    doc = await tenants.find_one({"tenant_id": normalized_tenant_id}, {"status": 1, "tenant_id": 1})
    if not doc:
        await ensure_tenant_exists(normalized_tenant_id, created_by="system")
        return

    status = str(doc.get("status") or "active").strip().lower()
    _set_tenant_status_cache(normalized_tenant_id, status)
    if status != "active":
        raise HTTPException(status_code=403, detail="Tenant is inactive")
