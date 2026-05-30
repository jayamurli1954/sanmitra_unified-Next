"""Phase 1: a MitraBooks (BUSINESS) tenant resolves the correct ERP context.

This locks the onboarding-side guarantees that the BUSINESS organization type
derives the right default modules and that the accounting module is reachable
for the mitrabooks app key.
"""

import pytest

from app.core.modules.registry import (
    ModuleAccessError,
    derive_enabled_modules,
    normalize_organization_type,
    require_module_access,
)


def test_mitrabooks_app_key_derives_business_org_type() -> None:
    org_type = normalize_organization_type(None, app_key="mitrabooks")
    assert org_type == "BUSINESS"


def test_business_default_modules_include_accounting_and_business() -> None:
    org_type = normalize_organization_type(None, app_key="mitrabooks")
    modules = derive_enabled_modules(organization_type=org_type)
    for expected in ("business", "accounting", "audit"):
        assert expected in modules, f"BUSINESS tenant should enable {expected}"


def test_accounting_module_allows_business_mitrabooks() -> None:
    definition = require_module_access(
        module_key="accounting",
        organization_type="BUSINESS",
        enabled_modules=["business", "accounting", "audit"],
        app_key="mitrabooks",
    )
    assert definition.module_key == "accounting"


def test_business_module_blocked_when_not_enabled() -> None:
    with pytest.raises(ModuleAccessError):
        require_module_access(
            module_key="business",
            organization_type="BUSINESS",
            enabled_modules=["accounting"],  # business intentionally omitted
            app_key="mitrabooks",
        )


def test_business_module_blocked_for_wrong_app_key() -> None:
    with pytest.raises(ModuleAccessError):
        require_module_access(
            module_key="business",
            organization_type="BUSINESS",
            enabled_modules=["business"],
            app_key="gruhamitra",  # housing app cannot reach business module
        )
