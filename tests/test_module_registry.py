import pytest

from app.core.modules.registry import (
    ModuleAccessError,
    derive_enabled_modules,
    normalize_organization_type,
    require_module_access,
)


def test_normalize_organization_type_from_legacy_names_and_app_key():
    assert normalize_organization_type("GruhaMitra") == "HOUSING"
    assert normalize_organization_type("GharMitra") == "HOUSING"
    assert normalize_organization_type(None, app_key="mandirmitra") == "TEMPLE"


def test_investment_organization_type_is_not_in_unified_scope():
    modules = derive_enabled_modules(organization_type="INVESTMENT")

    assert modules == []


def test_require_module_access_allows_enabled_module():
    definition = require_module_access(
        module_key="temple",
        organization_type="TEMPLE",
        enabled_modules=["temple", "accounting", "audit"],
        app_key="mandirmitra",
    )

    assert definition.module_key == "temple"


def test_require_module_access_blocks_wrong_app_key():
    with pytest.raises(ModuleAccessError, match="app_key"):
        require_module_access(
            module_key="temple",
            organization_type="TEMPLE",
            enabled_modules=["temple", "accounting", "audit"],
            app_key="legalmitra",
        )


def test_require_module_access_blocks_investment_modules():
    with pytest.raises(ModuleAccessError, match="Unknown module"):
        require_module_access(
            module_key="investment",
            organization_type="INVESTMENT",
            enabled_modules=["investment", "portfolio", "audit"],
            app_key="investmitra",
        )


def test_require_module_access_allows_explicit_future_integration_flag():
    definition = require_module_access(
        module_key="legal_ai",
        organization_type="LEGAL",
        enabled_modules=["legal", "rag", "compliance", "audit", "legal_ai"],
        app_key="legalmitra",
    )

    assert definition.module_key == "legal_ai"
