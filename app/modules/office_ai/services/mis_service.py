from __future__ import annotations

import re
from typing import Any

from app.modules.office_ai.ai import orchestrator
from app.modules.office_ai.services import mis_store

_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
INSUFFICIENT_DATA_TEXT = "Insufficient data for this pack — no facts available."


def citation_snapshot(fact: dict[str, Any]) -> dict[str, Any]:
    dims = fact.get("dimensions") if isinstance(fact.get("dimensions"), dict) else {}
    return {
        "fact_id": str(fact.get("fact_id") or "").strip(),
        "entity_type": str(fact.get("entity_type") or "").strip(),
        "period": fact.get("period"),
        "amount_decimal": fact.get("amount_decimal"),
        "amount_minor": fact.get("amount_minor"),
        "value": fact.get("value"),
        "currency": fact.get("currency") or "INR",
        "source_ref": fact.get("source_ref"),
        "source_system": fact.get("source_system"),
        "label": str(dims.get("line") or dims.get("kpi") or dims.get("bucket") or "").strip() or None,
    }


def deterministic_narrative_bullets(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots = [citation_snapshot(item) for item in facts if str(item.get("fact_id") or "").strip()]
    if not snapshots:
        return [{"text": INSUFFICIENT_DATA_TEXT, "fact_ids": [], "source": "deterministic"}]
    bullets: list[dict[str, Any]] = []
    for item in snapshots[:12]:
        amount = item.get("amount_decimal")
        if amount is None:
            amount = item.get("value")
        label = item.get("label") or item.get("entity_type") or "fact"
        parts = [str(label)]
        if item.get("period"):
            parts.append(str(item["period"]))
        if amount is not None:
            currency = item.get("currency") or ""
            parts.append(f"{amount} {currency}".strip())
        bullets.append(
            {
                "text": " · ".join(parts),
                "fact_ids": [item["fact_id"]],
                "source": "deterministic",
            }
        )
    return bullets


def _allowed_number_tokens(facts: list[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for fact in facts:
        for key in ("amount_decimal", "value", "amount_minor", "period"):
            raw = fact.get(key)
            if raw is None:
                continue
            compact = str(raw).replace(",", "").strip()
            if not compact:
                continue
            tokens.add(compact)
            # Periods like 2026-07 tokenize as 2026 and 07 in narrative text.
            for match in _NUMBER_RE.findall(compact):
                tokens.add(match.replace(",", ""))
    return tokens


def _numbers_are_grounded(text: str, cited: list[dict[str, Any]]) -> bool:
    allowed = _allowed_number_tokens(cited)
    for match in _NUMBER_RE.findall(text or ""):
        compact = match.replace(",", "")
        if compact not in allowed:
            return False
    return True


def sanitize_narrative_bullets(
    bullets: list[Any],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    snapshots = [citation_snapshot(item) for item in facts if str(item.get("fact_id") or "").strip()]
    by_id = {item["fact_id"]: item for item in snapshots}
    if not snapshots:
        return [{"text": INSUFFICIENT_DATA_TEXT, "fact_ids": [], "source": "deterministic"}]

    cleaned: list[dict[str, Any]] = []
    for raw in bullets or []:
        if not isinstance(raw, dict):
            continue
        fact_ids = [
            str(fid).strip()
            for fid in (raw.get("fact_ids") or [])
            if str(fid).strip() in by_id
        ]
        if not fact_ids:
            continue
        cited = [by_id[fid] for fid in fact_ids]
        text = str(raw.get("text") or "").strip()
        source = "ai"
        if not text or not _numbers_are_grounded(text, cited):
            fallback = deterministic_narrative_bullets(cited)
            text = fallback[0]["text"] if fallback else INSUFFICIENT_DATA_TEXT
            source = "deterministic"
        cleaned.append({"text": text[:1000], "fact_ids": fact_ids, "source": source})
    return cleaned or deterministic_narrative_bullets(facts)


async def generate_pack_narrative(
    *,
    tenant_id: str,
    pack_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    pack = await mis_store.get_pack(tenant_id=tenant_id, pack_id=pack_id)
    if pack is None:
        raise mis_store.MISPackNotFoundError(f"MIS pack not found: {pack_id}")
    facts = await mis_store.list_facts(tenant_id=tenant_id, pack_id=pack_id, limit=200)
    snapshots = [citation_snapshot(item) for item in facts]
    ai_result = await orchestrator.build_mis_narrative(
        tenant_id=tenant_id,
        facts=snapshots,
        user_id=str(user.get("sub") or user.get("user_id") or user.get("id") or "").strip() or None,
    )
    bullets = sanitize_narrative_bullets(ai_result.get("bullets") or [], facts)
    narrative = {
        "bullets": bullets,
        "prompt_version": ai_result.get("prompt_version"),
        "provider": ai_result.get("provider"),
        "model": ai_result.get("model"),
        "telemetry_id": ai_result.get("telemetry_id"),
        "ai_available": bool(ai_result.get("ai_available")),
        "advisory": ai_result.get("advisory"),
        "source": "ai" if ai_result.get("ai_available") else "deterministic",
    }
    pack = await mis_store.save_narrative(
        tenant_id=tenant_id,
        pack_id=pack_id,
        user=user,
        narrative=narrative,
    )
    return {"item": pack, "narrative": pack.get("narrative") or narrative, **{k: ai_result.get(k) for k in ("ai_available", "error_code", "advisory")}}

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
        "implementation_phase": "narrative",
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
