"""Code-registered LegalMitra Stage 5 workflow catalog and definitions."""
from __future__ import annotations

from typing import Any

WORKFLOW_CATALOG: list[dict[str, Any]] = [
    {
        "workflow_key": "prepare_matter_response",
        "display_name": "Prepare Matter Response",
        "catalog_status": "mvp",
        "description": "Guided intake → research → evidence check → draft → human review.",
    },
    {
        "workflow_key": "hearing_preparation",
        "display_name": "Hearing Preparation",
        "catalog_status": "planned",
        "description": "Planned: hearing prep pack from timeline, docs, and brief.",
    },
    {
        "workflow_key": "contract_review",
        "display_name": "Contract Review",
        "catalog_status": "planned",
        "description": "Planned: structured contract review workflow.",
    },
    {
        "workflow_key": "gst_notice_reply",
        "display_name": "GST Notice Reply",
        "catalog_status": "planned",
        "description": "Planned template pack on the Prepare Matter Response engine.",
    },
    {
        "workflow_key": "income_tax_notice",
        "display_name": "Income Tax Notice",
        "catalog_status": "planned",
        "description": "Planned template pack on the Prepare Matter Response engine.",
    },
    {
        "workflow_key": "roc_filing_review",
        "display_name": "ROC Filing Review",
        "catalog_status": "planned",
        "description": "Planned: secretarial filing review checklist.",
    },
]

_PREPARE_STEPS: list[dict[str, Any]] = [
    {
        "step_key": "INTAKE",
        "adapter": "matter_intake",
        "requires_human_gate": False,
        "estimated_minutes": 3,
    },
    {
        "step_key": "RESEARCH",
        "adapter": "legal_research",
        "requires_human_gate": True,
        "estimated_minutes": 6,
    },
    {
        "step_key": "EVIDENCE_CHECK",
        "adapter": "document_evidence",
        "requires_human_gate": False,
        "estimated_minutes": 4,
    },
    {
        "step_key": "DRAFT",
        "adapter": "drafting",
        "requires_human_gate": True,
        "estimated_minutes": 4,
    },
    {
        "step_key": "HUMAN_REVIEW",
        "adapter": "human_review_gate",
        "requires_human_gate": True,
        "estimated_minutes": 8,
    },
    {
        "step_key": "COMPLETE",
        "adapter": "complete",
        "requires_human_gate": False,
        "estimated_minutes": 1,
    },
]

WORKFLOW_DEFINITIONS: dict[str, dict[str, Any]] = {
    "prepare_matter_response": {
        "workflow_key": "prepare_matter_response",
        "version": 1,
        "workflow_template": "general",
        "display_name": "Prepare Matter Response",
        "catalog_status": "mvp",
        "steps": list(_PREPARE_STEPS),
        "allowed_practice_areas": [
            "gst",
            "income_tax",
            "litigation",
            "advisory",
            "compliance",
            "contract",
            "secretarial",
            "general",
        ],
        "enabled": True,
    }
}

TEMPLATE_QUERY_SEEDS: dict[str, str] = {
    "general": (
        "Summarize applicable Indian legal issues and next procedural steps "
        "for this matter under Indian law with citations where available."
    ),
    "gst_notice": (
        "CGST Act Section 54 GST refund time limit and GST show-cause or demand "
        "notice response issues under CGST Act for India with citations."
    ),
    "income_tax_notice": (
        "Income Tax Act 1961 Section 139 return filing and notice response "
        "issues for India with citations."
    ),
}

TEMPLATE_DOC_CHECKLIST: dict[str, list[str]] = {
    "general": ["Primary notice or pleading", "Client instructions", "Key evidence"],
    "gst_notice": [
        "SCN / order",
        "GST returns extract",
        "Payment / challan proof",
        "Grounds draft inputs",
    ],
    "income_tax_notice": [
        "IT notice",
        "Return / AIS extract",
        "Supporting accounts",
        "Prior replies",
    ],
}


def list_catalog() -> list[dict[str, Any]]:
    return [dict(item) for item in WORKFLOW_CATALOG]


def get_definition(workflow_key: str) -> dict[str, Any] | None:
    definition = WORKFLOW_DEFINITIONS.get(workflow_key)
    return dict(definition) if definition else None


def list_enabled_definitions() -> list[dict[str, Any]]:
    return [dict(d) for d in WORKFLOW_DEFINITIONS.values() if d.get("enabled")]


def resolve_template(workflow_template: str | None) -> str:
    raw = (workflow_template or "general").strip().lower()
    if raw in TEMPLATE_QUERY_SEEDS:
        return raw
    return "general"
