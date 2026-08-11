from __future__ import annotations

from typing import Any

from app.modules.office_ai.services import mis_store

# ADR-014 metric packs — config registry (loaders ship in later steps).
MIS_PACK_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "pack_key": "sme_general",
        "pack_version": "1.0.0",
        "display_name": "SME General Monthly MIS",
        "materiality_rule_version": "1.0.0",
    },
    {
        "pack_key": "ca_practice",
        "pack_version": "1.0.0",
        "display_name": "CA Practice Roll-up",
        "materiality_rule_version": "1.0.0",
    },
    {
        "pack_key": "professional_services",
        "pack_version": "1.0.0",
        "display_name": "Professional Services",
        "materiality_rule_version": "1.0.0",
    },
    {
        "pack_key": "manufacturing",
        "pack_version": "1.0.0",
        "display_name": "Manufacturing",
        "materiality_rule_version": "1.0.0",
    },
    {
        "pack_key": "housing",
        "pack_version": "1.0.0",
        "display_name": "Housing Society",
        "materiality_rule_version": "1.0.0",
    },
    {
        "pack_key": "temple",
        "pack_version": "1.0.0",
        "display_name": "Temple Trust",
        "materiality_rule_version": "1.0.0",
    },
)


def list_pack_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in MIS_PACK_CATALOG]


def get_pack_catalog_entry(pack_key: str) -> dict[str, Any] | None:
    key = str(pack_key or "").strip().lower()
    for item in MIS_PACK_CATALOG:
        if str(item.get("pack_key") or "").strip().lower() == key:
            return dict(item)
    return None


async def get_mis_status(
    *,
    tenant_id: str,
    enabled_modules: list[str] | None,
    office_ai_features: list[str] | None,
    mis_flags: dict[str, bool],
    enabled_packs: list[str],
) -> dict[str, Any]:
    packs = await mis_store.list_packs(tenant_id=tenant_id, limit=5)
    return {
        "tenant_id": tenant_id,
        "adr": "ADR-014",
        "implementation_phase": "fact_store",
        "mis_enabled": mis_flags.get("mis", False),
        "capabilities": {
            "import": mis_flags.get("import", False),
            "live_mitrabooks": mis_flags.get("live_mitrabooks", False),
            "export": mis_flags.get("export", False),
        },
        "enabled_packs": enabled_packs,
        "pack_catalog": list_pack_catalog(),
        "pack_count": len(packs),
        "recent_packs": packs,
        "collections": {
            "packs": "officemitra_mis_packs",
            "facts": "officemitra_mis_facts",
        },
        "enabled_modules": list(enabled_modules or []),
        "office_ai_features": list(office_ai_features or []),
    }
