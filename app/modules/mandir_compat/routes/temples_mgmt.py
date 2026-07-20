"""MandirMitra setup wizard, temple admin, and compliance config routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.donation_compliance import (
    compliance_public_fields,
    donation_compliance_config_view,
    validate_donation_compliance_config,
)
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router
from app.modules.mandir_compat.schemas import (
    MandirFirstLoginOnboardingRequest,
    MandirFirstLoginOnboardingResponse,
)

@router.get("/setup-wizard/status")
async def mandir_setup_wizard_status(_current_user: dict = Depends(get_current_user)):
    return {"completed": False, "steps": []}


@router.get("/temples/")
@router.get("/temples")
async def mandir_temples(
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    if mandir_router._is_platform_super_admin(_current_user):
        rows = await mandir_router.list_mandir_temples(app_key=app_key, limit=500)
    else:
        tenant_id = mandir_router.resolve_tenant_id(_current_user, x_tenant_id)
        rows = await mandir_router.list_mandir_temples(tenant_id=tenant_id, app_key=app_key, limit=20)

    if rows:
        return [mandir_router._sanitize_mongo_doc(row) for row in rows]

    if mandir_router._is_platform_super_admin(_current_user):
        return []

    return []




async def _resolve_temple_target_tenant(
    temple_id: int,
    *,
    current_user: dict,
    x_tenant_id: str | None,
    app_key: str = "mandirmitra",
) -> str:
    target_tenant_id = await mandir_router.resolve_tenant_by_temple_id(temple_id, app_key=app_key)
    if not target_tenant_id:
        raise HTTPException(status_code=404, detail="Temple not found")

    actor_tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    if not mandir_router._is_platform_super_admin(current_user) and actor_tenant_id != target_tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for this tenant")

    return target_tenant_id


_MANDIR_TEMPLE_PURGE_COLLECTIONS = [
    "mandir_temples",
    "mandir_donations",
    "mandir_sevas",
    "mandir_seva_bookings",
    "mandir_devotees",
    "mandir_bank_accounts",
    "mandir_bank_statements",
    "mandir_bank_statement_entries",
    "mandir_bank_unmatched_entries",
    "mandir_inventory_items",
    "mandir_journal_entries",
    "mandir_public_payments",
    "mandir_upi_payments",
    "mandir_role_permissions",
    "mandir_panchang_settings",
]

_MANDIR_TEMPLE_BUSINESS_COLLECTIONS = [
    name
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS
    if name not in {"mandir_temples", "mandir_role_permissions", "mandir_panchang_settings"}
]


def _mandir_tenant_app_query(tenant_id: str, app_key: str) -> dict[str, Any]:
    query: dict[str, Any] = {"tenant_id": tenant_id}
    if app_key == "mandirmitra":
        query["$or"] = [
            {"app_key": app_key},
            {"app_key": {"$exists": False}},
            {"app_key": None},
            {"app_key": ""},
        ]
    else:
        query["app_key"] = app_key
    return query


async def _mandir_temple_collection_counts(tenant_id: str, app_key: str) -> dict[str, int]:
    query = _mandir_tenant_app_query(tenant_id, app_key)
    counts: dict[str, int] = {}
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS:
        try:
            counts[name] = int(await mandir_router.get_collection(name).count_documents(query))
        except Exception:
            counts[name] = 0
    return counts


@router.post("/temples/{temple_id}/activate", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_activate_temple(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    now = datetime.now(timezone.utc).isoformat()
    await mandir_router.get_collection("mandir_temples").update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": True, "updated_at": now}},
        upsert=False,
    )
    doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {"tenant_id": tenant_id}
    return {"status": "activated", "temple_id": temple_id, "temple": mandir_router._sanitize_mongo_doc(doc)}


@router.post("/temples/{temple_id}/deactivate", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_deactivate_temple(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    now = datetime.now(timezone.utc).isoformat()
    await mandir_router.get_collection("mandir_temples").update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {"$set": {"is_active": False, "updated_at": now}},
        upsert=False,
    )
    doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {"tenant_id": tenant_id}
    return {"status": "deactivated", "temple_id": temple_id, "temple": mandir_router._sanitize_mongo_doc(doc)}


@router.get("/temples/{temple_id}/remove-preview")
async def mandir_remove_temple_preview(
    temple_id: int,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not mandir_router._is_platform_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only platform administrators can preview temple removal")

    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    target_tenant_id = await mandir_router._resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    counts = await mandir_router._mandir_temple_collection_counts(target_tenant_id, app_key)
    business_counts = {name: count for name, count in counts.items() if name in _MANDIR_TEMPLE_BUSINESS_COLLECTIONS and count > 0}
    return {
        "temple_id": temple_id,
        "tenant_id": target_tenant_id,
        "counts": counts,
        "has_business_data": bool(business_counts),
        "business_counts": business_counts,
        "can_remove_placeholder_safely": not business_counts,
    }


@router.delete("/temples/{temple_id}/remove", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_remove_temple(
    temple_id: int,
    payload: dict[str, Any] | None = None,
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if not mandir_router._is_platform_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only platform administrators can remove temples")

    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    target_tenant_id = await mandir_router._resolve_temple_target_tenant(temple_id, current_user=current_user, x_tenant_id=x_tenant_id, app_key=app_key)
    expected = f"DELETE {temple_id}"
    confirm_text = str((payload or {}).get("confirm_text") or "").strip()
    if confirm_text != expected:
        raise HTTPException(status_code=400, detail=f"Confirmation text mismatch. Expected: {expected}")

    counts = await mandir_router._mandir_temple_collection_counts(target_tenant_id, app_key)
    business_counts = {name: count for name, count in counts.items() if name in _MANDIR_TEMPLE_BUSINESS_COLLECTIONS and count > 0}
    allow_data_delete = bool((payload or {}).get("allow_data_delete"))
    if business_counts and not allow_data_delete:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Temple has business data. Review remove-preview before deleting.",
                "tenant_id": target_tenant_id,
                "business_counts": business_counts,
            },
        )

    delete_query = mandir_router._mandir_tenant_app_query(target_tenant_id, app_key)
    deleted_counts: dict[str, int] = {}
    for name in _MANDIR_TEMPLE_PURGE_COLLECTIONS:
        try:
            result = await mandir_router.get_collection(name).delete_many(delete_query)
            deleted_counts[name] = int(getattr(result, "deleted_count", 0) or 0)
        except Exception:
            deleted_counts[name] = 0

    return {
        "status": "removed",
        "temple_id": temple_id,
        "tenant_id": target_tenant_id,
        "deleted": deleted_counts,
    }

@router.post("/temples/onboard", response_model=MandirFirstLoginOnboardingResponse)
@router.post("/onboarding/first-login", response_model=MandirFirstLoginOnboardingResponse)
async def mandir_temples_onboard(
    payload: MandirFirstLoginOnboardingRequest,
    request: Request,
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_onboarding_token: str | None = Header(default=None, alias="X-Onboarding-Token"),
):
    from app.config import get_settings as _get_settings
    _settings = _get_settings()
    required_secret = _settings.MANDIR_ONBOARDING_SECRET
    if required_secret:
        provided = (x_onboarding_token or "").strip()
        if not provided or provided != required_secret:
            mandir_router.logger.warning(
                "Onboarding attempt rejected: missing/invalid X-Onboarding-Token from %s",
                request.client.host if request.client else "unknown",
            )
            raise HTTPException(status_code=403, detail="Invalid or missing onboarding token")
    else:
        if str(_settings.ENVIRONMENT or "").strip().lower() in {"production", "prod"}:
            raise HTTPException(status_code=503, detail="Mandir onboarding is not configured")
        mandir_router.logger.info(
            "Onboarding endpoint called without secret enforcement (MANDIR_ONBOARDING_SECRET not set). "
            "Set this env var in production to protect this endpoint."
        )
    if not str(x_app_key or "").strip():
        raise HTTPException(status_code=400, detail="X-App-Key header is required")
    app_key = mandir_router.resolve_app_key(str(x_app_key).strip())
    return await mandir_router.create_mandir_first_login_onboarding(payload, app_key=app_key)


@router.post("/temples/upload", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_temples_upload(_payload: dict[str, Any], _current_user: dict = Depends(get_current_user)):
    return mandir_router._ok("temples/upload")


@router.get("/compliance/donations/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def get_mandir_donation_compliance_config(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation compliance configuration read",
    )
    doc = await mandir_router.get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": context.tenant_id, "app_key": context.app_key}
    )
    return donation_compliance_config_view(doc)


@router.put("/compliance/donations/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def update_mandir_donation_compliance_config(
    payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    context = resolve_mandir_tenant(
        current_user=current_user,
        x_tenant_id=x_tenant_id,
        x_app_key=x_app_key,
        operation="donation compliance configuration update",
    )
    await mandir_router._assert_platform_can_write_tenant(
        current_user, tenant_id=context.tenant_id, app_key=context.app_key
    )
    config = validate_donation_compliance_config(payload)
    now = datetime.now(timezone.utc).isoformat()
    stored = {**config, "updated_at": now, "updated_by": mandir_router._mandir_actor_id(current_user)}
    collection = mandir_router.get_collection("mandir_donation_compliance_config")
    await collection.update_one(
        {"tenant_id": context.tenant_id, "app_key": context.app_key},
        {
            "$set": stored,
            "$setOnInsert": {
                "tenant_id": context.tenant_id,
                "app_key": context.app_key,
                "created_at": now,
            },
        },
        upsert=True,
    )
    try:
        await mandir_router.log_audit_event(
            tenant_id=context.tenant_id,
            user_id=mandir_router._mandir_actor_id(current_user),
            product=context.app_key,
            action="donation_compliance_config_updated",
            entity_type="mandir_donation_compliance_config",
            entity_id=f"{context.tenant_id}:{context.app_key}",
            old_value=None,
            new_value={
                "enable_80g": config["enable_80g"],
                "enable_fcra": config["enable_fcra"],
                "approval_valid_from": config.get("approval_valid_from"),
                "approval_valid_to": config.get("approval_valid_to"),
                "fcra_valid_from": config.get("fcra_valid_from"),
                "fcra_valid_to": config.get("fcra_valid_to"),
            },
        )
    except Exception:
        mandir_router.logger.warning("Failed to audit donation compliance configuration update", exc_info=True)
    return donation_compliance_config_view(stored)


async def _mandir_compliance_report(
    *, kind: str, tenant_id: str, app_key: str, from_date: date, to_date: date, session: AsyncSession
) -> dict[str, Any]:
    rows = await mandir_router.posted_donations(
        session,
        tenant_id=tenant_id,
        app_key=app_key,
        from_date=from_date,
        to_date=to_date,
    )
    items: list[dict[str, Any]] = []
    status_counts: dict[str, int] = {}
    for row in rows:
        if kind == "80g" and not bool(row.get("request_80g")):
            continue
        if kind == "fcra" and not bool(row.get("is_foreign_contribution")):
            continue
        public = compliance_public_fields(row)
        status_field = "80g_eligibility_status" if kind == "80g" else "fcra_status"
        status = str(public[status_field])
        status_counts[status] = status_counts.get(status, 0) + 1
        items.append({
            "donation_id": row.get("donation_id"),
            "receipt_number": row.get("receipt_number"),
            "date": row.get("date"),
            "amount": row.get("amount"),
            "payment_mode": row.get("payment_mode"),
            "devotee_name": row.get("devotee_name"),
            **public,
        })
    return {
        "report_kind": kind,
        "filing_artifact": False,
        "filing_notice": "Readiness report only; this is not an official government filing or certificate.",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "count": len(items),
        "status_counts": status_counts,
        "items": items,
    }


@router.get("/reports/compliance/80g", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_report_80g_readiness(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="80G readiness reporting",
    )
    return await mandir_router._mandir_compliance_report(
        kind="80g", tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=from_date, to_date=to_date, session=session,
    )


@router.get("/reports/compliance/fcra", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_report_fcra_readiness(
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    context = resolve_mandir_tenant(
        current_user=current_user, x_tenant_id=x_tenant_id, x_app_key=x_app_key,
        operation="FCRA readiness reporting",
    )
    return await mandir_router._mandir_compliance_report(
        kind="fcra", tenant_id=context.tenant_id, app_key=context.app_key,
        from_date=from_date, to_date=to_date, session=session,
    )


@router.get("/temples/modules/config")
async def mandir_temples_module_config(
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    app_key = mandir_router.resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(_current_user, x_tenant_id, temple_id, app_key)
    col = mandir_router.get_collection("mandir_temples")
    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    compliance_doc = await mandir_router.get_collection("mandir_donation_compliance_config").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    )
    compliance = donation_compliance_config_view(compliance_doc)
    return {
        "module_donations_enabled": bool(doc.get("module_donations_enabled", True)),
        "module_sevas_enabled": bool(doc.get("module_sevas_enabled", True)),
        "module_inventory_enabled": bool(doc.get("module_inventory_enabled", False)),
        "module_assets_enabled": bool(doc.get("module_assets_enabled", False)),
        "module_hr_enabled": bool(doc.get("module_hr_enabled", False)),
        "module_hundi_enabled": bool(doc.get("module_hundi_enabled", False)),
        "module_accounting_enabled": bool(doc.get("module_accounting_enabled", True)),
        "module_panchang_enabled": bool(doc.get("module_panchang_enabled", True)),
        "enable_80g": compliance["enable_80g"],
        "enable_fcra": compliance["enable_fcra"],
    }


@router.put("/temples/modules/config", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_temples_module_config_update(
    payload: dict[str, Any],
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    temple_id: int | None = Query(default=None),
):
    tenant_id = await mandir_router._resolve_tenant_for_mandir_request(_current_user, x_tenant_id, temple_id)
    app_key = mandir_router.resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())
    assigned_temple_id = await mandir_router.ensure_temple_numeric_id(tenant_id, app_key=app_key)
    col = mandir_router.get_collection("mandir_temples")

    allowed_keys = {
        "module_donations_enabled",
        "module_sevas_enabled",
        "module_inventory_enabled",
        "module_assets_enabled",
        "module_hr_enabled",
        "module_hundi_enabled",
        "module_accounting_enabled",
        "module_panchang_enabled",
    }
    update = {key: bool(payload.get(key)) for key in allowed_keys if key in payload}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["id"] = assigned_temple_id
    update["temple_id"] = assigned_temple_id

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key},
        {
            "$set": update,
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "app_key": app_key,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )

    doc = await col.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    return {
        "module_donations_enabled": bool(doc.get("module_donations_enabled", True)),
        "module_sevas_enabled": bool(doc.get("module_sevas_enabled", True)),
        "module_inventory_enabled": bool(doc.get("module_inventory_enabled", False)),
        "module_assets_enabled": bool(doc.get("module_assets_enabled", False)),
        "module_hr_enabled": bool(doc.get("module_hr_enabled", False)),
        "module_hundi_enabled": bool(doc.get("module_hundi_enabled", False)),
        "module_accounting_enabled": bool(doc.get("module_accounting_enabled", True)),
        "module_panchang_enabled": bool(doc.get("module_panchang_enabled", True)),
    }

