"""Business invoice and admin settings (read / save / module toggles).

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Uses runtime lookup on the service module for get_collection so existing tests
that monkeypatch business_service.get_collection keep working.
"""
from app.modules.business import service as business_service
from app.modules.business.schemas import (
    BusinessAdminSettings,
    BusinessAdminSettingsUpdateRequest,
    BusinessAiSettings,
    BusinessIntegrationSettings,
    INVOICE_STANDARD_FIELDS,
    InvoiceSettings,
    InvoiceSettingsUpdateRequest,
)

_MODULE_ENABLE_FLAGS = {"cost_centre_enabled", "manufacturing_enabled"}


async def get_invoice_settings(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    row = await business_service.get_collection(business_service.INVOICE_SETTINGS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    )
    if row is None:
        settings = InvoiceSettings()
        result = settings.model_dump()
    else:
        # Re-validate stored doc through the model so missing/new keys get defaults.
        stored = {
            k: v for k, v in row.items()
            if k in {"field_config", "numbering", "custom_fields", "branding", "inventory_enabled",
                     "inventory_valuation_policy", "hr_enabled", "cost_centre_enabled", "manufacturing_enabled"}
        }
        result = InvoiceSettings(**stored).model_dump()
    # Backfill any standard field missing from a partially-saved config so the
    # form and required-field validation always have a complete rule set.
    field_config = result.get("field_config") or {}
    for key in INVOICE_STANDARD_FIELDS:
        field_config.setdefault(key, {"visible": True, "required": False})
    result["field_config"] = field_config
    result.update({
        "tenant_id": tenant_id,
        "app_key": app_key,
        "accounting_entity_id": accounting_entity_id,
        "updated_by": (row or {}).get("updated_by"),
        "updated_at": (row or {}).get("updated_at"),
    })
    return result


async def get_gst_profile(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    """The entity's GST regime, read from invoice-settings branding.

    Returns registration_type ("regular"|"composition"), the composition
    category, and the derived composition tax rate (None for regular dealers).
    """
    settings = await get_invoice_settings(
        tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id,
    )
    branding = (settings or {}).get("branding") or {}
    reg_type = str(branding.get("gst_registration_type") or "regular")
    category = branding.get("composition_category")
    rate = business_service.COMPOSITION_RATES.get(category) if reg_type == "composition" else None
    return {
        "registration_type": reg_type,
        "composition_category": category,
        "composition_rate": rate,
        "is_composition": reg_type == "composition",
    }


async def save_invoice_settings(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: InvoiceSettingsUpdateRequest,
) -> dict:
    accounting_entity_id = payload.accounting_entity_id
    settings = InvoiceSettings(
        field_config=payload.field_config,
        numbering=payload.numbering,
        custom_fields=payload.custom_fields,
        branding=payload.branding,
        inventory_enabled=payload.inventory_enabled,
        inventory_valuation_policy=payload.inventory_valuation_policy,
        hr_enabled=payload.hr_enabled,
        cost_centre_enabled=payload.cost_centre_enabled,
        manufacturing_enabled=payload.manufacturing_enabled,
    )
    doc = settings.model_dump()
    doc.update({"updated_by": updated_by, "updated_at": business_service._now()})
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await business_service.get_collection(business_service.INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": doc, "$setOnInsert": {**filters, "created_at": business_service._now()}},
        upsert=True,
    )
    await business_service._audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_invoice_settings_updated",
        entity_type="business_invoice_settings",
        entity_id=accounting_entity_id,
        new_value=doc,
    )
    return await get_invoice_settings(tenant_id=tenant_id, app_key=app_key, accounting_entity_id=accounting_entity_id)


async def get_business_admin_settings(
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str,
) -> dict:
    row = await business_service.get_collection(business_service.ADMIN_SETTINGS_COLLECTION).find_one(
        {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    )
    if row is None:
        result = BusinessAdminSettings().model_dump()
    else:
        stored = {
            k: v for k, v in row.items()
            if k in {
                "organization",
                "branches",
                "roles",
                "permissions",
                "voucher_configuration",
                "financial_controls",
                "security",
                "templates",
                "notifications",
                "subscription_billing",
                "integrations",
                "ai_settings",
            }
        }
        result = BusinessAdminSettings(**stored).model_dump()
    result.update(
        {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": accounting_entity_id,
            "updated_by": (row or {}).get("updated_by"),
            "updated_at": (row or {}).get("updated_at"),
        }
    )
    return result


async def save_business_admin_settings(
    *,
    tenant_id: str,
    app_key: str,
    updated_by: str,
    payload: BusinessAdminSettingsUpdateRequest,
) -> dict:
    accounting_entity_id = payload.accounting_entity_id
    settings = BusinessAdminSettings(
        organization=payload.organization,
        branches=payload.branches,
        roles=payload.roles,
        permissions=payload.permissions,
        voucher_configuration=payload.voucher_configuration,
        financial_controls=payload.financial_controls,
        security=payload.security,
        templates=payload.templates,
        notifications=payload.notifications,
        subscription_billing=payload.subscription_billing,
        integrations=BusinessIntegrationSettings(**payload.integrations.model_dump()),
        ai_settings=BusinessAiSettings(
            **{
                **payload.ai_settings.model_dump(),
                "auto_post_to_ledger": False,
                "document_review_required": True,
                "posting_review_required": True,
            }
        ),
    )
    doc = settings.model_dump(mode="json")
    doc.update({"updated_by": updated_by, "updated_at": business_service._now()})
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await business_service.get_collection(business_service.ADMIN_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": doc, "$setOnInsert": {**filters, "created_at": business_service._now()}},
        upsert=True,
    )
    await business_service._audit_business_event(
        tenant_id=tenant_id,
        app_key=app_key,
        user_id=updated_by,
        action="business_admin_settings_updated",
        entity_type="business_admin_settings",
        entity_id=accounting_entity_id,
        new_value=doc,
    )
    return await get_business_admin_settings(
        tenant_id=tenant_id,
        app_key=app_key,
        accounting_entity_id=accounting_entity_id,
    )


async def set_hr_enabled(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, enabled: bool, updated_by: str
) -> bool:
    """Tenant-admin toggle for the HR add-on — flips just InvoiceSettings.hr_enabled
    (upserting the settings doc) without needing the full settings payload."""
    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await business_service.get_collection(business_service.INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": {"hr_enabled": bool(enabled), "updated_by": updated_by, "updated_at": business_service._now()},
         "$setOnInsert": {**filters, "created_at": business_service._now()}},
        upsert=True,
    )
    await business_service._audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=updated_by,
        action="business_hr_enabled_toggled", entity_type="business_invoice_settings",
        entity_id=accounting_entity_id, new_value={"hr_enabled": bool(enabled)},
    )
    return bool(enabled)


async def set_module_enabled(
    *, tenant_id: str, app_key: str, accounting_entity_id: str, flag: str, enabled: bool, updated_by: str,
) -> dict:
    """Tenant-admin toggle for an enterprise module flag on InvoiceSettings
    (cost_centre_enabled / manufacturing_enabled), upserting the settings doc.

    Manufacturing depends on cost centres, so enabling manufacturing implies
    cost centres ON, and disabling cost centres also disables manufacturing —
    the two flags can never end up in a contradictory state."""
    if flag not in _MODULE_ENABLE_FLAGS:
        raise ValueError(f"Unknown module flag '{flag}'")
    updates = {flag: bool(enabled)}
    if flag == "manufacturing_enabled" and enabled:
        updates["cost_centre_enabled"] = True
    if flag == "cost_centre_enabled" and not enabled:
        updates["manufacturing_enabled"] = False

    filters = {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}
    await business_service.get_collection(business_service.INVOICE_SETTINGS_COLLECTION).update_one(
        filters,
        {"$set": {**updates, "updated_by": updated_by, "updated_at": business_service._now()},
         "$setOnInsert": {**filters, "created_at": business_service._now()}},
        upsert=True,
    )
    await business_service._audit_business_event(
        tenant_id=tenant_id, app_key=app_key, user_id=updated_by,
        action="business_module_enabled_toggled", entity_type="business_invoice_settings",
        entity_id=accounting_entity_id, new_value=updates,
    )
    return updates
