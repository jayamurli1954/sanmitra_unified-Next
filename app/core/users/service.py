from datetime import datetime, timezone
from uuid import uuid4

from pymongo.errors import DuplicateKeyError, OperationFailure

from app.config import get_settings
from app.core.auth.security import hash_password
from app.core.tenants.context import get_app_key, resolve_app_key
from app.core.tenants.service import ensure_tenant_exists
from app.db.mongo import get_collection

USERS_COLLECTION = "core_users"


def _password_provider_subject(email: str) -> str:
    return f"password:{email.strip().lower()}"


def _mobile_provider_subject(mobile: str) -> str:
    return f"mobile:{mobile.strip()}"


async def ensure_users_indexes() -> None:
    users = get_collection(USERS_COLLECTION)
    await users.create_index("email", unique=True)
    await users.create_index([("app_key", 1), ("tenant_id", 1), ("role", 1)])
    await users.create_index([("tenant_id", 1), ("role", 1)])
    # Prefer scoped uniqueness for provider subject. Older MongoDB versions may
    # reject some partial index expressions; fall back to sparse uniqueness.
    try:
        await users.create_index(
            [("auth_provider", 1), ("provider_subject", 1)],
            unique=True,
            partialFilterExpression={"provider_subject": {"$exists": True}},
        )
    except OperationFailure:
        await users.create_index("provider_subject", unique=True, sparse=True)

    # Mobile login identity (optional for users created before OTP flow).
    try:
        await users.create_index(
            "mobile",
            unique=True,
            partialFilterExpression={"mobile": {"$exists": True}},
        )
    except OperationFailure:
        await users.create_index("mobile", unique=True, sparse=True)


async def ensure_seed_user() -> None:
    await ensure_users_indexes()
    users = get_collection(USERS_COLLECTION)

    seed_email = "admin@sanmitra.local"
    existing = await users.find_one({"email": seed_email})
    if existing:
        return

    await ensure_tenant_exists(
        "seed-tenant-1",
        display_name="SanMitra Seed Tenant",
        organization_type="TEMPLE",
        app_keys=["mandirmitra"],
        created_by="system",
    )

    now = datetime.now(timezone.utc)
    seed_doc = {
        "user_id": "seed-user-1",
        "email": seed_email,
        "full_name": "SanMitra Admin",
        "tenant_id": "seed-tenant-1",
        "app_key": resolve_app_key("mandirmitra"),
        "role": "tenant_admin",
        "hashed_password": hash_password("admin123"),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(seed_email),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    await users.insert_one(seed_doc)


async def ensure_super_admin_user() -> None:
    settings = get_settings()
    if not settings.SUPER_ADMIN_BOOTSTRAP:
        return

    email = str(settings.SUPER_ADMIN_EMAIL or "").strip().lower()
    password = str(settings.SUPER_ADMIN_PASSWORD or "").strip()
    full_name = str(settings.SUPER_ADMIN_FULL_NAME or "SanMitra Super Admin").strip() or "SanMitra Super Admin"
    tenant_id = str(settings.SUPER_ADMIN_TENANT_ID or "seed-tenant-1").strip() or "seed-tenant-1"
    uses_shared_seed_tenant = tenant_id == "seed-tenant-1"

    if not email or "@" not in email:
        return
    if len(password) < 6:
        return

    await ensure_users_indexes()
    await ensure_tenant_exists(
        tenant_id,
        display_name="SanMitra Seed Tenant" if uses_shared_seed_tenant else "SanMitra Platform",
        organization_type="TEMPLE" if uses_shared_seed_tenant else "BUSINESS",
        enabled_modules=["temple", "accounting", "audit"] if uses_shared_seed_tenant else None,
        app_keys=["mandirmitra"] if uses_shared_seed_tenant else ["gruhamitra", "mandirmitra", "mitrabooks", "legalmitra", "investmitra"],
        created_by="system",
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)

    existing = await users.find_one({"email": email})
    if existing:
        update_fields = {
            "role": "super_admin",
            "app_key": resolve_app_key(getattr(settings, "DEFAULT_APP_KEY", "mandirmitra")),
            "is_active": True,
            "updated_at": now,
        }
        if not str(existing.get("full_name") or "").strip():
            update_fields["full_name"] = full_name
        if not str(existing.get("tenant_id") or "").strip():
            update_fields["tenant_id"] = tenant_id
        if str(existing.get("auth_provider") or "").strip() == "password":
            update_fields["provider_subject"] = _password_provider_subject(email)
        if not existing.get("hashed_password"):
            update_fields["hashed_password"] = hash_password(password)
            update_fields["auth_provider"] = "password"
            update_fields["provider_subject"] = _password_provider_subject(email)

        await users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
        return

    doc = {
        "user_id": str(uuid4()),
        "email": email,
        "full_name": full_name,
        "tenant_id": tenant_id,
        "app_key": resolve_app_key(getattr(settings, "DEFAULT_APP_KEY", "mandirmitra")),
        "role": "super_admin",
        "hashed_password": hash_password(password),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(email),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    await users.insert_one(doc)


async def ensure_demo_mitrabooks_user(
    *,
    email: str,
    password: str,
    full_name: str = "Demo MitraBooks Admin",
    tenant_id: str = "demo-mitrabooks-business",
    display_name: str = "Local MitraBooks Demo Business",
) -> dict | None:
    normalized_email = str(email or "").strip().lower()
    normalized_password = str(password or "").strip()
    normalized_tenant_id = str(tenant_id or "").strip() or "demo-mitrabooks-business"
    normalized_full_name = str(full_name or "Demo MitraBooks Admin").strip() or "Demo MitraBooks Admin"
    normalized_display_name = str(display_name or "Local MitraBooks Demo Business").strip() or "Local MitraBooks Demo Business"

    if not normalized_email or "@" not in normalized_email:
        return None
    if len(normalized_password) < 6:
        return None

    await ensure_users_indexes()
    await ensure_tenant_exists(
        normalized_tenant_id,
        display_name=normalized_display_name,
        organization_type="BUSINESS",
        enabled_modules=["business", "accounting", "gst", "inventory", "audit"],
        app_keys=["mitrabooks"],
        subscription_plan="pro",
        created_by="local-demo-bootstrap",
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)
    existing = await users.find_one({"email": normalized_email})
    user_id = str(existing.get("user_id") or uuid4()) if existing else str(uuid4())
    update_fields = {
        "user_id": user_id,
        "email": normalized_email,
        "full_name": normalized_full_name,
        "tenant_id": normalized_tenant_id,
        "app_key": resolve_app_key("mitrabooks"),
        "role": "tenant_admin",
        "hashed_password": hash_password(normalized_password),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(normalized_email),
        "is_active": True,
        "subscription_tier": "pro",
        "subscription_status": "active",
        "accepted_terms_at": existing.get("accepted_terms_at") if existing else None,
        "query_usage_count": existing.get("query_usage_count", 0) if existing else 0,
        "updated_at": now,
    }
    if existing:
        await users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
    else:
        await users.insert_one({**update_fields, "created_at": now})

    return {
        "user_id": user_id,
        "email": normalized_email,
        "full_name": normalized_full_name,
        "tenant_id": normalized_tenant_id,
        "app_key": "mitrabooks",
        "role": "tenant_admin",
        "is_active": True,
        "subscription_tier": "pro",
        "subscription_status": "active",
    }


async def ensure_demo_gruhamitra_user(
    *,
    email: str,
    password: str,
    full_name: str = "Demo GruhaMitra Admin",
    tenant_id: str = "gruhamitra-demo-society",
    role: str = "tenant_admin",
) -> dict | None:
    normalized_email = str(email or "").strip().lower()
    normalized_password = str(password or "").strip()
    normalized_tenant_id = str(tenant_id or "").strip() or "gruhamitra-demo-society"
    normalized_full_name = str(full_name or "Demo GruhaMitra Admin").strip() or "Demo GruhaMitra Admin"
    normalized_role = str(role or "tenant_admin").strip() or "tenant_admin"

    if not normalized_email or "@" not in normalized_email:
        return None
    if len(normalized_password) < 8:
        return None

    await ensure_users_indexes()
    await ensure_tenant_exists(
        normalized_tenant_id,
        display_name="GruhaMitra Demo Society",
        organization_type="HOUSING",
        enabled_modules=["housing", "accounting", "audit"],
        app_keys=["gruhamitra"],
        subscription_plan="growth",
        created_by="gruhamitra-demo-bootstrap",
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)
    existing = await users.find_one({"email": normalized_email})
    user_id = str(existing.get("user_id") or uuid4()) if existing else str(uuid4())
    update_fields = {
        "user_id": user_id,
        "email": normalized_email,
        "full_name": normalized_full_name,
        "tenant_id": normalized_tenant_id,
        "app_key": resolve_app_key("gruhamitra"),
        "role": normalized_role,
        "hashed_password": hash_password(normalized_password),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(normalized_email),
        "is_active": True,
        "subscription_tier": "growth",
        "subscription_status": "active",
        "accepted_terms_at": existing.get("accepted_terms_at") if existing else None,
        "query_usage_count": existing.get("query_usage_count", 0) if existing else 0,
        "updated_at": now,
    }
    if existing:
        await users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
    else:
        await users.insert_one({**update_fields, "created_at": now})

    return {
        "user_id": user_id,
        "email": normalized_email,
        "full_name": normalized_full_name,
        "tenant_id": normalized_tenant_id,
        "app_key": "gruhamitra",
        "role": normalized_role,
        "is_active": True,
        "subscription_tier": "growth",
        "subscription_status": "active",
    }


async def get_user_by_email(email: str):
    users = get_collection(USERS_COLLECTION)
    normalized = email.strip().lower()
    try:
        return await users.find_one({"email": normalized, "is_active": True})
    except Exception as exc:
        # Surface datastore connectivity failures as controlled 503s from callers.
        raise RuntimeError(f"MongoDB user lookup failed: {exc}") from exc


async def get_user_by_mobile(mobile: str):
    users = get_collection(USERS_COLLECTION)
    normalized = mobile.strip()
    try:
        return await users.find_one({"mobile": normalized, "is_active": True})
    except Exception as exc:
        raise RuntimeError(f"MongoDB mobile user lookup failed: {exc}") from exc


async def create_user(
    *,
    email: str,
    password: str,
    full_name: str,
    tenant_id: str,
    role: str,
    app_key: str | None = None,
):
    await ensure_users_indexes()

    normalized_email = email.strip().lower()
    normalized_tenant_id = tenant_id.strip()
    normalized_app_key = resolve_app_key(app_key or get_app_key())
    await ensure_tenant_exists(
        normalized_tenant_id,
        organization_type=None,
        app_keys=[normalized_app_key],
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(uuid4()),
        "email": normalized_email,
        "full_name": full_name.strip(),
        "tenant_id": normalized_tenant_id,
        "app_key": normalized_app_key,
        "role": role.strip(),
        "hashed_password": hash_password(password),
        "auth_provider": "password",
        "provider_subject": _password_provider_subject(normalized_email),
        "is_active": True,
        "subscription_tier": "free",
        "subscription_status": "active",
        "accepted_terms_at": None,
        "query_usage_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await users.insert_one(doc)

    except DuplicateKeyError as exc:
        raise ValueError("User with this email already exists") from exc

    return {
        "user_id": doc["user_id"],
        "email": doc["email"],
        "full_name": doc["full_name"],
        "tenant_id": doc["tenant_id"],
        "app_key": doc["app_key"],
        "role": doc["role"],
        "is_active": doc["is_active"],
        "subscription_tier": doc.get("subscription_tier", "free"),
        "subscription_status": doc.get("subscription_status", "active"),
        "accepted_terms_at": doc.get("accepted_terms_at"),
        "query_usage_count": doc.get("query_usage_count", 0),
    }


async def create_user_from_google(
    *,
    email: str,
    full_name: str,
    tenant_id: str,
    role: str,
    provider_subject: str,
    app_key: str | None = None,
):
    await ensure_users_indexes()

    normalized_tenant_id = tenant_id.strip()
    normalized_app_key = resolve_app_key(app_key or get_app_key())
    await ensure_tenant_exists(
        normalized_tenant_id,
        organization_type=None,
        app_keys=[normalized_app_key],
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": str(uuid4()),
        "email": email.strip().lower(),
        "full_name": full_name.strip(),
        "tenant_id": normalized_tenant_id,
        "app_key": normalized_app_key,
        "role": role.strip(),
        "hashed_password": None,
        "auth_provider": "google",
        "provider_subject": provider_subject,
        "is_active": True,
        "subscription_tier": "free",
        "subscription_status": "active",
        "accepted_terms_at": None,
        "query_usage_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise ValueError("User with this email or Google account already exists") from exc

    return {
        "user_id": doc["user_id"],
        "email": doc["email"],
        "full_name": doc["full_name"],
        "tenant_id": doc["tenant_id"],
        "app_key": doc["app_key"],
        "role": doc["role"],
        "is_active": doc["is_active"],
        "auth_provider": doc["auth_provider"],
        "provider_subject": doc["provider_subject"],
        "subscription_tier": doc.get("subscription_tier", "free"),
        "subscription_status": doc.get("subscription_status", "active"),
        "accepted_terms_at": doc.get("accepted_terms_at"),
        "query_usage_count": doc.get("query_usage_count", 0),
    }


async def create_user_from_mobile(
    *,
    mobile: str,
    full_name: str,
    tenant_id: str,
    role: str = "operator",
    app_key: str | None = None,
):
    await ensure_users_indexes()

    normalized_tenant_id = tenant_id.strip()
    normalized_mobile = mobile.strip()
    normalized_app_key = resolve_app_key(app_key or get_app_key())
    await ensure_tenant_exists(
        normalized_tenant_id,
        organization_type=None,
        app_keys=[normalized_app_key],
    )

    users = get_collection(USERS_COLLECTION)
    now = datetime.now(timezone.utc)

    # Keep email valid and unique for legacy parts that still rely on email field.
    mobile_local = normalized_mobile.replace("+", "").replace(" ", "").replace("-", "")
    mobile_email = f"mobile.{mobile_local}@sanmitra.local"

    doc = {
        "user_id": str(uuid4()),
        "email": mobile_email,
        "mobile": normalized_mobile,
        "full_name": full_name.strip(),
        "tenant_id": normalized_tenant_id,
        "app_key": normalized_app_key,
        "role": role.strip(),
        "hashed_password": None,
        "auth_provider": "mobile_otp",
        "provider_subject": _mobile_provider_subject(normalized_mobile),
        "is_active": True,
        "subscription_tier": "free",
        "subscription_status": "active",
        "accepted_terms_at": None,
        "query_usage_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await users.insert_one(doc)
    except DuplicateKeyError as exc:
        raise ValueError("User with this mobile already exists") from exc

    return {
        "user_id": doc["user_id"],
        "email": doc["email"],
        "mobile": doc["mobile"],
        "full_name": doc["full_name"],
        "tenant_id": doc["tenant_id"],
        "app_key": doc["app_key"],
        "role": doc["role"],
        "is_active": doc["is_active"],
        "auth_provider": doc["auth_provider"],
        "provider_subject": doc["provider_subject"],
        "subscription_tier": doc.get("subscription_tier", "free"),
        "subscription_status": doc.get("subscription_status", "active"),
        "accepted_terms_at": doc.get("accepted_terms_at"),
        "query_usage_count": doc.get("query_usage_count", 0),
    }
