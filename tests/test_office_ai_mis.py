"""OfficeMitra CA Analysis Pack (ADR-014) — module gates and MIS flag helpers."""
from __future__ import annotations

import pytest

from app.core.modules.registry import (
    ModuleAccessError,
    is_office_ai_mis_enabled,
    is_office_ai_mis_export_enabled,
    is_office_ai_mis_import_enabled,
    is_office_ai_mis_live_mitrabooks_enabled,
    is_office_ai_mis_pack_enabled,
    require_module_feature,
)
from app.modules.office_ai.services import mis_service


def test_mis_feature_is_opt_in_not_parent_default():
    with pytest.raises(ModuleAccessError, match="office_ai.mis"):
        require_module_feature(
            module_key="office_ai",
            feature="mis",
            organization_type="PROFESSIONAL",
            enabled_modules=["office_ai"],
            app_key="officemitra",
        )

    require_module_feature(
        module_key="office_ai",
        feature="mis",
        organization_type="PROFESSIONAL",
        enabled_modules=["office_ai", "office_ai.mis"],
        app_key="officemitra",
    )

    assert is_office_ai_mis_enabled(enabled_modules=["office_ai"]) is False
    assert is_office_ai_mis_enabled(enabled_modules=["office_ai", "office_ai.mis"]) is True


def test_mis_sub_capabilities_require_parent_mis():
    modules = [
        "office_ai",
        "office_ai.mis",
        "office_ai.mis.import",
        "office_ai.mis.export",
        "office_ai.mis.live_mitrabooks",
    ]
    assert is_office_ai_mis_import_enabled(enabled_modules=modules) is True
    assert is_office_ai_mis_export_enabled(enabled_modules=modules) is True
    assert is_office_ai_mis_live_mitrabooks_enabled(enabled_modules=modules) is True

    assert is_office_ai_mis_import_enabled(enabled_modules=["office_ai", "office_ai.mis.import"]) is False
    assert is_office_ai_mis_import_enabled(enabled_modules=["office_ai", "office_ai.mis"]) is False


def test_mis_pack_flag_requires_parent_mis():
    modules = ["office_ai", "office_ai.mis", "office_ai.mis.pack.sme_general"]
    assert is_office_ai_mis_pack_enabled("sme_general", enabled_modules=modules) is True
    assert is_office_ai_mis_pack_enabled("ca_practice", enabled_modules=modules) is False
    assert is_office_ai_mis_pack_enabled("sme_general", enabled_modules=["office_ai"]) is False


def test_mis_pack_catalog_lists_adr014_starter_packs():
    catalog = mis_service.list_pack_catalog()
    keys = {item["pack_key"] for item in catalog}
    assert "sme_general" in keys
    assert "ca_practice" in keys
    assert all("pack_version" in item for item in catalog)
