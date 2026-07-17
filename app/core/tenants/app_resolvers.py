from dataclasses import dataclass

from fastapi import HTTPException

from app.core.tenants.context import InvalidAppKeyError, get_tenant_id, resolve_app_key, resolve_tenant_id, validate_app_key


UNSAFE_BUSINESS_TENANTS = {"default", ""}
DEFAULT_ACCOUNTING_ENTITY_ID = "primary"
ACCOUNTING_ENTITY_ADMIN_ROLES = frozenset({"super_admin", "tenant_admin", "owner", "admin"})


@dataclass(frozen=True)
class AppTenantContext:
    app_key: str
    tenant_id: str
    accounting_entity_id: str = DEFAULT_ACCOUNTING_ENTITY_ID


def resolve_business_app_tenant(
    *,
    current_user: dict,
    x_tenant_id: str | None,
    x_app_key: str | None,
    expected_app_key: str,
    operation: str = "write",
    block_default_tenant: bool = True,
    x_accounting_entity_id: str | None = None,
) -> AppTenantContext:
    """Resolve and validate app/tenant scope for business data operations.

    The optional accounting entity (client book) dimension lets one practice
    tenant manage multiple client books later. It always defaults to the single
    "primary" book so existing single-entity tenants are unaffected.
    """

    expected = resolve_app_key(expected_app_key)
    try:
        header_app_key = validate_app_key(x_app_key) if x_app_key else None
    except InvalidAppKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    app_key = resolve_app_key(header_app_key or current_user.get("app_key") or expected)
    if app_key != expected:
        raise HTTPException(status_code=403, detail=f"{expected} app context required")

    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    normalized_tenant = str(tenant_id or "").strip()
    if not normalized_tenant:
        raise HTTPException(status_code=401, detail="Tenant context missing")

    if block_default_tenant and normalized_tenant.lower() in UNSAFE_BUSINESS_TENANTS:
        raise HTTPException(
            status_code=400,
            detail=f"Explicit tenant selection is required for {expected} {operation}.",
        )

    accounting_entity_id = str(x_accounting_entity_id or DEFAULT_ACCOUNTING_ENTITY_ID).strip() or DEFAULT_ACCOUNTING_ENTITY_ID
    role = str(current_user.get("role") or "").strip().lower()
    if role not in ACCOUNTING_ENTITY_ADMIN_ROLES:
        assigned_entities = {
            str(entity_id).strip()
            for entity_id in (current_user.get("accounting_entity_ids") or [DEFAULT_ACCOUNTING_ENTITY_ID])
            if str(entity_id).strip()
        }
        if accounting_entity_id not in assigned_entities:
            raise HTTPException(status_code=403, detail="Accounting entity access denied")

    return AppTenantContext(
        app_key=app_key,
        tenant_id=normalized_tenant,
        accounting_entity_id=accounting_entity_id,
    )


def resolve_mandir_tenant(
    *,
    current_user: dict,
    x_tenant_id: str | None,
    x_app_key: str | None,
    operation: str = "write",
    block_default_tenant: bool = True,
) -> AppTenantContext:
    context_tenant_id = get_tenant_id()
    return resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=context_tenant_id or x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="mandirmitra",
        operation=operation,
        block_default_tenant=block_default_tenant,
    )


def resolve_gruha_tenant(
    *,
    current_user: dict,
    x_tenant_id: str | None,
    x_app_key: str | None,
    operation: str = "write",
    block_default_tenant: bool = True,
) -> AppTenantContext:
    return resolve_business_app_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        expected_app_key="gruhamitra",
        operation=operation,
        block_default_tenant=block_default_tenant,
    )
