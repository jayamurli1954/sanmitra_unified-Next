from fastapi import APIRouter, Depends, Header, Query

from app.core.auth.dependencies import get_current_user
from app.core.modules.dependencies import require_enabled_module
from app.core.tenants.context import resolve_app_key, resolve_tenant_id
from app.core.audit.service import list_audit_events

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
async def list_events(
    product: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=120),
    entity_id: str | None = Query(default=None, max_length=255),
    action: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    _module_context: dict = Depends(require_enabled_module("audit")),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = resolve_tenant_id(current_user, x_tenant_id)
    active_app_key = resolve_app_key(x_app_key or current_user.get("app_key"))
    product_filter = resolve_app_key(product) if product else active_app_key
    return await list_audit_events(
        tenant_id=tenant_id,
        product=product_filter,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
    )
